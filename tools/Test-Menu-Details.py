"""Native-event checks and presentation/behavior boundary checks for detail menus."""
from pathlib import Path
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent.parent
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
theme=module('theme','Theme-Menu-Details.py')
native=module('native','Test-Menu.py')
EVIDENCE=ROOT/'dist/verification/menu-details-20261006'

def semantics(s):
    tokens=[m[0] for m in theme.TOKEN.finditer(theme.stripped(s))]
    visual={**dict.fromkeys(['rect','forecolor','backcolor','bordercolor','outlinecolor','focuscolor','disablecolor','desccolor'],4),
            **dict.fromkeys(['text','desctext','background','font','textscale','textalign','textalignx','textaligny',
                            'textstyle','style','border','bordersize','descx','descy','descscale','descalignment'],1),
            'model_g2mins':3,'setitemrect':5,'setitemcolor':6}
    result=[];i=0
    while i<len(tokens):
        t=tokens[i];n=visual.get(t.lower())
        if t.lower() in ('name','group','show','hide','open','close','setfocus','cvar','cvartest'):
            result+=tokens[i:i+2];i+=2;continue
        if n is not None:i+=n+1;continue
        if t!=';':result.append(t)
        i+=1
    return result

def structure():
    counts={}
    for name in theme.NAMES:
        source=theme.stripped(theme.read_source(theme.SOURCE/(name+'.menu')))
        output=theme.stripped(theme.read_source(theme.OUT/'ui/jamp'/(name+'.menu')))
        for a,b in reversed(theme.blocks(output,'itemDef')):
            if theme.get(output[a:b],'name').startswith('st_editor_'):output=output[:a]+output[b:]
        assert semantics(source)==semantics(output),'Functional menu structure changed: '+name
        counts[name]=len(theme.blocks(source,'itemDef'))
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    (EVIDENCE/'structure.json').write_text(json.dumps(counts,indent=2)+'\n')
    print('PASS: all original actions, conditions, cvars, feeders and item identities preserved in',len(counts),'menus',flush=True)

def start(width=1280,height=1024,installed=False):
    # Use the actual installed maps, characters, fonts and menu extensions.
    # Hardlinks add no duplicate game assets and the test has its own config.
    for folder,dest in [(ROOT.parent/'base',native.RUNTIME/'base'),(ROOT,native.MOD)]:
        dest.mkdir(parents=True,exist_ok=True)
        for p in folder.glob('*.pk3'):
            q=dest/p.name
            if not q.exists():q.hardlink_to(p)
    native.start('installed' if installed else 'qa',width,height,None if installed else theme.OUT)

def capture_pause():
    native.pause_suite()
    for menu in ['ingame_setup','ingame_controls','ingame_player']:
        native.command('ui_openmenu '+menu);native.focused(menu)
        native.command('screenshot_png detail-'+menu)
        native.escape()
    print('PASS: matching in-game editors and exact numeric input',flush=True)

