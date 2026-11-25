// The presentation DLL is the same frontend used in Saber Trials. The remote
// game's own UI VM retains its own imports, menus, commands and lifetime.
static uiImport_t personalImports;
static uiExport_t *personalExports;
static bool personalShown,personalHandoff,personalFailed;
static int presentationDepth;
static unsigned presentationGeneration;
static HMODULE personalDll;
static const char *(*personalName)();
#include "personal_preferences.inc"
#include "shared_name.inc"

struct PersonalScope {
    const unsigned generation=presentationGeneration;
    PersonalScope(){++presentationDepth;}
    ~PersonalScope(){if(generation==presentationGeneration)--presentationDepth;}
};
static const byte *CL_BuiltinPresentationFile(const char *path,int *len) {
    static const struct Asset {const char *name;int id;} assets[]={
#include "hud_font_resources.inc"
#include "full_ui_resources.inc"
    };
    auto it=std::lower_bound(std::begin(assets),std::end(assets),path,[](const Asset &a,const char *b){return Q_stricmp(a.name,b)<0;});
    if(it==std::end(assets) || Q_stricmp(it->name,path))return nullptr;
    auto exe=GetModuleHandleW(nullptr);
    auto resource=FindResourceW(exe,MAKEINTRESOURCEW(it->id),MAKEINTRESOURCEW(10));
    if(!resource)return nullptr;
    *len=SizeofResource(exe,resource);
    return static_cast<const byte *>(LockResource(LoadResource(exe,resource)));
}
const byte *CL_PresentationFile(const char *path,int *len) {
    if(presentationDepth<=0 || !path || !Q_stricmpn(path,"fonts/",6))return nullptr;
    return CL_BuiltinPresentationFile(path,len);
}
const byte *CL_HudPresentationFile(const char *path,int *len) {
    if(Q_stricmpn(path,"fonts/",6) &&
       Q_stricmp(path,"ui/assets/sabertrials/rollout/frame.png") &&
       Q_stricmp(path,"ui/assets/sabertrials/rich/wordmark.png"))return nullptr;
    return CL_BuiltinPresentationFile(path,len);
}
static bool PersonalUserinfo(const char *name) {
    return !Q_stricmpn(name,"st_",3) || !Q_stricmp(name,"saberHand") ||
        !Q_stricmp(name,"saberStances") || !Q_stricmp(name,"saberCombatStyle");
}
static void PersonalRegister(vmCvar_t *v,const char *n,const char *d,uint32_t flags) {
    Cvar_Register(v,n,d,PersonalUserinfo(n)?flags&~CVAR_USERINFO:flags);
}
static int PersonalControls(const stcRequest_t *q,stcReply_t *r) {
    if(q && q->op==1200 && r) {
        *r={};
        r->a=JA_ActionsActive();
        r->b=r->a && JA_RGBAllowed();
        return 1;
    }
    std::vector<std::string> changed;
    if(q && (q->op==103 || q->op==112)) {
        const auto &draft=q->op==103?ssDraft:stcDraft;
        for(auto &s:ssSettings)if(stc::get(draft.base.vars,stc::lower(s.name))!=stc::get(draft.value.vars,stc::lower(s.name)))
            changed.emplace_back(s.name);
    }
    int result=STC_Controls(q,r);
    if(result>0)for(auto &n:changed)if(!sharePreference(n.c_str()))
        Q_strncpyz(r->text,"Saved for this mod only.",sizeof(r->text));
    return result;
}
static void PersonalImports(const uiImport_t &ui) {
    personalImports=ui;
    personalImports.ext.AddCommand=[](const char*){};
    personalImports.ext.RemoveCommand=[](const char*){};
    personalImports.LAN_SaveCachedServers=[](){};
    personalImports.Cvar_Register=PersonalRegister;
    personalImports.Cvar_Create=[](const char *n,const char *d,uint32_t f){PersonalRegister(nullptr,n,d,f);};
    personalImports.Controls=PersonalControls;
}
static bool PersonalLoad() {
    if(personalExports)return true;
    if(personalFailed)return false;
    personalFailed=true;
    wchar_t path[32768];
    DWORD n=GetModuleFileNameW(nullptr,path,ARRAY_LEN(path));
    if(!n || n==ARRAY_LEN(path))return false;
    std::wstring folder(path,n);
    auto slash=folder.find_last_of(L"/\\");
    if(slash==std::wstring::npos)return false;
    folder.resize(slash+1);
    personalDll=LoadLibraryExW((folder+L"SaberTrialsUI.x86_64.dll").c_str(),nullptr,LOAD_WITH_ALTERED_SEARCH_PATH);
    if(personalDll) {
        auto api=reinterpret_cast<GetUIAPI_t>(GetProcAddress(personalDll,"GetPersonalUIAPI"));
        personalName=reinterpret_cast<decltype(personalName)>(GetProcAddress(personalDll,"ST_PersonalMenuName"));
        if(api && personalName)personalExports=api(UI_API_VERSION,&personalImports);
    }
    if(!personalExports){Com_Printf("Saber Trials frontend unavailable; opening the server menu.\n");return false;}
    PersonalScope scope;
    personalExports->Init(qtrue);
    return true;
}
bool CL_PersonalPauseActive(){return personalShown && personalExports && cls.state==CA_ACTIVE && (Key_GetCatcher()&KEYCATCH_UI);}
static void PersonalReset() {
    if(personalShown && personalExports) {
        personalShown=false;
        PersonalScope scope;
        personalExports->SetActiveMenu(UIMENU_NONE);
    }
}
static void PersonalUnload() {
    PersonalReset();
    if(personalExports){PersonalScope scope;personalExports->Shutdown();personalExports->MenuReset();}
    personalExports=nullptr;personalName=nullptr;
    if(personalDll)FreeLibrary(personalDll);
    personalDll=nullptr;personalFailed=false;++presentationGeneration;presentationDepth=0;
}
static bool PersonalMenu(uiMenuCommand_t menu) {
    if(CL_TrialsGame() || cls.state<CA_PRIMED || personalHandoff ||
        (menu!=UIMENU_INGAME && menu!=UIMENU_PLAYERCONFIG && menu!=UIMENU_PLAYERFORCE)) {
        PersonalReset();return false;
    }
    if(!PersonalLoad())return false;
    PersonalScope scope;
    personalShown=true;
    personalExports->SetActiveMenu(menu);
    return true;
}
static void PersonalKey(int key,qboolean down) {
    PersonalScope scope;personalExports->KeyEvent(key,down);
    if(!(Key_GetCatcher()&KEYCATCH_UI))personalShown=false;
}
static void PersonalMouse(int x,int y){PersonalScope scope;personalExports->MouseEvent(x,y);}
static qboolean PersonalFullscreen(){PersonalScope scope;return personalExports->IsFullscreen();}
static void PersonalDraw(){PersonalScope scope;personalExports->Refresh(cls.realtime);}
static bool PersonalConsole(int time) {
    if(!CL_PersonalPauseActive())return false;
    PersonalScope scope;
    bool handled=personalExports->ConsoleCommand(time)!=qfalse;
    if(!(Key_GetCatcher()&KEYCATCH_UI))personalShown=false;
    return handled;
}
void CL_PersonalFrame() {
    if(ssResume && !ssWaitingForVideo && ssDisplayTest.deadline && !Key_GetCatcher()){
        UIVM_SetActiveMenu(UIMENU_INGAME);ssResume=false;
    }
}
void CL_ServerMenu() {
    if(CL_TrialsGame() || cls.state!=CA_ACTIVE)return;
    PersonalReset(); personalHandoff=true;
    UIVM_SetActiveMenu(UIMENU_INGAME);personalHandoff=false;
}
void CL_PersonalStatus() {
    if(!Cvar_VariableIntegerValue("developer"))return;
    Com_Printf("PERSONAL_UI frontend=%s\n",CL_PersonalPauseActive()?personalName():"server or gameplay");
    CL_ForeignChatStatus();
}
