#include "server.h"
#include "sv_account.h"
#include "sv_staff.h"
#include "bridge.h"
#include "server_storage.h"
#include "st_staff_types.h"
#include <array>
#include <chrono>
#include <cstring>
#include <future>
#include <memory>
namespace {
std::unique_ptr<staccount::ServerBridge> bridge;
struct Worker {std::future<staccount::Response> result;staccount::ServerWork job;uint64_t epoch=0;};
std::array<Worker,4> workers;
std::array<std::string,MAX_CLIENTS> generations,applied,sentChallenge;
std::array<double,MAX_CLIENTS> nextOffer={};
uint64_t epoch=0;bool attempted=false;
double Wall(){return std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();}
double Mono(){return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();}
bool Human(int i){return i>=0&&i<sv_maxclients->integer&&i<MAX_CLIENTS&&svs.clients[i].state==CS_ACTIVE&&svs.clients[i].netchan.remoteAddress.type!=NA_BOT;}
void ClearGame(int i){if(!applied[i].empty()){GVM_AccountClear(i);applied[i].clear();}}
bool Ready(){
 if(bridge)return true;if(attempted)return false;attempted=true;
 staccount::ServerCredential c;unsigned char boot[16];
 if(!staccount::LoadServerCredential(staccount::ServerCredentialPath(Cvar_VariableIntegerValue("net_port")),c)||!st::Random(boot,16))return false;
 bridge.reset(new staccount::ServerBridge(c.id,c.token,st::Hex(boot,16)));return true;
}
void Sync(double now){
 for(int i=0;i<MAX_CLIENTS;i++){
  unsigned char generation[16];std::string current;
  if(Human(i)&&SV_StaffGeneration(i,generation))current=st::Hex(generation,16);
  if(current!=generations[i]){
   ClearGame(i);bridge->Disconnect(i);generations[i]=current;sentChallenge[i].clear();nextOffer[i]=now;
   if(!current.empty())bridge->Connect(i,current);
  }
 }
}
void Publish(){
 for(int i=0;i<MAX_CLIENTS;i++){
  auto p=bridge->Profile(i);
  if(p.account.empty()){ClearGame(i);continue;}
  std::string key=p.account+"\n"+p.name+"\n"+p.team+"\n"+p.tag;
  if(key==applied[i])continue;
  unsigned char generation[16];STEProfile profile={};
  if(!Human(i)||!SV_StaffGeneration(i,generation))continue;
  std::memcpy(profile.account,p.account.c_str(),p.account.size()+1);std::memcpy(profile.name,p.name.c_str(),p.name.size()+1);
  std::memcpy(profile.team,p.team.c_str(),p.team.size()+1);std::memcpy(profile.teamName,p.tag.c_str(),p.tag.size()+1);profile.verified=profile.connected=1;
  if(GVM_AccountSet(i,generation,&profile))applied[i]=key;
  else {ClearGame(i);bridge->Clear(i,bridge->Nonce(i));}
 }
}
}
void SV_AccountReset(){
 for(int i=0;i<MAX_CLIENTS;i++){ClearGame(i);generations[i].clear();sentChallenge[i].clear();nextOffer[i]=0;}
 bridge.reset();attempted=false;++epoch; // outstanding workers cannot affect the next map
}
void SV_AccountFrame(){
 const double wall=Wall(),now=Mono();
 // Drain even when the next map has no compatible game extension.
 for(auto&w:workers)if(w.result.valid()&&w.result.wait_for(std::chrono::seconds(0))==std::future_status::ready){
  staccount::Response r;try{r=w.result.get();}catch(...){}
  if(bridge&&w.epoch==epoch)bridge->Complete(w.job,r,wall,now);w.job={};
 }
 if(!GVM_AccountAvailable()||!Ready())return;
 Sync(now);bridge->Tick(now);Publish();
 for(int i=0;i<MAX_CLIENTS;i++)if(!generations[i].empty()){
  const auto challenge=bridge->Challenge(i);
  if(!challenge.empty()&&challenge!=sentChallenge[i]){
   SV_SendServerCommand(&svs.clients[i],"staccount_challenge %s %s",bridge->Nonce(i).c_str(),challenge.c_str());sentChallenge[i]=challenge;
  }
  if(bridge->Idle(i)&&now>=nextOffer[i]){SV_SendServerCommand(&svs.clients[i],"staccount_offer");nextOffer[i]=now+30;}
 }
 for(auto&w:workers)if(!w.result.valid()){
  w.job=bridge->Next(wall,now);if(w.job.http.path.empty())continue;w.epoch=epoch;auto work=w.job.http;
  try{w.result=std::async(std::launch::async,[work]{return staccount::Send(work);});}
  catch(...){bridge->Complete(w.job,{},wall,now);w.job={};}
 }
}
bool SV_AccountCommand(int slot){
 const std::string cmd=Cmd_Argv(0);
 if(cmd!="staccount_begin"&&cmd!="staccount_ready"&&cmd!="staccount_clear")return false;
 if(Cmd_Argc()!=2||!Human(slot)||!GVM_AccountAvailable()||!Ready())return true;
 const double now=Mono();Sync(now);const std::string nonce=Cmd_Argv(1);
 if(cmd=="staccount_begin"){if(bridge->Begin(slot,nonce,now)){ClearGame(slot);sentChallenge[slot].clear();}}
 else if(cmd=="staccount_ready")bridge->Ready(slot,nonce,now);
 else if(bridge->Clear(slot,nonce))ClearGame(slot);
 return true;
}
void SV_AccountConsole_f(){
 const std::string op=Cmd_Argc()>1?Cmd_Argv(1):"status";
 if(op=="import"&&Cmd_Argc()==3){
  const bool ok=staccount::ImportServerCredential(Cmd_Argv(2),staccount::ServerCredentialPath(Cvar_VariableIntegerValue("net_port")));
  if(ok)SV_AccountReset();Com_Printf("Accounts: %s\n",ok?"server credential imported":"import failed; check the private credential file");return;
 }
 if(op=="status"){Com_Printf("Accounts: %s\n",Ready()?"server credential configured":"server credential not configured");return;}
 Com_Printf("accountserver status | import <private credential file>\n");
}
