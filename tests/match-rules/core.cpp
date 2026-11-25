// Native tests call the production contract directly. No engine or game launch.
#include "st_match_rules.h"
#include <functional>
#include <iostream>
#include <set>

namespace {
int checks=0, failures=0;
void check(bool value,const std::string& name) {
 ++checks;
 if(!value) {++failures;std::cerr<<"FAIL: "<<name<<"\n";}
}
bool same(const stmatch::Preset& a,const stmatch::Preset& b) {
 if(a.values!=b.values||a.force!=b.force||a.weaponDisable!=b.weaponDisable||
    a.map!=b.map||a.rotation!=b.rotation||a.hostname!=b.hostname||a.bots.size()!=b.bots.size())return false;
 for(size_t i=0;i<a.bots.size();++i) {
  const auto& x=a.bots[i];const auto& y=b.bots[i];
  if(x.slot!=y.slot||x.team!=y.team||x.skill!=y.skill||x.role!=y.role||x.model!=y.model)return false;
 }
 return true;
}
stmatch::Bot bot(int slot,int team=0,int role=0) {
 stmatch::Bot b;b.slot=slot;b.team=team;b.role=role;b.model="kyle/default";return b;
}
stmatch::Preset sentinel() {
 stmatch::Preset p;p.set("g_gametype",6);p.set("g_tffaTeams",4);p.set("sv_maxclients",12);
 p.force[2]=1;p.weaponDisable=1<<4;p.map="mp/ffa1";p.rotation="mp/ffa1 mp/ffa2";
 p.hostname="Destination remains intact";p.bots.push_back(bot(8,4,2));return p;
}
void rejects(const std::string& wire,const std::string& name) {
 auto destination=sentinel();const auto before=destination;std::string error="stale";
 check(!stmatch::decode(wire,destination,error),name+" rejected");
 check(same(destination,before),name+" leaves destination untouched");
 check(!error.empty(),name+" supplies a reason");
}
void invalid(const stmatch::Preset& p,const std::string& name) {
 std::string error;check(!stmatch::validate(p,error),name+" rejected by validation");
 check(!error.empty(),name+" validation supplies a reason");
 rejects(stmatch::encode(p),name+" preset");
}
void valid(const stmatch::Preset& p,const std::string& name) {
 std::string error;check(stmatch::validate(p,error),name+" accepted: "+error);
}
std::string replaced(std::string s,const std::string& from,const std::string& to) {
 const auto at=s.find(from);check(at!=std::string::npos,"test fixture contains replacement target");
 if(at!=std::string::npos)s.replace(at,from.size(),to);return s;
}
std::string beforeEnd(std::string s,const std::string& extra) {
 const auto at=s.rfind("end\n");check(at!=std::string::npos,"test fixture has end record");
 s.insert(at,extra);return s;
}

void catalog() {
 stmatch::Preset defaults;valid(defaults,"normal host defaults");
 check(defaults.get("st_spawnHealth")==0&&defaults.get("st_spawnShield")==-1,
       "defaults preserve native mode-specific spawn health and shields");
 check(defaults.get("st_forceModeActive")==0&&defaults.get("st_weaponsActive")==0,
       "default host uses Restricted Force and saber weapons");
 check(defaults.get("bot_minplayers")==0&&defaults.bots.empty(),"default host does not add bots");
 check(stmatch::valid(stmatch::find("st_shieldMax"),1)&&stmatch::valid(stmatch::find("st_shieldMax"),200)&&
       !stmatch::valid(stmatch::find("st_shieldMax"),0)&&!stmatch::valid(stmatch::find("st_shieldMax"),201),
       "shield recharge maximum respects the production gameplay bounds");
 check(stmatch::valid(stmatch::find("st_shieldRegenAmount"),1)&&stmatch::valid(stmatch::find("st_shieldRegenAmount"),10)&&
       !stmatch::valid(stmatch::find("st_shieldRegenAmount"),0)&&!stmatch::valid(stmatch::find("st_shieldRegenAmount"),11),
       "shield recharge amount respects the production gameplay bounds");
 check(defaults.get("g_forcerespawn")==60,"normal host preserves existing forced-respawn default");
 std::set<std::string> names;
 for(int i=0;i<stmatch::RuleCount;++i) {
  const auto& r=stmatch::rules[i];
  check(names.insert(r.cvar).second,std::string("unique rule ")+r.cvar);
  check(r.tab>=0&&r.tab<stmatch::TabCount,std::string("tab exists for ")+r.cvar);
  check(stmatch::valid(i,defaults.values[i]),std::string("default can apply for ")+r.cvar);
  check(!stmatch::valid(i,r.low-1)&&!stmatch::valid(i,r.high+1),std::string("range enforced for ")+r.cvar);
 }
 const int types[]={0,3,4,6,8};
 for(int t=-1;t<=9;++t)check(stmatch::valid(stmatch::find("g_gametype"),t)==
     (t==0||t==3||t==4||t==6||t==7||t==8),"supported game types only");
 for(int n=0;n<=10;++n)check(stmatch::valid(stmatch::find("st_duelBestOf"),n)==
     (n==1||n==3||n==5||n==7||n==9),"Duel series allows odd supported round counts");
 check(!stmatch::valid(-1,0)&&!stmatch::valid(stmatch::RuleCount,0),"invalid rule identifiers rejected");
 check(stmatch::find("rconpassword")==-1&&stmatch::find("g_password")==-1&&stmatch::find("password")==-1,
       "secrets are outside serializable catalog");

 for(int type:types) {
  auto p=defaults;p.set("g_gametype",type);
  check(stmatch::visible(stmatch::rules[stmatch::find("g_tffaTeams")],p)==(type==6||type==7||type==8),"teams visible in team modes");
  check(stmatch::visible(stmatch::rules[stmatch::find("capturelimit")],p)==(type==8),"capture limit visible only in CTF");
  check(stmatch::visible(stmatch::rules[stmatch::find("st_duelBestOf")],p)==(type==3),"series visible only in Duel");
  valid(p,"mode default retains dormant preferences");
 }
 auto p=defaults;p.set("st_combatMode",0);
 check(!stmatch::inactive(stmatch::rules[stmatch::find("st_attackParry")],p).empty(),"Original explains retained Trials preference");
 check(p.get("st_attackParry")==1,"Original keeps Trials preference");
 p=defaults;p.set("st_activeDefense",0);
 check(!stmatch::inactive(stmatch::rules[stmatch::find("st_attackParryWindow")],p).empty(),"missing defense explains inactive parry window");
 p=defaults;p.set("st_attackParry",0);
 check(!stmatch::inactive(stmatch::rules[stmatch::find("st_attackParryWindow")],p).empty(),"missing attack parry explains inactive window");
 p=defaults;p.set("st_shields",0);
 check(!stmatch::inactive(stmatch::rules[stmatch::find("st_shieldMax")],p).empty(),"missing shields explains recharge preference");
 p=defaults;p.set("st_fastForceRegen",0);
 check(!stmatch::inactive(stmatch::rules[stmatch::find("st_forceRegenInterval")],p).empty(),"missing recovery explains interval preference");
 for(int type:{3,4,7}) {
  p=defaults;p.set("g_gametype",type);p.set("st_respawnDelay",1500);
  check(!stmatch::inactive(stmatch::rules[stmatch::find("st_respawnDelay")],p).empty(),
        "Duel, Power Duel and Siege explain ignored minimum-respawn preference");
  check(p.get("st_respawnDelay")==1500,"unsupported mode retains minimum-respawn preference");
 }
 for(int type:{0,6,8}) {
  p=defaults;p.set("g_gametype",type);
  check(stmatch::inactive(stmatch::rules[stmatch::find("st_respawnDelay")],p).empty(),
        "normal respawning modes permit the minimum-respawn preference");
 }

 struct IntegerCase {const char* text;bool accepted;int value;};
 const IntegerCase cases[]={
  {"0",true,0},{"-0",true,0},{"2147483647",true,INT_MAX},{"-2147483648",true,INT_MIN},
  {"00000000001",true,1},{"2147483648",false,0},{"-2147483649",false,0},
  {"99999999999",false,0},{"999999999999999999999",false,0},{"",false,0},
  {"-",false,0},{"+1",false,0},{" 1",false,0},{"1 ",false,0},{"1.0",false,0},
  {"1e2",false,0},{"0x1",false,0},{"1;quit",false,0},{"1\n",false,0},
 };
 for(const auto& c:cases) {int out=713;bool accepted=stmatch::integer(c.text,out);
  check(accepted==c.accepted,std::string("strict integer ")+c.text);
  check(c.accepted?out==c.value:out==713,"strict integer result or untouched failure");}
 int out=713;check(!stmatch::integer(std::string("1\0",2),out)&&out==713,"integer embedded NUL rejected atomically");
}

void roundtrip() {
 stmatch::Preset p;
 for(int i=0;i<stmatch::RuleCount;++i)p.values[i]=stmatch::rules[i].high;
 for(int i=0;i<stmatch::ForceCount;++i)p.force[i]=i%4;
 p.weaponDisable=(1<<4)|(1<<8)|(1<<13);p.map="mp/ctf4";
 p.rotation="mp/ctf4 mp/ctf2 mp/ctf4";p.hostname="^2Complete host roster";
 p.bots.push_back(bot(0,1,5));p.bots.back().model="jan/red";p.bots.back().skill=1;
 p.bots.push_back(bot(31,2,6));p.bots.back().model="kyle/blue";p.bots.back().skill=5;
 valid(p,"complete nondefault host configuration");
 auto destination=sentinel();std::string error="stale";const auto encoded=stmatch::encode(p);
 check(stmatch::decode(encoded,destination,error),"complete configuration parses");
 check(same(destination,p),"all numeric fields, caps, strings and ordered roster survive roundtrip");
 check(error.empty(),"successful parse clears old error");
 check(encoded.find("password")==std::string::npos,"preset contains no password field");
 const auto rotationAt=encoded.find("rotation ");
 check(rotationAt!=std::string::npos&&encoded.find(p.rotation)==std::string::npos,
       "rotation serializes as data rather than executable command text");
 stmatch::Preset empty;empty.hostname="";empty.rotation="";
 const auto emptyWire=stmatch::encode(empty);check(emptyWire.find("rotation -\nhost -\n")!=std::string::npos,"empty text has unambiguous encoding");
 check(stmatch::decode(emptyWire,destination,error)&&same(empty,destination),"empty nonsecret text roundtrip");
 check(stmatch::decode(emptyWire+"\n\n",destination,error),"empty lines after end are harmless");
 check(stmatch::decode(emptyWire.substr(0,emptyWire.size()-1),destination,error),"complete final end without newline accepted");
 std::string raw;for(int i=0;i<256;++i)raw+=static_cast<char>(i);
 std::string decoded;check(stmatch::unhex(stmatch::hex(raw),decoded)&&decoded==raw,"byte data encoding is reversible");
 for(const auto* bad:{"x","00x0","AB","--","0","gg"})check(!stmatch::unhex(bad,decoded),"invalid byte encoding rejected");
}

void malformed() {
 const auto wire=stmatch::encode(stmatch::Preset());
 const auto endAt=wire.rfind("end\n");
 for(size_t n=0;n<endAt+3;++n)rejects(wire.substr(0,n),"truncated byte "+std::to_string(n));
 for(size_t start=wire.find('\n')+1;start<endAt;) {
  const auto next=wire.find('\n',start)+1;
  rejects(wire.substr(0,start)+wire.substr(next),"missing record "+std::to_string(start));start=next;
 }
 rejects(replaced(wire,"ST_MATCH_PRESET 1","ST_MATCH_PRESET 2"),"unknown format version");
 rejects(replaced(wire,"ST_MATCH_PRESET 1","ST_MATCH_PRESET 01"),"noncanonical format version");
 rejects(beforeEnd(wire,"rule st_combatMode 1\n"),"duplicate rule");
 rejects(beforeEnd(wire,"force 0 3\n"),"duplicate Force cap");
 rejects(beforeEnd(wire,"weapons 0\n"),"duplicate weapons record");
 rejects(beforeEnd(wire,"map mp/ffa1\n"),"duplicate map record");
 rejects(beforeEnd(wire,"rotation -\n"),"duplicate rotation record");
 rejects(beforeEnd(wire,"host -\n"),"duplicate hostname record");
 rejects(beforeEnd(wire,"rule sv_cheats 1\n"),"unknown rule");
 rejects(beforeEnd(wire,"rule g_password 12345\n"),"secret field");
 rejects(beforeEnd(wire,"exec evil.cfg\n"),"executable command record");
 rejects(beforeEnd(wire,"bot 0 0 4 0 6b796c65\nbot 0 0 4 0 6a616e\n"),"duplicate bot slot");
 rejects(replaced(wire,"rule st_combatMode 1\n","rule st_combatMode 1 trailing\n"),"rule trailing field");
 rejects(replaced(wire,"force 0 3\n","force 0\n"),"missing Force value");
 rejects(replaced(wire,"force 0 3\n","force 18 3\n"),"Force index out of range");
 rejects(replaced(wire,"force 0 3\n","force 0 4\n"),"Force value out of range");
 rejects(replaced(wire,"rule st_combatMode 1\n","rule st_combatMode 2147483648\n"),"integer overflow");
 rejects(replaced(wire,"rule st_combatMode 1\n","rule st_combatMode 1;quit\n"),"numeric command injection");
 rejects(replaced(wire,"end\n","end extra\n"),"end trailing field");
 rejects(wire+"quit\n","command after end");
 rejects(wire+" \n","nonempty trailing data");
 rejects(wire+std::string(1,'\0'),"trailing NUL");
 rejects(std::string(32769,'x'),"oversized file");
 for(const auto* field:{"map","rotation","host","weapons"}) {
  const std::string token=std::string(field)+" ";const auto start=wire.find(token),stop=wire.find('\n',start);
  rejects(wire.substr(0,start)+field+wire.substr(stop),std::string("missing ")+field+" value");
 }
 rejects(replaced(wire,"host "+stmatch::hex("Saber Trials Server"),"host 0x"),"malformed hex hostname");
 rejects(beforeEnd(wire,"bot 0 0 4 0\n"),"missing bot model");
 rejects(beforeEnd(wire,"bot 0 0 4 0 6b796c65 extra\n"),"bot trailing field");
 rejects(beforeEnd(wire,"bot 2147483648 0 4 0 6b796c65\n"),"bot integer overflow");
}

void validation() {
 {stmatch::Preset siege;siege.set("g_gametype",7);valid(siege,"native Siege host mode preserved");}
 {stmatch::Preset siege;siege.set("g_gametype",7);siege.bots={bot(0),bot(1)};siege.bots[0].team=1;siege.bots[1].team=2;valid(siege,"native Siege explicit bot teams preserved");}
 {stmatch::Preset power;power.set("g_gametype",4);power.set("sv_maxclients",2);invalid(power,"Power Duel needs three connection slots");power.set("sv_maxclients",3);valid(power,"Power Duel accepts three connection slots");}
 const int types[]={0,3,4,6,8};
 for(int type:types)for(int role=-1;role<=8;++role) {
  auto p=stmatch::Preset();p.set("g_gametype",type);p.bots.push_back(bot(0,0,role));
  const bool allowed=role==0||(type==0&&role>=1&&role<=4)||(type==3&&role==7)||
    (type==6&&role>=1&&role<=3)||(type==8&&(role==5||role==6));
  if(allowed)valid(p,"compatible bot role");else invalid(p,"mode-incompatible bot role");
 }
 for(int type:types)for(int team=-1;team<=10;++team) {
  auto p=stmatch::Preset();p.set("g_gametype",type);p.set("g_tffaTeams",4);p.bots.push_back(bot(0,team));
  bool allowed=team==0||((type==6||type==8)&&(team==1||team==2))||(type==6&&(team==4||team==5));
  if(allowed)valid(p,"active team selection");else invalid(p,"inactive team selection");
 }
 for(int teams=2;teams<=8;++teams) {
  auto p=stmatch::Preset();p.set("g_gametype",6);p.set("g_tffaTeams",teams);
  p.bots.push_back(bot(0,teams==2?2:teams+1));valid(p,"highest configured TFFA team available");
  if(teams<8){p.bots[0].team=teams+2;invalid(p,"next unconfigured TFFA team unavailable");}
 }
 auto p=stmatch::Preset();p.set("g_gametype",6);p.set("st_matchTeamCap",1);
 p.bots={bot(0,1),bot(1,1)};invalid(p,"explicit team exceeds cap");
 p.bots={bot(0,1),bot(1,2)};valid(p,"explicit teams at cap");
 p.bots={bot(0),bot(1),bot(2)};invalid(p,"automatic roster exceeds aggregate team capacity");
 p.set("st_matchTeamCap",0);valid(p,"zero team cap leaves connection capacity authoritative");
 p.set("g_gametype",0);p.set("st_matchTeamCap",1);valid(p,"nonteam mode retains inactive team-cap preference");
 p=stmatch::Preset();p.set("sv_maxclients",2);p.set("bot_minplayers",1);valid(p,"automatic population leaves an open connection");
 p.set("bot_minplayers",2);invalid(p,"automatic population consumes final connection");
 p.set("bot_minplayers",3);invalid(p,"automatic population exceeds connection count");
 p=stmatch::Preset();p.set("g_gametype",6);p.set("g_tffaTeams",4);p.set("st_matchTeamCap",2);p.set("bot_minplayers",8);
 valid(p,"TFFA automatic population fits all active teams");p.set("bot_minplayers",9);invalid(p,"TFFA automatic population exceeds aggregate team cap");
 p=stmatch::Preset();p.set("g_gametype",8);p.set("g_tffaTeams",8);p.set("st_matchTeamCap",3);p.set("bot_minplayers",6);
 valid(p,"CTF automatic population uses two teams despite dormant TFFA count");
 p.set("bot_minplayers",7);invalid(p,"CTF automatic population exceeds two-team cap");
 p.set("st_matchTeamCap",0);valid(p,"zero team cap permits population below connection count");
 p.set("g_gametype",0);p.set("st_matchTeamCap",1);valid(p,"nonteam automatic population ignores dormant team cap");
 p=stmatch::Preset();p.set("sv_maxclients",2);p.bots={bot(0)};valid(p,"one connection reserved beyond roster");
 p.bots.push_back(bot(1));invalid(p,"full bot roster leaves no open connection");
 p=stmatch::Preset();p.set("sv_maxclients",32);for(int i=0;i<31;++i)p.bots.push_back(bot(i));valid(p,"31 bots retain final open connection");
 p.bots.push_back(bot(31));invalid(p,"32 bots consume final connection");
 p=stmatch::Preset();p.bots={bot(-1)};invalid(p,"negative bot slot");
 p.bots[0].slot=32;invalid(p,"bot slot outside roster");
 p.bots={bot(0)};p.bots[0].skill=0;invalid(p,"bot skill below supported range");
 p.bots[0].skill=6;invalid(p,"bot skill above supported range");
 p=stmatch::Preset();p.set("sv_minPing",200);p.set("sv_maxPing",100);invalid(p,"maximum ping below minimum");
 p.set("sv_maxPing",200);valid(p,"equal ping bounds");p.set("sv_maxPing",0);valid(p,"disabled maximum ping with minimum");
 p=stmatch::Preset();p.force[0]=-1;invalid(p,"negative Force cap");p.force[0]=4;invalid(p,"excessive Force cap");
 p=stmatch::Preset();for(int mask:{-1,1<<stmatch::WeaponCount,1<<2,1<<3}) {p.weaponDisable=mask;invalid(p,"invalid custom weapon availability");}

 const std::vector<std::string> injected={";quit","\"quit","\\quit","\nquit","\rquit","\tquit",std::string("\0quit",5),std::string(1,127)};
 for(const auto& attack:injected) {
  p=stmatch::Preset();p.hostname="Server"+attack;invalid(p,"unsafe hostname bytes");
  p=stmatch::Preset();p.bots={bot(0)};p.bots[0].model="kyle"+attack;invalid(p,"unsafe bot-model bytes");
  p=stmatch::Preset();p.map="mp/ffa3"+attack;invalid(p,"unsafe map bytes");
  p=stmatch::Preset();p.rotation="mp/ffa3"+attack;invalid(p,"unsafe rotation bytes");
 }
 for(const auto* path:{"../evil","/mp/ffa3","mp/../evil","mp/ffa3.cfg","mp:ffa3","mp/ffa3 quit"}) {
  p=stmatch::Preset();p.map=path;invalid(p,"invalid or traversal map name");
 }
 for(const auto* name:{"","../evil","..","a/b","a\\b","a.cfg","a:b","a b","a;quit","a\nquit","a\"b"})
  check(!stmatch::filename(name),"unsafe preset filename rejected");
 check(!stmatch::filename(std::string("safe\0evil",9)),"NUL preset filename rejected");
 check(!stmatch::filename(std::string(41,'a')),"overlong preset filename rejected");
 for(const auto* name:{"CON","con","Con","PRN","prn","AUX","aux","NUL","nul","COM1","com9","LPT1","lpt9"})
  check(!stmatch::filename(name),std::string("reserved Windows device filename rejected: ")+name);
 for(int i=1;i<=9;++i) {
  check(!stmatch::filename("COM"+std::to_string(i)),"numbered COM device rejected");
  check(!stmatch::filename("LPT"+std::to_string(i)),"numbered LPT device rejected");
 }
 for(const auto* name:{"a","My_Rules-2026","standard","CONSOLE","CON_rules","COM0","COM10","LPT0","LPT10"})
  check(stmatch::filename(name),"plain preset filename accepted");
 p=stmatch::Preset();p.hostname=std::string(101,'a');invalid(p,"overlong server name");
 p=stmatch::Preset();p.map=std::string(61,'a');invalid(p,"overlong map name");
 p=stmatch::Preset();p.bots={bot(0)};p.bots[0].model=std::string(65,'a');invalid(p,"overlong bot model");
 p.bots[0].model="";invalid(p,"empty bot model");
 p=stmatch::Preset();for(int i=0;i<32;++i){if(i)p.rotation+=' ';p.rotation+="mp/ffa3";}valid(p,"32 ordered maps accepted");
 p.rotation+=" mp/ffa3";invalid(p,"33 map rotation rejected");
 p=stmatch::Preset();p.rotation=std::string(1025,' ');invalid(p,"overlong rotation rejected");
 p=stmatch::Preset();p.rotation=std::string(961,' ');invalid(p,"rotation exceeding safe console transport rejected");
 p.rotation=std::string(960,' ');valid(p,"maximum safe console rotation payload accepted");
 check(std::string("st_match_text rotation \"").size()+p.rotation.size()+2<1024,"rotation command fits the native 1024-byte command buffer");
 p=stmatch::Preset();p.rotation="  mp/ffa3   mp/ffa1  ";valid(p,"ordinary spaces separate ordered maps");
}
} // namespace

int main(int argc,char** argv) {
 const std::string group=argc>1?argv[1]:"all";
 if(group=="all"||group=="catalog")catalog();
 if(group=="all"||group=="roundtrip")roundtrip();
 if(group=="all"||group=="malformed")malformed();
 if(group=="all"||group=="validation")validation();
 if(!checks){std::cerr<<"Unknown test group: "<<group<<"\n";return 2;}
 std::cout<<"Match Rules "<<group<<": "<<checks<<" checks, "<<failures<<" failures\n";
 return failures?1:0;
}
