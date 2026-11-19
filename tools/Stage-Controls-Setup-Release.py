"""Stage only accepted menus and matching native binaries; never stage gameplay."""
from pathlib import Path
import hashlib, importlib.util, json, shutil, sys, zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist/controls-setup-release-01'
SETUP = OUT / 'setup'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    old = json.loads((ROOT / 'dist/hybrid-feedback-install.json').read_text())
    assert old['installed'] and not old.get('restored')
    for name, digest in old['after'].items():
        assert sha(ROOT / name) == digest, 'Installed baseline changed: ' + name
    menus = OUT / 'menus/ui/jamp'
    menus.mkdir(parents=True, exist_ok=True)
    for filename, name in [('controls', 'controlsMenu'), ('ingame_controls', 'ingame_controls'),
                           ('setup', 'setup_menu'), ('ingame_setup', 'ingame_setup')]:
        (menus / (filename + '.menu')).write_text(
            '{ menuDef { name "' + name + '" fullscreen 1 rect 0 0 640 480 visible 0 focusColor 1 1 1 1 } }\n')
    shutil.copy2(ROOT / 'development-source/setup/ingame.menu', menus / 'ingame.menu')
    package = OUT / 'zzzzzz_sabertrials_settings.pk3'
    with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(menus.glob('*.menu')):
            entry = zipfile.ZipInfo('ui/jamp/' + path.name, (2026, 11, 6, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, path.read_bytes())
    stage = SETUP / 'playable'
    files = {}

    def copy(source, rel):
        target = stage / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        files[rel] = sha(target)

    copy(SETUP / 'build-engine/Release/openjk.x86_64.exe', 'bin/SaberTrials.x86_64.exe')
    for name in ('SDL2.dll', 'OpenAL32.dll', 'rd-vanilla_x86_64.dll', 'rd-rend2_x86_64.dll'):
        copy(ROOT / 'client' / name, 'bin/' + name)
    for name in ('uix86_64.dll', 'cgamex86_64.dll'):
        copy(SETUP / 'build-frontend/Release' / name, 'home/SaberTrials/' + name)
    copy(package, 'home/SaberTrials/' + package.name)
    # No preview game DLL, animations, runtime package, or personal cfg is copied.
    manifest = {'schema': 1, 'installed': False, 'fs_game': 'SaberTrials',
                'baseline_install_sha256': sha(ROOT / 'dist/hybrid-feedback-install.json'),
                'source_sha256': sha(SETUP / 'source-receipt.json'),
                'files': files,
                'menus': {p.relative_to(OUT / 'menus').as_posix(): sha(p) for p in menus.glob('*.menu')},
                'package': {package.name: sha(package)},
                'builds': {kind + ('-qa' if qa else ''): {
                    name: sha(SETUP / ('build-' + kind + ('-qa' if qa else '')) / 'Release' / name)
                    for name in (['openjk.x86_64.exe'] if kind == 'engine' else ['uix86_64.dll', 'cgamex86_64.dll'])}
                    for qa in (False, True) for kind in ('engine', 'frontend')}}
    (OUT / 'release-manifest.json').write_text(json.dumps(manifest, indent=2))
    print('Menu-only release staged using the installed game assets; no launchers created.')


if __name__ == '__main__':
    main()
