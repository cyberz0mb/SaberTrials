"""Exercise native menu events using an isolated loopback game and QA-only UI."""
from pathlib import Path
import importlib.util
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parent.parent
WORK=Path(tempfile.gettempdir())/'SaberTrials-menu-20261006'
RUNTIME=WORK/'runtime';MOD=RUNTIME/'SaberTrials';HOME=RUNTIME/'home'
spec=importlib.util.spec_from_file_location('combat_test',ROOT/'tools/Test-Combat.py')
transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
transport.WORK=WORK;transport.HOME=HOME;transport.PORT=27975
command=transport.command

def start(mode='qa',width=1280,height=720,stage=None):
    pidfile=WORK/'test-pid.txt'
    if pidfile.exists():
        pid=pidfile.read_text()
        active=subprocess.run(['tasklist','/FI',f'PID eq {pid}','/FO','CSV'],capture_output=True,text=True)
        if f'"{pid}"' in active.stdout: raise RuntimeError('Previous isolated test is still running')
    MOD.mkdir(parents=True,exist_ok=True);(RUNTIME/'base').mkdir(exist_ok=True)
    for asset in (ROOT.parent/'base').glob('assets*.pk3'):
        dest=RUNTIME/'base'/asset.name
        if not dest.exists(): os.link(asset,dest)
    for name in ['SDL2.dll','OpenAL32.dll','rd-vanilla_x86_64.dll']:
        shutil.copy2(ROOT.parent/name,RUNTIME/name)
    for name in ['jampgamex86_64.dll','cgamex86_64.dll']:shutil.copy2(ROOT/name,MOD/name)
    ui=ROOT/'uix86_64.dll' if mode=='installed' else WORK/('build-qa' if mode=='qa' else 'build')/'Release/uix86_64.dll'
    shutil.copy2(ui,MOD/'uix86_64.dll')
    for directory in ['ui','shaders','server']:
        shutil.copytree(ROOT/directory,MOD/directory,dirs_exist_ok=True,ignore=shutil.ignore_patterns('private'))
    if mode!='installed':shutil.copytree(ROOT/'dist/menu-staging',MOD,dirs_exist_ok=True)
    for directory in ['gfx','menu']:
        if (ROOT/directory).exists():shutil.copytree(ROOT/directory,MOD/directory,dirs_exist_ok=True)
    if stage:shutil.copytree(stage,MOD,dirs_exist_ok=True)
    secret=secrets.token_hex(16);(WORK/'test-secret.txt').write_text(secret)
    (MOD/'st-menu-test.cfg').write_text(f'''set rconPassword {secret}
set sv_pure 0
set sv_maxclients 4
set sv_maxOOBRate 0
set sv_maxOOBRateIP 0
set g_gametype 0
set g_doWarmup 0
set fraglimit 0
set timelimit 0
set bot_minplayers 0
set name MenuTest
set model kyle/default
set cl_allowDownload 0
set con_notifytime 0
devmap mp/ffa3
''')
    args=[str(ROOT/'client/SaberTrials.x86_64.exe'),'+set','fs_basepath',str(RUNTIME),'+set','fs_homepath',str(HOME),
          '+set','fs_game','SaberTrials','+set','net_ip','127.0.0.1','+set','net_port','27975',
          '+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth',str(width),'+set','r_customheight',str(height),
          '+set','cl_renderer','rd-vanilla','+set','s_initsound','0','+set','com_maxfps','60','+set','logfile','2']
    for i in range(1,6): args+=['+set',f'sv_master{i}','']
    args+=['+exec','st-menu-test.cfg']
    si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    p=subprocess.Popen(args,cwd=RUNTIME,startupinfo=si,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    pidfile.write_text(str(p.pid))
    for _ in range(70):
        if 'Saber Trials gametype' in command('st_status'):break
        if p.poll() is not None: raise RuntimeError('Test game exited; inspect isolated log')
        time.sleep(.2)
    else: raise RuntimeError('Startup timed out')
    for _ in range(70):
        reply=command('st_clientqa state' if mode=='qa' else 'st_record')
        if ('MENU_QA' if mode=='qa' else 'recording to demos/') in reply:
            if mode!='qa':command('st_record')
            break
        time.sleep(.2)
    else:raise RuntimeError('Client did not finish loading')
    print('Started isolated menu test',p.pid,flush=True)

def click(menu,item):
    reply=command(f'st_clientqa move {menu} {item}')
    assert 'QA item missing' not in reply and 'Unknown command' not in reply,reply
    command('st_clientqa click')
def focused(name):
    # A legacy model picker can stall rendering while its assets load. Poll only
    # the read-only state query; never replay a click or a destructive action.
    for _ in range(10):
        reply=command('st_clientqa state')
        if 'MENU_QA focused=' in reply:break
        time.sleep(.2)
    assert 'focused='+name+'\n' in reply,reply
def escape():command('st_clientqa escape')

def pause_suite():
    command('ui_openmenu ingame');focused('ingame')
    assert '= "0"' in command('cl_paused')
    command('screenshot_png ST-pause')
    for root_item,dest in [('about','st_pause_about'),('join','ingame_join'),('player','ingame_player'),
                           ('vote','st_pause_vote'),('setup','st_pause_setup'),('photo','st_pause_photo'),
                           ('respawn','st_pause_respawn'),('exit','st_pause_exit')]:
        click('ingame',root_item);focused(dest);escape();focused('ingame')
    click('ingame','streamer');focused('ingame_setup');command('screenshot_png ST-streamer');escape();focused('ingame')
    click('ingame','vote');click('st_pause_vote','call');focused('ingame_callvote');escape();focused('st_pause_vote');escape()
    click('ingame','setup');click('st_pause_setup','input');focused('ingame_setup')
    for item,cvar,value in [('st_yaw_value','st_uiYawSpeed','175.25'),('st_accel_value','st_uiMouseAccel','0.5')]:
        command(f'set {cvar} ""');click('ingame_setup',item);command('st_clientqa type '+value)
        command('st_clientqa enter')
    click('ingame_setup','st_input_apply')
    assert '= "175.25"' in command('cl_yawspeed')
    assert '= "0.5"' in command('cl_mouseAccel')
    command('screenshot_png ST-input');escape();escape()
    click('ingame','setup');click('st_pause_setup','controls');focused('ingame_controls')
    click('ingame_controls','othercontrolbutton');click('ingame_controls','st_record_bind');command('st_clientqa bindf8')
    assert 'st_record' in command('bind F8');escape();escape()
    # Destructive actions require a separate confirmation and default to Back.
    click('ingame','exit');click('st_pause_exit','disconnect');focused('st_pause_disconnect');escape();escape();focused('ingame')
    command('st_clientqa tab');assert 'MENU_QA item=' in command('st_clientqa state')
    escape();focused('none')
    assert 'recording to demos/' in command('st_record');time.sleep(.2)
    assert 'Saved recording:' in command('st_record')
    print('PASS pause mouse/keyboard/back, setup/input/streamer/vote destinations, confirmations, recording binding and recording',flush=True)

def title_suite():
    # RCON stops on disconnect; the native command buffer continues the test.
    lines=['disconnect','wait 30','ui_openmenu main','wait 10','st_clientqa state','screenshot_png ST-main','st_uiMenuMovie']
    def click_cmd(menu,item):return [f'st_clientqa move {menu} {item}','st_clientqa click','wait 3','st_clientqa state']
    lines+=click_cmd('main','play')+click_cmd('multiplayermenu','ranked')
    lines+=['screenshot_png ST-ranked','st_clientqa escape','st_clientqa state','st_clientqa escape','st_clientqa state']
    lines+=click_cmd('mainMenu','motion')+['st_menuMotion','st_uiMenuMovie']
    lines+=click_cmd('mainMenu','controls')+click_cmd('controlsMenu','othercontrolbutton')+click_cmd('controlsMenu','st_record_bind')
    lines+=['st_clientqa bindf8','bind F8','st_clientqa escape','wait 3','st_clientqa state']
    lines+=['ui_openmenu main','st_clientqa escape','st_clientqa state','st_clientqa escape','st_clientqa state']
    for key in ['profile','setup']:
        lines+=['ui_openmenu main']+click_cmd('main',key)+['screenshot_png ST-main-'+key]
    for key in ['joinserver_button','startserver_button','quickserver_button','playdemo_button','rules_button']:
        lines+=['ui_openmenu main']+click_cmd('main','play')+click_cmd('multiplayermenu',key)
    lines+=['echo ST_MENU_TITLE_COMPLETE','wait 3','quit']
    (MOD/'st-title-test.cfg').write_text('\n'.join(lines)+'\n')
    log=HOME/'SaberTrials/qconsole.log';offset=log.stat().st_size
    command('exec st-title-test.cfg')
    for _ in range(80):
        time.sleep(.25)
        with log.open('rb') as f:f.seek(offset);result=re.sub(r'\^[0-9]','',f.read().decode(errors='replace'))
        if 'ST_MENU_TITLE_COMPLETE' in result:break
    assert 'ST_MENU_TITLE_COMPLETE' in result,result[-3000:]
    assert 'QA item missing' not in result and 'Unknown command' not in result,result[-6000:]
    for name in ['main','mainMenu','multiplayermenu','st_main_ranked','controlsMenu','st_main_exit',
                 'playerMenu','setup_menu','joinserver','createserver','quickgame','demo','rulesMenu']:
        assert 'focused='+name+'\n' in result,name
    assert 'Bind F8 = "st_record"' in result,result[-3000:]
    assert 'Cvar st_uiMenuMovie = "0"' in result,result[-3000:]
    for error in ['ERROR: ui/', 'Refusing to load non-power-2', 'QA item missing']:
        assert error not in result,result[-5000:]
    (ROOT/'dist/verification/menu-20261006/title-test.log').write_text(result)
    print('PASS main/Play/Ranked/Controls/Exit navigation and absent-footage fallback',flush=True)

def production_suite():
    reply=command('st_clientqa state')
    assert 'Unknown command' in reply and 'MENU_QA' not in reply,reply
    assert 'Saber Trials gametype' in command('st_status')
    command('ui_openmenu ingame');command('screenshot_png ST-production-pause')
    assert '= "0"' in command('cl_paused')
    script=['disconnect','wait 30','ui_openmenu main','wait 10','screenshot_png ST-production-main',
            'st_uiMenuMovie','echo ST_MENU_PRODUCTION_COMPLETE','wait 3','quit']
    (MOD/'st-production-menu.cfg').write_text('\n'.join(script)+'\n')
    log=HOME/'SaberTrials/qconsole.log';offset=log.stat().st_size
    command('exec st-production-menu.cfg')
    for _ in range(80):
        time.sleep(.25)
        with log.open('rb') as f:f.seek(offset);result=re.sub(r'\^[0-9]','',f.read().decode(errors='replace'))
        if 'ST_MENU_PRODUCTION_COMPLETE' in result:break
    assert 'ST_MENU_PRODUCTION_COMPLETE' in result,result[-3000:]
    assert 'Cvar st_uiMenuMovie = "0"' in result,result[-3000:]
    for error in ['ERROR: ui/', 'Refusing to load non-power-2']:
        assert error not in result,result[-5000:]
    print('PASS installed production UI: real game load, unpaused menu, static title fallback, no test commands or menu errors',flush=True)

if __name__=='__main__':
    action=sys.argv[1]
    if action=='start':start(sys.argv[2] if len(sys.argv)>2 else 'qa',*(map(int,sys.argv[3:5])))
    elif action=='command':print(command(sys.argv[2]))
    elif action=='pause':pause_suite()
    elif action=='title':title_suite()
    elif action=='production':production_suite()
    else:raise SystemExit('Use start [qa|production|installed] [width height], command TEXT, pause, title')
