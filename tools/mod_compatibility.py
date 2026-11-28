"""Apply stock OpenJK module ABI and external emote support to the release tree."""
from pathlib import Path
import shutil


def apply_profile(ui, baseline):
    assets = Path(__file__).resolve().parents[1] / "development-source/compatibility"
    shutil.copyfile(assets / "ja_wheel.h", ui / "ja_wheel.h")
    profile = (baseline / "ui_st_profile.inc").read_text()
    shutil.copyfile(assets / "ja_preview.inc", ui / "ja_preview.inc")
    (ui / "ui_st_profile.inc").write_text(profile)
    source = (baseline / "ui_st_emotes.inc").read_text()
    changes = [
        ('#include "qcommon/st_emotes.h"', '#include "qcommon/st_emotes.h"\n#include "ja_wheel.h"\n#include "ja_preview.inc"\nstatic bool jaEditor;'),
        ('static std::string EM_Slot(int slot) {', '''static std::string EM_Slot(int slot) {
    if (emui.editing && jaEditor) {
        const auto value = SPUI_Var(jawheel::slotVar(emui.group*jawheel::slots + slot));
        return value == "-" ? "" : value;
    }'''),
        ('static void EM_EditorOpen() {', '''static void EM_EditorOpen(bool ja = false) {
    jaEditor = ja;'''),
        ('emui.editing = true;\n    emui.clips = stemote::catalog(trap->Cvar_VariableStringBuffer);', '''emui.editing = true;
    emui.clips = jaEditor ? EM_JaCatalog() : stemote::catalog(trap->Cvar_VariableStringBuffer);'''),
        ('if (stemote::sharedGla(gla)) {','if (clip.frames>0 && stemote::sharedGla(gla)) {'),
        ('SCUI_Centered(466,348,152,21,.58f,clip.label.c_str(),scuText);','''if (jaEditor && !clip.frames)
        SCUI_Centered(460,321,164,21,.46f,"Animation pack unavailable",scuMuted);
    SCUI_Centered(466,348,152,21,.58f,clip.label.c_str(),scuText);'''),
        ('SCUI_Text(24,53,.89f,"Emotes",scuText);', '''SCUI_Text(24,53,.89f,"Emotes",scuText);
    EM_Button(294,48,152,25,"Saber Trials wheel",12,0,!jaEditor);
    EM_Button(455,48,161,25,"JA+ wheel",12,1,jaEditor);'''),
        ('const auto label = SPUI_Var(stemote::nameVar(group).c_str());', 'const std::string label = jaEditor ? va("Page %d",group+1) : SPUI_Var(stemote::nameVar(group).c_str());'),
        ('EM_Button(491,88,125,24,"Rename group",2);', 'if (!jaEditor) EM_Button(491,88,125,24,"Rename group",2);'),
        ('if (id == 1) {', 'if (id == 12) { if (jaEditor != (arg != 0)) EM_EditorOpen(arg != 0); return; }\n    if (id == 1) {'),
        ('if (id == 5 || id == 6) trap->Cvar_Set', '''if ((id == 5 || id == 6) && jaEditor) {
        const int slot = emui.group * jawheel::slots + emui.slot;
        const char *idText = id == 5 ? emui.clips[emui.selected].id.c_str() : "-";
        trap->Cmd_ExecuteText(EXEC_NOW,va("st_jaWheelAssign %d %s",slot+1,idText));
        emui.status = trap->Cvar_VariableValue("ui_stJaWheelSaved") ? "Saved" : "Could not save wheel";
    } else if (id == 5 || id == 6) trap->Cvar_Set'''),
        ('} else if (!Q_stricmp(operation,"rename") && emui.editing) {', '''} else if (!Q_stricmp(operation,"action") && emui.editing) {
        char arg[16];
        trap->Cmd_Argv(3,arg,sizeof(arg));
        for (const auto &hit : emui.hits) {
            if (hit.id == atoi(index) && hit.arg == atoi(arg)) {
                EM_EditorAction(hit.id,hit.arg);
                break;
            }
        }
    } else if (!Q_stricmp(operation,"rename") && emui.editing) {''')]
    for old, new in changes:
        if source.count(old) != 1:
            raise ValueError(f"Profile editor anchor changed: {old}")
        source = source.replace(old,new)
    (ui / "ui_st_emotes.inc").write_text(source)


