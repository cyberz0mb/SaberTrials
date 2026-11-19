"""Stage and build the rich UI on the installed, verified main-menu baseline."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,shutil,subprocess,zipfile
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'dist/main-menu-01';OUT=ROOT/'dist/rich-menus-01';PACKAGE='zzzzzzzzz_sabertrials_rich.pk3'
FILES=[ROOT/'development-source'/name for name in ('controls/ui_st_controls.inc','controls/ui_st_controls_draw.inc','setup/ui_st_setup_draw.inc','setup/ui_st_chat_preview.inc','client-game/codemp/ui/st_chat_layout.h','profile/ui_st_profile.inc','profile/ui_st_profile_draw.inc','main-menu/ui_st_main.inc','rich-menu/ui_st_rich.inc')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):return {f.relative_to(p).as_posix():sha(f) for f in sorted(p.rglob('*')) if f.is_file() and '__pycache__' not in f.parts}
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def inputs():return {str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in FILES+[ROOT/'tools/Generate-Rich-Menu-Art.ps1',ROOT/'tools/Generate-Main-Menu-Art.ps1',ROOT/'development-source/main-menu/layout.json']}
def patch(p,a,b):
 s=p.read_text();assert s.count(a)==1,(p,a);p.write_text(s.replace(a,b))
def prepare():
 baseline=json.loads((BASE/'source-receipt.json').read_text());assert tree(BASE/'frontend')==baseline['sources']
 state=json.loads((ROOT/'dist/main-menu-install.json').read_text());assert sha(ROOT/'uix86_64.dll')==state['after']['uix86_64.dll']
 OUT.mkdir(exist_ok=True);dest=OUT/'frontend'
 if not dest.exists():shutil.copytree(BASE/'frontend',dest)
 # Remove only unused files copied by this candidate's initial draft recipe.
 for name in ('cl_st_setup.inc','st_setup_core.h','cl_st_controller.inc','cl_st_controls.inc','st_controller.inc','st_controls_core.h'):
  p=dest/'codemp/ui'/name
  if 'codemp/ui/'+name not in baseline['sources'] and p.is_file():p.unlink()
 # Restore integration entry points before applying repeatable presentation edits.
 for n in ('ui_main.c','ui_atoms.c'):shutil.copy2(BASE/'frontend/codemp/ui'/n,dest/'codemp/ui'/n)
 for p in FILES:shutil.copy2(p,dest/'codemp/ui'/p.name)
 p=dest/'codemp/ui/ui_st_controls.inc'
 patch(p,'#include "ui_st_controls_draw.inc"','#include "ui_st_controls_draw.inc"\n#include "ui_st_setup.inc"')
 patch(p,'if(id>=100&&id<107){','if(id==106){if(scui.dirty){scui.modal=10;Q_strncpyz(scui.status,"Discard pending controls changes and open Saved Configs?",sizeof(scui.status));}else SSUI_FromControls();return;}\n if(id>=100&&id<107){')
 patch(p,'if(modal==1)SCUI_Close();','if(modal==10)SSUI_FromControls();else if(modal==1)SCUI_Close();')
 # Only the focused custom page paints. Its live/solid underlay precedes G2.
 p=dest/'codemp/ui/ui_main.c'
 patch(p,'if(SPUI_IsMenu())Menu_Paint(Menu_GetFocused(),qtrue);else if(!SMUI_Paint())Menu_PaintAll();','RUI_Background();\n\t\tif(RUI_Page())Menu_Paint(Menu_GetFocused(),qtrue);else if(!SMUI_Paint())Menu_PaintAll();')
 patch(p,'uie.IsFullscreen\t\t= Menus_AnyFullScreenVisible;','uie.IsFullscreen\t\t= RUI_IsFullscreen;')
 patch(p,'case UI_IS_FULLSCREEN:\n\t\treturn Menus_AnyFullScreenVisible();','case UI_IS_FULLSCREEN:\n\t\treturn RUI_IsFullscreen();')
 art=OUT/'assets/ui/assets/sabertrials/rich';art.mkdir(parents=True,exist_ok=True)
 subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'tools/Generate-Rich-Menu-Art.ps1'),'-Output',str(art),'-Metrics',str(dest/'codemp/ui/st_rich_type.h')],check=True)
 # Reuse main asset paths so the main shell receives the same improved material.
 main=OUT/'assets/ui/assets/sabertrials/main';main.mkdir(parents=True,exist_ok=True)
 for p in art.glob('*.png'):
  if p.stem in ('frame','button_focus','button_idle','glow','emblem') or p.stem.startswith('label_'):shutil.copy2(p,main/p.name)
 menus=OUT/'menus/ui/jamp';menus.mkdir(parents=True,exist_ok=True)
 for n in ('player.menu','ingame_player.menu','controls.menu','ingame_controls.menu','setup.menu','ingame_setup.menu'):shutil.copy2(ROOT/'ui/jamp'/n,menus/n)
 with zipfile.ZipFile(OUT/PACKAGE,'w',zipfile.ZIP_DEFLATED) as z:
  for folder in (OUT/'assets',OUT/'menus'):
   for p in sorted(folder.rglob('*')):
    if p.is_file():entry=zipfile.ZipInfo(p.relative_to(folder).as_posix(),(2026,11,6,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED;z.writestr(entry,p.read_bytes())
 receipt={'baseline_receipt_sha256':sha(BASE/'source-receipt.json'),'baseline_install_sha256':sha(ROOT/'dist/main-menu-install.json'),'inputs':inputs(),'sources':tree(dest),'assets':tree(OUT/'assets'),'menus':tree(OUT/'menus'),'package_sha256':sha(OUT/PACKAGE)}
 (OUT/'source-receipt.json').write_text(json.dumps(receipt,indent=2));print('Rich UI prepared; installed game untouched.',flush=True)
def build(qa):
 r=json.loads((OUT/'source-receipt.json').read_text());assert r['inputs']==inputs() and r['sources']==tree(OUT/'frontend')
 m=load('rich_profile_builder',ROOT/'tools/Build-Profile.py');m.OUT=OUT;m.SRC=ROOT/'development-source/rich-menu';original=m.tree;m.tree=lambda p:inputs() if p==m.SRC else original(p);m.build(qa)
 p=OUT/('build-record-qa.json' if qa else 'build-record.json');r=json.loads(p.read_text());r['builder_sha256']=sha(Path(__file__));p.write_text(json.dumps(r,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--build',action='store_true');p.add_argument('--qa',action='store_true');a=p.parse_args()
 if a.prepare:prepare()
 if a.build:build(a.qa)
