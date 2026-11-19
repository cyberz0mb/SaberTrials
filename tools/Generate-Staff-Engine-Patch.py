"""Maintainer utility: regenerate narrow staff hooks against --prepare-only source.

Run on a preparation with the staff patch temporarily excluded, not a production
installation. Build-Staff applies the resulting reviewed patch normally.
"""
from pathlib import Path
import difflib
import importlib.util
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'dist/staff-work/OpenJK-1a6a643427aa347553e9073dac5570b33337c4d9'
spec=importlib.util.spec_from_file_location('staff_build',ROOT/'tools/Build-Staff.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
helper.prepare(False,patches=False)
patch=[]
def edit(name,replacements):
    path=SOURCE/name;before=path.read_text();after=before
    for old,new in replacements:
        if after.count(old)!=1:raise RuntimeError(f'{name}: expected one hook {old[:65]!r}, got {after.count(old)}')
        after=after.replace(old,new,1)
    patch.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name,n=3))
edit('codemp/client/cl_main.cpp',[
 ('#include "client.h"','#include "client.h"\n#include "cl_staff.h"\n#include <string>'),
 ('\tc = Cmd_Argv( 0 );\n','\tif (CL_StaffPacket(from)) return;\n\tc = Cmd_Argv( 0 );\n'),
 ('void CL_Disconnect( qboolean showMainMenu ) {','void CL_Disconnect( qboolean showMainMenu ) {\n    CL_StaffReset();'),
 ('void CL_Frame ( int msec ) {','void CL_Frame ( int msec ) {\n    CL_StaffFrame();'),
 ('Cmd_AddCommand ("record", CL_Record_f, "Record a demo" );','CL_StaffInit();\n\tCmd_AddCommand ("record", CL_Record_f, "Record a demo" );'),
 ('void CL_Connect_f( void ) {\n\tchar\t*server;\n\tconst char\t*serverString;\n\n\tif ( Cmd_Argc() != 2 ) {\n\t\tCom_Printf( "usage: connect [server]\\n");\n\t\treturn;\n\t}\n',
  'void CL_ConnectAddress( const char* server ) {\n\tconst char *serverString;\n'),
 ('Cvar_Set("cl_reconnectArgs", Cmd_Args());','Cvar_Set("cl_reconnectArgs", server);'),
 ('\tserver = Cmd_Argv (1);\n',''),
 ('#define MAX_RCON_MESSAGE 1024','void CL_Connect_f(void) {\n if (Cmd_Argc()!=2) { Com_Printf("usage: connect [server]\\n"); return; }\n const std::string server = Cmd_Argv(1);\n CL_ConnectAddress(server.c_str());\n}\n\n#define MAX_RCON_MESSAGE 1024')
])
edit('codemp/client/cl_parse.cpp',[
 ('#include "client.h"','#include "client.h"\n#include "cl_staff.h"'),
 ('void CL_ParseGamestate( msg_t *msg ) {','void CL_ParseGamestate( msg_t *msg ) {\n CL_StaffReset();')
])
edit('codemp/client/cl_cgame.cpp',[
 ('#include "client.h"','#include "client.h"\n#include "cl_staff.h"'),
 ('if ( !strcmp( cmd, "map_restart" ) ) {','if ( !strcmp( cmd, "map_restart" ) ) {\n        CL_StaffReset();')
])
edit('codemp/server/sv_main.cpp',[
 ('#include "server.h"','#include "server.h"\n#include "sv_staff.h"'),
 ('\tc = Cmd_Argv(0);\n','\tif (SV_StaffPacket(from)) return;\n\tc = Cmd_Argv(0);\n')
])
edit('codemp/server/sv_ccmds.cpp',[
 ('#include "server.h"','#include "server.h"\n#include "sv_staff.h"'),
 ('Cmd_AddCommand ("heartbeat", SV_Heartbeat_f, "Sends a heartbeat to the masterserver" );',
  'if (com_dedicated->integer) Cmd_AddCommand("staff", SV_StaffConsole_f, "Permanent staff administration");\n\tCmd_AddCommand ("heartbeat", SV_Heartbeat_f, "Sends a heartbeat to the masterserver" );')
])
edit('codemp/server/sv_bot.cpp',[
 ('#include "server.h"','#include "server.h"\n#include "sv_staff.h"'),
 ('\t// cannot start recording auto demos here since bot\'s name is not set yet',
  '\t// Bots call ClientConnect inside the game module, bypassing GVM_ClientConnect.\n\tSV_StaffConnect(i,true);\n\t// cannot start recording auto demos here since bot\'s name is not set yet'),
 ('\tcl = &svs.clients[clientNum];\n\tcl->state = CS_FREE;',
  '\tSV_StaffDisconnect(clientNum);\n\tcl = &svs.clients[clientNum];\n\tcl->state = CS_FREE;')
])
edit('codemp/server/sv_gameapi.cpp',[
 ('#include "server.h"','#include "server.h"\n#include "sv_staff.h"\n#include "sys/sys_loadlib.h"'),
 ('static vm_t *gvm; // game vm, valid for legacy and new api', '''static vm_t *gvm; // game vm, valid for legacy and new api
static const STGameAPI* staffAPI;
int GVM_StaffExecute(const STVerifiedAction* action,STGameResult* result) {
 if(!gvm||gvm->isLegacy||!ST_ValidGameAPI(staffAPI))return 0;
 VMSwap v(gvm); return staffAPI->Execute(action,result);
}
int GVM_StaffResolve(const char* text,STTargetRef* target) {
 if(!gvm||gvm->isLegacy||!ST_ValidGameAPI(staffAPI))return 0;
 VMSwap v(gvm); return staffAPI->ResolveTarget(text,target);
}
void GVM_StaffRevoke(const char* account,int actorSlot) {
 if(gvm&&!gvm->isLegacy&&ST_ValidGameAPI(staffAPI)){ VMSwap v(gvm);staffAPI->Revoke(account,actorSlot); }
}
void GVM_StaffReset() {
 if(gvm&&!gvm->isLegacy&&ST_ValidGameAPI(staffAPI)){ VMSwap v(gvm);staffAPI->ResetSessions(); }
}'''),
 ('void GVM_InitGame( int levelTime, int randomSeed, int restart ) {','void GVM_InitGame( int levelTime, int randomSeed, int restart ) {\n    SV_StaffReset();'),
 ('void GVM_ShutdownGame( int restart ) {','void GVM_ShutdownGame( int restart ) {\n    SV_StaffReset();'),
 ('char *GVM_ClientConnect( int clientNum, qboolean firstTime, qboolean isBot ) {','char *GVM_ClientConnect( int clientNum, qboolean firstTime, qboolean isBot ) {\n    SV_StaffConnect(clientNum,isBot!=qfalse);'),
 ('void GVM_ClientDisconnect( int clientNum ) {','void GVM_ClientDisconnect( int clientNum ) {\n    SV_StaffDisconnect(clientNum);'),
 ('void GVM_RunFrame( int levelTime ) {','void GVM_RunFrame( int levelTime ) {\n    SV_StaffFrame();'),
 ('\t\tge = ret;','''\t\tge = ret;
        GetSaberTrialsStaffAPI_t staffExport=(GetSaberTrialsStaffAPI_t)Sys_LoadFunction(gvm->dllHandle,"GetSaberTrialsStaffAPI");
        staffAPI=staffExport?staffExport(SV_StaffImports()):NULL;
        if(!ST_ValidGameAPI(staffAPI))staffAPI=NULL;'''),
 ('\t// fall back to legacy syscall/vm_call api','\tstaffAPI=NULL;\n\t// fall back to legacy syscall/vm_call api'),
 ('\tVM_Free( gvm );','\tstaffAPI=NULL;\n\tVM_Free( gvm );')
])
edit('codemp/qcommon/common.cpp',[
 ('static void Com_Freeze_f (void) {','''#ifndef DEDICATED
extern void CL_StaffCommand_f(void);
extern bool CL_StaffConnected(void);
#endif
static void Com_Freeze_f (void) {
#ifndef DEDICATED
    if (CL_StaffConnected()) { CL_StaffCommand_f(); return; }
#endif''')
])
edit('codemp/game/bg_pmove.c',[
 ('#include "bg_local.h"','#include "bg_local.h"\n#include "../staff/st_staff_movement.h"'),
 ('int\t\tumove = 0; //cmd->upmove;',
  'int\t\tumove = (pm->ps->pm_type == PM_NOCLIP && pm->ps->stats[ST_STAFF_STAT] == ST_STAFF_GHOST) ? cmd->upmove : 0;'),
 ('\tfinalTime = pmove->cmd.serverTime;', '''\t// Apply the same restrictions in server movement and local prediction.
\tif ((pmove->ps->pm_type == PM_FREEZE && pmove->ps->stats[ST_STAFF_STAT] == ST_STAFF_FROZEN) ||
\t    (pmove->ps->pm_type == PM_NOCLIP && pmove->ps->stats[ST_STAFF_STAT] == ST_STAFF_GHOST)) {
\t\tpmove->cmd.buttons &= BUTTON_TALK;
\t\tpmove->cmd.generic_cmd = 0;
\t\tif (pmove->ps->stats[ST_STAFF_STAT] == ST_STAFF_FROZEN)
\t\t\tpmove->cmd.forwardmove = pmove->cmd.rightmove = pmove->cmd.upmove = 0;
\t\telse
\t\t\tpmove->ps->pm_flags &= ~PMF_JUMP_HELD;
\t}
\tfinalTime = pmove->cmd.serverTime;''')
])
edit('shared/sys/con_win32.cpp',[
 ('\tGetConsoleScreenBufferInfo( qconsole_hout, &binfo );',
  '\t// Redirected output has no console screen buffer. Never use uninitialized dimensions.\n\tif( !GetConsoleScreenBufferInfo( qconsole_hout, &binfo ) )\n\t\treturn;'),
 ('\tGetConsoleScreenBufferInfo( qconsole_hout, &info );',
  '\tif( !GetConsoleScreenBufferInfo( qconsole_hout, &info ) )\n\t\treturn;')
])
patch_text=''.join(patch)
out=ROOT/'development-source/staff/patches/01-native-staff.patch';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(patch_text,newline='\n')
print(out)
