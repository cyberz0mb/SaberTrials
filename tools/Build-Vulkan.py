"""Prepare and build the optional Vulkan client in an isolated candidate directory."""
import argparse
from importlib import import_module, util
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'development-source/vulkan'
OUT = ROOT / 'dist/vulkan-01'
REVISION = 'c78118a5812cd67dea24276fa07258e94b9172d8'
UPSTREAM = OUT / 'upstream' / ('EternalJK-' + REVISION)
BASE = ROOT / 'dist/server-browser-01'
ROLES = {
    'engine': ('engine', 'BuildMPEngine', 'openjk.x86_64', '.exe'),
    'vulkan': ('engine', 'BuildMPRdVulkan', 'rd-vulkan_x86_64', '.dll'),
    'ui': ('frontend', 'BuildMPUI', 'uix86_64', '.dll'),
}

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')

def tree(path):
    return {p.relative_to(path).as_posix(): sha(p) for p in sorted(Path(path).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}

def module(name, path):
    spec = util.spec_from_file_location(name, path)
    result = util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def prepare(base=BASE):
    archive = OUT / 'upstream/openjk-vulkan.zip'
    lock = read(SOURCE / 'upstream.json')
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        with urllib.request.urlopen(lock['url'], timeout=60) as remote, archive.with_suffix('.tmp').open('wb') as local:
            shutil.copyfileobj(remote, local)
        archive.with_suffix('.tmp').replace(archive)
    if sha(archive) != lock['sha256']:
        raise ValueError('Vulkan source archive checksum mismatch')
    with zipfile.ZipFile(archive) as zipped:
        for item in zipped.infolist():
            target = (archive.parent / item.filename).resolve()
            if not target.is_relative_to(archive.parent.resolve()):
                raise ValueError('Unsafe archive path')
        zipped.extractall(archive.parent)
    baseline = read(base / 'source-receipt.json')['sources']
    for role in ('engine', 'frontend'):
        if tree(base / role) != baseline[role]:
            raise ValueError(role + ' source differs from its checkpoint')
        # Copying fresh baselines makes preparing idempotent without modifying the source checkpoint.
        shutil.copytree(base / role, OUT / role, dirs_exist_ok=True)
    shutil.copytree(UPSTREAM / 'codemp/rd-vulkan', OUT / 'engine/codemp/rd-vulkan', dirs_exist_ok=True)
    subprocess.run(['git', 'apply', '--unsafe-paths', '--ignore-space-change',
                    '--directory=' + (OUT / 'engine').as_posix(), str(SOURCE / 'upstream-integration.patch')],
                   check=True, cwd=ROOT)
    module('st_vulkan_overlay', SOURCE / 'overlay.py').apply(OUT / 'engine', OUT / 'frontend')
    write(OUT / 'source-receipt.json', dict(baseline=str(base), baseline_receipt=sha(base / 'source-receipt.json'),
          upstream=lock, sources={role: tree(OUT / role) for role in ('engine','frontend')}, authored=tree(SOURCE)))
    print('Prepared optional Vulkan client sources.', flush=True)

def build(role):
    source, target, name, extension = ROLES[role]
    receipt = read(OUT / 'source-receipt.json')
    if tree(OUT / source) != receipt['sources'][source]:
        raise ValueError('Source changed since preparation')
    flags = ('BuildMPEngine','BuildMPDed','BuildMPGame','BuildMPCGame','BuildMPUI',
             'BuildMPRdVanilla','BuildMPRend2','BuildMPRdVulkan','BuildSPEngine','BuildSPGame','BuildSPRdVanilla')
    with (OUT / f'build-{role}.log').open('w') as log:
        subprocess.run(['cmake','-S',str(OUT/source),'-B',str(OUT/f'build-{role}'),
                        '-G','Visual Studio 18 2026','-A','x64','-DST_STAFF_QA=OFF',
                        '-DST_DEPS='+str(ROOT/'dist/handedness-baseline-06/deps'),
                        *[f'-D{f}={"ON" if f==target else "OFF"}' for f in flags]],
                       stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['cmake','--build',str(OUT/f'build-{role}'),'--config','Release',
                        '--parallel','5','--target',name],stdout=log,stderr=subprocess.STDOUT,check=True)
    write(OUT/f'build-{role}.json',dict(source=sha(OUT/'source-receipt.json'),
          sha256=sha(OUT/f'build-{role}'/'Release'/(name+extension))))
    print('Built '+role,flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', *ROLES))
    parser.add_argument('--checkpoint', type=Path, default=BASE)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args.checkpoint)
    else:
        build(args.action)
