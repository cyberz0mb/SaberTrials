"""Isolated portrait testing; never changes the player's profile or server."""
from pathlib import Path
import importlib.util, json, re, shutil, sys, tempfile, time
ROOT=Path(__file__).resolve().parent.parent
WORK=Path(tempfile.gettempdir())/'SaberTrials-portrait-20261006'
spec=importlib.util.spec_from_file_location('native',ROOT/'tools/Test-Menu.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
native.WORK=WORK;native.RUNTIME=WORK/'runtime';native.MOD=native.RUNTIME/'SaberTrials';native.HOME=native.RUNTIME/'home'
native.transport.WORK=WORK;native.transport.HOME=native.HOME
def command(text):
    # RCON invokes one command directly. Use the engine command buffer for
    # multi-command sequences; otherwise a semicolon can become a cvar value.
    if ';' in text:
        (native.MOD/'st-portrait-step.cfg').write_text(text.replace(';','\n')+'\n')
        return native.command('exec st-portrait-step.cfg')
    return native.command(text)
EVIDENCE=ROOT/'dist/verification/portrait-20261006'

def start(mode='qa',width=1280,height=720):
    for folder,dest in [(ROOT.parent/'base',native.RUNTIME/'base'),(ROOT,native.MOD)]:
        dest.mkdir(parents=True,exist_ok=True)
        for p in folder.glob('*.pk3'):
            q=dest/p.name
            if not q.exists():q.hardlink_to(p)
    stage=WORK/'test-stage';stage.mkdir(exist_ok=True)
    shutil.copytree(ROOT/'dist/portrait-staging',stage,dirs_exist_ok=True)
    source=ROOT if mode=='installed' else WORK/('build-qa' if mode=='qa' else 'build')/'Release'
    shutil.copy2(source/'cgamex86_64.dll',stage/'cgamex86_64.dll')
    native.start(mode,width,height,stage)
    command('set cg_drawEnemyInfo 1; set st_portraitMode 1; set st_portraitTarget 0; set st_portraitSize 80; set st_portraitDamage 1')
    command('set cg_drawFPS 0; set cg_drawTimer 0; set cg_thirdPerson 1; set st_streamerMode 0')
    if mode=='qa':
        command('ui_openmenu ingame');native.escape()
    command('team free')

def shot(name):
    p=native.HOME/'SaberTrials/screenshots'/('portrait-'+name+'.png')
    before=p.stat().st_mtime_ns if p.exists() else 0
    command('screenshot_png portrait-'+name)
    for _ in range(120):
        if p.exists() and p.stat().st_mtime_ns!=before:
            time.sleep(.2)
            break
        time.sleep(.2)
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    shutil.copy2(p,EVIDENCE/p.name)

def models():
    for model in ['kyle/default','alora/default','stormtrooper/default','jawa/default','luffy/default']:
        time.sleep(6) # Respect the engine's userinfo flood protection.
        command('model '+model);time.sleep(1.2)
        for _ in range(40):
            r=command('st_portraitqa')
            if 'ready=1' in r and 'model='+model.split('/')[0]+' ' in r:break
            time.sleep(.25)
        assert 'ready=1' in r and 'model='+model.split('/')[0]+' ' in r,r
        shot(model.split('/')[0])
        print(r.strip(),flush=True)
    command('model kyle/default')

def menu():
    command('ui_openmenu ingame_setup');native.focused('ingame_setup')
    native.click('ingame_setup','gameoptionmenubutton')
    native.click('ingame_setup','st_portrait_settings');native.focused('st_portrait_ingame')
    native.click('st_portrait_ingame','reset')
    shot('options')
    native.click('st_portrait_ingame','mode');assert '= "2"' in command('st_portraitMode')
    native.click('st_portrait_ingame','mode');assert '= "0"' in command('st_portraitMode')
    native.click('st_portrait_ingame','mode');assert '= "1"' in command('st_portraitMode')
    native.click('st_portrait_ingame','target');assert '= "1"' in command('st_portraitTarget')
    native.click('st_portrait_ingame','target');assert '= "2"' in command('st_portraitTarget')
    native.click('st_portrait_ingame','target');assert '= "0"' in command('st_portraitTarget')
    native.click('st_portrait_ingame','damage');assert '= "0"' in command('st_portraitDamage')
    command('set st_uiPortraitSize 48')
    native.click('st_portrait_ingame','size');native.click('st_portrait_ingame','apply')
    assert '= "48"' not in command('st_portraitSize')
    for value,valid in [('104',True),('999',False),('60.5',True)]:
        command('set st_uiPortraitSize ""');native.click('st_portrait_ingame','size_value')
        command('st_clientqa type '+value)
        native.click('st_portrait_ingame','apply')
        r=command('st_portraitSize')
        assert ('= "'+value+'"' in r)==valid,r
    native.click('st_portrait_ingame','reset');assert '= "80"' in command('st_portraitSize')
    native.click('st_portrait_ingame','back');native.focused('ingame_setup');native.escape()
    print('PASS portrait mode/target/damage toggles, numeric size, rejected out-of-range size, reset and back',flush=True)

def behavior():
    transcript=[]
    def cmd(s):
        r=command(s);transcript.append(s+'\n'+r);return r
    assert 'cases=14 failures=0' in cmd('st_portraitqa selection')
    cmd('model kyle/default; set st_portraitTarget 1; set st_portraitMode 1')
    time.sleep(1)
    first=cmd('st_portraitqa');time.sleep(.7);second=cmd('st_portraitqa')
    def yaw(r):return float(re.search(r'yaw=([-\d.]+)',r)[1])
    assert abs(yaw(first)-yaw(second))>.01
    cmd('st_portraitqa face');time.sleep(.1);r=cmd('st_portraitqa')
    frames=re.search(r'world=1/([\d.]+) portrait=1/([\d.]+)',r)
    assert frames and abs(float(frames[1])-float(frames[2]))<1,r
    cmd('set st_portraitMode 2');time.sleep(.3)
    r=cmd('st_portraitqa');assert 'yaw=0.000 pitch=0.000' in r
    shot('static-1280x1024')
    cmd('set st_portraitMode 0');time.sleep(.2)
    assert 'ready=0 cache=-1' in cmd('st_portraitqa');shot('off-1280x1024')
    cmd('set st_portraitMode 1; set st_portraitDamage 1; st_portraitqa damage; wait 3; st_portraitqa')
    r=transcript[-1];assert re.search(r'kick=0\.[1-9]',r),r
    cmd('set st_portraitDamage 0; st_portraitqa damage; wait 3; st_portraitqa')
    assert 'kick=0.000' in transcript[-1]
    for size in [48,144]:
        cmd('set st_portraitSize '+str(size));shot('size-'+str(size)+'-1280x1024')
    cmd('set st_portraitSize 80; set st_portraitDamage 1; set st_portraitTarget 0')
    cmd('set st_streamerMode 1; set st_streamerCleanHud 1');shot('streamer-clean')
    cmd('set st_streamerMode 0')
    assert 'recording to demos/' in cmd('st_record')
    assert 'Saved recording:' in cmd('st_record')
    cmd('map_restart 0');time.sleep(2)
    assert 'ready=1' in cmd('st_portraitqa')
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    (EVIDENCE/'behavior.log').write_text('\n'.join(transcript))
    print('PASS target selection, live pose, face mirroring, static/off, damage toggle, size limits, recording and restart',flush=True)

def title():
    lines=['disconnect','wait 45','ui_openmenu setup_menu','wait 10',
        'st_clientqa move setup_menu gameoptionmenubutton','st_clientqa click','wait 3',
        'st_clientqa move setup_menu st_portrait_settings','st_clientqa click','wait 3',
        'st_clientqa state','screenshot_png portrait-title-options',
        'st_clientqa move st_portrait_main mode','st_clientqa click','st_portraitMode',
        'st_clientqa move st_portrait_main reset','st_clientqa click',
        'st_clientqa move st_portrait_main back','st_clientqa click','st_clientqa state',
        'echo PORTRAIT_TITLE_COMPLETE','wait 3','quit']
    (native.MOD/'st-portrait-title.cfg').write_text('\n'.join(lines)+'\n')
    log=native.HOME/'SaberTrials/qconsole.log';offset=log.stat().st_size
    command('exec st-portrait-title.cfg')
    for _ in range(120):
        time.sleep(.25)
        result=log.read_bytes()[offset:].decode(errors='replace')
        if 'PORTRAIT_TITLE_COMPLETE' in result:break
    assert 'focused=st_portrait_main' in result and 'focused=setup_menu' in result,result[-3000:]
    assert 'QA item missing' not in result and 'ERROR: ui/' not in result
    (EVIDENCE/'title.log').write_text(result)
    shutil.copy2(native.HOME/'SaberTrials/screenshots/portrait-title-options.png',EVIDENCE/'portrait-title-options.png')
    print('PASS title Game Options portrait settings and Back navigation',flush=True)

def production():
    assert 'Unknown command' in command('st_portraitqa')
    assert 'Unknown command' in command('st_clientqa state')
    assert 'Saber Trials gametype' in command('st_status')
    time.sleep(6)
    command('model luffy/default');time.sleep(3)
    shot('production-luffy-1280x720')
    command('ui_openmenu st_portrait_ingame');shot('production-options-1280x720')
    # A real level change invokes CG_Shutdown and recreates the portrait cache.
    command('devmap mp/duel3')
    for _ in range(60):
        time.sleep(.3)
        if 'Saber Trials gametype' in command('st_status'):break
    time.sleep(3)
    command('team free');time.sleep(.5);shot('production-level-change')
    assert 'recording to demos/' in command('st_record')
    assert 'Saved recording:' in command('st_record')
    log=native.HOME/'SaberTrials/qconsole.log'
    content=log.read_text(errors='replace')
    assert 'ERROR: ui/' not in content and 'Failed userinfo validation' not in content
    (EVIDENCE/'production.log').write_text(content)
    command('quit')
    print('PASS production: no QA commands, portrait/menu load, level change and recording',flush=True)

if __name__=='__main__':
    action=sys.argv[1]
    if action=='start':start(sys.argv[2] if len(sys.argv)>2 else 'qa',*(map(int,sys.argv[3:5])))
    elif action=='command':print(command(sys.argv[2]))
    elif action=='models':models()
    elif action=='menu':menu()
    elif action=='behavior':behavior()
    elif action=='title':title()
    elif action=='production':production()
    elif action=='shot':shot(sys.argv[2])
    else:raise SystemExit('Use start, command, models, menu, shot')
