"""Build the Controls candidate in isolation. Does not install or launch it."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, shutil, subprocess
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'dist/purple-katana-candidate-07'
OUT=ROOT/'dist/controls-candidate-01'
SRC=ROOT/'development-source/controls'
FLAGS=('BuildMPEngine','BuildMPDed','BuildMPGame','BuildMPCGame','BuildMPUI','BuildMPRdVanilla','BuildMPRend2','BuildSPEngine','BuildSPGame','BuildSPRdVanilla')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):return {f.relative_to(p).as_posix():sha(f) for f in sorted(p.rglob('*')) if f.is_file() and '__pycache__' not in f.parts}
def patch(p,old,new):
    s=p.read_text();assert s.count(old)==1,(p,old,s.count(old));p.write_text(s.replace(old,new))
def prepare():
    state=json.loads((BASE/'manifest.json').read_text())
    for kind in ('engine','frontend'):
        assert tree(BASE/kind)==state['sources'][kind], 'Baseline source drift: '+kind
        dest=OUT/kind
        if not dest.exists():shutil.copytree(BASE/kind,dest)
        # Regenerate only files owned by this overlay, from the immutable baseline.
        paths=['codemp/ui/ui_public.h']
        paths+=['codemp/client/cl_uiapi.cpp','codemp/client/cl_input.cpp','codemp/client/cl_keys.cpp','shared/sdl/sdl_input.cpp'] if kind=='engine' else ['codemp/ui/ui_main.c','codemp/ui/ui_atoms.c']
        for name in paths:shutil.copy2(BASE/kind/name,dest/name)
        for name in ('st_controls_api.h','st_controls_catalog.h'):shutil.copy2(SRC/name,dest/'codemp/ui'/name)
        public=dest/'codemp/ui/ui_public.h'
        patch(public,'#define UI_API_VERSION 283','#define UI_API_VERSION 284')
        patch(public,'typedef struct uiImport_s {','#include "st_controls_api.h"\n\ntypedef struct uiImport_s {')
        patch(public,'} uiImport_t;','\tint (*Controls)(const stcRequest_t*, stcReply_t*);\n} uiImport_t;')
        if kind=='engine':
            for name in ('cl_st_controls.inc','cl_st_controller.inc','st_controls_core.h'):shutil.copy2(SRC/name,dest/'codemp/client'/name)
            shutil.copy2(SRC/'st_controller.inc',dest/'shared/sdl/st_controller.inc')
            p=dest/'codemp/client/cl_uiapi.cpp'
            patch(p,'void CL_BindUI( void ) {','#include "cl_st_controls.inc"\n\nvoid CL_BindUI( void ) {')
            patch(p,'GetUIAPI = (GetUIAPI_t)uivm->GetModuleAPI;', '#ifdef ST_CONTROLS_QA\n\tCmd_AddCommand("st_controlskey",STC_QAKey_f,"Controls regression input");\n#endif\n\tGetUIAPI = (GetUIAPI_t)uivm->GetModuleAPI;')
            patch(p,'ret = GetUIAPI( UI_API_VERSION, &uii );','uii.Controls = STC_Controls;\n\tret = GetUIAPI( UI_API_VERSION, &uii );')
            p=dest/'codemp/client/cl_keys.cpp'
            patch(p,'static qboolean CL_BindUICommand( const char *cmd ) {','extern bool STC_IsCapturing();\nstatic qboolean CL_BindUICommand( const char *cmd ) {\n\tif ((Key_GetCatcher() & KEYCATCH_UI) && STC_IsCapturing()) return qfalse;')
            p=dest/'codemp/client/cl_input.cpp'
            patch(p,'void CL_JoystickMove( usercmd_t *cmd ) {','#include "cl_st_controller.inc"\nvoid CL_JoystickMove( usercmd_t *cmd ) {\n\tif (STPadMove(cmd)) return;')
            p=dest/'shared/sdl/sdl_input.cpp'
            patch(p,'static void IN_JoyMove( void )','#include "st_controller.inc"\nstatic void IN_JoyMove( void )')
            patch(p,'static void IN_JoyMove( void )\n{','static void IN_JoyMove( void )\n{\n\tif (STPadFrame()) return;')
            patch(p,'static void IN_ShutdownJoystick( void )\n{','static void IN_ShutdownJoystick( void )\n{\n\tSTPadClose();')
        else:
            for name in ('ui_st_controls.inc','ui_st_controls_draw.inc','ui_st_controls_modals.inc'):shutil.copy2(SRC/name,dest/'codemp/ui'/name)
            p=dest/'codemp/ui/ui_main.c'
            patch(p,'static void UI_RunMenuScript(char **args)\n{','#include "ui_st_controls.inc"\n\nstatic void UI_RunMenuScript(char **args)\n{')
            patch(p,'\tuiInfo.uiDC.runScript\t\t\t\t\t\t= &UI_RunMenuScript;', '#ifdef ST_CONTROLS_QA\n\ttrap->ext.AddCommand("st_controlsqa");\n#endif\n\tuiInfo.uiDC.runScript\t\t\t\t\t\t= &UI_RunMenuScript;')
            patch(p,'\t\tST_UIPresentation();','\t\tST_UIPresentation();\n\t\tSCUI_Draw();')
            patch(p,'void UI_KeyEvent( int key, qboolean down ) {','void UI_KeyEvent( int key, qboolean down ) {\n\tif (SCUI_Key(key,down)) return;')
            patch(p,'\t\tDisplay_MouseMove(NULL, uiInfo.uiDC.cursorx, uiInfo.uiDC.cursory);','\t\tif (SCUI_IsMenu()) {SCUI_Mouse();return;}\n\t\tDisplay_MouseMove(NULL, uiInfo.uiDC.cursorx, uiInfo.uiDC.cursory);')
            p=dest/'codemp/ui/ui_atoms.c'
            patch(p,'qboolean UI_ConsoleCommand( int realTime ) {','#ifdef ST_CONTROLS_QA\nextern qboolean ST_ControlsQA(void);\n#endif\nqboolean UI_ConsoleCommand( int realTime ) {\n#ifdef ST_CONTROLS_QA\n\tif(ST_ControlsQA()) return qtrue;\n#endif')
    receipt={'baseline_manifest':sha(BASE/'manifest.json'),'inputs':tree(SRC),'sources':{k:tree(OUT/k) for k in ('engine','frontend')}}
    (OUT/'source-receipt.json').write_text(json.dumps(receipt,indent=2))
    print('Controls source prepared; baseline and normal installation untouched.',flush=True)
def build(kind,qa=False):
    folder=OUT/('build-'+kind+('-qa' if qa else ''))
    args=['cmake','-S',str(OUT/kind),'-B',str(folder),'-G','Visual Studio 18 2026','-A','x64','-DST_DEPS='+str(ROOT/'dist/handedness-baseline-06/deps'),'-DST_STAFF_QA=OFF']
    args+=['-D'+f+'='+('ON' if f==('BuildMPEngine' if kind=='engine' else 'BuildMPUI') else 'OFF') for f in FLAGS]
    args+=['-DCMAKE_CXX_FLAGS='+('/DST_CONTROLS_QA' if qa else '')]
    subprocess.run(args,check=True)
    subprocess.run(['cmake','--build',str(folder),'--config','Release','--parallel','6'],check=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--build',choices=['engine','frontend']);p.add_argument('--qa',action='store_true');a=p.parse_args()
    if a.prepare:prepare()
    if a.build:build(a.build,a.qa)
