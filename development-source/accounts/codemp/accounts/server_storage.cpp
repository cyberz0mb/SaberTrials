#include "server_storage.h"
#include "account.h"
#include "vendor/json.hpp"
#include "st_staff_types.h"
#ifdef _WIN32
#include <windows.h>
#include <wincrypt.h>
#else
#include "st_private_linux.h"
#include <sodium.h>
#include <cstring>
#endif
namespace staccount {
namespace {
bool Decode(const unsigned char*bytes,size_t size,ServerCredential&c){
 try{
  auto j=nlohmann::json::parse(bytes,bytes+size);
  ServerCredential value;value.id=j.at("server_id").get<std::string>();value.token=j.at("server_token").get<std::string>();
  if(value.id.empty()||value.id.size()>128||value.id.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.:-")!=std::string::npos||value.token.size()!=43||value.token.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")!=std::string::npos)return false;
  c=std::move(value);return true;
 }catch(...){return false;}
}
}
std::string ServerCredentialPath(int port){
 if(port<1||port>65535)return {};auto root=SessionPath();if(root.empty())return {};
 root.resize(root.find_last_of('/'));root+="/servers";if(!st::PrivateDirectory(root))return {};
 root+="/"+std::to_string(port);if(!st::PrivateDirectory(root))return {};return root+"/credential.bin";
}
bool ImportServerCredential(const std::string&input,const std::string&output){
 if(output.empty())return false;st::Bytes bytes;ServerCredential c;
 if(!st::ReadFileBytes(input,bytes,4096)||!Decode(bytes.data(),bytes.size(),c))return false;
#ifdef _WIN32
 DATA_BLOB plain={(DWORD)bytes.size(),bytes.data()},encrypted={};
 bool ok=CryptProtectData(&plain,L"Saber Trials server credential",nullptr,nullptr,nullptr,CRYPTPROTECT_UI_FORBIDDEN,&encrypted)!=FALSE;
 SecureZeroMemory(bytes.data(),bytes.size());if(!c.token.empty())SecureZeroMemory(&c.token[0],c.token.size());if(!ok)return false;
 bytes={'S','T','S','C',1};bytes.insert(bytes.end(),encrypted.pbData,encrypted.pbData+encrypted.cbData);LocalFree(encrypted.pbData);
 return st::PrivateWrite(output,bytes,true);
#else
 bool ok=st::PrivateFile(input)&&st::ProtectFile(output,"STSC",bytes,true);
 sodium_memzero(bytes.data(),bytes.size());sodium_memzero(&c.token[0],c.token.size());return ok;
#endif
}
bool LoadServerCredential(const std::string&path,ServerCredential&c){
#ifdef _WIN32
 c={};st::Bytes bytes;if(!st::ReadFileBytes(path,bytes,8192)||bytes.size()<6||memcmp(bytes.data(),"STSC\1",5))return false;
 DATA_BLOB encrypted={(DWORD)bytes.size()-5,bytes.data()+5},plain={};
 if(!CryptUnprotectData(&encrypted,nullptr,nullptr,nullptr,nullptr,CRYPTPROTECT_UI_FORBIDDEN,&plain))return false;
 bool ok=Decode(plain.pbData,plain.cbData,c);SecureZeroMemory(plain.pbData,plain.cbData);LocalFree(plain.pbData);return ok;
#else
 c={};st::Bytes plain;if(!st::UnprotectFile(path,"STSC",plain))return false;
 bool ok=Decode(plain.data(),plain.size(),c);sodium_memzero(plain.data(),plain.size());return ok;
#endif
}
}
