#include "server.h"
#include "sv_staff.h"
#include "../staff/st_staff_wire.h"
#include <memory>
#include <cstring>
#include <sstream>
#include <chrono>
namespace {
st::Store store;st::Identity identity;std::unique_ptr<st::Authority> authority;
st::Generation generations[MAX_CLIENTS]={};bool connected[MAX_CLIENTS]={},targetConnected[MAX_CLIENTS]={};
std::string activeAccounts[MAX_CLIENTS];
bool Ready(){
 if(authority)return true;
 std::string root=st::PrivateRoot();if(root.empty())return false;
 root+="/servers";if(!st::PrivateDirectory(root))return false;
 root+="/"+std::to_string(Cvar_VariableIntegerValue("net_port"));if(!st::PrivateDirectory(root))return false;
 if(!identity.LoadOrCreate(root+"/server.key",true)||!store.Open(root+"/accounts.db")){Com_Printf("Staff storage unavailable; access denied.\n");return false;}
 authority.reset(new st::Authority(store,identity));return true;
}
uint64_t Now(){return (uint64_t)std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
void Reply(const netadr_t* to,const char* command,const st::Bytes& bytes){auto sig=identity.Sign(bytes);if(sig.size()!=64)return;NET_OutOfBandPrint(NS_SERVER,to,"%s %s %s",command,st::Hex(bytes.data(),bytes.size()).c_str(),st::Hex(sig.data(),sig.size()).c_str());}
int Slot(const netadr_t* from){
 if(Cmd_Argc()<2||!com_sv_running->integer)return -1;
 std::string s=Cmd_Argv(1);if(s.empty()||s.size()>2)return -1;int slot=0;for(char c:s){if(c<'0'||c>'9')return -1;slot=slot*10+c-'0';}
 if(slot<0||slot>=sv_maxclients->integer||!connected[slot]||svs.clients[slot].state!=CS_ACTIVE)return -1;
 return NET_CompareAdr(from,&svs.clients[slot].netchan.remoteAddress)?slot:-1;
}
st::Role ParseRole(const char* s){if(!Q_stricmp(s,"admin"))return st::Role::Admin;if(!Q_stricmp(s,"moderator"))return st::Role::Moderator;return st::Role::None;}
void Revoke(const std::string& id){if(authority)authority->Revoke(id);for(auto& a:activeAccounts)if(a==id)a.clear();GVM_StaffRevoke(id.c_str(),-1);}
void PrintAction(const STVerifiedAction& action,bool ok){
 const char* name;
 switch(action.command){
 case ST_CMD_ADD:name="add staff";break;
 case ST_CMD_ROLE:name="change role";break;
 case ST_CMD_REMOVE:name="remove staff";break;
 case ST_CMD_FREEZE:name="freeze";break;
 case ST_CMD_UNFREEZE:name="unfreeze";break;
 case ST_CMD_GHOST_ON:name="ghost on";break;
 case ST_CMD_GHOST_OFF:name="ghost off";break;
 case ST_CMD_SUMMON:name="summon";break;
 case ST_CMD_TRAVEL_PLAYER:case ST_CMD_TRAVEL_COORDS:case ST_CMD_TRAVEL_SERVER:name="travel";break;
 case ST_CMD_LOGOUT:name="logout";break;
 case ST_CMD_TOURNAMENT:name="tournament";break;
 default:return; // Read-only queries and target lookups do not need a second console line.
 }
 Com_Printf("Staff action: %s #%d | %s | %s\n",st::RoleName((st::Role)action.role),action.actorSlot,name,ok?"allowed":"denied");
}
std::string Run(const STVerifiedAction& a,bool& ok){
 ok=false;const std::string actor=a.account;
 switch(a.command){
 case ST_CMD_WHOAMI:ok=true;return st::RoleName((st::Role)a.role);
 case ST_CMD_LIST:{ok=true;std::string out;for(auto row:store.List()){if(!row.enabled)continue;std::string entry=row.label+" ["+st::RoleName(row.role)+"] "+row.id+"; ";if(out.size()+entry.size()>325){out+="... use server console for full roster";break;}out+=entry;}return out.empty()?"No staff accounts":out;}
 case ST_CMD_ADD:case ST_CMD_ROLE:case ST_CMD_REMOVE:{auto old=store.Get(a.args[0]);st::Role role=a.command==ST_CMD_REMOVE?st::Role::None:ParseRole(a.args[1]);if(a.command!=ST_CMD_REMOVE&&role==st::Role::None)return "Choose admin or moderator";
  if(a.command==ST_CMD_ADD&&old.enabled)return "Account already enrolled; use staff role";
  if(a.command!=ST_CMD_ADD&&old.id.empty())return "Unknown account";
  ok=store.Change(actor,a.args[0],role,a.command==ST_CMD_ADD?a.args[2]:old.label,a.command!=ST_CMD_REMOVE);
  if(ok)Revoke(a.args[0]);return ok?"Account updated; previous sessions revoked":"Role change denied or could not be saved";}
 case ST_CMD_RESOLVE:{STTargetRef t={};if(!GVM_StaffResolve(a.args[0],&t))return "No unique eligible player. Use quoted name or #client-ID";ok=true;return std::to_string(t.slot)+" "+st::Hex(t.generation,16);}
 case ST_CMD_LOGOUT:authority->Disconnect(a.actorSlot);activeAccounts[a.actorSlot].clear();GVM_StaffRevoke(actor.c_str(),a.actorSlot);ok=true;return "Logged out";
 case ST_CMD_TRAVEL_SERVER:ok=st::NumericAddress(a.args[0]);return ok?"Server travel authorized":"Use numeric IPv4:port or [IPv6]:port";
 default:{STGameResult result={};if(!GVM_StaffExecute(&a,&result))return "Staff gameplay extension unavailable";ok=result.ok!=0;return result.message;}
 }
}
}
int SV_StaffRole(int slot){if(!authority||slot<0||slot>=MAX_CLIENTS)return 0;return (int)authority->Current(slot).role;}
int SV_StaffGeneration(int slot,unsigned char gen[16]){if(slot<0||slot>=MAX_CLIENTS||!targetConnected[slot])return 0;std::memcpy(gen,generations[slot].data(),16);return 1;}
const STStaffImports* SV_StaffImports(){static STStaffImports imports={ST_STAFF_API_VERSION,sizeof(STStaffImports),SV_StaffRole,SV_StaffGeneration};return &imports;}
// Bots are moderation targets, but never authentication-capable connections.
void SV_StaffConnect(int slot,bool bot){if(slot<0||slot>=MAX_CLIENTS)return;SV_StaffDisconnect(slot);targetConnected[slot]=st::Random(generations[slot].data(),16);connected[slot]=!bot&&targetConnected[slot];}
void SV_StaffDisconnect(int slot){if(slot<0||slot>=MAX_CLIENTS)return;if(!activeAccounts[slot].empty()){std::string old=activeAccounts[slot];activeAccounts[slot].clear();GVM_StaffRevoke(old.c_str(),slot);}if(authority)authority->Disconnect(slot);connected[slot]=targetConnected[slot]=false;generations[slot].fill(0);}
void SV_StaffReset(){GVM_StaffReset();if(authority)authority->Reset();for(int i=0;i<MAX_CLIENTS;i++){connected[i]=targetConnected[i]=false;generations[i].fill(0);activeAccounts[i].clear();}}
void SV_StaffFrame(){if(authority)for(int i=0;i<MAX_CLIENTS;i++)if(!activeAccounts[i].empty()&&!authority->Current(i).enabled){std::string old=activeAccounts[i];activeAccounts[i].clear();GVM_StaffRevoke(old.c_str(),i);}}
bool SV_StaffPacket(const netadr_t* from){
 const std::string command=Cmd_Argv(0);if(command!="sthello"&&command!="stproof"&&command!="staction")return false;
 int slot=Slot(from);if(slot<0||!Ready())return true;
 if(command=="sthello"&&Cmd_Argc()==4){st::Bytes nonce;if(!st::Unhex(Cmd_Argv(3),nonce,32))return true;st::Nonce cn;std::memcpy(cn.data(),nonce.data(),32);auto ch=authority->Begin(slot,generations[slot],Cmd_Argv(2),cn,Now());if(ch.ok)Reply(from,"stchallenge",ch.transcript);return true;}
 if(command=="stproof"&&Cmd_Argc()==3){st::Bytes sig;if(!st::Unhex(Cmd_Argv(2),sig,64))return true;
  auto session=authority->Complete(slot,sig,Now());if(session.ok){if(!session.duplicate){if(!activeAccounts[slot].empty())GVM_StaffRevoke(activeAccounts[slot].c_str(),slot);activeAccounts[slot]=authority->Current(slot).id;}Reply(from,"stsession",st::SessionMessage(session.transcript,session.id));}SV_StaffFrame();return true;}
 if(command=="staction"&&Cmd_Argc()==4){st::Bytes bytes,sig;if(!st::Unhex(Cmd_Argv(2),bytes)||!st::Unhex(Cmd_Argv(3),sig,64))return true;
  auto verified=authority->Verify(slot,generations[slot],bytes,sig,Now());SV_StaffFrame();if(!verified.ok)return true;st::Request req;if(!st::ParseRequest(bytes,req))return true;
  bool ok=false;std::string message;
  if(verified.duplicate){ok=!verified.result.empty()&&verified.result[0]=='1';message=verified.result.substr(1);}
  else {message=Run(verified.action,ok);authority->Remember(slot,req.sequence,std::string(ok?"1":"0")+message);PrintAction(verified.action,ok);}
  Reply(from,"stresult",st::ResultMessage(req.session,req.sequence,ok,message));return true;
 }return true;
}
void SV_StaffConsole_f(){
 if(!Ready())return;const std::string op=Cmd_Argv(1);
 if(op=="serverkey"){Com_Printf("Staff server public key: %s\n",identity.PublicId().c_str());return;}
 if(op=="list"){for(auto a:store.List())Com_Printf("%s | %s | %s | %s\n",a.id.c_str(),a.label.c_str(),st::RoleName(a.role),a.enabled?"enabled":"disabled");return;}
 bool ok=false;std::string target;
 if(op=="owner"&&Cmd_Argc()==5&&!Q_stricmp(Cmd_Argv(2),"add")){target=Cmd_Argv(3);ok=store.BootstrapOwner(target,Cmd_Argv(4));}
 else if(op=="owner"&&Cmd_Argc()==4&&!Q_stricmp(Cmd_Argv(2),"remove")){target=Cmd_Argv(3);auto old=store.Get(target);ok=store.ConsoleChange(target,st::Role::None,old.label,false);}
 else if(op=="add"&&Cmd_Argc()==5){target=Cmd_Argv(2);auto role=ParseRole(Cmd_Argv(3));if(role!=st::Role::None)ok=store.ConsoleChange(target,role,Cmd_Argv(4),true);}
 else if(op=="role"&&Cmd_Argc()==4){target=Cmd_Argv(2);auto old=store.Get(target);auto role=ParseRole(Cmd_Argv(3));if(role!=st::Role::None)ok=store.ConsoleChange(target,role,old.label,true);}
 else if(op=="remove"&&Cmd_Argc()==3){target=Cmd_Argv(2);auto old=store.Get(target);ok=store.ConsoleChange(target,st::Role::None,old.label,false);}
 else {Com_Printf("Server: staff serverkey | list | owner add <public-key> <label> | owner remove <id> | add <key> <admin|moderator> <label> | role <id> <role> | remove <id>\n");return;}
 if(ok)Revoke(target);Com_Printf("Staff: %s\n",ok?"account saved; active sessions revoked":"account change denied or storage unavailable");
}
