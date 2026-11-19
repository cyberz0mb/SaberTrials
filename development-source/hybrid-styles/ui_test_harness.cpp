/* Native unit harness; never part of a distributable game module. */
#include <map>
#include <string>
#include <cstring>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
typedef int qboolean;
enum {qfalse=0,qtrue=1,A_MOUSE1=1,A_MOUSE2=2};
struct menuDef_t {struct {const char *name;} window;};
static std::map<std::string,std::string> cvars;
static std::map<std::string,std::string> labels;
static std::string opened,closed;
static int held=0,st_hybridLibrary=1,failures=0;
static const char *va(const char *format,...) {
    static char out[2048];va_list args;va_start(args,format);vsnprintf(out,sizeof(out),format,args);va_end(args);return out;
}
static int Q_stricmp(const char *a,const char *b) {return _stricmp(a,b);}
static void CvarSet(const char *key,const char *value) {cvars[key]=value;}
static void CvarString(const char *key,char *out,int size) {snprintf(out,size,"%s",cvars[key].c_str());}
static int KeyDown(int key) {return held==key;}
struct Trap {
    void (*Cvar_Set)(const char*,const char*);
    void (*Cvar_VariableStringBuffer)(const char*,char*,int);
    int (*Key_IsDown)(int);
};
static Trap instance={CvarSet,CvarString,KeyDown},*trap=&instance;
#include "ui_st_hybrid_settings.inc"
static void ST_UIStanceCapability(void) {}
static void ST_UIStanceLabel(menuDef_t*,const char *key,const char *value) {labels[key]=value;}
static void Menus_CloseByName(const char *name) {closed=name;}
static void Menus_ActivateByName(const char *name) {
    opened=name;
    if(opened=="saberMenu" || opened=="ingame_saber") {
        // Models the existing parent onOpen's equipment reload.
        if(!st_hybridKeepSaberDraft) {
            cvars["ui_saber"]=cvars["saber1"];
            cvars["ui_saberHand"]=cvars["saberHand"];
            ST_UIHybridGetCvar();
        }
    }
}
#include "@FRAGMENT@"
#include "cg_st_hybrid_hud.inc"
#define CHECK(x) do {if(!(x)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x);failures++;}} while(0)
static void Draft(int a,int b,int c) {
    cvars["ui_saberStyleSlot1"]=std::to_string(a);
    cvars["ui_saberStyleSlot2"]=std::to_string(b);
    cvars["ui_saberStyleSlot3"]=std::to_string(c);
}
static std::string Selection(int a,int b,int c) {
    return std::to_string(a)+" "+std::to_string(b)+" "+std::to_string(c);
}
int main() {
    const char *routes[]={"Main","Game"};
    const int styles[]={0,4,5,6};
    for(const char *route:routes) {
        for(int a=1;a<=6;a++)for(int b=1;b<=6;b++)for(int c=1;c<=6;c++) {
            if(a==b || a==c || b==c)continue;
            opened.clear();closed.clear();cvars.clear();held=0;st_hybridLibrary=1;
            cvars["saberCombatStyle"]="0";
            cvars["saber1"]="single_1";cvars["ui_saber"]="custom_unapplied_hilt";
            cvars["saberHand"]="0";cvars["ui_saberHand"]="1";
            CHECK(ST_UIHybridScript((std::string("stHybridOpen")+route).c_str()));
            CHECK(opened==(!strcmp(route,"Main")?"st_hybrid_main":"st_hybrid_game"));
            CHECK(cvars["ui_saberStyleSlot1"]=="1");
            CHECK(cvars["ui_saberStyleSlot2"]=="2");
            CHECK(cvars["ui_saberStyleSlot3"]=="3");
            CHECK(cvars["saberStyleLoadout"].empty());
            Draft(a,b,c);
            CHECK(ST_UIHybridScript("stHybridApply"));
            CHECK(cvars["saberStyleLoadout"]==Selection(a,b,c));
            CHECK(st_hybridPendingReturn);
            held=A_MOUSE1;ST_UIHybridRefresh(NULL);
            CHECK(st_hybridPendingReturn);
            held=0;ST_UIHybridRefresh(NULL);
            CHECK(!st_hybridPendingReturn && !st_hybridKeepSaberDraft);
            CHECK(opened==(!strcmp(route,"Main")?"saberMenu":"ingame_saber"));
            CHECK(cvars["ui_saber"]=="custom_unapplied_hilt");
            CHECK(cvars["ui_saberHand"]=="1");
            CHECK(cvars["saber1"]=="single_1" && cvars["saberHand"]=="0");
            CHECK(ST_UIHybridScript((std::string("stHybridOpen")+route).c_str()));
            Draft(1,1,1);
            CHECK(ST_UIHybridScript("stHybridCancel"));
            CHECK(cvars["saberStyleLoadout"]==Selection(a,b,c));
            CHECK(cvars["ui_saberStyleSlot1"]==std::to_string(a));
            CHECK(cvars["ui_saberStyleSlot2"]==std::to_string(b));
            CHECK(cvars["ui_saberStyleSlot3"]==std::to_string(c));
            ST_UIHybridRefresh(NULL);
        }
    }
    cvars["saberStyleLoadout"]="4 2 3";ST_UIHybridScript("stHybridOpenMain");
    for(int slot=1;slot<=3;slot++)for(const char *invalid:{"0","-1","7","nan","4.5","4garbage","999999999999999999999999999999999999"}) {
        Draft(4,2,3);
        cvars["ui_saberStyleSlot"+std::to_string(slot)]=invalid;
        CHECK(ST_UIHybridScript("stHybridApply"));
        CHECK(!st_hybridPendingReturn);
        CHECK(cvars["saberStyleLoadout"]=="4 2 3");
    }
    for(const auto &duplicate:{"1 1 3","1 2 1","3 2 2"}) {
        Draft(duplicate[0]-'0',duplicate[2]-'0',duplicate[4]-'0');
        ST_UIHybridScript("stHybridApply");
        CHECK(!st_hybridPendingReturn && cvars["saberStyleLoadout"]=="4 2 3");
        CHECK(cvars["ui_hybridNotice"].find("different")!=std::string::npos);
    }
    st_hybridLibrary=0;Draft(6,2,3);
    ST_UIHybridScript("stHybridApply");
    CHECK(cvars["saberStyleLoadout"]=="4 2 3" && !st_hybridPendingReturn);
    CHECK(cvars["ui_hybridNotice"].find("missing")!=std::string::npos);
    Draft(3,1,2);ST_UIHybridScript("stHybridApply");
    CHECK(cvars["saberStyleLoadout"]=="3 1 2" && st_hybridPendingReturn);
    ST_UIHybridRefresh(NULL);
    CHECK(!ST_UIHybridScript("unrelatedScript"));
    ST_UIHybridScript("stHybridOpenMain");
    menuDef_t menu={{"st_hybrid_main"}};
    Draft(1,5,6);ST_UIHybridRefresh(&menu);
    CHECK(labels["st_hybrid_slot2_note"].find("recovery")!=std::string::npos);
    CHECK(labels["st_hybrid_assets"].find("missing")!=std::string::npos);
    CHECK(labels["st_hybrid_cycle"].find("Blue > Purple > Orange")!=std::string::npos);
    for(int legacy=4;legacy<=6;legacy++) {
        cvars["saberStyleLoadout"]="";cvars["saberCombatStyle"]=std::to_string(legacy);
        ST_UIHybridGetCvar();
        CHECK(cvars["ui_saberStyleSlot1"]==std::to_string(legacy));
        CHECK(cvars["ui_saberStyleSlot2"]=="2" && cvars["ui_saberStyleSlot3"]=="3");
        CHECK(cvars["saberStyleLoadout"].empty());
    }
    cvars["saberCombatStyle"]="5";
    for(const char *bad:{"1 1 3","1 2 3 4","1 2","1 2 3x","9 2 3"}) {
        cvars["saberStyleLoadout"]=bad;ST_UIHybridGetCvar();
        CHECK(cvars["ui_saberStyleSlot1"]=="1");
        CHECK(cvars["ui_saberStyleSlot2"]=="2" && cvars["ui_saberStyleSlot3"]=="3");
        CHECK(cvars["saberStyleLoadout"]==bad);
    }
    cvars["saberStyleLoadout"]="3 1 2";ST_UIHybridGetCvar();
    CHECK(cvars["ui_saberStyleSlot1"]=="3" && cvars["ui_saberStyleSlot2"]=="1" && cvars["ui_saberStyleSlot3"]=="2");
    ST_UIHybridScript("stHybridReset");
    CHECK(cvars["saberStyleLoadout"]=="3 1 2");
    CHECK(cvars["ui_saberStyleSlot1"]=="1" && cvars["ui_saberStyleSlot2"]=="2" && cvars["ui_saberStyleSlot3"]=="3");
    ST_UIHybridScript("stHybridApply");
    CHECK(cvars["saberStyleLoadout"]=="1 2 3");
    ST_UIHybridRefresh(NULL);
    cvars["saberStyleLoadout"]="  6\t5 4  ";ST_UIHybridGetCvar();
    CHECK(cvars["ui_saberStyleSlot1"]=="6" && cvars["ui_saberStyleSlot2"]=="5" && cvars["ui_saberStyleSlot3"]=="4");
    for(int style:styles) {
        const float *color=NULL;const char *name=ST_HybridHudLabel(style,&color);
        if(!style)CHECK(!name);
        else {CHECK(name && color);CHECK(strlen(name)<=6);}
    }
    printf("Three-style UI native checks (240 ordered route selections): %s\n",failures?"FAILED":"passed");
    return failures?1:0;
}
