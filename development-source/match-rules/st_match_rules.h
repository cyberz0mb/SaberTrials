// Shared native Match Rules contract. No engine calls or executable preset text.
#ifndef ST_MATCH_RULES_H
#define ST_MATCH_RULES_H
#include <array>
#include <string>
#include <vector>
#include <sstream>
#include <cstdlib>
#include <climits>
#include <algorithm>
namespace stmatch {
enum Tab { Combat, Force, Health, Teams, Match, Server, TabCount };
enum Scope { Trials=1, Team=2, Duel=4, Capture=8, CustomForce=16, CustomWeapon=32 };
struct Rule { const char *cvar,*label,*choices,*help; int tab,initial,low,high,step,scope; bool restart; };
#define MR(n,l,c,h,t,d,lo,hi,s,f,r) {n,l,c,h,t,d,lo,hi,s,f,r}
static const Rule rules[]={
 MR("st_combatMode","Combat preset","0=Original JKA|1=Saber Trials","Trials preferences are saved while Original JKA is active.",Combat,1,0,1,1,0,true),
 MR("g_manualBlocking","Blocking","0=Automatic|2=Manual|1=Both","Automatic retains legacy Walk defense. Manual requires guard; physical blade clashes still occur.",Combat,1,0,2,1,0,true),
 MR("st_activeDefense","Enhanced defense","0=Off|1=On","Enables Trials guard, timed parries and counters.",Combat,1,0,1,1,Trials,true),
 MR("st_attackParry","Attack-timed parry","0=Off|1=On","Tap Attack at contact; requires Trials enhanced defense.",Combat,1,0,1,1,Trials,true),
 MR("st_attackParryWindow","Attack parry window (ms)","","A larger contact timing window is more forgiving. Requires Attack parry.",Combat,150,60,200,5,Trials,true),
 MR("st_parryRecovery","Faster parry recovery","0=Off|1=On","Use the existing Trials recovery behavior.",Combat,1,0,1,1,Trials,true),
 MR("g_directionalFeints","Single-saber feints","0=Off|1=On","Supports ordinary Blue, Yellow, Red, Green and Orange wind-ups, including crouched and airborne.",Combat,1,0,1,1,0,true),
 MR("st_masterModeActive","Master Mode","0=Off|1=On","Uses the configured fixed unblocked contact damage and stronger perfect-parry stagger.",Combat,0,0,1,1,Trials,true),
 MR("st_masterSaberDamage","Master contact damage","","Damage for qualifying unblocked saber contact in Master Mode.",Combat,50,10,150,1,Trials,true),
 MR("g_saberLocking","Saber locks","0=Off|1=On","Allow saber lock contests.",Combat,1,0,1,1,0,true),
 MR("g_privateDuel","Private challenges","0=Off|1=On","Allow players to issue private saber challenges in supported modes.",Combat,1,0,1,1,0,true),
 MR("st_forceModeActive","Force rules","0=Restricted|1=Full|2=Custom","Restricted allows Jump, Speed, Saber Attack and Saber Defense. Custom caps are below.",Force,0,0,2,1,0,true),
 MR("g_maxForceRank","Force mastery","","Maximum Force allocation rank, from 0 through Jedi Master (7).",Force,7,0,7,1,0,true),
 MR("g_forceBasedTeams","Light / Dark teams","0=Off|1=On","Retains the existing team-based Force alignment rule for Red and Blue.",Force,0,0,1,1,Team,true),
 MR("st_weaponsActive","Weapon rules","0=Sabers only|1=All weapons|2=Custom","Custom uses the weapon checkboxes below; melee and saber remain available.",Force,0,0,2,1,0,true),
 MR("st_spawnHealth","Starting health","","0 keeps normal mode/handicap health. A custom value overrides non-Siege spawn health.",Health,0,0,500,5,0,true),
 MR("st_spawnShield","Starting shields","","-1 keeps current combat/mode defaults. 0 gives no starting shields.",Health,-1,-1,500,5,0,true),
 MR("st_shields","Regenerating shields","0=Off|1=On","Trials shield regeneration; custom starting shields are independent.",Health,1,0,1,1,Trials,true),
 MR("st_shieldMax","Shield recharge maximum","","Maximum shields restored by regeneration.",Health,100,1,200,1,Trials,true),
 MR("st_shieldRegenDelay","Shield recharge delay (ms)","","Time without damage before shields begin recovering.",Health,5000,0,30000,250,Trials,true),
 MR("st_shieldRegenAmount","Shield recharge amount","","Shields restored per existing regeneration tick.",Health,2,1,10,1,Trials,true),
 MR("st_noFallDamage","Falling damage","0=Enabled|1=Disabled","Trials falling-damage preference; Original JKA retains its normal behavior.",Health,1,0,1,1,Trials,true),
 MR("st_forceSpeed","Free Force Speed","0=Off|1=On","Trials spawn grant. Custom Force caps remain authoritative.",Health,1,0,1,1,Trials,true),
 MR("st_fastForceRegen","Fast Force recovery","0=Off|1=On","Use the configured Trials recovery interval.",Health,1,0,1,1,Trials,true),
 MR("st_forceRegenInterval","Force recovery interval (ms)","","Lower intervals recover Force energy faster; requires fast recovery.",Health,100,50,1000,10,Trials,true),
 MR("g_tffaTeams","Number of teams","","TFFA supports two through eight teams.",Teams,2,2,8,1,Team,true),
 MR("st_matchTeamCap","Players per team","","0 allows all available slots; otherwise limits each team. Connection capacity is separate.",Teams,0,0,16,1,Team,true),
 MR("g_teamForceBalance","Balance team entry","0=Off|1=On","Reject entry that would worsen team imbalance.",Teams,1,0,1,1,Team,false),
 MR("st_allowTeamSwitch","Allow team switching","0=Off|1=On","Players can always leave for spectator; switching active teams can be disabled.",Teams,1,0,1,1,Team,false),
 MR("st_matchLockTeams","Lock team entry","0=Off|1=On","TFFA: lock new entries and team changes, including new bots.",Teams,0,0,1,1,Team,false),
 MR("g_teamAutoJoin","Automatic team join","0=Off|1=On","New players join an available team when other admission rules permit.",Teams,1,0,1,1,Team,false),
 MR("bot_minplayers","Automatic bot population","","0 disables filling. Uses normal mode-aware bot population behavior.",Teams,0,0,31,1,0,false),
 MR("st_botSkill","Default bot skill","","Skill for role bots; individual roster slots can override it.",Teams,4,1,5,1,0,false),
 MR("sv_maxclients","Connection slots","","Includes humans, bots and spectators. Leave spare slots for yourself and future additions.",Teams,16,2,32,1,0,true),
 MR("g_gametype","Game type","0=FFA|3=Duel|4=Power Duel|6=Team FFA|7=Siege|8=CTF","Choose a compatible map. Mode-specific controls update automatically.",Match,0,0,8,1,0,true),
 MR("fraglimit","Score limit","","0 is unlimited. Duel rounds always end after one kill; use best-of for the series.",Match,10,0,1000,5,0,true),
 MR("timelimit","Time limit (minutes)","","0 is unlimited.",Match,0,0,180,1,0,true),
 MR("capturelimit","Capture limit","","Flag captures required to win CTF.",Match,8,0,100,1,Capture,true),
 MR("g_doWarmup","Warm-up","0=Off|1=On","Enable the pre-match warm-up countdown.",Match,0,0,1,1,0,true),
 MR("g_warmup","Warm-up duration (seconds)","","Pre-match warm-up duration when enabled.",Match,20,5,120,5,0,true),
 MR("st_respawnDelay","Minimum respawn delay (ms)","","0 keeps normal respawn timing. Custom delay applies to non-Duel, non-Siege modes.",Match,0,0,30000,250,0,true),
 MR("g_forcerespawn","Force respawn (seconds)","","0 leaves respawning to players, subject to the minimum delay.",Match,60,0,120,1,0,true),
 MR("st_duelBestOf","Duel series","1=One round|3=Best of 3|5=Best of 5|7=Best of 7|9=Best of 9","Controls the existing Duel series.",Match,3,1,9,2,Duel,true),
 MR("g_autoMapCycle","Automatic map rotation","0=Off|1=On","Use the ordered rotation configured in this screen.",Match,0,0,1,1,0,true),
 MR("g_friendlyFire","Friendly fire","0=Off|1=On","Allow teammates to damage each other.",Combat,0,0,1,1,Team,false),
 MR("g_allowVote","Allowed vote mask","","Use the individual vote controls below. 0 disables all player votes.",Server,16383,0,16383,1,0,false),
 MR("st_voteCooldown","Vote cooldown (seconds)","","Minimum delay between a player's vote calls.",Server,60,0,3600,5,0,false),
 MR("st_voteMaxCalls","Vote calls per map","","Maximum vote calls per player on a map.",Server,3,0,100,1,0,false),
 MR("sv_allowDownload","Server downloads","0=Off|1=On","Allow the existing in-game download path.",Server,0,0,1,1,0,false),
 MR("sv_pure","Pure server","0=Off|1=On","Require matching server packages. Loose development content may need packaging first.",Server,0,0,1,1,0,true),
 MR("sv_minPing","Minimum ping","","0 disables the admission minimum.",Server,0,0,999,5,0,false),
 MR("sv_maxPing","Maximum ping","","0 disables the admission maximum.",Server,0,0,999,5,0,false),
 MR("sv_maxRate","Maximum client rate","","0 uses the engine's unlimited/default behavior.",Server,0,0,100000,1000,0,false),
 MR("sv_reconnectlimit","Reconnect delay (seconds)","","Minimum reconnect interval enforced by the engine.",Server,3,0,120,1,0,false),
 MR("ui_dedicated","Hosting process","0=Play and host|1=Dedicated LAN|2=Dedicated Internet","Dedicated hosting leaves the local player client. This setting applies when hosting a new match.",Server,0,0,2,1,0,true),
};
#undef MR
static const int RuleCount=sizeof(rules)/sizeof(rules[0]);
static const int ForceCount=18, WeaponCount=19, MaxBots=32;
// Leave room for quotes and the command prefix in the native 1024-byte buffer.
static const int RotationLimit=960;
static const char* const forceNames[]={"Heal","Jump","Speed","Push","Pull","Mind Trick","Grip","Lightning","Rage","Protect","Absorb","Team Heal","Team Energize","Drain","Sight","Saber Attack","Saber Defense","Saber Throw"};
static const char* const weaponNames[]={"None","Stun baton","Melee","Lightsaber","Pistol","Blaster","Disruptor","Bowcaster","Repeater","DEMP2","Flechette","Rocket launcher","Thermal","Trip mine","Detpack","Concussion","Old pistol","Emplaced gun","Turret"};
static const char* const roleNames[]={"Automatic","Duelist","Sentinel","Berserker","Trickster","Defender","Flag Catcher","Saber Master"};
static const char* const roleTokens[]={"auto","duelist","sentinel","berserker","trickster","defender","flagcatcher","sabermaster"};
inline int find(const std::string& name) { for(int i=0;i<RuleCount;++i)if(name==rules[i].cvar)return i;return -1; }
inline bool integer(const std::string& text,int& out) {
 if(text.empty()||text.size()>11)return false;
 size_t n=text[0]=='-'?1:0;if(n==text.size())return false;
 long long v=0;for(size_t i=n;i<text.size();++i){if(text[i]<'0'||text[i]>'9')return false;v=v*10+text[i]-'0';if(v>2147483648LL)return false;}
 if(n)v=-v;if(v<INT_MIN||v>INT_MAX)return false;out=(int)v;return true;
}
inline bool valid(int id,int value) {
 if(id<0||id>=RuleCount)return false;const auto& r=rules[id];if(value<r.low||value>r.high)return false;
 if(!*r.choices)return true;std::istringstream stream(r.choices);std::string entry;
 while(std::getline(stream,entry,'|')){int n;if(integer(entry.substr(0,entry.find('=')),n)&&n==value)return true;}return false;
}
inline std::string label(int id,int value) {
 if(id<0||id>=RuleCount)return "";std::istringstream stream(rules[id].choices);std::string entry;
 while(std::getline(stream,entry,'|')){auto eq=entry.find('=');int n;if(integer(entry.substr(0,eq),n)&&n==value)return entry.substr(eq+1);}return std::to_string(value);
}
struct Bot {int slot=0,team=0,skill=4,role=0;std::string model;};
struct Preset {
 std::array<int,RuleCount> values;
 std::array<int,ForceCount> force;
 int weaponDisable=0;
 std::string map="mp/ffa3",rotation,hostname="Saber Trials Server";
 std::vector<Bot> bots;
 Preset(){for(int i=0;i<RuleCount;++i)values[i]=rules[i].initial;force.fill(3);}
 int get(const char* name)const {int i=find(name);return i<0?0:values[i];}
 void set(const char* name,int value){int i=find(name);if(i>=0)values[i]=value;}
};
inline bool mapName(const std::string& s) {
 if(s.empty()||s.size()>60||s[0]=='/'||s.find("..")!=std::string::npos)return false;
 for(char c:s)if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-'||c=='/'))return false;return true;
}
inline bool safeText(const std::string& s,size_t max) {
 if(s.size()>max)return false;for(unsigned char c:s)if(c<32||c==127||c=='"'||c=='\\'||c==';')return false;return true;
}
inline bool filename(const std::string& s) {
 if(s.empty()||s.size()>40)return false;std::string lower;
 for(char c:s){if(!((c>='A'&&c<='Z')||(c>='a'&&c<='z')||(c>='0'&&c<='9')||c=='-'||c=='_'))return false;lower+=c>='A'&&c<='Z'?char(c-'A'+'a'):c;}
 if(lower=="con"||lower=="prn"||lower=="aux"||lower=="nul")return false;
 if(lower.size()==4&&(lower.substr(0,3)=="com"||lower.substr(0,3)=="lpt")&&lower[3]>='1'&&lower[3]<='9')return false;
 return true;
}
inline bool roleAllowed(int type,int role) {
 if(role==0)return true;if(type==3)return role==7;if(type==4)return false;if(type==8)return role==5||role==6;
 if(type==6)return role>=1&&role<=3;return type==0&&role>=1&&role<=4;
}
inline bool visible(const Rule& rule,const Preset& p) {
 int type=p.get("g_gametype");if((rule.scope&Team)&&type!=6&&type!=7&&type!=8)return false;
 if(std::string(rule.cvar)=="fraglimit"&&(type==3||type==4))return false;
 if((rule.scope&Duel)&&type!=3)return false;if((rule.scope&Capture)&&type!=8)return false;return true;
}
inline std::string inactive(const Rule& rule,const Preset& p) {
 if((rule.scope&Trials)&&p.get("st_combatMode")!=1)return "Requires Saber Trials combat; preference retained.";
 std::string n=rule.cvar;
 if(p.get("g_gametype")==7&&(n=="st_forceModeActive"||n=="st_weaponsActive"||n=="g_maxForceRank"))return "Siege classes define Force and weapons; preference retained for other modes.";
 if(p.get("g_gametype")==7&&(n=="st_spawnHealth"||n=="st_spawnShield"))return "Siege classes define starting health and armor.";
 if(p.get("g_gametype")==7&&(n=="st_matchTeamCap"||n=="st_allowTeamSwitch"))return "This rule applies to TFFA and CTF; Siege admission is unchanged.";
 if((n=="st_attackParry"||n=="st_attackParryWindow")&&!p.get("st_activeDefense"))return "Requires enhanced defense; preference retained.";
 if(n=="st_attackParryWindow"&&!p.get("st_attackParry"))return "Requires Attack-timed parry; preference retained.";
 if(n=="st_masterSaberDamage"&&!p.get("st_masterModeActive"))return "Requires Master Mode; preference retained.";
 if((n=="st_shieldMax"||n=="st_shieldRegenDelay"||n=="st_shieldRegenAmount")&&!p.get("st_shields"))return "Requires regenerating shields; preference retained.";
 if(n=="st_forceRegenInterval"&&!p.get("st_fastForceRegen"))return "Requires fast Force recovery; preference retained.";
 if(n=="st_respawnDelay"&&(p.get("g_gametype")==3||p.get("g_gametype")==4||p.get("g_gametype")==7))return "Normal respawn timing applies in Duel, Power Duel and Siege; preference retained.";
 if(n=="g_tffaTeams"&&p.get("g_gametype")!=6)return "Extra teams are available in TFFA.";
 if(n=="st_matchLockTeams"&&p.get("g_gametype")!=6)return "Team locks currently apply to TFFA.";
 return "";
}
inline bool validate(const Preset& p,std::string& error) {
 for(int i=0;i<RuleCount;++i)if(!valid(i,p.values[i])){error=std::string("Invalid ")+rules[i].label;return false;}
 if(p.get("g_gametype")==4&&p.get("sv_maxclients")<3){error="Power Duel requires at least three connection slots.";return false;}
 for(int n:p.force)if(n<0||n>3){error="Force caps must be 0 through 3.";return false;}
 if(p.weaponDisable<0||p.weaponDisable>=(1<<WeaponCount)||(p.weaponDisable&(1<<2))||(p.weaponDisable&(1<<3))){error="Melee and saber must remain available.";return false;}
 if(!mapName(p.map)||!safeText(p.hostname,100)){error="Invalid map or server name.";return false;}
 if(p.rotation.size()>RotationLimit){error="Map rotation exceeds the safe 960-character limit.";return false;}
 for(unsigned char c:p.rotation)if(c<32||c==127){error="Separate rotation maps with ordinary spaces.";return false;}
 std::istringstream maps(p.rotation);std::string map;int count=0;while(maps>>map){if(!mapName(map)||++count>32){error="Invalid map rotation (maximum 32 maps).";return false;}}
 int min=p.get("sv_minPing"),max=p.get("sv_maxPing");if(max&&max<min){error="Maximum ping must be at least minimum ping.";return false;}
 if(p.bots.size()>31){error="Reserve a connection slot for the host or future players.";return false;}
 const int type=p.get("g_gametype"),teamCount=type==6?p.get("g_tffaTeams"):type==8?2:0,cap=p.get("st_matchTeamCap");
 if(p.get("bot_minplayers")>=p.get("sv_maxclients")){error="Automatic bot population must leave an open connection slot.";return false;}
 if(teamCount&&cap&&p.get("bot_minplayers")>teamCount*cap){error="Automatic bot population exceeds available team capacity.";return false;}
 if(teamCount&&cap&&(int)p.bots.size()>teamCount*cap){error="Bot roster exceeds available team capacity.";return false;}
 std::array<bool,MaxBots> seen={};std::array<int,10> teamBots={};
 for(const auto& b:p.bots){
  const bool activeTeam=b.team==0||((teamCount||type==7)&&(b.team==1||b.team==2))||(type==6&&b.team>=4&&b.team<=teamCount+1);
  if(b.slot<0||b.slot>=MaxBots||seen[b.slot]||!activeTeam||b.skill<1||b.skill>5||!roleAllowed(type,b.role)||!safeText(b.model,64)||b.model.empty()){
   error="Invalid or mode-incompatible bot slot.";return false;}seen[b.slot]=true;
  if(teamCount&&cap&&b.team&&++teamBots[b.team]>cap){error="Bot roster exceeds a team's player cap.";return false;}
 }
 if((int)p.bots.size()>=p.get("sv_maxclients")){error="Increase connection slots to leave room beyond the bot roster.";return false;}
 error.clear();return true;
}
inline std::string hex(const std::string& s){const char* h="0123456789abcdef";std::string r;for(unsigned char c:s){r+=h[c>>4];r+=h[c&15];}return r.empty()?"-":r;}
inline bool unhex(const std::string& s,std::string& out){out.clear();if(s=="-")return true;if(s.size()%2||s.size()>4096)return false;for(size_t i=0;i<s.size();i+=2){int n=0;for(int j=0;j<2;++j){char c=s[i+j];int v=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:-1;if(v<0)return false;n=n*16+v;}out+=char(n);}return true;}
inline std::string encode(const Preset& p) {
 std::ostringstream out;out<<"ST_MATCH_PRESET 1\n";
 for(int i=0;i<RuleCount;++i)out<<"rule "<<rules[i].cvar<<" "<<p.values[i]<<"\n";
 for(int i=0;i<ForceCount;++i)out<<"force "<<i<<" "<<p.force[i]<<"\n";
 out<<"weapons "<<p.weaponDisable<<"\nmap "<<p.map<<"\nrotation "<<hex(p.rotation)<<"\nhost "<<hex(p.hostname)<<"\n";
 for(const auto& b:p.bots)out<<"bot "<<b.slot<<" "<<b.team<<" "<<b.skill<<" "<<b.role<<" "<<hex(b.model)<<"\n";
 out<<"end\n";return out.str();
}
inline bool decode(const std::string& input,Preset& destination,std::string& error) {
 if(input.size()>32768){error="Preset is too large.";return false;}Preset p;std::istringstream in(input);std::string line;
 if(!std::getline(in,line)||line!="ST_MATCH_PRESET 1"){error="Unsupported preset format.";return false;}
 std::array<bool,RuleCount> seen={};std::array<bool,ForceCount> forces={};int extras=0;bool end=false;
 while(std::getline(in,line)){
  std::istringstream row(line);std::string op,a,b,c,d,e,junk;row>>op;
  if(op=="end"){if(row>>junk)break;end=true;break;}
  if(op=="rule"){int value;row>>a>>b;int id=find(a);if(id<0||seen[id]||!integer(b,value)||!valid(id,value)||(row>>junk))break;p.values[id]=value;seen[id]=true;}
  else if(op=="force"){int id,value;row>>a>>b;if(!integer(a,id)||!integer(b,value)||id<0||id>=ForceCount||forces[id]||value<0||value>3||(row>>junk))break;p.force[id]=value;forces[id]=true;}
  else if(op=="bot"){Bot bot;row>>a>>b>>c>>d>>e;if(!integer(a,bot.slot)||!integer(b,bot.team)||!integer(c,bot.skill)||!integer(d,bot.role)||!unhex(e,bot.model)||(row>>junk))break;p.bots.push_back(bot);}
  else if(op=="weapons"||op=="map"||op=="rotation"||op=="host"){
   int bit=op=="weapons"?1:op=="map"?2:op=="rotation"?4:8;row>>a;if((extras&bit)||a.empty()||(row>>junk))break;extras|=bit;
   if(op=="weapons"){if(!integer(a,p.weaponDisable))break;}else if(op=="map")p.map=a;else if(!unhex(a,op=="host"?p.hostname:p.rotation))break;
  }else break;
 }
 if(!end||extras!=15||std::find(seen.begin(),seen.end(),false)!=seen.end()||std::find(forces.begin(),forces.end(),false)!=forces.end()){
  error="Incomplete, duplicate or unrecognized preset data.";return false;}
 while(std::getline(in,line))if(!line.empty()){error="Unexpected data after preset end.";return false;}
 if(!validate(p,error))return false;destination=p;return true;
}
} // namespace stmatch
#endif
