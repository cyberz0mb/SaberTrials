"""Add the emote catalog, wheel, editor and cosmetic server state."""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent


def edit(path, old, new):
    source = path.read_text(encoding='utf8')
    assert source.count(old) == 1, (path, old)
    path.write_text(source.replace(old, new), encoding='utf8', newline='\n')


def copy(name, destination):
    shutil.copyfile(HERE/name, destination/name)


def wire_pad_wheel(sdl):
    edit(sdl,'static bool STPadFrame(bool focused) {',
         'extern bool CL_EmoteWheelActive();\n\nstatic bool STPadFrame(bool focused) {')
    edit(sdl,' if((menu||consoleKeyboard)&&focused){',
         ' if(focused&&CL_EmoteWheelActive()){\n'
         '  STPadPointer(values[2],values[3],Sys_Milliseconds(),Com_Clamp(1,10,cursorSpeed->value));\n'
         ' }else if((menu||consoleKeyboard)&&focused){')


def apply(engine, frontend, game):
    for root in (engine,frontend,game):
        copy('st_emotes.h', root/'codemp/qcommon')

    common = engine/'codemp/qcommon'
    client = engine/'codemp/client'
    copy('fs_st_emotes.inc', common)
    copy('cl_st_emotes.inc', client)
    edit(common/'files.cpp', 'long FS_ReadFile( const char *qpath, void **buffer ) {',
         '#include "fs_st_emotes.inc"\n\nlong FS_ReadFile( const char *qpath, void **buffer ) {')
    edit(common/'files.cpp', '\t// look for it in the filesystem or pack files\n\tlen = FS_FOpenFileRead( qpath, &h, qfalse );',
         '\tconst long emoteBytes = FS_ReadEmoteGla(qpath,buffer);\n'
         '\tif (emoteBytes >= 0) return emoteBytes;\n\t// look for it in the filesystem or pack files\n'
         '\tlen = FS_FOpenFileRead( qpath, &h, qfalse );')
    edit(common/'files.cpp', '\tFS_ReorderPurePaks();\n\n\t// print the current search paths',
         '\tFS_ReorderPurePaks();\n\tFS_LoadEmotes();\n\n\t// print the current search paths')
    edit(client/'cl_keys.cpp', 'void CL_KeyEvent (int key, qboolean down, unsigned time) {',
         '#include "../game/bg_public.h"\n#include "cl_st_emotes.inc"\n\n'
         'void CL_KeyEvent (int key, qboolean down, unsigned time) {\n'
         '\tif (CL_EmoteKey(key,down,time)) return;')
    edit(client/'cl_keys.cpp', 'void CL_GamepadButtonEvent(int button,qboolean down,unsigned time) {CL_GamepadButton(button,down,time);}',
         'void CL_GamepadButtonEvent(int button,qboolean down,unsigned time) {\n'
         ' if(!CL_EmotePadButton(button,down,time))CL_GamepadButton(button,down,time);\n}')
    edit(client/'cl_keys.cpp','void Key_ClearStates( void ) {',
         'void Key_ClearStates( void ) {\n\tCL_EmoteClose(false);\n'
         '\tstd::fill_n(stWheelConsumed,MAX_KEYS,false);')
    edit(client/'cl_keys.cpp','void CL_GamepadPointerEvent(int dx,int dy) {CL_GamepadPointer(dx,dy);}',
         'void CL_GamepadPointerEvent(int dx,int dy) {\n'
         ' if(CL_EmoteWheelActive())UIVM_MouseEvent(dx,dy);else CL_GamepadPointer(dx,dy);\n}')
    edit(client/'cl_input.cpp','void CL_MouseEvent( int dx, int dy, int time ) {',
         'extern bool CL_EmoteWheelActive();\n\nvoid CL_MouseEvent( int dx, int dy, int time ) {\n'
         '\tif (CL_EmoteWheelActive()) { UIVM_MouseEvent(dx,dy); return; }')
    edit(client/'cl_st_controller.inc',' cl.viewangles[YAW]-=',
         ' if(CL_EmoteWheelActive())return true;\n cl.viewangles[YAW]-=')
    wire_pad_wheel(engine/'shared/sdl/st_controller.inc')
    edit(client/'cl_main.cpp','void CL_Init( void ) {','extern void CL_EmotesInit();\nvoid CL_Init( void ) {')
    edit(client/'cl_main.cpp','\tCL_InitInput ();','\tCL_InitInput ();\n\tCL_EmotesInit();')
    edit(client/'cl_scrn.cpp','\tif ( Key_GetCatcher( ) & KEYCATCH_UI && cls.uiStarted ) {',
         '\textern bool CL_EmoteWheelActive();\n'
         '\tif ( CL_EmoteWheelActive() || (Key_GetCatcher() & KEYCATCH_UI && cls.uiStarted) ) {')

    ui = frontend/'codemp/ui'
    copy('ui_st_emotes.inc',ui)
    edit(ui/'ui_st_profile.inc', '#include "ui_st_profile_actions.inc"',
         '#include "ui_st_emotes.inc"\n#include "ui_st_profile_actions.inc"')
    edit(ui/'ui_st_profile.inc','if(spName.active){SPN_Key(key,down);return qtrue;}',
         'if(emui.editing){EM_EditorKey(key,down);return qtrue;}\n if(spName.active){SPN_Key(key,down);return qtrue;}')
    edit(ui/'ui_st_profile_actions.inc',' if(id>=110&&id<=112)',
         ' if(id==419) EM_EditorOpen();\n else if(id>=110&&id<=112)')
    edit(ui/'ui_st_profile_draw.inc', ' RUI_Shell();',
         ' if(emui.editing){EM_DrawEditor();return;}\n RUI_Shell();')
    edit(ui/'ui_st_profile_draw.inc',' SPUI_Button(402,identityY,65,22,"Customize",421);',
         ' SPUI_Button(360,identityY,60,22,"Emotes",419);\n'
         ' SPUI_Button(424,identityY,65,22,"Customize",421);')
    edit(ui/'ui_st_profile_draw.inc','SPUI_Button(473,identityY,62,22,"Sabers",510',
         'SPUI_Button(493,identityY,59,22,"Sabers",510')
    edit(ui/'ui_st_profile_draw.inc','SPUI_Button(541,identityY,77,22,"Force",511',
         'SPUI_Button(556,identityY,62,22,"Force",511')
    edit(ui/'ui_st_profile_draw.inc','spui.wide&&UI_TrueJediEnabled()?30:96','spui.wide&&UI_TrueJediEnabled()?30:79')
    edit(ui/'ui_st_profile_draw.inc','SPUI_Button(310,identityY,86,22','SPUI_Button(307,identityY,49,22')
    edit(ui/'ui_main.c','\tUI_RegisterCvars();','\tUI_RegisterCvars();\n\tEM_Init();')
    edit(ui/'ui_main.c','\tUI_UpdateCvars();\n trap->Cvar_Set("st_handProtocol"',
         '\tUI_UpdateCvars();\n\tif(EM_WheelOpen()){EM_WheelDraw();return;}\n\temui.wheel=false;\n'
         '\tif(emui.editing&&!SPUI_IsMenu())emui.editing=false;\n trap->Cvar_Set("st_handProtocol"')
    edit(ui/'ui_main.c','void UI_KeyEvent( int key, qboolean down ) {',
         'void UI_KeyEvent( int key, qboolean down ) {\n\tif(EM_WheelOpen()){EM_WheelKey(key,down);return;}')
    edit(ui/'ui_main.c','\t// update mouse screen position\n\tuiInfo.uiDC.cursorx += dx;',
         '\tif(EM_WheelOpen()){EM_WheelMove(dx,dy);return;}\n'
         '\t// update mouse screen position\n\tuiInfo.uiDC.cursorx += dx;')
    edit(ui/'ui_main.c','if (SPUI_IsMenu()) {SPUI_Mouse();return;}',
         'if (SPUI_IsMenu()) {if(emui.editing)spui.mouse=true;else SPUI_Mouse();return;}')
    edit(ui/'ui_atoms.c','qboolean UI_ConsoleCommand( int realTime ) {',
         'extern qboolean ST_EmoteUIQA(void);\nqboolean UI_ConsoleCommand( int realTime ) {\n'
         '\tif(ST_EmoteUIQA()) return qtrue;')
    for catalog in (engine/'codemp/ui/st_controls_catalog.h', ui/'st_controls_catalog.h'):
        pause = ' {"Pause menu","togglemenu","Camera / UI","Open or close the in-game menu",0}'
        edit(catalog,pause,pause+',\n {"Emote Wheel","+st_emotewheel","Communication","Open the emote wheel",0}')
    edit(ui/'ui_st_controls.inc','static void SCUI_Result(stcReply_t r)',
         'static bool SCUI_CanSwap(){\n'
         ' if(scui.key>=0)return true;\n'
         ' const auto row=SCUI_Call(STC_ACTIONINFO,scui.action,0,0,NULL,NULL);\n'
         ' return row.status>0&&(scui.slot?row.c:row.b)>=0;\n}\n'
         'static void SCUI_Result(stcReply_t r)')
    edit(ui/'ui_st_controls_modals.inc','if(scui.modal==2){SCUI_Button(310',
         'if(scui.modal==2){if(SCUI_CanSwap())SCUI_Button(310')

    cgame = frontend/'codemp/cgame'
    shutil.copyfile(HERE/'cg_st_emotes.inc',cgame/'cg_st_emotes.cpp')
    edit(cgame/'CMakeLists.txt','add_library(${MPCGame} SHARED ${MPCGameFiles})',
         'add_library(${MPCGame} SHARED ${MPCGameFiles} "${MPDir}/cgame/cg_st_emotes.cpp")')
    edit(cgame/'cg_main.c','void CG_Init( int serverMessageNum, int serverCommandSequence, int clientNum )\n{',
         'extern void CG_EmotesInit(void);\nvoid CG_Init( int serverMessageNum, int serverCommandSequence, int clientNum )\n{\n\tCG_EmotesInit();')
    edit(cgame/'cg_players.c','static void CG_PlayerAnimation( centity_t *cent,',
         'extern qboolean CG_EmotePose(centity_t *cent, qboolean torsoOnly);\n\nstatic void CG_PlayerAnimation( centity_t *cent,')
    edit(cgame/'cg_players.c','\tif (!PM_RunningAnim(cent->currentState.legsAnim) &&',
         '\tif (CG_EmotePose(cent,qfalse)) {\n\t\t*legsOld = *legs = *torsoOld = *torso = 0;\n'
         '\t\t*legsBackLerp = *torsoBackLerp = 0;\n\t\treturn;\n\t}\n\n'
         '\tif (!PM_RunningAnim(cent->currentState.legsAnim) &&')
    edit(cgame/'cg_players.c','\t// If this is not a vehicle, you may lerm the frame',
         '\tif (CG_EmotePose(cent,qtrue)) {\n\t\t*torsoOld = *torso = 0;\n'
         '\t\t*torsoBackLerp = 0;\n\t\treturn;\n\t}\n\n'
         '\t// If this is not a vehicle, you may lerm the frame')

    source = game/'codemp/game'
    shutil.copyfile(HERE/'g_st_emotes.inc',source/'g_st_emotes.cpp')
    edit(source/'CMakeLists.txt','add_library(${MPGame} SHARED ${MPGameFiles})',
         'add_library(${MPGame} SHARED ${MPGameFiles} "${MPDir}/game/g_st_emotes.cpp")')
    edit(source/'g_cmds.c','command_t commands[] = {',
         'extern void Cmd_STEmote_f(gentity_t *ent);\n\ncommand_t commands[] = {\n'
         '\t{"st_emote", Cmd_STEmote_f, CMD_NOINTERMISSION | CMD_ALIVE},')
    edit(source/'g_xcvar.h','XCVAR_DEF( st_tournamentBestOf,',
         'XCVAR_DEF( g_stEmotes, "1", NULL, CVAR_ARCHIVE, qfalse )\nXCVAR_DEF( st_tournamentBestOf,')
    edit(source/'g_main.c','void G_RunFrame\t\t\t\t\t( int levelTime );',
         'void G_RunFrame( int levelTime );\nextern void G_EmotesInit();\nextern void G_EmotesFrame();')
    edit(source/'g_main.c','\tG_UpdateCvars();','\tG_UpdateCvars();\n\tG_EmotesFrame();')
    edit(source/'g_main.c','\tG_RegisterCvars();','\tG_RegisterCvars();\n\tG_EmotesInit();')
    edit(source/'g_client.c','void ClientDisconnect( int clientNum ) {',
         'extern void G_EmoteInterrupt(gentity_t* ent);\nvoid ClientDisconnect( int clientNum ) {\n'
         '\tG_EmoteInterrupt(&g_entities[clientNum]);')
