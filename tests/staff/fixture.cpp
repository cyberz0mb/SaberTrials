// Test fixture creator. Never included in the game distribution or installation.
#include "st_staff_wire.h"
#include "check.h"
#include <fstream>
int main(int argc,char** argv){try{
 CHECK(argc==2);std::string root=argv[1];CHECK(st::PrivateDirectory(root));
 std::ofstream manifest(root+"/public.txt");CHECK(manifest.good());
 std::string ids[3];
 for(int i=0;i<3;i++){
  std::string p=root+"/client"+std::to_string(i);CHECK(st::PrivateDirectory(p));p+="/SaberTrialsStaff";CHECK(st::PrivateDirectory(p));p+="/client";CHECK(st::PrivateDirectory(p));
  st::Identity key;CHECK(key.LoadOrCreate(p+"/identity.key",true));ids[i]=key.PublicId();manifest<<"client"<<i<<" "<<ids[i]<<"\n";
 }
 std::string p=root+"/server";CHECK(st::PrivateDirectory(p));p+="/SaberTrialsStaff";CHECK(st::PrivateDirectory(p));p+="/servers";CHECK(st::PrivateDirectory(p));p+="/27977";CHECK(st::PrivateDirectory(p));
 st::Identity key;CHECK(key.LoadOrCreate(p+"/server.key",true));manifest<<"server "<<key.PublicId()<<"\n";
 st::Store db;CHECK(db.Open(p+"/accounts.db"));CHECK(db.BootstrapOwner(ids[0],"Fixture Owner"));CHECK(db.Change(ids[0],ids[1],st::Role::Admin,"Fixture Admin",true));CHECK(db.Change(ids[0],ids[2],st::Role::Moderator,"Fixture Moderator",true));
 return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
