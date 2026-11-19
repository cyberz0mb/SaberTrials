"""Run the emote candidate with its real client, game module and JA+ test pack."""
from argparse import ArgumentParser
from datetime import datetime
from importlib import import_module
import os
import re
import shutil
import subprocess
import time

b = import_module('Build-Emotes')
pack = import_module('Pack-Emote')


def log(path):
    file = path/'qconsole.log'
    return file.read_text(errors='replace') if file.exists() else ''


def stage(root, renderer, installed=False, server=False, use_pack=True):
    mod = root/'home/SaberTrials'
    mod.mkdir(parents=True)
    binary = root/'bin'
    binary.mkdir()
    if not installed:
        for name, source in b.files().items():
            dst = (binary if name.startswith('client/') else mod) / name.split('/')[-1]
            shutil.copyfile(source,dst)
    for name in ('SDL2.dll','OpenAL32.dll','rd-vanilla_x86_64.dll','rd-rend2_x86_64.dll','rd-dedicated_x86_64.dll'):
        if (b.ROOT/'client'/name).is_file():
            shutil.copyfile(b.ROOT/'client'/name,binary/name)
    shutil.copytree(b.ROOT/'client/translator/fonts',binary/'translator/fonts')
    if use_pack:
        pack.package(b.ROOT.parent/'base/japlus_gla_anims.pk3',mod/'dlc/emotes/japlus-silence.pk3',
                     'japlus_silence','Silence (JA+)',13518,29,20)
    if server:
        executable = 'openjkded.x86_64.exe'
    else:
        executable = 'SaberTrials.x86_64.exe'
    return (b.ROOT/'client'/executable if installed else binary/executable),mod


