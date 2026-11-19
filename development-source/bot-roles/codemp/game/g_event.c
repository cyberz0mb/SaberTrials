/* Native adapter for the account-keyed tournament controller. */
#include "g_local.h"
#include "g_event.h"
#include "g_staff.h"
#include "st_event_ui.h"

static STEvent event;
static STEProfile profiles[MAX_CLIENTS];
static unsigned char generations[MAX_CLIENTS][16];
static int memberSlots[STE_MEMBERS],lastSerial,lastReset,lastHistory,nextPublish,roundResetAt;
static qboolean placing;
static int nextRequest[MAX_CLIENTS],nextBracket[MAX_CLIENTS],nextView[MAX_CLIENTS];
static char sentUI[MAX_CLIENTS][STE_UI_LINES][256];
static char sentActions[MAX_CLIENTS][128];
static qboolean arenaReady(void);
static void uiText(int recipient,int line,const char*value);
typedef struct {qboolean valid;int health,armor,force,ammo[MAX_AMMO],weapons,holdables,weapon,weaponTime,weaponstate,assists,kills,deaths;vec3_t origin,velocity;} combatSave;
static combatSave saved[STE_MEMBERS];
typedef struct {qboolean held;vec3_t origin,velocity;int pmType,lastTime;} heldPlayer;
static heldPlayer held[MAX_CLIENTS];
static void clearAccount(int slot);
static void clearUI(void) {
 trap->SendServerCommand(-1,"stereset");
 memset(sentUI,0,sizeof(sentUI));memset(sentActions,0,sizeof(sentActions));
}

