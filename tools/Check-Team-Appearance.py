"""Verify the Setup switches and two independent views of a loopback team match."""
from datetime import datetime
import argparse
from importlib import import_module
import json
import os
import re
import shutil
import subprocess
import time

c = import_module('Build-Team-Appearance')

UI, CG, GAME = 'uix86_64.dll', 'cgamex86_64.dll', 'jampgamex86_64.dll'
EXE = c.build_tools.EXE
PORT = 29172
SKINS, SABERS = 'cg_teamColorSkins', 'cg_teamColorSabers'


def stage_client(folder, mode):
    mod = folder/'home/SaberTrials'
    mod.mkdir(parents=True)
    if mode == 'installed':
        return mod, {name: c.ROOT/name for name in (EXE, UI, CG, GAME)}
    engine = folder/EXE
    engine.parent.mkdir()
    shutil.copyfile(c.build_tools.binary('engine'), engine)
    for name in ('SDL2.dll', 'OpenAL32.dll', 'rd-rend2_x86_64.dll', 'rd-vanilla_x86_64.dll'):
        shutil.copyfile(c.ROOT/'client'/name, engine.parent/name)
    roles = {UI: 'qa' if mode == 'settings' else 'ui',
             CG: 'qa-cgame' if mode == 'settings' else 'cgame', GAME: 'game'}
    for name, role in roles.items():
        shutil.copyfile(c.build_tools.binary(role), mod/name)
    return mod, {EXE: engine, **{name: mod/name for name in roles}}


