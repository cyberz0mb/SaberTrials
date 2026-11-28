#include "server/server.h"
#include "server/sv_staff.h"
#include "server_hooks.h"
#include "ledger.h"
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdarg>
#include <filesystem>
#include <iostream>
#include <vector>
#define CHECK(x) do { if (!(x)) throw std::runtime_error(#x); } while (0)

client_t clients[MAX_CLIENTS];
AsStatic svs{clients};
AsServer sv;
cvar_t maximum{4,"4"}, setting{0,"0"}; cvar_t* sv_maxclients=&maximum;
playerState_t ps[MAX_CLIENTS];
std::string verified[MAX_CLIENTS], console, dropped;
std::vector<std::string> args, notices;
std::filesystem::path folder;
int begins=0;
unsigned char generation=0;
int SV_StaffGeneration(int i,unsigned char out[16]){
    if(i!=1 || !clients[i].state) return 0;
    std::memset(out,generation,16); return 1;
}
void (*admin)()=nullptr;
cvar_t* Cvar_Get(const char* name,const char* value,int,const char*) {
    CHECK(std::string(name)=="sv_stAntiScript" && std::string(value)=="0"); return &setting;
}
int Cvar_VariableIntegerValue(const char*) {return 29070;}
void Cmd_AddCommand(const char* name,void(*cb)(),const char*) {CHECK(std::string(name)=="st_as");admin=cb;}
int Cmd_Argc(){return int(args.size());}
const char* Cmd_Argv(int i){return i<Cmd_Argc()?args[i].c_str():"";}
void Com_Printf(const char* fmt,...){char b[1024];va_list a;va_start(a,fmt);vsnprintf(b,sizeof(b),fmt,a);va_end(a);console+=b;}
void SV_SendServerCommand(client_t* c,const char* fmt,...) {
    char b[1024];va_list a;va_start(a,fmt);vsnprintf(b,sizeof(b),fmt,a);va_end(a);
    notices.push_back((c?std::to_string(c-clients):"public")+" "+b);
}
void SV_DropClient(client_t* c,const char* why){dropped=why;c->state=0;SV_ASReset(int(c-clients));}
void GVM_ClientBegin(int i){CHECK(i==1);++begins;}
playerState_t* SV_GameClientNum(int i){return &ps[i];}
int Q_stricmp(const char* a,const char* b){return std::strcmp(a,b);}
void Q_strncpyz(char* to,const char* from,int n){std::snprintf(to,n,"%s",from);}
void Q_CleanStr(char*){}
std::string SV_VerifiedPlayerAccount(int i){return verified[i];}
namespace staccount {std::string ServerCredentialPath(int){return folder.generic_string()+"/credential.bin";}}

static void connect(const std::string& id){
    ++generation; SV_ASReset(1); verified[1]=id; clients[1].state=CS_ACTIVE; dropped.clear();
    if (!SV_ASDeferBegin(1)) GVM_ClientBegin(1);
    SV_ASFrame();
}
static void sample(int mask) {
    sv.time+=40;
    usercmd_s c; c.serverTime=sv.time;
    c.forwardmove=mask&4?127:0; c.buttons=mask&1?BUTTON_ATTACK:0;
    SV_ASSample(1,c);
}
static void runPattern(bool report) {
    sample(0);
    for (int n=0;n<3;++n) for (int m:{1,0,4,0}) sample(m);
    if(report){args={"st_as1",std::to_string(sv.time),"0145","1"};CHECK(SV_ASCommand(1));}
}
int main(){
    using namespace antiscript;
    try {
        folder=std::filesystem::temp_directory_path()/("as-adapter-"+std::to_string(
            std::chrono::steady_clock::now().time_since_epoch().count()));
        CHECK(std::filesystem::create_directory(folder));
        const auto path=(folder/"anti-script.sqlite").string();
        const std::string account(32,'a');
        SV_ASInit();
        connect("");runPattern(true);
        CHECK(!std::filesystem::exists(path) && notices.empty() && begins==1);
        setting={1,"1"};connect(account);runPattern(true);
        Ledger audit(path); CHECK(audit.lookup(account).strikes==0 && notices.empty());
        int logs=0; audit.evidence(account,INT64_MAX,[&](auto&){++logs;});CHECK(logs==3);
        setting={2,"2"};connect(""); CHECK(!SV_ASAllowed(1) && begins==2);
        runPattern(true);CHECK(audit.lookup(account).strikes==0);
        verified[1]=account;SV_ASFrame();CHECK(SV_ASAllowed(1) && begins==3);
        // A client-only claim, a bot, spectator, or a dead player's inputs cannot strike.
        args={"st_as1",std::to_string(sv.time),"0145","1"};CHECK(SV_ASCommand(1));
        CHECK(audit.lookup(account).strikes==0);
        for(int excluded=0;excluded<3;++excluded){
            if(excluded==0)clients[1].netchan.remoteAddress.type=NA_BOT;
            if(excluded==1)ps[1].persistant[PERS_TEAM]=TEAM_SPECTATOR;
            if(excluded==2)ps[1].stats[STAT_HEALTH]=0;
            runPattern(true);CHECK(audit.lookup(account).strikes==0);
            clients[1].netchan.remoteAddress.type=1;ps[1].persistant[PERS_TEAM]=0;ps[1].stats[STAT_HEALTH]=100;
        }
        connect(account);
        runPattern(false);CHECK(audit.lookup(account).strikes==0);
        runPattern(true);CHECK(audit.lookup(account).strikes==1);
        CHECK(notices.back()=="1 print \"Warning: Anti-cheating is active. You have been warned.\n\"");
        verified[1].clear();SV_ASAccountChanged(1);CHECK(!dropped.empty());
        // Seed old independent incidents to exercise the real adapter's next action.
        auto t=std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
        const char* expected[]={"",""," has been detected cheating."," has been kicked for cheating.",
            " has been temp-banned for cheating."," has been perma-banned for cheating."};
        for(int target=2;target<=5;++target){
            std::string id(32,char('a'+target));
            Claim c{"0145",100};Pattern p{"0145","40,40,40,40,40,40,40,40,40",100};
            for(int j=1;j<target;++j)CHECK(audit.confirm(Mode::Enforce,id,"old"+std::to_string(j),c,p,t-31LL*86400+j*601)==j);
            connect(id);
            if (target>=4) { clients[2].state=CS_ACTIVE; verified[2]=id; }
            runPattern(true);
            CHECK(audit.lookup(id).strikes==target);
            if(target>=4) CHECK(clients[2].state!=CS_ACTIVE);
            auto msg="public cp \"Jawa"+std::string(expected[target])+"\"";
            CHECK(std::find(notices.begin(),notices.end(),msg)!=notices.end());
            CHECK(dropped.empty()==(target<3));
            if (target>=4){
                int before=begins;connect(id);CHECK(!dropped.empty() && begins==before);
                args={"st_as","revoke",id};admin();connect(id);CHECK(dropped.empty() && begins==before+1);
                args={"st_as","clear",id};admin();CHECK(audit.lookup(id).strikes==0);
                args={"st_as","evidence",id};admin();CHECK(console.find("revoke-ban")!=console.npos);
            }
        }
        connect("");setting={0,"0"};SV_ASFrame();CHECK(SV_ASAllowed(1));
        return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
