#include "account.h"
#include "vendor/json.hpp"
#include "st_staff_types.h"
#include <windows.h>
#include <winhttp.h>
#include <wincrypt.h>
#include <shellapi.h>
#include <cmath>
namespace staccount {
namespace {
std::wstring Wide(const std::string& s){
 int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.data(),(int)s.size(),nullptr,0);
 if(n<=0)return {};std::wstring out(n,L'\0');MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.data(),(int)s.size(),&out[0],n);return out;
}
struct Handle {HINTERNET h=nullptr;Handle(HINTERNET value):h(value){}~Handle(){if(h)WinHttpCloseHandle(h);}operator HINTERNET()const{return h;}Handle(const Handle&)=delete;};
bool Token(const std::string& s){return s.size()==43&&s.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")==std::string::npos;}
}
Response Send(const Job& job){
 // Worker only. Never place bearer tokens or URLs in the game command buffer.
 if(job.path!="/healthz"&&job.path!="/v1/login/start"&&job.path!="/v1/login/poll"&&job.path!="/v1/me"&&job.path!="/v1/logout"&&job.path!="/v2/connection/authorize"&&job.path!="/v2/server/challenge"&&job.path!="/v1/server/redeem"&&job.path!="/v1/server/renew")return {};
 if((job.method!="GET"&&job.method!="POST")||job.body.size()>4096||(!job.bearer.empty()&&!Token(job.bearer)))return {};
 Handle session(WinHttpOpen(L"SaberTrials/Account-1",WINHTTP_ACCESS_TYPE_AUTOMATIC_PROXY,WINHTTP_NO_PROXY_NAME,WINHTTP_NO_PROXY_BYPASS,0));
 if(!session.h||!WinHttpSetTimeouts(session,5000,5000,5000,5000))return {};
 DWORD protocols=WINHTTP_FLAG_SECURE_PROTOCOL_TLS1_2|WINHTTP_FLAG_SECURE_PROTOCOL_TLS1_3;
 if(!WinHttpSetOption(session,WINHTTP_OPTION_SECURE_PROTOCOLS,&protocols,sizeof(protocols)))return {};
 Handle connection(WinHttpConnect(session,L"accounts-production-b56d.up.railway.app",INTERNET_DEFAULT_HTTPS_PORT,0));if(!connection.h)return {};
 Handle request(WinHttpOpenRequest(connection,Wide(job.method).c_str(),Wide(job.path).c_str(),nullptr,WINHTTP_NO_REFERER,WINHTTP_DEFAULT_ACCEPT_TYPES,WINHTTP_FLAG_SECURE));if(!request.h)return {};
 DWORD redirects=WINHTTP_OPTION_REDIRECT_POLICY_NEVER,auth=WINHTTP_AUTOLOGON_SECURITY_LEVEL_HIGH,disable=WINHTTP_DISABLE_COOKIES;
 if(!WinHttpSetOption(request,WINHTTP_OPTION_REDIRECT_POLICY,&redirects,sizeof(redirects))||!WinHttpSetOption(request,WINHTTP_OPTION_AUTOLOGON_POLICY,&auth,sizeof(auth))||!WinHttpSetOption(request,WINHTTP_OPTION_DISABLE_FEATURE,&disable,sizeof(disable)))return {};
 std::wstring headers=L"Accept: application/json\r\nContent-Type: application/json\r\n";
 if(!job.bearer.empty())headers+=L"Authorization: Bearer "+Wide(job.bearer)+L"\r\n";
 bool sent=WinHttpSendRequest(request,headers.c_str(),(DWORD)-1L,job.body.empty()?WINHTTP_NO_REQUEST_DATA:const_cast<char*>(job.body.data()),(DWORD)job.body.size(),(DWORD)job.body.size(),0)!=FALSE;
 SecureZeroMemory(&headers[0],headers.size()*sizeof(wchar_t));
 if(!sent||!WinHttpReceiveResponse(request,nullptr))return {};
 DWORD status=0,size=sizeof(status);
 if(!WinHttpQueryHeaders(request,WINHTTP_QUERY_STATUS_CODE|WINHTTP_QUERY_FLAG_NUMBER,WINHTTP_HEADER_NAME_BY_INDEX,&status,&size,WINHTTP_NO_HEADER_INDEX))return {};
 Response out;out.status=(int)status;char buffer[4096];DWORD count=0;
 const ULONGLONG began=GetTickCount64();
 while(WinHttpReadData(request,buffer,sizeof(buffer),&count)){
  if(!count)return out;
  if(out.body.size()+count>16384||GetTickCount64()-began>10000)return {};
  out.body.append(buffer,count);
 }
 return {};
}
bool Save(const std::string& path,const Saved& saved){
 if(path.empty()||(!saved.token.empty()&&(!Token(saved.token)||!std::isfinite(saved.expires))))return false;
 auto plain=nlohmann::json({{"token",saved.token},{"expires",saved.expires},{"logout",saved.logout}}).dump();
 DATA_BLOB input={(DWORD)plain.size(),(BYTE*)&plain[0]},encrypted={};
 bool ok=CryptProtectData(&input,L"Saber Trials player session",nullptr,nullptr,nullptr,CRYPTPROTECT_UI_FORBIDDEN,&encrypted)!=FALSE;
 SecureZeroMemory(&plain[0],plain.size());if(!ok)return false;
 st::Bytes bytes={'S','T','A','C',1};bytes.insert(bytes.end(),encrypted.pbData,encrypted.pbData+encrypted.cbData);LocalFree(encrypted.pbData);
 return st::PrivateWrite(path,bytes,true);
}
bool Load(const std::string& path,Saved& saved){
 saved={};st::Bytes bytes;
 if(!st::ReadFileBytes(path,bytes,8192)||bytes.size()<6||memcmp(bytes.data(),"STAC\1",5))return false;
 DATA_BLOB input={(DWORD)bytes.size()-5,bytes.data()+5},plain={};
 if(!CryptUnprotectData(&input,nullptr,nullptr,nullptr,nullptr,CRYPTPROTECT_UI_FORBIDDEN,&plain))return false;
 bool ok=false;
 try{
  auto j=nlohmann::json::parse(plain.pbData,plain.pbData+plain.cbData);
  auto token=j.at("token").get<std::string>();double expiry=j.at("expires").get<double>();bool logout=j.at("logout").get<bool>();
  if((token.empty()||Token(token))&&std::isfinite(expiry)){saved={token,expiry,logout};ok=true;}
 }catch(...){}
 SecureZeroMemory(plain.pbData,plain.cbData);LocalFree(plain.pbData);return ok;
}
std::string SessionPath(){
 wchar_t local[32768];DWORD n=GetEnvironmentVariableW(L"LOCALAPPDATA",local,32768);if(!n||n>=32768)return {};
 int len=WideCharToMultiByte(CP_UTF8,0,local,n,nullptr,0,nullptr,nullptr);if(len<=0)return {};
 std::string root(len,'\0');WideCharToMultiByte(CP_UTF8,0,local,n,&root[0],len,nullptr,nullptr);root+="/SaberTrialsAccounts";
 return st::PrivateDirectory(root)?root+"/session.bin":std::string();
}
bool Forget(const std::string& path){
 if(path.empty())return false;
 return DeleteFileW(Wide(path).c_str())||GetLastError()==ERROR_FILE_NOT_FOUND;
}
bool OpenBrowser(const std::string& url){return ValidBrowserUrl(url)&&(INT_PTR)ShellExecuteW(nullptr,L"open",Wide(url).c_str(),nullptr,nullptr,SW_SHOWNORMAL)>32;}
}
