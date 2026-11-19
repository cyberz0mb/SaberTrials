"""Verify/package the native account bridge; never install or launch a game."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'dist/verification/account-bridge-20261023'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    build = ROOT / 'dist/staff-build/Release'
    manifest = json.loads((build / 'staff-build-manifest.json').read_text())
    inputs = module('bridge_build', 'tools/Build-Staff.py').input_hashes()
    if manifest['kind'] != 'production' or manifest['inputs'] != inputs:
        raise RuntimeError('Build is not production or source changed since compilation')
    protected = {}
    for folder in ('client', 'ui', 'gfx', 'menu', 'server'):
        for path in (ROOT / folder).rglob('*'):
            if path.is_file():
                protected[path.relative_to(ROOT).as_posix()] = sha(path)
    for name in ('jampgamex86_64.dll', 'cgamex86_64.dll', 'uix86_64.dll', 'server.cfg', 'staff-setup.cfg'):
        if (ROOT / name).is_file():
            protected[name] = sha(ROOT / name)
    for label, args in (
        ('accounts', ['ctest', '--test-dir', 'dist/account-native-tests', '-C', 'Release', '--output-on-failure']),
        ('staff', ['ctest', '--test-dir', 'dist/staff-build-tests', '-C', 'Release', '--output-on-failure']),
        ('tournament', ['ctest', '--test-dir', 'dist/tournament-tests', '-C', 'Release', '--output-on-failure']),
        ('service', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v']),
    ):
        with (EVIDENCE / (label + '.log')).open('w', encoding='utf-8') as output:
            subprocess.run(args, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT, check=True)
    files = {}
    for name, expected in manifest['files'].items():
        if sha(build / name) != expected:
            raise RuntimeError('Binary mismatch: ' + name)
        files['candidate/binaries/' + name] = build / name
    for name in inputs:
        files[name] = ROOT / name
    for folder in ('tests/accounts', 'tests/staff', 'tests/tournament', 'services/accounts', 'services/ranking'):
        for path in (ROOT / folder).rglob('*'):
            if path.is_file() and path.suffix in ('.py', '.c', '.cpp', '.h', '.inc', '.txt'):
                files[path.relative_to(ROOT).as_posix()] = path
    for path in (ROOT / 'tests').glob('test_*.py'):
        files[path.relative_to(ROOT).as_posix()] = path
    for name in ('LICENSE.txt', 'CREDITS.txt', 'docs/Account-Server-Bridge.md', 'docs/Account-Login.md',
                 'docs/Tournament-Mode.md', 'docs/Account-Service.md', 'tools/Package-Account-Bridge.py'):
        files[name] = ROOT / name
    for name in ('sodium.tar.gz', 'sqlite.zip'):
        files['dist/staff-deps/' + name] = ROOT / 'dist/staff-deps' / name
    upstream = ROOT / 'dist/staff-work/openjk.zip'
    if sha(upstream) != manifest['source_archive_sha256']:
        raise RuntimeError('Upstream source changed')
    files['source/OpenJK-' + manifest['source_revision'] + '.zip'] = upstream
    if inputs != module('bridge_recheck', 'tools/Build-Staff.py').input_hashes():
        raise RuntimeError('Inputs changed during verification')
    if any(sha(ROOT / name) != expected for name, expected in protected.items()):
        raise RuntimeError('Installed assets changed during packaging')
    report = dict(status='Windows development candidate; not installed',
                  game_or_server_launched=False, real_multiplayer_verified=False,
                  native_build=manifest, protected_installed_files=protected,
                  checks=dict(accounts=5, staff=7, tournament=10, backend=90),
                  files={name: sha(path) for name, path in sorted(files.items())})
    archive = ROOT / 'dist/SaberTrials-account-bridge-development-20261023.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, path in sorted(files.items()):
            z.write(path, name)
        z.writestr('bridge-manifest.json', json.dumps(report, indent=2) + '\n')
    with zipfile.ZipFile(archive) as z:
        if z.testzip() or len(z.namelist()) != len(files) + 1:
            raise RuntimeError('Archive integrity failure')
        for name, expected in report['files'].items():
            if hashlib.sha256(z.read(name)).hexdigest() != expected:
                raise RuntimeError('Archive hash mismatch: ' + name)
    report['archive'] = archive.name
    report['archive_sha256'] = sha(archive)
    (EVIDENCE / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    archive.with_suffix('.zip.sha256').write_text(sha(archive) + '  ' + archive.name + '\n')
    print('112 automated checks passed; candidate contents and installed-file preservation verified.')
    print(archive.name)


if __name__ == '__main__':
    main()
