"""Use the release frontend and its own appearance resources in external games."""
from pathlib import Path
import re
from zipfile import ZipFile
from compat_hud import generate as generate_hud


CONTROLLER_LOOK_MAX = 60


def change(path, old, new):
    source = path.read_text()
    if source.count(old) != 1:
        raise ValueError(f"{path.name}: expected one occurrence of {old}")
    path.write_text(source.replace(old, new))


def presentation_assets(root, engine):
    def appearance(n):
        return (n.startswith("ui/jamp/") and n.endswith(".menu") or
                n.startswith("ui/assets/sabertrials/") and n.endswith((".tga", ".png", ".jpg")) or
                n in ("gfx/st_crystals/facet.tga","gfx/st_crystals/thumb.tga",
                      "gfx/sabertrials/hud_theme/chat_frame.png","gfx/sabertrials/hud_theme/chat_frame_fill.png",
                      "gfx/sabertrials/hud_theme/chat_header.png"))
    assets = {}
    for folder in ["ui", "gfx/sabertrials/hud_theme", "gfx/st_crystals"]:
        for path in (root / folder).rglob("*"):
            name = path.relative_to(root).as_posix().lower()
            if appearance(name) and path.is_file():
                assets[name] = path.read_bytes()
    for pack in sorted(root.glob("*.pk3")):
        with ZipFile(pack) as z:
            for path in z.namelist():
                name=path.replace("\\","/").lower()
                if appearance(name):
                    assets[name]=z.read(path)
    for required in ("gfx/st_crystals/facet.tga","gfx/st_crystals/thumb.tga"):
        if required not in assets:
            raise ValueError(f"Missing crystal workbench texture {required}")
    # Use the native ingame list, with stock menus continuing through the game's
    # approved filesystem. Only menu names are needed from the retail index.
    with ZipFile(root.parent / "base/assets1.pk3") as z:
        names = re.findall(rb'loadMenu\s*\{\s*"([^"]+)"', z.read("ui/jampingame.txt"),re.I)
    if b"ui/jamp/ingame_player.menu" not in names: raise ValueError("Missing player menu")
    assets["ui/jampingame.txt"]=b"{\n"+b"".join(b'loadMenu { "'+n+b'" }\n' for n in names)+b"}\n"
    # An explicit route to the connected mod's own UI for its custom actions.
    menu="ui/jamp/ingame.menu"
    mark=b'itemDef { name "resume"'
    pos=assets[menu].index(mark)
    assets[menu]=assets[menu][:pos]+b'''itemDef { name "server_menu" rect 20 432 210 24 type 1 text "Server menu" font 2 textscale .64 textalignx 42 textaligny 3 forecolor .76 .86 .93 1 visible 1 action { exec "st_serverMenu" ; } }
'''+assets[menu][pos:]
    target=engine/"codemp/win32/frontend-resources"
    target.mkdir(exist_ok=True)
    rc=[]; ids=[]
    for i,(name,data) in enumerate(sorted(assets.items()), 5000):
        (target / str(i)).write_bytes(data)
        ids.append(f'{{"{name}",{i}}},')
        rc.append(f'{i} RCDATA "frontend-resources/{i}"')
    (engine/"codemp/client/full_ui_resources.inc").write_text("\n".join(ids))
    with (target.parent/"openjk.rc").open("a") as f:
        f.write("\n"+"\n".join(rc)+"\n")


