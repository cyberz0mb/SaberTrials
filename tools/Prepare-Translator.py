"""Prepare the selected offline runtime, language models and fonts."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import shutil
import subprocess
import ssl
from urllib.error import URLError
from urllib.request import Request, urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'development-source/translator'
OUT = ROOT / 'dist/translator-02'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def extract(archive, destination):
    with ZipFile(archive) as package:
        for info in package.infolist():
            name = PurePosixPath(info.filename)
            if name.is_absolute() or '..' in name.parts or '\\' in info.filename or ':' in info.filename:
                raise ValueError('Unsafe archive path')
            if not info.is_dir():
                path = destination.joinpath(*name.parts)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(package.read(info))


def prepare(download=False):
    lock = json.loads((SOURCE / 'dependencies.json').read_text())
    for entry in lock['files']:
        path = OUT / 'downloads' / entry['file']
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            if not download:
                raise ValueError('Missing dependency; use --download: ' + entry['file'])
            request = Request(entry['url'], headers={'User-Agent': 'ArgosTranslate/1.9'})
            try:
                with urlopen(request, timeout=60) as response, path.with_suffix('.part').open('wb') as target:
                    shutil.copyfileobj(response, target)
            except URLError as error:
                if not isinstance(error.reason,ssl.SSLCertVerificationError):raise
                # Windows curl uses the OS trust store; certificate checks stay enabled.
                subprocess.run(['curl.exe','--fail','--location','--silent','--show-error','--output',str(path.with_suffix('.part')),entry['url']],check=True)
            path.with_suffix('.part').rename(path)
        if path.stat().st_size != entry['bytes'] or sha(path) != entry['sha256']:
            raise ValueError('Dependency checksum mismatch: ' + entry['file'])
    runtime = OUT / 'runtime'
    runtime.mkdir(exist_ok=True)
    for entry in lock['files']:
        archive = OUT / 'downloads' / entry['file']
        if entry['kind'] == 'python':
            extract(archive, runtime)
            (runtime / 'python314._pth').write_text('python314.zip\n.\nLib/site-packages\nimport site\n')
        elif entry['kind'] == 'wheel':
            extract(archive, runtime / 'Lib/site-packages')
        elif entry['kind'] == 'font':
            target = runtime / entry['file']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(archive, target)
        elif entry['kind'] in ('model','marian'):
            target = runtime / 'models' / entry['pair']
            if entry['kind']=='marian':
                extracted=OUT/'marian-source'/entry['pair']
                # Extract only data needed by the converter, never upstream shell scripts.
                with ZipFile(archive) as package:
                    for info in package.infolist():
                        name=PurePosixPath(info.filename)
                        if name.is_absolute() or '..' in name.parts or len(name.parts)!=1:raise ValueError('Unsafe Marian path')
                        if name.suffix not in ('.npz','.yml','.spm') and str(name) not in ('README.md','LICENSE'):continue
                        extracted.mkdir(parents=True,exist_ok=True);(extracted/str(name)).write_bytes(package.read(info))
                # Preserve the superseded local prototype before replacing its different format.
                if (target/'sentencepiece.model').exists():
                    backup=OUT/'superseded-models'/entry['pair']
                    assert target.resolve().is_relative_to(runtime.resolve()) and not backup.exists()
                    backup.parent.mkdir(exist_ok=True);target.rename(backup)
                subprocess.run([str(runtime/'python.exe'),'-I','-B',str(ROOT/'tools/Convert-Translator-Marian.py'),str(extracted),str(target)],check=True)
            else:
              with ZipFile(archive) as package:
                for info in package.infolist():
                    if info.is_dir():
                        continue
                    parts = PurePosixPath(info.filename).parts
                    if '..' in parts or len(parts) < 2:
                        raise ValueError('Unsafe model path')
                    relative = PurePosixPath(*parts[1:])
                    if relative.parts[0] != 'model' and str(relative) not in ('sentencepiece.model', 'bpe.model', 'README.md', 'metadata.json'):
                        continue  # Chat does not need the bundled sentence-segmentation models.
                    if relative.suffix not in ('.bin', '.json', '.model', '.txt', '.md'):
                        raise ValueError('Model pack contains executable content')
                    dest = target / relative
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(package.read(info))
            write(target / 'manifest.json', dict(version=1, source=entry['pair'][:2], target=entry['pair'][3:],
                tokenizer='sentencepiece_dual' if entry['kind']=='marian' else 'sentencepiece' if (target / 'sentencepiece.model').exists() else 'bpe',
                origin=entry['url'], archive_sha256=entry['sha256'], license=entry['license'],
                files={p.relative_to(target).as_posix(): sha(p) for p in target.rglob('*')
                       if p.is_file() and p.name != 'manifest.json'}))
    (runtime / 'python314._pth').write_text('python314.zip\n.\nLib/site-packages\nimport site\n')
    shutil.copyfile(SOURCE / 'worker.py', runtime / 'worker.py')
    shutil.copyfile(SOURCE / 'languages.json', runtime / 'languages.json')
    shutil.copytree(SOURCE / 'terms', runtime / 'terms', dirs_exist_ok=True)
    write(OUT / 'runtime-receipt.json', dict(dependencies=sha(SOURCE / 'dependencies.json'),
        files={p.relative_to(runtime).as_posix(): sha(p) for p in runtime.rglob('*')
               if p.is_file() and '__pycache__' not in p.parts}))
    print('Prepared the offline runtime, selected language packs and bundled fonts.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true', help='Download only the pinned language, font and helper dependencies')
    prepare(parser.parse_args().download)
