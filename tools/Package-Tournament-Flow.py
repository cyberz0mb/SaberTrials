"""Package verified matching tournament modules and menus; never install or launch JKA."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT/'dist/verification/tournament-ui-20261023'
BUILD = ROOT/'dist/staff-build/Release'
STAGE = ROOT/'dist/tournament-staging'
ARCHIVE = ROOT/'dist/SaberTrials-tournament-player-flow-20261023.zip'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_checks():
    counts = {}
    for name, count in [('account', 5), ('staff', 7), ('tournament', 12)]:
        log = (EVIDENCE/(name+'-tests.log')).read_text()
        if not re.search(r'100% tests passed(?:, 0 tests failed)? out of '+str(count)+r'\b', log):
            raise RuntimeError('Windows checks incomplete: '+name)
        counts['windows_'+name] = count
    for name, count in [('linux', 1), ('accounts', 5), ('staff', 7), ('tournament', 12)]:
        log = (EVIDENCE/'linux'/(name+'-test.log')).read_text()
        if f'100% tests passed, 0 tests failed out of {count}' not in log:
            raise RuntimeError('Linux checks incomplete: '+name)
        counts['linux_'+name] = count
    log = (EVIDENCE/'python-tests.log').read_text()
    if 'Ran 92 tests' not in log or not re.search(r'^OK\s*$', log, re.M):
        raise RuntimeError('Python checks incomplete')
    counts['python'] = 92
    return counts


def main():
    counts = verify_checks()
    native = json.loads((BUILD/'staff-build-manifest.json').read_text())
    inputs = load('flow_build', 'tools/Build-Staff.py').input_hashes()
    if native['kind'] != 'production' or native['inputs'] != inputs:
        raise RuntimeError('Windows source changed since production build')
    linux = json.loads((EVIDENCE/'linux/artifacts.json').read_text())
    if linux['game_server_started'] or not linux['source_matches']:
        raise RuntimeError('Linux verification incomplete')
    sources = json.loads((ROOT/'dist/linux-tooling/source-manifest.json').read_text())
    for name, expected in sources['inputs'].items():
        if sha(ROOT/name) != expected:
            raise RuntimeError('Linux source changed: '+name)
    protected = json.loads((EVIDENCE/'installed-before.json').read_text())
    for name, expected in protected.items():
        if sha(ROOT/name) != expected:
            raise RuntimeError('Installed file changed: '+name)
    menus = json.loads((STAGE/'menu-manifest.json').read_text())
    files = {}
    for name, expected in native['files'].items():
        if sha(BUILD/name) != expected:
            raise RuntimeError('Windows artifact changed: '+name)
        destination = 'client/SaberTrials.x86_64.exe' if name == 'openjk.x86_64.exe' else name
        files['candidate/windows/'+destination] = BUILD/name
    for name, info in linux['artifacts'].items():
        path = ROOT/'dist/tournament-ui-linux-release'/name
        if sha(path) != info['sha256']:
            raise RuntimeError('Linux artifact changed: '+name)
        destination = 'SaberTrials/'+name if name.endswith('.so') else name
        files['candidate/linux/'+destination] = path
    for name, expected in menus['files'].items():
        if sha(STAGE/name) != expected or sha(ROOT/name) != menus['originals'][name]:
            raise RuntimeError('Staged menu or original changed: '+name)
        files['candidate/menus/'+name] = STAGE/name
    for name in inputs:
        files[name] = ROOT/name
    for folder in ('tests/accounts', 'tests/staff', 'tests/tournament', 'tests/linux', 'services/accounts', 'services/ranking'):
        for path in (ROOT/folder).rglob('*'):
            if path.is_file() and path.suffix in ('.py', '.c', '.cpp', '.h', '.inc', '.txt', '.json'):
                files[path.relative_to(ROOT).as_posix()] = path
    for path in (ROOT/'tests').glob('test_*.py'):
        files[path.relative_to(ROOT).as_posix()] = path
    for name in ('LICENSE.txt', 'CREDITS.txt', 'docs/Tournament-Player-Flow.md', 'docs/Tournament-Mode.md',
                 'docs/Account-Login.md', 'docs/Account-Server-Bridge.md', 'docs/Linux-Server-Upload.md',
                 'docs/Asutech-Installation.md', 'tools/Stage-Tournament.py', 'tools/Preview-Tournament.py',
                 'tools/Package-Tournament-Flow.py', 'tools/Build-Linux-Server.py', 'tools/build-linux-server.sh',
                 'tools/Verify-Linux-Artifacts.py'):
        files[name] = ROOT/name
    files['READ-ME-FIRST.md'] = ROOT/'docs/Tournament-Player-Flow.md'
    files['preview/index.html'] = ROOT/'dist/tournament-ui-preview/index.html'
    files['preview/lobby-layout.png'] = ROOT/'dist/tournament-ui-preview/lobby-layout.png'
    upstream = ROOT/'dist/staff-work/openjk.zip'
    if sha(upstream) != native['source_archive_sha256']:
        raise RuntimeError('Pinned upstream archive changed')
    files['source/OpenJK-'+native['source_revision']+'.zip'] = upstream
    files['source/SaberTrials-linux-source.tar.gz'] = ROOT/'dist/linux-tooling/source.tar.gz'
    for name in ('sodium.tar.gz', 'sqlite.zip'):
        files['dist/staff-deps/'+name] = ROOT/'dist/staff-deps'/name
    files['verification/windows-build-manifest.json'] = BUILD/'staff-build-manifest.json'
    files['verification/linux-source-manifest.json'] = ROOT/'dist/linux-tooling/source-manifest.json'
    files['verification/menu-manifest.json'] = STAGE/'menu-manifest.json'
    for name in ('production-build.log', 'tournament-build.log', 'tournament-tests.log', 'account-tests.log',
                 'staff-tests.log', 'python-tests.log', 'installed-before.json', 'review.md'):
        files['verification/'+name] = EVIDENCE/name
    for path in (EVIDENCE/'linux').glob('*'):
        if path.suffix in ('.log', '.json'):
            files['verification/linux/'+path.name] = path
    contents = {name: sha(path) for name, path in sorted(files.items())}
    report = dict(status='Development update; not installed', game_or_server_launched=False,
                  real_multiplayer_verified=False, hosted_servers_changed=False, checks=counts,
                  protected_installed_files_verified=len(protected), files=contents)
    generated = {'manifest.json': (json.dumps(report, indent=2)+'\n').encode(),
                 'SHA256SUMS.txt': ''.join(h+'  '+n+'\n' for n, h in contents.items()).encode()}
    with zipfile.ZipFile(ARCHIVE, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, path in sorted(files.items()):
            item = zipfile.ZipInfo(name)
            item.create_system = 3
            item.compress_type = zipfile.ZIP_DEFLATED
            executable = name.endswith('.sh') or name == 'candidate/linux/openjkded.x86_64'
            item.external_attr = (stat.S_IFREG | (0o755 if executable else 0o644)) << 16
            archive.writestr(item, path.read_bytes())
        for name, content in generated.items():
            archive.writestr(name, content)
    with zipfile.ZipFile(ARCHIVE) as archive:
        if archive.testzip() or set(archive.namelist()) != set(files)|set(generated):
            raise RuntimeError('Package integrity failure')
        for name, expected in contents.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise RuntimeError('Package hash mismatch: '+name)
    if any(sha(ROOT/name) != expected for name, expected in protected.items()):
        raise RuntimeError('Installed files changed during packaging')
    report['archive_sha256'] = sha(ARCHIVE)
    (EVIDENCE/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    ARCHIVE.with_suffix('.zip.sha256').write_text(report['archive_sha256']+'  '+ARCHIVE.name+'\n')
    print(f'Verified {len(files)} packaged files, {sum(counts.values())} automated tests/suites, '
          f'and {len(protected)} unchanged installed files.')
    print(ARCHIVE)


if __name__ == '__main__':
    main()
