"""Build UI-only menu styling/scroll fixes on the installed Profile release."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'dist/profile-candidate-01';OUT=ROOT/'dist/menu-polish-01'
FILES={folder:list((ROOT/'development-source'/folder).glob(pattern)) for folder,pattern in [('controls','ui_st_*.inc'),('setup','ui_st_*.inc'),('profile','ui_st_*.inc'),('menu-polish','*')]}
def configure(revision):
 global BASE,OUT,PREVIOUS_STATE
 assert revision>=1
 OUT=ROOT/('dist/menu-polish-%02d'%revision)
 BASE=ROOT/('dist/profile-candidate-01' if revision==1 else 'dist/menu-polish-%02d'%(revision-1))
 PREVIOUS_STATE=ROOT/('dist/profile-browser-install.json' if revision==1 else 'dist/menu-polish-install.json' if revision==2 else 'dist/menu-polish-%02d-install.json'%(revision-1))
configure(1)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):return {f.relative_to(p).as_posix():sha(f) for f in sorted(p.rglob('*')) if f.is_file() and '__pycache__' not in f.parts}
def inputs():return {str(p.relative_to(ROOT)):sha(p) for paths in FILES.values() for p in paths if p.is_file()}
def prepare():
 baseline=json.loads((BASE/'source-receipt.json').read_text());assert tree(BASE/'frontend')==baseline['sources'],'Profile source baseline drift'
 state=json.loads(PREVIOUS_STATE.read_text());assert state['installed'];assert sha(ROOT/'uix86_64.dll')==state['after']['uix86_64.dll'],'Installed Profile UI drift'
 OUT.mkdir(exist_ok=True);dest=OUT/'frontend'
 if not dest.exists():shutil.copytree(BASE/'frontend',dest)
 for paths in FILES.values():
  for p in paths:
   if p.is_file():shutil.copy2(p,dest/'codemp/ui'/p.name)
 # Retain the installed Setup integration, applied by its original builder.
 p=dest/'codemp/ui/ui_st_controls.inc';text=p.read_text()
 if '#include "ui_st_setup.inc"' not in text:
  text=text.replace('#include "ui_st_controls_draw.inc"','#include "ui_st_controls_draw.inc"\n#include "ui_st_setup.inc"')
  text=text.replace('if(id>=100&&id<107){','if(id==106){if(scui.dirty){scui.modal=10;Q_strncpyz(scui.status,"Discard pending controls changes and open Saved Configs?",sizeof(scui.status));}else SSUI_FromControls();return;}\n if(id>=100&&id<107){')
  text=text.replace('if(modal==1)SCUI_Close();','if(modal==10)SSUI_FromControls();else if(modal==1)SCUI_Close();')
 p.write_text(text)
 shutil.copytree(BASE/'menus',OUT/'menus',dirs_exist_ok=True)
 receipt={'baseline_receipt_sha256':sha(BASE/'source-receipt.json'),'baseline_install_sha256':sha(PREVIOUS_STATE),'inputs':inputs(),'sources':tree(dest)}
 (OUT/'source-receipt.json').write_text(json.dumps(receipt,indent=2));print('Prepared isolated menu UI; installed files unchanged.')
def build(qa):
 receipt=json.loads((OUT/'source-receipt.json').read_text());assert receipt['inputs']==inputs() and receipt['sources']==tree(OUT/'frontend')
 spec=importlib.util.spec_from_file_location('profile_builder',ROOT/'tools/Build-Profile.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 # The original builder's UI-only build/API switches, operating on this candidate.
 m.OUT=OUT;m.SRC=ROOT/'development-source/menu-polish'
 original_tree=m.tree
 m.tree=lambda p:inputs() if p==m.SRC else original_tree(p)
 m.build(qa)
 record=OUT/('build-record-qa.json' if qa else 'build-record.json');data=json.loads(record.read_text());data['builder_sha256']=sha(Path(__file__));record.write_text(json.dumps(data,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--revision',type=int,default=1);p.add_argument('--prepare',action='store_true');p.add_argument('--build',action='store_true');p.add_argument('--qa',action='store_true');a=p.parse_args();configure(a.revision)
 if a.prepare:prepare()
 if a.build:build(a.qa)