def launch(root, exe, mod, lines, port, renderer, server=False):
    (mod/'emotes-test.cfg').write_text('\n'.join(lines)+'\n',encoding='ascii')
    cvars = dict(fs_basepath=b.ROOT.parent,fs_homepath=root/'home',fs_game='SaberTrials',
                 com_unpackLibraries=0,logfile=2,net_ip='127.0.0.1',net_port=port,
                 sv_pure=0,s_initsound=0,com_introplayed=1,developer=1)
    if server:
        cvars.update(dedicated=1,sv_maxclients=6)
    else:
        cvars.update(r_fullscreen=0,r_mode=-1,r_customwidth=1280,r_customheight=720,
                     cl_renderer=renderer,com_maxfps=60)
    command = [str(exe),'+safe']
    for key,value in cvars.items():
        command += ['+set',key,str(value)]
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    return subprocess.Popen(command+['+exec','emotes-test.cfg'],cwd=b.ROOT.parent,startupinfo=startup,
        env={**os.environ,'LOCALAPPDATA':str(root/'local-app-data')},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


def verify(root, watched, name):
    files = {name:b.sha(path) for name,path in b.files().items()}
    b.write(root/'result.json',dict(source=b.sha(b.RECEIPT),files=files,logs={p.name:b.sha(p) for p in watched}))
    print('Passed '+name,flush=True)


def local(renderer, installed):
    root = b.OUT / ('installed-'+renderer if installed else renderer)
    run = root / datetime.now().strftime('%H%M%S-%f')
    exe,mod = stage(run,renderer,installed)
    lines = ['set st_menuMotion 1','set con_notifytime 0','wait 60','bind F6 +scores','bind JOY9 +use','ui_openmenu controlsMenu','wait 22',
        'st_emoteuiqa controls','st_emoteinputqa F6 1','st_emoteinputqa F6 0','st_emoteuiqa conflict replace',
        'st_emoteinputqa F6 0','st_emoteuiqa controls','st_emoteinputqa JOY9 1','st_emoteinputqa JOY9 0',
        'st_emoteuiqa conflict swap','st_emoteinputqa F6 0','st_emoteinputqa JOY9 0',
        'st_emoteuiqa resume','ui_openmenu playerMenu','wait 35','st_emoteuiqa open','wait 20','st_emoteuiqa loop',
        'st_emoteuiqa preview 5','wait 12','st_emoteuiqa loop','screenshot_png emote-library',
        'wait 215','st_emoteuiqa loop','wait 14','st_emoteuiqa loop','st_emoteuiqa rename','wait 4',
        'screenshot_png emote-rename','st_emoteuiqa rename','st_emoteuiqa assign','st_emoteuiqa close','wait 5',
        'set cg_thirdPerson 1','set cg_thirdPersonAngle 160','set g_gametype 0','devmap mp/ffa3',
        'wait 420','team free','wait 100','st_emoteuiqa resume','wait 75','st_emote japlus_silence',
        'wait 29','screenshot_png emote-playing','wait 120',
        'setviewpos -1208 -912 192 0','wait 65','set st_emoteGroup 0',
        '+forward','wait 8','st_emoteinputqa JOY9 1',
        'wait 8','st_emoteinputqa 2 1','st_emoteinputqa 2 0','wait 16','screenshot_png emote-wheel',
        'wait 6','st_emoteinputqa JOY9 0',
        'wait 10','-forward','wait 80',
        'echo EMOTES_DONE','quit']
    proc = launch(run,exe,mod,lines,29603,renderer)
    try:
        assert proc.wait(timeout=145) == 0
    finally:
        if proc.poll() is None: proc.kill(); proc.wait()
    output = log(mod)
    for required in ('loaded 1 DLC clips','ST_EMOTE_UI_ASSIGN japlus_silence','EMOTES_DONE',
                     'ST_EMOTE_UI_PREVIEW 5 1','ST_EMOTE_START 0 japlus_silence','ST_EMOTE_POSE 0 japlus_silence',
                     'ST_EMOTE_UI_LOOP taunt 1','ST_EMOTE_START 0 bow moving=1','ST_EMOTE_POSE 0 bow',
                     'ST_EMOTE_BIND_ROW Emote Wheel','ST_EMOTE_BIND_CONFLICT 0','ST_EMOTE_BIND_CONFLICT 1'):
        assert required in output, (required,mod/'qconsole.log')
    for key,command in (('F6','+use'),('JOY9','+st_emotewheel')):
        assert re.search(rf'ST_EMOTE_INPUT {key} \d+ 0 0 {re.escape(command)}\b',output), key
    frames = re.findall(r'ST_EMOTE_UI_LOOP japlus_silence 1 ([\d.]+)',output)
    assert len(frames)==3 and abs(float(frames[-1])-float(frames[-2]))>0.1, frames
    for name in ('emote-library','emote-rename','emote-playing','emote-wheel'):
        assert f'Wrote screenshots/{name}.png' in output, name
    verify(root,[mod/'qconsole.log'],root.name)


def network():
    root = b.OUT/'network'
    run = root/datetime.now().strftime('%H%M%S-%f')
    server = run/'server'
    client = run/'client'
    observer = run/'observer'
    server_exe, server_mod = stage(server,'rd-vanilla',server=True)
    client_exe, client_mod = stage(client,'rd-vanilla')
    view_exe, view_mod = stage(observer,'rd-vanilla')
    port = 29619
    server_cmd = ['set g_gametype 0','set fraglimit 0','set g_warmup 0','map mp/ffa3']
    connect = ['wait 55',f'connect 127.0.0.1:{port}','wait 520']
    client_cmd = connect + ['team free','wait 215','st_emoteuiqa resume','wait 30','st_emote japlus_silence','wait 190',
        '+forward','wait 8','st_emote bow','wait 26','-forward','wait 75',
        'echo EMOTE_PLAYER_COMPLETE','quit']
    observer_cmd = connect + ['team s','wait 145','follownext','st_emoteuiqa resume','wait 615',
        'screenshot_png emote-observer','echo EMOTE_OBSERVER_COMPLETE','quit']
    procs=[]
    try:
        procs.append(launch(server,server_exe,server_mod,server_cmd,port,'rd-vanilla',True))
        deadline = time.monotonic()+40
        while 'Game Initialization' not in log(server_mod):
            assert time.monotonic() < deadline and procs[0].poll() is None
            time.sleep(.2)
        procs.append(launch(observer,view_exe,view_mod,observer_cmd,port+1,'rd-vanilla'))
        procs.append(launch(client,client_exe,client_mod,client_cmd,port+2,'rd-vanilla'))
        assert procs[2].wait(timeout=170) == 0
        assert procs[1].wait(timeout=170) == 0
        assert 'EMOTE_PLAYER_COMPLETE' in log(client_mod)
        assert 'EMOTE_OBSERVER_COMPLETE' in log(view_mod)
        assert any('ST_EMOTE_START ' in line and 'japlus_silence' in line for line in log(server_mod).splitlines()), server_mod
        assert any('ST_EMOTE_POSE ' in line and 'japlus_silence' in line for line in log(view_mod).splitlines()), view_mod
        assert re.search(r'ST_EMOTE_START \d+ bow moving=1',log(server_mod)), server_mod
        assert re.search(r'ST_EMOTE_POSE \d+ bow',log(view_mod)), view_mod
        verify(root,[server_mod/'qconsole.log',client_mod/'qconsole.log',view_mod/'qconsole.log'],'network')
    finally:
        for process in procs:
            if process.poll() is None:process.kill();process.wait()


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--vanilla',action='store_true')
    parser.add_argument('--network',action='store_true')
    parser.add_argument('--installed',action='store_true')
    args = parser.parse_args()
    if args.network:
        network()
    else:
        local('rd-vanilla' if args.vanilla else 'rd-rend2',args.installed)
