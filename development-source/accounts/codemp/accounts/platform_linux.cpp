#include "account.h"
#include "vendor/json.hpp"
#include "st_private_linux.h"
#include <curl/curl.h>
#include <sodium.h>
#include <cmath>
#include <unistd.h>
#include <cerrno>
namespace staccount {
namespace {
bool Token(const std::string&s){return s.size()==43&&s.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")==std::string::npos;}
size_t Receive(char* data,size_t size,size_t count,void* context){
 auto& body=*static_cast<std::string*>(context);
 if(size&&count>16384/size)return 0;size_t n=size*count;
 if(body.size()+n>16384)return 0;body.append(data,n);return n;
}
struct Request {CURL* handle=nullptr;curl_slist* headers=nullptr;~Request(){if(handle)curl_easy_cleanup(handle);if(headers)curl_slist_free_all(headers);}};
}
Response Send(const Job& job){
 if(job.path!="/healthz"&&job.path!="/v1/login/start"&&job.path!="/v1/login/poll"&&job.path!="/v1/me"&&job.path!="/v1/logout"&&job.path!="/v2/connection/authorize"&&job.path!="/v2/server/challenge"&&job.path!="/v1/server/redeem"&&job.path!="/v1/server/renew")return {};
 if((job.method!="GET"&&job.method!="POST")||job.body.size()>4096||(!job.bearer.empty()&&!Token(job.bearer)))return {};
 static const bool initialized=curl_global_init(CURL_GLOBAL_DEFAULT)==CURLE_OK;if(!initialized)return {};
 Request r;r.handle=curl_easy_init();if(!r.handle)return {};
 const std::string url=std::string(Origin)+job.path;Response response;
 r.headers=curl_slist_append(r.headers,"Accept: application/json");r.headers=curl_slist_append(r.headers,"Content-Type: application/json");
 if(!job.bearer.empty()){std::string auth="Authorization: Bearer "+job.bearer;r.headers=curl_slist_append(r.headers,auth.c_str());sodium_memzero(&auth[0],auth.size());}
 if(!r.headers)return {};
 // Every setting must succeed. No redirects, cookies, netrc, insecure TLS or custom hosts.
#define SET(option,value) if(curl_easy_setopt(r.handle,option,value)!=CURLE_OK)return {}
 SET(CURLOPT_URL,url.c_str());SET(CURLOPT_HTTPHEADER,r.headers);SET(CURLOPT_USERAGENT,"SaberTrials/Account-1");
 SET(CURLOPT_PROTOCOLS,CURLPROTO_HTTPS);SET(CURLOPT_REDIR_PROTOCOLS,CURLPROTO_HTTPS);SET(CURLOPT_FOLLOWLOCATION,0L);
 SET(CURLOPT_NETRC,CURL_NETRC_IGNORED);SET(CURLOPT_SSL_VERIFYPEER,1L);SET(CURLOPT_SSL_VERIFYHOST,2L);
 SET(CURLOPT_SSLVERSION,CURL_SSLVERSION_TLSv1_2);SET(CURLOPT_NOSIGNAL,1L);SET(CURLOPT_CONNECTTIMEOUT_MS,5000L);SET(CURLOPT_TIMEOUT_MS,10000L);
 SET(CURLOPT_WRITEFUNCTION,Receive);SET(CURLOPT_WRITEDATA,&response.body);
 if(job.method=="POST"){SET(CURLOPT_POST,1L);SET(CURLOPT_POSTFIELDS,job.body.data());SET(CURLOPT_POSTFIELDSIZE,(long)job.body.size());}
#undef SET
 if(curl_easy_perform(r.handle)!=CURLE_OK)return {};
 long status=0;if(curl_easy_getinfo(r.handle,CURLINFO_RESPONSE_CODE,&status)!=CURLE_OK)return {};
 response.status=(int)status;return response;
}
bool Save(const std::string&path,const Saved&saved){
 if(path.empty()||(!saved.token.empty()&&(!Token(saved.token)||!std::isfinite(saved.expires))))return false;
 auto text=nlohmann::json({{"token",saved.token},{"expires",saved.expires},{"logout",saved.logout}}).dump();
 st::Bytes plain(text.begin(),text.end());sodium_memzero(&text[0],text.size());bool ok=st::ProtectFile(path,"STAC",plain,true);sodium_memzero(plain.data(),plain.size());return ok;
}
bool Load(const std::string&path,Saved&saved){
 saved={};st::Bytes plain;if(!st::UnprotectFile(path,"STAC",plain))return false;bool ok=false;
 try{auto j=nlohmann::json::parse(plain);auto token=j.at("token").get<std::string>();double expiry=j.at("expires").get<double>();bool logout=j.at("logout").get<bool>();
  if((token.empty()||Token(token))&&std::isfinite(expiry)){saved={token,expiry,logout};ok=true;}
 }catch(...){}sodium_memzero(plain.data(),plain.size());return ok;
}
std::string SessionPath(){auto root=st::LinuxStateRoot("accounts");return root.empty()?root:root+"/session.bin";}
bool Forget(const std::string&path){return !path.empty()&&(unlink(path.c_str())==0||errno==ENOENT);}
// This target is a headless server. Browser login belongs to the player's client.
bool OpenBrowser(const std::string&){return false;}
}
