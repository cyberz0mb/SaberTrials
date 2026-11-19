#include "client.h"
#include "account.h"
#include "cl_account.h"
#include "vendor/json.hpp"
#include <atomic>
#include <chrono>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <map>
#include <stdexcept>
#include <thread>
#include <vector>
#include <sstream>
#ifndef _WIN32
#include <strings.h>
#define _stricmp strcasecmp
#endif
using namespace staccount;
#define CHECK(x) do{if(!(x))throw std::runtime_error(#x);}while(0)
AccountTestCls cls;AccountTestClc clc;
std::map<std::string,std::string> cvars;
std::map<std::string,void(*)()> commands;
std::string command,console;
std::vector<std::string> incoming,sent;
int forwarded=0,browserOpened=0;
std::thread::id mainThread;
std::atomic<bool> block{true},entered{false};
std::atomic<bool> logoutOffline{false};
Saved disk;bool saveFails=false,forgot=false;
double now(){return std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();}
void onMain(){CHECK(std::this_thread::get_id()==mainThread);}
void Cvar_Set(const char* k,const char* v){onMain();cvars[k]=v;}
void Cvar_Get(const char* k,const char* v,int flags){onMain();CHECK(flags==CVAR_ROM);cvars.emplace(k,v);}
void Com_Printf(const char* fmt,...){onMain();char b[2048];va_list args;va_start(args,fmt);vsnprintf(b,sizeof(b),fmt,args);va_end(args);console+=b;}
void Cmd_AddCommand(const char* k,void(*fn)(),const char*){commands[k]=fn;}
void Cmd_RemoveCommand(const char* k){commands.erase(k);}
int Cmd_Argc(){return incoming.empty()?1:(int)incoming.size();}
const char* Cmd_Argv(int i){return incoming.empty()?command.c_str():incoming.at(i).c_str();}
int Q_stricmp(const char* a,const char* b){return _stricmp(a,b);}
void CL_AddReliableCommand(const char*s,int){onMain();++forwarded;sent.push_back(s);}
const char* NET_AdrToString(const netadr_t*){return "192.0.2.10:29070";}
int Cvar_VariableIntegerValue(const char*){return 29070;}
namespace staccount {
bool Save(const std::string&,const Saved& s){onMain();if(saveFails)return false;disk=s;return true;}
bool Load(const std::string&,Saved& s){s=disk;return true;}
bool Forget(const std::string&){onMain();forgot=true;disk={};return true;}
std::string SessionPath(){return "test-only";}
bool OpenBrowser(const std::string& url){onMain();CHECK(ValidBrowserUrl(url));++browserOpened;return true;}
Response Send(const Job& j){
 CHECK(std::this_thread::get_id()!=mainThread);entered=true;
 while(block)std::this_thread::sleep_for(std::chrono::milliseconds(1));
 if(j.path=="/v2/connection/authorize"){
  auto data=nlohmann::json::parse(j.body);CHECK(data["endpoint"]=="192.0.2.10:29070");CHECK(data["slot"]==3);CHECK(j.bearer==std::string(43,'t'));
  return {200,"{\"authorized\":true}"};
 }
 if(j.kind==Kind::Logout)return logoutOffline?Response{0,""}:Response{200,"{}"};
 const std::string token(43,'t'),id(32,'a');
 auto profile=nlohmann::json({{"account",id},{"name","SamplePlayer"},{"team",""},{"teamName",""},{"verified",true}});
 if(j.kind==Kind::Start)return {200,nlohmann::json({{"request_id",id},{"poll_token",std::string(43,'p')},{"browser_url",std::string(Origin)+"/login?request="+id+"&token="+token},{"expires_at",now()+600}}).dump()};
 if(j.kind==Kind::Poll)return {200,nlohmann::json({{"status","complete"},{"session_token",token},{"expires_at",now()+60000},{"profile",profile}}).dump()};
 CHECK(j.kind==Kind::Profile);
 return {200,nlohmann::json({{"account",std::string(32,'a')},{"name","SamplePlayer"},{"team",""},{"teamName",""},{"verified",true}}).dump()};
}
}
void pump(const char* key,const char* value){
 auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(8);
 do{CL_AccountFrame();if(cvars[key]==value)return;std::this_thread::sleep_for(std::chrono::milliseconds(1));}while(std::chrono::steady_clock::now()<deadline);
 throw std::runtime_error("adapter response timeout");
}
int main(){mainThread=std::this_thread::get_id();try{
 const std::string secret(43,'t');disk={secret,now()+60000,false};
 CL_AccountInit();CHECK(cvars["ui_stAccountSignedIn"]=="0");
 auto start=std::chrono::steady_clock::now();CL_AccountFrame();
 CHECK(std::chrono::steady_clock::now()-start<std::chrono::milliseconds(250));
 // Logout during a blocked profile response stays signed out on completion.
 command="logout";commands.at(command)();CHECK(disk.logout);CHECK(cvars["ui_stAccountSignedIn"]=="0");
 block=false;pump("ui_stAccountStatus","Signed out.");CHECK(disk.token.empty());CHECK(console.find("Account: Logged out.\n")!=std::string::npos);CL_AccountShutdown();
 // Saved identity verifies in the main menu, without an active game server.
 console.clear();disk={secret,now()+60000,false};CL_AccountInit();pump("ui_stAccountSignedIn","1");CHECK(cvars["ui_stAccountName"]=="SamplePlayer");
 CHECK(console.find("Account: Logged in as SamplePlayer.\n")!=std::string::npos);
 auto announced=console;for(int i=0;i<20;++i)CL_AccountFrame();CHECK(console==announced);
 // Storage failure falls back to removing the old session on logout.
 cls.state=CA_ACTIVE;saveFails=true;command="logout";commands.at(command)();CHECK(forgot&&disk.token.empty());CHECK(forwarded==0);
 pump("ui_stAccountStatus","Signed out.");CL_AccountShutdown();
 // Completing a fresh browser login announces success without typing login again.
 saveFails=false;console.clear();CL_AccountInit();command="login";commands.at(command)();pump("ui_stAccountSignedIn","1");
 CHECK(browserOpened==1);CHECK(console.find("Account: Logged in as SamplePlayer.\n")!=std::string::npos);
 announced=console;for(int i=0;i<20;++i)CL_AccountFrame();CHECK(console==announced);
 console.clear();command="logout";commands.at(command)();CHECK(console.find("Account: Logged out.\n")==std::string::npos);
 pump("ui_stAccountStatus","Signed out.");CHECK(console.find("Account: Logged out.\n")!=std::string::npos);CHECK(forwarded==0);CL_AccountShutdown();
 // An outage reports local sign-out, without claiming server revocation yet.
 disk={secret,now()+60000,false};CL_AccountInit();pump("ui_stAccountSignedIn","1");console.clear();logoutOffline=true;
 command="logout";commands.at(command)();pump("ui_stAccountStatus","Signed out. Server logout will retry.");
 CHECK(console.find("Account: Logged out on this device. Server sign-out will retry.\n")!=std::string::npos);
 CHECK(console.find("Account: Logged out.\n")==std::string::npos);
 announced=console;for(int i=0;i<20;++i)CL_AccountFrame();CHECK(console==announced);CL_AccountShutdown();
 logoutOffline=false;CL_AccountInit();pump("ui_stAccountStatus","Signed out.");CHECK(console.find("Account: Logged out.\n")!=std::string::npos);CL_AccountShutdown();
 // Only an advertised live connection may start the native server handshake.
 disk={secret,now()+60000,false};CL_AccountInit();pump("ui_stAccountSignedIn","1");cls.state=CA_ACTIVE;
 incoming={"staccount_offer"};CHECK(CL_AccountServerCommand());CHECK(!sent.empty());
 std::istringstream begin(sent.back());std::string opcode,nonce;begin>>opcode>>nonce;CHECK(opcode=="staccount_begin");CHECK(nonce.size()==32);
 incoming={"staccount_challenge",nonce,std::string(43,'c')};CHECK(CL_AccountServerCommand());incoming.clear();
 auto until=std::chrono::steady_clock::now()+std::chrono::seconds(2);
 while((sent.empty()||sent.back()!="staccount_ready "+nonce)&&std::chrono::steady_clock::now()<until){CL_AccountFrame();std::this_thread::sleep_for(std::chrono::milliseconds(1));}
 CHECK(sent.back()=="staccount_ready "+nonce);
 command="logout";commands.at(command)();CHECK(sent.back()=="staccount_clear "+nonce);pump("ui_stAccountStatus","Signed out.");CL_AccountShutdown();
 for(auto& text:sent){CHECK(text.find(secret)==std::string::npos);CHECK(text.find(std::string(43,'c'))==std::string::npos);}
 for(const auto& p:cvars)CHECK(p.second.find(secret)==std::string::npos);
 CHECK(console.find(secret)==std::string::npos);CHECK(commands.empty());
 std::cout<<"Actual client adapter: nonblocking worker, main-menu verification, late logout, storage fallback and secret-free UI passed.\n";return 0;
}catch(const std::exception& e){block=false;CL_AccountShutdown();std::cerr<<e.what()<<'\n';return 1;}}
