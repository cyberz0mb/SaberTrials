#include "st_staff_protocol.h"
#include <cstring>
#include <algorithm>
namespace st {
namespace {
void U(Bytes& b,uint64_t v,int n){for(int i=0;i<n;i++)b.push_back((unsigned char)(v>>(i*8)));}
void Append(Bytes& b,const unsigned char* p,size_t n){b.insert(b.end(),p,p+n);}
struct Reader {const Bytes& b;size_t pos=0;bool ok=true;uint64_t U(int n){if(pos+n>b.size()){ok=false;return 0;}uint64_t v=0;for(int i=0;i<n;i++)v|=(uint64_t)b[pos++]<<(i*8);return v;}void Read(unsigned char* p,size_t n){if(pos+n>b.size()){ok=false;return;}std::memcpy(p,b.data()+pos,n);pos+=n;}};
bool Shape(const Request& r){
 if(!r.sequence||r.command<ST_CMD_LIST||r.command>ST_CMD_TOURNAMENT||r.args.size()>ST_STAFF_MAX_ARGS)return false;
 for(const auto& s:r.args){if(s.empty()||s.size()>=ST_STAFF_ARG_SIZE)return false;for(unsigned char c:s)if(c<32||c==127)return false;}
 bool target=r.command==ST_CMD_FREEZE||r.command==ST_CMD_UNFREEZE||r.command==ST_CMD_SUMMON||r.command==ST_CMD_TRAVEL_PLAYER;
 if(target){if(r.target.slot<0||r.target.slot>=64)return false;bool any=false;for(auto c:r.target.generation)any|=c!=0;if(!any)return false;}
 else {if(r.target.slot!=0)return false;for(auto c:r.target.generation)if(c)return false;}
 const size_t n=r.args.size();
 if(r.command==ST_CMD_TOURNAMENT)return (n==2&&(r.args[0]=="pause"||r.args[0]=="resume"||r.args[0]=="restart"))||(n==3&&r.args[0]=="disqualify");
 switch(r.command){case ST_CMD_ADD:return n==3;case ST_CMD_ROLE:return n==2;case ST_CMD_REMOVE:case ST_CMD_TRAVEL_SERVER:case ST_CMD_RESOLVE:return n==1;case ST_CMD_TRAVEL_COORDS:return n==3;default:return n==0;}
}
}
Bytes Encode(const Request& r){
 if(!Shape(r))return {};Bytes b={'S','T','A',1};Append(b,r.session.data(),32);U(b,r.sequence,8);U(b,r.command,2);U(b,(uint32_t)r.target.slot,4);Append(b,r.target.generation,16);U(b,r.args.size(),1);
 for(const auto& s:r.args){U(b,s.size(),2);Append(b,(const unsigned char*)s.data(),s.size());}if(b.size()>420)return {};return b;
}
bool ParseRequest(const Bytes& b,Request& r){
 r=Request();if(b.size()<67||b.size()>420||std::memcmp(b.data(),"STA\1",4))return false;Reader p{b};p.pos=4;p.Read(r.session.data(),32);r.sequence=p.U(8);r.command=(int)p.U(2);r.target.slot=(int)p.U(4);p.Read(r.target.generation,16);size_t n=(size_t)p.U(1);if(n>4)return false;
 for(size_t i=0;i<n;i++){size_t len=(size_t)p.U(2);if(!p.ok||len>=ST_STAFF_ARG_SIZE||p.pos+len>b.size())return false;r.args.emplace_back((const char*)b.data()+p.pos,len);p.pos+=len;}
 return p.ok&&p.pos==b.size()&&Shape(r);
}
Bytes AuthTranscript(const std::string& server,const std::string& account,const Nonce& cn,const Nonce& sn,const Generation& gen){
 Bytes sk,pk;if(!Unhex(server,sk,32)||!Unhex(account,pk,32))return {};Bytes b={'S','T','L',1};Append(b,sk.data(),32);Append(b,pk.data(),32);Append(b,cn.data(),32);Append(b,sn.data(),32);Append(b,gen.data(),16);return b;
}
void Authority::Failure(Connection& c,uint64_t now){if(now<c.window||now-c.window>=30000){c.window=now;c.failures=0;}if(++c.failures>=5){c.cooldown=now+30000;c.challenge.clear();c.active=false;}}
Challenge Authority::Begin(int slot,const Generation& gen,const std::string& id,const Nonce& cn,uint64_t now){
 Challenge out;if(slot<0||slot>=64||!ValidId(id))return out;
 auto& c=connections_[slot];if(c.generation!=gen){c=Connection();c.generation=gen;}
 if(now<c.cooldown||(c.lastBegin&&now-c.lastBegin<1000))return out;
 c.lastBegin=now;c.challenge.clear();
 auto a=db_.Get(id);if(!a.enabled||a.role==Role::None||server_.PublicId().empty())return out;
 Nonce sn;if(!random_(sn.data(),sn.size()))return out;
 c.challengeAccount=id;c.challengeRevision=a.revision;c.challenge=AuthTranscript(server_.PublicId(),id,cn,sn,gen);c.deadline=now+30000;
 out.transcript=c.challenge;out.signature=server_.Sign(out.transcript);out.ok=out.signature.size()==64;return out;
}
SessionResult Authority::Complete(int slot,const Bytes& sig,uint64_t now){
 SessionResult out;auto it=connections_.find(slot);if(it==connections_.end())return out;auto& c=it->second;
 if(c.active&&now<c.receiptUntil&&sig==c.receiptProof&&Current(slot).enabled){out.ok=true;out.duplicate=true;out.id=c.session;out.transcript=c.receiptTranscript;return out;}
 Bytes transcript;transcript.swap(c.challenge);if(transcript.empty()||now>=c.deadline||now<c.cooldown)return out;
 if(!Identity::Verify(c.challengeAccount,transcript,sig)){Failure(c,now);return out;}
 auto a=db_.Get(c.challengeAccount);Nonce fresh;if(!a.enabled||a.revision!=c.challengeRevision||!random_(fresh.data(),32))return out;
 c.account=c.challengeAccount;c.revision=c.challengeRevision;c.session=fresh;c.active=true;c.cache.clear();c.highest=0;c.receiptProof=sig;c.receiptTranscript=transcript;c.receiptUntil=now+30000;out.ok=true;out.id=c.session;out.transcript=transcript;return out;
}
Account Authority::Current(int slot){auto i=connections_.find(slot);if(i==connections_.end()||!i->second.active)return {};auto a=db_.Get(i->second.account);if(!a.enabled||a.revision!=i->second.revision){i->second.active=false;return {};}return a;}
Verification Authority::Verify(int slot,const Generation& gen,const Bytes& bytes,const Bytes& sig,uint64_t now){
 Verification out;auto it=connections_.find(slot);if(it==connections_.end())return out;auto& c=it->second;
 if(!c.active||c.generation!=gen||now<c.cooldown)return out;
 auto account=Current(slot);if(!account.enabled)return out;Request r;if(!ParseRequest(bytes,r)||r.session!=c.session){Failure(c,now);return out;}
 if(!Identity::Verify(c.account,bytes,sig)){Failure(c,now);return out;}
 if(r.sequence<=c.highest){for(auto& e:c.cache)if(e.sequence==r.sequence&&e.bytes==bytes){out.ok=true;out.duplicate=true;out.result=e.result;return out;}return out;}
 c.highest=r.sequence;if(c.cache.size()>=64)c.cache.pop_front();c.cache.push_back({r.sequence,bytes,"Request consumed; result unavailable"});
 out.ok=true;auto& a=out.action;std::memcpy(a.account,c.account.c_str(),65);a.actorSlot=slot;a.role=(int)account.role;a.revision=account.revision;a.sequence=r.sequence;a.command=r.command;a.target=r.target;a.argc=(int)r.args.size();for(int i=0;i<a.argc;i++)std::memcpy(a.args[i],r.args[i].c_str(),r.args[i].size()+1);return out;
}
void Authority::Remember(int slot,uint64_t seq,const std::string& result){auto i=connections_.find(slot);if(i!=connections_.end())for(auto& e:i->second.cache)if(e.sequence==seq){e.result=result.substr(0,768);break;}}
void Authority::Revoke(const std::string& id){for(auto& item:connections_)if(item.second.account==id){item.second.active=false;item.second.challenge.clear();item.second.cache.clear();}}
}
