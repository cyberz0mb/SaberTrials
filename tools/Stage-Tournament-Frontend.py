"""Native Play -> Tournament visual preview. No server, account or match actions."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT/'dist/tournament-frontend-staging'
STATE = ROOT/'dist/tournament-frontend-install.json'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def block_span(text, kind, name):
    match = re.search(r'\b'+kind+r'\s*\{\s*name\s+"?'+re.escape(name)+r'"?(?=\s|\})', text)
    if not match:
        raise ValueError(name)
    depth = 0
    for token in re.finditer(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/|[{}]', text[match.start():], re.S):
        if token[0] == '{': depth += 1
        if token[0] == '}':
            depth -= 1
            if depth == 0:
                return match.start(), match.start()+token.end()
    raise ValueError('Unclosed '+name)


def clean_player(text):
    try:
        a, b = block_span(text, 'itemDef', 'sabertrialsTournament')
        text = text[:a]+text[b:]
    except ValueError:
        pass
    a, b = block_span(text, 'menuDef', 'ingame_player')
    # Keep the exact Player menu body; discard the obsolete second wrapper.
    return text[:a]+text[a:b]+'\n}\n'


def label(name, text, x, y, w=550, scale='.72', color='.76 .86 .93 1', cvar=False, extra=''):
    return f'itemDef {{ name {name} rect {x} {y} {w} 22 type 0 {"cvar" if cvar else "text"} "{text}" font 2 textscale {scale} forecolor {color} visible 1 decoration {extra} }}\n'


def box(name, x, y, w, h):
    return f'itemDef {{ name {name} rect {x} {y} {w} {h} style 1 backcolor .008 .026 .044 .94 border 1 bordersize .5 bordercolor .30 .78 1 .4 visible 1 decoration }}\n'


def shown(cvar, value):
    return f'cvarTest "ui_stFront{cvar}" showCvar {{ "{value}" }}'


def button(name, text, x, y, w, action, extra=''):
    return f'''itemDef {{ name {name} rect {x} {y} {w} 30 type 1 text "{text}" font 2 textscale .78
 textalignx 10 textaligny 6 forecolor .76 .86 .93 1 visible 1 {extra}
 style 1 backcolor .015 .055 .08 .94 border 1 bordersize .5 bordercolor .30 .78 1 .5
 onFocus {{ setitemcolor {name} backcolor .035 .19 .28 .98 ; }}
 leaveFocus {{ setitemcolor {name} backcolor .015 .055 .08 .94 ; }}
 action {{ play "sound/interface/button1.wav" ; {action} ; }} }}
'''


def page(name, title, back, focus='back'):
    s = f'''menuDef {{ name "{name}" rect 0 0 640 480 visible 0 fullscreen 1
 focusColor 1 1 1 1 disableColor .35 .42 .47 1
 onOpen {{ setfocus {focus} ; }} onESC {{ close {name} ; open {back} ; }}
 itemDef {{ name arena rect 0 0 640 480 style 3 background "ui/assets/sabertrials/arena.tga" forecolor 1 1 1 1 visible 1 decoration }}
 itemDef {{ name shade rect 0 0 640 480 style 1 backcolor .004 .015 .028 .60 visible 1 decoration }}
'''
    s += label('brand', 'S A B E R   T R I A L S', 28, 20, scale='1.15', color='.30 .78 1 1')
    s += label('heading', 'TOURNAMENT  /  '+title, 28, 57, scale='.86')
    s += label('preview', 'VISUAL PREVIEW', 482, 28, 140, '.62', '.53 .77 .9 1')
    s += label('sample', 'Sample players and events. No live registration or match starts.', 212, 441, 400, '.58', '.57 .72 .81 1')
    s += button('back', 'Back to Play' if back == 'multiplayermenu' else 'Back to ready room', 28, 434, 171,
                f'close {name} ; open {back}')
    return s


def route(source, destination):
    return f'close {source} ; open {destination}'


def pages():
    s = page('st_main_tournament', 'SELECT A FORMAT', 'multiplayermenu', 'individual')
    s += label('intro', 'Choose a tournament to view its ready room.', 28, 98, scale='.82')
    s += box('individual_card', 28, 140, 282, 271)+box('team_card', 326, 140, 286, 271)
    s += label('solo_title', 'INDIVIDUAL', 46, 158, 250, '1', '.30 .78 1 1')
    for i, text in enumerate(('One duelist. One champion.', '8-32 players / even entries', '10 rounds per match', '5-5 tie: one deciding round', '5 minutes to reconnect')):
        s += label('solo_rule'+str(i), text, 46, 193+i*27, 250, '.72')
    action = 'exec "exec st-tournament-preview-individual.cfg" ; '+route('st_main_tournament','st_tournament_ready')
    s += button('individual', 'Enter individual lobby', 46, 359, 246, action)
    s += label('team_title', 'TEAMS', 344, 158, 250, '1', '.30 .78 1 1')
    for i, text in enumerate(('Up to 8 registered teams', 'One TFFA match / respawns', 'Complete, equal lineups required')):
        s += label('team_rule'+str(i), text, 344, 193+i*25, 250, '.69')
    for n in range(2, 6):
        action = f'exec "exec st-tournament-preview-{n}v{n}.cfg" ; '+route('st_main_tournament','st_tournament_ready')
        s += button('team'+str(n), f'{n}v{n} / {n*10} kills', 344+(n%2)*126, 279+((n-2)//2)*38, 120, action)
    s += label('team_reconnect','10 minutes: reconnect or substitute',344,365,250,'.66')
    s += label('team_ready','Every active player selects Ready.',344,387,250,'.66')
    s += '}\n'

    name = 'st_tournament_ready'
    s += page(name, 'READY ROOM', 'st_main_tournament', 'ready')
    # Returning to selection is a clear, local preview navigation action.
    start = s.rfind('menuDef')
    s = s[:start]+s[start:].replace('Back to ready room','Select tournament',1)
    s += label('event','ui_stFrontEvent',28,96,584,'.94','.30 .78 1 1',True)
    s += label('entries','ui_stFrontEntries',28,125,584,'.67',cvar=True)
    for side, x in enumerate((28,326)):
        s += box('roster'+str(side),x,158,286,190)
        s += label('team'+str(side),'ui_stFrontSide'+str(side),x+16,170,250,'.84','.9 .96 1 1',True)
        if side == 0:
            for ready in (0,1):
                s += label('count'+str(ready),'ui_stFrontCount'+str(ready),x+16,196,250,'.62',cvar=True,extra=shown('Ready',ready))
        else:
            s += label('opponentcount','ui_stFrontOpponentCount',x+16,196,250,'.62',cvar=True)
        for row in range(5):
            y = 222+row*24
            if side == row == 0:
                for ready in (0,1):
                    s += label('you'+str(ready),'You (preview)  /  '+('READY' if ready else 'Not ready'),x+16,y,250,'.68',
                               '.42 .87 .77 1' if ready else '.96 .8 .47 1',extra=shown('Ready',ready))
            else:
                s += label('row'+str(side)+str(row),'ui_stFrontRow'+str(side*5+row),x+16,y,250,'.68',cvar=True)
    s += label('waiting','Select Ready when you are prepared. Select again to unready.',28,361,584,'.69',extra=shown('Ready',0))
    s += label('allready','Everyone is ready. This preview does not start a match.',28,361,584,'.69','.42 .87 .77 1',extra=shown('Ready',1))
    s += button('ready','Ready',28,391,140,'setcvar ui_stFrontReady "1" ; setfocus unready',shown('Ready',0))
    s += button('unready','Ready / Unready',28,391,140,'setcvar ui_stFrontReady "0" ; setfocus ready',shown('Ready',1))
    s += button('bracket','View bracket',180,391,140,route(name,'st_tournament_bracket1'))
    s += button('reserves','Team reserves',332,391,140,route(name,'st_tournament_reserves'),shown('Team',1))
    s += button('leave','Leave lobby',484,391,128,route(name,'st_tournament_leave'))
    s += '}\n'

    for p in range(1,5):
        name = 'st_tournament_bracket'+str(p)
        s += page(name,'BRACKET','st_tournament_ready')
        s += label('stage','ui_stFrontBracketHeading'+str(p),28,99,584,'.83','.30 .78 1 1',True)
        s += box('matches',28,137,584,244)
        for r in range(8):
            idx = (p-1)*8+r
            s += label('match'+str(r),'ui_stFrontMatch'+str(idx),44,149+r*28,552,'.72',cvar=True)
        for n in range(1,5):
            s += button('page'+str(n),str(n),28+(n-1)*52,391,44,route(name,'st_tournament_bracket'+str(n)),shown('BracketPage'+str(n),1))
        s += label('legend','Current match is marked >. Later pairings await results.',260,398,352,'.62')
        s += '}\n'

    name = 'st_tournament_reserves'
    s += page(name,'TEAM RESERVES','st_tournament_ready')
    s += box('content',28,135,584,279)
    s += label('team','ui_stFrontSide0',46,151,548,'.95','.30 .78 1 1',True)
    for i,text in enumerate(('Only reserves registered with this team may replace a player.',
                              'A disconnect pauses the match for up to 10 minutes.',
                              'The missing player may reconnect, or a reserve takes their place.',
                              'The complete lineup must ready up again before play resumes.')):
        s += label('rule'+str(i),text,46,190+i*25,548,'.73')
    s += label('reserve','Lyra  /  Registered reserve (sample)',46,309,548,'.82')
    s += label('available','Both lineups are complete. No replacement is needed.',46,354,548,'.74')
    s += '}\n'
    name = 'st_tournament_leave'
    s += page(name,'LEAVE LOBBY?','st_tournament_ready','stay')
    s += box('content',28,146,584,254)
    s += label('question','Return to tournament selection?',48,171,544,'1','.30 .78 1 1')
    s += label('explain','Your sample ready status will reset when you select another event.',48,218,544,'.75')
    s += button('confirm','Leave lobby',48,322,240,'setcvar ui_stFrontReady "0" ; '+route(name,'st_main_tournament'))
    s += button('stay','Stay in ready room',308,322,282,route(name,'st_tournament_ready'))
    return s+'}\n'


def config(size):
    team = size > 1
    v = dict(Ready=0,Team=int(team),Event=f'{size}v{size} TEAM TOURNAMENT / {size*10} KILLS' if team else 'INDIVIDUAL TOURNAMENT / 10 ROUNDS',
             Entries='8 / 8 teams  |  Quarterfinals  |  Match 1' if team else '32 / 32 players  |  Round of 32  |  Match 1',
             Side0='Blue Horizon' if team else 'You (preview)', Side1='Crimson Guard' if team else 'Mira',
             Count0=f'{size}/{size} present  |  {size-1}/{size} ready',Count1=f'{size}/{size} present  |  {size}/{size} ready',
             OpponentCount=f'{size}/{size} present  |  {size}/{size} ready')
    for i in range(10):
        v['Row'+str(i)] = ''
    for i in range(1,size): v['Row'+str(i)] = ('Mira','Orion','Rook','Nova')[i-1]+'  /  READY'
    for i in range(size): v['Row'+str(i+5)] = (('Kade','Echo','Vex','Sol','Ash')[i] if team else 'Mira')+'  /  READY'
    for i in range(32): v['Match'+str(i)] = ''
    if team:
        for i,text in enumerate(('>  Blue Horizon  vs  Crimson Guard','Silver Dawn  vs  Nightwatch','Saber Guild  vs  Eclipse','Vanguard  vs  Nova Squad',
                                 'Semifinal 1: winners of matches 1 and 2','Semifinal 2: winners of matches 3 and 4','Final: winners of the semifinals')):
            v['Match'+str(i)] = text
    else:
        for i in range(16):
            v['Match'+str(i)] = '>  You (preview)  vs  Mira' if i==0 else f'Match {i+1}: Duelist {i*2+1}  vs  Duelist {i*2+2}'
        for i in range(16,31):
            v['Match'+str(i)] = f'Match {i+1}: awaiting winners of matches {(i-16)*2+1} and {(i-16)*2+2}'
    for i in range(1,5):
        v['BracketPage'+str(i)] = int(not team or i==1)
        v['BracketHeading'+str(i)] = '8 TEAMS / QUARTERFINALS TO FINAL' if team else ('ROUND OF 32 / MATCHES 1-8','ROUND OF 32 / MATCHES 9-16','ROUND OF 16 / MATCHES 17-24','QUARTERFINALS / SEMIFINALS / FINAL')[i-1]
    return ''.join(f'set ui_stFront{k} "{value}"\n' for k,value in v.items())


def play_menu(text):
    # Preserve brand, art and existing actions; make room for one extra row.
    a,b = block_span(text,'menuDef','multiplayermenu')
    text = text[:b]+'\n}\n'
    text = text.replace('195 269','195 290').replace('1.0 269.0','1.0 290.0')
    for key,y in [('joinserver_button',180),('startserver_button',214),('quickserver_button',248),('playdemo_button',282),('ranked',316),('rules_button',384),('back',430)]:
        for suffix,new_y in [('',y),('_line',y+(27 if key=='back' else 31)),('_icon',y+6)]:
            try: a,b = block_span(text,'itemDef',key+suffix)
            except ValueError: continue
            item = text[a:b]
            item = re.sub(r'(\brect\s+[\d.]+)\s+[\d.]+',rf'\g<1> {new_y}',item,count=1)
            if not suffix:
                item = re.sub(r'(\brect\s+[\d.]+\s+[\d.]+\s+[\d.]+)\s+[\d.]+',rf'\g<1> {28 if key=="back" else 32}',item,count=1)
                item = re.sub(r'setitemrect focus_glow [\d. ]+;',f'setitemrect focus_glow 20 {y} 192 {28 if key=="back" else 32} ;',item)
                item = item.replace('textaligny 8.0','textaligny 6.0')
            text = text[:a]+item+text[b:]
    a,b = block_span(text,'itemDef','ranked_line')
    c,d = block_span(text,'itemDef','ranked')
    row = text[a:d].replace('ranked','tournament').replace('Ranked Play','Tournament')
    row = row.replace('347','381').replace('322','356').replace('316','350')
    text = text[:d]+'\n'+row+text[d:]
    end = text.rfind('}')
    return text[:end]+pages()+text[end:]


def stage():
    STAGE.mkdir(parents=True,exist_ok=True)
    # Rerunning staging must be reproducible from pre-install originals.
    source = ROOT
    if STATE.exists() and json.loads(STATE.read_text()).get('installed'):
        source = ROOT/json.loads(STATE.read_text())['backup']
    files = {'ui/jamp/multiplayer.menu':play_menu((source/'ui/jamp/multiplayer.menu').read_text()),
             'ui/jamp/ingame_player.menu':clean_player((source/'ui/jamp/ingame_player.menu').read_text())}
    for n in range(1,6):
        files['st-tournament-preview-'+('individual' if n==1 else f'{n}v{n}')+'.cfg'] = config(n)
    for name,content in files.items():
        dest=STAGE/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(content,newline='\n')
    (STAGE/'manifest.json').write_text(json.dumps({name:digest(STAGE/name) for name in files},indent=2)+'\n')
    print('Staged Play menu, selection, ready room, bracket and reserve screens.')


def idle():
    processes=subprocess.check_output(['tasklist','/FO','CSV'],text=True).lower()
    assert not any('"'+name+'"' in processes for name in ('sabertrials.x86_64.exe','openjk.x86_64.exe','jamp.exe','openjkded.x86_64.exe')), 'Close Saber Trials before installation.'


def install():
    idle()
    assert not STATE.exists() or not json.loads(STATE.read_text()).get('installed'), 'Already installed'
    files=json.loads((STAGE/'manifest.json').read_text())
    assert files=={name:digest(STAGE/name) for name in files}
    menus={name:STAGE/name for name in files if name.endswith('.menu')}
    configs={name:STAGE/name for name in files if name.endswith('.cfg')}
    assert all(not (ROOT/name).exists() for name in configs)
    baseline=json.loads((ROOT/'dist/tournament-visual-preview-install.json').read_text())
    protected={name:digest(ROOT/name) for name in baseline['protected'] if name not in menus}
    spec=importlib.util.spec_from_file_location('staff_installer',ROOT/'tools/Install-Staff.py')
    installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
    backup=ROOT/'dist/backups'/('tournament-frontend-'+time.strftime('%Y%m%d-%H%M%S'))
    # New sample files first; absent menu routes cannot use them until transaction.
    created=[]
    try:
        for name,source in configs.items():
            with (ROOT/name).open('xb') as f:f.write(source.read_bytes())
            created.append(ROOT/name)
        record=installer.transaction(ROOT,menus,backup)
    except Exception:
        for path in created:
            assert path.resolve().parent==ROOT.resolve()
            if digest(path)==files[path.name]:path.unlink()
        raise
    assert protected=={name:digest(ROOT/name) for name in protected}
    assert files=={name:digest(ROOT/name) for name in files}
    record.update(installed=True,menu_only=True,preview_configs={name:files[name] for name in configs},protected=protected)
    STATE.write_text(json.dumps(record,indent=2)+'\n')
    print('Installed Play -> Tournament. Protected files unchanged:',len(protected))


def restore():
    idle();record=json.loads(STATE.read_text())
    if not record['installed']:print('Already restored');return
    backup=(ROOT/record['backup']).resolve()
    assert backup.is_relative_to((ROOT/'dist/backups').resolve())
    for name,h in record['after'].items():
        assert digest(ROOT/name)==h and digest(backup/name)==record['before'][name]
    for name,h in record['preview_configs'].items():
        assert re.fullmatch(r'st-tournament-preview-(individual|[2-5]v[2-5])\.cfg',name)
        assert digest(ROOT/name)==h
    for name in record['after']:
        target=ROOT/name;temporary=target.with_suffix('.front-restore')
        with temporary.open('xb') as f:f.write((backup/name).read_bytes())
        os.replace(temporary,target)
    for name in record['preview_configs']:(ROOT/name).unlink()
    record['installed']=False;STATE.write_text(json.dumps(record,indent=2)+'\n')
    print('Restored the previous menus and removed the five unchanged sample files.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('stage','install','restore'));args=p.parse_args()
    {'stage':stage,'install':install,'restore':restore}[args.action]()
