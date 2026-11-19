"""Loopback dedicated server: matching and missing-pack observers."""
from datetime import datetime
from importlib import import_module
import os
import re
import shutil
import subprocess
import time

b=import_module('Build-Weapon-DLC')
checks=import_module('Check-Weapon-DLC')


def start(folder,lines,port,server=False,assets=True):
    mod=folder/'home/SaberTrials'
    mod.mkdir(parents=True)
    for name,path in b.files().items(): shutil.copyfile(path,mod/name)
    if assets: checks.fixtures(mod)
    (mod/'test.cfg').write_text('\n'.join(lines)+'\n')
    options=dict(fs_basepath=b.ROOT.parent,fs_homepath=folder/'home',fs_game='SaberTrials',com_unpackLibraries=0,
        logfile=2,net_ip='127.0.0.1',net_port=port,sv_pure=0,sv_allowDownload=0)
    if not server:
        options.update(r_fullscreen=0,r_mode=-1,r_customwidth=960,r_customheight=540,
            cl_renderer='rd-vanilla',com_maxfps=60,s_initsound=0,com_introplayed=1,cl_allowDownload=0)
    command=[str(b.ROOT/'client'/('openjkded.x86_64.exe' if server else 'SaberTrials.x86_64.exe')),'+safe']
    for name,value in options.items(): command.extend(['+set',name,str(value)])
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    return subprocess.Popen(command+['+exec','test.cfg'],cwd=b.ROOT.parent,startupinfo=startup,
        env={**os.environ,'LOCALAPPDATA':str(folder/'local-app-data')},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


def log(folder):
    path=folder/'home/SaberTrials/qconsole.log'
    return path.read_text(errors='replace') if path.exists() else ''


def wait_for(folder,marker,timeout=50):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if marker in log(folder): return
        time.sleep(.25)
    raise AssertionError((marker,log(folder)[-1200:]))


def run():
    folder=b.OUT/f'network-{datetime.now():%H%M%S}'
    serverFolder=folder/'server';actorFolder=folder/'actor'
    processes=[];results={}
    print(folder,flush=True)
    try:
        processes.append(start(serverFolder,['set sv_hostname "Weapon DLC private test"','set sv_maxclients 4',
            'set g_gametype 0','set g_weaponDisable 0','set st_mvpPrototype 0','set g_infiniteAmmo 1',
            'set sv_master1 ""','set sv_master2 ""','set sv_master3 ""','set sv_master4 ""','set sv_master5 ""',
            'devmap mp/ffa3'],29244,True))
        wait_for(serverFolder,'InitGame:')
        processes.append(start(actorFolder,['wait 60','set name DLC_Actor','connect 127.0.0.1:29244','wait 650',
            'team free','wait 120','ui_openmenu ingame_setup','wait 10','togglemenu','wait 30',
            'give weapons','give ammo 100','god','wait 120','weaponclean 5','wait 150',
            'weapnext','wait 100','weapnext','wait 100','st_weaponinfo','echo ST_DLC_ACTOR_READY',
            '+attack','wait 200','-attack','wait 24000','quit'],29245))
        wait_for(actorFolder,'ST_DLC_ACTOR_READY')
        for missing in (False,True):
            label='missing' if missing else 'matching'
            observer=folder/label
            p=start(observer,['wait 60','set name DLC_Observer','connect 127.0.0.1:29244','wait 650',
                'team spectator','wait 70','ui_openmenu ingame_setup','wait 10','togglemenu',
                'wait 60','team follow1','wait 60','follow DLC_Actor','wait 180','set cg_thirdPerson 1',
                'wait 100','st_weaponinfo','screenshot_png '+label,'echo ST_DLC_OBSERVER_DONE','wait 15','quit'],
                29246,assets=not missing)
            processes.append(p)
            assert p.wait(timeout=70)==0
            record=log(observer)
            assert 'ST_DLC_OBSERVER_DONE' in record,record[-1000:]
            match=re.search(r'ST_DLC_REMOTE client=0 base=5 id=2 installed=(\d) attached=(\d)',record)
            assert match,record[-2500:]
            assert tuple(match.groups())==(('0','0') if missing else ('1','1')),match.group()
            if missing: assert 'missing or different; stock visuals used' in record
            results[label]=match.group()
            print(label+': '+match.group(),flush=True)
        b.write(folder/'result.json',dict(source=b.sha(b.RECEIPT),files={name:b.sha(path) for name,path in b.files().items()},results=results))
    finally:
        for p in reversed(processes):
            if p.poll() is None: p.terminate();p.wait(timeout=15)
    print('Passed dedicated-server add-on visibility and missing-pack fallback.',flush=True)


if __name__=='__main__': run()
