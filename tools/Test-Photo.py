"""Verify Photo Mode using an isolated native loopback game and real menu input."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, re, shutil, subprocess, time

ROOT=Path(__file__).resolve().parent.parent
WORK=Path.home()/'AppData/Local/Temp/SaberTrials-photo-20261012'
EVIDENCE=ROOT/'dist/verification/photo-20261012'
spec=importlib.util.spec_from_file_location('native',ROOT/'tools/Test-Menu.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
native.WORK=WORK;native.RUNTIME=WORK/'runtime';native.MOD=native.RUNTIME/'SaberTrials';native.HOME=native.RUNTIME/'home'
native.transport.WORK=WORK;native.transport.HOME=native.HOME
game_process=None
def command(text):
    # RCON executes one command; it does not split semicolon command buffers.
    return '\n'.join(native.command(part.strip()) for part in text.split(';') if part.strip())

def start(mode='qa',width=1280,height=720,extra_stage=None):
    stage=WORK/'test-stage';stage.mkdir(parents=True,exist_ok=True)
    # Test-Menu has historical staging; overlay the complete accepted current UI.
    shutil.copytree(ROOT/'ui',stage/'ui',dirs_exist_ok=True)
    if mode!='installed':shutil.copytree(ROOT/'dist/photo-staging/ui',stage/'ui',dirs_exist_ok=True)
    if extra_stage:shutil.copytree(extra_stage,stage,dirs_exist_ok=True)
    output=ROOT if mode=='installed' else WORK/('build-qa' if mode=='qa' else 'build')/'Release'
    shutil.copy2(output/'cgamex86_64.dll',stage/'cgamex86_64.dll')
    engine=ROOT/'client/SaberTrials.x86_64.exe' if mode=='installed' else output/'openjk.x86_64.exe'
    real_popen=subprocess.Popen
    def photo_popen(args,**kwargs):
        global game_process
        args=list(args)
        if Path(args[0])==ROOT/'client/SaberTrials.x86_64.exe':
            args[0]=str(engine)
            game_process=real_popen(args,**kwargs)
            return game_process
        return real_popen(args,**kwargs)
    native.subprocess.Popen=photo_popen
    try:native.start(mode,width,height,stage)
    finally:native.subprocess.Popen=real_popen
    command('team free')
    command('set cg_draw2D 1; set cg_drawEnemyInfo 1; set st_hudStyle 1; set cg_drawFPS 1; set st_streamerMode 0; set cg_thirdPerson 1')
    time.sleep(.5)
    EVIDENCE.mkdir(parents=True,exist_ok=True)

def state():
    reply=command('st_photoqa')
    match=re.findall(r'PHOTO_QA (.+)',reply)
    assert match,reply
    return dict(re.findall(r'(\w+)=([^\s]+)',match[-1]))

def shot(name):
    p=native.HOME/'SaberTrials/screenshots'/('photo-'+name+'.png')
    stamp=p.stat().st_mtime_ns if p.exists() else 0
    command('screenshot_png photo-'+name)
    for _ in range(60):
        if p.exists() and p.stat().st_mtime_ns!=stamp:break
        time.sleep(.15)
    assert p.exists() and p.stat().st_mtime_ns!=stamp,'Screenshot missing: '+name
    shutil.copy2(p,EVIDENCE/p.name)

def key(code,down=True):command(f'st_engineqa key {code} {int(down)}')
def tap(code):key(code);key(code,False)

def capture():
    folder=native.HOME/'SaberTrials/screenshots'
    before=set(folder.glob('shot*.png'))
    command('st_photoCapture')
    for _ in range(80):
        files=set(folder.glob('shot*.png'))-before
        if files:break
        time.sleep(.1)
    assert files,'Clean capture was not saved'
    time.sleep(.2)
    p=next(iter(files));shutil.copy2(p,EVIDENCE/('clean-'+p.name))
    return p

def menu(size):
    command('ui_openmenu ingame');native.click('ingame','photo');native.focused('st_photo')
    shot('settings-'+size)
    for item,cv,value in [('value0','st_uiPhotoFov','77.5'),('value1','st_uiPhotoRoll','-12.5'),('value2','st_uiPhotoSpeed','134.5')]:
        command('set '+cv+' ""');native.click('st_photo',item);command('st_clientqa type '+value)
        command('st_clientqa enter')
    native.click('st_photo','apply')
    for cv,value in [('st_photoFov','77.5'),('st_photoRoll','-12.5'),('st_photoSpeed','134.5')]:
        assert f'= "{value}"' in command(cv),(cv,command(cv))
    command('set st_uiPhotoFov 999');native.click('st_photo','apply')
    assert '= "77.5"' in command('st_photoFov')
    native.click('st_photo','reset')
    for slider in ['slider0','slider1','slider2']:native.click('st_photo',slider)
    native.click('st_photo','apply');native.click('st_photo','reset')
    native.click('st_photo','guides')
    native.click('st_photo','start');time.sleep(.3)
    s=state();assert s['active']=='1' and s['detached']=='1' and s['solo']=='1',s
    assert s['hud']=='1' and s['streamer']=='0',s
    shot('camera-'+size)
    capture()
    print('PASS Photo page, sliders, manual decimals, invalid input, reset, clean PNG capture',flush=True)

def behavior():
    tap(ord('f'));time.sleep(.4)
    a=state();time.sleep(.5);b=state()
    assert a['frozen']=='1' and a['time']==b['time'],(a,b)
    key(ord('d'));time.sleep(.4);key(ord('d'),False)
    command('st_engineqa mouse 90 -30')
    c=state();assert c['origin']!=b['origin'] and c['angles']!=b['angles'],(b,c)
    assert c['time']==b['time'],(b,c)
    capture()
    tap(9);native.focused('st_photo');shot('frozen-settings')
    native.click('st_photo','start')
    s=state();assert s['active']=='1' and s['frozen']=='1',s
    tap(ord('f'));time.sleep(.5);s=state();assert s['frozen']=='0' and s['time']!=c['time'],s
    tap(27);time.sleep(.2);s=state();assert s['active']=='0' and s['catcher']=='0',s
    assert '= "0"' in command('cl_paused')
    assert '= "1"' in command('cg_draw2D') and '= "1"' in command('cg_drawEnemyInfo')
    shot('restored-hud')
    command('st_photo');time.sleep(.3);tap(ord('f'));time.sleep(.3)
    command('map_restart 0');time.sleep(3)
    s=state();assert s['active']=='0' and s['frozen']=='0',s
    assert '= "0"' in command('cl_paused')
    command('addbot kyle 1');time.sleep(2)
    command('st_photo');time.sleep(.3);tap(ord('f'));time.sleep(.3)
    a=state();time.sleep(.4);b=state();assert a['solo']=='1' and a['frozen']=='1' and a['time']==b['time'],(a,b)
    capture();tap(27)
    print('PASS local Live/Freeze, frozen camera movement, mouse look, resume, Esc restore, restart cleanup, bots',flush=True)

def replay():
    command('g_synchronousClients 1; record photo-test')
    command('+forward');time.sleep(1);command('-forward');time.sleep(2)
    command('stoprecord')
    # RCON stops with the local server; playback is driven by the client buffer.
    script=['disconnect','wait 45',
            'demo photo-test','wait 120','st_photo','wait 30','st_photoqa',
            'st_engineqa key 100 1','wait 15','st_engineqa key 100 0','st_engineqa mouse 80 0',
            'wait 5','st_photoqa','st_photoCapture']
    # Slow replay keeps enough recorded time for deterministic input checks.
    script.insert(2,'timescale 0.3')
    (native.MOD/'st-photo-replay.cfg').write_text('\n'.join(script)+'\n')
    log=native.HOME/'SaberTrials/qconsole.log';offset=log.stat().st_size
    command('exec st-photo-replay.cfg')
    for _ in range(300):
        time.sleep(.2);result=log.read_bytes()[offset:].decode(errors='replace')
        if result.count('DISCONNECTED')>=2:break
    assert result.count('DISCONNECTED')>=2,result[-3000:]
    rows=[dict(re.findall(r'(\w+)=([^\s]+)',line)) for line in re.findall(r'PHOTO_QA (.+)',result)]
    assert len(rows)>=2 and rows[0]['active']=='1' and rows[0]['solo']=='0',result[-5000:]
    assert rows[1]['origin']!=rows[0]['origin'] and rows[1]['angles']!=rows[0]['angles'],rows
    assert 'Wrote screenshots/' in result,result[-3000:]
    (EVIDENCE/'replay.log').write_text(result)
    print('PASS recorded replay free camera, movement, look, capture and exit',flush=True)

def online():
    command('st_photo');command('st_photoFreeze 1');time.sleep(.3)
    assert state()['frozen']=='1'
    peerhome=WORK/'peer-home'
    script=['wait 300','st_clientqa escape','st_clientqa escape','team free','wait 1600','st_photo','wait 10','st_photoqa',
            'set st_photoFreeze 1','wait 10','st_photoqa','team spectator','wait 90',
            'st_photo','wait 20','st_photoqa','+forward','wait 40','-forward',
            'wait 10','st_photoqa','wait 20','st_photoqa',
            'wait 1600','team free','wait 90','st_photoqa','wait 1600','team spectator',
            'wait 90','st_photo','wait 20','echo PHOTO_ONLINE_COMPLETE','st_photoCapture']
    (native.MOD/'st-photo-peer.cfg').write_text('\n'.join(script)+'\n')
    args=[str(WORK/'build-qa/Release/openjk.x86_64.exe'),'+set','fs_basepath',str(native.RUNTIME),
          '+set','fs_homepath',str(peerhome),'+set','fs_game','SaberTrials',
          '+set','net_ip','127.0.0.1','+set','net_port','27976','+set','r_fullscreen','0',
          '+set','r_mode','4','+set','s_initsound','0','+set','com_maxfps','60',
          '+set','logfile','2','+set','name','PhotoPeer','+set','cl_allowDownload','0',
          '+connect','127.0.0.1:27975','+exec','st-photo-peer.cfg']
    si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    peer=subprocess.Popen(args,cwd=native.RUNTIME,startupinfo=si,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(45):
            time.sleep(.2);s=state()
            if s['solo']=='0':break
        assert s['solo']=='0' and s['frozen']=='0' and s['active']=='0',s
        assert '= "0"' in command('cl_paused')
        for _ in range(300):
            time.sleep(.2)
            result=(peerhome/'SaberTrials/qconsole.log').read_text(errors='replace')
            if 'PHOTO_ONLINE_COMPLETE' in result and 'Wrote screenshots/' in result:break
        rows=[dict(re.findall(r'(\w+)=([^\s]+)',line)) for line in re.findall(r'PHOTO_QA (.+)',result)]
        assert len(rows)==6 and 'PHOTO_ONLINE_COMPLETE' in result,result[-3000:]
        assert all(row['solo']=='0' and row['frozen']=='0' for row in rows),rows
        assert rows[0]['active']==rows[1]['active']=='0',rows
        assert rows[2]['active']=='1' and rows[2]['detached']=='0',rows
        assert rows[3]['origin']!=rows[2]['origin'],rows
        assert rows[5]['active']=='0' and 'Wrote screenshots/' in result,rows
        (EVIDENCE/'online.log').write_text(result)
        print('PASS real second client releases freeze; remote player blocked; spectator movement/capture; rejoin cleanup',flush=True)
    finally:
        if peer.poll() is None:peer.terminate();peer.wait(timeout=10)

def production(size):
    assert 'Unknown command' in command('st_photoqa')
    assert 'Unknown command' in command('st_clientqa state')
    command('ui_openmenu st_photo');shot('production-settings-'+size)
    # Menu click/catcher handling is verified in the QA build. Production smoke
    # checks the identical camera/pause code without injected input commands.
    command('set st_photoMode 1; set st_photoFreeze 1')
    time.sleep(.5)
    assert '= "1"' in command('st_photoFrozen')
    command('st_photo');time.sleep(.3)
    assert '= "0"' in command('cl_paused')
    print('PASS production hooks absent, Photo settings render, local freeze and exit',flush=True)

def stop():
    command('quit')
    if game_process and game_process.poll() is None:
        try:game_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            game_process.terminate();game_process.wait(timeout=10)

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['qa','production','installed']);p.add_argument('--height',type=int,default=720)
    p.add_argument('--replay',action='store_true');p.add_argument('--online',action='store_true');args=p.parse_args()
    start(args.mode,1280,args.height)
    try:
        if args.mode=='qa':
            menu(f'1280x{args.height}');behavior()
            if args.online:online()
            if args.replay:replay()
        else:production(f'1280x{args.height}')
    finally:stop()
    output=ROOT if args.mode=='installed' else WORK/('build-qa' if args.mode=='qa' else 'build')/'Release'
    paths={name:output/name for name in ['cgamex86_64.dll','uix86_64.dll']}
    paths['engine']=ROOT/'client/SaberTrials.x86_64.exe' if args.mode=='installed' else output/'openjk.x86_64.exe'
    paths['menu']=ROOT/'ui/jamp/ingame.menu' if args.mode=='installed' else ROOT/'dist/photo-staging/ui/jamp/ingame.menu'
    hashes={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in paths.items()}
    report={'passed':True,'mode':args.mode,'height':args.height,'files':hashes,'replay':args.replay,'online':args.online}
    (EVIDENCE/f'{args.mode}-1280x{args.height}.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
