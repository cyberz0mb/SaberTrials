"""Capture the Profile and live scoreboard using isolated client settings."""
import argparse
from importlib import import_module
import os
from pathlib import Path
import shutil
import subprocess

build = import_module('Build-Profile-Scoreboard')
ROOT, OUT, sha, read = build.ROOT, build.OUT, build.sha, build.read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag', choices=('baseline', 'wide', 'tall', 'production', 'installed'))
    parser.add_argument('--install-receipt', type=Path)
    args = parser.parse_args()
    tag = args.tag
    qa = tag in ('baseline', 'wide', 'tall')
    renderer, height = ('rd-rend2', '1024') if tag == 'tall' else ('rd-vanilla', '720')
    run = OUT / 'verification' / ('checked-' + tag)
    mod = run / 'home/SaberTrials'
    mod.mkdir(parents=True)
    state = read(OUT / 'source-receipt.json')
    modules = {'uix86_64.dll': 'qa' if qa else 'ui', 'cgamex86_64.dll': 'cgame'}
    evidence = {}
    if args.install_receipt and tag != 'installed':
        parser.error('--install-receipt is only for checking an installed build')
    for name, role in modules.items():
        if tag == 'baseline':
            path = build.UI_BASE / 'build-qa/Release' / name if role == 'qa' else ROOT / name
            expected = read(build.UI_BASE / 'build-record-qa.json')['ui_sha256'] if role == 'qa' else state['installed'][name]
        elif args.install_receipt:
            path = ROOT / name
            expected = read(args.install_receipt)['after'][name]
        else:
            record = read(OUT / f'build-{role}.json')
            assert record['source_sha256'] == sha(OUT / 'source-receipt.json')
            expected = record['sha256']
            path = ROOT / name if tag == 'installed' else OUT / ('build-' + role) / 'Release' / name
        assert sha(path) == expected
        if tag != 'installed':
            shutil.copy2(path, mod / name)
        evidence[role] = expected
    lines = ['wait 70', 'set st_hudStyle 1', 'set name "Profile Review"', 'set model kyle/default',
             'set g_gametype 0', 'set sv_maxclients 16', 'set g_warmup 0', 'devmap mp/ffa3', 'wait 160',
             'team free', 'addbot "Kyle Katarn" 1', 'addbot "Jan Ors" 1', 'addbot desann 1', 'addbot reborn 1',
             'addbot tavion 1', 'addbot "Luke Skywalker" 1', 'addbot alora 1', 'addbot stormtrooper 1', 'wait 90']
    captures = []

    def shot(name):
        captures.append(name)
        lines.extend(['wait 8', 'screenshot_png ' + name, 'wait 4'])

    def profile(command):
        lines.extend(['st_profileqa ' + command, 'wait 5'])

    lines.extend(['ui_openmenu ingame', 'wait 8', 'togglemenu', 'wait 12', '+scores', 'wait 32'])
    shot('scoreboard-ffa')
    lines.extend(['-scores', 'wait 16', 'ui_openmenu ingame_player', 'wait 15'])
    if qa:
        profile('assertlayout wide')
    shot('profile')
    if qa:
        profile('choose alora/default')
        profile('assertdirty 1')
        profile('favorite')
        profile('assertfavorite 1')
        profile('click 137')
        shot('profile-favorites')
        profile('click 137')
        profile('click 500')
        shot('profile-pending')
        profile('click 1002')
        profile('assertdirty 1')
        profile('click 500')
        profile('click 1001')
        lines.extend(['st_legacyqa assertmenu ingame', 'wait 5'])
        lines.extend(['togglemenu', 'set g_gametype 6', 'devmap mp/ffa3', 'wait 155',
                      'team red', 'addbot "Kyle Katarn" 1 red', 'addbot desann 1 blue', 'wait 65',
                      'ui_openmenu ingame', 'wait 8', 'togglemenu', 'wait 12', '+scores', 'wait 32'])
        shot('scoreboard-team')
        lines.append('-scores')
    lines.extend(['wait 8', 'echo ST_PROFILE_SCOREBOARD_COMPLETE', 'quit'])
    (mod / 'profile-scoreboard.cfg').write_text('\n'.join(lines) + '\n')
    options = {'fs_basepath': ROOT.parent, 'fs_homepath': run / 'home', 'fs_game': 'SaberTrials',
               'com_unpackLibraries': 0, 'r_fullscreen': 0, 'r_mode': -1, 'r_customwidth': 1280,
               'r_customheight': height, 'cl_renderer': renderer, 'com_maxfps': 60,
               's_initsound': 0, 'logfile': 2, 'com_introplayed': 1}
    command = [str(ROOT / 'client/SaberTrials.x86_64.exe'), '+safe']
    for key, value in options.items():
        command.extend(['+set', key, str(value)])
    command.extend(['+exec', 'profile-scoreboard.cfg'])
    startup = subprocess.STARTUPINFO()
    startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    env = {**os.environ, 'LOCALAPPDATA': str(run / 'local-app-data')}
    subprocess.run(command, cwd=ROOT.parent, env=env, startupinfo=startup,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=130, check=True)
    log_path = mod / 'qconsole.log'
    log = log_path.read_text(errors='replace')
    errors = [line for line in log.splitlines() if any(s in line for s in (
        'ST_PROFILE_FAIL', 'ST_LEGACY_FAIL', 'Unknown command "st_', 'ERROR: Could not'))]
    assert not errors and 'ST_PROFILE_SCOREBOARD_COMPLETE' in log, errors or log[-1800:]
    assert 'Server Initialization' in log and 'mp/ffa3' in log
    assert all((mod / 'screenshots' / (capture + '.png')).is_file() for capture in captures)
    build.write(run / 'result.json', dict(source_sha256=sha(OUT / 'source-receipt.json'),
                ui_sha256=evidence[modules['uix86_64.dll']], cgame_sha256=evidence['cgame'],
                log_sha256=sha(log_path), screenshots=captures, renderer=renderer, height=int(height)))
    print(f'Passed {tag}: {", ".join(captures)}', flush=True)


if __name__ == '__main__':
    main()
