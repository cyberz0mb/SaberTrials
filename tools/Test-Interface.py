"""Native UI navigation, editable settings, screenshots and production smoke check.

Runs only in an isolated loopback install with a separate player configuration.
"""
from pathlib import Path
import importlib.util
import json
import re
import shutil
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parent.parent
WORK=Path(tempfile.gettempdir())/'SaberTrials-interface-20261011'
EVIDENCE=ROOT/'dist/verification/interface-20261011'
spec=importlib.util.spec_from_file_location('portrait',ROOT/'tools/Test-Portrait.py')
portrait=importlib.util.module_from_spec(spec);spec.loader.exec_module(portrait)
native=portrait.native
native.WORK=WORK;native.RUNTIME=WORK/'runtime';native.MOD=native.RUNTIME/'SaberTrials';native.HOME=native.RUNTIME/'home'
native.transport.WORK=WORK;native.transport.HOME=native.HOME
raw_command=native.command

def readback_command(text):
    reply=raw_command(text)
    # Rendering or asset loading may exceed the UDP read window. Retry only
    # read-only queries, never clicks, edits, recording or other actions.
    query=re.fullmatch(r'(?:cl_|cg_|st_ui|st_hud|st_portrait|st_streamer)[A-Za-z0-9_]+',text)
    if query:
        for _ in range(8):
            if 'Cvar '+text+' = ' in reply:break
            time.sleep(.15);reply=raw_command(text)
    return reply

native.command=readback_command
command=portrait.command

def shot(name):
    source=native.HOME/'SaberTrials/screenshots'/('interface-'+name+'.png')
    before=source.stat().st_mtime_ns if source.exists() else 0
    command('screenshot_png interface-'+name)
    for _ in range(100):
        if source.exists() and source.stat().st_mtime_ns!=before:
            time.sleep(.2);break
        time.sleep(.2)
    else: raise RuntimeError('Screenshot did not finish: '+name)
    shutil.copy2(source,EVIDENCE/source.name)

def start(mode,width,height):
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    stage=WORK/'test-stage';stage.mkdir(parents=True,exist_ok=True)
    # Test-Menu also stages the initial shell. Override it with the accepted
    # current menus before applying this pass, preserving every later refinement.
    shutil.copytree(ROOT/'ui',stage/'ui',dirs_exist_ok=True)
    if mode!='installed':shutil.copytree(ROOT/'dist/interface-staging',stage,dirs_exist_ok=True)
    native.start(mode,width,height,stage)
    command('set st_hudStyle 1; set st_hudScale 100; set st_hudOpacity 55; set st_portraitMode 1; set st_portraitSize 80; set st_portraitTarget 1; set cg_drawEnemyInfo 1; set cg_drawScores 1; set cg_thirdPerson 1; set st_streamerMode 0')
    command('ui_openmenu ingame')
    if mode=='qa':native.escape()
    command('team free')

def edit(menu,item,cvar,text,apply,stored):
    command(f'set {cvar} ""')
    native.click(menu,item);command('st_clientqa type '+text)
    # One click must commit the text field and activate Apply.
    native.click(menu,apply)
    reply=command(stored)
    assert f'= "{text}"' in reply,reply

def hub(parent,suffix):
    page='st_interface_'+suffix
    native.focused(page)
    native.click(page,'hud');native.focused('st_hud_'+suffix)
    hud='st_hud_'+suffix
    shot('hud-child-'+suffix)
    edit(hud,'size_value','st_uiHudScale','110','apply','st_hudScale')
    edit(hud,'opacity_value','st_uiHudOpacity','65','apply','st_hudOpacity')
    native.click(hud,'reset');assert '= "100"' in command('st_hudScale')
    native.click(hud,'back');native.focused(page)
    native.click(page,'portrait');native.focused('st_portrait_'+suffix)
    head='st_portrait_'+suffix
    shot('portrait-child-'+suffix)
    edit(head,'size_value','st_uiPortraitSize','92','apply','st_portraitSize')
    native.click(head,'mode');assert '= "2"' in command('st_portraitMode')
    native.click(head,'reset');assert '= "80"' in command('st_portraitSize')
    native.escape();native.focused(page)
    native.click(page,'back');native.focused(parent)

