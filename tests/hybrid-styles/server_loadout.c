/* Production server adapter, with engine-only services supplied by the fixture. */
#include "st_hybrid.h"
#include "st_combat_core.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
enum {SABER_SINGLE=1,GT_SIEGE=7,FP_SABER_OFFENSE=0,ERR_DROP=1,
 ST_TOURNAMENT_PAUSED=3,ST_STAFF_STAT=1,ST_STAFF_FROZEN=2,ST_STAFF_GHOST=3,
 TEAM_SPECTATOR=3,SS_STRONG=3,LS_A_TL2BR=10,LS_A_T2B=16};
typedef int qboolean;
enum {qfalse,qtrue};
typedef struct {int serverTime;} usercmd_t;
typedef struct {char model[16];int type,numBlades;unsigned stylesForbidden,stylesLearned;} saberInfo_t;
typedef struct {STH_State stHybrid;int commandTime,stCombatFlags,stats[4],saberInFlight,saberMove,torsoAnim;
 struct {int forcePowerLevel[4],saberAnimLevel,saberAnimLevelBase,saberDrawAnimLevel;} fd;} playerState_t;
typedef struct {playerState_t ps;saberInfo_t saber[2];int siegeClass,saberCycleQueue;
 struct {int sessionTeam,stSaberStyle;} sess;struct {usercmd_t cmd;}pers;} gclient_t;
typedef struct {gclient_t* client;int localAnimIndex,health;} gentity_t;
static gentity_t g_entities[2];
static struct {int integer;} g_hybridStyles;
static struct {int gametype,stTournamentPhase,time;} level;
static struct {unsigned saberStance;} bgSiegeClasses[2];
static struct {int anims[1];} bgAllAnims[2];
static void error(int code,const char* text,...){(void)code;fprintf(stderr,"Unexpected drop: %s\n",text);exit(2);}
static void send(int client,const char* text){(void)client;(void)text;}
static struct {void (*Error)(int,const char*,...);void (*SendServerCommand)(int,const char*);} services={error,send},*trap=&services;
static const char* Info_ValueForKey(const char* info,const char* key) {
 static char out[4][64];static unsigned index;char* result=out[(index++)%4];const char* p=info;
 result[0]=0;
 while(*p) {const char* k;const char* v;size_t n;
  if(*p=='\\')p++;k=p;while(*p&&*p!='\\')p++;n=(size_t)(p-k);
  if(*p)p++;v=p;while(*p&&*p!='\\')p++;
  if(strlen(key)==n&&!strncmp(k,key,n)){size_t len=(size_t)(p-v);if(len>63)len=63;memcpy(result,v,len);result[len]=0;return result;}
 }return result;
}
static int ST_StanceAssetsAvailable(void){return 1;}
static int STH_AnimationsValid(const int* a){return a!=NULL;}
static int STH_AnimStyle(int a){return a==99?5:0;}
static void BG_ST_HybridStopped(playerState_t* p,const usercmd_t* c,unsigned guards){(void)p;(void)c;(void)guards;}
#include "g_st_hybrid.inc"
static int checks;
#define CHECK(x) do{++checks;if(!(x)){fprintf(stderr,"server:%d %s\n",__LINE__,#x);exit(1);}}while(0)
int main(void) {
 gclient_t client={0};gentity_t* ent=&g_entities[0];STH_State* s=&client.ps.stHybrid;
 ent->client=&client;ent->health=100;client.ps.fd.forcePowerLevel[0]=3;
 client.saber[0].type=SABER_SINGLE;client.saber[0].numBlades=1;strcpy(client.saber[0].model,"single");
 client.ps.fd.saberAnimLevel=client.ps.fd.saberAnimLevelBase=1;g_hybridStyles.integer=1;
 G_ST_HybridSpawn(ent,"\\saberStyleLoadout\\2 5 6");
 CHECK(s->selectedStyle==2&&!s->style&&client.ps.fd.saberAnimLevel==2);
 CHECK(s->loadout[0]==2&&s->loadout[1]==5&&s->loadout[2]==6);
 G_ST_HybridUserinfo(ent,"\\saberStyleLoadout\\2 5 6\\name\\changed");
 CHECK(s->requestedSelection==2); /* Unrelated userinfo must not reset the cycle. */
 CHECK(G_ST_HybridCycle(ent));CHECK(s->requestedSelection==5);
 G_ST_HybridUserinfo(ent,"\\saberStyleLoadout\\2 5 6\\name\\changed again");
 CHECK(s->requestedSelection==5);
 CHECK(G_ST_HybridCycle(ent));CHECK(s->requestedSelection==6);
 CHECK(STH_ApplySelection(s,1));
 CHECK(G_ST_HybridCycle(ent));CHECK(s->requestedSelection==2);
 G_ST_HybridRememberStyle(ent);
 memset(s,0,sizeof(*s));
 G_ST_HybridSpawn(ent,"\\saberStyleLoadout\\2 5 6");
 CHECK(s->selectedStyle==6&&s->style==6&&client.ps.fd.saberAnimLevel==3);
 CHECK(G_ST_HybridCycle(ent));CHECK(s->requestedSelection==2);
 G_ST_HybridSpawn(ent,"\\saberStyleLoadout\\2 5 4");
 CHECK(s->selectedStyle==2&&!s->style&&client.ps.fd.saberAnimLevel==2);
 /* A model with its own rig cannot be given humanoid hybrid animation IDs. */
 ent->localAnimIndex=2;G_ST_HybridUserinfo(ent,"\\saberStyleLoadout\\4 5 6");
 CHECK(s->allowedMask==0&&s->availableMask==14&&s->requestedSelection==1);
 puts("server loadout adapter passed");return 0;
}
