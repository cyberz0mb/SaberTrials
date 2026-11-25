// Exercise the actual console/frame adapter against a small deterministic engine.
#include "st_match_server_policy.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <set>
#ifdef NDEBUG
#error Match Rules tests require active assertions.
#endif
enum qboolean {qfalse,qtrue};
typedef int team_t;typedef int forcePowers_t;typedef int fileHandle_t;
enum {MAX_CLIENTS=32,NUM_FORCE_POWERS=18,MAX_INFO_STRING=1024,MAX_QPATH=64};
enum {TEAM_FREE=0,TEAM_RED=1,TEAM_BLUE=2,TEAM_SPECTATOR=3,GT_FFA=0,GT_DUEL=3,GT_POWERDUEL=4,GT_TEAM=6,GT_SIEGE=7,GT_CTF=8};
enum {CON_DISCONNECTED,CON_CONNECTING,CON_CONNECTED};
enum {SVF_BOT=1,CVAR_ARCHIVE=1,CVAR_NORESTART=2,CVAR_ROM=4,FS_READ=0,EXEC_APPEND=2,ST_COMBAT_DEFENSE=0,CS_ST_COMBAT_CONTROLS=100};
enum {STAT_MAX_HEALTH,STAT_HEALTH,STAT_ARMOR,STAT_WEAPONS,WP_SABER=3};
struct vmCvar_t {int integer=0;};
struct gclient_t {
 struct {int connected=0,maxHealth=100,stBotRole=0;} pers;
 struct {int sessionTeam=TEAM_SPECTATOR;} sess;
 struct {int stats[8]={0},weapon=WP_SABER;struct {int forcePowerLevel[18]={0},forcePowerBaseLevel[18]={0},forcePowersActive=0,forcePowersKnown=0;} fd;} ps;
};
struct gentity_t {gclient_t *client=nullptr;struct{int number=0;}s;struct{int svFlags=0;}r;int health=100;};
struct {int maxclients=8,gametype=GT_TEAM,time=1000,framenum=3; qboolean stTeamsLocked=qfalse,restarted=qfalse;int stLockedTeam[32]={0};gclient_t clients[32];struct{int num=2;}bots;} level;
gentity_t g_entities[32];
vmCvar_t st_forceModeActive,st_weaponsActive,g_duelWeaponDisable,g_autoMapCycle,fraglimit;
static const char *va(const char *format,...) {static char ring[32][4096];static int cursor=0;char *out=ring[(cursor++)%32];va_list args;va_start(args,format);vsnprintf(out,4096,format,args);va_end(args);return out;}
static int Com_Clampi(int low,int high,int value){return std::max(low,std::min(high,value));}
static void Q_strncpyz(char *out,const char *in,size_t size){if(size){size_t length=std::min(size-1,std::strlen(in));std::memcpy(out,in,length);out[length]=0;}}
static int Q_stricmp(const char *a,const char *b){return std::string(a).compare(b);}
static int Q_stricmpn(const char *a,const char *b,int n){return std::strncmp(a,b,n);}
struct FakeTrap {
 std::map<std::string,std::string> cvars;
 std::vector<std::string> args,commands,prints;
 std::vector<int> dropped,spawned;
 std::set<std::string> maps={"maps/mp/ffa3.bsp","maps/mp/ffa1.bsp"};
 void Cvar_VariableStringBuffer(const char *name,char *out,size_t size){Q_strncpyz(out,cvars[name].c_str(),size);}
 int Cvar_VariableIntegerValue(const char *name){return atoi(cvars[name].c_str());}
 void Cvar_Set(const char *name,const char *value){cvars[name]=value;}
 void Cvar_Register(vmCvar_t *,const char *name,const char *value,int){if(!cvars.count(name))cvars[name]=value;}
 void Cvar_Update(vmCvar_t *value){if(value==&g_duelWeaponDisable)value->integer=Cvar_VariableIntegerValue("g_duelWeaponDisable");if(value==&fraglimit)value->integer=Cvar_VariableIntegerValue("fraglimit");}
 int FS_Open(const char *path,fileHandle_t *file,int){bool found=maps.count(path)!=0;*file=found?1:0;return found?128:-1;}
 void FS_Close(fileHandle_t){}
 void Print(const char *format,...){char out[2048];va_list formatArgs;va_start(formatArgs,format);vsnprintf(out,sizeof(out),format,formatArgs);va_end(formatArgs);prints.push_back(out);}
 void SetConfigstring(int,const char*){}
 void SendConsoleCommand(int,const char *command){commands.push_back(command);}
 int Argc(){return (int)args.size();}
 void Argv(int index,char *out,size_t size){Q_strncpyz(out,index<(int)args.size()?args[index].c_str():"",size);}
 void DropClient(int index,const char*){dropped.push_back(index);level.clients[index].pers.connected=CON_DISCONNECTED;}
} fake,*trap=&fake;
int G_TffaTeams(){return level.gametype==GT_TEAM?Com_Clampi(2,8,trap->Cvar_VariableIntegerValue("g_tffaTeams")):2;}
int ST_TffaTeamAt(int slot){return slot==0?TEAM_RED:slot==1?TEAM_BLUE:slot+2;}
const char *ST_TffaName(int team){static const char *names[]={"free","red","blue","spectator","green","yellow","orange","cyan","pink","purple"};return names[team];}
int TeamCount(int ignore,team_t team){int count=0;for(int i=0;i<level.maxclients;++i)if(i!=ignore&&level.clients[i].pers.connected!=CON_DISCONNECTED&&level.clients[i].sess.sessionTeam==team)++count;return count;}
int PickTeam(int ignore){int best=TEAM_RED;for(int slot=1;slot<G_TffaTeams();++slot){int team=ST_TffaTeamAt(slot);if(TeamCount(ignore,team)<TeamCount(ignore,best))best=team;}return best;}
char *G_GetBotInfoByName(const char *name){return !std::strcmp(name,"Luke")||!std::strcmp(name,"Reborn")?(char *)"definition":nullptr;}
int ST_BotParseRole(const char *token){for(int i=0;i<8;++i)if(!std::strcmp(token,stmatch::roleTokens[i]))return i;return 0;}
void WP_ForcePowerStop(gentity_t *ent,forcePowers_t power){ent->client->ps.fd.forcePowersActive&=~(1<<power);}
int ST_BlockingMode(){return 1;}
qboolean ST_CombatOption(int){return qtrue;}
void G_UpdateCvars(){st_forceModeActive.integer=trap->Cvar_VariableIntegerValue("st_forceModeActive");st_weaponsActive.integer=trap->Cvar_VariableIntegerValue("st_weaponsActive");g_autoMapCycle.integer=trap->Cvar_VariableIntegerValue("g_autoMapCycle");}
void ST_MatchApplyTeamLock();
void ST_MatchPublishLiveBots(){}
void ST_MatchLiveInit(){}
qboolean ST_MatchBotValid(const char *,int,int,int,int);
void ST_MatchSpawnBot(const char *,int,int,int,int);
qboolean ST_ApplyQueuedRuleChanges();
#include "g_st_match_rules.inc"
static void G_AddBot(const char *,float,const char *team,int,char *,int,qboolean keepSkill){
 assert(keepSkill==qtrue);int selected=0;
 for(int slot=0;slot<G_TffaTeams();++slot)if(!std::strcmp(team,ST_TffaName(ST_TffaTeamAt(slot))))selected=ST_TffaTeamAt(slot);
 for(int i=0;i<level.maxclients;++i)if(level.clients[i].pers.connected==CON_DISCONNECTED){
  level.clients[i].pers.connected=CON_CONNECTED;level.clients[i].sess.sessionTeam=selected;g_entities[i].r.svFlags=SVF_BOT;fake.spawned.push_back(selected);return;}
 assert(false&&"Adapter preflight must prevent allocation failure");
}
#include "g_st_match_bots.inc"
qboolean ST_ApplyQueuedRuleChanges(){char map[MAX_QPATH]={0};qboolean restart=ST_MatchCommit(map,sizeof(map));if(restart){level.restarted=qtrue;trap->SendConsoleCommand(EXEC_APPEND,map[0]?va("map %s\n",map):"map_restart 0\n");}return restart;}
static void command(std::initializer_list<const char *> args){fake.args.clear();for(const char *a:args)fake.args.push_back(a);assert(ST_MatchConsoleCommand(fake.args[0].c_str()));}
static void fresh(int slots=8,int cap=0,int lock=0){
 fake=FakeTrap();level={};level.maxclients=slots;level.gametype=GT_TEAM;level.time=1000;level.framenum=3;
 for(int i=0;i<32;++i){g_entities[i]={};g_entities[i].client=&level.clients[i];g_entities[i].s.number=i;}
 for(const auto& rule:stmatch::rules)fake.cvars[rule.cvar]=std::to_string(rule.initial);
 fake.cvars["g_gametype"]="6";fake.cvars["mapname"]="mp/ffa3";fake.cvars["sv_maxclients"]=std::to_string(slots);fake.cvars["bot_enable"]="1";fake.cvars["st_matchManaged"]="0";fake.cvars["st_matchTeamCap"]=std::to_string(cap);fake.cvars["st_matchLockTeams"]=std::to_string(lock);
 fake.cvars["st_matchTeamsManaged"]=cap?"1":"0";fake.cvars["g_tffaTeamSize"]="0";fake.cvars["g_weaponDisable"]="0";fake.cvars["g_duelWeaponDisable"]="1";
 G_UpdateCvars();ST_MatchInit();
}
static void occupant(int slot,int team,bool bot,int connected=CON_CONNECTED){level.clients[slot].pers.connected=connected;level.clients[slot].sess.sessionTeam=team;g_entities[slot].r.svFlags=bot?SVF_BOT:0;}
int main(){
 // Staging, cancelling and unknown commands cannot adopt managed semantics.
 fresh();command({"st_match_set","fraglimit","25"});assert(fake.cvars["fraglimit"]=="10"&&fake.cvars["st_matchManaged"]=="0");
 command({"st_match_cancel"});assert(fake.cvars["st_matchPendingCount"]=="0"&&fake.cvars["st_matchManaged"]=="0");assert(!ST_MatchConsoleCommand("st_match_unknown"));assert(fake.cvars["st_matchManaged"]=="0");
 // Pure requires a full map spawn, even when the selected map is unchanged.
 fresh();command({"st_match_set","sv_pure","1"});command({"st_match_apply","now"});assert(level.restarted&&fake.commands.back()=="map mp/ffa3\n");
 // Normal later application keeps edits inert until the real boundary calls commit.
 fresh();command({"st_match_set","fraglimit","25"});command({"st_match_apply","later"});assert(fake.cvars["fraglimit"]=="10");char map[64]={0};assert(ST_MatchCommit(map,sizeof(map)));assert(fake.cvars["fraglimit"]=="25");
 // Engine settling frames precede reconnect. Rebuild and lock must wait for it.
 fresh(8,0,1);fake.cvars["st_matchInitialRosterPending"]="1";command({"st_match_clearbots"});command({"st_match_addbot","Luke","4","1","1"});command({"st_match_apply","roster"});
 for(int frame=0;frame<3;++frame){level.framenum=frame;ST_MatchFrame();assert(fake.dropped.empty()&&fake.spawned.empty()&&!level.stTeamsLocked);}
 occupant(0,TEAM_RED,false,CON_CONNECTING);occupant(1,TEAM_BLUE,true);level.framenum=3;ST_MatchFrame();assert(fake.dropped.size()==1&&fake.dropped[0]==1&&fake.spawned.size()==1);assert(level.clients[0].pers.connected==CON_CONNECTING&&level.stTeamsLocked&&level.stLockedTeam[0]==TEAM_RED);
 // Existing humans/bots count against a nonreplacement roster and its spare slot.
 fresh(4);occupant(0,1,false);occupant(1,1,true);occupant(2,2,true);occupant(3,2,false);command({"st_match_addbot","Luke","3","2","1"});command({"st_match_apply","roster"});ST_MatchFrame();assert(fake.spawned.empty()&&fake.dropped.empty());
 // The reserve is for a human, and can be consumed in either connection order.
 fresh(2);occupant(0,1,false);command({"st_match_addbot","Luke","3","2","1"});command({"st_match_apply","roster"});ST_MatchFrame();assert(fake.spawned.size()==1);
 fresh(2);command({"st_match_addbot","Luke","3","1","1"});command({"st_match_apply","roster"});ST_MatchFrame();assert(fake.spawned.size()==1);occupant(1,2,false);command({"st_match_set","g_allowVote","0"});command({"st_match_apply","now"});assert(fake.cvars["g_allowVote"]=="0");
 command({"st_match_addbot","Reborn","3","2","1"});command({"st_match_apply","roster"});ST_MatchFrame();assert(fake.spawned.size()==1);
 fresh(2);command({"st_match_set","g_gametype","4"});command({"st_match_apply","now"});assert(fake.cvars["g_gametype"]=="6"&&!level.restarted);
 // Explicit teams populate before Automatic, regardless of the saved slot order.
 fresh(8,1);command({"st_match_addbot","Luke","3","0","1","0"});command({"st_match_addbot","Reborn","3","1","1","1"});command({"st_match_apply","roster"});ST_MatchFrame();assert(fake.spawned.size()==2&&fake.spawned[0]==TEAM_RED&&fake.spawned[1]==TEAM_BLUE);
 // A legacy lock remains authoritative during this map, without becoming persistent.
 fresh();ST_MatchFrame();level.stTeamsLocked=qtrue;ST_MatchFrame();assert(level.stTeamsLocked&&fake.cvars["st_matchLockTeams"]=="0");command({"st_match_addbot","Luke","3","1","1"});command({"st_match_apply","roster"});assert(fake.cvars["st_matchRosterExecute"]!="1");
 command({"st_match_set","st_matchLockTeams","0"});command({"st_match_apply","now"});ST_MatchFrame();assert(!level.stTeamsLocked&&fake.spawned.size()==1);
 // Queued work cannot execute again in an outgoing restarted game VM.
 fresh();command({"st_match_addbot","Luke","3","1","1"});command({"st_match_apply","roster"});level.restarted=qtrue;ST_MatchFrame();assert(fake.spawned.empty());
 // Siege class inventories keep their default grants; explicit Custom remains supported.
 fresh();level.gametype=GT_SIEGE;assert(ST_MatchWeaponMask(0)==0);fake.cvars["st_matchWeaponDisable"]="32";assert(ST_MatchWeaponMask(2)==32);
 // Cap 0 remains authoritative over both known and already-running powers.
 fresh();st_forceModeActive.integer=2;fake.cvars["st_matchForceCap2"]="0";auto& force=level.clients[0].ps.fd;force.forcePowerLevel[2]=force.forcePowerBaseLevel[2]=3;force.forcePowersKnown=force.forcePowersActive=1<<2;ST_MatchApplyForce(&g_entities[0]);assert(force.forcePowerLevel[2]==0&&force.forcePowerBaseLevel[2]==0&&force.forcePowersKnown==0&&force.forcePowersActive==0);
 // Removing/clearing a queued rotation is a represented pending edit.
 fresh();fake.cvars["st_matchRotation"]="mp/ffa1";command({"st_match_text","rotation",""});assert(fake.cvars["st_matchPending_hasrotation"]=="1"&&fake.cvars["st_matchPending_rotation"].empty());
 // Explicit full stop discards both armed drafts and committed deferred roster work.
 fresh();command({"st_match_addbot","Luke","3","1","1"});command({"st_match_apply","roster"});fake.cvars["sv_killserver"]="1";ST_MatchShutdown();assert(fake.cvars["st_matchRosterExecute"]=="0"&&fake.cvars["st_matchPendingCount"]=="0");
 fresh();command({"st_match_addbot","Luke","3","1","1"});command({"st_match_apply","later"});fake.args={"killserver"};ST_MatchShutdown();assert(!ST_MatchReady()&&fake.cvars["st_matchRosterExecute"]=="0");
 // Vote/password/roster commits never adopt unrelated pristine legacy FFA guns.
 fresh();level.gametype=GT_FFA;fake.cvars["g_gametype"]="0";occupant(0,TEAM_FREE,false);level.clients[0].ps.stats[STAT_WEAPONS]=(1<<3)|(1<<5);level.clients[0].ps.weapon=5;
 command({"st_match_set","g_allowVote","0"});command({"st_match_apply","now"});assert(ST_MatchVotesManaged()&&!ST_MatchWeaponsManaged()&&!ST_MatchTeamsManaged()&&!ST_MatchPopulationManaged()&&fake.cvars["st_matchManaged"]=="0");
 command({"st_match_text","password","test-only"});command({"st_match_apply","now"});command({"st_match_addbot","Luke","3","0","1"});command({"st_match_apply","roster"});ST_MatchFrame();ST_MatchSpawn(&g_entities[0]);assert(ST_MatchEffectiveWeaponMask()==0&&level.clients[0].ps.weapon==5&&(level.clients[0].ps.stats[STAT_WEAPONS]&(1<<5))&&!ST_MatchWeaponsManaged()&&fake.cvars["st_matchManaged"]=="0");
 // Legacy TFFA size survives those same independent commits and roster preflight.
 fresh();fake.cvars["g_tffaTeamSize"]="2";occupant(0,1,false);occupant(1,1,false);assert(ST_MatchEffectiveTeamCap()==2&&!ST_MatchHasRoom(1,-1));command({"st_match_set","g_allowVote","0"});command({"st_match_apply","now"});command({"st_match_text","password","test-only"});command({"st_match_apply","now"});command({"st_match_addbot","Luke","3","2","1"});command({"st_match_apply","roster"});ST_MatchFrame();assert(fake.spawned.size()==1&&ST_MatchEffectiveTeamCap()==2&&!ST_MatchHasRoom(1,-1)&&!ST_MatchTeamsManaged());
 // Same raw 0 means a new explicit Saber-only intent in unmanaged FFA.
 fresh();level.gametype=GT_FFA;fake.cvars["g_gametype"]="0";command({"st_match_set","st_weaponsActive","0"});assert(fake.cvars["st_matchPendingCount"]=="1"&&!ST_MatchWeaponsManaged());command({"st_match_apply","now"});assert(ST_MatchWeaponsManaged()&&ST_MatchEffectiveWeaponMask()==524274&&!ST_MatchTeamsManaged()&&!ST_MatchPopulationManaged()&&!ST_MatchVotesManaged()&&fake.cvars["st_matchManaged"]=="0");
 // Same raw team cap 0 explicitly adopts unlimited, without adopting weapons.
 fresh();fake.cvars["g_tffaTeamSize"]="2";fake.cvars["g_weaponDisable"]="524278";command({"st_match_set","st_matchTeamCap","0"});assert(fake.cvars["st_matchPendingCount"]=="1");command({"st_match_apply","now"});assert(ST_MatchTeamsManaged()&&ST_MatchEffectiveTeamCap()==0&&!ST_MatchWeaponsManaged()&&ST_MatchEffectiveWeaponMask()==524278);
 // Population owns only its own policy. Existing full legacy targets do not
 // make an unrelated vote/password commit fail validation.
 fresh();fake.cvars["bot_minplayers"]="8";command({"st_match_set","g_allowVote","0"});command({"st_match_apply","now"});assert(fake.cvars["g_allowVote"]=="0"&&!ST_MatchPopulationManaged());command({"st_match_set","bot_minplayers","1"});command({"st_match_apply","now"});assert(ST_MatchPopulationManaged()&&!ST_MatchWeaponsManaged()&&!ST_MatchTeamsManaged());
 // Reaffirming a historically migrated numeric vote mask adopts only voting,
 // so the next legacy-init migration guard preserves the explicit bit pattern.
 fresh();fake.cvars["g_allowVote"]="1074";command({"st_match_set","g_allowVote","1074"});assert(fake.cvars["st_matchPendingCount"]=="1");command({"st_match_apply","now"});assert(ST_MatchVotesManaged()&&fake.cvars["g_allowVote"]=="1074"&&!ST_MatchWeaponsManaged()&&!ST_MatchTeamsManaged());
 // Explicit custom-mask adoption retains the paired effective Full mode.
 fresh();level.gametype=GT_FFA;fake.cvars["g_gametype"]="0";command({"st_match_set","st_weaponsActive","1"});command({"st_match_weapons","32"});command({"st_match_apply","now"});assert(ST_MatchWeaponsManaged()&&ST_MatchEffectiveWeaponMask()==0&&fake.cvars["st_matchWeaponDisable"]=="32");
 // Match Rules mode changes begin Duel rounds at one kill; untouched legacy
 // Duel vote/password changes preserve existing gameplay values.
 fresh();command({"st_match_set","g_gametype","3"});command({"st_match_apply","now"});assert(fake.cvars["fraglimit"]=="1"&&fake.cvars["st_matchManaged"]=="0");
 fresh();level.gametype=GT_DUEL;fake.cvars["g_gametype"]="3";ST_MatchInit();assert(fake.cvars["fraglimit"]=="10");command({"st_match_set","g_allowVote","0"});command({"st_match_apply","now"});assert(fake.cvars["fraglimit"]=="10");fake.cvars["st_matchManaged"]="1";ST_MatchInit();assert(fake.cvars["fraglimit"]=="1");
 return 0;
}
