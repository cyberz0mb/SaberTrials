import concurrent.futures
from pathlib import Path
import sqlite3
import tempfile
import unittest
from services.ranking.store import RankingStore, InvalidMatch

class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='st-ranking-test-')
        self.path=Path(self.temp.name)/'ranking.sqlite'
        self.now=1000
        self.store=RankingStore(self.path,clock=lambda:self.now)
        for i in range(1,5):self.store.register_verified_player(f'p{i}',f'Player {i}')
        self.store.register_server('s1','Test server')
        self.store.register_server('s2','Other server')
        self.store.register_ruleset('duel-original-v1','duel',combat='original',settings={'test_only':True})
        self.store.register_ruleset('duel-trials-v1','duel',combat='trials',settings={'test_only':True})
        self.store.register_ruleset('team-original-v1','team',combat='original',team_size=2,allow_draw=True,settings={'test_only':True})

    def tearDown(self):
        self.store.close();self.temp.cleanup()

    def duel(self,id='m1',route='duel',rules='duel-original-v1',a='p1',b='p2',**overrides):
        args=dict(match_id=id,server_id='s1',route=route,rules_id=rules,side_a=[a],side_b=[b],accepted=[a,b],game_type='ffa' if route=='challenge' else 'duel')
        args.update(overrides);return self.store.start_match(**args)

    def test_empty_has_no_invented_standings_or_online_servers(self):
        self.assertEqual(self.store.leaderboard('duel','duel-original-v1'),[])
        self.assertEqual(self.store.server_directory(),[])
        self.duel()
        self.assertEqual(self.store.leaderboard('duel','duel-original-v1'),[])

    def test_duel_and_challenge_share_rating_and_durable_history(self):
        self.duel();self.store.finish_match('m1','s1','a')
        snapshot=self.duel('m2','challenge')
        self.assertEqual(snapshot['rating'],[1012,988])
        receipt=self.store.finish_match('m2','s1','b')
        self.assertGreater(receipt['delta'][1],12)
        self.assertAlmostEqual(sum(receipt['new']),2000)
        self.store.close();self.store=RankingStore(self.path)
        rows=self.store.leaderboard('duel','duel-original-v1')
        self.assertEqual([r['matches'] for r in rows],[2,2])
        self.assertEqual(self.store.finish_match('m2','s1','b'),receipt)

    def test_same_result_is_exactly_once_conflicting_retry_rejected(self):
        self.duel();first=self.store.finish_match('m1','s1','a')
        self.assertEqual(self.store.finish_match('m1','s1','a'),first)
        with self.assertRaises(InvalidMatch):self.store.finish_match('m1','s1','b')
        self.assertEqual(self.store.leaderboard('duel','duel-original-v1')[0]['wins'],1)

    def test_parallel_result_retries_apply_once(self):
        self.duel()
        def submit(_):
            store=RankingStore(self.path)
            try:return store.finish_match('m1','s1','a')
            finally:store.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(submit,range(2)))
        self.assertEqual(results[0],results[1])
        self.assertEqual(self.store.leaderboard('duel','duel-original-v1')[0]['rating'],1012)

    def test_authorized_server_and_match_ownership_required(self):
        with self.assertRaises(InvalidMatch):self.duel(server_id='unregistered')
        self.duel()
        with self.assertRaises(InvalidMatch):self.store.finish_match('m1','s2','a')
        self.store.set_server_enabled('s1',False)
        with self.assertRaises(InvalidMatch):self.store.finish_match('m1','s1','a')
        self.assertEqual(self.store.leaderboard('duel','duel-original-v1'),[])

    def test_no_self_matches_bots_missing_acceptance_or_wrong_route(self):
        for args in [dict(b='p1'),dict(b='bot:kyle'),dict(accepted=['p1']),dict(game_type='tffa'),dict(route='challenge',game_type='duel')]:
            with self.subTest(args=args),self.assertRaises(InvalidMatch):self.duel(**args)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM matches').fetchone()[0],0)

    def test_active_reservations_and_failed_start_roll_back(self):
        self.duel()
        with self.assertRaises(InvalidMatch):self.duel('m2',a='p1',b='p3')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM matches').fetchone()[0],1)
        self.assertIsNone(self.store.db.execute('SELECT * FROM ratings WHERE subject="p3"').fetchone())
        self.store.finish_match('m1','s1','void')
        self.duel('m2',a='p1',b='p3')

    def test_void_does_not_rate_and_draw_needs_explicit_policy(self):
        self.duel()
        with self.assertRaises(InvalidMatch):self.store.finish_match('m1','s1','draw')
        self.assertEqual(self.store.finish_match('m1','s1','void')['delta'],[0,0])
        self.assertEqual(self.store.leaderboard('duel','duel-original-v1'),[])

    def test_competitive_presets_have_separate_ladders(self):
        self.duel();self.store.finish_match('m1','s1','a')
        self.assertEqual(self.duel('m2',rules='duel-trials-v1')['rating'],[1000,1000])
        self.store.finish_match('m2','s1','b')
        self.assertEqual(self.store.leaderboard('duel','duel-original-v1')[0]['id'],'p1')
        self.assertEqual(self.store.leaderboard('duel','duel-trials-v1')[0]['id'],'p2')
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.register_ruleset('duel-original-v1','duel',combat='trials',settings={})

    def team_setup(self):
        self.store.register_team('t1','Jawa','[JAWA]');self.store.register_team('t2','Sith','[SITH]')
        for p,t in [('p1','t1'),('p2','t1'),('p3','t2'),('p4','t2')]:self.store.set_membership(p,t)

    def team_match(self,**overrides):
        args=dict(match_id='m1',server_id='s1',route='tffa',rules_id='team-original-v1',side_a=['p1','p2'],
                  side_b=['p3','p4'],accepted=['p1','p2','p3','p4'],game_type='tffa',team_a='t1',team_b='t2')
        args.update(overrides);return self.store.start_match(**args)

    def test_registered_team_rating_not_individual_kill_rating(self):
        self.team_setup();self.team_match()
        with self.assertRaises(InvalidMatch):self.store.set_membership('p1','t2')
        self.store.finish_match('m1','s1','a')
        rows=self.store.leaderboard('team','team-original-v1')
        self.assertEqual([(r['tag'],r['rating']) for r in rows],[('[JAWA]',1012),('[SITH]',988)])
        self.assertEqual(self.store.leaderboard('duel','duel-original-v1'),[])
        self.assertEqual(self.duel('m2')['rating'],[1000,1000])

    def test_team_tags_rosters_and_size_are_validated(self):
        self.team_setup()
        with self.assertRaises(sqlite3.IntegrityError):self.store.register_team('t3','Duplicate','[jawa]')
        for args in [dict(team_a='fake'),dict(team_b='t1'),dict(side_a=['p1']),dict(side_a=['p1','p3'],side_b=['p2','p4'])]:
            with self.subTest(args=args),self.assertRaises(InvalidMatch):self.team_match(**args)

    def test_permitted_draws_and_equal_rating_ties(self):
        self.team_setup();self.team_match();self.store.finish_match('m1','s1','draw')
        rows=self.store.leaderboard('team','team-original-v1')
        self.assertEqual([r['rank'] for r in rows],[1,1])
        self.assertEqual([r['draws'] for r in rows],[1,1])

    def test_directory_excludes_stale_revoked_and_future_heartbeats(self):
        self.store.heartbeat('s1','duel','mp/duel3',2,4)
        self.assertEqual(len(self.store.server_directory()),1)
        self.now=999;self.assertEqual(self.store.server_directory(),[])
        self.now=1091;self.assertEqual(self.store.server_directory(),[])
        self.store.heartbeat('s1','challenge','mp/ffa3',3,16)
        self.store.set_server_enabled('s1',False)
        self.assertEqual(self.store.server_directory(),[])

    def test_reject_invalid_metadata_without_database_changes(self):
        with self.assertRaises(ValueError):self.store.register_verified_player('bad id','Name')
        with self.assertRaises(ValueError):self.store.register_verified_player('id','Name\ncommand')
        with self.assertRaises(ValueError):self.store.heartbeat('s1','duel','mp/duel3',7,4)
        with self.assertRaises(ValueError):self.store.register_ruleset('bad','duel',combat='original',settings={'nan':float('nan')})

    def test_operator_can_release_abandoned_match_without_awarding_points(self):
        self.duel();self.store.set_server_enabled('s1',False)
        self.store.operator_void_match('m1','Server revoked during match')
        self.assertEqual(self.store.leaderboard('duel','duel-original-v1'),[])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM audit').fetchone()[0],1)
        self.store.operator_void_match('m1','Retry')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM audit').fetchone()[0],1)
        self.duel('m2',server_id='s2');self.store.finish_match('m2','s2','a')
        with self.assertRaises(InvalidMatch):self.store.operator_void_match('m2','Cannot erase history')

if __name__=='__main__':unittest.main()
