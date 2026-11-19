"""Install the accepted menus, preserving gameplay and every existing profile."""
from pathlib import Path
import argparse, datetime, hashlib, importlib.util, json, shutil, subprocess, sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist/controls-setup-release-01'
STATE = ROOT / 'dist/controls-setup-install.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def read(path):
    return json.loads(path.read_text())


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stopped():
    ids = subprocess.check_output(['powershell', '-NoProfile', '-Command',
        "Get-Process -Name 'SaberTrials.x86_64','openjk.x86_64','openjkded.x86_64','taystjk.x86_64','jamp','jampDed' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id; exit 0"], text=True)
    assert not ids.strip(), 'Close Jedi Academy/Saber Trials before installing.'


def settings():
    documents = subprocess.check_output(['powershell', '-NoProfile', '-Command',
        "[Environment]::GetFolderPath('MyDocuments')"], text=True).strip()
    folders = [ROOT, Path(documents) / 'My Games/OpenJK/SaberTrials',
               ROOT / 'dist/controls-candidate-01/playable/home/SaberTrialsControlsTest',
               ROOT / 'dist/setup-candidate-01/playable/home/SaberTrialsSetupTest']
    return {str(p): sha(p) for folder in folders for p in folder.glob('*.cfg') if p.is_file()}


def sources():
    result = {'client/SaberTrials.x86_64.exe': OUT / 'setup/build-engine/Release/openjk.x86_64.exe'}
    for name in ('uix86_64.dll', 'cgamex86_64.dll'):
        result[name] = OUT / 'setup/build-frontend/Release' / name
    result.update({p.relative_to(OUT / 'menus').as_posix(): p for p in (OUT / 'menus').rglob('*.menu')})
    result['zzzzzz_sabertrials_settings.pk3'] = OUT / 'zzzzzz_sabertrials_settings.pk3'
    return result


def verify():
    state = read(STATE)
    assert state['installed'] and not state.get('restored')
    for name, digest in {**state['protected'], **state['after']}.items():
        assert sha(ROOT / name) == digest, 'Installed/protected file changed: ' + name
    for path, digest in state['preserved_settings'].items():
        assert sha(Path(path)) == digest, 'Settings changed during installation: ' + path
    backup = Path(state['backup']).resolve()
    assert backup.is_relative_to((ROOT / 'dist/backups').resolve())
    for name, digest in state['before'].items():
        if digest is not None:
            assert sha(backup / name) == digest, 'Backup changed: ' + name
    assert sha(OUT / 'release-manifest.json') == state['release_manifest_sha256']
    print('Installed menus/native files, preserved gameplay/settings, and backups verified.')
    return state


