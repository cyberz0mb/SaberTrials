"""Local authoritative ranking ledger, with no network listener or login service.

Only a trusted service adapter may call mutation methods. The adapter must verify
account identities and server credentials; strings passed here are NOT proof of
authentication. No game client, Discord bot or public endpoint is connected yet.
"""
from contextlib import contextmanager
import json
import math
from pathlib import Path
import re
import sqlite3
import time
import unicodedata
from .rating import INITIAL_RATING, rate_match
from .tournament import (BONUS_INTERVAL, MIN_BONUS_ENTRANTS, MIN_PLAYED_WINS,
                         TOURNAMENT_BONUS, summarize_bracket)

ROUTES={'duel':('duel','duel'),'challenge':('duel','ffa'),'tffa':('team','tffa')}

class InvalidMatch(ValueError):
    pass

def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',value):
        raise ValueError('Invalid identifier')
    return value

def display(value,maximum=48):
    if not isinstance(value,str) or not value.strip() or len(value)>maximum:
        raise ValueError('Invalid display name')
    if any(unicodedata.category(c).startswith('C') for c in value) or '^' in value:
        raise ValueError('Display names cannot contain control/color codes')
    return value.strip()

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)

class RankingStore:
    def __init__(self,path,clock=time.time):
        self.path=Path(path);self.clock=clock
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(str(self.path),timeout=15,isolation_level=None)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA journal_mode=WAL')
        version=self.db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0,1,2):
            self.db.close();raise ValueError('Unsupported ranking database version')
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS players(id TEXT PRIMARY KEY,name TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS teams(id TEXT PRIMARY KEY,name TEXT NOT NULL,tag TEXT NOT NULL UNIQUE COLLATE NOCASE);
          CREATE TABLE IF NOT EXISTS members(player TEXT PRIMARY KEY REFERENCES players(id),team TEXT NOT NULL REFERENCES teams(id));
          CREATE TABLE IF NOT EXISTS servers(id TEXT PRIMARY KEY,name TEXT NOT NULL,enabled INTEGER NOT NULL,seen REAL,route TEXT,map TEXT,players INTEGER,capacity INTEGER);
          CREATE TABLE IF NOT EXISTS rules(id TEXT PRIMARY KEY,league TEXT NOT NULL,settings TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS ratings(league TEXT NOT NULL,rules TEXT NOT NULL REFERENCES rules(id),subject TEXT NOT NULL,rating REAL NOT NULL,wins INTEGER NOT NULL DEFAULT 0,losses INTEGER NOT NULL DEFAULT 0,draws INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(league,rules,subject));
          CREATE TABLE IF NOT EXISTS matches(id TEXT PRIMARY KEY,server TEXT NOT NULL REFERENCES servers(id),route TEXT NOT NULL,rules TEXT NOT NULL REFERENCES rules(id),status TEXT NOT NULL,started REAL NOT NULL,finished REAL,snapshot TEXT NOT NULL,result TEXT,receipt TEXT);
          CREATE TABLE IF NOT EXISTS reservations(subject TEXT PRIMARY KEY,match TEXT NOT NULL REFERENCES matches(id));
          CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,match TEXT NOT NULL REFERENCES matches(id),time REAL NOT NULL,action TEXT NOT NULL,reason TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS tournaments(id TEXT PRIMARY KEY,server TEXT NOT NULL REFERENCES servers(id),rules TEXT NOT NULL REFERENCES rules(id),champion TEXT NOT NULL REFERENCES players(id),recorded REAL NOT NULL,bonus REAL NOT NULL,snapshot TEXT NOT NULL,receipt TEXT NOT NULL);
          CREATE INDEX IF NOT EXISTS tournament_champion ON tournaments(champion,recorded);
          PRAGMA user_version=2;
        ''')

    def close(self):self.db.close()

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK');raise

    def register_verified_player(self,player_id,name):
        """Operator/auth-adapter entry point; never expose as unauthenticated signup."""
        self.db.execute('INSERT INTO players VALUES(?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name',
                        (identifier(player_id),display(name)))

    def register_team(self,team_id,name,tag):
        tag=display(tag,18)
        if not re.fullmatch(r'\[[A-Za-z0-9_-]{1,16}\]',tag):raise ValueError('Use a registered tag such as [JAWA]')
        self.db.execute('INSERT INTO teams VALUES(?,?,?)',(identifier(team_id),display(name),tag))

    def set_membership(self,player_id,team_id):
        with self.transaction():
            if self.db.execute('SELECT 1 FROM reservations WHERE subject=?',('player:'+player_id,)).fetchone():
                raise InvalidMatch('Player is in an unfinished ranked match')
            self.db.execute('INSERT INTO members VALUES(?,?) ON CONFLICT(player) DO UPDATE SET team=excluded.team',
                            (identifier(player_id),identifier(team_id)))

    def register_server(self,server_id,name):
        """Explicit operator registration; installing Saber Trials cannot call this."""
        self.db.execute('INSERT INTO servers(id,name,enabled) VALUES(?,?,1)',(identifier(server_id),display(name,80)))

    def set_server_enabled(self,server_id,enabled):
        if type(enabled) is not bool:raise ValueError('enabled must be boolean')
        if self.db.execute('UPDATE servers SET enabled=? WHERE id=?',(int(enabled),server_id)).rowcount!=1:
            raise ValueError('Unknown server')

    def _server(self,server_id):
        row=self.db.execute('SELECT * FROM servers WHERE id=? AND enabled=1',(server_id,)).fetchone()
        if not row:raise InvalidMatch('Server is not authorized')
        return row

    def heartbeat(self,server_id,route,map_name,players,capacity):
        if route not in ROUTES:raise ValueError('Unknown ranked route')
        if type(players) is not int or type(capacity) is not int or not 0<=players<=capacity<=64 or capacity<2:
            raise ValueError('Invalid server population')
        with self.transaction():
            self._server(server_id)
            self.db.execute('UPDATE servers SET seen=?,route=?,map=?,players=?,capacity=? WHERE id=?',
                            (self.clock(),route,display(map_name,64),players,capacity,server_id))

    def server_directory(self,max_age=90):
        if not isinstance(max_age,(int,float)) or not 0<max_age<=300:raise ValueError('Invalid heartbeat age')
        now=self.clock()
        return [dict(r) for r in self.db.execute('SELECT id,name,route,map,players,capacity,seen FROM servers WHERE enabled=1 AND seen BETWEEN ? AND ? ORDER BY name,id',(now-max_age,now))]

    def register_ruleset(self,rules_id,league,*,team_size=1,allow_draw=False,combat,settings):
        """Versioned operator decision; no proposed competitive rules are auto-enabled."""
        if league not in ('duel','team') or type(team_size) is not int or not 1<=team_size<=16:
            raise ValueError('Invalid league or team size')
        if league=='duel' and team_size!=1:raise ValueError('Duel is 1v1')
        if type(allow_draw) is not bool or combat not in ('original','trials') or not isinstance(settings,dict):
            raise ValueError('Invalid ruleset')
        payload={'team_size':team_size,'allow_draw':allow_draw,'combat':combat,'settings':settings}
        self.db.execute('INSERT INTO rules VALUES(?,?,?)',(identifier(rules_id),league,canonical(payload)))

    def _rating(self,league,rules,subject):
        self.db.execute('INSERT OR IGNORE INTO ratings(league,rules,subject,rating) VALUES(?,?,?,?)',
                        (league,rules,subject,INITIAL_RATING))
        return self.db.execute('SELECT rating FROM ratings WHERE league=? AND rules=? AND subject=?',
                               (league,rules,subject)).fetchone()[0]

    def start_match(self,match_id,server_id,route,rules_id,side_a,side_b,*,accepted,game_type,team_a=None,team_b=None):
        identifier(match_id)
        if route not in ROUTES or ROUTES[route][1]!=game_type:raise InvalidMatch('Wrong game type for this ranked route')
        if not isinstance(side_a,list) or not isinstance(side_b,list) or not isinstance(accepted,list):
            raise InvalidMatch('Player sides and acceptance must be lists')
        players=side_a+side_b
        if not players or any(not isinstance(p,str) for p in players+accepted):raise InvalidMatch('Invalid player identity')
        if len(set(players))!=len(players) or set(players)!=set(accepted) or len(players)!=len(accepted):
            raise InvalidMatch('Distinct participants must accept the official match')
        with self.transaction():
            self._server(server_id)
            if self.db.execute('SELECT 1 FROM matches WHERE id=?',(match_id,)).fetchone():
                raise InvalidMatch('Match ID already exists')
            rule=self.db.execute('SELECT * FROM rules WHERE id=?',(rules_id,)).fetchone()
            league=ROUTES[route][0]
            if not rule or rule['league']!=league:raise InvalidMatch('No approved ruleset for this ladder')
            policy=json.loads(rule['settings'])
            if len(side_a)!=policy['team_size'] or len(side_b)!=policy['team_size']:
                raise InvalidMatch('Roster size does not match the registered ruleset')
            for player in players:
                if not self.db.execute('SELECT 1 FROM players WHERE id=?',(player,)).fetchone():
                    raise InvalidMatch('Every participant needs a verified player account; bots are ineligible')
            if league=='team':
                if not team_a or not team_b or team_a==team_b:raise InvalidMatch('Two registered teams required')
                for team,roster in [(team_a,side_a),(team_b,side_b)]:
                    for player in roster:
                        if not self.db.execute('SELECT 1 FROM members WHERE player=? AND team=?',(player,team)).fetchone():
                            raise InvalidMatch('Player is not on this registered team roster')
                subjects=[team_a,team_b]
            else:
                if team_a is not None or team_b is not None:raise InvalidMatch('Duel rating uses players, not teams')
                subjects=[side_a[0],side_b[0]]
            rating=[self._rating(league,rules_id,s) for s in subjects]
            snapshot={'league':league,'subjects':subjects,'players':[side_a,side_b],'rating':rating,
                      'policy':policy,'accepted':sorted(accepted),'game_type':game_type}
            self.db.execute('INSERT INTO matches(id,server,route,rules,status,started,snapshot) VALUES(?,?,?,?,?,?,?)',
                            (match_id,server_id,route,rules_id,'running',self.clock(),canonical(snapshot)))
            locks=['player:'+p for p in players]
            if league=='team':locks+=['team:'+s for s in subjects]
            try:
                self.db.executemany('INSERT INTO reservations VALUES(?,?)',[(key,match_id) for key in locks])
            except sqlite3.IntegrityError as exc:raise InvalidMatch('A participant or team is already in a ranked match') from exc
            return snapshot

    def finish_match(self,match_id,server_id,outcome):
        """One confirmed outcome per match/series; kills do not award rating."""
        if outcome not in ('a','b','draw','void'):raise InvalidMatch('Invalid outcome')
        with self.transaction():
            self._server(server_id)
            match=self.db.execute('SELECT * FROM matches WHERE id=? AND server=?',(match_id,server_id)).fetchone()
            if not match:raise InvalidMatch('Unknown match or wrong reporting server')
            if match['status']!='running':
                if match['result']!=outcome:raise InvalidMatch('Conflicting duplicate result')
                return json.loads(match['receipt'])
            snap=json.loads(match['snapshot'])
            if outcome=='draw' and not snap['policy']['allow_draw']:raise InvalidMatch('This ruleset does not permit draws')
            receipt={'match_id':match_id,'route':match['route'],'ruleset':match['rules'],
                     'outcome':outcome,'old':snap['rating'],'new':snap['rating'],'delta':[0.0,0.0]}
            if outcome!='void':
                change=rate_match(*snap['rating'],{'a':1,'b':0,'draw':.5}[outcome])
                receipt.update(new=[change.new_a,change.new_b],delta=[change.delta_a,change.delta_b])
                for index,subject in enumerate(snap['subjects']):
                    won=outcome==('a' if index==0 else 'b');lost=not won and outcome!='draw'
                    self.db.execute('UPDATE ratings SET rating=?,wins=wins+?,losses=losses+?,draws=draws+? WHERE league=? AND rules=? AND subject=?',
                                    (receipt['new'][index],int(won),int(lost),int(outcome=='draw'),snap['league'],match['rules'],subject))
            self.db.execute('UPDATE matches SET status=?,finished=?,result=?,receipt=? WHERE id=?',
                            ('void' if outcome=='void' else 'completed',self.clock(),outcome,canonical(receipt),match_id))
            self.db.execute('DELETE FROM reservations WHERE match=?',(match_id,))
            return receipt

    def operator_void_match(self,match_id,reason):
        """Explicit operator recovery for unfinished matches, including revoked servers.

        This never overwrites a completed result or automatically forfeits an outage.
        Like registration, the future adapter must restrict it to trusted operators.
        """
        reason=display(reason,200)
        with self.transaction():
            match=self.db.execute('SELECT * FROM matches WHERE id=?',(match_id,)).fetchone()
            if not match:raise InvalidMatch('Unknown match')
            if match['status']=='void':return json.loads(match['receipt'])
            if match['status']!='running':raise InvalidMatch('Completed results require a separate review process')
            snap=json.loads(match['snapshot'])
            receipt={'match_id':match_id,'route':match['route'],'ruleset':match['rules'],'outcome':'void',
                     'old':snap['rating'],'new':snap['rating'],'delta':[0.0,0.0]}
            self.db.execute('UPDATE matches SET status="void",finished=?,result="void",receipt=? WHERE id=?',
                            (self.clock(),canonical(receipt),match_id))
            self.db.execute('INSERT INTO audit(match,time,action,reason) VALUES(?,?,?,?)',
                            (match_id,self.clock(),'operator_void',reason))
            self.db.execute('DELETE FROM reservations WHERE match=?',(match_id,))
            return receipt

    def record_tournament(self,tournament_id,server_id,rules_id,seeds,rounds):
        """Trusted-adapter entry point for a verified, completed championship.

        The adapter must authenticate the server, bind a globally unique event ID
        to it, and verify roster/check-in and actual series evidence. Neither
        account strings nor a consistent bracket prove that an event occurred.
        Awards use service receipt time, never a caller-supplied completion time.
        Rejected active-match submissions must retry after that match resolves;
        no championship or bonus is partially written on rejection.
        """
        identifier(tournament_id)
        try:
            summary=summarize_bracket(seeds,rounds)
            for player in summary['entrants']:identifier(player)
            snapshot=canonical({'seeds':seeds,'rounds':rounds})
        except (ValueError,TypeError) as exc:
            raise InvalidMatch(str(exc)) from exc
        champion=summary['champion']
        with self.transaction():
            self._server(server_id)
            prior=self.db.execute('SELECT * FROM tournaments WHERE id=?',(tournament_id,)).fetchone()
            if prior:
                if (prior['server']!=server_id or prior['rules']!=rules_id
                        or prior['snapshot']!=snapshot):
                    raise InvalidMatch('Conflicting tournament result or wrong reporting server')
                return json.loads(prior['receipt'])
            rule=self.db.execute('SELECT * FROM rules WHERE id=?',(rules_id,)).fetchone()
            if not rule or rule['league']!='duel':
                raise InvalidMatch('Tournament bonus requires an approved Duel ruleset')
            for player in summary['entrants']:
                if not self.db.execute('SELECT 1 FROM players WHERE id=?',(player,)).fetchone():
                    raise InvalidMatch('Tournament entrants require verified human accounts')
            # finish_match applies its starting rating snapshot. Never change that
            # rating underneath it or the bonus could be lost or miscomputed.
            if self.db.execute('SELECT 1 FROM reservations WHERE subject=?',('player:'+champion,)).fetchone():
                raise InvalidMatch('Champion has an unfinished ranked match; retry after resolution')
            now=self.clock()
            if isinstance(now,bool) or not isinstance(now,(int,float)) or not math.isfinite(now):
                raise InvalidMatch('Invalid service clock')
            previous=self.db.execute('SELECT MAX(recorded) FROM tournaments WHERE champion=? AND bonus>0',
                                     (champion,)).fetchone()[0]
            if len(summary['entrants'])<MIN_BONUS_ENTRANTS:
                reason='insufficient_entrants'
            elif summary['played_wins']<MIN_PLAYED_WINS:
                reason='insufficient_played_wins'
            elif previous is not None and now<previous+BONUS_INTERVAL:
                reason='weekly_limit'
            else:
                reason='awarded'
            bonus=TOURNAMENT_BONUS if reason=='awarded' else 0.0
            old=self._rating('duel',rules_id,champion)
            receipt={'tournament_id':tournament_id,'ruleset':rules_id,'champion':champion,
                     'entrants':len(summary['entrants']),'played_series_wins':summary['played_wins'],
                     'old':old,'new':old+bonus,'bonus':bonus,'bonus_reason':reason,
                     'recorded_at':now,
                     'next_bonus_at':now+BONUS_INTERVAL if bonus else
                         (previous+BONUS_INTERVAL if previous is not None else None)}
            self.db.execute('UPDATE ratings SET rating=rating+? WHERE league="duel" AND rules=? AND subject=?',
                            (bonus,rules_id,champion))
            self.db.execute('INSERT INTO tournaments VALUES(?,?,?,?,?,?,?,?)',
                            (tournament_id,server_id,rules_id,champion,now,bonus,snapshot,canonical(receipt)))
            return receipt

    def leaderboard(self,league,rules_id,limit=100):
        if league not in ('duel','team') or type(limit) is not int or not 1<=limit<=1000:raise ValueError('Invalid leaderboard request')
        table='players' if league=='duel' else 'teams'
        tag="''" if league=='duel' else 'p.tag'
        rows=self.db.execute(f'''SELECT r.subject AS id,p.name,{tag} AS tag,r.rating,r.wins,r.losses,r.draws,
            (r.wins+r.losses+r.draws) AS matches,
            COALESCE(t.championships,0) AS tournament_wins,
            COALESCE(t.points,0) AS tournament_bonus_points
            FROM ratings r JOIN {table} p ON p.id=r.subject
            LEFT JOIN (SELECT champion,rules,COUNT(*) AS championships,SUM(bonus) AS points
                       FROM tournaments GROUP BY champion,rules) t
                ON r.league='duel' AND t.champion=r.subject AND t.rules=r.rules
            WHERE r.league=? AND r.rules=? AND ((r.wins+r.losses+r.draws)>0 OR COALESCE(t.championships,0)>0)
            ORDER BY r.rating DESC,r.subject LIMIT ?''',(league,rules_id,limit))
        result=[];previous=None;rank=0
        for position,row in enumerate(rows,1):
            item=dict(row)
            if previous!=item['rating']:rank=position
            previous=item['rating'];item['rank']=rank;result.append(item)
        return result
