/* Unit test of the production game module. Engine services are deterministic
 * substitutes; this executable never starts a server or loads a map. */
#include "g_local.h"
qboolean ST_EventActive(void){return qfalse;}
qboolean ST_EventCanJoin(int slot,int team){(void)slot;(void)team;return qfalse;}
int ST_EventStaff(const STVerifiedAction*a,STGameResult*r){(void)a;(void)r;return 0;}
#include <stdio.h>
#include <stdlib.h>

#define CHECK(x) do { if (!(x)) { fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x); exit(1); } } while(0)
level_locals_t level;
gentity_t g_entities[MAX_GENTITIES];
gclient_t g_clients[MAX_CLIENTS];
bgLoadedAnim_t bgAllAnims[MAX_ANIM_FILES];
static gameImport_t imports;
gameImport_t* trap=&imports;
static int roles[MAX_CLIENTS];
static unsigned char generations[MAX_CLIENTS][16];
static float obstruction=1;
static qboolean embedded=qfalse;
static int Role(int slot){return roles[slot];}
static int Generation(int slot,unsigned char out[16]){if(!generations[slot][0])return 0;memcpy(out,generations[slot],16);return 1;}
static void Link(sharedEntity_t* ent){(void)ent;}
static void Send(int slot,const char* message){(void)slot;(void)message;}
static int Contents(const vec3_t point,int pass){(void)point;(void)pass;return 0;}
static void Trace(trace_t* out,const vec3_t start,const vec3_t mins,const vec3_t maxs,const vec3_t end,int pass,int mask,int capsule,int flags,int lod){
 (void)mins;(void)maxs;(void)pass;(void)mask;(void)capsule;(void)flags;(void)lod;
 memset(out,0,sizeof(*out));out->fraction=VectorCompare(start,end)?1:obstruction;
 out->entityNum=ENTITYNUM_WORLD;out->startsolid=embedded;
}
void WP_ForcePowerStop(gentity_t* self,forcePowers_t power){(void)self;(void)power;}
void Pmove(pmove_t* move){(void)move;}
void BG_PlayerStateToEntityState(playerState_t* ps,entityState_t* s,qboolean snap){(void)ps;(void)s;(void)snap;}
void SetTeam(gentity_t* ent,char* team){(void)team;ent->client->sess.sessionTeam=TEAM_SPECTATOR;}
gentity_t* SelectSpawnPoint(vec3_t avoid,vec3_t origin,vec3_t angles,team_t team,qboolean bot){(void)avoid;(void)origin;(void)angles;(void)team;(void)bot;return NULL;}
static NORETURN void Fatal(int level,const char* fmt,...){(void)level;(void)fmt;exit(2);}
static void Print(const char* fmt,...){(void)fmt;}
NORETURN_PTR void (*Com_Error)(int,const char*,...)=Fatal;
void (*Com_Printf)(const char*,...)=Print;
extern const STGameAPI* GetSaberTrialsStaffAPI(const STStaffImports*);
static void Player(int slot,float x,float y){
 gentity_t* e=&g_entities[slot];memset(e,0,sizeof(*e));e->s.number=slot;e->inuse=qtrue;e->health=100;e->client=&g_clients[slot];
 memset(e->client,0,sizeof(*e->client));e->client->pers.connected=CON_CONNECTED;e->client->ps.origin[0]=x;e->client->ps.origin[1]=y;
 e->client->ps.viewheight=24;VectorSet(e->r.mins,-16,-16,-24);VectorSet(e->r.maxs,16,16,40);
 e->r.contents=CONTENTS_BODY;generations[slot][0]=(unsigned char)(slot+1);
 Com_sprintf(e->client->pers.netname,MAX_NETNAME,"Player %d",slot);
}
int main(void){
 STStaffImports staff={ST_STAFF_API_VERSION,sizeof(STStaffImports),Role,Generation};
 const STGameAPI* api;STVerifiedAction a={0};STGameResult result;STTargetRef target;
 imports.Trace=Trace;imports.PointContents=Contents;imports.LinkEntity=imports.UnlinkEntity=Link;imports.SendServerCommand=Send;
 level.maxclients=4;level.gametype=GT_FFA;Player(0,0,0);Player(1,100,0);roles[0]=3;
 api=GetSaberTrialsStaffAPI(&staff);CHECK(api!=NULL);
 a.actorSlot=0;a.role=3;strcpy(a.account,"owner");a.command=ST_CMD_LOGOUT+1;
 // A live player straight ahead is selected using the actor's view.
 CHECK(api->Execute(&a,&result)&&result.ok);CHECK(!strncmp(result.message,"1 ",2));
 // A solid wall, embedded viewpoint or empty aim never chooses somebody.
 obstruction=0.001f;CHECK(api->Execute(&a,&result)&&!result.ok);obstruction=1;
 embedded=qtrue;CHECK(api->Execute(&a,&result)&&!result.ok);embedded=qfalse;
 g_clients[1].ps.origin[1]=100;CHECK(api->Execute(&a,&result)&&!result.ok);g_clients[1].ps.origin[1]=0;
 // Freeze a bot, then resolve it despite the intentional removal of collision.
 g_entities[1].r.svFlags|=SVF_BOT;CHECK(api->ResolveTarget("#1",&target));
 a.command=ST_CMD_FREEZE;a.target=target;CHECK(api->Execute(&a,&result)&&result.ok);CHECK(ST_StaffBlocked(&g_entities[1]));CHECK(g_entities[1].r.contents==0);
 a.command=ST_CMD_LOGOUT+1;a.target=(STTargetRef){0};CHECK(api->Execute(&a,&result)&&result.ok);CHECK(!strncmp(result.message,"1 ",2));
 a.command=ST_CMD_UNFREEZE;a.target=target;CHECK(api->Execute(&a,&result)&&result.ok);CHECK(!ST_StaffBlocked(&g_entities[1]));
 // A recycled slot, peer, duel participant and self remain protected.
 a.command=ST_CMD_FREEZE;generations[1][0]++;CHECK(api->Execute(&a,&result)&&!result.ok);generations[1][0]--;
 roles[1]=3;CHECK(api->Execute(&a,&result)&&!result.ok);roles[1]=0;
 g_clients[1].ps.duelInProgress=qtrue;CHECK(api->Execute(&a,&result)&&!result.ok);g_clients[1].ps.duelInProgress=qfalse;
 CHECK(api->ResolveTarget("#0",&a.target));CHECK(api->Execute(&a,&result)&&!result.ok);
 a.command=ST_CMD_LOGOUT+1;a.target=(STTargetRef){0};roles[0]=0;CHECK(api->Execute(&a,&result)&&!result.ok);roles[0]=3;
 // Nearest visible player wins, even if somebody else is frozen behind them.
 Player(2,60,0);CHECK(api->Execute(&a,&result)&&result.ok);CHECK(!strncmp(result.message,"2 ",2));
 // Looking away does not reuse a previous target; pitch/yaw drive a fresh ray.
 g_clients[0].ps.viewangles[YAW]=180;CHECK(api->Execute(&a,&result)&&!result.ok);
 g_clients[0].ps.viewangles[YAW]=90;Player(3,0,100);CHECK(api->Execute(&a,&result)&&result.ok);CHECK(!strncmp(result.message,"3 ",2));
 g_clients[0].ps.viewangles[YAW]=0;g_clients[0].ps.viewangles[PITCH]=-45;
 g_clients[1].ps.origin[2]=124;CHECK(api->Execute(&a,&result)&&result.ok);CHECK(!strncmp(result.message,"1 ",2));
 // Freeze holds a midair bot's full position even when it supplies movement.
 CHECK(api->ResolveTarget("#1",&a.target));a.command=ST_CMD_FREEZE;
 CHECK(api->Execute(&a,&result)&&result.ok);g_clients[1].ps.velocity[2]=-400;g_clients[1].pers.cmd.upmove=127;
 CHECK(ST_StaffThink(&g_entities[1]));CHECK(g_clients[1].ps.origin[2]==124&&VectorLengthSquared(g_clients[1].ps.velocity)==0);
 api->Revoke("owner",0);CHECK(!ST_StaffBlocked(&g_entities[1]));
 puts("PASS: aim, empty space, walls, frozen bot, unfreeze, recycled slots and role/duel protections");return 0;
}
