"""Prepare/build a matching isolated feint engine and modules. Never install or launch."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/feint-candidate-01'
ORIGINS={'engine':ROOT/'dist/handedness-baseline-06/engine',
         'game':ROOT/'dist/combat-foundation-01/candidate/game',
         'frontend':ROOT/'dist/combat-foundation-01/candidate/frontend'}
def module(name,file):
 spec=importlib.util.spec_from_file_location(name,file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(root):return {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
def read(p):return json.loads(p.read_text())
def write(p,data):p.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
def inputs():return {p.relative_to(ROOT).as_posix():sha(p) for folder in ('combat-foundation','combat-integration') for p in (ROOT/'development-source'/folder).glob('*') if p.is_file()}
def original():
 module('foundation',ROOT/'tools/Stage-Combat-Foundation.py').verify()
 manifests=read(ROOT/'dist/combat-foundation-01/candidate.json')['sources']
 manifests['engine']=read(ROOT/'dist/handedness-baseline-06/provenance.json')['components']['engine']
 for kind,source in ORIGINS.items():
  if tree(source)!=manifests[kind]:raise ValueError('Original drift: '+kind)
 return manifests
def verify(require_inputs=True):
 original();m=read(OUT/'manifest.json')
 if require_inputs and inputs()!=m['inputs']:raise ValueError('Overlay changed; sync candidate explicitly')
 for kind in ORIGINS:
  if tree(OUT/kind)!=m['sources'][kind]:raise ValueError('Candidate source drift: '+kind)
 for kind,files in m['builds'].items():
  for name,expected in files.items():
   if sha(OUT/('build-'+kind)/'Release'/name)!=expected:raise ValueError('Build drift: '+name)
 return m
def prepare():
 baseline=original()
 if OUT.exists():raise ValueError('Candidate exists: do not overwrite it')
 OUT.mkdir(parents=True)
 overlay=module('feint_overlay',ROOT/'development-source/combat-integration/prepare.py')
 m={'installed':False,'origins':{k:str(v) for k,v in ORIGINS.items()},'baseline_sources':baseline,
    'sources':{},'changes':{},'inputs':inputs(),'builds':{}}
 for kind,source in ORIGINS.items():
  shutil.copytree(source,OUT/kind);overlay.apply(OUT/kind,kind)
  m['sources'][kind]=tree(OUT/kind)
  m['changes'][kind]=[n for n,h in m['sources'][kind].items() if baseline[kind].get(n)!=h]
 write(OUT/'manifest.json',m);verify();print('Matching feint engine/game/frontend candidate prepared; default off; not installed.')
def sync():
 m=verify(False);overlay=module('feint_overlay',ROOT/'development-source/combat-integration/prepare.py')
 for kind,source in ORIGINS.items():
  for name in m['changes'][kind]:
   if name in m['baseline_sources'][kind]:shutil.copy2(source/name,OUT/kind/name)
  overlay.apply(OUT/kind,kind);m['sources'][kind]=tree(OUT/kind)
  m['changes'][kind]=[n for n,h in m['sources'][kind].items() if m['baseline_sources'][kind].get(n)!=h]
 m['inputs']=inputs();m['builds']={};write(OUT/'manifest.json',m);print('Overlay regenerated; rebuild all matching components.')
def build(kind):
 m=verify();helper=module('baseline',ROOT/'tools/Prepare-Handedness-Baseline.py')
 folder=OUT/('build-'+kind)
 subprocess.run(['cmake','-S',str(OUT/kind),'-B',str(folder),'-G','Visual Studio 18 2026','-A','x64',
   '-DST_DEPS='+str(ROOT/'dist/handedness-baseline-06/deps'),'-DST_STAFF_QA=OFF',
   *['-D'+f+'='+('ON' if f in helper.TARGETS[kind] else 'OFF') for f in helper.FLAGS]],check=True)
 subprocess.run(['cmake','--build',str(folder),'--config','Release','--parallel','6'],check=True)
 m=verify();m['builds'][kind]={n:sha(folder/'Release'/n) for n in helper.ARTIFACTS[kind]}
 write(OUT/'manifest.json',m);print('Built',kind,'without installing or launching.')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
 g.add_argument('--prepare',action='store_true');g.add_argument('--sync',action='store_true')
 g.add_argument('--verify',action='store_true');g.add_argument('--build',choices=tuple(ORIGINS))
 a=p.parse_args()
 if a.prepare:prepare()
 elif a.sync:sync()
 elif a.build:build(a.build)
 else:verify();print('Feint candidate, originals, build outputs and installed baseline verified.')
