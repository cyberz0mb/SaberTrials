#include "bridge.h"
#include "vendor/json.hpp"
#include <algorithm>
#include <cmath>
#include <set>
#include <vector>
#include <stdexcept>
namespace staccount {
namespace {
using nlohmann::json;
bool Id(const std::string&s){return s.size()==32&&s.find_first_not_of("0123456789abcdef")==std::string::npos;}
bool Token(const std::string&s){return s.size()==43&&s.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")==std::string::npos;}
bool Identifier(const std::string&s,size_t limit=64){return !s.empty()&&s.size()<=limit&&s.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.:-")==std::string::npos;}
bool Text(const std::string&s){if(s.empty()||s.size()>63)return false;for(unsigned char c:s)if(c<32||c==127||c=='^'||c=='"'||c==';'||c=='\\')return false;return true;}
bool SlotNumber(int i){return i>=0&&i<64;}
json Parse(const std::string&text){
 if(text.size()>16384)throw std::runtime_error("size");
 std::vector<std::set<std::string>> keys;
 auto cb=[&](int depth,json::parse_event_t e,json&v){
  if(depth>6)throw std::runtime_error("depth");
  if(e==json::parse_event_t::object_start)keys.emplace_back();
  if(e==json::parse_event_t::key&&!keys.back().insert(v.get<std::string>()).second)throw std::runtime_error("duplicate");
  if(e==json::parse_event_t::object_end)keys.pop_back();return true;
 };
 auto j=json::parse(text,cb);if(!j.is_object())throw std::runtime_error("object");return j;
}
double Lifetime(const json&j,double wall,double maximum){
 double remaining=j.at("expires_at").get<double>()-wall;
 if(!std::isfinite(remaining)||remaining<=0||remaining>maximum+5)throw std::runtime_error("expiry");
 return std::min(remaining,maximum);
}
RankProfile ReadProfile(const json&j){
 RankProfile p;
 if(!j.at("verified").is_boolean()||!j.at("verified").get<bool>())throw std::runtime_error("unverified");
 p.account=j.at("account").get<std::string>();p.name=j.at("name").get<std::string>();p.team=j.at("team").get<std::string>();p.tag=j.at("teamName").get<std::string>();
 if(!Id(p.account)||!Text(p.name)||(!p.team.empty()&&(!Identifier(p.team)||!Text(p.tag)))||(p.team.empty()!=p.tag.empty()))throw std::runtime_error("profile");
 return p;
}
}
ServerBridge::ServerBridge(std::string s,std::string c,std::string i):server_(std::move(s)),credential_(std::move(c)),instance_(std::move(i)){
 enabled_=Identifier(server_,128)&&Token(credential_)&&Id(instance_);
}
void ServerBridge::Drop(int i,double retry){
 auto generation=slots_[i].generation;slots_[i]={};slots_[i].generation=generation;slots_[i].serial=++sequence_;slots_[i].beginAfter=retry;
}
void ServerBridge::Connect(int i,const std::string&gen){if(!SlotNumber(i))return;Disconnect(i);if(enabled_&&Id(gen))slots_[i].generation=gen;}
void ServerBridge::Disconnect(int i){if(!SlotNumber(i))return;Drop(i);slots_[i].generation.clear();}
bool ServerBridge::Begin(int i,const std::string&nonce,double now){
 if(!SlotNumber(i)||!enabled_||!Id(nonce)||slots_[i].generation.empty()||now<slots_[i].beginAfter)return false;
 Drop(i,now+10);auto&s=slots_[i];s.nonce=nonce;s.phase=Phase::Challenge;s.due=now;s.expires=now+90;return true;
}
bool ServerBridge::Ready(int i,const std::string&nonce,double now){
 Tick(now);if(!SlotNumber(i))return false;auto&s=slots_[i];
 if(s.phase!=Phase::Await||s.nonce!=nonce)return false;s.phase=Phase::Redeem;s.due=now;return true;
}
bool ServerBridge::Clear(int i,const std::string&nonce){if(!SlotNumber(i)||nonce.empty()||slots_[i].nonce!=nonce)return false;Drop(i,slots_[i].beginAfter);return true;}
void ServerBridge::Tick(double now){for(int i=0;i<64;i++)if(slots_[i].phase!=Phase::Idle&&now>=slots_[i].expires)Drop(i,now+10);}
ServerWork ServerBridge::Next(double /*wall*/,double now){
 Tick(now);
 for(int n=0;n<64;n++){
  int i=(cursor_+n)%64;auto&s=slots_[i];if(s.pending||now<s.due||s.phase==Phase::Idle||s.phase==Phase::Await)continue;
  ServerWork w;w.slot=i;w.http.method="POST";w.http.bearer=credential_;
  if(s.phase==Phase::Challenge){w.http.path="/v2/server/challenge";w.http.body=json({{"instance",instance_},{"slot",i},{"generation",s.generation},{"client_nonce",s.nonce}}).dump();}
  else if(s.phase==Phase::Redeem){w.http.path="/v1/server/redeem";w.http.body=json({{"challenge",s.challenge},{"instance",instance_},{"slot",i},{"generation",s.generation}}).dump();}
  else {w.http.path="/v1/server/renew";w.http.body=json({{"lease_token",s.lease}}).dump();}
  w.http.serial=s.serial=++sequence_;s.pending=true;cursor_=(i+1)%64;return w;
 }return {};
}
void ServerBridge::Complete(const ServerWork&w,const Response&r,double wall,double now){
 Tick(now);if(!SlotNumber(w.slot))return;auto&s=slots_[w.slot];
 if(!s.pending||s.serial!=w.http.serial)return;s.pending=false;
 if(r.status!=200){
  if(s.phase==Phase::Verified&&(r.status==0||r.status==429||r.status>=500)){s.due=now+5;return;}
  Drop(w.slot,now+30);return;
 }
 try{
  auto j=Parse(r.body);
  if(j.at("instance").get<std::string>()!=instance_||j.at("generation").get<std::string>()!=s.generation||!j.at("slot").is_number_integer()||j.at("slot").get<int>()!=w.slot)throw std::runtime_error("binding");
  if(s.phase==Phase::Challenge){
   auto token=j.at("challenge").get<std::string>();if(!Token(token)||j.at("server").get<std::string>()!=server_)throw std::runtime_error("server");
   s.expires=std::min(s.expires,now+Lifetime(j,wall,90));s.challenge=token;s.phase=Phase::Await;return;
  }
  auto p=ReadProfile(j.at("profile"));
  if(!s.profile.account.empty()&&s.profile.account!=p.account)throw std::runtime_error("identity changed");
  if(s.phase==Phase::Redeem){auto token=j.at("lease_token").get<std::string>();if(!Token(token))throw std::runtime_error("lease");s.lease=token;}
  s.expires=now+Lifetime(j,wall,60);s.profile=p;s.phase=Phase::Verified;s.challenge.clear();s.due=now+20;
 }catch(...){Drop(w.slot,now+30);}
}
RankProfile ServerBridge::Profile(int i)const{return SlotNumber(i)?slots_[i].profile:RankProfile{};}
std::string ServerBridge::Challenge(int i)const{return SlotNumber(i)&&slots_[i].phase==Phase::Await?slots_[i].challenge:std::string();}
std::string ServerBridge::Nonce(int i)const{return SlotNumber(i)?slots_[i].nonce:std::string();}
bool ServerBridge::Idle(int i)const{return SlotNumber(i)&&slots_[i].phase==Phase::Idle;}
void ClientBridge::Reset(){endpoint_.clear();nonce_.clear();challenge_.clear();slot_=-1;pending_=finished_=authorized_=false;++serial_;}
bool ClientBridge::Begin(const std::string&endpoint,int slot,const std::string&nonce){
 Reset();if(!SlotNumber(slot)||!Id(nonce)||endpoint.empty()||endpoint.size()>64||endpoint.find_first_not_of("0123456789abcdefABCDEF.:[]")!=std::string::npos||endpoint.find(':')==std::string::npos)return false;
 endpoint_=endpoint;slot_=slot;nonce_=nonce;return true;
}
bool ClientBridge::Offer(const std::string&nonce,const std::string&challenge){if(nonce_!=nonce||nonce.empty()||pending_||finished_||!Token(challenge))return false;challenge_=challenge;return true;}
Job ClientBridge::Next(const std::string&session){
 if(pending_||finished_||challenge_.empty()||!Token(session))return {};
 Job j;j.serial=++serial_;j.method="POST";j.path="/v2/connection/authorize";j.bearer=session;
 j.body=json({{"challenge",challenge_},{"endpoint",endpoint_},{"client_nonce",nonce_},{"slot",slot_}}).dump();pending_=true;return j;
}
void ClientBridge::Complete(const Job&j,const Response&r){
 if(!pending_||j.serial!=serial_)return;pending_=false;finished_=true;
 try{auto value=Parse(r.body);authorized_=r.status==200&&value.at("authorized").is_boolean()&&value.at("authorized").get<bool>();}catch(...){authorized_=false;}
 challenge_.clear();
}
}
