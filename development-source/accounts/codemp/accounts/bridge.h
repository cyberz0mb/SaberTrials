#pragma once
#include "account.h"
#include <array>
namespace staccount {
struct RankProfile {std::string account,name,team,tag;};
struct ServerWork {Job http;int slot=-1;};
class ServerBridge {
    enum class Phase {Idle,Challenge,Await,Redeem,Verified};
    struct Slot {
        std::string generation,nonce,challenge,lease;
        RankProfile profile;
        Phase phase=Phase::Idle;
        uint64_t serial=0;
        bool pending=false;
        double expires=0,due=0,beginAfter=0;
    };
    std::array<Slot,64> slots_;
    std::string server_,credential_,instance_;
    uint64_t sequence_=0;int cursor_=0;
    bool enabled_=false;
    void Drop(int slot,double retry=0);
public:
    ServerBridge(std::string server,std::string credential,std::string instance);
    void Connect(int slot,const std::string& generation);
    void Disconnect(int slot);
    bool Begin(int slot,const std::string& nonce,double monotonic);
    bool Ready(int slot,const std::string& nonce,double monotonic);
    bool Clear(int slot,const std::string& nonce);
    void Tick(double monotonic);
    ServerWork Next(double wall,double monotonic);
    void Complete(const ServerWork&,const Response&,double wall,double monotonic);
    std::string AwardLease(int i) const { return i>=0 && i<64 && slots_[i].phase==Phase::Verified ? slots_[i].lease : std::string(); }
    const std::string& Credential() const { return credential_; }
    RankProfile Profile(int slot)const;
    std::string Challenge(int slot)const;
    std::string Nonce(int slot)const;
    bool Idle(int slot)const;
};
class ClientBridge {
    std::string endpoint_,nonce_,challenge_;
    int slot_=-1;
    uint64_t serial_=0;
    bool pending_=false,finished_=false,authorized_=false;
public:
    void Reset();
    bool Begin(const std::string& endpoint,int slot,const std::string& nonce);
    bool Offer(const std::string& nonce,const std::string& challenge);
    Job Next(const std::string& session);
    void Complete(const Job&,const Response&);
    bool Authorized()const{return authorized_;}
    const std::string& Nonce()const{return nonce_;}
};
}