def qa(width,height):
    start('qa',width,height)
    command('ui_openmenu ingame');native.focused('ingame')
    native.command('st_clientqa move ingame photo')
    shot(f'pause-{width}x{height}')
    native.click('ingame','setup');native.focused('st_pause_setup')
    shot(f'pause-setup-{width}x{height}')
    native.click('st_pause_setup','interface');native.focused('st_interface_ingame')
    shot(f'ui-settings-{width}x{height}')
    hub('st_pause_setup','ingame')
    native.click('st_pause_setup','settings');native.focused('ingame_setup')
    native.click('ingame_setup','st_interface_settings');hub('ingame_setup','ingame')
    native.click('ingame_setup','gameoptionmenubutton')
    shot(f'game-options-{width}x{height}')
    native.escape();native.escape();native.escape();native.focused('none')
    if height==1024:native.pause_suite()
    print('PASS compact pause actions, both UI Settings routes, child Back/Esc and numeric Apply',flush=True)
    title(width,height)

def title(width,height):
    steps=['disconnect','wait 45','ui_openmenu main','wait 10']
    def click(menu,item):
        steps.extend([f'st_clientqa move {menu} {item}','st_clientqa click','wait 4','st_clientqa state'])
    click('main','setup')
    steps.append(f'screenshot_png interface-title-setup-{width}x{height}')
    click('setup_menu','st_interface_settings')
    steps.append(f'screenshot_png interface-title-ui-settings-{width}x{height}')
    click('st_interface_main','hud')
    steps.append(f'screenshot_png interface-title-hud-{width}x{height}')
    click('st_hud_main','back')
    click('st_interface_main','portrait')
    steps.extend(['st_clientqa escape','wait 3','st_clientqa state'])
    click('st_interface_main','back')
    click('setup_menu','modsmenubutton')
    click('setup_menu','gamedefaultsmenubutton')
    steps.extend(['echo ST_INTERFACE_TITLE_COMPLETE','wait 8','quit'])
    (native.MOD/'st-interface-title.cfg').write_text('\n'.join(steps)+'\n')
    log=native.HOME/'SaberTrials/qconsole.log';offset=log.stat().st_size
    command('exec st-interface-title.cfg')
    for _ in range(160):
        time.sleep(.25)
        with log.open('rb') as f:f.seek(offset);result=re.sub(r'\^[0-9]','',f.read().decode(errors='replace'))
        if 'ST_INTERFACE_TITLE_COMPLETE' in result:break
    assert 'ST_INTERFACE_TITLE_COMPLETE' in result,result[-3000:]
    assert 'QA item missing' not in result and 'Unknown command' not in result,result[-5000:]
    for menu in ['setup_menu','st_interface_main','st_hud_main','st_portrait_main']:
        assert 'focused='+menu+'\n' in result,menu
    check_log(log)
    (EVIDENCE/f'title-{width}x{height}.log').write_text(result)
    for p in (native.HOME/'SaberTrials/screenshots').glob(f'interface-title-*-{width}x{height}.png'):
        shutil.copy2(p,EVIDENCE/p.name)
    time.sleep(1)
    print('PASS main Setup category, HUD/portrait children, Back/Esc, Mods/Defaults; no menu errors',flush=True)

def check_log(log):
    result=log.read_text(errors='replace')
    for error in ['ERROR: ui/', 'Refusing to load non-power-2', 'QA item missing', 'could not find menu']:
        assert error not in result,error

def production(mode,width,height):
    start(mode,width,height)
    time.sleep(4) # Let spawn effects and join text settle before visual evidence.
    response=command('st_clientqa state')
    assert 'Unknown command' in response and 'MENU_QA' not in response,response
    command('ui_openmenu ingame');shot(f'{mode}-pause-{width}x{height}')
    assert '= "0"' in command('cl_paused')
    command('ui_openmenu st_interface_ingame');shot(f'{mode}-ui-settings-{width}x{height}')
    command('ui_openmenu st_hud_ingame');shot(f'{mode}-hud-{width}x{height}')
    check_log(native.HOME/'SaberTrials/qconsole.log')
    command('quit');time.sleep(.7)
    print('PASS production menu rendering, no QA commands and unpaused multiplayer',flush=True)

if __name__=='__main__':
    mode=sys.argv[1];width,height=map(int,sys.argv[2:4])
    if mode=='qa':qa(width,height)
    else:production(mode,width,height)
