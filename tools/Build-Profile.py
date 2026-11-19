"""Build only the approved Profile UI on the installed Controls/Setup frontend."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, shutil, subprocess, sys, zipfile
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'dist/controls-setup-release-01/setup'
OUT=ROOT/'dist/profile-candidate-01'
SRC=ROOT/'development-source/profile'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):return {f.relative_to(p).as_posix():sha(f) for f in sorted(p.rglob('*')) if f.is_file() and '__pycache__' not in f.parts}
def patch(p,old,new):
 text=p.read_text();assert text.count(old)==1,(p,old,text.count(old));p.write_text(text.replace(old,new))

def prepare():
 record=json.loads((BASE/'source-receipt.json').read_text())
 assert tree(BASE/'frontend')==record['sources']['frontend'],'Installed frontend source drift'
 for name in ('ui_st_profile.inc','ui_st_profile_catalog.inc','ui_st_profile_draw.inc','ui_st_profile_actions.inc','player.menu','ingame_player.menu'):
  assert (SRC/name).is_file(),'Missing Profile integration: '+name
 OUT.mkdir(parents=True,exist_ok=True);dest=OUT/'frontend'
 if not dest.exists():shutil.copytree(BASE/'frontend',dest)
 for name in ('ui_main.c','ui_atoms.c','ui_sabertrials_profile.inc'):
  shutil.copy2(BASE/'frontend/codemp/ui'/name,dest/'codemp/ui'/name)
 for source in SRC.glob('*'):
  if source.suffix in ('.inc','.h'):shutil.copy2(source,dest/'codemp/ui'/source.name)
 tags=json.loads((SRC/'catalog.json').read_text());lines=['// Curated fallback metadata; optional installed st_profile.ini takes priority.','struct SPTag {const char *model,*text;};','static const SPTag spTags[]={']
 for folder,tag in tags.items():
  text='\n'.join(key+'='+(','.join(value) if isinstance(value,list) else value) for key,value in tag.items())+'\n'
  lines.append('{'+json.dumps(folder)+','+json.dumps(text)+'},')
 lines.append('};');(dest/'codemp/ui/st_profile_tags.h').write_text('\n'.join(lines)+'\n')
 voices=set()
 for archive in (ROOT.parent/'base').glob('assets?.pk3'):
  with zipfile.ZipFile(archive) as z:
   voices.update(name.split('/')[2].lower() for name in z.namelist() if name.lower().startswith('sound/chars/') and len(name.split('/'))>4)
 assert voices,'Original game voice catalog is unavailable'
 (dest/'codemp/ui/st_profile_stock_voices.h').write_text('// Original JKA voice folders; custom packages never change this baseline.\nstatic const char* spStockVoices[]={'+','.join(json.dumps(v) for v in sorted(voices))+'};\n')
 p=dest/'codemp/ui/ui_main.c'
 patch(p,'#include "ui_st_controls.inc"','#include "ui_st_controls.inc"\n#include "ui_st_profile.inc"')
 patch(p,'\t\tST_UIRefreshShell();','\t\tSPUI_BeforePaint();\n\t\tST_UIRefreshShell();')
 patch(p,'\t\tMenu_PaintAll();','\t\tif(SPUI_IsMenu())Menu_Paint(Menu_GetFocused(),qtrue);else Menu_PaintAll();')
 patch(p,'\t\tSSUI_Draw();','\t\tSSUI_Draw();\n\t\tSPUI_Draw();')
 patch(p,'\tif (SSUI_Key(key,down)) return;','\tif (SPUI_Key(key,down)) return;\n\tif (SSUI_Key(key,down)) return;')
 patch(p,'\t\tif (SSUI_IsMenu()) {SSUI_Mouse();return;}','\t\tif (SPUI_IsMenu()) {SPUI_Mouse();return;}\n\t\tif (SSUI_IsMenu()) {SSUI_Mouse();return;}')
 patch(p,'trap->ext.AddCommand("st_setupqa");','trap->ext.AddCommand("st_setupqa");\n\ttrap->ext.AddCommand("st_profileqa");')
 p=dest/'codemp/ui/ui_atoms.c'
 patch(p,'extern qboolean ST_SetupQA(void);','extern qboolean ST_SetupQA(void);\nextern qboolean ST_ProfileQA(void);')
 patch(p,'if(ST_SetupQA()||ST_ControlsQA()) return qtrue;','if(ST_ProfileQA()||ST_SetupQA()||ST_ControlsQA()) return qtrue;')
 p=dest/'codemp/ui/ui_sabertrials_profile.inc'
 patch(p,'static void ST_UIProfilePreview( menuDef_t *menu ) {','extern void UI_ClearG2Pointer(void* ghoul2);\nstatic void ST_UIProfilePreview( menuDef_t *menu ) {')
 patch(p,'if ( !menu || Q_stricmp( menu->window.name, "playerMenu" ) ) {','if ( !menu || (Q_stricmp(menu->window.name,"playerMenu") && Q_stricmp(menu->window.name,"ingame_player")) ) {')
 patch(p,'trap->Cvar_VariableStringBuffer( "model", selection, sizeof(selection) );','trap->Cvar_VariableStringBuffer( "ui_stProfileSelection", selection, sizeof(selection) );\n if(!selection[0])trap->Cvar_VariableStringBuffer("model",selection,sizeof(selection));')
 patch(p,'preview->g2skin = trap->R_RegisterSkin( path );','''preview->g2skin = trap->R_RegisterSkin( path );
 if(!preview->g2skin){
  // Unlink the old tracked instance before releasing it. A valid GLM with an
  // absent/empty skin must not fall through to the renderer's default surfaces.
  if(item->ghoul2){UI_ClearG2Pointer(item->ghoul2);trap->G2API_CleanGhoul2Models(&item->ghoul2);}
  item->flags &= ~ITF_G2VALID;loaded=qfalse;
  trap->Cvar_Set("ui_stProfilePreviewAvailable","0");return;
 }''')
 patch(p,'loaded = item->ghoul2 && (item->flags & ITF_G2VALID);','loaded = item->ghoul2 && (item->flags & ITF_G2VALID);\n if(!loaded && item->ghoul2)trap->G2API_CleanGhoul2Models(&item->ghoul2);')
 # ItemParse_asset_model_go already clears the old instance AND its tracking
 # entry. Only clean the untracked empty container from a failed new load here.
 (OUT/'source-receipt.json').write_text(json.dumps({'baseline':sha(BASE/'source-receipt.json'),'inputs':tree(SRC),'sources':tree(dest)},indent=2))
 print('Profile frontend prepared; installed API 285 and gameplay sources preserved.',flush=True)

def build(qa):
 receipt=json.loads((OUT/'source-receipt.json').read_text())
 assert receipt['inputs']==tree(SRC) and receipt['sources']==tree(OUT/'frontend'),'Prepared source drift'
 folder=OUT/('build-qa' if qa else 'build')
 flags=('BuildMPEngine','BuildMPDed','BuildMPGame','BuildMPCGame','BuildMPUI','BuildMPRdVanilla','BuildMPRend2','BuildSPEngine','BuildSPGame','BuildSPRdVanilla')
 args=['cmake','-S',str(OUT/'frontend'),'-B',str(folder),'-G','Visual Studio 18 2026','-A','x64','-DST_DEPS='+str(ROOT/'dist/handedness-baseline-06/deps'),'-DST_STAFF_QA=OFF']
 args+=['-D'+f+'='+('ON' if f=='BuildMPUI' else 'OFF') for f in flags]
 args+=['-DCMAKE_CXX_FLAGS='+('/DST_CONTROLS_QA' if qa else '')]
 subprocess.run(args,check=True);subprocess.run(['cmake','--build',str(folder),'--config','Release','--parallel','6'],check=True)
 (OUT/('build-record-qa.json' if qa else 'build-record.json')).write_text(json.dumps({'source_receipt_sha256':sha(OUT/'source-receipt.json'),'builder_sha256':sha(Path(__file__)),'ui_sha256':sha(folder/'Release/uix86_64.dll'),'qa':qa,'ui_api':285},indent=2))

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');parser.add_argument('--build',action='store_true');parser.add_argument('--qa',action='store_true');args=parser.parse_args()
 if args.prepare:prepare()
 if args.build:build(args.qa)
