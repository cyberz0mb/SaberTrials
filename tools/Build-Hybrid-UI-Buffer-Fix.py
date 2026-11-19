"""Build only the menu parser correction; preserve all installed candidates."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'dist/hybrid-candidate-02'
OUT=ROOT/'dist/hybrid-ui-buffer-fix'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def tree(p):return {x.relative_to(p).as_posix():sha(x) for x in sorted(p.rglob('*')) if x.is_file() and '__pycache__' not in x.parts}
def read(p):return json.loads(p.read_text())
def write(m):(OUT/'manifest.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8',newline='\n')
def inputs():return {p.relative_to(ROOT).as_posix():sha(p) for p in (Path(__file__),ROOT/'development-source/hybrid-styles/animation.py')}
def load(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def verify():
 m=read(OUT/'manifest.json')
 if sha(PARENT/'manifest.json')!=m['parent_manifest_sha256']:raise ValueError('Parent manifest changed')
 parent=read(PARENT/'manifest.json')['sources']['frontend']
 if tree(PARENT/'frontend')!=parent:raise ValueError('Accepted frontend changed')
 if inputs()!=m['inputs']:raise ValueError('Hotfix source inputs changed')
 if tree(OUT/'source')!=m['sources']:raise ValueError('Hotfix source changed')
 changed=[name for name,h in m['sources'].items() if parent.get(name)!=h]
 if changed!=['codemp/ui/ui_main.c']:raise ValueError('Unexpected hotfix scope: '+str(changed))
 for name,h in m['builds'].items():
  if sha(OUT/'build/Release'/name)!=h:raise ValueError('Hotfix binary changed')
 return m

def prepare():
 if OUT.exists():raise ValueError('Hotfix exists; preserve it and use --build or --verify')
 parent=read(PARENT/'manifest.json')
 if tree(PARENT/'frontend')!=parent['sources']['frontend']:raise ValueError('Accepted frontend source drift')
 before=inputs()
 shutil.copytree(PARENT/'frontend',OUT/'source')
 load('animation_overlay',ROOT/'development-source/hybrid-styles/animation.py').fix_ui_parser(OUT/'source')
 if before!=inputs():raise ValueError('Inputs changed during prepare')
 write(dict(sources=tree(OUT/'source'),inputs=before,builds={},
            parent_manifest_sha256=sha(PARENT/'manifest.json')))
 verify();print('Prepared the single-file menu parser correction; installed files unchanged.')

def build():
 m=verify()
 if m['builds']:print('Existing UI-only build verified.');return
 helper=load('build_flags',ROOT/'tools/Prepare-Handedness-Baseline.py')
 subprocess.run(['cmake','-S',str(OUT/'source'),'-B',str(OUT/'build'),'-G','Visual Studio 18 2026','-A','x64',
  '-DST_DEPS='+str(ROOT/'dist/handedness-baseline-06/deps'),'-DST_STAFF_QA=OFF',
  *['-D'+flag+'='+('ON' if flag=='BuildMPUI' else 'OFF') for flag in helper.FLAGS]],check=True)
 subprocess.run(['cmake','--build',str(OUT/'build'),'--config','Release','--target','uix86_64','--parallel','6'],check=True)
 m=verify();m['builds']={'uix86_64.dll':sha(OUT/'build/Release/uix86_64.dll')};write(m)
 print('UI-only hotfix built; no engine, gameplay or installed files changed.')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
 g.add_argument('--prepare',action='store_true');g.add_argument('--build',action='store_true');g.add_argument('--verify',action='store_true')
 a=p.parse_args()
 if a.prepare:prepare()
 elif a.build:build()
 else:verify();print('UI hotfix source, scope and binary verified.')
