#include "account.h"
#include "vendor/json.hpp"
#include <iostream>
#include <filesystem>
#include <fstream>
#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#define GetCurrentProcessId getpid
#endif
#include <stdexcept>
using namespace staccount;
using nlohmann::json;
#define CHECK(x) do{if(!(x))throw std::runtime_error(#x);}while(0)
const std::string token(43,'t'),rid(32,'a'),poll(43,'p');
json profile(){return {{"account",rid},{"name","SamplePlayer"},{"team",""},{"teamName",""},{"verified",true}};}
Response start(){return {200,json({{"request_id",rid},{"poll_token",poll},{"browser_url",std::string(Origin)+"/login?request="+rid+"&token="+token},{"expires_at",1600},{"poll_interval",5}}).dump()};}
Response complete(){return {200,json({{"status","complete"},{"session_token",token},{"expires_at",600000},{"profile",profile()}}).dump()};}
void begin(Client& c){c.Login(1000);auto j=c.Next(1000);CHECK(j.kind==Kind::Start);c.Complete(j,start(),1000);}
void signedIn(Client& c){begin(c);auto j=c.Next(1005);CHECK(j.kind==Kind::Poll);CHECK(j.bearer.empty());c.Complete(j,complete(),1005);CHECK(c.Status().signedIn);}
int main(int argc,char** argv){try{
 if(argc==2&&std::string(argv[1])=="--health") {Job j;j.method="GET";j.path="/healthz";auto r=Send(j);CHECK(r.status==200);CHECK(json::parse(r.body)["status"]=="ok");std::cout<<"Native HTTPS health check passed.\n";return 0;}
 Client c; signedIn(c);CHECK(c.Status().name=="SamplePlayer");CHECK(c.Record().token==token);
 c.Logout(1006);CHECK(!c.Status().signedIn);CHECK(c.Record().logout);auto out=c.Next(1006);CHECK(out.kind==Kind::Logout);CHECK(out.bearer==token);
 c.Complete(out,{0,""},1006);CHECK(c.Record().logout);CHECK(!c.Status().signedIn);CHECK(c.Next(1007).kind==Kind::None);
 Client restarted;restarted.Restore(c.Record(),1010);out=restarted.Next(1010);CHECK(out.kind==Kind::Logout);restarted.Complete(out,{200,"{}"},1010);CHECK(restarted.Record().token.empty());
 Client cancelled;begin(cancelled);auto inflight=cancelled.Next(1005);cancelled.Logout(1006);cancelled.Complete(inflight,complete(),1007);CHECK(!cancelled.Status().signedIn);CHECK(cancelled.Next(1007).kind==Kind::Logout);CHECK(cancelled.TakeBrowserUrl().empty());
 Client restore;restore.Restore({token,600000,false},1000);CHECK(!restore.Status().signedIn);auto verify=restore.Next(1000);CHECK(verify.kind==Kind::Profile);restore.Complete(verify,{403,"{}"},1000);CHECK(restore.Record().token.empty());
 Client expired;expired.Restore({token,999,false},1000);CHECK(expired.Record().token.empty());CHECK(expired.Next(1000).kind==Kind::None);
 Client timeout;begin(timeout);CHECK(timeout.Next(1601).kind==Kind::None);CHECK(!timeout.Status().busy);
 Client late;begin(late);auto lateJob=late.Next(1599);CHECK(lateJob.kind==Kind::Poll);late.Next(1601);late.Complete(lateJob,complete(),1602);CHECK(!late.Status().signedIn);CHECK(late.Next(1602).kind==Kind::Logout);
 Client expiredFlight;expiredFlight.Restore({token,1002,false},1000);auto expiredJob=expiredFlight.Next(1000);expiredFlight.Next(1003);expiredFlight.Complete(expiredJob,{200,profile().dump()},1004);CHECK(!expiredFlight.Status().signedIn);CHECK(expiredFlight.Record().token.empty());
 for(const std::string body:std::vector<std::string>{"{}","[]","null","{",std::string(17000,'x'),"{\"status\":\"pending\",\"status\":\"complete\"}"}){Client bad;begin(bad);auto j=bad.Next(1005);bad.Complete(j,{200,body},1005);CHECK(!bad.Status().signedIn);}
 for(const std::string name:{"evil^1","bad;quit","bad\nname","bad\"name"}){Client bad;begin(bad);auto j=bad.Next(1005);auto r=json::parse(complete().body);r["profile"]["name"]=name;bad.Complete(j,{200,r.dump()},1005);CHECK(!bad.Status().signedIn);}
 Client unicode;begin(unicode);auto j=unicode.Next(1005);auto r=json::parse(complete().body);r["profile"]["name"]="Jawa \u00e9";unicode.Complete(j,{200,r.dump(-1,' ',true)},1005);CHECK(unicode.Status().name=="Jawa \u00e9");
 Client offline;signedIn(offline);j=offline.Next(1066);CHECK(j.kind==Kind::Profile);offline.Complete(j,{0,""},1066);CHECK(!offline.Status().signedIn);CHECK(!offline.Record().token.empty());
 const std::string url=std::string(Origin)+"/login?request="+rid+"&token="+token;CHECK(ValidBrowserUrl(url));
 for(auto bad:{url+"&extra=1",std::string("http://")+url.substr(8),std::string("https://evil.test/login?request=")+rid+"&token="+token,std::string(Origin)+".evil.test/login?request="+rid+"&token="+token})CHECK(!ValidBrowserUrl(bad));
 auto root=std::filesystem::temp_directory_path()/("st-account-test-"+std::to_string(GetCurrentProcessId()));std::filesystem::create_directory(root);
 auto path=(root/"session.bin").string();CHECK(Save(path,{token,600000,true}));Saved saved;CHECK(Load(path,saved));CHECK(saved.token==token&&saved.logout);
 std::ifstream f(path,std::ios::binary);std::string bytes((std::istreambuf_iterator<char>(f)),{});f.close();CHECK(bytes.find(token)==std::string::npos);
 bytes.back()^=1;{std::ofstream f2(path,std::ios::binary|std::ios::trunc);f2<<bytes;}CHECK(!Load(path,saved));
 CHECK(Save(path,{}));CHECK(Load(path,saved));CHECK(saved.token.empty());std::filesystem::remove_all(root);
 std::cout<<"Account state, response validation, cancellation, URL, and protected storage checks passed.\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
