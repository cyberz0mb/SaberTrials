"""Native HUD/menu verification in a separate loopback-only profile."""
from pathlib import Path
import importlib.util, json, re, shutil, sys, tempfile, time
ROOT=Path(__file__).resolve().parent.parent
WORK=Path(tempfile.gettempdir())/'SaberTrials-hud-20261006'
EVIDENCE=ROOT/'dist/verification/hud-20261006'
spec=importlib.util.spec_from_file_location('portrait',ROOT/'tools/Test-Portrait.py')
portrait=importlib.util.module_from_spec(spec);spec.loader.exec_module(portrait)
native=portrait.native
native.WORK=WORK;native.RUNTIME=WORK/'runtime';native.MOD=native.RUNTIME/'SaberTrials';native.HOME=native.RUNTIME/'home'
native.transport.WORK=WORK;native.transport.HOME=native.HOME
command=portrait.command

def start(mode='qa',width=1280,height=720):
    WORK.mkdir(parents=True,exist_ok=True)
    (WORK/'test-resolution.json').write_text(json.dumps([width,height]))
    stage=WORK/'test-stage';stage.mkdir(exist_ok=True)
    for src,dst in [(ROOT.parent/'base',native.RUNTIME/'base'),(ROOT,native.MOD)]:
        dst.mkdir(parents=True,exist_ok=True)
        for p in src.glob('*.pk3'):
            target=dst/p.name
            if not target.exists(): target.hardlink_to(p)
    shutil.copytree(ROOT/'dist/hud-staging',stage,dirs_exist_ok=True)
    shutil.copytree(ROOT/'development-source/menu/portrait-profiles',stage,dirs_exist_ok=True)
    source=ROOT if mode=='installed' else WORK/('build-qa' if mode=='qa' else 'build')/'Release'
    shutil.copy2(source/'cgamex86_64.dll',stage/'cgamex86_64.dll')
    native.start(mode,width,height,stage)
    command('set cg_drawEnemyInfo 1; set st_portraitMode 1; set st_portraitTarget 0; set st_portraitSize 80')
    command('set st_hudStyle 1; set st_hudScale 100; set st_hudOpacity 55; set st_hudPulse 1; set cg_drawScores 1; set cg_drawStatus 1')
    command('set cg_drawFPS 0; set cg_drawTimer 0; set cg_thirdPerson 1; set st_streamerMode 0; set cg_draw2D 1')
    if mode=='qa':command('ui_openmenu ingame');native.escape()
    command('team free');time.sleep(.4)

def shot(name):
    path=native.HOME/'SaberTrials/screenshots'/('hud-'+name+'.png')
    stamp=path.stat().st_mtime_ns if path.exists() else 0
    command('screenshot_png hud-'+name)
    for _ in range(120):
        if path.exists() and path.stat().st_mtime_ns!=stamp:time.sleep(.2);break
        time.sleep(.2)
    assert path.exists() and path.stat().st_mtime_ns!=stamp,'Screenshot did not finish'
    EVIDENCE.mkdir(parents=True,exist_ok=True);shutil.copy2(path,EVIDENCE/path.name)

