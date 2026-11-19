"""Restore verified Saber Trials Windows sources without touching the game install."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from urllib.request import urlretrieve
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / 'development-source/windows-checkpoint'
PACKAGES = {
    'settings': 'zzzzzz_sabertrials_settings.pk3',
    'profile': 'zzzzzzz_sabertrials_profile.pk3',
    'main': 'zzzzzzzz_sabertrials_main.pk3',
    'rich': 'zzzzzzzzz_sabertrials_rich.pk3',
    'rollout': 'zzzzzzzzzz_sabertrials_rollout.pk3',
    'workbench': 'zzzzzzzzzzz_sabertrials_workbench.pk3',
    'crystals': 'zzzzzzzzzzzz_sabertrials_crystals.pk3',
    'hud_theme': 'zzzzzzzzzzzzz_sabertrials_hud_theme.pk3',
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def restore(archive, output, manifest):
    if sha256(archive.read_bytes()) != manifest['archive_sha256']:
        raise ValueError('OpenJK archive does not match the pinned checksum')

    upstream = output.parent / 'upstream'
    archive_root = 'OpenJK-' + manifest['upstream_revision']
    with ZipFile(archive) as source:
        for entry in source.infolist():
            if entry.is_dir():
                continue
            path = PurePosixPath(entry.filename)
            if not path.parts or path.parts[0] != archive_root or '..' in path.parts:
                raise ValueError(f'Unexpected archive path: {entry.filename}')
            destination = upstream.joinpath(*path.parts[1:])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read(entry))

    for role, data in manifest['roles'].items():
        destination = output / role
        shutil.copytree(upstream, destination)
        for name, expected in data['overlay'].items():
            content = (CHECKPOINT / role / name).read_bytes()
            if sha256(content) != expected:
                raise ValueError(f'Checkpoint checksum mismatch in {role}/{name}')
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        tree = {
            path.relative_to(destination).as_posix(): sha256(path.read_bytes())
            for path in destination.rglob('*') if path.is_file()
        }
        tree_hash = sha256(json.dumps(tree, sort_keys=True, separators=(',', ':')).encode('ascii'))
        if len(tree) != data['file_count'] or tree_hash != data['tree_sha256']:
            raise ValueError(f'Reconstructed source does not match the {role} checkpoint')
        print(f'{role}: verified {len(tree)} files')

    packages = output / 'packages'
    packages.mkdir()
    shutil.copy2(ROOT / 'z_sabertrials_studio_intro.pk3', packages)
    for label, name in PACKAGES.items():
        payload = ROOT / 'assets/runtime-packages' / label
        with ZipFile(packages / name, 'w', compression=ZIP_DEFLATED) as package:
            for path in sorted(payload.rglob('*')):
                if path.is_file():
                    package.write(path, path.relative_to(payload).as_posix())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Existing pinned OpenJK source ZIP')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/windows-checkpoint',
                        help='New directory for reconstructed sources and packages')
    args = parser.parse_args()
    destination = args.output.resolve()
    if destination.exists():
        parser.error(f'Output already exists: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((CHECKPOINT / 'manifest.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='st-checkpoint-', dir=destination.parent) as folder:
        work = Path(folder)
        archive = args.archive or work / 'openjk.zip'
        if args.archive is None:
            urlretrieve('https://codeload.github.com/JACoders/OpenJK/zip/'
                        + manifest['upstream_revision'], archive)
        restored = work / 'restored'
        restore(archive, restored, manifest)
        restored.rename(destination)
    print(f'Sources and runtime packages restored to {destination}')


if __name__ == '__main__':
    main()
