"""Convert the supplied studio ident to a native, skippable JKA startup movie."""
import argparse
from datetime import datetime
from importlib import import_module
from pathlib import Path
import hashlib
import json
import shutil
import struct
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZipFile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist/studio-intro-01'
PACKAGE = 'z_sabertrials_studio_intro.pk3'
RECEIPT = OUT / 'source-receipt.json'
STATE = ROOT / 'dist/studio-intro-install.json'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def movie_info(path):
    data = Path(path).read_bytes()
    magic, sentinel, fps = struct.unpack_from('<HIH', data)
    assert magic == 0x1084 and sentinel == 0xFFFFFFFF and fps == 30
    offset, frames, audio = 8, 0, 0
    width = height = 0
    while offset < len(data):
        kind, length, flags = struct.unpack_from('<HIH', data, offset)
        offset += 8
        assert length <= 65528 and offset + length <= len(data), 'Invalid native cinematic chunk'
        if kind == 0x1001:
            width, height = struct.unpack_from('<HH', data, offset)
        elif kind == 0x1011:
            frames += 1
        elif kind == 0x1021:
            audio += length // 2
        else:
            assert kind == 0x1002, 'Unexpected native cinematic chunk'
        offset += length
    assert (width, height) == (512, 512), 'Native cinematic buffer dimensions exceeded'
    assert 119 <= frames <= 123 and 3.9 <= audio / 22050 <= 4.2
    return dict(width=width, height=height, frames=frames, fps=fps,
                duration=frames / fps, audio_rate=22050, audio_channels=2,
                audio_duration=audio / 22050, display_aspect='16:9')


def prepare(source):
    source = Path(source).resolve(strict=True)
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, OUT / 'source.mp4')
    sys.path.insert(0, str(ROOT / 'dist/video-review-tools'))
    ffmpeg = import_module('imageio_ffmpeg').get_ffmpeg_exe()
    # The stock player stretches its square texture to the fullscreen viewport.
    # Encode the complete frame anamorphically for the normal 16:9 game display.
    command = [ffmpeg, '-hide_banner', '-y', '-i', str(OUT / 'source.mp4'),
               '-map', '0:v:0', '-map', '0:a:0', '-vf',
               'scale=512:512:flags=lanczos,setsar=1', '-r', '30',
               '-c:v', 'roqvideo', '-b:v', '8000000',
               '-c:a', 'roq_dpcm', '-ar', '22050', '-ac', '2', str(OUT / 'openinglogos.roq')]
    with (OUT / 'encode.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=log, check=True)
    info = movie_info(OUT / 'openinglogos.roq')
    with ZipFile(OUT / PACKAGE, 'w', compression=ZIP_DEFLATED) as archive:
        archive.write(OUT / 'openinglogos.roq', 'video/openinglogos.roq')
    write(RECEIPT, dict(source=str(source), original_sha256=sha(source),
                       copied_sha256=sha(OUT / 'source.mp4'), ffmpeg_sha256=sha(ffmpeg),
                       command=command, movie=info, movie_sha256=sha(OUT / 'openinglogos.roq'),
                       package_sha256=sha(OUT / PACKAGE), builder_sha256=sha(__file__)))
    print('Prepared studio intro with stereo audio.', flush=True)


def install():
    assert not STATE.exists(), 'Installation already recorded'
    helper = import_module('Install-Profile-Browser')
    helper.stopped()
    receipt = read(RECEIPT)
    assert receipt['builder_sha256'] == sha(__file__), 'Intro build recipe changed'
    assert sha(OUT / PACKAGE) == receipt['package_sha256']
    assert sha(OUT / 'source.mp4') == receipt['original_sha256']
    evidence = {}
    for name in ('rd-vanilla', 'rd-rend2', 'rd-vulkan', 'startup', 'skip'):
        result = OUT / 'checks' / name / 'result.json'
        report = read(result)
        assert report['passed'] and report['package'] == receipt['package_sha256']
        assert report['executable'] == sha(ROOT / 'client/SaberTrials.x86_64.exe')
        evidence[name] = dict(path=str(result), sha256=sha(result))
    home, settings = helper.settings()
    protected = {p.relative_to(ROOT).as_posix(): sha(p)
                 for p in list(ROOT.glob('*.dll')) + list(ROOT.glob('*.pk3')) + list((ROOT / 'client').glob('*'))
                 if p.is_file() and p.name != PACKAGE}
    before = {PACKAGE: helper.sha(ROOT / PACKAGE)}
    after = {PACKAGE: sha(OUT / PACKAGE)}
    backup = ROOT / 'dist/backups' / ('studio-intro-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    state = dict(installed=True, before=before, after=after, protected=protected,
                 source_sha256=sha(RECEIPT), preserved_settings=settings,
                 backup=str(backup), evidence=evidence)
    import_module('Install-Handedness').install_transaction(
        ROOT, {PACKAGE: OUT / PACKAGE}, before, after, protected, backup, STATE, state)
    assert settings == helper.settings()[1]
    print('Installed studio intro before the main menu.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'install'))
    parser.add_argument('--source', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        assert args.source is not None, 'Supply --source with the approved MP4'
        prepare(args.source)
    else:
        install()