def patch_engine(root, engine):
    presentation_assets(root, engine)
    generate_hud(root,engine)
    client=engine/"codemp/client"
    for axis in ("horizontal", "vertical"):
        value = f"{axis}Setting->value"
        change(client/"cl_st_controller.inc", f"Com_Clamp(1,30,{value})",
               f"Com_Clamp(1,{CONTROLLER_LOOK_MAX},{value})")
    patch_shared_name(engine)
    files=engine/"codemp/qcommon/files.cpp"
    change(files,"qboolean\thandleSync;", "const byte *presentation;\n\tint cursor;\n\tqboolean\thandleSync;")
    change(files,"if ( fsh[i].handleFiles.file.o == NULL )", "if (!fsh[i].presentation && fsh[i].handleFiles.file.o == NULL)")
    mark="\tisUserConfig = !Q_stricmp( filename,"
    change(files,mark,"""#ifndef DEDICATED
    extern const byte *CL_PresentationFile(const char *,int *);
    int builtinLength=0;
    if(const byte *data=CL_PresentationFile(filename,&builtinLength)) {
        *file=FS_HandleForFile(); auto &h=fsh[*file];
        h.presentation=data;h.cursor=0;h.fileSize=builtinLength;
        Q_strncpyz(h.name,filename,sizeof(h.name));return builtinLength;
    }
#endif
"""+mark)
    change(files,"buf = (byte *)buffer;\n\tfs_readCount", """if (fsh[f].presentation) {
        auto &h=fsh[f];int n=Com_Clampi(0,h.fileSize-h.cursor,len);
        memcpy(buffer,h.presentation+h.cursor,n);h.cursor+=n;return n;
    }
    buf = (byte *)buffer;
	fs_readCount""")
    for mark,body in [
        ("int FS_filelength( fileHandle_t f ) {","if(fsh[f].presentation)return fsh[f].fileSize;"),
        ("FS_FTell( fileHandle_t f ) {","if(fsh[f].presentation)return fsh[f].cursor;"),
        ("void FS_FCloseFile( fileHandle_t f ) {","if(fsh[f].presentation){Com_Memset(&fsh[f],0,sizeof(fsh[f]));return;}"),
        ("int FS_Seek( fileHandle_t f, long offset, int origin ) {", """if(fsh[f].presentation) {
        auto &h=fsh[f];long long pos=(origin==FS_SEEK_CUR?h.cursor:origin==FS_SEEK_END?h.fileSize:0)+(long long)offset;
        if(pos<0 || pos>h.fileSize)return -1;h.cursor=(int)pos;return 0;
    }""")]:
        change(files,mark,mark+"\n    "+body)
    change(files,"if ( fsh[i].handleFiles.file.o )","if (fsh[i].presentation || fsh[i].handleFiles.file.o)")
    main=client/"cl_main.cpp"
    change(client/"cl_sabertrials_photo.inc","if (cls.state != CA_ACTIVE || !cls.cgameStarted)",
           "if (cls.state != CA_ACTIVE || !cls.cgameStarted || !CL_TrialsGame())")
    mark="void CL_AddReliableCommand( const char *cmd, qboolean isDisconnectCmd ) {"
    change(main,mark,'#include "cl_st_chat_color.h"\n#include "outgoing_chat.inc"\n'+mark)
    change(main,"cmd, sizeof(*clc.reliableCommands)", "CL_OutgoingChat(cmd).c_str(), sizeof(*clc.reliableCommands)")
    keys=client/"cl_keys.cpp"
    change(keys,"const std::string colored = ST_ChatColorized(chatField.buffer);","// The shared reliable-command path applies the outgoing chat color.")
    source=keys.read_text()
    if source.count("colored.c_str()")!=3: raise ValueError("Expected three chat field routes")
    keys.write_text(source.replace("colored.c_str()","chatField.buffer"))
    ui=client/"cl_uiapi.cpp"
    change(ui,"static void PersonalKey(int);","static void PersonalKey(int,qboolean);\nstatic bool PersonalConsole(int);\nstatic void PersonalUnload();")
    change(ui,"if(down) PersonalKey(key);","PersonalKey(key,down);")
    change(ui,"qboolean UIVM_ConsoleCommand( int realTime ) {","qboolean UIVM_ConsoleCommand( int realTime ) {\n    if(PersonalConsole(realTime))return qtrue;")
    change(ui,"void CL_UnbindUI( void ) {","void CL_UnbindUI( void ) {\n    PersonalUnload();")
    # Build both import tables even when the mod uses a legacy VM.
    change(ui,"if ( uivm && !uivm->isLegacy ) {\n\t\tuii.Print", "{\n\t\tuii.Print")
    mark="GetUIAPI = (GetUIAPI_t)uivm->GetModuleAPI;\n\t\tuii.Controls = STC_Controls;"
    change(ui,mark,"""uii.Controls = STC_Controls;
        PersonalImports(uii);
    }
    if(uivm && !uivm->isLegacy) {
        GetUIAPI=(GetUIAPI_t)uivm->GetModuleAPI;""")
    change(client/"ja_wheel_profile.inc","if (!CL_TrialsGame() || Cmd_Argc()!=3)", "if ((!CL_TrialsGame() && !CL_PersonalPauseActive()) || Cmd_Argc()!=3)")
    change(client/"cl_st_emotes.inc",'Cmd_AddCommand("st_personalStatus",CL_PersonalStatus);',
           'Cmd_AddCommand("st_personalStatus",CL_PersonalStatus);\n    Cmd_AddCommand("st_serverMenu",CL_ServerMenu);')
    mark='if (!Cvar_VariableIntegerValue("developer") || Cmd_Argc() != 3) return;'
    change(client/"cl_st_emotes.inc",mark,"""if (!Cvar_VariableIntegerValue("developer")) return;
    if(Cmd_Argc()==4 && !Q_stricmp(Cmd_Argv(1),"motion")){
        const int dx=atoi(Cmd_Argv(2)),dy=atoi(Cmd_Argv(3));
        if(CL_PersonalPauseActive())UIVM_MouseEvent(dx,dy);
        else CL_MouseEvent(dx,dy,Sys_Milliseconds());
        return;
    }
    if(Cmd_Argc()!=3)return;""")
    change(client/"client.h","void CL_PersonalStatus();","void CL_PersonalStatus();\nvoid CL_ServerMenu();")
    change(client/"client.h","void CL_PersonalFrame();","void CL_PersonalFrame();\nvoid CL_PhotoEditorFrame(bool);\nbool CL_ForeignPhotoFrame();\nbool CL_ForeignPhotoKey(int);\nbool CL_PhotoOrbitMouse(int,int);\nbool CL_PhotoOrbitInput();")
    cg=client/"cl_cgameapi.cpp"
    change(cg,'#include "foreign_chat.inc"','#include "foreign_camera.inc"\n#include "foreign_hud.inc"\n#include "foreign_chat.inc"')
    change(cg,"void CL_BindCGame( void ) {","void CL_BindCGame( void ) {\n    personalCamera::reset();personalHud::reset();")
    change(cg,"qboolean CGVM_ConsoleCommand( void ) {","qboolean CGVM_ConsoleCommand( void ) {\n    personalHud::command();\n    if(personalCamera::command())return qtrue;")
    mark="void CGVM_DrawActiveFrame( int serverTime, stereoFrame_t stereoView, qboolean demoPlayback ) {"
    change(cg,mark,mark+"\n    personalCamera::begin();personalHud::begin();")
    change(cg,"CL_TrialsGame() ? Cvar_Register : foreignChat::reg","CL_TrialsGame() ? personalCamera::nativeRegister : foreignChat::reg")
    change(cg,"CL_TrialsGame() ? Cvar_Update : foreignChat::update","CL_TrialsGame() ? personalCamera::nativeUpdate : foreignChat::update")
    input_cpp=client/"cl_input.cpp"
    mark="void CL_MouseEvent( int dx, int dy, int time ) {"
    change(input_cpp,mark,mark+"\n    if(CL_PhotoOrbitMouse(dx,dy))return;")
    mark="// store out the final values"
    change(input_cpp,mark,"""if(CL_PhotoOrbitInput()){
        VectorCopy(oldAngles,cl.viewangles);
        cmd.forwardmove=cmd.rightmove=cmd.upmove=0;
        cmd.buttons=0;
    }
    """+mark)
    change(cg,"= re->RegisterShaderNoMip;","= CL_TrialsGame()?re->RegisterShaderNoMip:personalHud::shader;")
    change(cg,"return re->RegisterShaderNoMip( (const char *)VMA(1) );","return personalHud::shader( (const char *)VMA(1) );")
    change(cg,"= re->DrawStretchPic;","= CL_TrialsGame()?re->DrawStretchPic:personalHud::stretch;")
    change(cg,"re->DrawStretchPic( VMF(1),","personalHud::stretch( VMF(1),")
    change(cg,"= re->RenderScene;","= personalCamera::render;")
    change(cg,"re->RenderScene( (const refdef_t *)VMA(1) );","personalCamera::render( (const refdef_t *)VMA(1) );")
    change(keys,"// escape is always handled special","if(CL_ForeignPhotoKey(key))return;\n\t// escape is always handled special")
    scr=client/"cl_scrn.cpp"
    change(client/"client.h","void CL_DrawForeignChat();","void CL_DrawForeignChat();\nvoid CL_DrawForeignHud();")
    change(scr,"if (!CL_TrialsGame()) {CL_PersonalFrame(); CL_DrawForeignChat();}",
           "if (!CL_TrialsGame()) CL_PersonalFrame();\n            if(!CL_ForeignPhotoFrame() && !CL_TrialsGame()){CL_DrawForeignHud(); CL_DrawForeignChat();}")
    change(scr,"CL_NetDraw();","if(!Cvar_VariableIntegerValue(\"st_photoMode\")) CL_NetDraw();")
    setup=client/"cl_st_setup.inc"
    mark="if(q->op==115)"
    change(setup,mark,"if(q->op==116){CL_PhotoEditorFrame(q->a!=0);return 1;}\n "+mark)
    change(setup,"SS_PublishCameraPreview(bool enabled)","SS_PublishCameraPreview(bool enabled,const ssSetting_t *typed=nullptr,const char *text=nullptr)")
    change(setup,"const auto value=stc::get(ssDraft.value.vars,key);","const std::string value=&setting==typed?text:stc::get(ssDraft.value.vars,key);")
    change(setup,"SS_PublishCameraPreview(q->a!=0);return 1;",'''const ssSetting_t *typed=nullptr;
    if(q->a && q->name[0]){
        const int i=SS_Index(q->name);
        if(i>=0 && ssSettings[i].tab==6 && ssSettings[i].kind==3 && SS_Disabled(i).empty() &&
            SS_Valid(q->name,q->text,SS_Get(q->name),error))typed=&ssSettings[i];
    }
    SS_PublishCameraPreview(q->a!=0,typed,q->text);return 1;''')
    extend_api(engine)


