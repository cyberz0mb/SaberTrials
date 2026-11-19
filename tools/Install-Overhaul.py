"""Install a verified local production build and package this incremental update."""
from pathlib import Path
import hashlib
import json
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
BUILD = Path(tempfile.gettempdir()) / 'SaberTrials-overhaul-20261003/build/Release'
VERSION = 'overhaul-20261003'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((BUILD / 'build-manifest.json').read_text())
    if manifest['kind'] != 'production':
        raise RuntimeError('Refusing to install a QA build')
    for name in ['openjk.x86_64.exe', 'uix86_64.dll']:
        data = (BUILD / name).read_bytes()
        if digest(BUILD / name) != manifest['files'][name]:
            raise RuntimeError('Build hash mismatch: ' + name)
        if any(marker in data for marker in [b'st_clientqa', b'st_engineqa']):
            raise RuntimeError('Test-only command found in production binary: ' + name)
    dependencies = ['SDL2.dll', 'OpenAL32.dll', 'rd-vanilla_x86_64.dll']
    for name in dependencies:
        if not (ROOT.parent / name).is_file():
            raise RuntimeError('Required installed OpenJK runtime is missing: ' + name)
    backup = ROOT / 'dist/backups' / VERSION
    backup.mkdir(parents=True, exist_ok=True)
    old_ui = ROOT / 'uix86_64.dll'
    if old_ui.exists() and not (backup / old_ui.name).exists():
        shutil.copy2(old_ui, backup / old_ui.name)
    client = ROOT / 'client'
    client.mkdir(exist_ok=True)
    shutil.copy2(BUILD / 'openjk.x86_64.exe', client / 'SaberTrials.x86_64.exe')
    for name in dependencies:
        shutil.copy2(ROOT.parent / name, client / name)
    shutil.copy2(BUILD / 'uix86_64.dll', old_ui)
    installed = {'version': VERSION, 'build': manifest, 'installed_files': {}}
    for path in [client / 'SaberTrials.x86_64.exe', old_ui] + [client / n for n in dependencies]:
        installed['installed_files'][path.relative_to(ROOT).as_posix()] = digest(path)
    (client / 'manifest.json').write_text(json.dumps(installed, indent=2) + '\n')
    # Incremental package: never sweep unrelated models, private configs, logs, or base assets.
    paths = [client / 'SaberTrials.x86_64.exe', old_ui, client / 'manifest.json',
             ROOT / 'Launch-SaberTrials-Overhaul.cmd', ROOT / 'LICENSE.txt', ROOT / 'CREDITS.txt',
             ROOT / 'tools/Build-Overhaul.py', ROOT / 'tools/Install-Overhaul.py',
             ROOT / 'tools/Test-Overhaul.py', ROOT / 'tests/test_rating.py',
             ROOT / 'tests/overhaul_ui_qa.inc', ROOT / 'tests/overhaul_engine_qa.inc',
             ROOT / 'docs/MATCH_RECORDING.md', ROOT / 'docs/OVERHAUL_PROGRESS.md',
             ROOT / 'development-source/client-overhaul/README.md',
             ROOT / 'development-source/bot-roles/codemp/ui/ui_sabertrials_menu.inc']
    paths += [ROOT / 'development-source/bot-roles/patches' / n for n in
              ['ui-built-in-character-roster.patch', 'ui-menu-controls.patch', 'ui-input-sliders.patch']]
    paths += sorted((ROOT / 'development-source/client-overhaul/patches').glob('*.patch'))
    paths += sorted(p for p in (ROOT / 'ui').rglob('*') if p.is_file())
    paths += sorted(p for p in (ROOT / 'services').rglob('*.py'))
    # Runtime DLLs already belong to the installed OpenJK; launcher also searches GameData.
    package = ROOT / 'dist' / ('SaberTrials-' + VERSION + '.zip')
    with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, 'SaberTrials/' + path.relative_to(ROOT).as_posix())
    (package.with_suffix('.zip.sha256')).write_text(digest(package) + '  ' + package.name + '\n')
    print('Installed verified production client/UI; backup:', backup)
    print('Packaged incremental update:', package)


if __name__ == '__main__':
    main()
