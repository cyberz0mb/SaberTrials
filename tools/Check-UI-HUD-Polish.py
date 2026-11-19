"""Capture the updated menus and HUD in an isolated local game."""
import argparse
from datetime import datetime
from importlib import import_module
import os
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
b = import_module('Build-UI-HUD-Polish')


def run(mode):
    qa = mode in ('wide','tall')
    folder = b.OUT/f'{mode}-{datetime.now():%H%M%S}'
    mod = folder/'home/SaberTrials'
    screenshots = mod/'screenshots'
    screenshots.mkdir(parents=True)
    files = ({name:b.ROOT/name for name in b.files()} if mode=='installed' else b.files(qa))
    exe = b.build_tools.EXE
    if mode=='installed':
        installed = b.read(b.ROOT/'dist/ui-hud-polish-install.json')
        assert {name:b.sha(path) for name,path in files.items()} == installed['after']
    else:
        for name,path in files.items():
            target = folder/name if name==exe else mod/name
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target)
        for name in ('SDL2.dll','OpenAL32.dll','rd-vanilla_x86_64.dll','rd-rend2_x86_64.dll'):
            shutil.copyfile(b.ROOT/'client'/name,folder/'client'/name)
    print(folder,flush=True)
    lines = ['set name "Menu Review"','set model kyle/default','set saber1 single_1','set saber2 none','wait 80']
    shots = []

    def shot(name):
        shots.append(name)
        lines.extend(['wait 12','screenshot_png '+name,'wait 8'])

    if qa:
        for menu,label in [('createserver','host'),('advancedcreateserver','server-rules'),
                           ('quickbots','roster'),('st_stances_main','stances'),('demo','recordings'),
                           ('rulesMenu','rules'),('playerMenu','profile')]:
            lines.extend(['ui_openmenu '+menu,'wait 12','st_legacyqa assertmenu '+menu])
            shot(label)
        lines.extend(['unbind F12','ui_openmenu controlsMenu','wait 12','st_controlsqa click 10',
                      'st_controlsqa text "Open / collapse"','wait 12','st_controlsqa asserthit 500 1'])
        shot('chat-binding')
        lines.extend(['st_controlsqa click 500','st_controlsqa key 152','wait 8',
                      'st_controlsqa assertstatus "Assignment staged"','st_controlsqa click 1302',
                      'st_controlsqa assertbind 152 st_togglechat'])
    lines.extend(['set sv_hostname "Local Review"','set sv_location "Miami, US"','set sv_fps 40',
                  'set sv_maxRate 25000','set sv_pure 0','set g_gametype 0','set timelimit 0',
                  'set fraglimit 0','set g_doWarmup 0','set st_mvpPrototype 0',
                  'set cg_chatBox 15000','set st_portraitMode 0',
                  'devmap mp/ffa3','wait 365','team free','wait 65','addbot "Kyle Katarn" 1',
                  'addbot "Tavion" 1','addbot "Alora" 1','wait 65'])
    lines.extend(['ui_openmenu ingame_about','wait 15'])
    if qa:
        lines.append('st_legacyqa assertpaint ingame_about')
    shot('about')
    if qa:
        lines.extend(['st_legacyqa click back','wait 10','ui_openmenu ingame_callvote',
                      'wait 15','st_legacyqa click kickbutton','wait 10'])
        shot('kick-vote')
        lines.extend(['ui_openmenu ingame_setup','wait 15','st_setupqa click 2002','wait 8',
                      'st_setupqa scroll 177','wait 10'])
        shot('chat-settings')
        lines.extend(['st_setupqa set st_chatSize 2','st_setupqa set st_chatOpacity 78',
                      'st_setupqa click 2902','wait 12','st_setupqa assertvar st_chatSize 2',
                      'st_setupqa assertvar st_chatOpacity 78','ui_openmenu st_qa_no_menu',
                      'st_inspectqa key 27 1','wait 25'])
    else:
        lines.extend(['togglemenu','wait 12'])

    lines.extend(['set cg_thirdPerson 1','weapon 1','wait 75','say First chat message',
                  'say A longer chat message to check that it wraps inside the panel and keeps its color as it moves to the next line.', 'wait 10'])
    shot('single-chat')
    lines.extend(['st_togglechat','wait 10'])
    shot('chat-collapsed')
    lines.extend(['set st_chatSize 0','set st_chatOpacity 28','st_togglechat','wait 10'])
    shot('small-chat')
    lines.extend(['st_togglechat','set saber1 dual_1','set saber2 none','wait 70'])
    shot('staff')
    lines.extend(['set saber1 single_1','set saber2 single_2','wait 70'])
    shot('dual')
    lines.extend(['set saber2 none','wait 70','kill','wait 30','+scores','wait 32'])
    shot('ffa-scoreboard')
    lines.extend(['-scores','kick Tavion','kick Alora','wait 10','set timelimit 1',
                  'set timescale 12','wait 590','set timescale 1','wait 25'])
    shot('ffa-results')
    lines.extend(['echo ST_UI_HUD_COMPLETE','wait 15','quit'])
    (mod/'review.cfg').write_text('\n'.join(lines)+'\n')
    width,height = (1280,1024) if mode=='tall' else (1600,900)
    opts = dict(fs_basepath=b.ROOT.parent,fs_homepath=folder/'home',fs_game='SaberTrials',
                com_unpackLibraries=0,logfile=2,net_ip='127.0.0.1',net_port=29191 if mode=='tall' else 29190,
                r_fullscreen=0,r_mode=-1,r_customwidth=width,r_customheight=height,
                cl_renderer='rd-rend2' if mode in ('production','installed') else 'rd-vanilla',
                com_maxfps=60,s_initsound=0,com_introplayed=1)
    command = [str(files[exe] if mode=='installed' else folder/exe),'+safe']
    for name,value in opts.items():
        command.extend(['+set',name,str(value)])
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    proc = subprocess.Popen(command+['+exec','review.cfg'],cwd=b.ROOT.parent,startupinfo=startup,
                            env={**os.environ,'LOCALAPPDATA':str(folder/'local-app-data')},
                            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        assert proc.wait(timeout=120)==0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    log = (mod/'qconsole.log').read_text(errors='replace')
    errors = [line for line in log.splitlines() if any(word in line for word in
              ('ST_LEGACY_FAIL','ST_SETUP_FAIL','ST_CONTROLS_FAIL','Unknown command "st_togglechat"'))]
    assert 'ST_UI_HUD_COMPLETE' in log and not errors, errors or log[-1800:]
    assert all((screenshots/f'{name}.png').stat().st_size>10000 for name in shots)
    assert 'First chat message' in log
    assert 'Timelimit hit' in log or 'Time limit hit' in log, log[-1800:]
    b.write(folder/'result.json',dict(source=b.sha(b.RECEIPT), mode=mode, qa=qa,
                                     files={name:b.sha(path) for name,path in files.items()}, screenshots=shots))
    print(f'Passed {folder.name}, {len(shots)} screenshots')


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('wide','tall','production','installed'))
    run(parser.parse_args().mode)
