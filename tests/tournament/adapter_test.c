/* Real adapter, scripted engine imports; never starts a server or game. */
#include "g_local.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do{if(!(x)){fprintf(stderr,"line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
level_locals_t level;
gentity_t g_entities[MAX_GENTITIES];
gclient_t g_clients[MAX_CLIENTS];
static gameImport_t imports;gameImport_t*trap=&imports;
static const char*arg="join",*arg2="";
static int broadcasts,unicasts;
static int placementFails;
static char ui[MAX_CLIENTS][61][256];
static int actions[MAX_CLIENTS][10],messages[MAX_CLIENTS];
static void Argv(int n,char*out,int len){Q_strncpyz(out,n==0?"tournament":n==1?arg:n==2?arg2:"",len);}
static int Mode(const char*name){return !strcmp(name,"st_tournamentMode")?2:!strcmp(name,"st_tournamentRequireDiscord")?1:0;}
static void Link(sharedEntity_t*e){(void)e;}
static void Send(int slot,const char*text){
 int first=slot<0?0:slot,last=slot<0?level.maxclients:slot+1,s,line,used;
 if(slot<0)broadcasts++;else unicasts++;
 for(s=first;s<last;s++){
  messages[s]++;
  if(!strcmp(text,"stereset")){memset(ui[s],0,sizeof(ui[s]));memset(actions[s],0,sizeof(actions[s]));}
  if(sscanf(text,"steui %d %n",&line,&used)==1&&line>=0&&line<61&&text[used]=='"'){
   size_t len;Q_strncpyz(ui[s][line],text+used+1,sizeof(ui[s][line]));len=strlen(ui[s][line]);if(len&&ui[s][line][len-1]=='"')ui[s][line][len-1]=0;
  }
  if(!strncmp(text,"steactions ",11))sscanf(text+11,"%d %d %d %d %d %d %d %d %d %d",
   &actions[s][0],&actions[s][1],&actions[s][2],&actions[s][3],&actions[s][4],
   &actions[s][5],&actions[s][6],&actions[s][7],&actions[s][8],&actions[s][9]);
 }
}
static void CvarSet(const char*name,const char*value){(void)name;(void)value;}
static void Print(const char*fmt,...){(void)fmt;}
static NORETURN void Fatal(int level,const char*fmt,...){(void)level;(void)fmt;exit(2);}
void(*Com_Printf)(const char*,...)=Print;
NORETURN_PTR void(*Com_Error)(int,const char*,...)=Fatal;
char*ConcatArgs(int start){(void)start;return "Test reason";}
int ST_StaffGenerationForClient(int slot,unsigned char out[16]){memset(out,0,16);out[0]=(unsigned char)(slot+1);return 1;}
void BG_PlayerStateToEntityState(playerState_t*ps,entityState_t*s,qboolean snap){(void)ps;(void)s;(void)snap;}
void ClientSpawn(gentity_t*e){e->health=e->client->ps.stats[STAT_HEALTH]=100;e->client->ps.stats[STAT_ARMOR]=100;e->client->ps.fd.forcePower=100;e->client->ps.pm_type=PM_NORMAL;VectorClear(e->client->ps.origin);}
void SetTeam(gentity_t*e,char*team){if(placementFails&&e->s.number==0)return;e->client->sess.sessionTeam=!strcmp(team,"red")?TEAM_RED:!strcmp(team,"blue")?TEAM_BLUE:TEAM_SPECTATOR;ClientSpawn(e);}
qboolean ST_StaffBlocked(const gentity_t*e){(void)e;return qfalse;}
void G_FreeEntity(gentity_t*e){e->inuse=qfalse;}
void CalculateRanks(void){}
static void Player(int slot){gentity_t*e=&g_entities[slot];memset(e,0,sizeof(*e));e->s.number=slot;e->inuse=qtrue;e->client=&g_clients[slot];memset(e->client,0,sizeof(*e->client));e->client->pers.connected=CON_CONNECTED;e->client->sess.sessionTeam=TEAM_SPECTATOR;ClientSpawn(e); const char*oldArg=arg,*oldArg2=arg2;
 arg="hello";arg2="1";ST_EventClientCommand(&g_entities[slot]);arg=oldArg;arg2=oldArg2;
}
static STEProfile Profile(int slot){STEProfile p;memset(&p,0,sizeof(p));Com_sprintf(p.account,sizeof(p.account),"account%d",slot);Com_sprintf(p.name,sizeof(p.name),"Player %d",slot);Com_sprintf(p.team,sizeof(p.team),"team%d",slot/2);Com_sprintf(p.teamName,sizeof(p.teamName),"[Team %d]",slot/2);p.verified=1;return p;}
extern const STEventAccountAPI* GetSaberTrialsEventAccountAPI(void);
static void request(int slot,const char*op){level.time+=1000;arg=op;CHECK(ST_EventClientCommand(&g_entities[slot]));}
static void presentation(void){
 const STEventAccountAPI*api=GetSaberTrialsEventAccountAPI();unsigned char gen[16];STEProfile p;STEvent state;int i,target;
 level.maxclients=8;level.clients=g_clients;level.gametype=GT_TEAM;level.time=1000;ST_EventInit();
 Player(0);request(0,"status");CHECK(actions[0][0]==1);CHECK(!actions[0][1]&&!actions[0][2]&&!actions[0][3]);
 for(i=0;i<4;i++){
  Player(i);p=Profile(i);ST_StaffGenerationForClient(i,gen);CHECK(api->SetAccount(i,gen,&p));
  request(i,"status");CHECK(actions[i][1]&&!actions[i][2]&&!actions[i][3]);
  request(i,"join");CHECK(!actions[i][1]&&actions[i][2]&&!actions[i][3]);CHECK(ui[i][55][0]);
 }
 arg="start";ST_EventConsole();ST_EventFrame();
 CHECK(actions[0][3]&&!actions[0][2]);CHECK(ui[0][47][0]&&ui[0][48][0]);
 CHECK(ui[0][1][0]&&ui[0][2][0]&&!ui[0][3][0]);CHECK(ui[0][6][0]&&ui[0][7][0]&&!ui[0][8][0]);
 memset(ui[0],0,sizeof(ui[0]));memset(messages,0,sizeof(messages));request(0,"status");
 CHECK(ui[0][47][0]&&ui[0][48][0]); /* A client UI reload can request a full refresh. */
 arg="bracket";ST_EventClientCommand(&g_entities[0]);ST_EventFrame();CHECK(messages[0]<64);
 arg="ready";ST_EventClientCommand(&g_entities[0]);CHECK(!strcmp(ui[0][11],"Unready")); /* Opening a page must not swallow the first click. */
 request(0,"ready");CHECK(!strcmp(ui[0][11],"Ready"));
 arg="pause";ST_EventConsole();request(0,"status");
 CHECK(!actions[0][3]);CHECK(!strcmp(ui[0][55],"Staff pause. See console for the reason."));
 arg="resume";ST_EventConsole();ST_EventFrame();
 Player(4);p=Profile(0);Q_strncpyz(p.account,"reserve",sizeof(p.account));Q_strncpyz(p.name,"Reserve",sizeof(p.name));
 ST_StaffGenerationForClient(4,gen);CHECK(api->SetAccount(4,gen,&p));request(4,"join");
 request(4,"status");CHECK(!actions[4][3]);CHECK(!actions[4][5]);
 ST_EventDisconnect(0);g_clients[0].pers.connected=CON_DISCONNECTED;ST_EventFrame();request(4,"status");
 target=actions[4][5];CHECK(target==1);CHECK(ui[4][54][0]);
 CHECK(!actions[2][5]); /* Other team cannot see replacement action. */
 arg2="1";request(4,"substitute");arg2="";ST_EventFrame();
 CHECK(api->GetSnapshot(&state,sizeof(state)));CHECK(state.members[4].starter&&!state.members[0].starter);
 CHECK(!actions[4][5]&&actions[4][3]);
 api->ClearAccount(4);ST_EventFrame();CHECK(!actions[4][1]&&!actions[4][3]&&!actions[4][4]);
 arg="close";ST_EventConsole();CHECK(!ui[2][0][0]&&!ui[2][47][0]&&!actions[2][3]);
 puts("presentation pass");
}
int main(int argc,char**argv){
 const STEventAccountAPI*api=GetSaberTrialsEventAccountAPI();unsigned char gen[16];STEProfile p;int i;
 imports.Argv=Argv;imports.Cvar_VariableIntegerValue=Mode;imports.Cvar_Set=CvarSet;imports.SendServerCommand=Send;imports.LinkEntity=Link;imports.Print=Print;
 if(argc>1&&!strcmp(argv[1],"presentation")){presentation();return 0;}
 level.maxclients=8;level.clients=g_clients;level.gametype=GT_TEAM;level.time=1000;ST_EventInit();
 CHECK(ST_EventActive());
 for(i=0;i<4;i++){Player(i);p=Profile(i);ST_StaffGenerationForClient(i,gen);CHECK(api->SetAccount(i,gen,&p));arg="join";CHECK(ST_EventClientCommand(&g_entities[i]));}
 Player(7);p=Profile(0);ST_StaffGenerationForClient(7,gen);CHECK(!api->SetAccount(7,gen,&p)); /* duplicate connection */
 p=Profile(7);gen[0]=99;CHECK(!api->SetAccount(7,gen,&p));
 ST_StaffGenerationForClient(7,gen);p.verified=0;CHECK(!api->SetAccount(7,gen,&p));
 g_clients[1].pers.stTffaAssists=4;g_clients[1].pers.stTffaKills=3;g_clients[1].pers.stTffaDeaths=5;
 arg="start";ST_EventConsole();placementFails=1;ST_EventFrame();
 CHECK(g_clients[1].pers.stTffaAssists==0&&g_clients[1].pers.stTffaKills==0&&g_clients[1].pers.stTffaDeaths==0);
 CHECK(!ST_EventCanJoin(0,TEAM_SPECTATOR));CHECK(!ST_EventAllowCommand(0,"kill"));
 level.time+=1000;arg="ready";for(i=0;i<4;i++)ST_EventClientCommand(&g_entities[i]);CHECK(ST_EventBlocked(&g_entities[0]));
 placementFails=0;level.time+=1000;
 arg="ready";for(i=0;i<4;i++)ST_EventClientCommand(&g_entities[i]);ST_EventFrame();
 CHECK(!ST_EventBlocked(&g_entities[0]));
 arg="status";broadcasts=unicasts=0;ST_EventClientCommand(&g_entities[7]);
 CHECK(broadcasts==0&&unicasts<64);unicasts=0;ST_EventClientCommand(&g_entities[7]);CHECK(unicasts==0);
 g_entities[0].health=g_clients[0].ps.stats[STAT_HEALTH]=40;g_clients[0].ps.stats[STAT_ARMOR]=12;g_clients[0].ps.fd.forcePower=21;
 g_clients[0].ps.origin[0]=300;g_clients[0].ps.velocity[2]=80;
 g_clients[0].ps.ammo[AMMO_BLASTER]=7;g_clients[0].ps.weaponTime=800;
 g_clients[0].pers.stTffaAssists=2;g_clients[0].pers.stTffaKills=5;g_clients[0].pers.stTffaDeaths=3;
 g_clients[1].ps.powerups[PW_BATTLESUIT]=level.time+5000;
 g_clients[1].ps.fd.forcePowerDuration[FP_SPEED]=level.time+5000;
 ST_EventDisconnect(0);g_clients[0].pers.connected=CON_DISCONNECTED;
 ST_EventThink(&g_entities[1]);
 level.previousTime=level.time;level.time+=1000;ST_EventFrame();CHECK(ST_EventBlocked(&g_entities[1]));
 CHECK(g_clients[1].ps.powerups[PW_BATTLESUIT]==level.time+5000);
 CHECK(g_clients[1].ps.fd.forcePowerDuration[FP_SPEED]==level.time+5000);
 Player(4);p=Profile(0);ST_StaffGenerationForClient(4,gen);CHECK(api->SetAccount(4,gen,&p));ST_EventFrame();
 CHECK(g_entities[4].health==40&&g_clients[4].ps.stats[STAT_ARMOR]==12&&g_clients[4].ps.fd.forcePower==21);
 CHECK(g_clients[4].ps.origin[0]==300);CHECK(!ST_EventCanJoin(7,TEAM_RED));
 CHECK(g_clients[4].ps.ammo[AMMO_BLASTER]==7&&g_clients[4].ps.weaponTime==800);
 CHECK(g_clients[4].pers.stTffaAssists==2&&g_clients[4].pers.stTffaKills==5&&g_clients[4].pers.stTffaDeaths==3);
 level.time+=1000;arg="ready";for(i=1;i<=4;i++)ST_EventClientCommand(&g_entities[i]);ST_EventFrame();CHECK(!ST_EventBlocked(&g_entities[4]));CHECK(g_clients[4].ps.velocity[2]==80);
 /* Verified account moving to another team must invalidate the event session. */
 Q_strncpyz(p.team,"changed-team",sizeof(p.team));CHECK(!api->SetAccount(4,gen,&p));CHECK(ST_EventBlocked(&g_entities[4]));
 puts("adapter pass");return 0;
}
