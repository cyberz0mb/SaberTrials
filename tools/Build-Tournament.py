"""Build/test/stage a development candidate; never run or install the game."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'dist/tournament-staging'
BUILD = ROOT / 'dist/staff-build/Release'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args):
    subprocess.run([str(arg) for arg in args], cwd=ROOT, check=True)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def installed_hashes():
    names = ['client/SaberTrials.x86_64.exe', 'jampgamex86_64.dll', 'cgamex86_64.dll',
             'ui/jamp/main.menu', 'ui/jamp/ingame.menu', 'ui/jamp/ingame_player.menu']
    return {name: sha(ROOT / name) for name in names if (ROOT / name).is_file()}


def main():
    before = installed_hashes()
    run(sys.executable, 'tools/Build-Staff.py')
    run('cmake', '-S', 'tests/tournament', '-B', 'dist/tournament-tests',
        '-G', 'Visual Studio 18 2026', '-A', 'x64')
    run('cmake', '--build', 'dist/tournament-tests', '--config', 'Release', '--parallel', '6')
    run('ctest', '--test-dir', 'dist/tournament-tests', '-C', 'Release', '--output-on-failure')
    run(sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v')
    run(sys.executable, 'tools/Stage-Tournament.py')

    native = json.loads((BUILD / 'staff-build-manifest.json').read_text())
    if native['inputs'] != load('staff_build', 'tools/Build-Staff.py').input_hashes():
        raise RuntimeError('Source changed after compilation')
    menus = json.loads((STAGE / 'menu-manifest.json').read_text())
    files = {}
    for name, expected in native['files'].items():
        path = BUILD / name
        if sha(path) != expected:
            raise RuntimeError('Build output hash mismatch: ' + name)
        files['candidate/binaries/' + name] = path
    for name, expected in menus['files'].items():
        path = STAGE / name
        if sha(path) != expected or sha(ROOT / name) != menus['originals'][name]:
            raise RuntimeError('Menu staging hash mismatch: ' + name)
        files['candidate/' + name] = path
    files['README.md'] = ROOT / 'docs/Tournament-Mode.md'
    files['templates/tournament-preview.cfg'] = ROOT / 'templates/tournament-preview.cfg'
    files['LICENSE.txt'] = ROOT / 'LICENSE.txt'
    for folder in ('bot-roles', 'client-game', 'client-overhaul', 'staff', 'accounts'):
        for path in (ROOT / 'development-source' / folder).rglob('*'):
            if path.is_file() and path.suffix not in ('.pyc', '.tmp', '.bak'):
                files[path.relative_to(ROOT).as_posix()] = path
    for folder in ('tests/tournament', 'tests/staff', 'services/ranking'):
        for path in (ROOT / folder).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                files[path.relative_to(ROOT).as_posix()] = path
    for path in (ROOT / 'tests').glob('test_*.py'):
        files[path.relative_to(ROOT).as_posix()] = path
    for name in ('Build-Tournament.py', 'Build-Staff.py', 'Build-Overhaul.py', 'Stage-Tournament.py'):
        files['tools/' + name] = ROOT / 'tools' / name
    after = installed_hashes()
    if before != after:
        raise RuntimeError('Installed game/menu files changed while building')
    manifest = {
        'status': 'development candidate - not installed',
        'account_service': 'browser login verified; native server connection binding pending',
        'runtime_tested': False,
        'game_or_server_launched': False,
        'installed_before': before,
        'installed_after': after,
        'native_build': native,
        'files': {name: sha(path) for name, path in sorted(files.items())},
    }
    manifest_bytes = (json.dumps(manifest, indent=2) + '\n').encode()
    (STAGE / 'candidate-manifest.json').write_bytes(manifest_bytes)
    package = ROOT / 'dist/SaberTrials-tournament-development-20261022.zip'
    with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, path in sorted(files.items()):
            archive.write(path, name)
        archive.writestr('candidate-manifest.json', manifest_bytes)
    with zipfile.ZipFile(package) as archive:
        if len(archive.namelist()) != len(files) + 1:
            raise RuntimeError('Unexpected package entries')
        for name, expected in manifest['files'].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise RuntimeError('Package content mismatch: ' + name)
    package.with_suffix('.zip.sha256').write_text(sha(package) + '  ' + package.name + '\n')
    print('Development candidate verified. Installed game and menus unchanged.')
    print(package)


if __name__ == '__main__':
    main()
