#include "server_storage.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#include <sys/stat.h>
#define GetCurrentProcessId getpid
#endif
#include <stdexcept>
#define CHECK(x) do{if(!(x))throw std::runtime_error(#x);}while(0)
int main(){try{
 auto root=std::filesystem::temp_directory_path()/("st-server-storage-"+std::to_string(GetCurrentProcessId()));std::filesystem::create_directory(root);
 auto input=(root/"credential.json").string(),output=(root/"credential.bin").string();const std::string secret(43,'s');
 {std::ofstream f(input);f<<"{\"server_id\":\"temple\",\"server_token\":\""<<secret<<"\"}";}
#ifndef _WIN32
 CHECK(chmod(input.c_str(),0600)==0);
#endif
 CHECK(staccount::ImportServerCredential(input,output));staccount::ServerCredential c;
 CHECK(staccount::LoadServerCredential(output,c));CHECK(c.id=="temple"&&c.token==secret);
 std::ifstream in(output,std::ios::binary);std::string bytes((std::istreambuf_iterator<char>(in)),{});in.close();CHECK(bytes.find(secret)==std::string::npos);
 bytes.back()^=1;{std::ofstream f(output,std::ios::binary|std::ios::trunc);f<<bytes;}
 CHECK(!staccount::LoadServerCredential(output,c));CHECK(c.token.empty());
 {std::ofstream f(input);f<<"{\"server_id\":\"bad;quit\",\"server_token\":\""<<secret<<"\"}";}
 CHECK(!staccount::ImportServerCredential(input,output));std::filesystem::remove_all(root);
 std::cout<<"Private server import, protected storage and corrupted-file rejection passed.\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
