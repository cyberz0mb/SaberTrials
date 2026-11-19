"""Check regular-launcher menus and dedicated compatibility with isolated settings."""
from pathlib import Path
import argparse
import importlib.util
import json
import os
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('mvp_installer', ROOT / 'tools/Install-MVP-Cinematic.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def run(folder, renderer=None):
    mod = folder / 'home/SaberTrials'
    mod.mkdir(parents=True)
    settings = dict(fs_basepath=str(ROOT.parent), fs_homepath=str(folder / 'home'),
                    fs_game='SaberTrials', com_unpackLibraries='0', logfile='2', developer='1',
                    net_ip='127.0.0.1', net_port='29081')
    if renderer:
        # Use the flags actually enabled by the normal launcher, with only
        # window/renderer/home overrides needed for a nonintrusive smoke check.
        launcher = (ROOT / 'tools/launchers/SaberTrials.cmd').read_text()
        for name in ('sv_pure', 'st_mvpPrototype', 'st_mvpTestSingleSaber'):
            match = re.search(r'\+set ' + name + r' (\d+)\b', launcher)
            assert match, name
            settings[name] = match[1]
        settings.update(r_fullscreen='0', r_mode='-1', r_customwidth='1280', r_customheight='720',
                        cl_renderer=renderer, com_maxfps='60', com_introplayed='1', s_initsound='0')
        lines = ['wait 90', 'screenshot_png installed-main', 'wait 20',
                 'ui_openmenu controlsMenu', 'wait 20', 'screenshot_png installed-controls',
                 'wait 20', 'ui_openmenu setup_menu', 'wait 20', 'screenshot_png installed-setup',
                 'wait 20', 'echo MVP_INSTALLED_MENUS_COMPLETE', 'quit']
        executable = ROOT / 'client/SaberTrials.x86_64.exe'
    else:
        settings.update(dedicated='1', st_mvpPrototype='1')
        lines = ['set sv_master%d ""' % i for i in range(1, 6)] + [
            'set sv_pure 0', 'set g_gametype 3', 'set sv_maxclients 4', 'map mp/duel1',
            'wait 20', 'echo MVP_INSTALLED_SERVER_COMPLETE', 'quit']
        executable = ROOT / 'client/openjkded.x86_64.exe'
    (mod / 'installed-check.cfg').write_text('\n'.join(lines) + '\n', encoding='ascii')
    command = [str(executable), '+safe'] + [v for key, value in settings.items() for v in ('+set', key, value)]
    command += ['+exec', 'installed-check.cfg']
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    env = os.environ.copy()
    env['LOCALAPPDATA'] = str(folder / 'local-app-data')
    process = subprocess.Popen(command, cwd=ROOT.parent, env=env, startupinfo=startup,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        process.wait(timeout=60)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        raise
    logpath = mod / 'qconsole.log'
    log = logpath.read_text(errors='replace')
    assert process.returncode == 0, 'Installed process failed: ' + str(process.returncode)
    assert not re.search(r'Mismatched .*API_VERSION|API version mismatch|VM_Create on .* failed', log)
    assert not list(mod.glob('*.dll')) and not list(mod.glob('*.pk3'))
    assert not (mod / 'ui').exists(), 'Unexpected UI override in smoke home.'
    if renderer:
        assert 'MVP_INSTALLED_MENUS_COMPLETE' in log
        assert 'Server Initialization' not in log
        loads = re.findall(r'Trying to load "(rd-[^"]+)" from "([^"]+)"', log)
        assert loads and all(name == renderer + '_x86_64.dll' and Path(path).resolve() == (ROOT / 'client').resolve()
                             for name, path in loads), loads
        shots = list((mod / 'screenshots').glob('installed-*.png'))
        assert len(shots) == 3 and all(p.stat().st_size > 10000 for p in shots)
    else:
        assert 'MVP_INSTALLED_SERVER_COMPLETE' in log and '------- Game Initialization -------' in log
        assert 'MVP_PLAYBACK' not in log and 'WINNER_FINAL' not in log
        shots = []
    return dict(passed=True, returncode=process.returncode, renderer=renderer,
                log_sha256=installer.sha(logpath), executable_sha256=installer.sha(executable),
                screenshots={p.name: installer.sha(p) for p in shots})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    installer.verify(settings=True)
    folder = installer.OUT / 'qa' / args.run
    assert not folder.exists(), 'Use a new evidence folder.'
    results = {}
    for name in ('rd-vanilla', 'rd-rend2', 'server'):
        results[name] = run(folder / name, None if name == 'server' else name)
        print('Installed check passed:', name, flush=True)
    installer.verify(settings=True)
    (folder / 'result.json').write_text(json.dumps(dict(passed=True, results=results,
        installation_receipt_sha256=installer.sha(installer.STATE)), indent=2) + '\n')
