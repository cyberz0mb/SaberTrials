#include <iostream>
#include <stdexcept>
#include <filesystem>
#include <fstream>
#include <sys/stat.h>
#include <unistd.h>
#include "st_private_linux.h"
#include "st_staff_identity.h"
#include "st_staff_store.h"
#include "server_storage.h"
#define CHECK(x) do { if(!(x)) throw std::runtime_error(#x); } while(0)
int main(){try{
 namespace fs=std::filesystem;
 const auto root=fs::temp_directory_path()/("sabertrials-linux-"+std::to_string(getpid()));
 CHECK(st::PrivateDirectory(root.string()));
 const auto file=(root/"secret").string();st::Bytes raw(64,42),loaded;
 CHECK(st::ProtectFile(file,"STTS",raw,false));
 CHECK(!st::ProtectFile(file,"STTS",st::Bytes(64,10),false));
 CHECK(st::UnprotectFile(file,"STTS",loaded)&&loaded==raw);
 struct stat info{};CHECK(!stat(file.c_str(),&info)&&(info.st_mode&0777)==0600);
 CHECK(!stat((file+".protect").c_str(),&info)&&(info.st_mode&0777)==0600);
 CHECK(st::ReadFileBytes(file,loaded));CHECK(loaded!=raw);
 loaded.back()^=1;CHECK(st::PrivateWrite(file,loaded,true));
 CHECK(!st::UnprotectFile(file,"STTS",loaded)&&loaded.empty());
 CHECK(st::ProtectFile(file,"STTS",raw,true));
 CHECK(!chmod((file+".protect").c_str(),0644));CHECK(!st::UnprotectFile(file,"STTS",loaded));
 CHECK(!chmod((file+".protect").c_str(),0600));
 CHECK(!chmod(file.c_str(),0644));CHECK(!st::UnprotectFile(file,"STTS",loaded));
 CHECK(!chmod(file.c_str(),0600));
 const auto link=(root/"link").string();CHECK(!symlink(file.c_str(),link.c_str()));
 CHECK(!st::ReadFileBytes(link,loaded));CHECK(!st::PrivateWrite(link,raw,true));
 const auto dirlink=(root/"dirlink").string();CHECK(!symlink(root.c_str(),dirlink.c_str()));
 CHECK(!st::PrivateWrite(dirlink+"/escape",raw,false));
 CHECK(!st::PrivateDirectory(dirlink));
 const auto identity=(root/"staff.key").string();st::Identity first,second;
 CHECK(first.LoadOrCreate(identity,true));CHECK(second.LoadOrCreate(identity,false));
 CHECK(first.PublicId()==second.PublicId());CHECK(st::Identity::Verify(first.PublicId(),raw,second.Sign(raw)));
 CHECK(st::ValidLabel("Jedi \xF0\x9F\x8C\x9F"));CHECK(!st::ValidLabel("bad\xC0\xAF"));CHECK(!st::ValidLabel("bad\xC2\x85"));
 CHECK(!st::ValidLabel(std::string(49,'a')));
 const auto input=(root/"input.json").string(),output=(root/"credential.bin").string();
 const std::string token(43,'s');std::string json="{\"server_id\":\"temple\",\"server_token\":\""+token+"\"}";
 CHECK(st::PrivateWrite(input,st::Bytes(json.begin(),json.end()),false));
 CHECK(staccount::ImportServerCredential(input,output));staccount::ServerCredential c;
 CHECK(staccount::LoadServerCredential(output,c)&&c.id=="temple"&&c.token==token);
 CHECK(st::ReadFileBytes(output,loaded));CHECK(std::string(loaded.begin(),loaded.end()).find(token)==std::string::npos);
 CHECK(!chmod(output.c_str(),0644));CHECK(!staccount::LoadServerCredential(output,c)&&c.token.empty());
 const auto dbfile=(root/"accounts.db").string();{st::Store db;CHECK(db.Open(dbfile));CHECK(db.BootstrapOwner(first.PublicId(),"Owner"));}
 CHECK(!stat(dbfile.c_str(),&info)&&(info.st_mode&0777)==0600);
 fs::remove_all(root);
 std::cout<<"Linux private storage, identity, credential and permission checks passed.\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
