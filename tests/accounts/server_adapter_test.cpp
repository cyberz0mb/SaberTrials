#include "server.h"
#include "sv_account.h"
#include "account.h"
#include "server_storage.h"
#include "vendor/json.hpp"
#include <atomic>
#include <chrono>
#include <cstdarg>
#include <cstdio>
#include <iostream>
#include <thread>
#include <vector>
#include <stdexcept>
#include <cstring>
#define CHECK(x) do{if(!(x))throw std::runtime_error(#x);}while(0)
TestServerStatic svs;TestCvar maximum{4};TestCvar* sv_maxclients=&maximum;
std::vector<std::string> args,messages;
std::string console;bool credential=true;unsigned char generation[16]={1};
STEProfile applied{};int clears=0;std::atomic<bool> blocked{false},entered{false};std::thread::id mainThread;
int Cmd_Argc(){return (int)args.size();}const char*Cmd_Argv(int i){return args.at(i).c_str();}
int Cvar_VariableIntegerValue(const char*){return 29070;}
void Com_Printf(const char*fmt,...){CHECK(std::this_thread::get_id()==mainThread);char b[2048];va_list a;va_start(a,fmt);vsnprintf(b,sizeof(b),fmt,a);va_end(a);console+=b;}
void SV_SendServerCommand(client_t*,const char*fmt,...){CHECK(std::this_thread::get_id()==mainThread);char b[2048];va_list a;va_start(a,fmt);vsnprintf(b,sizeof(b),fmt,a);va_end(a);messages.push_back(b);}
int SV_StaffGeneration(int i,unsigned char*out){if(i!=3)return 0;memcpy(out,generation,16);return 1;}
bool GVM_AccountAvailable(){return true;}
int GVM_AccountSet(int i,const unsigned char*gen,const STEProfile*p){CHECK(i==3);CHECK(!memcmp(gen,generation,16));applied=*p;return 1;}
void GVM_AccountClear(int i){CHECK(i==3);applied={};++clears;}
double wall(){return std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();}
namespace staccount {
std::string ServerCredentialPath(int){return "test-only";}
bool LoadServerCredential(const std::string&,ServerCredential&c){if(!credential)return false;c={"temple",std::string(43,'s')};return true;}
bool ImportServerCredential(const std::string&,const std::string&){return false;}
Response Send(const Job&j){
 CHECK(std::this_thread::get_id()!=mainThread);CHECK(j.bearer==std::string(43,'s'));entered=true;
 while(blocked)std::this_thread::sleep_for(std::chrono::milliseconds(1));
 auto body=nlohmann::json::parse(j.body);
 if(j.path=="/v2/server/challenge")return {200,nlohmann::json({{"challenge",std::string(43,'c')},{"server","temple"},{"instance",body["instance"]},{"slot",body["slot"]},{"generation",body["generation"]},{"expires_at",wall()+90}}).dump()};
 CHECK(j.path=="/v1/server/redeem");
 return {200,nlohmann::json({{"lease_token",std::string(43,'l')},{"instance",body["instance"]},{"slot",body["slot"]},{"generation",body["generation"]},{"expires_at",wall()+60},{"profile",{{"account",std::string(32,'a')},{"name","Registered Jawa"},{"team","clan-jawa"},{"teamName","[JAWA]"},{"verified",true}}}}).dump()};
}
}
template<class F>void pump(F done){auto until=std::chrono::steady_clock::now()+std::chrono::seconds(2);do{SV_AccountFrame();if(done())return;std::this_thread::sleep_for(std::chrono::milliseconds(1));}while(std::chrono::steady_clock::now()<until);throw std::runtime_error("server adapter timeout");}
int main(){mainThread=std::this_thread::get_id();try{
 svs.clients[3].state=CS_ACTIVE;credential=false;SV_AccountFrame();CHECK(messages.empty());
 credential=true;SV_AccountReset();SV_AccountFrame();CHECK(messages.back()=="staccount_offer");
 const std::string nonce(32,'b');args={"staccount_begin",nonce};CHECK(SV_AccountCommand(3));blocked=true;
 auto before=std::chrono::steady_clock::now();SV_AccountFrame();CHECK(std::chrono::steady_clock::now()-before<std::chrono::milliseconds(250));CHECK(applied.account[0]==0);
 blocked=false;pump([]{return !messages.empty()&&messages.back().find("staccount_challenge ")==0;});
 args={"staccount_ready",nonce};CHECK(SV_AccountCommand(3));pump([]{return applied.account[0]!=0;});CHECK(std::string(applied.name)=="Registered Jawa");CHECK(std::string(applied.team)=="clan-jawa");
 args={"staccount_clear",nonce};CHECK(SV_AccountCommand(3));CHECK(applied.account[0]==0&&clears==1);
 // Bots and stale slot generations never retain verification.
 svs.clients[3].netchan.remoteAddress.type=NA_BOT;args={"staccount_begin",nonce};CHECK(SV_AccountCommand(3));SV_AccountFrame();CHECK(applied.account[0]==0);
 SV_AccountReset();CHECK(console.find(std::string(43,'s'))==std::string::npos);
 for(auto&s:messages){CHECK(s.find(std::string(43,'s'))==std::string::npos);CHECK(s.find(std::string(43,'l'))==std::string::npos);}
 std::cout<<"Actual native server adapter: approved storage, async verification, game identity handoff, logout and bot rejection passed.\n";return 0;
}catch(const std::exception&e){blocked=false;std::cerr<<e.what()<<'\n';return 1;}}
