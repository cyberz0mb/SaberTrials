"""Build the approved main-menu shell on the installed UI, without game changes."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,re,shutil,subprocess,zipfile
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'dist/menu-polish-02';OUT=ROOT/'dist/main-menu-01';SRC=ROOT/'development-source/main-menu';PREVIOUS=ROOT/'dist/menu-polish-02-install.json';PACKAGE='zzzzzzzz_sabertrials_main.pk3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):return {f.relative_to(p).as_posix():sha(f) for f in sorted(p.rglob('*')) if f.is_file() and '__pycache__' not in f.parts}
def inputs():return {'source':tree(SRC),'art_generator_sha256':sha(ROOT/'tools/Generate-Main-Menu-Art.ps1')}
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def patch(p,a,b):
 s=p.read_text();assert s.count(a)==1,(p,a);p.write_text(s.replace(a,b))
def prepare():
 baseline=json.loads((BASE/'source-receipt.json').read_text());assert tree(BASE/'frontend')==baseline['sources']
 old=json.loads(PREVIOUS.read_text());assert sha(ROOT/'uix86_64.dll')==old['after']['uix86_64.dll'],'Installed baseline drift'
 OUT.mkdir(exist_ok=True);dest=OUT/'frontend'
 if not dest.exists():shutil.copytree(BASE/'frontend',dest)
 for name in ('ui_main.c','ui_atoms.c'):shutil.copy2(BASE/'frontend/codemp/ui'/name,dest/'codemp/ui'/name)
 for name in ('st_main_core.h','ui_st_main.inc'):shutil.copy2(SRC/name,dest/'codemp/ui'/name)
 design=json.loads((SRC/'layout.json').read_text());g=['// Generated from approved main-menu geometry.']
 for key,name in [('outer','smOuter'),('inner','smInner'),('gold_bottom','smGoldBottom'),('account','smAccount')]:g.append('static const std::vector<stmain::Point> '+name+'={'+','.join('{%s,%s}'%tuple(point) for point in design[key])+'};')
 g+=['struct SMButton {const char* name;const char* icon;float y;};','static const SMButton smButtons[]={'+','.join('{"%s","%s",%s}'%(b['name'],b['icon'],b['y']) for b in design['buttons'])+'};']
 (dest/'codemp/ui/st_main_geometry.h').write_text('\n'.join(g)+'\n')
 patch(dest/'codemp/ui/ui_main.c','#include "ui_st_profile.inc"','#include "ui_st_profile.inc"\n#include "ui_st_main.inc"')
 patch(dest/'codemp/ui/ui_main.c','if(SPUI_IsMenu())Menu_Paint(Menu_GetFocused(),qtrue);else Menu_PaintAll();','if(SPUI_IsMenu())Menu_Paint(Menu_GetFocused(),qtrue);else if(!SMUI_Paint())Menu_PaintAll();')
 patch(dest/'codemp/ui/ui_main.c','\tif (SSUI_Key(key,down)) return;','\tif (SMUI_Key(key,down)) return;\n\tif (SSUI_Key(key,down)) return;')
 patch(dest/'codemp/ui/ui_main.c','trap->ext.AddCommand("st_profileqa");','trap->ext.AddCommand("st_profileqa");\n trap->ext.AddCommand("st_mainqa");')
 patch(dest/'codemp/ui/ui_atoms.c','extern qboolean ST_ProfileQA(void);','extern qboolean ST_ProfileQA(void);\nextern qboolean ST_MainQA(void);')
 patch(dest/'codemp/ui/ui_atoms.c','if(ST_ProfileQA()||ST_SetupQA()||ST_ControlsQA())','if(ST_MainQA()||ST_ProfileQA()||ST_SetupQA()||ST_ControlsQA())')
 original=subprocess.check_output(['git','show','d54ee1e:ui/jamp/main.menu'],cwd=ROOT,text=True)
 (OUT/'original-main.menu').write_text(original)
 blocks=module('main_blocks',ROOT/'tools/Stage-Tournament-Frontend.py')
 a,b=blocks.block_span(original,'menuDef','main');main=original[a:b]
 def action(name):
  a,b=blocks.block_span(main,'itemDef',name);found=re.search(r'\baction\s*{([^}]+)}',main[a:b],re.S);assert found;return found[1].strip()
 text=original
 for root in ('main','mainMenu'):
  body=['menuDef { name "'+root+'" rect 0 0 640 480 visible 0 fullscreen 1 focusColor 0 0 0 0','onOpen { uiScript stMenuInit; setfocus play; } onESC { open st_main_exit; }',
   'itemDef { name arena rect 0 0 640 480 style 3 background "ui/assets/sabertrials/arena.tga" forecolor 1 1 1 1 visible 1 decoration }',
   'itemDef { name shade rect 0 0 640 480 style 1 backcolor .005 .018 .032 .28 visible 1 decoration }',
   'itemDef { name movie rect 0 0 640 480 style 5 cinematic "video/sabertrials_menu.roq" visible 1 decoration cvarTest "st_uiMenuMovie" showCvar { "1" } }',
   'itemDef { name movie_shade rect 0 0 640 480 style 1 backcolor .005 .018 .032 .18 visible 1 decoration }']
  for button in design['buttons']:
   act=action(button['name']).replace('close main ;','close '+root+' ;')
   body.append('itemDef { name '+button['name']+' rect 23 '+str(button['y'])+' 153 40 type 1 text "'+button['label']+'" forecolor 0 0 0 0 visible 1 action { '+act+' } }')
  body+=['itemDef { name account_link rect 518 26 107 29 type 1 text "Account / Log in" forecolor 0 0 0 0 visible 1 action { '+action('account_link')+' } }',
   'itemDef { name motion rect 516 435 105 27 type 1 text "Menu motion" forecolor 0 0 0 0 visible 1 action { '+action('motion')+' } }','}']
  a,b=blocks.block_span(text,'menuDef',root);text=text[:a]+'\n'.join(body)+text[b:]
 (SRC/'main.menu').write_text(text);menus=OUT/'menus/ui/jamp';menus.mkdir(parents=True,exist_ok=True);shutil.copy2(SRC/'main.menu',menus/'main.menu')
 art=OUT/'assets/ui/assets/sabertrials/main';art.mkdir(parents=True,exist_ok=True)
 subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'tools/Generate-Main-Menu-Art.ps1'),'-Layout',str(SRC/'layout.json'),'-Output',str(art)],check=True)
 with zipfile.ZipFile(OUT/PACKAGE,'w',zipfile.ZIP_DEFLATED) as z:
  for folder in (OUT/'menus',OUT/'assets'):
   for p in sorted(folder.rglob('*')):
    if p.is_file():entry=zipfile.ZipInfo(p.relative_to(folder).as_posix(),(2026,11,6,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED;z.writestr(entry,p.read_bytes())
 receipt={'baseline_receipt_sha256':sha(BASE/'source-receipt.json'),'previous_install_sha256':sha(PREVIOUS),'original_main_sha256':sha(ROOT/'ui/jamp/main.menu'),'inputs':inputs(),'sources':tree(dest),'assets':tree(OUT/'assets'),'menus':tree(OUT/'menus'),'package_sha256':sha(OUT/PACKAGE)}
 (OUT/'source-receipt.json').write_text(json.dumps(receipt,indent=2));print('Main menu and frame art staged; installed files unchanged.',flush=True)
def build(qa):
 receipt=json.loads((OUT/'source-receipt.json').read_text());assert receipt['inputs']==inputs() and receipt['sources']==tree(OUT/'frontend')
 m=module('ui_builder',ROOT/'tools/Build-Profile.py');m.OUT=OUT;m.SRC=SRC;original=m.tree;m.tree=lambda p:inputs() if p==SRC else original(p);m.build(qa)
 p=OUT/('build-record-qa.json' if qa else 'build-record.json');r=json.loads(p.read_text());r['builder_sha256']=sha(Path(__file__));p.write_text(json.dumps(r,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--build',action='store_true');p.add_argument('--qa',action='store_true');a=p.parse_args()
 if a.prepare:prepare()
 if a.build:build(a.qa)
