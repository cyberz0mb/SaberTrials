"""Build the independent validated-loader/cosmetic-mesh candidate; never installs."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/enhanced-models'
BASE=ROOT/'dist/mvp-cinematic-candidate-03'

def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args()
    receipt=json.loads((BASE/'manifest.json').read_text())
    for name,digest in receipt['sources']['engine'].items():
        if sha(BASE/'engine'/name)!=digest: raise RuntimeError(f'Checkpoint drift: {name}')
    shutil.copytree(BASE/'engine',OUT/'engine',dirs_exist_ok=True)
    spec=importlib.util.spec_from_file_location('model_overlay',ROOT/'development-source/enhanced-models/overlay.py')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    mod.apply(OUT/'engine')
    if args.prepare_only: return
    enabled={'BuildMPEngine','BuildMPDed','BuildMPRdVanilla','BuildMPRend2'}
    options=enabled|{'BuildMPGame','BuildMPCGame','BuildMPUI','BuildSPEngine','BuildSPGame','BuildSPRdVanilla'}
    cmd=['cmake','-S',str(OUT/'engine'),'-B',str(OUT/'build'),'-G','Visual Studio 18 2026','-A','x64',
         f'-DST_DEPS={ROOT / "dist/handedness-baseline-06/deps"}','-DST_STAFF_QA=OFF']
    cmd += [f'-D{k}={"ON" if k in enabled else "OFF"}' for k in sorted(options)]
    with (OUT/'build.log').open('w') as log:
        subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['cmake','--build',str(OUT/'build'),'--config','Release','--parallel','8'],stdout=log,stderr=subprocess.STDOUT,check=True)
    binaries={p.name:sha(p) for p in (OUT/'build/Release').iterdir() if p.suffix in ('.dll','.exe')}
    (OUT/'build.json').write_text(json.dumps({'checkpoint':sha(BASE/'manifest.json'),'binaries':binaries,
        'inputs':{p.name:sha(p) for p in (ROOT/'development-source/enhanced-models').iterdir() if p.is_file()}},indent=2))

if __name__=='__main__': main()
