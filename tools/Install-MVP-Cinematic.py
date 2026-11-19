"""Promote the accepted local cinematic build into the regular Saber Trials client."""
from pathlib import Path
import argparse
import datetime
import hashlib
import importlib.util
import json
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist/mvp-cinematic-candidate-03'
STATE = ROOT / 'dist/mvp-cinematic-install.json'
LAUNCHERS = ('tools/launchers/SaberTrials.cmd',)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    if not path.is_file():
        return None
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def personal_home():
    documents = subprocess.check_output(['powershell', '-NoProfile', '-Command',
        "[Environment]::GetFolderPath('MyDocuments')"], text=True).strip()
    return Path(documents) / 'My Games/OpenJK/SaberTrials'


def stopped():
    running = subprocess.check_output(['powershell', '-NoProfile', '-Command',
        "Get-Process -Name 'SaberTrials.x86_64','openjk.x86_64','openjkded.x86_64',"
        "'jamp','jampDed' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id; exit 0"], text=True)
    assert not running.strip(), 'Close the running game before installation.'


def build_server():
    """The shared game API also needs a matching dedicated executable."""
    builder = load('mvp_server_build', ROOT / 'tools/Build-MVP-Cinematic.py')
    candidate = builder.verify()
    flags = load('mvp_build_flags', ROOT / 'tools/Prepare-Handedness-Baseline.py').FLAGS
    folder = OUT / 'build-server'
    commands = [
        ['cmake', '-S', str(OUT / 'engine'), '-B', str(folder), '-G', 'Visual Studio 18 2026', '-A', 'x64',
         '-DST_DEPS=' + str(ROOT / 'dist/handedness-baseline-06/deps'), '-DST_STAFF_QA=OFF'] +
        ['-D' + flag + '=' + ('ON' if flag == 'BuildMPDed' else 'OFF') for flag in flags],
        ['cmake', '--build', str(folder), '--config', 'Release', '--parallel', '6'],
    ]
    log = OUT / 'build-server.log'
    with log.open('w', encoding='utf-8') as output:
        for command in commands:
            subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, check=True)
    builder.verify()
    binary = folder / 'Release/openjkded.x86_64.exe'
    assert binary.is_file()
    builder.write(OUT / 'server-build.json', dict(binary_sha256=sha(binary),
        sources=candidate['sources']['engine'], candidate_manifest_sha256=sha(OUT / 'manifest.json')))
    return binary


