"""Install the verified optional Vulkan client, preserving the current profile and gameplay."""
import argparse
from datetime import datetime
from importlib import import_module
from pathlib import Path
import zipfile

s = import_module('Stage-Vulkan')
b = s.b
h = import_module('Install-Profile-Browser')
t = import_module('Install-Handedness')
STATE = b.ROOT / 'dist/vulkan-install.json'


def sources():
    files = {
        'client/SaberTrials.x86_64.exe': s.PLAY / 'client/SaberTrials.x86_64.exe',
        'client/rd-vulkan_x86_64.dll': s.PLAY / 'client/rd-vulkan_x86_64.dll',
        'uix86_64.dll': s.PLAY / 'home/SaberTrials/uix86_64.dll',
    }
    for name in ('OpenJK-GPL-2.0.txt', 'Vulkan-upstream-credits.md',
                 'stb_dxt-source-and-BSD-license.h', 'Khronos-Vulkan-MIT.txt'):
        files['client/licenses/vulkan/' + name] = s.PLAY / 'licenses' / name
    return files


def candidate():
    record = s.verify()
    s.evidence()
    receipt = b.read(b.OUT / 'source-receipt.json')
    for role in ('engine', 'frontend'):
        assert b.tree(b.OUT / role) == receipt['sources'][role], 'Prepared source drift: ' + role
    baseline = Path(receipt['baseline'])
    assert b.sha(baseline / 'source-receipt.json') == receipt['baseline_receipt'], 'Browser baseline changed'
    for role in ('engine', 'frontend'):
        assert b.tree(baseline / role) == b.read(baseline / 'source-receipt.json')['sources'][role]
    for name, path in sources().items():
        staged = 'home/SaberTrials/uix86_64.dll' if name == 'uix86_64.dll' else name
        if staged in record['files']:
            assert b.sha(path) == record['files'][staged], 'Staged binary drift: ' + name
    license_sources = {
        'OpenJK-GPL-2.0.txt': b.UPSTREAM / 'LICENSE.txt',
        'Vulkan-upstream-credits.md': b.UPSTREAM / 'codemp/rd-vulkan/README.md',
        'stb_dxt-source-and-BSD-license.h': b.UPSTREAM / 'codemp/rd-vulkan/utils/stb_dxt.h',
        'Khronos-Vulkan-MIT.txt': b.ROOT / 'docs/licenses/Khronos-Vulkan-MIT.txt',
    }
    for name, source in license_sources.items():
        assert b.sha(s.PLAY / 'licenses' / name) == b.sha(source), 'License drift: ' + name
    data = (s.PLAY / 'home/SaberTrials/uix86_64.dll').read_bytes()
    assert not any(marker in data for marker in (b'st_controlsqa', b'st_setupqa', b'st_profileqa'))
    return record


def verify(check_settings=False):
    record = b.read(STATE)
    assert record['installed'] and not record.get('restored')
    for name, digest in {**record['protected'], **record['after']}.items():
        assert h.sha(b.ROOT / name) == digest, 'Installed/protected file changed: ' + name
    backup = Path(record['backup']).resolve()
    assert backup.is_relative_to((b.ROOT / 'dist/backups').resolve())
    for name, digest in record['before'].items():
        if digest is not None:
            assert b.sha(backup / name) == digest, 'Backup changed: ' + name
    if check_settings:
        assert h.settings()[1] == record['preserved_settings'], 'Saved settings changed'
    print('Installed Vulkan files, existing gameplay/renderers, and backups verified.', flush=True)
    return record


def install():
    assert not STATE.exists(), 'Installation receipt exists; use verify.'
    h.stopped()
    stage = candidate()
    # The installed browser update is part of this candidate's verified source baseline.
    previous = [b.ROOT / 'dist/worldwide-browser-install.json',
                b.ROOT / 'dist/worldwide-browser-region-install.json']
    expected = {}
    for path in previous:
        expected.update(b.read(path)['after'])
    assert b.read(previous[-1])['source_sha256'] == b.read(b.OUT / 'source-receipt.json')['baseline_receipt']
    for name, digest in expected.items():
        assert h.sha(b.ROOT / name) == digest, 'Installed browser baseline changed: ' + name
    # Every reused module must match the binaries exercised by the approved candidate.
    for staged, digest in stage['files'].items():
        name = staged.removeprefix('home/SaberTrials/')
        if name not in sources():
            assert h.sha(b.ROOT / name) == digest, 'Reused module changed: ' + name
    home, settings = h.settings()
    assert not list(home.glob('*x86_64.dll')), 'Inspect saved-profile DLL overrides before installing.'
    for folder in (home, b.ROOT, b.ROOT.parent / 'base'):
        for path in folder.glob('*.pk3'):
            with zipfile.ZipFile(path) as package:
                assert 'uix86_64.dll' not in {n.lower() for n in package.namelist()}, 'Packaged UI override: ' + str(path)
    mapping = sources()
    protected = {}
    paths = list(b.ROOT.glob('*.dll')) + list(b.ROOT.glob('*.pk3')) + list(b.ROOT.glob('*.cmd'))
    paths += list((b.ROOT / 'client').glob('*'))
    paths += list((b.ROOT / 'ui').rglob('*.menu')) + list((b.ROOT / 'tools/launchers').rglob('*.cmd'))
    for path in paths:
        name = path.relative_to(b.ROOT).as_posix()
        if path.is_file() and name not in mapping:
            protected[name] = b.sha(path)
    before = {name: h.sha(b.ROOT / name) for name in mapping}
    after = {name: b.sha(path) for name, path in mapping.items()}
    backup = b.ROOT / 'dist/backups' / ('vulkan-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    record = dict(installed=True, restored=False, installed_at=datetime.now().isoformat(),
        before=before, after=after, protected=protected, backup=str(backup),
        preserved_settings=settings, source=stage['source'],
        stage_receipt_sha256=b.sha(s.PLAY / 'stage-receipt.json'), checks=stage['checks'],
        previous_receipts={str(p): b.sha(p) for p in previous},
        sources={name: str(path) for name, path in mapping.items()},
        renderer_default_changed=False, gameplay_unchanged=True, dlss=False,
        post_install_validation=None)
    h.stopped()
    assert h.settings()[1] == settings, 'Settings changed during preflight'
    for name in mapping:
        (b.ROOT / name).parent.mkdir(parents=True, exist_ok=True)
    t.install_transaction(b.ROOT, mapping, before, after, protected, backup, STATE, record)
    verify(check_settings=True)
    print('Backup: ' + str(backup), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('check', 'install', 'verify'))
    args = parser.parse_args()
    {'check': candidate, 'install': install, 'verify': verify}[args.action]()
