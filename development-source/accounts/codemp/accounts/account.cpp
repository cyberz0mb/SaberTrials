#include "account.h"
#include "vendor/json.hpp"
#include <cmath>
#include <set>
#include <vector>
#include <stdexcept>
namespace staccount {
using nlohmann::json;
const char* const Origin="https://accounts-production-b56d.up.railway.app";
namespace {
void Erase(std::string& s){for(size_t i=0;i<s.size();++i)static_cast<volatile char*>(&s[0])[i]=0;s.clear();}
bool Alphabet(const std::string& s,size_t size,const char* chars){return s.size()==size&&s.find_first_not_of(chars)==std::string::npos;}
bool Token(const std::string& s){return Alphabet(s,43,"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-");}
bool Id(const std::string& s){return Alphabet(s,32,"0123456789abcdef");}
json Parse(const std::string& text){
 if(text.size()>16384)throw std::runtime_error("size");
 std::vector<std::set<std::string>> keys;
 auto callback=[&](int depth,json::parse_event_t event,json& value){
  if(depth>6)throw std::runtime_error("depth");
  if(event==json::parse_event_t::object_start)keys.emplace_back();
  if(event==json::parse_event_t::key&&!keys.back().insert(value.get<std::string>()).second)throw std::runtime_error("duplicate");
  if(event==json::parse_event_t::object_end)keys.pop_back();
  return true;
 };
 auto j=json::parse(text,callback);if(!j.is_object())throw std::runtime_error("object");return j;
}
bool Text(const std::string& s,size_t limit,bool empty=false){
 if((s.empty()&&!empty)||s.size()>limit)return false;
 for(unsigned char c:s)if(c<32||c==127||c=='^'||c=='"'||c==';'||c=='\\')return false;
 return true;
}
bool Profile(const json& j,View& view){
 if(!j.is_object()||!j.at("verified").is_boolean()||!j.at("verified").get<bool>())return false;
 const auto id=j.at("account").get<std::string>(),name=j.at("name").get<std::string>();
 const auto team=j.at("team").get<std::string>(),tag=j.at("teamName").get<std::string>();
 if(!Id(id)||!Text(name,63)||!Text(tag,63,true)||team.size()>128||team.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.:-")!=std::string::npos||(team.empty()!=tag.empty()))return false;
 view.status="Signed in with Discord.";
 if(j.contains("format_points") && j["format_points"].is_number_unsigned())
  view.status="Format points: "+std::to_string(j["format_points"].get<uint64_t>());
 view.name=name;view.team=tag;view.signedIn=true;return true;
}
double Expires(const json& j,double now,double maximum){
 if(!j.at("expires_at").is_number())throw std::runtime_error("expiry");
 double expiry=j.at("expires_at").get<double>();
 if(!std::isfinite(expiry)||expiry<=now||expiry>now+maximum+60)throw std::runtime_error("expiry");return expiry;
}
}
bool ValidBrowserUrl(const std::string& url){
 const std::string prefix=std::string(Origin)+"/login?request=";
 if(url.compare(0,prefix.size(),prefix)||url.size()!=prefix.size()+32+7+43)return false;
 return Id(url.substr(prefix.size(),32))&&url.substr(prefix.size()+32,7)=="&token="&&Token(url.substr(prefix.size()+39));
}
Client::~Client(){Erase(saved_.token);Erase(poll_);Erase(browser_);}
void Client::Hide(){view_.signedIn=false;view_.name="Signed out";view_.team.clear();}
void Client::Clear(const char* status){Erase(saved_.token);saved_.expires=0;saved_.logout=false;++revision_;Hide();view_.busy=false;view_.status=status;}
void Client::Fail(const char* status){start_=false;request_.clear();Erase(poll_);Erase(browser_);Hide();view_.busy=false;view_.status=status;}
void Client::Restore(const Saved& saved,double now){
 if(!Token(saved.token)||!std::isfinite(saved.expires)||saved.expires<=now||saved.expires>now+604860){Clear("Log in with Discord.");return;}
 saved_=saved;due_=now;Hide();view_.busy=true;view_.status=saved.logout?"Finishing sign-out...":"Checking saved sign-in...";
}
void Client::Login(double now){
 if(active_!=Kind::None||start_||!request_.empty()||saved_.logout||view_.signedIn)return;
 cancelled_=false;due_=now;view_.busy=true;
 if(!saved_.token.empty()){view_.status="Checking saved sign-in...";return;}
 start_=true;view_.status="Opening Discord sign-in...";
}
void Client::Logout(double now){
 cancelled_=true;start_=false;request_.clear();Erase(poll_);Erase(browser_);Hide();due_=now;
 saved_.logout=!saved_.token.empty();++revision_;view_.busy=saved_.logout;
 view_.status=saved_.logout?"Signing out...":"Signed out.";
}
Job Client::Next(double now){
 if(!saved_.token.empty()&&saved_.expires<=now)Clear("Sign-in expired. Please log in again.");
 if(!request_.empty()&&now>=deadline_){cancelled_=true;Fail("Sign-in timed out. Please try again.");}
 if(active_!=Kind::None||now<due_)return {};
 Job j;j.method="POST";j.body="{}";
 if(saved_.logout&&!saved_.token.empty()){j.kind=Kind::Logout;j.path="/v1/logout";j.bearer=saved_.token;}
 else if(start_){j.kind=Kind::Start;j.path="/v1/login/start";start_=false;}
 else if(!request_.empty()){j.kind=Kind::Poll;j.path="/v1/login/poll";j.body=json({{"request_id",request_},{"poll_token",poll_}}).dump();}
 else if(!saved_.token.empty()){j.kind=Kind::Profile;j.method="GET";j.path="/v1/me";j.bearer=saved_.token;j.body.clear();}
 if(j.kind!=Kind::None){active_=j.kind;j.serial=++serial_;}return j;
}
void Client::Complete(const Job& job,const Response& response,double now){
 if(job.serial!=serial_||job.kind!=active_||active_==Kind::None)return;
 active_=Kind::None;
 if(job.kind==Kind::Logout){
  if(response.status==200||response.status==401||response.status==403)Clear("Signed out.");
  else {Hide();view_.busy=false;view_.status="Signed out. Server logout will retry.";due_=now+15;}
  return;
 }
 if(job.kind==Kind::Start&&cancelled_)return;
 if(job.kind==Kind::Profile&&saved_.logout){due_=now;return;}
 if(job.kind==Kind::Profile&&(saved_.token.empty()||saved_.expires<=now)){Clear("Sign-in expired. Please log in again.");return;}
 if(job.kind==Kind::Poll&&now>=deadline_){cancelled_=true;Fail("Sign-in timed out. Please try again.");}
 if(response.status!=200){
  if(job.kind==Kind::Profile){
   if(response.status==401||response.status==403)Clear("Sign-in expired or unavailable. Please log in.");
   else {Hide();view_.busy=false;view_.status="Account service unavailable. Retrying...";due_=now+30;}
  }else if(job.kind==Kind::Poll&&!cancelled_&&(response.status==0||response.status==429||response.status>=500)){
   view_.status="Waiting for sign-in. Connection will retry.";due_=now+10;
  }else Fail(cancelled_?"Signed out.":"Could not sign in. Please try again.");
  return;
 }
 try{
  auto j=Parse(response.body);
  if(job.kind==Kind::Start){
   auto request=j.at("request_id").get<std::string>(),secret=j.at("poll_token").get<std::string>(),url=j.at("browser_url").get<std::string>();
   const std::string prefix=std::string(Origin)+"/login?request=";
   if(!Id(request)||!Token(secret)||!ValidBrowserUrl(url)||url.substr(prefix.size(),32)!=request)throw std::runtime_error("link");
   deadline_=Expires(j,now,600);request_=request;poll_=secret;browser_=url;due_=now+5;view_.status="Finish sign-in in your browser.";return;
  }
  if(job.kind==Kind::Poll){
   auto status=j.at("status").get<std::string>();
   if(status=="pending"){if(!cancelled_)due_=now+5;return;}
   if(status!="complete")throw std::runtime_error("status");
   auto token=j.at("session_token").get<std::string>();if(!Token(token))throw std::runtime_error("token");
   double expires=Expires(j,now,604800);
   saved_={token,expires,cancelled_};++revision_;request_.clear();Erase(poll_);Erase(browser_);
   if(cancelled_){view_.busy=true;view_.status="Signing out...";due_=now;return;}
   if(!Profile(j.at("profile"),view_))throw std::runtime_error("profile");
  }else if(!Profile(j,view_))throw std::runtime_error("profile");
  view_.busy=false;due_=now+60;
 }catch(...){
  Fail("Invalid account response. Please try again.");
  if(!saved_.token.empty()){saved_.logout=true;++revision_;due_=now;}
 }
}
std::string Client::TakeBrowserUrl(){std::string result;result.swap(browser_);return result;}
}