static void say(int slot,const char*text) {
 char clean[768];int i;Q_strncpyz(clean,text,sizeof(clean));
 for(i=0;clean[i];i++)if(clean[i]=='"'||clean[i]=='\\'||clean[i]=='\n'||clean[i]=='\r')clean[i]=' ';
 trap->SendServerCommand(slot,va("print \"Tournament: %s\\n\"",clean));
}
static int slotMember(int slot) {return slot>=0&&slot<MAX_CLIENTS?STE_Member(&event,profiles[slot].account):-1;}
static const char*phaseName(void) {
 switch(event.phase){case STE_REGISTRATION:return "Registration";case STE_READY:return "Ready check";
 case STE_LIVE:return "Playing";case STE_PAUSED:return "Paused";case STE_COMPLETE:return "Complete";default:return "Off";}
}
static const char*entryName(int entry) {return entry==-2?"TBD":entry<0?"Bye":event.entries[entry].name;}
static void publishBracket(int slot) {
 int i=0,n,pair,entries[STE_ENTRIES];char text[220];
 memcpy(entries,event.seeds,sizeof(entries));
 for(n=event.bracketSize;n>1;n/=2)for(pair=0;pair<n/2;pair++,i++){
  if(i<event.historyCount){STEResult*r=&event.history[i];
   Com_sprintf(text,sizeof(text),"%d. %.12s %d:%d %.12s | %s: %.12s",i+1,entryName(r->a),r->score[0],r->score[1],entryName(r->b),
    r->kind==STE_PLAYED?"Win":r->kind==STE_FORFEIT?"Forfeit":r->kind==STE_BYE?"Bye":"Void",r->winner<0?"None":entryName(r->winner));
   entries[pair]=r->winner;
  }else{
   Com_sprintf(text,sizeof(text),"%d. %.20s / %.20s%s",i+1,entryName(entries[pair*2]),entryName(entries[pair*2+1]),i==event.historyCount?" [Current]":"");
   entries[pair]=-2;
  }
  uiText(slot,i+13,text);
 }
 while(i<31){uiText(slot,i+13,"");i++;}
}
static void status(int slot) {
 int i;char text[700];
 Com_sprintf(text,sizeof(text),"%s | %s | %d %s",phaseName(),event.teamSize?va("%dv%d TFFA",event.teamSize,event.teamSize):"Individual - 10 rounds",event.count,event.teamSize?"teams":"players");say(slot,text);
 if(event.active[0]>=0&&event.active[1]>=0){
  say(slot,va("%s %d - %d %s",event.entries[event.active[0]].name,event.score[0],event.score[1],event.entries[event.active[1]].name));
  for(i=0;i<event.memberCount;i++)if(STE_Side(&event,i)>=0)say(slot,va("%s: %s",event.members[i].profile.name,
   !event.members[i].profile.connected?"Disconnected":event.members[i].ready?"READY":"Not ready"));
 }
 for(i=0;i<event.historyCount;i++){STEResult*r=&event.history[i];say(slot,va("Match %d: %s (%s)",i+1,r->winner<0?"No winner":event.entries[r->winner].name,
 r->kind==STE_PLAYED?"played":r->kind==STE_BYE?"bye":r->kind==STE_FORFEIT?"forfeit":"void"));}
 if(event.phase==STE_COMPLETE)say(slot,event.champion<0?"Event ended without a champion":va("Champion: %s",event.entries[event.champion].name));
}
#include "g_event_ui.inc"
qboolean ST_EventActive(void){return event.phase!=STE_OFF;}
qboolean ST_EventPlacing(void){return placing;}
static void release(int slot) {
 if(held[slot].held&&g_entities[slot].client){g_entities[slot].client->ps.pm_type=held[slot].pmType;VectorCopy(held[slot].velocity,g_entities[slot].client->ps.velocity);}
 held[slot].held=qfalse;
}
static void saveCombat(int slot,int m) {
 gentity_t*ent=&g_entities[slot];combatSave*s;
 if(m<0||STE_Side(&event,m)<0||ent->client->sess.sessionTeam==TEAM_SPECTATOR)return;
 s=&saved[m];s->valid=qtrue;s->health=ent->health;s->armor=ent->client->ps.stats[STAT_ARMOR];s->force=ent->client->ps.fd.forcePower;
 memcpy(s->ammo,ent->client->ps.ammo,sizeof(s->ammo));s->weapons=ent->client->ps.stats[STAT_WEAPONS];s->holdables=ent->client->ps.stats[STAT_HOLDABLE_ITEMS];
 s->weapon=ent->client->ps.weapon;s->weaponTime=ent->client->ps.weaponTime;s->weaponstate=ent->client->ps.weaponstate;
 s->assists=ent->client->pers.stTffaAssists;
 s->kills=ent->client->pers.stTffaKills;s->deaths=ent->client->pers.stTffaDeaths;
 VectorCopy(ent->client->ps.origin,s->origin);VectorCopy(held[slot].held?held[slot].velocity:ent->client->ps.velocity,s->velocity);
}
static void restoreCombat(int slot,int m) {
 gentity_t*ent=&g_entities[slot];combatSave*s=&saved[m];if(!s->valid)return;
 ent->health=ent->client->ps.stats[STAT_HEALTH]=s->health;ent->client->ps.stats[STAT_ARMOR]=s->armor;ent->client->ps.fd.forcePower=s->force;
 memcpy(ent->client->ps.ammo,s->ammo,sizeof(s->ammo));ent->client->ps.stats[STAT_WEAPONS]=s->weapons;ent->client->ps.stats[STAT_HOLDABLE_ITEMS]=s->holdables;
 ent->client->ps.weapon=s->weapon;ent->client->ps.weaponTime=s->weaponTime;ent->client->ps.weaponstate=s->weaponstate;
 ent->client->pers.stTffaAssists=s->assists;
 ent->client->pers.stTffaKills=s->kills;ent->client->pers.stTffaDeaths=s->deaths;
 VectorCopy(s->origin,ent->client->ps.origin);VectorCopy(s->origin,ent->r.currentOrigin);VectorCopy(s->velocity,ent->client->ps.velocity);
 ent->client->ps.pm_type=s->health>0?PM_NORMAL:PM_DEAD;
 if(s->health<=0){ent->client->ps.eFlags|=EF_DEAD;ent->client->respawnTime=level.time+1700;}
 ent->client->ps.eFlags^=EF_TELEPORT_BIT;
 trap->LinkEntity((sharedEntity_t*)ent);
}
void ST_EventDisconnect(int slot) {
 if(slot<0||slot>=MAX_CLIENTS)return;
 saveCombat(slot,slotMember(slot));
 STE_Connected(&event,profiles[slot].account,0,(uint64_t)level.time);
 memset(&profiles[slot],0,sizeof(profiles[slot]));memset(generations[slot],0,16);held[slot].held=qfalse;nextPublish=0;
 memset(sentUI[slot],0,sizeof(sentUI[slot]));sentActions[slot][0]=0;
}
static qboolean validText(const char*s,int length,qboolean identifier) {
 int i;for(i=0;i<length&&s[i];i++){unsigned char c=(unsigned char)s[i];if(c<32||c==127||c=='"'||c=='\\'||c==';'||(identifier&&c>126))return qfalse;}
 return i>0&&i<length;
}
static int setAccount(int slot,const unsigned char generation[16],const STEProfile*p) {
 unsigned char current[16];int i;
 if(slot<0||slot>=level.maxclients||!generation||!p||!p->verified||level.clients[slot].pers.connected!=CON_CONNECTED||
 (g_entities[slot].r.svFlags&SVF_BOT)||!ST_StaffGenerationForClient(slot,current)||memcmp(current,generation,16)||
 !validText(p->account,sizeof(p->account),qtrue)||!validText(p->name,sizeof(p->name),qfalse)||
 (p->team[0]&&(!validText(p->team,sizeof(p->team),qtrue)||!validText(p->teamName,sizeof(p->teamName),qfalse))))return 0;
 for(i=0;i<level.maxclients;i++)if(i!=slot&&!strcmp(profiles[i].account,p->account))return 0;
 if(profiles[slot].account[0]&&strcmp(profiles[slot].account,p->account))return 0;
 i=STE_Member(&event,p->account);
 if(i>=0&&strcmp(event.members[i].profile.team,p->team)){clearAccount(slot);return 0;}
 profiles[slot]=*p;profiles[slot].connected=1;memcpy(generations[slot],generation,16);
 STE_Connected(&event,p->account,1,(uint64_t)level.time);
 trap->SendServerCommand(slot,va("steaccount 1 \"%s\"",p->name));nextPublish=0;return 1;
}
static void clearAccount(int slot) {
 if(slot<0||slot>=MAX_CLIENTS)return;ST_EventDisconnect(slot);trap->SendServerCommand(slot,"steaccount 0 \"Signed out\"");
}
static int getSnapshot(STEvent*out,unsigned int size) {if(!out||size!=sizeof(event))return 0;*out=event;return 1;}
Q_EXPORT const STEventAccountAPI* GetSaberTrialsEventAccountAPI(void) {
 static const STEventAccountAPI api={1,sizeof(STEventAccountAPI),setAccount,clearAccount,getSnapshot};return &api;
}
void ST_EventInit(void) {
 int mode=trap->Cvar_VariableIntegerValue("st_tournamentMode");
 memset(&event,0,sizeof(event));memset(profiles,0,sizeof(profiles));memset(held,0,sizeof(held));memset(saved,0,sizeof(saved));
 memset(generations,0,sizeof(generations));lastSerial=lastReset=lastHistory=nextPublish=roundResetAt=0;
 memset(nextRequest,0,sizeof(nextRequest));memset(nextBracket,0,sizeof(nextBracket));memset(nextView,0,sizeof(nextView));placing=qfalse;
 memset(sentUI,0,sizeof(sentUI));memset(sentActions,0,sizeof(sentActions));
 if(mode>=1&&mode<=5&&level.gametype==(mode==1?GT_DUEL:GT_TEAM))STE_Open(&event,mode==1?0:mode,(uint64_t)level.time);
}
qboolean ST_EventCanJoin(int slot,int team) {
 int member,side;if(!ST_EventActive()||placing)return qtrue;
 member=slotMember(slot);side=STE_Side(&event,member);
 if(team==TEAM_SPECTATOR)return side<0;
 return side>=0&&(event.phase==STE_READY||event.phase==STE_PAUSED||event.phase==STE_LIVE)&&team==(event.teamSize?(side?TEAM_BLUE:TEAM_RED):TEAM_FREE);
}
qboolean ST_EventAllowCommand(int slot,const char*cmd) {
 if(!ST_EventActive()||STE_Side(&event,slotMember(slot))<0||event.phase==STE_LIVE)return qtrue;
 return !Q_stricmp(cmd,"tournament")||!Q_stricmp(cmd,"say")||!Q_stricmp(cmd,"say_team")||
 !Q_stricmp(cmd,"tell")||!Q_stricmp(cmd,"score")||!Q_stricmp(cmd,"players");
}
qboolean ST_EventBlocked(const gentity_t* ent) {
 int member;if(!ST_EventActive()||!ent||!ent->client||ent->s.number>=MAX_CLIENTS)return qfalse;
 member=slotMember(ent->s.number);
 return event.phase!=STE_LIVE||roundResetAt||STE_Side(&event,member)<0;
}
/* Absolute deadlines need the same pause as movement; relative pmove timers
 * already stop because paused players never enter pmove. Run once per tick. */