def menu():
    command('ui_openmenu ingame_setup');native.focused('ingame_setup')
    native.click('ingame_setup','gameoptionmenubutton')
    shot('game-options')
    native.click('ingame_setup','st_hud_settings');native.focused('st_hud_ingame')
    native.click('st_hud_ingame','reset');shot('options')
    for item,cv,first in [('style','st_hudStyle',0),('score','cg_drawScores',0),('pulse','st_hudPulse',0)]:
        native.click('st_hud_ingame',item);assert '= "0"' in command(cv)
        native.click('st_hud_ingame',item);assert '= "1"' in command(cv)
    native.click('st_hud_ingame','size');native.click('st_hud_ingame','opacity')
    for item,cv,value in [('size_value','st_uiHudScale','103.5'),('opacity_value','st_uiHudOpacity','35.5')]:
        command('set '+cv+' ""');native.click('st_hud_ingame',item)
        command('st_clientqa type '+value)
    native.click('st_hud_ingame','apply')
    assert '= "103.5"' in command('st_hudScale')
    assert '= "35.5"' in command('st_hudOpacity')
    command('set st_uiHudScale ""');native.click('st_hud_ingame','size_value');command('st_clientqa type 999')
    native.click('st_hud_ingame','apply');assert '= "103.5"' in command('st_hudScale')
    assert 'Enter size' in command('st_uiHudStatus')
    native.click('st_hud_ingame','reset');assert '= "100"' in command('st_hudScale')
    native.click('st_hud_ingame','back');native.focused('ingame_setup')
    native.click('ingame_setup','st_portrait_settings');native.focused('st_portrait_ingame')
    native.click('st_portrait_ingame','reset');native.click('st_portrait_ingame','back')
    native.escape()
    print('PASS HUD menu switches, sliders, decimals, invalid input, reset, Back and portrait settings',flush=True)

def behavior():
    lines=[]
    def cmd(s):
        r=command(s);lines.append(s+'\n'+r);return r
    assert 'cases=11 failures=0' in cmd('st_hudqa math')
    assert 'cases=14 failures=0' in cmd('st_portraitqa selection')
    cmd('st_shields 0; map_restart 0');time.sleep(3)
    cmd('st_hudStyle 1; st_hudScale 100; st_hudOpacity 55; st_combatMode 0; st_shields 0; give health 100; give armor 25; give force 100')
    time.sleep(.5);r=cmd('st_hudqa');assert 'health=100 armor=25' in r,r
    dimensions=json.loads((WORK/'test-resolution.json').read_text())
    shot('gameplay-'+'x'.join(map(str,dimensions)))
    cmd('give health 23; give armor 0');time.sleep(.3)
    assert 'health=23 armor=0' in cmd('st_hudqa');shot('low-health')
    cmd('give health 100; give armor 25; st_weaponsActive 1; give weapons; give ammo 87; wait 20; weapon 3');time.sleep(1)
    r=cmd('st_hudqa');assert 'weapon=5 ammo=87' in r,r;shot('blaster')
    cmd('weapon 1');time.sleep(.7)
    for scale in [75,125]:
        cmd('st_hudScale '+str(scale));shot('size-'+str(scale))
    cmd('st_hudScale 100; st_hudOpacity 0');shot('transparent')
    cmd('st_hudOpacity 55; st_hudStyle 0');shot('original')
    cmd('st_hudStyle 1; cg_drawScores 0');shot('score-hidden')
    cmd('cg_drawScores 1; st_streamerMode 1; st_streamerCleanHud 1');shot('streamer-clean')
    cmd('st_streamerMode 0; cg_draw2D 0');shot('all-hidden')
    cmd('cg_draw2D 1');assert 'recording to demos/' in cmd('st_record')
    assert 'Saved recording:' in cmd('st_record')
    cmd('team spectator');time.sleep(.5);shot('spectator')
    cmd('team free');time.sleep(.5)
    EVIDENCE.mkdir(parents=True,exist_ok=True);(EVIDENCE/'behavior.log').write_text('\n'.join(lines))
    print('PASS live vitals/ammo, bounds, original, visibility toggles, recording, spectator and portrait regression',flush=True)