def patch_shared_name(engine):
    common=engine/"codemp/qcommon"
    client=engine/"codemp/client"
    mark='if(!Com_SafeMode())\n\t{\n\t\t// skip the q3config.cfg'
    change(common/"common.cpp",mark,'#ifndef DEDICATED\n\textern void CL_LoadSharedName();\n\tCL_LoadSharedName();\n#endif\n\t'+mark)
    mark='Cvar_Get ("name", "Padawan", CVAR_USERINFO | CVAR_ARCHIVE_ND, "Player name" );'
    change(client/"cl_main.cpp",mark,'extern void CL_StartSharedName();\n\tCL_StartSharedName();')

    # An archived mod cfg can be queued across frames. Follow its actual commands
    # through the existing buffer so unrelated input and explicit scripts still work.
    cmd=common/"cmd.cpp"
    mark='#include "cmd_tags.inc"'
    change(cmd,mark,mark+'''
static antiscript::TagBuffer<MAX_CMD_BUFFER> playerConfigTags;
static bool insertingPlayerConfig, executingPlayerConfig;
bool Cbuf_ReadingPlayerConfig(){return executingPlayerConfig;}''')
    mark='if (CL_ASCollecting()) asTags.append(cmd_text.cursize,l,asAdding);'
    change(cmd,mark,mark+'\nplayerConfigTags.append(cmd_text.cursize,l,0);')
    mark='if (CL_ASCollecting()) asTags.prepend(len,asInserting);'
    change(cmd,mark,mark+'\nplayerConfigTags.prepend(len,insertingPlayerConfig || executingPlayerConfig);')
    mark='uint32_t previousOrigin = asExecuting;'
    change(cmd,mark,mark+'\nconst bool previousConfig=executingPlayerConfig;\nexecutingPlayerConfig=playerConfigTags.take(i,i+(i<cmd_text.cursize))!=0;')
    change(cmd,'asExecuting = previousOrigin;','asExecuting = previousOrigin;\nexecutingPlayerConfig=previousConfig;')
    change(cmd,'Cbuf_ASScript(f.c);','insertingPlayerConfig=!FS_FilenameCompare(filename,Q3CONFIG_CFG) || !FS_FilenameCompare(filename,"autoexec.cfg");\n\tCbuf_ASScript(f.c);\n\tinsertingPlayerConfig=false;')

    cvar=common/"cvar.cpp"
    mark='var = Cvar_FindVar (var_name);\n\tif (!var) {\n\t\tif ( !value )'
    change(cvar,mark,'''var = Cvar_FindVar (var_name);
#ifndef DEDICATED
    extern bool CL_HasSharedName();
    extern bool Cbuf_ReadingPlayerConfig();
    if(var && Cbuf_ReadingPlayerConfig() && CL_HasSharedName() && !Q_stricmp(var_name,"name"))return var;
#endif
    if (!var) {
        if ( !value )''')
    mark='var->integer = atoi (var->string);\n\n\treturn var;\n}\n\n/*\n============\nCvar_Set'
    change(cvar,mark,mark.replace('\n\n\treturn', '''
#ifndef DEDICATED
    extern void CL_SaveSharedName(const char *);
    if(!(defaultFlags&CVAR_SERVER_CREATED) && !Q_stricmp(var_name,"name"))CL_SaveSharedName(var->string);
#endif
    return'''))


