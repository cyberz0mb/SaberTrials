#include "bridge.h"
#include "vendor/json.hpp"
#include <iostream>
#include <stdexcept>
using namespace staccount;
using nlohmann::json;
#define CHECK(x) do{if(!(x))throw std::runtime_error(#x);}while(0)
const std::string credential(43,'s'),session(43,'p'),challenge(43,'c'),lease(43,'l');
const std::string generation(32,'a'),nonce(32,'b'),boot(32,'d');
json profile(){return {{"account",std::string(32,'e')},{"name","Jawa"},{"team","clan-jawa"},{"teamName","[JAWA]"},{"verified",true}};}
Response issued(){return {200,json({{"challenge",challenge},{"server","temple"},{"instance",boot},{"slot",3},{"generation",generation},{"expires_at",1090}}).dump()};}
Response redeemed(){return {200,json({{"lease_token",lease},{"instance",boot},{"slot",3},{"generation",generation},{"expires_at",1060},{"profile",profile()}}).dump()};}
void start(ServerBridge& s){s.Connect(3,generation);CHECK(s.Begin(3,nonce,0));}
void verify(ServerBridge& s){start(s);auto j=s.Next(1000,0);CHECK(j.http.path=="/v2/server/challenge");s.Complete(j,issued(),1000,0);CHECK(s.Challenge(3)==challenge);CHECK(s.Ready(3,nonce,1));j=s.Next(1001,1);CHECK(j.http.path=="/v1/server/redeem");s.Complete(j,redeemed(),1001,1);CHECK(s.Profile(3).account==std::string(32,'e'));}
int main(){try{
 ServerBridge s("temple",credential,boot);verify(s);CHECK(s.Profile(3).name=="Jawa");CHECK(s.Profile(3).team=="clan-jawa");
 CHECK(s.Next(1019,19).http.path.empty());auto renew=s.Next(1021,21);CHECK(renew.http.path=="/v1/server/renew");
 s.Complete(renew,{0,""},1022,22);CHECK(!s.Profile(3).account.empty());s.Tick(60);CHECK(s.Profile(3).account.empty());
 // An in-flight reply may not authenticate a replacement in the same slot.
 ServerBridge stale("temple",credential,boot);start(stale);auto old=stale.Next(1000,0);stale.Disconnect(3);stale.Connect(3,std::string(32,'f'));stale.Complete(old,issued(),1000,1);CHECK(stale.Challenge(3).empty());
 // Revoke immediately on explicit denial, without waiting out the lease.
 ServerBridge denied("temple",credential,boot);verify(denied);auto j=denied.Next(1021,21);denied.Complete(j,{403,"{}"},1021,21);CHECK(denied.Profile(3).account.empty());
 // A changed or malicious HTTP binding/profile never reaches the game.
 for(const char* field:{"instance","generation","slot","profile"}){
  ServerBridge bad("temple",credential,boot);start(bad);j=bad.Next(1000,0);bad.Complete(j,issued(),1000,0);CHECK(bad.Ready(3,nonce,1));j=bad.Next(1001,1);auto r=json::parse(redeemed().body);
  if(std::string(field)=="slot")r[field]=4;else if(std::string(field)=="profile")r[field]["name"]="Bad;quit";else r[field]=std::string(32,'f');
  bad.Complete(j,{200,r.dump()},1001,1);CHECK(bad.Profile(3).account.empty());
 }
 ServerBridge logout("temple",credential,boot);verify(logout);CHECK(!logout.Clear(3,std::string(32,'f')));CHECK(logout.Clear(3,nonce));CHECK(logout.Profile(3).account.empty());
 ServerBridge pending("temple",credential,boot);start(pending);j=pending.Next(1000,0);pending.Complete(j,issued(),1000,0);CHECK(!pending.Ready(3,std::string(32,'f'),1));pending.Tick(91);CHECK(pending.Challenge(3).empty());
 // Client sends credentials only to fixed HTTPS transport, not server messages.
 ClientBridge c;CHECK(c.Begin("192.0.2.10:29070",3,nonce));CHECK(c.Offer(nonce,challenge));j={};auto auth=c.Next(session);CHECK(auth.path=="/v2/connection/authorize");auto body=json::parse(auth.body);CHECK(body["endpoint"]=="192.0.2.10:29070");CHECK(body["slot"]==3);CHECK(body["client_nonce"]==nonce);CHECK(auth.bearer==session);CHECK(auth.body.find(session)==std::string::npos);
 c.Reset();c.Complete(auth,{200,"{\"authorized\":true}"});CHECK(!c.Authorized());
 CHECK(c.Begin("192.0.2.10:29070",3,nonce));CHECK(!c.Offer(std::string(32,'f'),challenge));CHECK(c.Offer(nonce,challenge));auth=c.Next(session);c.Complete(auth,{200,"{\"authorized\":true}"});CHECK(c.Authorized());CHECK(c.Next(session).path.empty());
 CHECK(!c.Begin("evil.test;quit",3,nonce));
 std::cout<<"Connection binding, lease expiry, denial, stale replies, logout and player-token separation passed.\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