def title():
    lines=['disconnect','wait 45','ui_openmenu setup_menu','wait 10',
        'st_clientqa move setup_menu gameoptionmenubutton','st_clientqa click','wait 3',
        'st_clientqa move setup_menu st_hud_settings','st_clientqa click','wait 3',
        'st_clientqa state','screenshot_png hud-title-options',
        'st_clientqa move st_hud_main style','st_clientqa click','st_hudStyle',
        'st_clientqa move st_hud_main reset','st_clientqa click',
        'st_clientqa move st_hud_main back','st_clientqa click','st_clientqa state',
        'echo HUD_TITLE_COMPLETE','wait 3','quit']
    (native.MOD/'st-hud-title.cfg').write_text('\n'.join(lines)+'\n')
    log=native.HOME/'SaberTrials/qconsole.log';offset=log.stat().st_size
    command('exec st-hud-title.cfg')
    for _ in range(120):
        time.sleep(.25);result=log.read_bytes()[offset:].decode(errors='replace')
        if 'HUD_TITLE_COMPLETE' in result:break
    assert 'focused=st_hud_main' in result and 'focused=setup_menu' in result,result[-3000:]
    assert 'QA item missing' not in result and 'ERROR: ui/' not in result
    (EVIDENCE/'title.log').write_text(result)
    shutil.copy2(native.HOME/'SaberTrials/screenshots/hud-title-options.png',EVIDENCE/'hud-title-options.png')
    print('PASS title settings and navigation',flush=True)

def modes():
    lines=[]
    def cmd(s):
        r=command(s);lines.append(s+'\n'+r);return r
    cmd('g_gametype 6; map_restart 0');time.sleep(3)
    cmd('team red; cg_drawRadar 0; kick allbots; addbot Alora 1 blue');time.sleep(6)
    cmd('ui_openmenu ingame; st_clientqa escape')
    r=cmd('st_hudqa');assert 'gt=6' in r and 'team=1' in r,r
    shot('team-1280x1024')
    cmd('team spectator; wait 15; follow 1');time.sleep(1)
    r=cmd('st_hudqa');assert 'follow=1' in r,r
    shot('follow-player')
    cmd('g_gametype 3; fraglimit 5; devmap mp/duel3')
    for _ in range(60):
        time.sleep(.3)
        r=cmd('st_hudqa')
        if 'gt=3' in r:break
    cmd('ui_openmenu ingame; st_clientqa escape')
    r=cmd('st_hudqa');assert 'gt=3' in r,r
    shot('duel-1280x1024')
    log=(native.HOME/'SaberTrials/qconsole.log').read_text(errors='replace')
    for error in ['ERROR: ui/','Refusing to load non-power-2','Failed userinfo validation']:
        assert error not in log,error
    (EVIDENCE/'modes.log').write_text('\n'.join(lines))
    print('PASS TFFA, spectator follow and real Duel 3 level transition',flush=True)

def production():
    results=[]
    for name in ['st_hudqa','st_portraitqa','st_clientqa state']:
        result=command(name);assert 'Unknown command' in result,result
        results.append(result)
    command('ui_openmenu st_hud_ingame');shot('production-options-1280x720')
    log=native.HOME/'SaberTrials/qconsole.log';offset=log.stat().st_size
    command('devmap mp/duel3')
    for _ in range(100):
        time.sleep(.25)
        if 'CL_InitCGame:' in log.read_bytes()[offset:].decode(errors='replace'):break
    else:raise AssertionError('Production map did not load')
    time.sleep(1)
    command('model jawa/default');time.sleep(3)
    command('give health 100; give armor 25; cg_thirdPersonRange 100')
    time.sleep(1);shot('production-1280x720')
    assert 'recording to demos/' in command('st_record')
    assert 'Saved recording:' in command('st_record')
    content=log.read_text(errors='replace')
    for error in ['ERROR: ui/','Refusing to load non-power-2','Failed userinfo validation']:
        assert error not in content,error
    (EVIDENCE/'production.log').write_text('\n'.join(results)+'\n'+content)
    command('quit')
    print('PASS installed production: no QA hooks, settings, real level change, model/portrait and recording',flush=True)

if __name__=='__main__':
    action=sys.argv[1]
    if action=='start':start(sys.argv[2],*map(int,sys.argv[3:5]))
    elif action=='command':print(command(sys.argv[2]))
    elif action=='shot':shot(sys.argv[2])
    elif action in ['menu','behavior','title','modes','production']:globals()[action]()
    else:raise SystemExit('Unknown test action')
