"""Check installed native menus with private settings; never load a map/server."""
from pathlib import Path
import importlib.util, json, os, subprocess, sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist/controls-setup-release-01'


if __name__ == '__main__':
    spec = importlib.util.spec_from_file_location('installed_menus', ROOT / 'tools/Install-Controls-Setup.py')
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    state = installer.verify()
    results = {}
    for renderer in ('rd-vanilla', 'rd-rend2'):
        run = OUT / 'installed-verification' / renderer
        assert not run.exists()
        mod = run / 'home/SaberTrials'
        mod.mkdir(parents=True)
        (mod / 'installed-menu-check.cfg').write_text('\n'.join([
            'wait 80', 'ui_openmenu controlsMenu', 'wait 15',
            'screenshot_png installed-controls', 'wait 8',
            'ui_openmenu setup_menu', 'wait 15',
            'screenshot_png installed-setup', 'wait 8',
            'echo ST_INSTALLED_MENUS_COMPLETE', 'quit', '']))
        exe = ROOT / 'client/SaberTrials.x86_64.exe'
        args = [str(exe), '+safe', '+set', 'fs_basepath', str(ROOT.parent),
                '+set', 'fs_homepath', str(run / 'home'), '+set', 'fs_game', 'SaberTrials',
                '+set', 'com_unpackLibraries', '0', '+set', 'r_fullscreen', '0',
                '+set', 'r_mode', '-1', '+set', 'r_customwidth', '1280',
                '+set', 'r_customheight', '720', '+set', 'cl_renderer', renderer,
                '+set', 's_initsound', '0', '+set', 'com_maxfps', '60',
                '+set', 'logfile', '2', '+set', 'developer', '1',
                '+set', 'com_introplayed', '1', '+exec', 'installed-menu-check.cfg']
        startup = subprocess.STARTUPINFO()
        startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        env = os.environ.copy()
        env['LOCALAPPDATA'] = str(run / 'local-app-data')
        process = subprocess.Popen(args, cwd=ROOT.parent, env=env, startupinfo=startup,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print('Checking installed menus:', renderer, process.pid, flush=True)
        try:
            process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait()
            raise
        logpath = mod / 'qconsole.log'
        log = logpath.read_text(errors='replace')
        assert process.returncode == 0, 'Installed client returned an error.'
        assert 'ST_INSTALLED_MENUS_COMPLETE' in log
        assert all(marker not in log for marker in ('SpawnServer', 'Server Initialization',
                   'API version mismatch', 'UI_API_VERSION', 'VM_Create on UI failed'))
        # Home contains no DLL or package: both the native UI and menu definitions
        # must come from the real regular installation (or stock base dependencies).
        assert not list(mod.glob('*.dll')) and not list(mod.glob('*.pk3'))
        screenshots = list((mod / 'screenshots').glob('installed-*.png'))
        assert len(screenshots) == 2 and all(p.stat().st_size > 10000 for p in screenshots)
        results[renderer] = {'exit_code': process.returncode, 'menu_only': True,
                             'log_sha256': installer.sha(logpath),
                             'screenshots': {p.name: installer.sha(p) for p in screenshots},
                             'engine_sha256': installer.sha(exe),
                             'ui_sha256': installer.sha(ROOT / 'uix86_64.dll')}
    installer.verify()
    (OUT / 'installed-verification.json').write_text(json.dumps({
        'passed': True, 'results': results,
        'installed_receipt_sha256': installer.sha(installer.STATE),
        'native_cgame_game_api_preserved': [219, 218],
        'live_gameplay_tested': False,
    }, indent=2))
    print('Installed Controls/Setup passed under Vanilla and Rend2; personal settings unchanged.')