def title(width):
    lines=['disconnect','wait 45','ui_openmenu main','wait 10']
    expectations={}
    def step(name,commands,expected,extra=()):
        lines.extend(['echo DETAILS_STEP_'+name]+commands+['wait 15','st_clientqa state']+list(extra)+['echo DETAILS_END_'+name])
        expectations[name]=expected
    def click(menu,item):return [f'st_clientqa move {menu} {item}','st_clientqa click','wait 5']
    def screenshot(name):return ['screenshot_png details-'+str(width)+'-'+name]
    step('profile',click('main','profile'),'playerMenu',screenshot('profile'))
    step('name',['set ui_Name ""']+click('playerMenu','namefield')+['st_clientqa type ThemeQA','st_clientqa enter'],'playerMenu',['ui_Name'])
    step('model',click('playerMenu','headlist'),'playerMenu',['ui_model'])
    step('custom',click('playerMenu','custom'),'playerMenu2',screenshot('custom'))
    step('customback',['st_clientqa escape'],'playerMenu')
    step('saber',click('playerMenu','next'),'saberMenu',screenshot('saber'))
    step('controls',['ui_openmenu controlsMenu'],'controlsMenu',screenshot('controls'))
    for name in ['attackcontrolbutton','weaponscontrolbutton','forcecontrolbutton','forcecontrolbutton2','mousejoystickcontrolbutton','othercontrolbutton']:
        step(name,click('controlsMenu',name),'controlsMenu')
    step('recordbind',click('controlsMenu','st_record_bind')+['st_clientqa bindf8'],'controlsMenu',['bind F8'])
    step('setup',['ui_openmenu setup_menu'],'setup_menu',screenshot('setup'))
    for name in ['video2menubutton','soundmenubutton','gameoptionmenubutton','modsmenubutton','gamedefaultsmenubutton','video1menubutton']:
        step(name,click('setup_menu',name),'setup_menu',screenshot(name) if name=='soundmenubutton' else ())
    step('play',['ui_openmenu main']+click('main','play'),'multiplayermenu')
    step('browser',click('multiplayermenu','joinserver_button'),'joinserver',screenshot('browser'))
    step('password',click('joinserver','passwordText'),'password_popmenu',screenshot('password'))
    step('passwordedit',['set password ""']+click('password_popmenu','passwordEntry')+['st_clientqa type MenuQA123','st_clientqa enter'],'password_popmenu',['password'])
    step('passwordback',click('password_popmenu','doneText'),'joinserver')
    step('filter',click('joinserver','viewEmpty'),'joinserver',['ui_browserShowEmpty'])
    step('browserback',['st_clientqa escape'],'multiplayermenu')
    step('host',click('multiplayermenu','startserver_button'),'createserver',screenshot('host'))
    step('hosttime',['set timelimit ""']+click('createserver','normal')+['st_clientqa type 15','st_clientqa enter'],'createserver',['timelimit'])
    step('hostadvanced',click('createserver','advanced'),'advancedcreateserver',screenshot('advanced'))
    step('hostback',['st_clientqa escape'],'createserver')
    step('hostmap',click('createserver','maplist')+['st_clientqa down'],'createserver',['ui_currentNetMap'])
    step('solohub',['st_clientqa escape'],'multiplayermenu')
    step('solo',click('multiplayermenu','quickserver_button'),'quickgame',screenshot('solo'))
    step('solomap',click('quickgame','maplist')+['st_clientqa down'],'quickgame',['ui_currentMap'])
    step('solonext',click('quickgame','next_button'),'quickgame2',screenshot('solo-rules'))
    step('soloback',['st_clientqa escape'],'quickgame')
    step('solohubback',['st_clientqa escape'],'multiplayermenu')
    step('recordings',click('multiplayermenu','playdemo_button'),'demo',screenshot('recordings'))
    # A real previously captured test demo exercises the existing playback action.
    step('recordselect',click('demo','demolist'),'demo')
    lines+=click('demo','begin')+['echo DETAILS_INPUT_COMPLETE']
    cfg=native.MOD/'st-details-title.cfg';cfg.write_text('\n'.join(lines)+'\n')
    log=native.HOME/'SaberTrials/qconsole.log';offset=log.stat().st_size
    native.command('exec st-details-title.cfg')
    for _ in range(180):
        time.sleep(.25)
        with log.open('rb') as f:f.seek(offset);result=re.sub(r'\^[0-9]','',f.read().decode(errors='replace'))
        if 'DETAILS_INPUT_COMPLETE' in result and ('CL_InitCGame' in result or 'Playing demo' in result):break
    (EVIDENCE/f'native-{width}.log').write_text(result)
    assert 'DETAILS_INPUT_COMPLETE' in result,result[-2500:]
    for name,expected in expectations.items():
        segment=result.split('DETAILS_STEP_'+name+'\n',1)[-1].split('DETAILS_END_'+name,1)[0]
        assert 'MENU_QA focused='+expected+'\n' in segment,(name,expected,segment[-600:])
    for expected in ['Cvar ui_Name = "ThemeQA"','Bind F8 = "st_record"','Cvar password = "MenuQA123"','Cvar timelimit = "15"']:
        assert expected in result,expected
    for error in ['ERROR: ui/','Refusing to load non-power-2','QA item missing','Unknown command "st_clientqa"']:
        assert error not in result,error
    # Native demo messages are the proof of playback, not a menu transition alone.
    assert 'Playing demo' in result or 'CL_InitCGame' in result,result[-2500:]
    save_captures(width)
    stop_test()
    print(f'PASS: {len(expectations)} native navigation/input checkpoints and recording playback at {width}',flush=True)