def install():
    assert not STATE.exists(), 'Already installed; use --verify.'
    stopped()
    builder = load('release_builder', ROOT / 'tools/Build-Controls-Setup-Release.py')
    _, setup = builder.modules()
    builder.verify(setup)
    manifest = read(OUT / 'release-manifest.json')
    assert sha(setup.OUT / 'source-receipt.json') == manifest['source_sha256']
    old = read(ROOT / 'dist/hybrid-feedback-install.json')
    assert old['installed'] and not old.get('restored')
    for name, digest in old['after'].items():
        assert sha(ROOT / name) == digest, 'Installed baseline changed: ' + name
    for kind, files in manifest['builds'].items():
        for name, digest in files.items():
            assert sha(setup.OUT / ('build-' + kind) / 'Release' / name) == digest
    for rel, digest in manifest['menus'].items():
        assert sha(OUT / 'menus' / rel) == digest
    for rel, digest in manifest['package'].items():
        assert sha(OUT / rel) == digest
    mapping = sources()
    for name, path in mapping.items():
        if path.suffix in ('.exe', '.dll'):
            data = path.read_bytes()
            assert all(marker not in data for marker in (b'st_controlsqa', b'st_setupqa', b'st_controlskey'))
    for tag in ('release-menu', 'release-pause', 'release-layout', 'release-display'):
        log = (setup.OUT / 'verification' / tag / 'home/SaberTrials/qconsole.log').read_text(errors='replace')
        marker = 'ST_CONTROLS_COMPLETE' if tag == 'release-layout' else 'ST_SETUP_COMPLETE'
        assert marker in log and 'ST_SETUP_FAIL' not in log and 'ST_CONTROLS_FAIL' not in log
        assert 'SpawnServer' not in log and 'Server Initialization' not in log
    preserved = settings()
    # A home-directory native module would take priority over the mod installation.
    documents = subprocess.check_output(['powershell', '-NoProfile', '-Command',
        "[Environment]::GetFolderPath('MyDocuments')"], text=True).strip()
    home = Path(documents) / 'My Games/OpenJK/SaberTrials'
    assert not list(home.glob('*x86_64.dll')), 'Inspect home-directory native module overrides first.'
    assert not list((home / 'ui').rglob('*.menu')), 'Inspect personal menu overrides first.'
    protected = {}
    for folder in ('client', 'ui', 'server', 'models', 'scripts', 'sound', 'textures', 'fonts', 'ext_data'):
        for p in (ROOT / folder).rglob('*'):
            if p.is_file():
                rel = p.relative_to(ROOT).as_posix()
                if rel not in mapping:
                    protected[rel] = sha(p)
    for p in list(ROOT.glob('*.pk3')) + list(ROOT.glob('*.dll')) + list(ROOT.glob('Launch-*.cmd')):
        if p.name not in mapping:
            protected[p.name] = sha(p)
    before = {name: sha(ROOT / name) for name in mapping}
    after = {name: sha(path) for name, path in mapping.items()}
    for name in mapping:
        (ROOT / name).parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup = ROOT / 'dist/backups' / ('controls-setup-' + stamp)
    state = {'schema': 1, 'installed': True, 'restored': False, 'backup': str(backup),
             'before': before, 'after': after, 'protected': protected,
             'preserved_settings': preserved,
             'sources': {name: str(path) for name, path in mapping.items()},
             'release_manifest_sha256': sha(OUT / 'release-manifest.json'),
             'previous_receipt': 'dist/hybrid-feedback-install.json',
             'previous_receipt_sha256': sha(ROOT / 'dist/hybrid-feedback-install.json'),
             'gameplay_api': 218, 'cgame_api': 219, 'ui_api': 285,
             'gameplay_preserved': True, 'live_gameplay_tested': False}
    helper = load('menu_install_transaction', ROOT / 'tools/Install-Handedness.py')
    helper.install_transaction(ROOT, mapping, before, after, protected, backup, STATE, state)
    verify()


def retire():
    state = verify()
    assert read(OUT / 'installed-verification.json')['passed'], 'Verify installed startup first.'
    stopped()
    names = ['Play-SaberTrials-Controls-Test.cmd', 'Play-SaberTrials-Setup-Test.cmd',
             'dist/controls-candidate-01/playable/Launch-Controls-Test.ps1',
             'dist/setup-candidate-01/playable/Launch-Setup-Test.ps1']
    retired = {}
    for name in names:
        path = (ROOT / name).resolve()
        assert path.is_relative_to(ROOT.resolve()) and path.name in (
            'Play-SaberTrials-Controls-Test.cmd', 'Play-SaberTrials-Setup-Test.cmd',
            'Launch-Controls-Test.ps1', 'Launch-Setup-Test.ps1')
        if path.exists():
            digest = sha(path)
            saved = Path(state['backup']) / 'retired-launchers' / name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, saved)
            assert sha(saved) == digest
            path.unlink()
            retired[name] = digest
    assert all(not (ROOT / name).exists() for name in names)
    (OUT / 'retired-launchers.json').write_text(json.dumps({'removed': retired,
        'profiles_preserved': True, 'unrelated_launchers_preserved': True}, indent=2))
    print('Removed Controls/Setup test launchers; profiles and development sources retained.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['install', 'verify', 'retire-launchers'])
    args = parser.parse_args()
    {'install': install, 'verify': verify, 'retire-launchers': retire}[args.action]()
