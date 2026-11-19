"""Stage a private MVP fidelity test without replacing installed game files."""
from pathlib import Path
import importlib.util
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist/mvp-cinematic-candidate-03'
TEST_MAP = 'mp/duel1'  # Bespin Courtyard: compact duel arena, played as FFA.


def helper():
    spec = importlib.util.spec_from_file_location('mvp_build', ROOT / 'tools/Build-MVP-Cinematic.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage(folder):
    build = helper()
    state = build.verify()
    if set(state['builds']) != {'engine', 'game', 'frontend'}:
        raise RuntimeError('All three matching components must be built first')
    files = {'bin/SaberTrials.x86_64.exe': OUT / 'build-engine/Release/openjk.x86_64.exe',
             'home/SaberTrials/jampgamex86_64.dll': OUT / 'build-game/Release/jampgamex86_64.dll',
             'home/SaberTrials/cgamex86_64.dll': OUT / 'build-frontend/Release/cgamex86_64.dll',
             'home/SaberTrials/uix86_64.dll': OUT / 'build-frontend/Release/uix86_64.dll'}
    for name in ('SDL2.dll', 'OpenAL32.dll'):
        files['bin/' + name] = ROOT / 'client' / name
    for name in ('rd-vanilla_x86_64.dll', 'rd-rend2_x86_64.dll'):
        files['bin/' + name] = OUT / 'build-engine/Release' / name
    for name in state['assets']:
        files['home/SaberTrials/' + name] = OUT / 'assets' / name
    for relative, source in files.items():
        target = folder / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    build.write(folder / 'stage-receipt.json', {'installed': False,
                'files': {name: build.sha(folder / name) for name in files}})
    return folder / 'home/SaberTrials'


def installed_home(folder):
    installer = helper().load('mvp_install_check', ROOT / 'tools/Install-MVP-Cinematic.py')
    installer.verify(settings=True)
    mod = folder / 'home/SaberTrials'
    mod.mkdir(parents=True)
    return mod


def executable(folder, installed=False):
    return ROOT / 'client/SaberTrials.x86_64.exe' if installed else folder / 'bin/SaberTrials.x86_64.exe'


def arguments(folder, renderer='vanilla', installed=False):
    values = {'fs_basepath': str(ROOT.parent), 'fs_homepath': str(folder / 'home'),
              'fs_game': 'SaberTrials', 'fs_forcegame': 'SaberTrials', 'com_unpackLibraries': '0',
              'r_fullscreen': '0', 'r_mode': '-1', 'r_customwidth': '1280', 'r_customheight': '720',
              'cl_renderer': 'rd-' + renderer, 'com_maxfps': '60', 'com_introplayed': '1',
              'logfile': '2', 'developer': '1', 'net_ip': '127.0.0.1', 'net_port': '29079'}
    if installed:
        launcher = (ROOT / 'tools/launchers/SaberTrials.cmd').read_text()
        for name in ('st_mvpPrototype', 'st_mvpTestSingleSaber'):
            match = re.search(r'\+set ' + name + r' (\d+)\b', launcher)
            assert match, 'Missing cinematic launcher setting: ' + name
            values[name] = match[1]
    return ['+safe'] + [part for key, value in values.items() for part in ('+set', key, value)]


def match_settings(scrimmage=False):
    # OpenJK accepts only 32 startup commands. Match settings belong in the cfg.
    values = {'sv_pure': '0', 'sv_maxclients': '2', 'sv_fps': '20', 'g_gametype': '0',
              'fraglimit': '1', 'g_doWarmup': '0', 'g_warmup': '0', 'timelimit': '0', 'st_mvpPrototype': '1',
              'model': 'kyle/default', 'saber1': 'single_1', 'saber2': 'none',
              'name': 'MVP Tester', 'd_perPlayerGhoul2': '1', 'cl_allowDownload': '0', 'con_notifytime': '0'}
    values.update({'sv_master' + str(i): '' for i in range(1, 6)})
    if scrimmage:
        values.update({'sv_maxclients': '4', 'fraglimit': '5'})
    return ['exec mpdefault.cfg'] + ['set ' + key + ' "' + value + '"' for key, value in values.items()]


def configure(folder, lines, config, launcher):
    mod = stage(folder)
    (mod / config).write_text('\n'.join(lines) + '\n', encoding='ascii')
    args = arguments(folder) + ['+exec', config]
    (folder / 'launch-arguments.json').write_text(json.dumps(args, indent=2))
    (folder / 'Launch-MVP-Test.ps1').write_text('''$stageRoot = $PSScriptRoot
$argsList = Get-Content -LiteralPath (Join-Path $stageRoot 'launch-arguments.json') -Raw | ConvertFrom-Json
$quotedArgs = $argsList | ForEach-Object { '"' + ($_ -replace '"', '\\"') + '"' }
$env:LOCALAPPDATA = Join-Path $stageRoot 'local-app-data'
Start-Process -FilePath (Join-Path $stageRoot 'bin/SaberTrials.x86_64.exe') -ArgumentList $quotedArgs -WorkingDirectory (Join-Path $stageRoot 'bin')
''')
    # Development launchers belong beside their private builds, never in the
    # main game folder after a completed feature has been promoted.
    (folder / launcher).write_bytes(('@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File '
        '"%~dp0Launch-MVP-Test.ps1"\r\nif errorlevel 1 pause\r\n').encode('ascii'))
    print('Private MVP test staged: ' + str(folder))


def main():
    lines = match_settings(scrimmage=True) + ['bind F5 "exec mvp-test.cfg"',
            'devmap ' + TEST_MAP, 'wait 180', 'team free', 'wait 90', 'kick allbots']
    for number in range(1, 4):
        lines += ['addbot "Kyle Katarn" 1 free 0 "MVP Bot %d" duelist' % number]
    lines += ['wait 240', 'st_mvptestready']
    configure(OUT / 'playable', lines, 'mvp-test.cfg', 'Play-SaberTrials-MVP-Test.cmd')
    for tournament in (False, True):
        lines = match_settings() + ['set g_gametype 3', 'set sv_maxclients 4',
            'set st_mvpTestSingleSaber 1', 'set st_mvpPrototype 0',
            'set st_duelBestOf 3', 'set duel_fraglimit 0',
            'set st_tournamentBestOf 3', 'set st_tournamentFinalBestOf 3',
            'set st_tournamentArenas "mp/duel1"', 'bind F5 "exec winner-test.cfg"',
            'devmap ' + TEST_MAP, 'wait 180', 'st_tournament reset',
            'team free', 'wait 90', 'kick allbots', 'set st_mvpPrototype 1']
        for number in range(1, 4 if tournament else 2):
            lines += ['addbot "Kyle Katarn" 1 free 0 "Duel Bot %d" duelist' % number]
        lines += ['wait 240']
        if tournament:
            lines += ['st_tournament open'] + ['st_tournament add %d' % n for n in range(4)]
            lines += ['st_tournament start', 'wait 240']
        lines += ['st_mvptestready']
        configure(OUT / ('playable-tournament' if tournament else 'playable-duel'), lines,
                  'winner-test.cfg', 'Play-SaberTrials-' +
                  ('1v1-Tournament' if tournament else 'Duel') + '-Replay-Test.cmd')


if __name__ == '__main__':
    main()
