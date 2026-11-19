"""Build an isolated Setup overlay on verified Controls sources."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'dist/controls-candidate-01';OUT=ROOT/'dist/setup-candidate-01';SRC=ROOT/'development-source/setup'
spec=importlib.util.spec_from_file_location('controls_build',ROOT/'tools/Build-Controls.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
sha=b.sha;tree=b.tree;patch=b.patch
def prepare():
 receipt=json.loads((BASE/'source-receipt.json').read_text());OUT.mkdir(exist_ok=True)
 for kind in ('engine','frontend'):
  assert tree(BASE/kind)==receipt['sources'][kind],'Controls source drift: '+kind
  dest=OUT/kind
  if not dest.exists():shutil.copytree(BASE/kind,dest)
  # Always regenerate the modified baseline files; preserve build directories.
  files=['codemp/ui/ui_public.h']
  files+=['codemp/client/cl_uiapi.cpp','codemp/client/cl_main.cpp','codemp/client/st_controls_core.h','codemp/client/cl_st_controls.inc'] if kind=='engine' else ['shared/qcommon/q_platform.h','codemp/ui/CMakeLists.txt','codemp/ui/ui_main.c','codemp/ui/ui_atoms.c','codemp/ui/ui_syscalls.c','codemp/ui/ui_st_controls.inc','codemp/ui/ui_st_controls_draw.inc','codemp/cgame/cg_draw.c']
  for name in files:shutil.copy2(BASE/kind/name,dest/name)
  patch(dest/'codemp/ui/ui_public.h','#define UI_API_VERSION 284','#define UI_API_VERSION 285')
  shutil.copy2(SRC/'st_setup_catalog.h',dest/'codemp/ui/st_setup_catalog.h')
  shutil.copy2(ROOT/'development-source/client-game/codemp/ui/st_chat_layout.h',dest/'codemp/ui/st_chat_layout.h')
  if kind=='engine':
   for n in ('cl_st_setup.inc','st_setup_core.h'):shutil.copy2(SRC/n,dest/'codemp/client'/n)
   p=dest/'codemp/client/st_controls_core.h'
   patch(p,'auto n=lower(s);for(auto prefix:', 'auto n=lower(s);if(n=="com_maxfps")return true;for(auto prefix:')
   patch(p,'"controls-test","purple-test"','"controls-test","purple-test","setup-test"')
   patch(p,'Load through Controls > Saved Configs','Load through Setup > Saved Configs')
   p=dest/'codemp/client/cl_st_controls.inc'
   patch(p,'(v->flags&CVAR_ARCHIVE)||STC_Catalog(v->name)','(v->flags&CVAR_ARCHIVE)||STC_Catalog(v->name)||!Q_stricmp(v->name,"cl_timeNudge")')
   patch(p,'static int STC_Controls(const stcRequest_t* q,stcReply_t* r){','#include "cl_st_setup.inc"\nstatic int STC_Controls(const stcRequest_t* q,stcReply_t* r){\n if(q&&q->op>=100)return STSetup_Controls(q,r);')
   p=dest/'codemp/client/cl_main.cpp'
   patch(p,'void CL_Vid_Restart_f( void ) {','extern void STSetup_DisplayReady();\nvoid CL_Vid_Restart_f( void ) {')
   patch(p,'// startup all the client stuff\n\tCL_StartHunkUsers();','// startup all the client stuff\n\tCL_StartHunkUsers();\n STSetup_DisplayReady();')
   patch(p,'\t\tCL_InitUI();\n\t}\n}', '\t\tCL_InitUI();\n STSetup_DisplayReady();\n\t}\n}')
   patch(p,'void CL_InitRef( void ) {','extern void STSetup_EarlyRecovery();\nvoid CL_InitRef( void ) {\n STSetup_EarlyRecovery();')
   patch(p,'void CL_Frame ( int msec ) {','extern void STSetup_Frame();\nvoid CL_Frame ( int msec ) {\n STSetup_Frame();')
  else:
   for n in ('ui_st_setup.inc','ui_st_setup_draw.inc','ui_st_chat_preview.inc'):shutil.copy2(SRC/n,dest/'codemp/ui'/n)
   p=dest/'codemp/ui/ui_st_controls.inc'
   patch(p,'#include "ui_st_controls_draw.inc"','#include "ui_st_controls_draw.inc"\n#include "ui_st_setup.inc"')
   patch(p,'if(id>=100&&id<107){','if(id==106){if(scui.dirty){scui.modal=10;Q_strncpyz(scui.status,"Discard pending controls changes and open Saved Configs?",sizeof(scui.status));}else SSUI_FromControls();return;}\n if(id>=100&&id<107){')
   patch(p,'if(modal==1)SCUI_Close();','if(modal==10)SSUI_FromControls();else if(modal==1)SCUI_Close();')
   p=dest/'shared/qcommon/q_platform.h'
   patch(p,'typedef enum { qfalse, qtrue } qboolean;','#if defined(UI_BUILD) && defined(__cplusplus)\nenum { qfalse, qtrue }; typedef int qboolean;\n#else\ntypedef enum { qfalse, qtrue } qboolean;\n#endif')
   p=dest/'codemp/ui/CMakeLists.txt'
   patch(p,'add_library(${MPUI} SHARED ${MPUIFiles})','foreach(setup_ui_source ${MPUIFiles})\n if(setup_ui_source MATCHES \"[.]c$\")\n  set_source_files_properties(${setup_ui_source} PROPERTIES LANGUAGE CXX)\n endif()\nendforeach()\nadd_library(${MPUI} SHARED ${MPUIFiles})')
   p=dest/'codemp/ui/ui_main.c'
   patch(p,'Q_EXPORT uiExport_t* QDECL GetModuleAPI','extern "C" Q_EXPORT uiExport_t* QDECL GetModuleAPI')
   patch(p,'Q_EXPORT intptr_t vmMain','extern "C" Q_EXPORT intptr_t vmMain')
   patch(p,'dirlist = malloc(DIR_LIST_SIZE);','dirlist = (char*)malloc(DIR_LIST_SIZE);')
   patch(p,'BG_FindItemForWeapon( i )','BG_FindItemForWeapon( (weapon_t)i )')
   patch(p,'BG_FindItemForHoldable(i)','BG_FindItemForHoldable((holdable_t)i)')
   patch(p,'SaberColorToString(trap->Cvar_VariableValue("color1"))','SaberColorToString((saber_colors_t)(int)trap->Cvar_VariableValue("color1"))')
   patch(p,'SaberColorToString(trap->Cvar_VariableValue("color2"))','SaberColorToString((saber_colors_t)(int)trap->Cvar_VariableValue("color2"))')
   patch(p,'extern void UI_SaberAttachToChar( itemDef_t *item );','extern void UI_SaberAttachToChar( itemDef_t *item );\nextern qboolean WP_SaberParseParm(const char*,const char*,char*);')
   patch(p,'buffer = malloc(filelen + 1);','buffer = (char*)malloc(filelen + 1);')
   patch(p,'UI_SetActiveMenu( arg0 );','UI_SetActiveMenu( (uiMenuCommand_t)arg0 );')
   patch(p,'\t\tSCUI_Draw();','\t\tSCUI_Draw();\n\t\tSSUI_Draw();')
   patch(p,'\tif (SCUI_Key(key,down)) return;','\tif (SSUI_Key(key,down)) return;\n\tif (SCUI_Key(key,down)) return;')
   patch(p,'\t\tif (SCUI_IsMenu()) {SCUI_Mouse();return;}','\t\tif (SSUI_IsMenu()) {SSUI_Mouse();return;}\n\t\tif (SCUI_IsMenu()) {SCUI_Mouse();return;}')
   patch(p,'trap->ext.AddCommand("st_controlsqa");','trap->ext.AddCommand("st_controlsqa");\n\ttrap->ext.AddCommand("st_setupqa");')
   p=dest/'codemp/ui/ui_syscalls.c'
   patch(p,'Q_EXPORT void dllEntry','extern "C" Q_EXPORT void dllEntry')
   patch(p,'return Q_syscall(UI_CIN_STOPCINEMATIC, handle);','return (e_status)Q_syscall(UI_CIN_STOPCINEMATIC, handle);')
   patch(p,'return Q_syscall(UI_CIN_RUNCINEMATIC, handle);','return (e_status)Q_syscall(UI_CIN_RUNCINEMATIC, handle);')
   p=dest/'codemp/ui/ui_atoms.c'
   patch(p,'extern qboolean ST_ControlsQA(void);','extern qboolean ST_ControlsQA(void);\nextern qboolean ST_SetupQA(void);')
   patch(p,'if(ST_ControlsQA()) return qtrue;','if(ST_SetupQA()||ST_ControlsQA()) return qtrue;')
   p=dest/'codemp/cgame/cg_draw.c'
   patch(p,'static void ST_DrawStreamerPresentation( void ) {','static void ST_DrawStreamerPresentation( void ) {\n if(!cg_draw2D.integer)return;')
 (OUT/'source-receipt.json').write_text(json.dumps({'baseline':sha(BASE/'source-receipt.json'),'inputs':tree(SRC),'sources':{k:tree(OUT/k) for k in ('engine','frontend')}},indent=2))
 print('Setup source prepared; Controls baseline preserved.',flush=True)
def build(kind,qa):
 folder=OUT/('build-'+kind+('-qa' if qa else ''))
 flags=b.FLAGS
 args=['cmake','-S',str(OUT/kind),'-B',str(folder),'-G','Visual Studio 18 2026','-A','x64','-DST_DEPS='+str(ROOT/'dist/handedness-baseline-06/deps'),'-DST_STAFF_QA=OFF']
 on=['BuildMPEngine'] if kind=='engine' else ['BuildMPUI','BuildMPCGame']
 args+=['-D'+f+'='+('ON' if f in on else 'OFF') for f in flags]
 args+=['-DCMAKE_CXX_FLAGS='+('/DST_CONTROLS_QA' if qa else '')]
 subprocess.run(args,check=True);subprocess.run(['cmake','--build',str(folder),'--config','Release','--parallel','6'],check=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--build',choices=['engine','frontend']);p.add_argument('--qa',action='store_true');a=p.parse_args()
 if a.prepare:prepare()
 if a.build:build(a.build,a.qa)
