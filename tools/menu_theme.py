"""Install the menu-theme changes into the existing generated OpenJK trees."""
from pathlib import Path
import shutil

SOURCE = Path(__file__).resolve().parents[1] / "development-source/menu-theme"


def replace(path, old, new):
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if text.count(old) != 1:
        raise ValueError(f"Expected one menu-theme insertion point in {path}: {old[:80]}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def catalog(tree):
    path = tree / "codemp/ui/st_setup_catalog.h"
    start = ' {"st_personalChat",'
    replace(path, start, ' {"st_menuTheme","Menu Theme","Appearance","Choose the appearance of the menus.",'
            '"0=Classic JKA|1=Saber Trials","1",2,2,0,0,CVAR_ARCHIVE,0,1},\n' + start)


def engine(tree):
    catalog(tree)
    client = tree / "codemp/client"
    qc = tree / "codemp/qcommon"
    shutil.copyfile(SOURCE / "preference.inc", client / "menu_theme_pref.inc")
    replace(client / "shared_name.inc", "void CL_LoadSharedName(){",
            '#include "menu_theme_pref.inc"\n\nvoid CL_LoadSharedName(){\n    CL_LoadMenuTheme();')
    replace(client / "cl_st_setup.inc", "auto flags=Cvar_Flags(s.name);",
            'auto flags=Cvar_Flags(s.name);\n if(!Q_stricmp(s.name,"st_menuTheme"))flags &= ~CVAR_PROTECTED;')
    replace(client / "cl_st_setup.inc", " return STC_ValidSetting(name,value,error);",
            ' if(!Q_stricmp(name.c_str(),"st_menuTheme"))return value=="0" || value=="1";\n return STC_ValidSetting(name,value,error);')
    cvar = qc / "cvar.cpp"
    replace(cvar, "    if(var && Cbuf_ReadingPlayerConfig()", '''
    if (var && !Q_stricmp(var_name,"st_menuTheme") &&
        (Cbuf_ReadingPlayerConfig() || (value && strcmp(value,"0") && strcmp(value,"1")))) return var;
    if(var && Cbuf_ReadingPlayerConfig()''')
    replace(cvar, "    extern void CL_SaveSharedName(const char *);",
            '''    extern void CL_SaveMenuTheme(const char *);
    if (!Q_stricmp(var_name,"st_menuTheme")) CL_SaveMenuTheme(var->string);
    extern void CL_SaveSharedName(const char *);''')
    for function in ("Cvar_Server_Set", "Cvar_VM_Set"):
        text = cvar.read_text(encoding="utf-8")
        start = text.index("void " + function + "(")
        declaration = text[start:text.index("{",start)+1]
        replace(cvar, declaration, declaration + '\n#ifndef DEDICATED\n'
                '    if (!Q_stricmp(var_name,"st_menuTheme")) return;\n#endif')
    fs = qc / "files.cpp"
    replace(fs, "#ifndef DEDICATED\n    extern const byte *CL_PresentationFile", '''
    bool retailMenu = false;
#ifndef DEDICATED
    static const char prefix[] = "st_retail/";
    if (!Q_stricmpn(filename,prefix,sizeof(prefix)-1)) {
        filename += sizeof(prefix)-1;
        const char *ext = strrchr(filename,'.');
        retailMenu = !Q_stricmp(filename,"ui/jampmenus.txt") || !Q_stricmp(filename,"ui/jampingame.txt") ||
            !Q_stricmp(filename,"ui/jamp/menudef.h") || (!Q_stricmpn(filename,"ui/jamp/",8) &&
            !strpbrk(filename+8,"/\\\\") && ext && !Q_stricmp(ext,".menu"));
        if (!retailMenu) { *file = 0; return -1; }
    }
    extern const byte *CL_PresentationFile''')
    replace(fs, "if(const byte *data=CL_PresentationFile(filename,&builtinLength))",
            "if(const byte *data=retailMenu ? nullptr : CL_PresentationFile(filename,&builtinLength))")
    replace(fs, "if ( search->pack ) {\n\t\t\t\thash = FS_HashFileName(filename, search->pack->hashSize);",
            '''if (retailMenu) {
                if (!search->pack || Q_stricmp(search->pack->pakGamename,BASEGAME)) continue;
                const char *pakName = search->pack->pakBasename;
                if (strlen(pakName)!=7 || Q_stricmpn(pakName,"assets",6) || pakName[6]<'0' || pakName[6]>'3') continue;
            }
            if ( search->pack ) {
				hash = FS_HashFileName(filename, search->pack->hashSize);''')


def frontend(tree):
    catalog(tree)
    ui = tree / "codemp/ui"
    for name in ("menu_theme.inc", "menu_items.inc"):
        shutil.copyfile(SOURCE / name, ui / name)
    main = ui / "ui_main.c"
    shared = ui / "ui_shared.c"
    replace(main, '#include "ui_st_menu_language.inc"', '''#include "ui_st_menu_language.inc"
static bool themeClassic, themeExtensions;
bool ST_ClassicLayout() { return themeClassic && !themeExtensions; }
static const char *ThemeAsset(const char *name) {
    return ST_ClassicLayout() ? va("st_retail/%s",name) : name;
}''')
    replace(main, "trap->PC_LoadSource(menuFile)", "trap->PC_LoadSource(ThemeAsset(menuFile))")
    replace(main, "void UI_LoadNonIngame() {", "static void UI_LoadPage(const char *requested);\nvoid UI_LoadNonIngame() {")
    replace(main, '#include "ui_st_legacy.inc"', 'void UI_MouseEvent(int dx,int dy);\n#include "ui_st_legacy.inc"')
    replace(main, 'trap->PC_LoadGlobalDefines ( "ui/jamp/menudef.h" );', '''
    if (ST_ClassicLayout() && Q_stricmp(menuFile,"ui/jampingame.txt")) menuFile = "ui/jampmenus.txt";
    trap->PC_LoadGlobalDefines ( ThemeAsset("ui/jamp/menudef.h") );''')
    replace(main, "trap->PC_LoadSource( menuFile )", "trap->PC_LoadSource( ThemeAsset(menuFile) )")
    replace(main, "trap->PC_RemoveAllGlobalDefines ( );", "trap->PC_RemoveAllGlobalDefines ( );\n    extern void ST_AddClassicInterface();\n    ST_AddClassicInterface();")
    replace(main, 'trap->PC_LoadSource( "ui/jampmenus.txt" )', 'trap->PC_LoadSource( ThemeAsset("ui/jampmenus.txt") )')
    replace(main, "void UI_Load( void ) {", "static void UI_LoadPage(const char *requested) {")
    replace(main, "if (menu && menu->window.name) {\n\t\tQ_strncpyz(lastName,",
            "if (requested) Q_strncpyz(lastName,requested,sizeof(lastName));\n\telse if (menu && menu->window.name) {\n\t\tQ_strncpyz(lastName,")
    replace(main, "\tString_Init();\n\n#ifdef PRE_RELEASE_TADEMO", '''
    char menuPath[MAX_QPATH];
    Q_strncpyz(menuPath,menuSet,sizeof(menuPath));
    String_Init();

#ifdef PRE_RELEASE_TADEMO''')
    replace(main, "UI_LoadMenus(menuSet, qtrue);\n\tMenus_CloseAll();\n\tMenus_ActivateByName(lastName);\n}",
            "UI_LoadMenus(menuPath, qtrue);\n\tMenus_CloseAll();\n\tif (*lastName) Menus_ActivateByName(lastName);\n}\n\nvoid UI_Load(void) { UI_LoadPage(NULL); }")
    replace(main, '#include "ui_st_workbench.inc"', '#include "ui_st_workbench.inc"\n#include "menu_theme.inc"')
    replace(main, "if ( MRUI_Script( name ) )", "if (ThemeAction(name)) return;\n\t\tif ( MRUI_Script( name ) )")
    rules = ui / "ui_st_match_rules.inc"
    replace(rules, "if(start)mrui.modal=MR_SUMMARY;", """if(!local && trap->Cvar_VariableValue("ui_stHostPresetSet"))
     mrui.draft.set("st_combatMode",trap->Cvar_VariableValue("ui_stHostPreset") ? 1 : 0);
 if(start)mrui.modal=MR_SUMMARY;""")
    replace(rules, "if(keep&&!mrui.local){", """if(keep&&!mrui.local){
  trap->Cvar_SetValue("ui_stHostPreset",mrui.draft.get("st_combatMode"));
  trap->Cvar_Set("ui_stHostPresetSet","1");""")
    replace(main, "uiInfo.inGameLoad = inGameLoad;", '''uiInfo.inGameLoad = inGameLoad;
    themeClassic = trap->Cvar_VariableValue("st_menuTheme") == 0;
    themeExtensions = themeInterface = false;
    themeDestination = NULL;
    char preset[8];
    trap->Cvar_VariableStringBuffer("st_combatMode",preset,sizeof(preset));
    trap->Cvar_Create("ui_stHostPreset",!strcmp(preset,"0") ? "0" : "1",CVAR_TEMP);
    trap->Cvar_Create("ui_stHostPresetSet","0",CVAR_TEMP);''')
    replace(main, "UI_UpdateCvars();\n\tif(EM_WheelOpen()", "UI_UpdateCvars();\n\tThemeFrame();\n\tif(EM_WheelOpen()")
    replace(main, "\t\tSPUI_BeforePaint();", "\t\tif (ST_ClassicLayout()) { ST_UIStanceCapability(); LUI_EndFrame(); Menu_PaintAll(); MRUI_Draw(); }\n\t\telse {\n\t\tSPUI_BeforePaint();")
    replace(main, "LUI_EndFrame();\n\t\t// refresh server browser", '''LUI_EndFrame();
        if (ThemeReturnVisible())
            SCUI_Centered(228,450,184,29,.65f,"Back to Classic JKA",scuGold);
        }
		// refresh server browser''')
    replace(main, "if (MRUI_Key(key,down)) return;", "if (ThemeReturnKey(key,down)) return;\n\tif (MRUI_Key(key,down)) return;")
    replace(main, "if (SWI_Key(key, down))", "if (!ST_ClassicLayout() && SWI_Key(key, down))")
    replace(main, "if (SWB_Key(key, down))", """key = ThemeNativeKey(key,ST_ClassicLayout());
    if (ST_ClassicLayout()) {
        if (!Display_KeyBindPending())
        switch (key) {
        case A_JOY0: key=A_ENTER; break;
        case A_JOY1: key=A_ESCAPE; break;
        case A_JOY11: key=A_CURSOR_UP; break;
        case A_JOY12: key=A_CURSOR_DOWN; break;
        case A_JOY13: key=A_CURSOR_LEFT; break;
        case A_JOY14: key=A_CURSOR_RIGHT; break;
        }
    } else {
    if (SWB_Key(key, down))""")
    replace(main, "if (SCUI_Key(key,down)) return;", "if (SCUI_Key(key,down)) return;\n    }")
    replace(main, "if (MRUI_Mouse()) return;", "if (MRUI_Mouse()) return;\n        if (!ST_ClassicLayout()) {")
    replace(main, "if (SCUI_IsMenu()) {SCUI_Mouse();return;}", "if (SCUI_IsMenu()) {SCUI_Mouse();return;}\n        }")
    replace(main, "void UI_SetActiveMenu( uiMenuCommand_t menu ) {", """void UI_SetActiveMenu( uiMenuCommand_t menu ) {
    if (themeExtensions && (menu == UIMENU_MAIN || menu == UIMENU_INGAME)) {
        themeExtensions = false;
        UI_LoadPage("");
    }""")
    replace(shared, "void Menu_New(int handle) {", '#ifdef UI_BUILD\n#include "menu_items.inc"\n#endif\nvoid Menu_New(int handle) {')
    replace(shared, "if (Menu_Parse(handle, menu)) {\n", "if (Menu_Parse(handle, menu)) {\n#ifdef UI_BUILD\n            ThemeItems(menu);\n#endif\n")
    legacy = ui / "ui_st_legacy.inc"
    replace(legacy, 'if(LUI_Name(op,"inventory"))', '''if(LUI_Name(op,"layout")){
  if(ST_ClassicLayout() != !!atoi(a)) fail("unexpected cosmetic layout");
 }else if(LUI_Name(op,"pointer")){
  uiInfo.uiDC.cursorx=atoi(a);uiInfo.uiDC.cursory=atoi(SMUI_Arg(3));UI_MouseEvent(0,0);
  UI_KeyEvent(A_MOUSE1,qtrue);UI_KeyEvent(A_MOUSE1,qfalse);
 }else if(LUI_Name(op,"pad")){
  int key=LUI_Name(a,"up")?A_JOY11:LUI_Name(a,"down")?A_JOY12:LUI_Name(a,"back")?A_JOY1:A_JOY0;
  UI_KeyEvent(key,qtrue); UI_KeyEvent(key,qfalse);
 }else if(LUI_Name(op,"inventory"))''')
    replace(legacy, "static qboolean LUI_IsFullscreen(){", "static qboolean LUI_IsFullscreen(){\n if(ST_ClassicLayout())return Menus_AnyFullScreenVisible();")
    replace(legacy, "static void LUI_BeginFrame(menuDef_t* forced=NULL){", "static void LUI_BeginFrame(menuDef_t* forced=NULL){\n if(ST_ClassicLayout()){lui.top=NULL;lui.item=NULL;return;}")
