#include "client.h"
#include "cl_staff.h"
#include "cl_account.h"
#include "../server/sv_staff.h"
#include "../staff/st_staff_wire.h"
#include <windows.h>
#include <sodium.h>
#include <cstring>
#include <sstream>
namespace {
st::Identity identity;st::Nonce nonce={},session={};st::Bytes transcript;
std::string pin,root,wire;uint64_t started=0,sent=0,sequence=0;
bool active=false,suppressed=false,attempted=false;int state=0;
st::Request pending;int resolveCommand=0;
uint64_t Now(){return GetTickCount64();}
bool PrivateClient(){if(root.empty()){root=st::PrivateRoot();if(root.empty())return false;root+="/client";if(!st::PrivateDirectory(root)){root.clear();return false;}}return true;}
bool Ready(bool create){if(!PrivateClient())return false;
 if(!identity.PublicId().empty())return true;return identity.LoadOrCreate(root+"/identity.key",create);}
std::string PinPath(){if(root.empty())return {};std::string p=root+"/pins";if(!st::PrivateDirectory(p))return {};std::string adr=NET_AdrToString(&clc.serverAddress);return p+"/"+st::Hex((const unsigned char*)adr.data(),adr.size())+".pin";}
void Send(const std::string& message){NET_OutOfBandPrint(NS_CLIENT,&clc.serverAddress,"%s",message.c_str());}
void Login(){
 attempted=true;active=false;session.fill(0);sequence=0;wire.clear();transcript.clear();resolveCommand=0;
 if(cls.state!=CA_ACTIVE||clc.demoplaying){Com_Printf("Staff: join a live server first.\n");return;}
 if(!Ready(false)){Com_Printf("Staff: use staff identity to create your local identity.\n");return;}
 st::Bytes data;if(!st::ReadFileBytes(PinPath(),data,64)||(pin=std::string(data.begin(),data.end())).size()!=64||!st::ValidId(pin)){Com_Printf("Staff: verify the server public key with its operator, then staff trust <public-key>.\n");return;}
 if(!st::Random(nonce.data(),32))return;
 wire="sthello "+std::to_string(clc.clientNum)+" "+identity.PublicId()+" "+st::Hex(nonce.data(),32);started=sent=Now();Send(wire);
}
void Request(st::Request req){
 if(!active||clc.demoplaying){Com_Printf("Staff: login required.\n");return;}
 if(!wire.empty()){Com_Printf("Staff: wait for the current request.\n");return;}
 req.session=session;req.sequence=++sequence;auto bytes=st::Encode(req);if(bytes.empty()){Com_Printf("Staff: invalid or oversized command arguments.\n");return;}
 auto sig=identity.Sign(bytes);if(sig.size()!=64)return;pending=req;
 wire="staction "+std::to_string(clc.clientNum)+" "+st::Hex(bytes.data(),bytes.size())+" "+st::Hex(sig.data(),sig.size());started=sent=Now();Send(wire);
}
}
void CL_StaffReset(){active=false;attempted=false;state=0;wire.clear();pin.clear();transcript.clear();sequence=0;session.fill(0);nonce.fill(0);resolveCommand=0;pending=st::Request();}
bool CL_StaffConnected(){return cls.state>=CA_CONNECTED;}
void CL_StaffFrame(){
 CL_AccountFrame();
 if(cls.state!=CA_ACTIVE||clc.demoplaying){if(state==CA_ACTIVE)CL_StaffReset();state=cls.state;return;}state=cls.state;
 if(!attempted&&!suppressed){attempted=true;if(Ready(false)){st::Bytes p;if(st::ReadFileBytes(PinPath(),p,64))Login();}}
 if(!wire.empty()){uint64_t now=Now();if(now-started>=8000){Com_Printf("Staff: request timed out or permission was revoked. Use staff login to retry.\n");wire.clear();resolveCommand=0;active=false;transcript.clear();}
 else if(now-sent>=1100){sent=now;Send(wire);}}
}
bool CL_StaffPacket(const netadr_t* from){
#ifdef ST_STAFF_QA
 if(!strcmp(Cmd_Argv(0),"stqacmd")) {
  char token[128]={};GetEnvironmentVariableA("ST_STAFF_QA_TOKEN",token,sizeof(token));
  if(from->type==NA_IP&&from->ip[0]==127&&token[0]&&Cmd_Argc()==3&&!strcmp(token,Cmd_Argv(1))){st::Bytes text;if(st::Unhex(Cmd_Argv(2),text)&&text.size()<900){std::string command(text.begin(),text.end());
   if(command=="qa_client_state")Com_Printf("STAFF_CLIENT_QA state=%d catcher=%d mode=%d pm=%d up=%d forward=%d buttons=%d x=%.2f y=%.2f z=%.2f\n",cls.state,Key_GetCatcher(),cl.snap.ps.stats[15],cl.snap.ps.pm_type,cl.cmds[cl.cmdNumber&CMD_MASK].upmove,cl.cmds[cl.cmdNumber&CMD_MASK].forwardmove,cl.cmds[cl.cmdNumber&CMD_MASK].buttons,cl.snap.ps.origin[0],cl.snap.ps.origin[1],cl.snap.ps.origin[2]);
   else Cbuf_ExecuteText(EXEC_APPEND,(command+"\n").c_str());}}
  return true;
 }
#endif
 std::string kind=Cmd_Argv(0);if(kind!="stchallenge"&&kind!="stsession"&&kind!="stresult")return false;
 if(clc.demoplaying||cls.state!=CA_ACTIVE||!NET_CompareAdr(from,&clc.serverAddress)||Cmd_Argc()!=3||wire.empty()||pin.empty())return true;
 st::Bytes data,sig;if(!st::Unhex(Cmd_Argv(1),data)||!st::Unhex(Cmd_Argv(2),sig,64)||!st::Identity::Verify(pin,data,sig))return true;
 if(kind=="stchallenge"){
  if(wire.compare(0,8,"sthello ")||data.size()!=148||std::memcmp(data.data(),"STL\1",4))return true;
  st::Bytes id;if(!st::Unhex(identity.PublicId(),id,32)||std::memcmp(data.data()+36,id.data(),32)||std::memcmp(data.data()+68,nonce.data(),32))return true;
  st::Bytes server;if(!st::Unhex(pin,server,32)||std::memcmp(data.data()+4,server.data(),32))return true;
  transcript=data;auto proof=identity.Sign(data);wire="stproof "+std::to_string(clc.clientNum)+" "+st::Hex(proof.data(),proof.size());sent=Now();Send(wire);return true;
 }
 if(kind=="stsession"){
  if(wire.compare(0,8,"stproof ")||!st::ReadSessionMessage(data,transcript,session))return true;
  active=true;wire.clear();transcript.clear();Com_Printf("Staff: authenticated.\n");st::Request r;r.command=ST_CMD_WHOAMI;Request(r);return true;
 }
 if(kind=="stresult"){
  bool ok=false;std::string message;if(wire.compare(0,9,"staction ")||!st::ReadResultMessage(data,session,pending.sequence,ok,message))return true;
  const int cmd=pending.command;wire.clear();
  if((cmd==ST_CMD_RESOLVE||cmd==ST_CMD_RESOLVE_AIM)&&resolveCommand){int next=resolveCommand;resolveCommand=0;if(!ok){Com_Printf("Staff: %s\n",message.c_str());return true;}
   std::istringstream s(message);int slot=-1;std::string gen,extra;s>>slot>>gen;if(!s||s>>extra)return true;st::Bytes bytes;if(slot<0||slot>=MAX_CLIENTS||!st::Unhex(gen,bytes,16))return true;
   st::Request r;r.command=next;r.target.slot=slot;std::memcpy(r.target.generation,bytes.data(),16);Request(r);return true;
  }
  if(cmd==ST_CMD_WHOAMI&&ok)Com_Printf("%s\n",message.c_str());
  else Com_Printf("Staff: %s\n",message.c_str());
  if(cmd==ST_CMD_LOGOUT){active=false;suppressed=true;}
  if(cmd==ST_CMD_TRAVEL_SERVER&&ok&&pending.args.size()==1&&st::NumericAddress(pending.args[0])){std::string address=pending.args[0];CL_StaffReset();CL_ConnectAddress(address.c_str());}
 }return true;
}
void CL_StaffCommand_f(){
 const std::string command=Cmd_Argv(0),op=Cmd_Argv(1);const int argc=Cmd_Argc();
 if(command=="staff"){
  if(op=="freeze"||op=="unfreeze"){Com_Printf("Use %s without the staff prefix. Example: %s #0, or bind F6 \"%s\" to aim at a player.\n",op.c_str(),op.c_str(),op.c_str());return;}
  if((op=="owner"||op=="serverkey")&&com_sv_running->integer){SV_StaffConsole_f();return;}
  if(op=="identity"&&argc==2){if(Ready(true))Com_Printf("Staff public account ID: %s\n",identity.PublicId().c_str());else Com_Printf("Staff: private identity unavailable; existing files were not replaced.\n");return;}
  if(op=="trust"&&argc==3){if(cls.state!=CA_ACTIVE||!Ready(false)||!st::ValidId(Cmd_Argv(2))){Com_Printf("Staff: join a live server and provide its verified 64-character public key.\n");return;}std::string value=Cmd_Argv(2);st::Bytes b(value.begin(),value.end());if(st::PrivateWrite(PinPath(),b,true)){Com_Printf("Staff: server key pinned.\n");suppressed=false;Login();}return;}
  if(op=="login"&&argc==2){suppressed=false;Login();return;}
  if((op=="export"||op=="import")&&argc==3){std::string path=Cmd_Argv(2);if(!(op=="import"?PrivateClient():Ready(false))){Com_Printf("Staff: private identity location unavailable.\n");return;}std::string pass;if(!st::AskPassphrase(pass,op=="export"))return;bool ok=op=="export"?identity.ExportProtected(path,pass):identity.ImportProtected(path,pass,root+"/identity.key");if(!pass.empty())sodium_memzero(&pass[0],pass.size());CL_StaffReset();Com_Printf("Staff backup: %s\n",ok?"completed":"failed; check the path and passphrase");return;}
  if(op=="logout"&&argc==2){suppressed=true;if(!active){CL_StaffReset();Com_Printf("Staff: logged out.\n");return;}}
 }
 st::Request r;
 if(command=="staff"){
  if(op=="whoami"&&argc==2)r.command=ST_CMD_WHOAMI;
  else if(op=="list"&&argc==2)r.command=ST_CMD_LIST;
  else if(op=="logout"&&argc==2)r.command=ST_CMD_LOGOUT;
  else if(op=="add"&&argc==5)r.command=ST_CMD_ADD;
  else if(op=="role"&&argc==4)r.command=ST_CMD_ROLE;
  else if(op=="remove"&&argc==3)r.command=ST_CMD_REMOVE;
  for(int i=2;i<argc;i++)r.args.push_back(Cmd_Argv(i));
 }else if(command=="ghost"&&argc==2){if(op=="on")r.command=ST_CMD_GHOST_ON;else if(op=="off")r.command=ST_CMD_GHOST_OFF;}
 else if(command=="travel"&&op=="coords"&&argc==5){r.command=ST_CMD_TRAVEL_COORDS;for(int i=2;i<5;i++)r.args.push_back(Cmd_Argv(i));}
 else if(command=="travel"&&op=="server"&&argc==3){if(!st::NumericAddress(Cmd_Argv(2))){Com_Printf("Staff: use numeric IPv4:port or [IPv6]:port.\n");return;}r.command=ST_CMD_TRAVEL_SERVER;r.args.push_back(Cmd_Argv(2));}
 else if(argc==1&&(command=="freeze"||command=="unfreeze")){
  if(!wire.empty()){Com_Printf("Staff: wait for the current request.\n");return;}
  resolveCommand=command=="freeze"?ST_CMD_FREEZE:ST_CMD_UNFREEZE;r.command=ST_CMD_RESOLVE_AIM;
 }
 else if(argc==2){int targetCommand=command=="freeze"?ST_CMD_FREEZE:command=="unfreeze"?ST_CMD_UNFREEZE:command=="summon"?ST_CMD_SUMMON:command=="travel"?ST_CMD_TRAVEL_PLAYER:0;
  if(targetCommand){if(!wire.empty()){Com_Printf("Staff: wait for the current request.\n");return;}resolveCommand=targetCommand;r.command=ST_CMD_RESOLVE;r.args.push_back(op);}}
 if(!r.command){Com_Printf("Staff: identity | trust <server-key> | login | logout | whoami | list | add <key> <admin|moderator> <label> | role <id> <role> | remove <id> | export/import <file>. Moderation (no staff prefix): freeze/unfreeze [name|#ID] (no target = aim), summon <name|#ID>, ghost on/off, travel <name|#ID>, travel coords x y z, travel server IP:port.\n");return;}
 Request(r);
}
static void CL_Tournament_f(){
 const std::string op=Cmd_Argv(1);
 if(com_sv_running->integer&&(op=="open"||op=="start"||op=="close")){
  Cbuf_ExecuteText(EXEC_APPEND,va("st_event %s\n",Cmd_Args()));return;
 }
 if(op=="pause"||op=="resume"||op=="restart"||op=="disqualify"){
  st::Request r;r.command=ST_CMD_TOURNAMENT;r.args.push_back(op);
  const int reasonStart=op=="disqualify"?3:2;
  if(op=="disqualify")r.args.push_back(Cmd_Argv(2));
  std::string reason;for(int i=reasonStart;i<Cmd_Argc();i++){if(!reason.empty())reason+=' ';reason+=Cmd_Argv(i);}
  if(reason.empty()||reason.size()>159){Com_Printf("Tournament: include a short reason.\n");return;}
  r.args.push_back(reason);Request(r);return;
 }
 if(cls.state!=CA_ACTIVE||clc.demoplaying){Com_Printf("Tournament: join a server first.\n");return;}
 CL_AddReliableCommand(va("tournament %s",Cmd_Args()),qfalse);
}
void CL_StaffInit(){
 CL_AccountInit();
 Cmd_AddCommand("tournament",CL_Tournament_f,"Tournament registration, readiness and staff controls");
 for(const char* name:{"staff","unfreeze","ghost","summon","travel"})Cmd_AddCommand(name,CL_StaffCommand_f,"Saber Trials authenticated staff command");
 // The existing developer freeze registration is routed safely in common.cpp.
 if(!com_developer->integer)Cmd_AddCommand("freeze",CL_StaffCommand_f,"Freeze a player (staff)");
}