def complete_server():
    """Finish an earlier client promotion without replacing its accepted bytes."""
    state = verify(settings=True)
    if 'client/openjkded.x86_64.exe' in state['after']:
        print('The matching cinematic client and server are already installed.')
        return
    stopped()
    binary = build_server()
    stopped()
    transaction = load('mvp_server_transaction', ROOT / 'tools/Install-Handedness.py')
    name = 'client/openjkded.x86_64.exe'
    before = {name: sha(ROOT / name)}
    after = {name: sha(binary)}
    backup = Path(state['backup'])
    protected = {**state['protected'], **state['after']}
    protected.pop(name)
    server_backup = ROOT / 'dist/backups' / ('mvp-server-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    server_state = ROOT / 'dist/mvp-server-compat-install.json'
    transaction.install_transaction(ROOT, {name: binary}, before, after, protected,
        server_backup, server_state, dict(installed=True, before=before, after=after,
            backup=str(server_backup), build_receipt_sha256=sha(OUT / 'server-build.json')))
    # Consolidate the verified original executable into the main rollback set.
    import shutil
    saved = backup / name
    saved.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(server_backup / name, saved)
    assert sha(saved) == before[name]
    transaction.atomic_record(backup / 'client-install-receipt.json', state)
    state['before'].update(before)
    state['after'].update(after)
    state['sources'][name] = str(binary)
    state['protected'].pop(name)
    state['server_build_sha256'] = sha(OUT / 'server-build.json')
    transaction.atomic_record(STATE, state)
    verify(settings=True)
    print('Installed matching dedicated server; shared game API is consistent.')


def verify(settings=False):
    state = read(STATE)
    assert state['installed'] and not state.get('restored')
    for name, digest in {**state['protected'], **state['after']}.items():
        assert sha(ROOT / name) == digest, 'Installed/protected file changed: ' + name
    for name, digest in state['before'].items():
        assert sha(Path(state['backup']) / name) == digest, 'Backup changed: ' + name
    if settings:
        for name, digest in state['preserved_settings'].items():
            assert sha(Path(name)) == digest, 'Personal settings changed: ' + name
    candidate=Path(state.get('candidate',ROOT/'dist/mvp-cinematic-candidate-01'))
    assert sha(candidate / 'manifest.json') == state['candidate_manifest_sha256']
    if state.get('server_build_sha256'):
        assert sha(candidate / 'server-build.json') == state['server_build_sha256']
        assert read(candidate / 'server-build.json')['binary_sha256'] == state['after']['client/openjkded.x86_64.exe']
    for name in LAUNCHERS:
        data = (ROOT / name).read_text()
        assert '+set st_mvpPrototype 1 +set st_mvpTestSingleSaber 0' in data
    return state


def install():
    if STATE.exists():
        complete_server()
        return
    stopped()
    builder = load('mvp_build', ROOT / 'tools/Build-MVP-Cinematic.py')
    candidate = builder.verify()
    assert set(candidate['builds']) == {'engine', 'game', 'frontend'}
    evidence = {}
    for name in ('winner-duel-06', 'winner-series-02', 'winner-match-final-01',
                 'winner-champion-final-01', 'winner-forfeit-final-01',
                 'winner-disconnect-final-01', 'winner-suicide-final-01',
                 'winner-ffa-regression-01'):
        folder = OUT / 'qa' / name
        result = read(folder / 'result.json')
        assert result['returncode'] == 0, 'Native check failed: ' + name
        staged = read(folder / 'stage-receipt.json')['files']
        for kind, binary, relative in (
            ('engine', 'openjk.x86_64.exe', 'bin/SaberTrials.x86_64.exe'),
            ('game', 'jampgamex86_64.dll', 'home/SaberTrials/jampgamex86_64.dll'),
            ('frontend', 'cgamex86_64.dll', 'home/SaberTrials/cgamex86_64.dll')):
            assert staged[relative] == candidate['builds'][kind][binary], 'Stale native check: ' + name
        evidence[name] = sha(folder / 'result.json')
    home = personal_home()
    assert not list(home.glob('*x86_64.dll')), 'Inspect personal native-module overrides first.'
    assert not (home / 'ui/assets/sabertrials/mvp').exists(), 'Inspect personal cinematic art overrides first.'
    preserved = {str(p): sha(p) for folder in (ROOT, home) for p in folder.glob('*.cfg')}
    files = {
        'client/SaberTrials.x86_64.exe': OUT / 'build-engine/Release/openjk.x86_64.exe',
        'jampgamex86_64.dll': OUT / 'build-game/Release/jampgamex86_64.dll',
        'cgamex86_64.dll': OUT / 'build-frontend/Release/cgamex86_64.dll',
        'client/openjkded.x86_64.exe': build_server(),
    }
    for name in ('rd-vanilla_x86_64.dll', 'rd-rend2_x86_64.dll'):
        files['client/' + name] = OUT / 'build-engine/Release' / name
    files.update({name: OUT / 'assets' / name for name in candidate['assets']})
    staged = OUT / 'installation'
    staged.mkdir(exist_ok=True)
    for name in LAUNCHERS:
        original = (ROOT / name).read_bytes()
        anchor = b'+set sv_pure 0'
        assert original.count(anchor) == 1
        if b'st_mvpPrototype' in original:
            assert b'+set st_mvpPrototype 1 +set st_mvpTestSingleSaber 0' in original
            updated = original
        else:
            updated = original.replace(anchor, anchor + b' +set st_mvpPrototype 1 +set st_mvpTestSingleSaber 0')
        (staged / name).parent.mkdir(parents=True, exist_ok=True)
        (staged / name).write_bytes(updated)
        files[name] = staged / name
    protected = {}
    for folder in ('client', 'ui', 'server', 'models', 'scripts', 'sound', 'textures', 'fonts', 'ext_data'):
        for path in (ROOT / folder).rglob('*'):
            if path.is_file():
                name = path.relative_to(ROOT).as_posix()
                if name not in files:
                    protected[name] = sha(path)
    for pattern in ('*.pk3', '*.dll', '*.cfg', '*SaberTrials*.cmd'):
        for path in ROOT.glob(pattern):
            if path.name not in files:
                protected[path.name] = sha(path)
    before = {name: sha(ROOT / name) for name in files}
    after = {name: sha(source) for name, source in files.items()}
    for name in files:
        (ROOT / name).parent.mkdir(parents=True, exist_ok=True)
    backup = ROOT / 'dist/backups' / ('mvp-cinematic-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    state = dict(schema=1, installed=True, restored=False, before=before, after=after,
                 protected=protected, preserved_settings=preserved, backup=str(backup),
                 candidate_manifest_sha256=sha(OUT / 'manifest.json'), evidence=evidence,
                 sources={name: str(path) for name, path in files.items()},
                 game_api=237, cgame_api=236, ui_api=285,
                 server_build_sha256=sha(OUT / 'server-build.json'),
                 scope='Accepted local FFA/Duel/legacy 1v1 replay; remote/custom-model support pending')
    transaction = load('mvp_transaction', ROOT / 'tools/Install-Handedness.py')
    transaction.install_transaction(ROOT, files, before, after, protected, backup, STATE, state)
    verify(settings=True)
    builder.verify()
    print('Installed matching client/server, renderers, game modules, 12 art assets and the main launcher.')
    print('Existing UI, packages, settings and unrelated launchers preserved. Backup:', backup)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'verify'))
    args = parser.parse_args()
    if args.action == 'install':
        install()
    else:
        verify(settings=True)
        print('Installed cinematic files, backups and preserved settings verified.')
