#include <iostream>
#include <cstdlib>
#include "st_controls_core.h"
#include "st_controls_api.h"
static void check(bool ok,const char* message){if(!ok){std::cerr<<message<<"\n";std::exit(1);}}
int main(){
 stc::Snapshot original;original.binds[1]="+attack";original.binds[2]="say \"good fight\"; vstr my_alias";original.binds[3]="+attack";original.vars["sensitivity"]="5";
 stc::Draft d;d.open(original);check(!d.dirty(),"open changed settings");
 check(!d.move(1,2,stc::Cancel),"conflict silently replaced");check(d.value==original,"cancel changed commands");
 check(d.move(1,2,stc::Swap),"swap rejected");check(d.value.binds[1]==original.binds[2]&&d.value.binds[2]=="+attack","swap lost exact command");check(d.value.binds[3]=="+attack","extra assignment lost");d.cancel();check(d.value==original,"cancel failed");
 check(d.move(1,2,stc::Replace),"replace failed");check(!d.value.binds.count(1)&&d.value.binds[2]=="+attack","replace kept wrong assignments");d.cancel();
 stc::Snapshot live=original;live.binds[1]="+use";d.value.binds[1]="+altattack";check(!d.canApply(live),"concurrent changed key overwritten");live=original;live.binds[9]="unrelated";check(d.canApply(live),"unrelated change blocked apply");
 auto keyName=[](int key){return std::string("K")+std::to_string(key);};auto keyCode=[](const std::string& key){return key.size()>1&&key[0]=='K'?std::atoi(key.c_str()+1):-1;};
 original.binds[4]=std::string(12000,'x')+"\\\";custom";original.vars["my_alias"]="say \"hello\";echo C:\\mods";
 original.vars["international_alias"]=u8"say caf\u00e9 \u5251";
 check(!STC_EditableCommand(original.vars["international_alias"].c_str())&&!STC_EditableCommand(original.binds[4].c_str())&&STC_EditableCommand("say hello; vstr alias"),"text edit safety guard failed");
 const auto cfg=stc::serialize(original,keyName);stc::Snapshot parsed;std::string error;
 check(stc::parse(cfg,keyCode,parsed,error),error.c_str());check(parsed==original,"cfg roundtrip lost bytes");
 check(stc::parse(R"(bind K9 "say C:\mods\new\file")",keyCode,parsed,error),"legacy cfg rejected");
 check(parsed.binds[9]==R"(say C:\mods\new\file)","legacy cfg backslashes corrupted");
 auto prior=parsed;check(!stc::parse(cfg+"\nexec autoexec.cfg\n",keyCode,parsed,error),"executable cfg accepted");check(parsed==prior,"rejected import partially changed draft");
 check(!stc::parse("bind K1 \"+attack\"; quit",keyCode,parsed,error),"semicolon injection accepted");
 check(!stc::parse("seta sensitivity \"unterminated",keyCode,parsed,error),"bad quotes accepted");
 check(!stc::parse(std::string("bind K1 x\0quit",14),keyCode,parsed,error),"NUL accepted");
 bool replaces=false;check(stc::parse("unbind K1",keyCode,parsed,error,&replaces)&&!replaces&&parsed.binds.count(1)&&parsed.binds[1].empty(),"partial unbind lost");
 check(stc::validName("Duel setup.cfg")&&stc::validName("Ranked_2"),"valid profile refused");
 for(const auto& name:{"../bad","bad;quit","server.cfg","autoexec","CON","LPT1.cfg","C:\\bad","","foo.cfg.cfg"})check(!stc::validName(name),"unsafe filename accepted");
 check(stc::validVar("my_alias")&&!stc::validVar("rconPassword")&&!stc::validVar("sv_maxclients")&&!stc::validVar("st_accountToken"),"personal variable policy wrong");
 std::cout<<"PASS: exact/custom/extra binds, conflict/cancel/concurrency, 12K and Unicode snapshot roundtrip, legacy backslashes, partial unbind, rejection, filenames and personal settings\n";
}
