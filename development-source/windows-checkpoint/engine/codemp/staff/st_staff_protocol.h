#pragma once
#include "st_staff_identity.h"
#include "st_staff_store.h"
#include <map>
#include <deque>
namespace st {
struct Request {
 Nonce session={};uint64_t sequence=0;int command=0;STTargetRef target={};std::vector<std::string> args;
};
Bytes Encode(const Request&);
bool ParseRequest(const Bytes&,Request&);
Bytes AuthTranscript(const std::string& server,const std::string& account,const Nonce& clientNonce,const Nonce& serverNonce,const Generation& generation);
struct Challenge {bool ok=false;Bytes transcript,signature;};
struct SessionResult {bool ok=false,duplicate=false;Nonce id={};Bytes transcript;};
struct Verification {bool ok=false,duplicate=false;std::string result;STVerifiedAction action={};};
class Authority {
 struct Cached {uint64_t sequence;Bytes bytes;std::string result;};
 struct Connection {
  Generation generation={};std::string account;uint64_t revision=0;
  Bytes challenge;std::string challengeAccount;uint64_t challengeRevision=0,deadline=0;Nonce session={};bool active=false;
  Bytes receiptProof,receiptTranscript;uint64_t receiptUntil=0;
  uint64_t lastBegin=0,window=0,cooldown=0,highest=0;unsigned failures=0,burst=0;
  std::deque<Cached> cache;
 };
 Store& db_;Identity& server_;std::map<int,Connection> connections_;
 bool (*random_)(void*,size_t);
 void Failure(Connection&,uint64_t now);
public:
 Authority(Store& db,Identity& server,bool (*rng)(void*,size_t)=Random):db_(db),server_(server),random_(rng){}
 Challenge Begin(int slot,const Generation&,const std::string& account,const Nonce&,uint64_t now);
 SessionResult Complete(int slot,const Bytes& signature,uint64_t now);
 Verification Verify(int slot,const Generation&,const Bytes&,const Bytes& signature,uint64_t now);
 void Remember(int slot,uint64_t seq,const std::string& result);
 void Disconnect(int slot){connections_.erase(slot);}
 void Reset(){connections_.clear();}
 void Revoke(const std::string& account);
 Account Current(int slot);
};
}