def save_captures(width):
    for p in (native.HOME/'SaberTrials/screenshots').glob('details-'+str(width)+'-*.png'):
        shutil.copy2(p,EVIDENCE/p.name)
    for p in (native.HOME/'SaberTrials/screenshots').glob('detail-ingame*.png'):
        shutil.copy2(p,EVIDENCE/(str(width)+'-'+p.name))

def stop_test():
    pid=int((native.WORK/'test-pid.txt').read_text())
    # Stop only our recorded isolated game, never the user's running game.
    ps=f'$p = Get-CimInstance Win32_Process -Filter "ProcessId = {pid}"; if ($p -and $p.CommandLine.Contains("SaberTrials-menu-20261006")) {{ Stop-Process -Id {pid} }}'
    subprocess.run(['powershell','-NoProfile','-Command',ps],check=True,capture_output=True)

def release():
    # Called after start(installed=True). Asset loading can delay an RCON reply;
    # retry only this read-only query, not gameplay/menu mutations.
    for _ in range(10):
        reply=native.command('st_clientqa state')
        if 'Unknown command' in reply:break
        time.sleep(.2)
    assert 'Unknown command' in reply and 'MENU_QA' not in reply,reply
    native.command('ui_openmenu ingame_setup');native.command('screenshot_png final-ingame-setup')
    native.command('ui_openmenu ingame');assert '= "0"' in native.command('cl_paused')
    names=['playerMenu','controlsMenu','setup_menu','demo','joinserver','createserver','quickgame','playerMenu2','saberMenu']
    lines=['disconnect','wait 45','ui_openmenu main','wait 10']
    for name in names:lines+=['ui_openmenu '+name,'wait 30','screenshot_png final-'+name,'wait 4']
    lines+=['echo DETAILS_RELEASE_COMPLETE','wait 3','quit']
    (native.MOD/'st-details-release.cfg').write_text('\n'.join(lines)+'\n')
    log=native.HOME/'SaberTrials/qconsole.log';offset=log.stat().st_size
    native.command('exec st-details-release.cfg')
    for _ in range(100):
        time.sleep(.25)
        with log.open('rb') as f:f.seek(offset);result=f.read().decode(errors='replace')
        if 'DETAILS_RELEASE_COMPLETE' in result:break
    assert 'DETAILS_RELEASE_COMPLETE' in result,result[-1500:]
    assert not re.search(r'ERROR:.*ui/|Refusing to load non-power-2',result),result[-1500:]
    for name in names:assert 'Wrote screenshots/final-'+name+'.png' in result,name
    (EVIDENCE/'installed-release.log').write_text(result)
    for p in (native.HOME/'SaberTrials/screenshots').glob('final-*.png'):shutil.copy2(p,EVIDENCE/p.name)
    print('PASS installed release: nine screens rendered, in-game Setup, no QA hook or menu parser errors',flush=True)

if __name__=='__main__':
    action=sys.argv[1]
    if action=='structure':structure()
    elif action=='start':start(*(map(int,sys.argv[2:4])))
    elif action=='pause':capture_pause()
    elif action=='title':title(sys.argv[2])
    elif action=='stop':stop_test()
    elif action=='release':release()