def extend_api(tree):
    ui=tree/"codemp/ui/ui_public.h"
    for axis in ("Horizontal", "Vertical"):
        row = f'"{axis} look sensitivity",1,'
        change(ui.parent/"st_controls_catalog.h", row+"30,3}", row+f"{CONTROLLER_LOOK_MAX},3}}")
    cat=ui.parent/"st_setup_catalog.h"
    mark=' {"st_chatSize"'
    change(cat,mark,' {"st_personalChat","Chat box","Chat","Choose the chat display on this server.","1=Saber Trials|0=Server mod","1",2,2,0,0,CVAR_ARCHIVE,0,1},\n'+mark)
    mark=' {"st_hudStyle"'
    change(cat,mark,' {"st_personalHud","HUD style","HUD","Choose the combat display on this server.","0=Server mod|1=Saber Trials","0",2,2,0,0,CVAR_ARCHIVE,0,1},\n'+mark)


def patch_frontend(frontend):
    extend_api(frontend)
    ui=frontend/"codemp/ui"
    change(ui/"ui_local.h","extern uiImport_t *trap;","extern uiImport_t *trap;\nbool ST_IsPersonalFrontend();\nbool UI_BlockedPersonalMenu(const char *);\nvoid UI_PersonalNotice(const char *);\nvoid UI_RequiresTrials();")
    change(ui/"ui_st_emotes.inc","jaEditor = ja;", "jaEditor = ja || ST_IsPersonalFrontend();")
    change(ui/"ui_st_emotes.inc","if (id == 12) {","if (id == 12 && ST_IsPersonalFrontend() && arg==0) { emui.status=\"Requires a Saber Trials server.\"; return; }\n    if (id == 12) {")
    main=ui/"ui_main.c"
    with main.open("a") as out:
        out.write("""
static bool personalFrontend;
bool ST_IsPersonalFrontend(){return personalFrontend;}
extern "C" Q_EXPORT uiExport_t *QDECL GetPersonalUIAPI(int version,uiImport_t *imports){
    personalFrontend=true;
    return GetModuleAPI(version,imports);
}
extern "C" Q_EXPORT const char *ST_PersonalMenuName(){
    auto m=Menu_GetFocused();return m?m->window.name:"closed";
}
""")
    mark="void UI_Refresh( int realtime )"
    change(main,mark,"""static int personalNoticeUntil;
static const char *personalNoticeText="";
void UI_PersonalNotice(const char *text) {
    personalNoticeText=text;
    personalNoticeUntil=uiInfo.uiDC.realTime+3500;
    if(trap->Cvar_VariableValue("developer"))Com_Printf("%s\\n",text);
}
void UI_RequiresTrials(){UI_PersonalNotice("Requires a Saber Trials server.");}
bool UI_BlockedPersonalMenu(const char *name) {
    if (!ST_IsPersonalFrontend() || !name)return false;
    for (const char *prefix:{"st_photo","st_pause_photo","st_pause_account","st_pause_pug","st_pug","st_tffa","st_tournament","st_ranked","st_handedness","st_stance","st_hybrid","advancedcreateserver"}) {
        if (!Q_stricmpn(name,prefix,strlen(prefix))) {UI_RequiresTrials();return true;}
    }
    return false;
}
"""+mark)
    change(main,"MRUI_Draw();","MRUI_Draw();\n        if(ST_IsPersonalFrontend() && personalNoticeUntil>realtime) SCUI_Centered(90,430,460,24,.7f,personalNoticeText,scuGold);")
    change(main,"ST_UIRefreshShell();","ST_UIRefreshShell();\n        auto focusedPhoto=Menu_GetFocused();\n        if(focusedPhoto && !Q_stricmp(focusedPhoto->window.name,\"st_photo\"))SSUI_Call(116,1);")
    change(ui/"ui_st_setup_draw.inc","SSUI_Call(115,SSUI_CameraView());",'''const bool typingCamera=SSUI_CameraView() && ssui.field==1 && ssui.setting>=0;
 SSUI_Call(115,SSUI_CameraView(),0,0,typingCamera?ssSettings[ssui.setting].name:nullptr,typingCamera?ssui.edit:nullptr);''')
    photo=ui/"ui_sabertrials_photo.inc"
    change(photo,"Drag or type values, then Apply camera.","Adjust framing for a live preview. Apply camera saves it.")
    mark='if (!Q_stricmp(name,"stPhotoApply")) {'
    change(photo,mark,'const bool start=!Q_stricmp(name,"stPhotoStart") || !Q_stricmp(name,"stPhotoCapture");\n    if (start || !Q_stricmp(name,"stPhotoApply")) {')
    mark='trap->Cvar_Set("st_uiPhotoStatus","Camera settings applied.");\n        return qtrue;'
    change(photo,mark,mark.replace('return qtrue;', 'if(!start)return qtrue;'))
    draw=ui/"ui_st_setup_draw.inc"
    mark="static void SSUI_DrawSettings()"
    change(draw,mark,'''static bool SSUI_VisibleSetting(const char *name){
        if(ST_IsPersonalFrontend())return strcmp(name,"st_hudStyle")!=0;
        return strcmp(name,"st_personalChat") && strcmp(name,"st_personalHud");
    }
    '''+mark)
    change(draw,'if(group!="Advanced video"||ssui.advanced)',
           'if((group!="Advanced video"||ssui.advanced) && SSUI_VisibleSetting(ssSettings[i].name))')
    change(ui/"ui_st_chat_preview.inc","if(SSUI_ChatSetting(i))values[next++]",
           'if(SSUI_ChatSetting(i) && ssSettings[i].kind==3)values[next++]')
    change(ui/"ui_st_setup_draw.inc",'auto& s=ssSettings[i];if(SSUI_Lower(std::string(STML_Translate(s.label))',
           'auto& s=ssSettings[i];if(!SSUI_VisibleSetting(s.name))continue;if(SSUI_Lower(std::string(STML_Translate(s.label))')
    legacy=ui/"ui_st_legacy.inc"
    change(legacy,'{"account_link","player"}','{"account_link","player"},{"server_menu","info"}')
    mark="LUI_Fit(x,y,right-x,scale,text,c);return qtrue;"
    change(legacy,mark,"""if(ST_IsPersonalFrontend() && (LUI_Name(i->window.name,"photo") || LUI_Name(i->window.name,"account_link") || LUI_Name(i->window.name,"match_rules")))
   memcpy(c,scuMuted,sizeof(c));
  """+mark)
    votes=ui/"ui_sabertrials_menu.inc"
    mark='int gt = (int)trap->Cvar_VariableValue( "st_uiVoteGametype" );'
    change(votes,mark,mark+"\n        if(ST_IsPersonalFrontend() && (gt==-1 || ST_ModeFormat(gt))){UI_RequiresTrials();return qtrue;}")
    change(ui/"ui_atoms.c","static void UI_OpenMenu_f( void ) {","static void UI_OpenMenu_f( void ) {\n    if(UI_BlockedPersonalMenu(UI_Argv(1)))return;")
    change(ui/"ui_shared.c","menuDef_t *Menus_ActivateByName(const char *p) {", """menuDef_t *Menus_ActivateByName(const char *p) {
#ifdef UI_BUILD
    extern bool UI_BlockedPersonalMenu(const char *);
    if(UI_BlockedPersonalMenu(p))return NULL;
#endif""")
    bench=ui/"ui_st_workbench.inc"
    mark="static void SWB_Button("
    change(bench,mark,"""static bool SWB_Locked(SWB_Action action,int value) {
    return ST_IsPersonalFrontend() && (action==SWB_Hand || action==SWB_Stances || action==SWB_Combat ||
        action==SWB_Channel || action==SWB_Hex || action==SWB_ResetRgb || action==SWB_WhiteCore ||
        action==SWB_Blade || (action==SWB_Color && value>=6));
}
"""+mark)
    change(bench,"focus || selected ? ruCyan : ruWhite, true","SWB_Locked(action,value) ? scuMuted : focus || selected ? ruCyan : ruWhite, true")
    mark="switch (control.action) {"
    change(bench,mark,"if(SWB_Locked(control.action,control.value)){UI_RequiresTrials();return;}\n    "+mark)
    mark="UI_UpdateSaberCvars();\n\t\tfor"
    change(bench,mark,"UI_UpdateSaberCvars();\n\t\tif(!ST_IsPersonalFrontend()){\n\t\tfor")
    mark="trap->Cvar_Set(ST_WHITE_CORE_CVAR, UI_Cvar_VariableString(ST_WHITE_CORE_DRAFT));"
    change(bench,mark,mark+"\n        }")
    crystal=ui/"ui_st_crystal_controls.inc"
    mark="static void SWB_SetChannel(int channel, int value)\n{"
    change(crystal,mark,mark+"\n    if(ST_IsPersonalFrontend()){UI_RequiresTrials();return;}")
