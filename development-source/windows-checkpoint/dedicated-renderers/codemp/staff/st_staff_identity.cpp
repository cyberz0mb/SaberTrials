#include "st_staff_identity.h"
#include <windows.h>
#include <wincrypt.h>
#include <bcrypt.h>
#include <sddl.h>
#include <sodium.h>
#include <algorithm>
#include <cstring>
namespace st {
const char* RoleName(Role r) { switch(r){case Role::Owner:return "Owner";case Role::Admin:return "Admin";case Role::Moderator:return "Moderator";default:return "None";} }
bool Random(void* out,size_t n) { return n<=0xffffffff && BCryptGenRandom(NULL,(PUCHAR)out,(ULONG)n,BCRYPT_USE_SYSTEM_PREFERRED_RNG)==0; }
std::string Hex(const unsigned char* p,size_t n) { static const char h[]="0123456789abcdef"; std::string s; s.reserve(n*2); for(size_t i=0;i<n;i++){s+=h[p[i]>>4];s+=h[p[i]&15];} return s; }
bool Unhex(const std::string& s,Bytes& out,size_t expected) { out.clear(); if(s.size()%2 || s.size()>4096 || (expected && s.size()!=expected*2))return false; for(size_t i=0;i<s.size();i+=2){int v=0;for(int j=0;j<2;j++){char c=s[i+j]; int x=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:-1;if(x<0){out.clear();return false;}v=v*16+x;}out.push_back((unsigned char)v);}return true; }
bool ValidId(const std::string& s){Bytes b;return Unhex(s,b,32);}
bool ValidLabel(const std::string& s){
 if(s.empty()||s.size()>192)return false;
 for(size_t i=0;i<s.size();i++){unsigned char c=s[i];if(c<32||c==127||c=='^')return false;}
 wchar_t w[193];int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.data(),(int)s.size(),w,193);
 if(n<1||n>48)return false;
 for(int i=0;i<n;i++)if(w[i]>=0x80&&w[i]<=0x9f)return false;
 return true;
}
static std::wstring Wide(const std::string& s){int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.c_str(),-1,NULL,0);if(n<=0)return {};std::wstring w(n,L'\0');MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.c_str(),-1,&w[0],n);w.resize(n-1);return w;}
class PrivateSecurity {
 PSECURITY_DESCRIPTOR descriptor_=NULL;
public:
 SECURITY_ATTRIBUTES attributes={sizeof(SECURITY_ATTRIBUTES),NULL,FALSE};
 PrivateSecurity(){
  HANDLE token=NULL;DWORD n=0;if(!OpenProcessToken(GetCurrentProcess(),TOKEN_QUERY,&token))return;
  GetTokenInformation(token,TokenUser,NULL,0,&n);Bytes data(n);
  if(!GetTokenInformation(token,TokenUser,data.data(),n,&n)){CloseHandle(token);return;} CloseHandle(token);
  LPWSTR sid=NULL;if(!ConvertSidToStringSidW(((TOKEN_USER*)data.data())->User.Sid,&sid))return;
  std::wstring s=L"D:P(A;OICI;FA;;;";s+=sid;s+=L")";LocalFree(sid);
  if(ConvertStringSecurityDescriptorToSecurityDescriptorW(s.c_str(),SDDL_REVISION_1,&descriptor_,NULL))attributes.lpSecurityDescriptor=descriptor_;
 }
 ~PrivateSecurity(){if(descriptor_)LocalFree(descriptor_);}
 bool good()const{return descriptor_!=NULL;}
 bool Apply(const std::wstring& p){return good()&&SetFileSecurityW(p.c_str(),DACL_SECURITY_INFORMATION|PROTECTED_DACL_SECURITY_INFORMATION,descriptor_);}
};
bool PrivateDirectory(const std::string& path){
 PrivateSecurity sec;auto p=Wide(path);if(!sec.good()||p.empty())return false;
 DWORD attr=GetFileAttributesW(p.c_str());
 if(attr==INVALID_FILE_ATTRIBUTES){if(GetLastError()!=ERROR_FILE_NOT_FOUND&&GetLastError()!=ERROR_PATH_NOT_FOUND)return false;if(!CreateDirectoryW(p.c_str(),&sec.attributes))return false;}
 else if(!(attr&FILE_ATTRIBUTE_DIRECTORY)||(attr&FILE_ATTRIBUTE_REPARSE_POINT))return false;
 return sec.Apply(p);
}
bool ReadFileBytes(const std::string& path,Bytes& bytes,size_t limit){
 bytes.clear();auto p=Wide(path);HANDLE h=CreateFileW(p.c_str(),GENERIC_READ,FILE_SHARE_READ,NULL,OPEN_EXISTING,FILE_FLAG_OPEN_REPARSE_POINT,NULL);if(h==INVALID_HANDLE_VALUE)return false;
 BY_HANDLE_FILE_INFORMATION info;LARGE_INTEGER size;bool ok=GetFileInformationByHandle(h,&info)&&!(info.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT)&&GetFileSizeEx(h,&size)&&size.QuadPart>=0&&(uint64_t)size.QuadPart<=limit;
 if(ok){bytes.resize((size_t)size.QuadPart);DWORD read=0;ok=ReadFile(h,bytes.data(),(DWORD)bytes.size(),&read,NULL)&&read==bytes.size();}CloseHandle(h);if(!ok)bytes.clear();return ok;
}
bool PrivateWrite(const std::string& path,const Bytes& data,bool replace){
 PrivateSecurity sec;auto p=Wide(path);if(!sec.good()||p.empty())return false;
 unsigned char random[16];if(!Random(random,sizeof(random)))return false;auto tmp=p+L"."+Wide(Hex(random,16))+L".tmp";
 HANDLE h=CreateFileW(tmp.c_str(),GENERIC_WRITE,0,&sec.attributes,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,NULL);if(h==INVALID_HANDLE_VALUE)return false;
 DWORD written=0;bool ok=WriteFile(h,data.data(),(DWORD)data.size(),&written,NULL)&&written==data.size()&&FlushFileBuffers(h);CloseHandle(h);
 if(ok)ok=MoveFileExW(tmp.c_str(),p.c_str(),MOVEFILE_WRITE_THROUGH|(replace?MOVEFILE_REPLACE_EXISTING:0))!=FALSE;
 if(!ok)DeleteFileW(tmp.c_str());return ok;
}
Identity::Identity(){sodium_init();std::memset(key_,0,sizeof(key_));}
Identity::~Identity(){Clear();}
void Identity::Clear(){sodium_memzero(key_,sizeof(key_));loaded_=false;}
bool Identity::Save(const std::string& path,bool replace){
 DATA_BLOB in={(DWORD)sizeof(key_),key_},out={};if(!CryptProtectData(&in,L"Saber Trials staff identity",NULL,NULL,NULL,CRYPTPROTECT_UI_FORBIDDEN,&out))return false;
 Bytes data={'S','T','I','D',1};data.insert(data.end(),out.pbData,out.pbData+out.cbData);sodium_memzero(out.pbData,out.cbData);LocalFree(out.pbData);
 return PrivateWrite(path,data,replace);
}
bool Identity::LoadOrCreate(const std::string& path,bool create){
 Clear();if(sodium_init()<0)return false;auto p=Wide(path);DWORD attr=GetFileAttributesW(p.c_str());
 if(attr==INVALID_FILE_ATTRIBUTES){if(!create||GetLastError()!=ERROR_FILE_NOT_FOUND)return false;unsigned char seed[32];if(!Random(seed,32))return false;unsigned char pk[32];crypto_sign_seed_keypair(pk,key_,seed);sodium_memzero(seed,32);loaded_=Save(path,false);if(!loaded_)Clear();return loaded_;}
 if(attr&(FILE_ATTRIBUTE_REPARSE_POINT|FILE_ATTRIBUTE_DIRECTORY))return false;
 PrivateSecurity sec;if(!sec.Apply(p))return false;
 Bytes data;if(!ReadFileBytes(path,data)||data.size()<6||std::memcmp(data.data(),"STID\1",5))return false;
 DATA_BLOB in={(DWORD)(data.size()-5),data.data()+5},out={};if(!CryptUnprotectData(&in,NULL,NULL,NULL,NULL,CRYPTPROTECT_UI_FORBIDDEN,&out))return false;
 bool ok=out.cbData==64;if(ok){unsigned char pk[32],sk[64];crypto_sign_seed_keypair(pk,sk,out.pbData);ok=sodium_memcmp(sk,out.pbData,64)==0;sodium_memzero(sk,64);if(ok)std::memcpy(key_,out.pbData,64);}
 sodium_memzero(out.pbData,out.cbData);LocalFree(out.pbData);loaded_=ok;return ok;
}
std::string Identity::PublicId()const {return loaded_?Hex(key_+32,32):std::string();}
Bytes Identity::Sign(const Bytes& bytes)const {if(!loaded_)return {};Bytes sig(64);if(crypto_sign_detached(sig.data(),NULL,bytes.data(),bytes.size(),key_)!=0)return {};return sig;}
bool Identity::Verify(const std::string& id,const Bytes& bytes,const Bytes& sig){Bytes pk;if(!Unhex(id,pk,32)||sig.size()!=64)return false;return crypto_sign_verify_detached(sig.data(),bytes.data(),bytes.size(),pk.data())==0;}
bool Identity::ExportProtected(const std::string& path,const std::string& pass)const {
 if(!loaded_||pass.size()<12||pass.size()>1024)return false;
 Bytes out={'S','T','B','K',1};out.resize(5+16+24);if(!Random(out.data()+5,40))return false;
 unsigned char key[32];if(crypto_pwhash(key,32,pass.data(),pass.size(),out.data()+5,crypto_pwhash_OPSLIMIT_MODERATE,crypto_pwhash_MEMLIMIT_MODERATE,crypto_pwhash_ALG_ARGON2ID13)!=0)return false;
 out.resize(45+64+crypto_aead_xchacha20poly1305_ietf_ABYTES);
 int rc=crypto_aead_xchacha20poly1305_ietf_encrypt(out.data()+45,NULL,key_,64,out.data(),45,NULL,out.data()+21,key);sodium_memzero(key,32);
 return rc==0&&PrivateWrite(path,out,false);
}
bool Identity::ImportProtected(const std::string& path,const std::string& pass,const std::string& destination){
 Bytes in;if(pass.size()>1024||!ReadFileBytes(path,in)||in.size()!=125||std::memcmp(in.data(),"STBK\1",5))return false;
 unsigned char key[32],plain[64];if(crypto_pwhash(key,32,pass.data(),pass.size(),in.data()+5,crypto_pwhash_OPSLIMIT_MODERATE,crypto_pwhash_MEMLIMIT_MODERATE,crypto_pwhash_ALG_ARGON2ID13)!=0)return false;
 bool ok=crypto_aead_xchacha20poly1305_ietf_decrypt(plain,NULL,NULL,in.data()+45,80,in.data(),45,in.data()+21,key)==0;sodium_memzero(key,32);
 if(ok){unsigned char pk[32],sk[64];crypto_sign_seed_keypair(pk,sk,plain);ok=sodium_memcmp(sk,plain,64)==0;sodium_memzero(sk,64);}
 if(ok){Identity temp;std::memcpy(temp.key_,plain,64);temp.loaded_=true;ok=temp.Save(destination,true);if(ok){std::memcpy(key_,plain,64);loaded_=true;}}
 sodium_memzero(plain,64);return ok;
}
}