static void shiftDeadline(int*t,int dt) {if(*t>0&&*t<2147483647-dt)*t+=dt;}
static void shiftPlayerTimers(gclient_t*c,int dt) {
 int i;playerState_t*p=&c->ps;if(dt<=0)return;
 for(i=0;i<MAX_POWERUPS;i++)shiftDeadline(&p->powerups[i],dt);
 for(i=0;i<NUM_FORCE_POWERS;i++){shiftDeadline(&p->fd.forcePowerDuration[i],dt);shiftDeadline(&p->fd.forcePowerDebounce[i],dt);}
 shiftDeadline(&p->fd.forcePowerRegenDebounceTime,dt);shiftDeadline(&p->fd.forceRageRecoveryTime,dt);
 shiftDeadline(&p->fd.forceGripUseTime,dt);shiftDeadline(&p->fd.forceGripDamageDebounceTime,dt);
 shiftDeadline(&p->forceHandExtendTime,dt);shiftDeadline(&p->forceRageDrainTime,dt);
 shiftDeadline(&p->forceAllowDeactivateTime,dt);shiftDeadline(&p->saberBlockTime,dt);
 shiftDeadline(&p->saberLockTime,dt);shiftDeadline(&p->electrifyTime,dt);
 shiftDeadline(&c->respawnTime,dt);shiftDeadline(&c->inactivityTime,dt);shiftDeadline(&c->airOutTime,dt);
 shiftDeadline(&c->stParryWindowEnd,dt);shiftDeadline(&c->stParryCooldownEnd,dt);
 shiftDeadline(&c->stPerfectParrySuccessTime,dt);shiftDeadline(&c->stCounterWindowEnd,dt);shiftDeadline(&c->stShieldRegenDelayEnd,dt);
}
qboolean ST_EventThink(gentity_t* ent) {
 heldPlayer*h;int slot;if(!ST_EventActive()||!ent||!ent->client||ent->s.number>=MAX_CLIENTS)return qfalse;
 slot=ent->s.number;h=&held[slot];
 if(ent->client->sess.sessionTeam==TEAM_SPECTATOR){release(slot);return qfalse;}
 if(!ST_EventBlocked(ent)){release(slot);return qfalse;}
 if(!h->held){h->held=qtrue;h->lastTime=level.time;h->pmType=ent->client->ps.pm_type;VectorCopy(ent->client->ps.origin,h->origin);VectorCopy(ent->client->ps.velocity,h->velocity);}
 shiftPlayerTimers(ent->client,level.time-h->lastTime);h->lastTime=level.time;
 VectorCopy(h->origin,ent->client->ps.origin);VectorClear(ent->client->ps.velocity);ent->client->ps.pm_type=PM_FREEZE;
 ent->client->ps.commandTime=ent->client->pers.cmd.serverTime;ent->client->buttons=ent->client->oldbuttons=0;
 BG_PlayerStateToEntityState(&ent->client->ps,&ent->s,qtrue);VectorCopy(h->origin,ent->r.currentOrigin);trap->LinkEntity((sharedEntity_t*)ent);return qtrue;
}
qboolean ST_EventHoldEntity(gentity_t*ent) {
 int dt;if(!ST_EventActive()||(event.phase==STE_LIVE&&!roundResetAt)||ent->s.number<MAX_CLIENTS||!ent->inuse)return qfalse;
 dt=level.time-level.previousTime;ent->s.pos.trTime+=dt;ent->s.apos.trTime+=dt;if(ent->nextthink>0)ent->nextthink+=dt;return qtrue;
}
static void placePlayers(qboolean reset) {
 int slot,m,side,team,red=level.teamScores[TEAM_RED],blue=level.teamScores[TEAM_BLUE];placing=qtrue;if(reset){
  memset(saved,0,sizeof(saved));
  /* Player-created explosives must not cross individual rounds or restarts. */
  for(slot=MAX_CLIENTS;slot<level.num_entities;slot++)if(g_entities[slot].inuse&&
   (g_entities[slot].s.eType==ET_MISSILE||g_entities[slot].s.weapon==WP_DET_PACK)&&
   g_entities[slot].r.ownerNum>=0&&g_entities[slot].r.ownerNum<MAX_CLIENTS&&
   g_entities[slot].s.weapon!=WP_SABER)G_FreeEntity(&g_entities[slot]);
 }
 for(slot=0;slot<level.maxclients;slot++)if(level.clients[slot].pers.connected==CON_CONNECTED){
  m=slotMember(slot);side=STE_Side(&event,m);team=side<0?TEAM_SPECTATOR:event.teamSize?(side?TEAM_BLUE:TEAM_RED):TEAM_FREE;
  if(level.clients[slot].sess.sessionTeam!=team){release(slot);SetTeam(&g_entities[slot],team==TEAM_SPECTATOR?"spectator":team==TEAM_RED?"red":team==TEAM_BLUE?"blue":"free");if(side>=0&&!reset)restoreCombat(slot,m);}
  if(reset&&side>=0){
   gclient_t*c=&level.clients[slot];
   release(slot);ClientSpawn(&g_entities[slot]);c->ps.persistant[PERS_SCORE]=0;
   c->pers.stTffaAssists=c->pers.stTffaKills=c->pers.stTffaDeaths=0;
  }
 }
 if(reset){level.teamScores[TEAM_RED]=level.teamScores[TEAM_BLUE]=0;CalculateRanks();}
 else {level.teamScores[TEAM_RED]=red;level.teamScores[TEAM_BLUE]=blue;}
 placing=qfalse;
}
static qboolean arenaReady(void) {
 int m,slot,side,wanted;
 for(m=0;m<event.memberCount;m++)if((side=STE_Side(&event,m))>=0){
  for(slot=0;slot<level.maxclients;slot++)if(profiles[slot].account[0]&&!strcmp(profiles[slot].account,event.members[m].profile.account))break;
  wanted=event.teamSize?(side?TEAM_BLUE:TEAM_RED):TEAM_FREE;
  if(slot==level.maxclients||level.clients[slot].pers.connected!=CON_CONNECTED||
   level.clients[slot].sess.sessionTeam!=wanted||ST_StaffBlocked(&g_entities[slot]))return qfalse;
 }
 return qtrue;
}
void ST_EventFrame(void) {
 int i,m,dead[2]={0,0};unsigned char current[16];if(!ST_EventActive())return;
 for(i=0;i<STE_MEMBERS;i++)memberSlots[i]=-1;
 for(i=0;i<level.maxclients;i++)if(profiles[i].account[0]){
  if(level.clients[i].pers.connected!=CON_CONNECTED||!ST_StaffGenerationForClient(i,current)||memcmp(current,generations[i],16)){ST_EventDisconnect(i);continue;}
  m=slotMember(i);if(m>=0)memberSlots[m]=i;
 }
 if(event.teamSize&&event.phase==STE_LIVE)STE_Score(&event,level.teamScores[TEAM_RED],level.teamScores[TEAM_BLUE],(uint64_t)level.time);
 else STE_Tick(&event,(uint64_t)level.time);
 if(lastSerial!=event.serial||lastReset!=event.resetSerial){lastSerial=event.serial;lastReset=event.resetSerial;roundResetAt=0;placePlayers(qtrue);say(-1,"Bracket updated. Current competitors must select Ready.");}
 else placePlayers(qfalse);
 if(event.phase==STE_LIVE){
  if(roundResetAt){if(level.time>=roundResetAt){roundResetAt=0;placePlayers(qtrue);}}
  else if(!event.teamSize) {
   for(i=0;i<event.memberCount;i++)if(STE_Side(&event,i)>=0&&memberSlots[i]>=0&&g_entities[memberSlots[i]].health<=0)dead[STE_Side(&event,i)]=1;
   if(dead[0]||dead[1]){if(dead[0]!=dead[1])STE_Round(&event,dead[0]?1:0,(uint64_t)level.time);roundResetAt=level.time+2500;nextPublish=0;}
  }
 }
 for(i=0;i<level.maxclients;i++)if(g_entities[i].inuse)ST_EventThink(&g_entities[i]);
 for(i=0;i<event.memberCount;i++)if(memberSlots[i]>=0)saveCombat(memberSlots[i],i);
 if(lastHistory!=event.historyCount){lastHistory=event.historyCount;publishBracket(-1);nextPublish=0;}
 if(level.time>=nextPublish){publish(-1);nextPublish=level.time+1000;}
}
static int control(const char*op,const char*arg,const char*reason) {
 int ok=0,index;if(!ST_EventActive())return 0;
 if(!reason||!validText(reason,160,qfalse))return 0;
 if(!Q_stricmp(op,"pause"))ok=STE_Pause(&event,1,(uint64_t)level.time);
 else if(!Q_stricmp(op,"resume"))ok=STE_Pause(&event,0,(uint64_t)level.time);
 else if(!Q_stricmp(op,"restart"))ok=STE_Restart(&event,(uint64_t)level.time);
 else if(!Q_stricmp(op,"disqualify")) {char*end;long parsed=strtol(arg,&end,10);index=(int)parsed;if(arg[0]&&!*end&&parsed>=1&&parsed<=event.count)ok=STE_Disqualify(&event,index-1,(uint64_t)level.time);}
 /* Keep long moderation reasons out of the one-line menu feedback area. */
 if(ok){say(-1,va("Staff %s: %s",op,reason));uiText(-1,55,va("Staff %s. See console for the reason.",op));nextPublish=0;}return ok;
}
int ST_EventStaff(const STVerifiedAction*a,STGameResult*r) {
 r->ok=a->argc>=2&&control(a->args[0],a->argc==3?a->args[1]:"",a->args[a->argc-1]);
 Q_strncpyz(r->message,r->ok?"Tournament updated":"Use tournament pause/resume/restart <reason>, or disqualify <entry number> <reason>",sizeof(r->message));return 1;
}
qboolean ST_EventClientCommand(gentity_t*ent) {
 char op[32],target[65];int slot=ent->s.number,m,ok=0;trap->Argv(1,op,sizeof(op));
 if(!ST_EventActive()&&Q_stricmp(op,"logout"))return qfalse;
 /* Bound every visitor request before producing any reliable messages. */
 if(!Q_stricmp(op,"bracket")){
  if(level.time<nextBracket[slot])return qtrue;nextBracket[slot]=level.time+750;
 }else if(!Q_stricmp(op,"status")||!op[0]){
  if(level.time<nextView[slot])return qtrue;nextView[slot]=level.time+750;
 }else{if(level.time<nextRequest[slot])return qtrue;nextRequest[slot]=level.time+750;}
 if(!Q_stricmp(op,"logout")){clearAccount(slot);return qtrue;}
 if(!ST_EventActive()){say(slot,"No account tournament is open. The operator can select Tournament Individual or Team.");return qtrue;}
 if(!Q_stricmp(op,"bracket")){int i;for(i=13;i<44;i++)sentUI[slot][i][0]=1;publishBracket(slot);return qtrue;}
 if(!Q_stricmp(op,"status")||!op[0]){
  int i;for(i=0;i<STE_UI_LINES;i++)if(i<13||i>=44)sentUI[slot][i][0]=1;
  sentActions[slot][0]=0;publish(slot);return qtrue;
 }
 if(!profiles[slot].verified){feedback(slot,"Account not verified on this server. Open Account and check sign-in.");publish(slot);return qtrue;}
 if(!Q_stricmp(op,"join")&&!ST_StaffBlocked(ent))ok=STE_Join(&event,&profiles[slot]);
 else if(!Q_stricmp(op,"leave"))ok=STE_Leave(&event,profiles[slot].account);
 else if(!Q_stricmp(op,"ready")){
  placePlayers(qfalse);
  /* Allow unready anytime, but no ready transition until placement succeeds. */
  m=slotMember(slot);
  if((m>=0&&event.members[m].ready)||arenaReady())ok=STE_Ready(&event,profiles[slot].account,(uint64_t)level.time);
 }
 else if(!Q_stricmp(op,"substitute")){
  /* A short roster number identifies even an absent starter; no account hash. */
  char*end;long number;trap->Argv(2,target,sizeof(target));number=strtol(target,&end,10);
  m=target[0]&&!*end&&number>=1&&number<=event.memberCount?(int)number-1:-1;
  if(m>=0){ok=STE_Substitute(&event,event.members[m].profile.account,profiles[slot].account,(uint64_t)level.time);if(ok)saved[slotMember(slot)]=saved[m];}
 }
 if(ok)feedback(slot,!Q_stricmp(op,"join")?"Registered for this tournament.":!Q_stricmp(op,"leave")?"Registration removed.":
  !Q_stricmp(op,"ready")?(event.members[slotMember(slot)].ready?"You are ready.":"You are not ready."):"Replacement accepted. Everyone must ready again.");
 else feedback(slot,!Q_stricmp(op,"join")?(event.teamSize&&!profiles[slot].team[0]?"Join a registered team before entering a team tournament.":"Cannot join: registration is closed, full, or you are already registered."):
  !Q_stricmp(op,"leave")?"You can leave only while registration is open.":!Q_stricmp(op,"ready")?"Only current competitors can ready. Both lineups must be present.":
  "Only a registered reserve can replace an absent teammate in this match.");
 publish(slot);nextPublish=0;return qtrue;
}
void ST_EventConsole(void) {
 char op[32],kind[32];int size;trap->Argv(1,op,sizeof(op));trap->Argv(2,kind,sizeof(kind));
 if(!Q_stricmp(op,"open")){
  size=!Q_stricmp(kind,"individual")?1:atoi(kind);
  if(size<1||size>5){trap->Print("Tournament: open individual, or open 2/3/4/5 for team size.\n");return;}
 if(ST_EventActive()&&event.phase!=STE_COMPLETE){trap->Print("Tournament already open. Close it explicitly first.\n");return;}
  trap->Cvar_Set("st_tournamentMode",va("%d",size));trap->Cvar_Set("g_gametype",va("%d",size==1?GT_DUEL:GT_TEAM));
  trap->SendConsoleCommand(EXEC_APPEND,"map_restart 0\n");return;
 }
 if(!Q_stricmp(op,"close")){say(-1,"Event closed by operator");memset(&event,0,sizeof(event));trap->Cvar_Set("st_tournamentMode","0");for(size=0;size<MAX_CLIENTS;size++)release(size);clearUI();return;}
 if(!Q_stricmp(op,"start")){say(-1,STE_Start(&event,(uint32_t)Q_irand(1,2147483646),(uint64_t)level.time)?"Bracket locked; active players must select Ready":"Need even 8-32 individuals, or 2-8 full registered teams");return;}
 if(!Q_stricmp(op,"status")||!Q_stricmp(op,"bracket")){int i;status(-1);for(i=0;i<event.count;i++)trap->Print("Entry %d: %s\n",i+1,event.entries[i].name);return;}
 if(!control(op,kind,ConcatArgs(!Q_stricmp(op,"disqualify")?3:2)))trap->Print("Tournament: open individual|2|3|4|5, start, status, bracket, pause/resume/restart <reason>, disqualify <entry> <reason>, close\n");
}