def launch(folder, exe, filename, port, renderer=None):
    options = dict(fs_basepath=c.ROOT.parent, fs_homepath=folder/'home', fs_game='SaberTrials',
                   com_unpackLibraries=0, logfile=2, net_ip='127.0.0.1', net_port=port)
    if renderer:
        options.update(r_fullscreen=0, r_mode=-1, r_customwidth=1600, r_customheight=900,
                       cl_renderer='rd-'+renderer, com_maxfps=60, s_initsound=0, com_introplayed=1)
    command = [str(exe), '+safe']
    for key, value in options.items():
        command.extend(['+set', key, str(value)])
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    return subprocess.Popen(command+['+exec', filename], cwd=c.ROOT.parent,
        env={**os.environ, 'LOCALAPPDATA': str(folder/'local-app-data')}, startupinfo=startup,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def config(mod, lines):
    (mod/'review.cfg').write_text('\n'.join(lines)+'\n')


def log(mod):
    file = mod/'qconsole.log'
    return file.read_text(errors='replace') if file.exists() else ''


def smoke(folder, mode):
    mod, paths = stage_client(folder, mode)
    config(mod, ['wait 65', 'ui_openmenu setup_menu', 'wait 50', 'set sv_pure 0',
                 'set g_gametype 6', 'map mp/ffa3', 'wait 450', 'team red', 'wait 115',
                 'set cg_teamColorSkins 0', 'set cg_teamColorSabers 0', 'wait 30',
                 'echo TEAM_APPEARANCE_SMOKE', 'quit'])
    client = launch(folder, paths[EXE], 'review.cfg', PORT + 4, 'rend2')
    try:
        assert client.wait(timeout=85) == 0
    finally:
        if client.poll() is None:
            client.kill()
            client.wait()
    record = log(mod)
    assert 'TEAM_APPEARANCE_SMOKE' in record and 'CL_InitCGame:' in record, record[-1400:]
    return paths


def settings(folder):
    host = folder/'host'
    server = host/'home/SaberTrials'
    server.mkdir(parents=True)
    shutil.copyfile(c.build_tools.binary('game'), server/GAME)
    config(server, ['sv_pure 0', 'g_gametype 6', 'g_teamForceBalance 0', 'g_warmup 0',
                    'fraglimit 0', 'g_spawnInvulnerability 0', 'st_mvpPrototype 0', 'map mp/ffa3'])
    observer, actor, modular = (folder/name for name in ('observer','actor','modular'))
    observerMod, paths = stage_client(observer, 'settings')
    actorMod, actorPaths = stage_client(actor, 'settings')
    modularMod, modularPaths = stage_client(modular, 'settings')
    common = ['wait 55', f'connect 127.0.0.1:{PORT}', 'wait 420']
    close = ['ui_openmenu st_qa_no_menu', 'st_inspectqa key 27 1', 'wait 18']
    config(actorMod, ['set name AppearanceRed', 'set model kyle/default', 'set color1 3',
                     'set saber1 dual_1', 'set saber2 none', 'set st_crystal1 FF7A17,19ECCD']+common+
           ['team red', 'wait 120']+close+['weapon 1', 'wait 55', 'set st_reviewTeamAppearance other-initial',
           'wait 680', 'set st_reviewTeamAppearance other-later', 'wait 430', 'quit'])
    config(modularMod, ['set name AppearanceModular', 'set model jedi_hm/default',
                       'set char_color_red 63', 'set char_color_green 143', 'set char_color_blue 214']+common+
           ['team red', 'wait 130']+close+['wait 1120', 'quit'])

    catalog = json.loads((c.ROOT/'development-source/setup/catalog.json').read_text())
    ids = {row['name']: 2200 + i for i,row in enumerate(catalog)}
    lines = ['set name AppearanceBlue', 'set model bobathefett/esb', 'set color1 1',
             'set saber1 single_1', 'set saber2 none', 'set st_crystal1 B53DFF']+common+[
             'team blue', 'wait 190']+close+['set cg_thirdPerson 1', 'weapon 1', 'wait 105',
             'set st_reviewTeamAppearance defaults', 'wait 36', 'screenshot_png team-colors-on',
             'ui_openmenu ingame_setup', 'wait 32', 'st_setupqa assertmenu ingame_setup',
             'st_setupqa click 2003', 'wait 26',
             'screenshot_png team-appearance-setup']

    def toggle(name):
        lines.extend([f'st_setupqa click {ids[name]}', 'wait 12'])

    def apply():
        lines.extend(['st_setupqa click 2902', 'wait 36'])

    toggle(SKINS)
    lines.extend([f'st_setupqa assertvar {SKINS} 1', 'st_setupqa assertdirty 1',
                  'st_setupqa click 2901', 'wait 12', 'st_setupqa assertdirty 0'])
    toggle(SKINS)
    apply()
    lines.extend([f'st_setupqa assertvar {SKINS} 0', f'st_setupqa assertvar {SABERS} 1',
                  'set st_reviewTeamAppearance skins-off', 'wait 25'])
    toggle(SABERS)
    apply()
    lines.extend([f'st_setupqa assertvar {SABERS} 0', 'set st_reviewTeamAppearance both-off',
                  'wait 25', 'writeconfig appearance-saved.cfg'])
    toggle(SKINS)
    apply()
    lines.extend(['set st_reviewTeamAppearance sabers-off', 'wait 25'])
    toggle(SKINS)
    apply()
    lines.extend(close+['screenshot_png team-colors-off', 'wait 25',
                        'echo TEAM_APPEARANCE_DONE', 'quit'])
    config(observerMod, lines)

    serverProc = launch(host, c.ROOT/'client/openjkded.x86_64.exe', 'review.cfg', PORT)
    processes = [serverProc]
    try:
        deadline = time.monotonic()+30
        while 'Game Initialization' not in log(server) and time.monotonic()<deadline:
            assert serverProc.poll() is None, log(server)[-1600:]
            time.sleep(.2)
        assert 'Game Initialization' in log(server), log(server)[-1600:]
        for directory, files, port in ((actor,actorPaths,PORT+1), (modular,modularPaths,PORT+2),
                                       (observer,paths,PORT+3)):
            processes.append(launch(directory, files[EXE], 'review.cfg', port, 'vanilla'))
        for proc in processes[1:]:
            assert proc.wait(timeout=100) == 0
    finally:
        for proc in reversed(processes):
            if proc.poll() is None:
                proc.kill()
                proc.wait()

    observed = log(observerMod)
    assert 'TEAM_APPEARANCE_DONE' in observed and 'ST_SETUP_FAIL' not in observed, observed[-3300:]
    for phase, skin, preset, rgb in [
        ('defaults','red',0,'FFFFFFFF,FFFFFFFF'),
        ('skins-off','default',0,'FFFFFFFF,FFFFFFFF'),
        ('both-off','default',3,'FF7A17,19ECCD'),
        ('sabers-off','red',3,'FF7A17,19ECCD'),
    ]:
        assert re.search(fr'TEAM_APPEARANCE {phase} 1 kyle/{skin} preset={preset} rgb={rgb} .*defer=0', observed), observed[-5000:]
    assert re.search(r'TEAM_APPEARANCE defaults 2 bobathefett/esb preset=4 ', observed), observed[-5000:]
    assert re.search(r'TEAM_APPEARANCE both-off 1 jedi_hm/default .*outfit=3F8FD6 ', observed), observed[-5000:]
    for phase in ('other-initial','other-later'):
        assert f'TEAM_APPEARANCE {phase} 1 kyle/red preset=0 rgb=FFFFFFFF,FFFFFFFF' in log(actorMod)
    saved = (observerMod/'appearance-saved.cfg').read_text()
    assert all(f'seta {name} "0"' in saved for name in (SKINS, SABERS))
    assert all((observerMod/'screenshots'/f'{name}.png').is_file()
               for name in ('team-colors-on', 'team-colors-off', 'team-appearance-setup'))
    return paths


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('settings','production','installed'))
    mode = parser.parse_args().mode
    folder = c.OUT/f'{mode}-{datetime.now():%H%M%S}'
    print(folder, flush=True)
    files = settings(folder) if mode == 'settings' else smoke(folder, mode)
    c.write(folder/'result.json', dict(mode=mode, source=c.sha(c.RECEIPT),
                                      binaries={name: c.sha(path) for name,path in files.items()}))
    print('Passed '+folder.name)