def apply_compatibility(client, baseline):
    assets = Path(__file__).resolve().parents[1] / "development-source/compatibility"
    for file in assets.glob("*.inc"):
        shutil.copyfile(file, client / file.name)
    shutil.copyfile(assets / "ja_wheel.h",client / "ja_wheel.h")

    def edit(name, changes):
        path = client / name
        source = (baseline / name).read_text()
        for old, new in changes:
            if source.count(old) != 1:
                raise ValueError(f"{name}: expected one occurrence of {old}")
            source = source.replace(old, new)
        if path.read_text() != source:
            path.write_text(source)

    decl = "void CL_SetCGameTime( void );"
    edit("client.h", [(decl, decl + """
inline bool CL_TrialsGame() { return !Q_stricmp(Cvar_VariableString("fs_game"), "SaberTrials"); }
void CL_RememberGameSwitch(const char *next);
void CL_EmoteWheelMove(int dx,int dy);
void CL_DrawForeignWheel();
void CL_DrawForeignChat();
void CL_ResetPersonalArt();
qhandle_t CL_PersonalArt(const char*);
void CL_PersonalPic(const char*,float,float,float,float);
float CL_PersonalText(const char*,float,float,float,const float*,bool);
bool CL_PersonalPauseActive();
void CL_PersonalStatus();
void CL_PersonalFrame();
void CL_ForeignChatStatus();
""")])
    legacy = 'Com_Error(ERR_FATAL,"Saber Trials feint candidate requires matching native modules; legacy modules are not compatible.");\n\treturn;'
    def legacy_guard(flag):
        return f'''if (CL_TrialsGame()) {{
            cls.{flag}Started = qfalse;
            Com_Error(ERR_FATAL, "Saber Trials requires matching native {flag} modules.");
        }}'''
    failure = 'Com_Error( ERR_FATAL, "GetGameAPI failed on %s", dllName );'
    def bad_module(vm):
        return f'''VM_Free({vm});
            {vm} = NULL;
            Com_Error(cls.state >= CA_CONNECTED ? ERR_DROP : ERR_FATAL,
                      "Incompatible native module %s for %s", dllName, FS_GetCurrentGameDir(false));'''
    edit("cl_cgameapi.cpp", [
        ('#include "cl_st_menu_font.inc"', '#include "cl_st_menu_font.inc"\n#include "stock_snapshot.inc"\n#include "foreign_art.inc"\n#include "foreign_chat.inc"'),
        ('cgi.Print\t\t\t\t\t\t\t\t= Com_Printf;', 'cgi.Print = CL_TrialsGame() ? Com_Printf : foreignChat::print;'),
        ('= Cvar_Register;', '= CL_TrialsGame() ? Cvar_Register : foreignChat::reg;'),
        ('= Cvar_Update;', '= CL_TrialsGame() ? Cvar_Update : foreignChat::update;'),
        ('Com_Printf( "%s", (const char*)VMA(1) );','foreignChat::print("%s", (const char*)VMA(1));'),
        ('Cvar_Register( (vmCvar_t *)VMA(1)', 'foreignChat::reg( (vmCvar_t *)VMA(1)'),
        ('Cvar_Update( (vmCvar_t *)VMA(1)', 'foreignChat::update( (vmCvar_t *)VMA(1)'),
        ('STTR_Reset();STCT_Reset();', 'STTR_Reset();STCT_Reset();foreignChat::reset();'),
        ('qboolean CGVM_ConsoleCommand( void ) {','''qboolean CGVM_ConsoleCommand( void ) {
    if (!CL_TrialsGame() && !Q_stricmp(Cmd_Argv(0),"st_togglechat") && foreignChat::enabled()) {
        foreignChat::hidden=!foreignChat::hidden;
        foreignChat::expanded=!foreignChat::hidden;
        return qtrue;
    }'''),
        ('= CL_GetSnapshot;', '= CL_TrialsGame() ? CL_GetSnapshot : CL_GetStockSnapshot;'),
        ('return CL_GetSnapshot( args[1]', 'return CL_GetStockSnapshot( args[1]'),
        ('GetCGameAPI( CGAME_API_VERSION,', 'GetCGameAPI( CL_TrialsGame() ? CGAME_API_VERSION : 2,'),
        (failure, bad_module("cgvm")),
        (legacy, legacy_guard("cgame"))])
    edit("cl_uiapi.cpp", [
        ('#include "cl_st_controls.inc"', '#include "cl_st_controls.inc"\n#include "ja_wheel_profile.inc"\n#include "full_ui.inc"'),
        ('void UIVM_Init( qboolean inGameLoad ) {','''static bool PersonalMenu(uiMenuCommand_t);
static void PersonalKey(int);
static void PersonalMouse(int,int);
static void PersonalDraw();
static qboolean PersonalFullscreen();
static void PersonalReset();
void UIVM_Init( qboolean inGameLoad ) {'''),
        ('void UIVM_Shutdown( void ) {','void UIVM_Shutdown( void ) {\n    PersonalReset();'),
        ('void UIVM_KeyEvent( int key, qboolean down ) {','void UIVM_KeyEvent( int key, qboolean down ) {\n    if (CL_PersonalPauseActive()) {if(down) PersonalKey(key);return;}'),
        ('void UIVM_MouseEvent( int dx, int dy ) {','void UIVM_MouseEvent( int dx, int dy ) {\n    if (CL_PersonalPauseActive()) { PersonalMouse(dx,dy);return;}'),
        ('void UIVM_Refresh( int realtime ) {','void UIVM_Refresh( int realtime ) {\n    if(CL_PersonalPauseActive()) {PersonalDraw();return;}'),
        ('qboolean UIVM_IsFullscreen( void ) {','qboolean UIVM_IsFullscreen( void ) {\n    if(CL_PersonalPauseActive())return PersonalFullscreen();'),
        ('void UIVM_SetActiveMenu( uiMenuCommand_t menu ) {','void UIVM_SetActiveMenu( uiMenuCommand_t menu ) {\n    if(PersonalMenu(menu))return;'),
        ('GetUIAPI( UI_API_VERSION,', 'GetUIAPI( CL_TrialsGame() ? UI_API_VERSION : 3,'),
        (failure, bad_module("uivm")),
        (legacy, legacy_guard("ui"))])
    edit("cl_main.cpp", [('void CL_FlushMemory( void ) {', """
static bool returnToTrials;
void CL_RememberGameSwitch(const char *next) {
    if (CL_TrialsGame() && Q_stricmp(next, "SaberTrials")) returnToTrials = true;
}

void CL_FlushMemory( void ) {"""),
        ('CL_ShutdownAll( qfalse );', '''CL_ShutdownAll( qfalse );
    if (returnToTrials && cls.state == CA_DISCONNECTED) {
        returnToTrials = false;
        Cvar_Set("fs_game", "SaberTrials");
        FS_ConditionalRestart(0);
    }'''),
        ('    CL_StaffFrame();', '    if (CL_TrialsGame()) CL_StaffFrame();'),
        ('if (CL_StaffPacket(from))', 'if (CL_TrialsGame() && CL_StaffPacket(from))')])
    edit("cl_parse.cpp", [
        ('char next;','int next;'),
        ('next = MSG_ReadByte( msg );','next = MSG_ReadByte( msg );\n\t\tif (next < 0) Com_Error(ERR_DROP, "Truncated server game directory");'),
        ('newGameDir[i] = 0;', 'if (i == MAX_QPATH) Com_Error(ERR_DROP, "Server game directory too long");\n\tnewGameDir[i] = 0;'),
        ('if(!FS_FilenameCompare(newGameDir, BASEGAME))', 'CL_RememberGameSwitch(newGameDir);\n\tif(!FS_FilenameCompare(newGameDir, BASEGAME))'),
        ('gameSet = qtrue;', 'CL_RememberGameSwitch(value);\n\t\t\tgameSet = qtrue;'),
        ('Cvar_Set( "fs_game", "" );', 'CL_RememberGameSwitch("");\n\t\tCvar_Set( "fs_game", "" );')])
    edit("cl_input.cpp", [
        ('if (CL_EmoteWheelActive()) { UIVM_MouseEvent', 'if (CL_EmoteWheelActive()) { CL_EmoteWheelMove'),
        ('"Directional feint", IN_Button12Down', '"Directional feint", [] { if (CL_TrialsGame()) IN_Button12Down(); }'),
        ('"Manual saber block", IN_Button13Down', '"Manual saber block", [] { if (CL_TrialsGame()) IN_Button13Down(); }'),
        ('\tCL_ASFrame();','\tif (CL_TrialsGame()) CL_ASFrame();')])
    edit("cl_cgame.cpp", [('if (CL_AccountServerCommand())', 'if (CL_TrialsGame() && CL_AccountServerCommand())')])
    edit("cl_keys.cpp", [('if(CL_EmoteWheelActive())UIVM_MouseEvent','if(CL_EmoteWheelActive())CL_EmoteWheelMove')])
    edit("cl_scrn.cpp", [('CL_NetDraw();','if (!CL_TrialsGame()) {CL_PersonalFrame(); CL_DrawForeignChat();}\n\t\t\tCL_NetDraw();'), ('if ( CL_EmoteWheelActive() ||',
        'if (CL_EmoteWheelActive() && !CL_TrialsGame()) CL_DrawForeignWheel();\n\telse if ( CL_EmoteWheelActive() ||')])
    edit("cl_st_emotes.inc", [
        ('static int stWheelKey', '#include "foreign_wheel.inc"\nstatic int stWheelKey'),
        ('void CL_EmotesInit() {', 'void CL_EmotesInit() {\n    CL_JaProfileInit();\n    Cmd_AddCommand("st_personalStatus",CL_PersonalStatus);'),
        ('if (confirm) {', 'if (confirm && !CL_TrialsGame()) CL_ForeignPlay(CL_AssignedIndex(foreignSlot));\n    else if (confirm) {'),
        ('const auto clips =', '''if (!CL_TrialsGame()) {
        int count = CL_ForeignCount();
        for (int i = 0; i < count; ++i) {
            if (!Q_stricmp(id,CL_ForeignChoice(i).command)) { CL_ForeignPlay(i); return; }
        }
        return;
    }
    const auto clips ='''),
        ('UIVM_KeyEvent(A_HOME,qtrue);', 'if (CL_TrialsGame()) UIVM_KeyEvent(A_HOME,qtrue);\n        else { foreignPage = 0; foreignSlot = -1; wheelX = wheelY = 0; }'),
        ('else UIVM_KeyEvent(key,qtrue);','else if (CL_TrialsGame()) UIVM_KeyEvent(key,qtrue);\n    else CL_ForeignKey(key);')])
    edit("cl_st_menu_font.inc", [
        ("ST_MenuTextureCount = 192", "ST_MenuTextureCount = 128"),
        ("void STML_ResetFont() {","void STML_ResetFont() {\n    CL_ResetPersonalArt();")])
    edit("cl_st_setup.inc", [
        ("static void SS_Open(){", """static const char *SS_ModRestriction(const char *name) {
 if(CL_TrialsGame())return "";
 if(!Q_stricmp(name,"st_hudStyle")||!Q_stricmpn(name,"st_portrait",11)||!Q_stricmp(name,"st_notifications"))
  return "The connected mod supplies this HUD.";
 if(!Q_stricmpn(name,"st_streamer",11)||!Q_stricmp(name,"st_cameraShoulder"))
  return "Requires Saber Trials spectator or camera support.";
 return "";
}
static void SS_Open(){"""),
        ("if(!SS_Cvar(s.name)&&s.tab!=0)", "if(!SS_Cvar(s.name)&&s.tab!=0&&!*SS_ModRestriction(s.name))"),
        ("auto& s=ssSettings[i];auto flags=Cvar_Flags(s.name);",
         "auto& s=ssSettings[i];if(*SS_ModRestriction(s.name))return SS_ModRestriction(s.name);auto flags=Cvar_Flags(s.name);")])
    edit("cl_st_pad_menu.inc", [
        ('else if(button>=11&&button<=14&&!Cvar_VariableIntegerValue("st_uiNameKeyboard"))return;',
         '''else if(button>=11&&button<=14&&CL_PersonalPauseActive()){
    const int keys[]={A_CURSOR_UP,A_CURSOR_DOWN,A_CURSOR_LEFT,A_CURSOR_RIGHT};key=keys[button-11];
   }else if(button>=11&&button<=14&&!Cvar_VariableIntegerValue("st_uiNameKeyboard"))return;''')])
