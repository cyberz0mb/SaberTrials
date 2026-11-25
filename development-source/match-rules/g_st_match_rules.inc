/* Authoritative Match Rules adapter. Included only in the game module.
 * Commands are dispatched exclusively by the server console. GPL-2.0. */
#include "st_match_server_policy.h"

static stmatch::Draft stMatchDraft;
static std::vector<stmatch::Bot> stMatchBots;
static qboolean stMatchClearBots = qfalse;
static qboolean stMatchRosterArmed = qfalse;
static bool stMatchLockPending = true;
static int stMatchLiveUpdateAt=0;

static std::string ST_MatchCvar(const char *name) {
 char value[2048];trap->Cvar_VariableStringBuffer(name,value,sizeof(value));return value;
}
int ST_MatchInt(const char *name) {return trap->Cvar_VariableIntegerValue(name);}
static qboolean ST_MatchOwned(const char *domain) {return ST_MatchInt("st_matchManaged")||ST_MatchInt(domain)?qtrue:qfalse;}
qboolean ST_MatchWeaponsManaged(void) {return ST_MatchOwned("st_matchWeaponsManaged");}
qboolean ST_MatchTeamsManaged(void) {return ST_MatchOwned("st_matchTeamsManaged");}
qboolean ST_MatchPopulationManaged(void) {return ST_MatchOwned("st_matchPopulationManaged");}
qboolean ST_MatchVotesManaged(void) {return ST_MatchOwned("st_matchVotesManaged");}
int ST_MatchEffectiveTeamCap(void) {
 if(level.gametype!=GT_TEAM&&level.gametype!=GT_CTF)return 0;
 if(ST_MatchTeamsManaged())return Com_Clampi(0,16,ST_MatchInt("st_matchTeamCap"));
 int legacy=level.gametype==GT_TEAM?ST_MatchInt("g_tffaTeamSize"):0;
 return legacy?Com_Clampi(2,4,legacy):0;
}
static int ST_MatchTarget(const char *name) {
 const auto item=stMatchDraft.edits.find(name);
 return item==stMatchDraft.edits.end()?ST_MatchInt(name):atoi(item->second.c_str());
}
static int ST_MatchTargetCap(int type) {
 if(type!=GT_TEAM&&type!=GT_CTF)return 0;
 if(ST_MatchTeamsManaged()||stMatchDraft.edits.count("st_matchTeamCap"))return ST_MatchTarget("st_matchTeamCap");
 int legacy=type==GT_TEAM?ST_MatchInt("g_tffaTeamSize"):0;return legacy?Com_Clampi(2,4,legacy):0;
}
static void ST_MatchPublish(void) {
 for(int i=0;i<stmatch::RuleCount;++i){
  const auto item=stMatchDraft.edits.find(stmatch::rules[i].cvar);
  trap->Cvar_Set(va("st_matchPending_%s",stmatch::rules[i].cvar),item==stMatchDraft.edits.end()?"":item->second.c_str());
 }
 for(int i=0;i<stmatch::ForceCount;++i){
  const auto item=stMatchDraft.edits.find(std::string("st_matchForceCap")+std::to_string(i));
  trap->Cvar_Set(va("st_matchPending_force%d",i),item==stMatchDraft.edits.end()?"":item->second.c_str());
 }
 const char *keys[]={"st_matchWeaponDisable","st_matchRotation","sv_hostname","g_password","mapname"};
 const char *names[]={"weapons","rotation","hostname","password","map"};
 for(int i=0;i<5;++i){const auto item=stMatchDraft.edits.find(keys[i]);
  trap->Cvar_Set(va("st_matchPending_%s",names[i]),item==stMatchDraft.edits.end()?"":i==3?"1":item->second.c_str());}
 trap->Cvar_Set("st_matchPending_hasrotation",stMatchDraft.edits.count("st_matchRotation")?"1":"");
 trap->Cvar_Set("st_matchPending_hashostname",stMatchDraft.edits.count("sv_hostname")?"1":"");
 trap->Cvar_Set("st_matchPending_hasmap",stMatchDraft.edits.count("mapname")?"1":"");
 trap->Cvar_Set("st_matchPending_bots",stMatchBots.empty()?"":va("%d",(int)stMatchBots.size()));
 trap->Cvar_Set("st_matchPending_clearbots",stMatchClearBots?"1":"");
 for(int slot=0;slot<32;++slot){
  const stmatch::Bot *bot=NULL;for(const auto& candidate:stMatchBots)if(candidate.slot==slot){bot=&candidate;break;}
  trap->Cvar_Set(va("st_matchPending_bot%d_model",slot),bot?bot->model.c_str():"");
  trap->Cvar_Set(va("st_matchPending_bot%d_skill",slot),bot?va("%d",bot->skill):"");
  trap->Cvar_Set(va("st_matchPending_bot%d_team",slot),bot?va("%d",bot->team):"");
  trap->Cvar_Set(va("st_matchPending_bot%d_role",slot),bot?va("%d",bot->role):"");
 }
 trap->Cvar_Set("st_matchPendingCount",va("%d",(int)stMatchDraft.edits.size()+(int)stMatchBots.size()+(stMatchClearBots?1:0)));
 trap->Cvar_Set("st_matchPendingApply",stMatchDraft.armed||stMatchRosterArmed?"1":"0");
}
static void ST_MatchDropEqual(const char *name) {
 stMatchRosterArmed=qfalse;
 auto item=stMatchDraft.edits.find(name);
 bool adoption=(!ST_MatchWeaponsManaged()&&(!strcmp(name,"st_weaponsActive")||!strcmp(name,"st_matchWeaponDisable")))||
  (!ST_MatchTeamsManaged()&&!strcmp(name,"st_matchTeamCap"))||(!ST_MatchPopulationManaged()&&!strcmp(name,"bot_minplayers"))||(!ST_MatchVotesManaged()&&!strcmp(name,"g_allowVote"));
 if(item!=stMatchDraft.edits.end()&&item->second==ST_MatchCvar(name)&&
  !adoption&&(strcmp(name,"st_matchLockTeams")||atoi(item->second.c_str())==(level.stTeamsLocked?1:0)))stMatchDraft.edits.erase(item);
 ST_MatchPublish();
}
static bool ST_MatchBsp(const std::string& map) {
 if(!stmatch::mapName(map))return false;
 fileHandle_t file=0;int length=trap->FS_Open(va("maps/%s.bsp",map.c_str()),&file,FS_READ);
 if(file)trap->FS_Close(file);return length>0;
}
static bool ST_MatchRosterCapacity(const std::vector<stmatch::Bot>& bots,bool clear,int slots,int type,int cap,int teamCount) {
 int occupants=0,survivingBots=0,teams[10]={0};
 for(int i=0;i<level.maxclients;++i){
  if(level.clients[i].pers.connected==CON_DISCONNECTED)continue;
  if(clear&&(g_entities[i].r.svFlags&SVF_BOT))continue;
  if(g_entities[i].r.svFlags&SVF_BOT)++survivingBots;
  ++occupants;int team=level.clients[i].sess.sessionTeam;
  if(team>=0&&team<10)++teams[team];
 }
 if(survivingBots+(int)bots.size()>=slots){trap->Print("Match Rules: the bot roster must leave a connection for the host or another human.\n");return false;}
 if(occupants+(int)bots.size()>slots){trap->Print("Match Rules: surviving players plus the roster exceed connection capacity.\n");return false;}
 int active=0;for(int slot=0;slot<teamCount;++slot)active+=teams[ST_TffaTeamAt(slot)];
 if((type==GT_TEAM||type==GT_CTF)&&cap&&active+(int)bots.size()>teamCount*cap){
  trap->Print("Match Rules: surviving players plus the roster exceed total team capacity.\n");return false;}
 if((type==GT_TEAM||type==GT_CTF)&&cap)for(const auto& bot:bots)if(bot.team&&++teams[bot.team]>cap){
  trap->Print("Match Rules: surviving players plus the roster exceed a team cap.\n");return false;}
 return true;
}
static bool ST_MatchValidDraft(void) {
 int minimum=ST_MatchTarget("sv_minPing"),maximum=ST_MatchTarget("sv_maxPing");
 if(maximum&&maximum<minimum){trap->Print("Match Rules: maximum ping must be at least minimum ping.\n");return false;}
 auto map=stMatchDraft.edits.find("mapname");
 if(map!=stMatchDraft.edits.end()&&!ST_MatchBsp(map->second)){trap->Print("Match Rules: selected map BSP was not found.\n");return false;}
 if(stMatchDraft.edits.count("sv_pure")&&map==stMatchDraft.edits.end()&&!ST_MatchBsp(ST_MatchCvar("mapname"))){trap->Print("Match Rules: pure changes need an installed map for a full reload.\n");return false;}
 auto rotation=stMatchDraft.edits.find("st_matchRotation");
 if(rotation!=stMatchDraft.edits.end()){
  std::vector<std::string> maps;if(!stmatch::rotation(rotation->second,maps))return false;
  for(const auto& name:maps)if(!ST_MatchBsp(name)){trap->Print("Match Rules: rotation BSP missing: %s\n",name.c_str());return false;}
 }
 int type=ST_MatchTarget("g_gametype"),counts[10]={0},slots=ST_MatchTarget("sv_maxclients"),cap=ST_MatchTargetCap(type);
 if(type==GT_POWERDUEL&&slots<3){trap->Print("Match Rules: Power Duel requires at least three connection slots.\n");return false;}
 bool explicitUnlock=stMatchDraft.edits.count("st_matchLockTeams")&&ST_MatchTarget("st_matchLockTeams")==0;
 if(!stMatchBots.empty()&&type==GT_TEAM&&level.stTeamsLocked&&!explicitUnlock){
  trap->Print("Match Rules: unlock the existing teams before adding or rebuilding a bot roster.\n");return false;}
 if(!stMatchBots.empty()&&!ST_MatchInt("bot_enable")){trap->Print("Match Rules: bots are disabled.\n");return false;}
 int teamCount=type==GT_TEAM?ST_MatchTarget("g_tffaTeams"):type==GT_CTF?2:0;
 int minimumBots=ST_MatchTarget("bot_minplayers");
 bool populationEdit=stMatchDraft.edits.count("bot_minplayers")||stMatchDraft.edits.count("sv_maxclients")||stMatchDraft.edits.count("st_matchTeamCap")||stMatchDraft.edits.count("g_tffaTeams");
 if(populationEdit&&minimumBots>=slots){trap->Print("Match Rules: automatic bot population must leave a spare connection slot.\n");return false;}
 if(teamCount&&cap&&((populationEdit&&minimumBots>teamCount*cap)||(int)stMatchBots.size()>teamCount*cap)){
  trap->Print("Match Rules: bot population exceeds total team capacity.\n");return false;}
 if((int)stMatchBots.size()>=slots){trap->Print("Match Rules: reserve a connection slot beyond the bot roster.\n");return false;}
 for(const auto& bot:stMatchBots){
  if(!stmatch::roleAllowed(type,bot.role)||!stmatch::teamAllowed(type,ST_MatchTarget("g_tffaTeams"),bot.team)||!G_GetBotInfoByName(bot.model.c_str())){
   trap->Print("Match Rules: invalid or mode-incompatible bot roster.\n");return false;}
  if(bot.team&&cap&&++counts[bot.team]>cap){trap->Print("Match Rules: bot roster exceeds the team cap.\n");return false;}
 }
 bool capacityEdit=!stMatchBots.empty()||stMatchClearBots||stMatchDraft.edits.count("sv_maxclients")||stMatchDraft.edits.count("st_matchTeamCap")||stMatchDraft.edits.count("g_tffaTeams");
 return !capacityEdit||ST_MatchRosterCapacity(stMatchBots,stMatchClearBots!=0,slots,type,cap,teamCount);
}
static void ST_MatchQueueRoster(void) {
 if(!stMatchClearBots&&stMatchBots.empty()){trap->Cvar_Set("st_matchInitialRosterPending","0");return;}
 trap->Cvar_Set("st_matchRosterClear",stMatchClearBots?"1":"0");
 trap->Cvar_Set("st_matchRosterCount",va("%d",(int)stMatchBots.size()));
 for(size_t i=0;i<stMatchBots.size();++i){const auto& b=stMatchBots[i];
  trap->Cvar_Set(va("st_matchRoster_%d",(int)i),va("%d %d %d %d %s",b.slot,b.team,b.skill,b.role,stmatch::hex(b.model).c_str()));}
 trap->Cvar_Set("st_matchRosterExecute","1");
 stMatchBots.clear();stMatchClearBots=qfalse;stMatchRosterArmed=qfalse;
}
// Called at the existing rule boundary before the legacy queues commit.
qboolean ST_MatchReady(void) {return stMatchDraft.armed||stMatchRosterArmed?qtrue:qfalse;}
qboolean ST_MatchCommit(char *map,size_t size) {
 if(!ST_MatchReady())return qfalse;
 if(!ST_MatchValidDraft()){stMatchDraft.armed=false;stMatchRosterArmed=qfalse;ST_MatchPublish();return qfalse;}
 bool restart=stMatchDraft.restart();
 bool pureChange=stMatchDraft.edits.count("sv_pure")&&ST_MatchTarget("sv_pure")!=ST_MatchInt("sv_pure");
 bool duelModeChange=stMatchDraft.edits.count("g_gametype")&&(ST_MatchTarget("g_gametype")==GT_DUEL||ST_MatchTarget("g_gametype")==GT_POWERDUEL);
 if(stMatchDraft.edits.count("st_matchLockTeams"))stMatchLockPending=true;
 if(stMatchDraft.edits.count("st_weaponsActive")||stMatchDraft.edits.count("st_matchWeaponDisable"))trap->Cvar_Set("st_matchWeaponsManaged","1");
 if(stMatchDraft.edits.count("st_matchTeamCap"))trap->Cvar_Set("st_matchTeamsManaged","1");
 if(stMatchDraft.edits.count("bot_minplayers"))trap->Cvar_Set("st_matchPopulationManaged","1");
 if(stMatchDraft.edits.count("g_allowVote"))trap->Cvar_Set("st_matchVotesManaged","1");
 for(const auto& item:stMatchDraft.edits){
  if(item.first=="mapname"){if(map)Q_strncpyz(map,item.second.c_str(),size);}
  else trap->Cvar_Set(item.first.c_str(),item.second.c_str());
 }
 if(duelModeChange)trap->Cvar_Set("fraglimit","1");
 if(stMatchRosterArmed)ST_MatchQueueRoster();
 if(pureChange&&map&&!map[0])Q_strncpyz(map,ST_MatchCvar("mapname").c_str(),size);
 stMatchDraft.clear();G_UpdateCvars();
 if(!ST_MatchInt("st_matchRosterExecute")||!ST_MatchInt("st_matchLockTeams"))ST_MatchApplyTeamLock();
 ST_MatchPublish();
 trap->Print("Match Rules: queued settings applied%s.\n",restart?" at the restart boundary":"");
 return restart?qtrue:qfalse;
}
void ST_MatchShutdown(void) {
 char command[64];trap->Argv(0,command,sizeof(command));
 if(ST_MatchInt("sv_killserver")||!Q_stricmp(command,"killserver")){
  stMatchDraft.clear();stMatchBots.clear();stMatchClearBots=stMatchRosterArmed=qfalse;
  trap->Cvar_Set("st_matchRosterExecute","0");trap->Cvar_Set("st_matchRosterCount","0");trap->Cvar_Set("st_matchRosterClear","0");trap->Cvar_Set("st_matchInitialRosterPending","0");ST_MatchPublish();return;
 }
 // A normal map command also supplies a boundary. Do not replace its selected map.
 char unused[MAX_QPATH]={0};ST_MatchCommit(unused,sizeof(unused));
}
void ST_MatchApplyTeamLock(void) {
 if(!stMatchLockPending)return;
 stMatchLockPending=false;
 if(level.gametype!=GT_TEAM)return;
 qboolean lock=ST_MatchInt("st_matchLockTeams")?qtrue:qfalse;
 if(lock==level.stTeamsLocked)return;
 level.stTeamsLocked=lock;
 for(int i=0;i<level.maxclients;++i)level.stLockedTeam[i]=lock&&level.clients[i].pers.connected!=CON_DISCONNECTED?level.clients[i].sess.sessionTeam:TEAM_SPECTATOR;
}
qboolean ST_MatchHasRoom(int team,int ignoreClient) {
 if(level.gametype!=GT_TEAM&&level.gametype!=GT_CTF)return qtrue;
 int cap=ST_MatchEffectiveTeamCap();
 return !cap||TeamCount(ignoreClient,(team_t)team)<cap?qtrue:qfalse;
}
qboolean ST_MatchJoinAllowed(int clientNum,int team) {
 if(clientNum<0||clientNum>=level.maxclients)return qfalse;
 int old=level.clients[clientNum].sess.sessionTeam;
 return stmatch::entryAllowed(level.gametype,old,team,ST_MatchInt("st_allowTeamSwitch")!=0,
  level.stTeamsLocked!=0,level.stLockedTeam[clientNum],ST_MatchEffectiveTeamCap(),TeamCount(clientNum,(team_t)team))?qtrue:qfalse;
}
int ST_MatchForceCap(int power) {
 if(power<0||power>=NUM_FORCE_POWERS)return 0;
 return Com_Clampi(0,3,ST_MatchInt(va("st_matchForceCap%d",power)));
}
int ST_MatchForceMask(int mode) {
 std::array<int,stmatch::ForceCount> caps;for(int i=0;i<stmatch::ForceCount;++i)caps[i]=ST_MatchForceCap(i);
 return stmatch::forceMask(mode,caps);
}
int ST_MatchWeaponMask(int mode) {
 if(level.gametype==GT_SIEGE&&mode!=2)return 0;
 int mask=ST_MatchInt("st_matchWeaponDisable");
 if(mask<0||mask>=(1<<stmatch::WeaponCount))mask=0;
 return stmatch::weaponMask(mode,mask&~12);
}
int ST_MatchEffectiveWeaponMask(void) {
 if(ST_MatchWeaponsManaged())return ST_MatchWeaponMask(st_weaponsActive.integer);
 return ST_MatchInt(level.gametype==GT_DUEL||level.gametype==GT_POWERDUEL?"g_duelWeaponDisable":"g_weaponDisable");
}
void ST_MatchApplyForce(gentity_t *ent) {
 if(!ent||!ent->client||ent->s.number>=MAX_CLIENTS||st_forceModeActive.integer!=2)return;
 for(int i=0;i<NUM_FORCE_POWERS;++i){int cap=ST_MatchForceCap(i);
  ent->client->ps.fd.forcePowerLevel[i]=stmatch::forceCap(2,cap,ent->client->ps.fd.forcePowerLevel[i]);
  ent->client->ps.fd.forcePowerBaseLevel[i]=stmatch::forceCap(2,cap,ent->client->ps.fd.forcePowerBaseLevel[i]);
  if(!cap){if(ent->client->ps.fd.forcePowersActive&(1<<i))WP_ForcePowerStop(ent,(forcePowers_t)i);ent->client->ps.fd.forcePowersKnown&=~(1<<i);}
 }
}
void ST_MatchSpawn(gentity_t *ent) {
 if(!ent||!ent->client)return;
 gclient_t *client=ent->client;
 int health=Com_Clampi(0,500,ST_MatchInt("st_spawnHealth")),shield=Com_Clampi(-1,500,ST_MatchInt("st_spawnShield"));
 if(level.gametype!=GT_SIEGE&&client->sess.sessionTeam!=TEAM_SPECTATOR){
  if(health){client->pers.maxHealth=client->ps.stats[STAT_MAX_HEALTH]=health;ent->health=client->ps.stats[STAT_HEALTH]=health;}
  client->ps.stats[STAT_ARMOR]=stmatch::spawnShield(level.gametype,shield,client->ps.stats[STAT_ARMOR]);
 }
 if(client->sess.sessionTeam!=TEAM_SPECTATOR&&ST_MatchWeaponsManaged()){
  client->ps.stats[STAT_WEAPONS]&=~ST_MatchWeaponMask(st_weaponsActive.integer);
  if(!(client->ps.stats[STAT_WEAPONS]&(1<<client->ps.weapon))){
   int selected=0;for(int weapon=1;weapon<stmatch::WeaponCount;++weapon)if(client->ps.stats[STAT_WEAPONS]&(1<<weapon))selected=weapon;
   if(client->ps.stats[STAT_WEAPONS]&(1<<WP_SABER))selected=WP_SABER;
   // Explicit Custom may remove every gun in a Siege class. Keep a usable
   // melee fallback rather than selecting an unowned saber.
   if(!selected){selected=2;client->ps.stats[STAT_WEAPONS]|=1<<selected;}
   client->ps.weapon=selected;
  }
 }
 ST_MatchApplyForce(ent);
}
int ST_MatchRespawnAt(int normal) {return stmatch::respawnAt(level.gametype,normal,level.time,Com_Clampi(0,30000,ST_MatchInt("st_respawnDelay")));}
void ST_MatchPublishControls(void) {
 if(ST_MatchWeaponsManaged()){
  // The game's Cvar_VM_Set force-writes, including CVAR_LATCH cvars.
  trap->Cvar_Set("g_duelWeaponDisable",va("%d",ST_MatchWeaponMask(st_weaponsActive.integer)));
  trap->Cvar_Update(&g_duelWeaponDisable);
 }
 std::string caps;for(int i=0;i<NUM_FORCE_POWERS;++i)caps+=char('0'+ST_MatchForceCap(i));
 trap->SetConfigstring(CS_ST_COMBAT_CONTROLS,va("1 %d %d %d %s",ST_BlockingMode(),ST_CombatOption(ST_COMBAT_DEFENSE)?1:0,st_forceModeActive.integer,caps.c_str()));
}
void ST_MatchInit(void) {
 trap->Cvar_Register(NULL,"st_matchManaged","0",CVAR_ARCHIVE|CVAR_NORESTART);
 const char *domains[]={"st_matchWeaponsManaged","st_matchTeamsManaged","st_matchPopulationManaged","st_matchVotesManaged"};
 for(int i=0;i<4;++i)trap->Cvar_Register(NULL,domains[i],"0",CVAR_ARCHIVE|CVAR_NORESTART);
 const char *names[]={"st_spawnHealth","st_spawnShield","st_respawnDelay","st_matchTeamCap","st_allowTeamSwitch","st_matchLockTeams","st_matchWeaponDisable","st_matchRotation"};
 const char *values[]={"0","-1","0","0","1","0","0",""};
 for(int i=0;i<8;++i)trap->Cvar_Register(NULL,names[i],values[i],CVAR_ARCHIVE|CVAR_NORESTART);
 for(int i=0;i<NUM_FORCE_POWERS;++i)trap->Cvar_Register(NULL,va("st_matchForceCap%d",i),"3",CVAR_ARCHIVE|CVAR_NORESTART);
 for(int i=0;i<stmatch::RuleCount;++i)trap->Cvar_Register(NULL,va("st_matchPending_%s",stmatch::rules[i].cvar),"",CVAR_ROM);
 for(int i=0;i<NUM_FORCE_POWERS;++i)trap->Cvar_Register(NULL,va("st_matchPending_force%d",i),"",CVAR_ROM);
 const char *state[]={"weapons","rotation","hostname","password","map","bots","clearbots","hasrotation","hashostname","hasmap"};
 for(int i=0;i<10;++i)trap->Cvar_Register(NULL,va("st_matchPending_%s",state[i]),"",CVAR_ROM);
 trap->Cvar_Register(NULL,"st_matchPendingCount","0",CVAR_ROM);
 trap->Cvar_Register(NULL,"st_matchPendingApply","0",CVAR_ROM);
 const char *botFields[]={"model","skill","team","role"};
 for(int slot=0;slot<32;++slot)for(int field=0;field<4;++field)trap->Cvar_Register(NULL,va("st_matchPending_bot%d_%s",slot,botFields[field]),"",CVAR_ROM);
 stMatchDraft.clear();stMatchBots.clear();stMatchClearBots=stMatchRosterArmed=qfalse;ST_MatchPublish();
 stMatchLockPending=true;
 stMatchLiveUpdateAt=0;
 ST_MatchLiveInit();
 if(ST_MatchInt("st_matchManaged")&&(level.gametype==GT_DUEL||level.gametype==GT_POWERDUEL)){trap->Cvar_Set("fraglimit","1");trap->Cvar_Update(&fraglimit);}
 ST_MatchPublishControls();
}
void ST_MatchFrame(void) {
 // Both SV_SpawnServer and SV_MapRestart run three settling frames before
 // reconnecting engine clients. The fourth frame sees the restored occupants.
 if(level.restarted||level.framenum<3)return;
 if(level.time>=stMatchLiveUpdateAt){ST_MatchPublishLiveBots();stMatchLiveUpdateAt=level.time+500;}
 if(!ST_MatchInt("st_matchRosterExecute")){
  if(!ST_MatchInt("st_matchInitialRosterPending"))ST_MatchApplyTeamLock();return;
 }
 trap->Cvar_Set("st_matchRosterExecute","0");
 std::vector<stmatch::Bot> executing;
 int count=Com_Clampi(0,31,ST_MatchInt("st_matchRosterCount"));
 for(int i=0;i<count;++i){std::istringstream row(ST_MatchCvar(va("st_matchRoster_%d",i)));stmatch::Bot b;std::string model;
  if(row>>b.slot>>b.team>>b.skill>>b.role>>model&&stmatch::unhex(model,b.model))executing.push_back(b);
  trap->Cvar_Set(va("st_matchRoster_%d",i),"");
 }
 bool clear=ST_MatchInt("st_matchRosterClear")!=0;
 int teamCount=level.gametype==GT_TEAM?G_TffaTeams():level.gametype==GT_CTF?2:0;
 bool valid=(int)executing.size()==count&&ST_MatchRosterCapacity(executing,clear,level.maxclients,level.gametype,ST_MatchEffectiveTeamCap(),teamCount);
 if(!executing.empty()&&(!ST_MatchInt("bot_enable")||(level.gametype==GT_TEAM&&level.stTeamsLocked)))valid=false;
 for(const auto& b:executing)if(!ST_MatchBotValid(b.model.c_str(),b.skill,b.team,b.role,b.slot))valid=false;
 trap->Cvar_Set("st_matchInitialRosterPending","0");
 if(valid&&clear){
  // DropClient acts on a checked bot entity; names and humans cannot be targeted.
  for(int i=0;i<level.maxclients;++i)if(g_entities[i].client&&(g_entities[i].r.svFlags&SVF_BOT)&&level.clients[i].pers.connected!=CON_DISCONNECTED)trap->DropClient(i,"Match Rules: rebuilding bot roster");
 }
 // Explicit assignments reserve their team slots before Automatic picks teams.
 if(valid){for(int automatic=0;automatic<2;++automatic)for(const auto& b:executing)if((b.team==0)==(automatic!=0))ST_MatchSpawnBot(b.model.c_str(),b.skill,b.team,b.role,b.slot);}
 else trap->Print("Match Rules: roster transaction rejected before changing any bots; review current capacity and installed definitions.\n");
 trap->Cvar_Set("st_matchRosterCount","0");trap->Cvar_Set("st_matchRosterClear","0");
 ST_MatchApplyTeamLock();
 ST_MatchPublishLiveBots();
}
qboolean ST_MatchRotationConfigured(void) {
 std::vector<std::string> maps;return g_autoMapCycle.integer&&stmatch::rotation(ST_MatchCvar("st_matchRotation"),maps)&&!maps.empty()?qtrue:qfalse;
}
static void ST_MatchNextMap(void) {
 std::vector<std::string> maps;if(!g_autoMapCycle.integer||!stmatch::rotation(ST_MatchCvar("st_matchRotation"),maps)||maps.empty()){
  trap->SendConsoleCommand(EXEC_APPEND,"map_restart 0\n");return;
 }
 std::string current=ST_MatchCvar("mapname");size_t start=0;
 // Cursor preserves intentionally repeated entries in an ordered rotation.
 int cursor=ST_MatchInt("st_matchRotationCursor");
 if(cursor>=0&&cursor<(int)maps.size()&&maps[cursor]==current)start=(cursor+1)%maps.size();
 else for(size_t i=0;i<maps.size();++i)if(maps[i]==current){start=(i+1)%maps.size();break;}
 for(size_t n=0;n<maps.size();++n){size_t index=(start+n)%maps.size();if(!ST_MatchBsp(maps[index]))continue;
  trap->Cvar_Set("st_matchRotationCursor",va("%d",(int)index));trap->SendConsoleCommand(EXEC_APPEND,va("map %s\n",maps[index].c_str()));return;}
 trap->Print("Match Rules: rotation contains no installed BSPs; restarting current map.\n");trap->SendConsoleCommand(EXEC_APPEND,"map_restart 0\n");
}
static bool ST_MatchArgInt(int index,int& value) {char text[64];trap->Argv(index,text,sizeof(text));return stmatch::integer(text,value);}
qboolean ST_MatchBotValid(const char *name,int skill,int team,int role,int slot) {
 return name&&*name&&stmatch::safeText(name,64)&&skill>=1&&skill<=5&&slot>=0&&slot<32&&
  stmatch::roleAllowed(level.gametype,role)&&stmatch::teamAllowed(level.gametype,G_TffaTeams(),team)&&G_GetBotInfoByName(name)?qtrue:qfalse;
}
const char *ST_MatchRoleToken(int role) {return role>=0&&role<8?stmatch::roleTokens[role]:"";}
qboolean ST_MatchConsoleCommand(const char *cmd) {
 if(Q_stricmpn(cmd,"st_match_",9))return qfalse;
 char name[80],value[2048];int n=0,index=0;trap->Argv(1,name,sizeof(name));trap->Argv(2,value,sizeof(value));
 if(!Q_stricmp(cmd,"st_match_set")){
  if(trap->Argc()!=3||!stMatchDraft.set(name,value))trap->Print("Match Rules: invalid or start-only numeric setting.\n");else ST_MatchDropEqual(name);
 }else if(!Q_stricmp(cmd,"st_match_text")){
  if(trap->Argc()!=3||!stMatchDraft.text(name,value))trap->Print("Match Rules: invalid text setting.\n");
  else ST_MatchDropEqual(!Q_stricmp(name,"rotation")?"st_matchRotation":!Q_stricmp(name,"hostname")?"sv_hostname":!Q_stricmp(name,"password")?"g_password":"mapname");
 }else if(!Q_stricmp(cmd,"st_match_force")){
  if(trap->Argc()!=3||!ST_MatchArgInt(1,index)||!ST_MatchArgInt(2,n)||!stMatchDraft.force(index,n))trap->Print("Usage: st_match_force <index 0..17> <cap 0..3>\n");else ST_MatchDropEqual(va("st_matchForceCap%d",index));
 }else if(!Q_stricmp(cmd,"st_match_weapons")){
  if(trap->Argc()!=2||!ST_MatchArgInt(1,n)||!stMatchDraft.weapons(n))trap->Print("Match Rules: invalid weapon disable mask; melee and saber must remain available.\n");else ST_MatchDropEqual("st_matchWeaponDisable");
 }else if(!Q_stricmp(cmd,"st_match_cancel")){
  stMatchDraft.clear();stMatchBots.clear();stMatchClearBots=stMatchRosterArmed=qfalse;trap->Cvar_Set("st_matchInitialRosterPending","0");ST_MatchPublish();trap->Print("Match Rules: unapplied edits discarded.\n");
 }else if(!Q_stricmp(cmd,"st_match_clearbots")){
  if(trap->Argc()!=1)trap->Print("Usage: st_match_clearbots (stages an explicit bots-only rebuild)\n");
  else{stMatchClearBots=qtrue;stMatchBots.clear();stMatchRosterArmed=qfalse;stMatchDraft.armed=false;ST_MatchPublish();}
 }else if(!Q_stricmp(cmd,"st_match_rosterreset")){
  if(trap->Argc()!=1)trap->Print("Usage: st_match_rosterreset (discards only staged roster edits)\n");
  else{stMatchBots.clear();stMatchClearBots=stMatchRosterArmed=qfalse;ST_MatchPublish();}
 }else if(!Q_stricmp(cmd,"st_match_addbot")){
  stmatch::Bot b;char model[128];trap->Argv(1,model,sizeof(model));b.model=model;
  for(b.slot=0;b.slot<32;++b.slot){bool used=false;for(const auto& old:stMatchBots)if(old.slot==b.slot){used=true;break;}if(!used)break;}
  if((trap->Argc()!=5&&trap->Argc()!=6)||!ST_MatchArgInt(2,b.skill)||!ST_MatchArgInt(3,b.team)||!ST_MatchArgInt(4,b.role)||(trap->Argc()==6&&!ST_MatchArgInt(5,b.slot))||
   b.slot<0||b.slot>=32||b.skill<1||b.skill>5||!stmatch::safeText(b.model,64)||b.model.empty()||!stmatch::roleAllowed(ST_MatchTarget("g_gametype"),b.role)||!stmatch::teamAllowed(ST_MatchTarget("g_gametype"),ST_MatchTarget("g_tffaTeams"),b.team)||!G_GetBotInfoByName(b.model.c_str()))trap->Print("Match Rules: invalid bot definition, skill, team, role or slot.\n");
  else{bool replaced=false;for(auto& old:stMatchBots)if(old.slot==b.slot){old=b;replaced=true;break;}if(!replaced&&stMatchBots.size()<31)stMatchBots.push_back(b);stMatchRosterArmed=qfalse;stMatchDraft.armed=false;ST_MatchPublish();}
 }else if(!Q_stricmp(cmd,"st_match_apply")){
  if(trap->Argc()!=2||(Q_stricmp(name,"now")&&Q_stricmp(name,"later")&&Q_stricmp(name,"roster")))trap->Print("Usage: st_match_apply <now|later|roster>\n");
  else if(ST_MatchValidDraft()){
   if(!Q_stricmp(name,"roster")){ST_MatchQueueRoster();ST_MatchPublish();}
   else{stMatchDraft.armed=!stMatchDraft.edits.empty();stMatchRosterArmed=stMatchClearBots||!stMatchBots.empty()?qtrue:qfalse;ST_MatchPublish();
    if(!Q_stricmp(name,"now")){trap->Print("Match Rules: applying now; settings that need it restart this match.\n");ST_ApplyQueuedRuleChanges();}
    else trap->Print("Match Rules: changes queued for the next normal round or map boundary.\n");}
  }else if(!Q_stricmp(name,"roster")){trap->Cvar_Set("st_matchInitialRosterPending","0");ST_MatchApplyTeamLock();}
 }else if(!Q_stricmp(cmd,"st_match_nextmap")){if(trap->Argc()==1)ST_MatchNextMap();}
 else return qfalse;
 return qtrue;
}
