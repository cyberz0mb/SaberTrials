#include "st_private_linux.h"
#include <sodium.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <limits.h>
namespace st {
namespace {
struct FD { int n; explicit FD(int value):n(value){} ~FD(){if(n>=0)close(n);} FD(const FD&)=delete; };
// Resolve every parent without following symlinks, including intermediate components.
int Parent(const std::string& path,std::string& leaf){
 if(path.empty()||path.find('\0')!=std::string::npos||path.size()>=PATH_MAX)return -1;
 int fd=open(path[0]=='/'?"/":".",O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);if(fd<0)return -1;
 size_t begin=path[0]=='/'?1:0;
 while(true){size_t end=path.find('/',begin);std::string part=path.substr(begin,end==std::string::npos?end:end-begin);
  if(part.empty()||part==".."||part=="."){close(fd);return -1;}
  if(end==std::string::npos){leaf=part;return fd;}
  int next=openat(fd,part.c_str(),O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);close(fd);if(next<0)return -1;
  fd=next;begin=end+1;
 }
}
bool Owned(int fd,bool directory,bool privateMode){struct stat s{};return !fstat(fd,&s)&&s.st_uid==geteuid()&&(directory?S_ISDIR(s.st_mode):S_ISREG(s.st_mode))&&(!privateMode||!(s.st_mode&077));}
bool Key(const std::string& path,Bytes& key,bool create){
 const auto name=path+".protect";
 std::string leaf;FD parent(Parent(name,leaf));if(parent.n<0)return false;struct stat s{};
 if(fstatat(parent.n,leaf.c_str(),&s,AT_SYMLINK_NOFOLLOW)){
  if(errno!=ENOENT||!create)return false;
  Bytes value(32);if(!Random(value.data(),value.size()))return false;
  bool ok=PrivateWrite(name,value,false);sodium_memzero(value.data(),value.size());
  // Another initializer may have won the exclusive creation race.
  if(!ok&&fstatat(parent.n,leaf.c_str(),&s,AT_SYMLINK_NOFOLLOW))return false;
 }
 return PrivateFile(name)&&ReadFileBytes(name,key,32)&&key.size()==32;
}
}
bool Random(void* p,size_t n){if(sodium_init()<0)return false;randombytes_buf(p,n);return true;}
bool PrivateFile(const std::string& path){std::string leaf;FD parent(Parent(path,leaf));if(parent.n<0)return false;FD f(openat(parent.n,leaf.c_str(),O_RDONLY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK));return f.n>=0&&Owned(f.n,false,true);}
bool PrivateDirectory(const std::string& path){
 std::string leaf;FD parent(Parent(path,leaf));if(parent.n<0)return false;
 if(mkdirat(parent.n,leaf.c_str(),0700)&&errno!=EEXIST)return false;
 FD dir(openat(parent.n,leaf.c_str(),O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW));
 return dir.n>=0&&Owned(dir.n,true,false)&&fchmod(dir.n,0700)==0;
}
bool ReadFileBytes(const std::string& path,Bytes& out,size_t limit){
 out.clear();std::string leaf;FD parent(Parent(path,leaf));if(parent.n<0)return false;
 FD file(openat(parent.n,leaf.c_str(),O_RDONLY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK));struct stat s{};
 if(file.n<0||fstat(file.n,&s)||!S_ISREG(s.st_mode)||s.st_size<0||(uint64_t)s.st_size>limit)return false;
 out.resize((size_t)s.st_size);size_t at=0;
 while(at<out.size()){ssize_t n=read(file.n,out.data()+at,out.size()-at);if(n<0&&errno==EINTR)continue;if(n<=0){out.clear();return false;}at+=(size_t)n;}
 unsigned char extra;ssize_t n;do{n=read(file.n,&extra,1);}while(n<0&&errno==EINTR);
 if(n!=0){out.clear();return false;}return true;
}
bool PrivateWrite(const std::string& path,const Bytes& bytes,bool replace){
 std::string leaf;FD parent(Parent(path,leaf));if(parent.n<0||!Owned(parent.n,true,false))return false;
 struct stat mode{};if(fstat(parent.n,&mode)||(mode.st_mode&022))return false;
 if(!fstatat(parent.n,leaf.c_str(),&mode,AT_SYMLINK_NOFOLLOW)){if(!replace||!S_ISREG(mode.st_mode)||mode.st_uid!=geteuid())return false;}else if(errno!=ENOENT)return false;
 unsigned char random[16];if(!Random(random,16))return false;const auto tmp=leaf+"."+Hex(random,16)+".tmp";
 FD f(openat(parent.n,tmp.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC|O_NOFOLLOW,0600));if(f.n<0)return false;
 bool ok=true;size_t at=0;
 while(at<bytes.size()){ssize_t n=write(f.n,bytes.data()+at,bytes.size()-at);if(n<0&&errno==EINTR)continue;if(n<=0){ok=false;break;}at+=(size_t)n;}
 ok=ok&&fsync(f.n)==0;
 if(ok){if(replace)ok=renameat(parent.n,tmp.c_str(),parent.n,leaf.c_str())==0;else ok=linkat(parent.n,tmp.c_str(),parent.n,leaf.c_str(),0)==0;}
 unlinkat(parent.n,tmp.c_str(),0);if(ok)ok=fsync(parent.n)==0;return ok;
}
bool ProtectFile(const std::string& path,const char magic[5],const Bytes& plain,bool replace){
 if(plain.size()>16384)return false;Bytes key;if(!Key(path,key,true))return false;
 Bytes data(5+24+plain.size()+crypto_aead_xchacha20poly1305_ietf_ABYTES);std::memcpy(data.data(),magic,4);data[4]=2;
 bool ok=Random(data.data()+5,24)&&crypto_aead_xchacha20poly1305_ietf_encrypt(data.data()+29,nullptr,plain.data(),plain.size(),data.data(),5,nullptr,data.data()+5,key.data())==0;
 sodium_memzero(key.data(),key.size());return ok&&PrivateWrite(path,data,replace);
}
bool UnprotectFile(const std::string& path,const char magic[5],Bytes& plain){
 plain.clear();Bytes key,data;
 if(!PrivateFile(path)||!ReadFileBytes(path,data,16429)||data.size()<45||std::memcmp(data.data(),magic,4)||data[4]!=2||!Key(path,key,false))return false;
 plain.resize(data.size()-45);bool ok=crypto_aead_xchacha20poly1305_ietf_decrypt(plain.data(),nullptr,nullptr,data.data()+29,data.size()-29,data.data(),5,data.data()+5,key.data())==0;
 sodium_memzero(key.data(),key.size());if(!ok){sodium_memzero(plain.data(),plain.size());plain.clear();}return ok;
}
std::string LinuxStateRoot(const char* component){
 const char* overridePath=std::getenv("SABERTRIALS_STATE_DIR");const char* home=std::getenv("HOME");
 std::string root=overridePath?overridePath:home?std::string(home)+"/.sabertrials":std::string();
 if(root.empty()||root[0]!='/'||!PrivateDirectory(root))return {};
 root+="/";root+=component;return PrivateDirectory(root)?root:std::string();
}
}
