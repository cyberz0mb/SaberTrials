"""Reuse native UI navigation checks in an isolated install of the soft skin."""
from pathlib import Path
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parent.parent
WORK=Path(tempfile.gettempdir())/'SaberTrials-menu-soft-20261011'
EVIDENCE=ROOT/'dist/verification/menu-soft-20261011'
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
skin=module('soft_skin','Soften-Menus.py')
checks=module('interface_checks','Test-Interface.py')
details=module('details_checks','Test-Menu-Details.py')
remainder=module('remainder_checks','Test-Menu-Remainder.py')
native=checks.native
native.WORK=WORK;native.RUNTIME=WORK/'runtime';native.MOD=native.RUNTIME/'SaberTrials';native.HOME=native.RUNTIME/'home'
native.transport.WORK=WORK;native.transport.HOME=native.HOME
checks.EVIDENCE=EVIDENCE;details.EVIDENCE=EVIDENCE;remainder.EVIDENCE=EVIDENCE
details.native=native;remainder.native=native
command=checks.command

def structure():
    counts={}
    for source in sorted(skin.SOURCE.glob('*.menu')):
        before=skin.theme.read_source(source)
        after=skin.theme.read_source(skin.OUT/'ui/jamp'/source.name)
        assert details.semantics(before)==details.semantics(after),source.name
        old=[skin.rect(before[a:b]) for a,b in skin.theme.blocks(before,'itemDef')]
        new=[skin.rect(after[a:b]) for a,b in skin.theme.blocks(after,'itemDef')]
        assert old==new,source.name
        counts[source.name]=len(old)
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    (EVIDENCE/'structure.json').write_text(json.dumps({'menus':len(counts),'items':sum(counts.values()),
        'preserved_semantics_and_hitboxes':True,'item_counts':counts},indent=2)+'\n')
    print('PASS preserved menu behavior and geometry:',len(counts),'files,',sum(counts.values()),'items',flush=True)

def start(mode,width,height):
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    qa=WORK/'build-qa/Release/uix86_64.dll';qa.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(WORK.parent/'SaberTrials-interface-20261011/build-qa/Release/uix86_64.dll',qa)
    stage=WORK/'test-stage';stage.mkdir(parents=True,exist_ok=True)
    shutil.copytree(ROOT/'ui',stage/'ui',dirs_exist_ok=True)
    if mode!='installed':shutil.copytree(skin.OUT,stage,dirs_exist_ok=True)
    # Production DLL plus candidate data: native.start calls that mode installed.
    native.start('installed' if mode=='production' else mode,width,height,stage)
    command('set st_hudStyle 1; set st_portraitMode 1; set cg_thirdPerson 1; set st_streamerMode 0; team free')

def stop():
    pid=int((WORK/'test-pid.txt').read_text())
    ps=f'$p = Get-CimInstance Win32_Process -Filter "ProcessId = {pid}"; if ($p -and $p.CommandLine.Contains("{WORK.name}")) {{ Stop-Process -Id {pid} }}'
    subprocess.run(['powershell','-NoProfile','-Command',ps],check=True,capture_output=True)

def shot(label):
    checks.shot('soft-'+label)

def gallery(label,names):
    for name in names:
        command('ui_openmenu '+name);time.sleep(.15);shot(label+'-'+name)

def detail():
    start('qa',1280,1024)
    native.pause_suite()
    command('ui_openmenu ingame');native.click('ingame','setup');native.click('st_pause_setup','interface')
    checks.hub('st_pause_setup','ingame')
    remainder.pause('soft-1024')
    gallery('1024',['ingame','ingame_controls','ingame_player','ingame_setup','st_pause_setup','st_pause_exit'])
    details.stop_test=stop
    details.title(1280)
    checks.check_log(native.HOME/'SaberTrials/qconsole.log')

def wide():
    start('qa',1280,720)
    gallery('720',['ingame','st_pause_about'])
    # Front-end menus load after disconnect. Extend the existing native rules
    # script there, rather than trying to open title-only definitions in-game.
    lines=[]
    names=['main','multiplayermenu','playerMenu','controlsMenu','setup_menu','demo','joinserver',
        'createserver','quickgame','quickgame2','advancedcreateserver','password_popmenu','st_main_ranked']
    for name in names:
        parents={'advancedcreateserver':('createserver','advanced'),'password_popmenu':('joinserver','passwordText')}
        if name in parents:
            parent,item=parents[name]
            lines+=['ui_openmenu '+parent,'wait 5',f'st_clientqa move {parent} {item}','st_clientqa click']
        else:lines+=['ui_openmenu '+name]
        lines+=['wait 20','st_clientqa state','screenshot_png remainder-soft-720-'+name]
    lines+=['ui_openmenu setup_menu','wait 5','st_clientqa move setup_menu st_interface_settings',
        'st_clientqa click','wait 10','st_clientqa state','screenshot_png remainder-soft-720-ui-settings',
        'st_clientqa move st_interface_main hud','st_clientqa click','wait 10','st_clientqa state',
        'screenshot_png remainder-soft-720-hud-child','st_clientqa escape','wait 5','st_clientqa state',
        'st_clientqa escape','wait 5','st_clientqa state','ui_openmenu main','wait 10']
    raw=native.command
    def run(text):
        if text=='exec st-remainder-title.cfg':
            p=native.MOD/'st-remainder-title.cfg';s=p.read_text()
            p.write_text(s.replace('ui_openmenu main\nwait 10\n','ui_openmenu main\nwait 10\n'+'\n'.join(lines)+'\n',1))
        return raw(text)
    native.command=run
    try:remainder.title('soft-720')
    finally:native.command=raw
    result=(EVIDENCE/'title-soft-720.log').read_text()
    for name in names+['st_interface_main','st_hud_main']:
        assert 'focused='+name+'\n' in result,name
    checks.check_log(native.HOME/'SaberTrials/qconsole.log')

def production(mode):
    start(mode,1280,1024 if mode=='installed' else 720)
    reply=command('st_clientqa state');assert 'Unknown command' in reply and 'MENU_QA' not in reply,reply
    assert '= "0"' in command('cl_paused')
    gallery(mode,['ingame','st_interface_ingame','st_hud_ingame','ingame_join','ingame_about','ingame_addbot'])
    lines=['disconnect','wait 45']
    for name in ['main','playerMenu','controlsMenu','setup_menu','joinserver']:
        lines+=['ui_openmenu '+name,'wait 20','screenshot_png soft-'+mode+'-'+name]
    lines+=['echo SOFT_PRODUCTION_COMPLETE','wait 5','quit']
    (native.MOD/'st-soft-production.cfg').write_text('\n'.join(lines)+'\n')
    log=native.HOME/'SaberTrials/qconsole.log';offset=log.stat().st_size
    command('exec st-soft-production.cfg')
    for _ in range(100):
        time.sleep(.25)
        with log.open('rb') as f:f.seek(offset);result=f.read().decode(errors='replace')
        if 'SOFT_PRODUCTION_COMPLETE' in result:break
    assert 'SOFT_PRODUCTION_COMPLETE' in result,result[-2000:]
    checks.check_log(log)
    (EVIDENCE/(mode+'.log')).write_text(result)
    for p in (native.HOME/'SaberTrials/screenshots').glob('soft-'+mode+'-*.png'):shutil.copy2(p,EVIDENCE/p.name)
    print('PASS',mode,'native rendering, no QA hook, multiplayer unpaused',flush=True)

if __name__=='__main__':
    action=sys.argv[1]
    if action=='structure':structure()
    elif action=='detail':detail()
    elif action=='wide':wide()
    elif action=='stop':stop()
    else:production(action)
