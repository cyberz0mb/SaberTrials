#include "client.h"
#include "cl_account.h"
#include "../accounts/account.h"
#include <chrono>
#include <future>
#include <memory>

namespace {
std::unique_ptr<staccount::Client> account;
std::future<staccount::Response> request;
staccount::Job pending;
std::string path, browserError, previousNotice;
uint64_t persistedRevision=0;
double saveRetry=0;
bool storageFailed=false;

double Now(){return std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();}
void Persist(double now){
 if(account->Revision()==persistedRevision||now<saveRetry)return;
 bool ok=staccount::Save(path,account->Record());
 // A failed logout write must not leave a reusable saved sign-in behind.
 if(!ok&&(account->Record().logout||account->Record().token.empty()))ok=staccount::Forget(path);
 if(ok){persistedRevision=account->Revision();storageFailed=false;return;}
 if(!storageFailed)Com_Printf("Account: could not update saved sign-in. Keep the game open until sign-out finishes.\n");
 storageFailed=true;saveRetry=now+10;
}
void Publish(bool announce=false,bool force=false){
 const auto& view=account->Status();
 const auto& saved=account->Record();
 Cvar_Set("ui_stAccountSignedIn",view.signedIn?"1":"0");
 Cvar_Set("ui_stAccountName",view.name.c_str());
 Cvar_Set("ui_stAccountTeam",view.team.empty()?"No registered team":view.team.c_str());
 Cvar_Set("ui_stAccountCanLogin",!view.signedIn&&!view.busy&&!saved.logout?"1":"0");
 Cvar_Set("ui_stAccountCanLogout",view.signedIn||view.busy||!saved.token.empty()?"1":"0");
 Cvar_Set("ui_stAccountAction",view.signedIn?"Log out":"Cancel / Sign out");
 const char* status=view.status.c_str();
 if(storageFailed)status="Saved sign-in unavailable. Keep open to finish sign-out.";
 else if(!browserError.empty())status=browserError.c_str();
 Cvar_Set("ui_stAccountStatus",status);
 // Requests finish on later frames, often after the player closes the account
 // page. Announce state changes once so console users see the final result too.
 std::string notice=status;
 if(!storageFailed&&browserError.empty()){
  if(view.signedIn)notice="Logged in as "+view.name+".";
  else if(view.status=="Signed out.")notice="Logged out.";
  else if(saved.logout&&!view.busy)notice="Logged out on this device. Server sign-out will retry.";
 }
 if(announce&&(force||notice!=previousNotice))Com_Printf("Account: %s\n",notice.c_str());
 previousNotice=notice;
}
void Complete(double now){
 staccount::Response response;
 try{response=request.get();}catch(...){/* Never display transport data or credentials. */}
 account->Complete(pending,response,now);pending={};Persist(now);
}
void Command(){
 if(!account)return;
 if(Cmd_Argc()!=1){Com_Printf("Account: use login or logout without arguments.\n");return;}
 browserError.clear();double now=Now();
 if(!Q_stricmp(Cmd_Argv(0),"logout")){
  account->Logout(now);
  // Central revocation is handled by the account worker. The installed game
  // has no account bridge yet and does not understand "tournament logout".
 }else account->Login(now);
 Persist(now);Publish(true,true);
}
}

void CL_AccountInit(){
 if(account)return;
 account.reset(new staccount::Client);path=staccount::SessionPath();
 persistedRevision=0;saveRetry=0;storageFailed=false;browserError.clear();previousNotice.clear();
 for(const char* name:{"ui_stAccountSignedIn","ui_stAccountName","ui_stAccountTeam","ui_stAccountStatus","ui_stAccountCanLogin","ui_stAccountCanLogout","ui_stAccountAction"})Cvar_Get(name,"",CVAR_ROM);
 staccount::Saved saved;if(staccount::Load(path,saved))account->Restore(saved,Now());
 Cmd_AddCommand("login",Command,"Sign in to Saber Trials with Discord");
 Cmd_AddCommand("logout",Command,"Sign out of Saber Trials or cancel sign-in");
 Publish();
}
void CL_AccountFrame(){
 if(!account)return;
 const double now=Now();
 if(request.valid()&&request.wait_for(std::chrono::seconds(0))==std::future_status::ready)Complete(now);
 Persist(now);
 auto url=account->TakeBrowserUrl();
 if(!url.empty()&&!staccount::OpenBrowser(url)){
  account->Logout(now);browserError="Could not open the browser. Check your default browser.";Persist(now);
 }
 if(!request.valid()){
  pending=account->Next(now);
  if(pending.kind!=staccount::Kind::None){
   const auto work=pending;
   try{request=std::async(std::launch::async,[work]{return staccount::Send(work);});}
   catch(...){account->Complete(pending,{},now);pending={};}
  }
 }
 Persist(now);Publish(true);
}
void CL_AccountShutdown(){
 if(!account)return;
 // A bounded in-flight HTTP request may have just issued a session. Consume it
 // before shutdown so it is saved (or marked for revocation after cancellation).
 if(request.valid())Complete(Now());
 saveRetry=0;Persist(Now());account.reset();pending={};path.clear();
 Cmd_RemoveCommand("login");Cmd_RemoveCommand("logout");
}
