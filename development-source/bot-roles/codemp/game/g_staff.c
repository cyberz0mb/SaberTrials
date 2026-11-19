#include "g_local.h"
#include "g_staff.h"
#include <stdlib.h>
#include <math.h>
typedef struct {
 int mode; /* 1 frozen, 2 ghost. Never populated from userinfo. */
 char owner[65]; int actorSlot; vec3_t origin; int contents; int svFlags; int eFlags;
} staffState_t;
static staffState_t states[MAX_CLIENTS];
static const STStaffImports* engine;
int ST_StaffRoleForClient(int slot){return engine?engine->RoleForClient(slot):0;}
int ST_StaffGenerationForClient(int slot,unsigned char generation[16]){return engine?engine->GenerationForClient(slot,generation):0;}
static void StaffTrace(trace_t* result,const vec3_t start,const vec3_t mins,const vec3_t maxs,const vec3_t end,int pass,int mask){trap->Trace(result,start,mins,maxs,end,pass,mask,qfalse,0,0);}
static qboolean Player(const gentity_t* ent){return ent&&ent->inuse&&ent->client&&ent->s.number>=0&&ent->s.number<MAX_CLIENTS&&ent->client->pers.connected==CON_CONNECTED;}
qboolean ST_StaffBlocked(const gentity_t* ent){return Player(ent)&&states[ent->s.number].mode!=0;}
static qboolean Competing(const gentity_t* ent){
 if(!Player(ent))return qtrue;
 if(ST_EventActive()&&ST_EventCanJoin(ent->s.number,ent->client->sess.sessionTeam)&&ent->client->sess.sessionTeam!=TEAM_SPECTATOR)return qtrue;
 if(ent->client->ps.duelInProgress)return qtrue;
 if((level.gametype==GT_DUEL||level.gametype==GT_POWERDUEL)&&ent->client->sess.sessionTeam!=TEAM_SPECTATOR)return qtrue;
 if(level.stTournamentPhase==ST_TOURNAMENT_RUNNING&&(level.stTournamentActiveA==ent->s.number||level.stTournamentActiveB==ent->s.number))return qtrue;
 return qfalse;
}
static qboolean Carrier(const gentity_t* ent){return ent->client->ps.powerups[PW_REDFLAG]||ent->client->ps.powerups[PW_BLUEFLAG]||ent->client->ps.powerups[PW_NEUTRALFLAG]||ent->client->ps.isJediMaster||ent->client->ps.m_iVehicleNum;}
static qboolean Safe(gentity_t* subject,const vec3_t point){
 trace_t tr;int i;vec3_t foot;
 for(i=0;i<3;i++)if(!isfinite(point[i])||fabsf(point[i])>131072)return qfalse;
 trap->Trace(&tr,point,subject->r.mins,subject->r.maxs,point,subject->s.number,MASK_PLAYERSOLID|CONTENTS_LAVA|CONTENTS_SLIME|CONTENTS_TRIGGER,qfalse,0,0);
 if(tr.startsolid||tr.allsolid||tr.fraction<1)return qfalse;
 VectorCopy(point,foot);foot[2]+=subject->r.mins[2];
 if((trap->PointContents(point,subject->s.number)|trap->PointContents(foot,subject->s.number))&(CONTENTS_LAVA|CONTENTS_SLIME|CONTENTS_TRIGGER|CONTENTS_SOLID))return qfalse;
 // No teleport into an active private duel or competition's immediate space.
 for(i=0;i<level.maxclients;i++){gentity_t* other=&g_entities[i];vec3_t d;if(other==subject||!Player(other)||other->client->sess.sessionTeam==TEAM_SPECTATOR)continue;VectorSubtract(point,other->client->ps.origin,d);if(Competing(other)&&VectorLengthSquared(d)<256*256)return qfalse;}
 return qtrue;
}
static void Place(gentity_t* ent,const vec3_t origin){
 trap->UnlinkEntity((sharedEntity_t*)ent);VectorCopy(origin,ent->client->ps.origin);VectorClear(ent->client->ps.velocity);ent->client->ps.pm_time=0;ent->client->ps.pm_flags&=~PMF_ALL_TIMES;ent->client->ps.groundEntityNum=ENTITYNUM_NONE;ent->client->ps.eFlags^=EF_TELEPORT_BIT;
 BG_PlayerStateToEntityState(&ent->client->ps,&ent->s,qtrue);VectorCopy(origin,ent->r.currentOrigin);trap->LinkEntity((sharedEntity_t*)ent);
}
static qboolean Near(gentity_t* subject,const vec3_t center,vec3_t result){
 static const float offsets[8][2]={{96,0},{-96,0},{0,96},{0,-96},{96,96},{-96,96},{96,-96},{-96,-96}};int i;
 for(i=0;i<8;i++){VectorCopy(center,result);result[0]+=offsets[i][0];result[1]+=offsets[i][1];if(Safe(subject,result))return qtrue;}return qfalse;
}
static void CancelPowers(gentity_t* ent){int p;for(p=0;p<NUM_FORCE_POWERS;p++)if(ent->client->ps.fd.forcePowersActive&(1<<p))WP_ForcePowerStop(ent,(forcePowers_t)p);ent->client->ps.fd.forceGripBeingGripped=0;ent->client->ps.forceGripChangeMovetype=0;ent->client->ps.saberHolstered=2;if(ent->client->ps.saberEntityNum>0&&ent->client->ps.saberEntityNum<ENTITYNUM_WORLD){gentity_t* saber=&g_entities[ent->client->ps.saberEntityNum];saber->r.contents=0;trap->UnlinkEntity((sharedEntity_t*)saber);}ent->client->ps.saberMove=LS_READY;ent->client->ps.weaponTime=0;ent->client->ps.saberBlocked=0;ent->client->jetPackOn=qfalse;}
void ST_StaffClearClient(int slot){
 gentity_t* ent;staffState_t saved;vec3_t destination,angles;
 if(slot<0||slot>=MAX_CLIENTS)return;saved=states[slot];memset(&states[slot],0,sizeof(states[slot]));if(!saved.mode)return;ent=&g_entities[slot];if(!ent->client)return;
 ent->client->ps.stats[ST_STAFF_STAT]=0;ent->client->noclip=qfalse;ent->client->ps.pm_type=PM_NORMAL;ent->client->ps.eFlags=(ent->client->ps.eFlags&~EF_NODRAW)|(saved.eFlags&EF_NODRAW);ent->r.svFlags=(ent->r.svFlags&~SVF_NOCLIENT)|(saved.svFlags&SVF_NOCLIENT);ent->r.contents=saved.contents;
 VectorClear(ent->client->ps.velocity);ent->client->ps.pm_time=0;ent->client->ps.pm_flags&=~PMF_ALL_TIMES;CancelPowers(ent);
 if(!Player(ent))return;
 if(saved.mode==2||!Safe(ent,ent->client->ps.origin)){
  if(Safe(ent,saved.origin))Place(ent,saved.origin);
  else {gentity_t* spawn=SelectSpawnPoint(saved.origin,destination,angles,ent->client->sess.sessionTeam,qfalse);if(spawn&&Safe(ent,destination))Place(ent,destination);else SetTeam(ent,"spectator");}
 }else {Place(ent,ent->client->ps.origin);}
 trap->SendServerCommand(slot,"print \"Staff movement restriction cleared.\n\"");
}
void ST_StaffResetAll(void){int i;for(i=0;i<MAX_CLIENTS;i++)ST_StaffClearClient(i);memset(states,0,sizeof(states));}
qboolean ST_StaffThink(gentity_t* ent){
 staffState_t* state;pmove_t move;int serverTime;
 if(!ST_StaffBlocked(ent))return qfalse;state=&states[ent->s.number];CancelPowers(ent);
 memset(&move,0,sizeof(move));move.ps=&ent->client->ps;move.cmd=ent->client->pers.cmd;move.cmd.buttons&=BUTTON_TALK;move.cmd.generic_cmd=0;
 serverTime=move.cmd.serverTime;if(serverTime>level.time+200)serverTime=level.time+200;if(serverTime<level.time-1000)serverTime=level.time-1000;move.cmd.serverTime=serverTime;
 move.trace=StaffTrace;move.pointcontents=trap->PointContents;move.tracemask=MASK_PLAYERSOLID;move.gametype=level.gametype;
 // Shared movement reads entity and animation data before handling PM_FREEZE/PM_NOCLIP.
 move.baseEnt=(bgEntity_t*)g_entities;move.entSize=sizeof(gentity_t);
 move.animations=bgAllAnims[ent->localAnimIndex].anims;move.nonHumanoid=ent->localAnimIndex>1;
 VectorCopy(ent->modelScale,move.modelScale);
 ent->client->ps.stats[ST_STAFF_STAT]=state->mode;ent->client->ps.pm_type=state->mode==1?PM_FREEZE:PM_NOCLIP;ent->client->ps.speed=400;
 if(state->mode==1){move.cmd.forwardmove=move.cmd.rightmove=move.cmd.upmove=0;VectorCopy(state->origin,ent->client->ps.origin);VectorClear(ent->client->ps.velocity);}
 else {ent->client->ps.eFlags|=EF_NODRAW;ent->r.svFlags|=SVF_NOCLIENT;}
 Pmove(&move);
 if(state->mode==1){VectorCopy(state->origin,ent->client->ps.origin);VectorClear(ent->client->ps.velocity);}
 ent->client->ps.groundEntityNum=ENTITYNUM_NONE;ent->r.contents=0;BG_PlayerStateToEntityState(&ent->client->ps,&ent->s,qtrue);VectorCopy(ent->client->ps.origin,ent->r.currentOrigin);trap->LinkEntity((sharedEntity_t*)ent);return qtrue;
}
void ST_StaffFrame(void){int i;for(i=0;i<MAX_CLIENTS;i++)if(states[i].mode)ST_StaffThink(&g_entities[i]);}
static int Resolve(const char* text,STTargetRef* out){
 int i,found=-1;char input[MAX_NETNAME],name[MAX_NETNAME];char* end;long slot;
 if(!engine||!text||!out||strlen(text)>=MAX_NETNAME)return 0;
 if(text[0]=='#'){slot=strtol(text+1,&end,10);if(!text[1]||*end||slot<0||slot>=level.maxclients)return 0;found=(int)slot;}
 else {
  Q_strncpyz(input,text,sizeof(input));Q_CleanStr(input);
  // Prefer one exact visible-name match, then one substring match. Never choose arbitrarily.
  for(i=0;i<level.maxclients;i++){if(!Player(&g_entities[i]))continue;Q_strncpyz(name,g_entities[i].client->pers.netname,sizeof(name));Q_CleanStr(name);if(!Q_stricmp(name,input)){if(found>=0)return 0;found=i;}}
  if(found<0)for(i=0;i<level.maxclients;i++){if(!Player(&g_entities[i]))continue;Q_strncpyz(name,g_entities[i].client->pers.netname,sizeof(name));Q_CleanStr(name);Q_strlwr(name);Q_strlwr(input);if(strstr(name,input)){if(found>=0)return 0;found=i;}}
  if(found<0){slot=strtol(text,&end,10);if(*text&&!*end&&slot>=0&&slot<level.maxclients)found=(int)slot;}
 }
 if(found<0||!Player(&g_entities[found])||!engine->GenerationForClient(found,out->generation))return 0;out->slot=found;return 1;
}
/* Frozen players have contents=0. Intersect their bounds as well as live
 * players, clipped by the world trace, so unfreeze can still aim at them. */
static qboolean AimBounds(const vec3_t start,const vec3_t delta,const gentity_t* ent,float limit,float* distance){
 float low=0,high=limit;int axis;
 for(axis=0;axis<3;axis++){
  float min=ent->client->ps.origin[axis]+ent->r.mins[axis],max=ent->client->ps.origin[axis]+ent->r.maxs[axis];
  float a,b;
  if(fabsf(delta[axis])<0.00001f){if(start[axis]<min||start[axis]>max)return qfalse;continue;}
  a=(min-start[axis])/delta[axis];b=(max-start[axis])/delta[axis];if(a>b){float swap=a;a=b;b=swap;}
  if(a>low)low=a;if(b<high)high=b;if(low>high)return qfalse;
 }
 if(low>=limit)return qfalse;*distance=low;return qtrue;
}
static int ResolveAim(gentity_t* actor,STTargetRef* out){
 vec3_t start,end,forward,delta;trace_t tr;float nearest;int i,found=-1;
 VectorCopy(actor->client->ps.origin,start);start[2]+=actor->client->ps.viewheight;
 AngleVectors(actor->client->ps.viewangles,forward,NULL,NULL);VectorScale(forward,8192,delta);VectorAdd(start,delta,end);
 StaffTrace(&tr,start,NULL,NULL,end,actor->s.number,CONTENTS_SOLID|CONTENTS_BODY);
 if(tr.startsolid||tr.allsolid)return 0;
 nearest=tr.fraction;
 if(tr.entityNum>=0&&tr.entityNum<level.maxclients&&tr.entityNum!=actor->s.number&&Player(&g_entities[tr.entityNum]))found=tr.entityNum;
 for(i=0;i<level.maxclients;i++){
  gentity_t* candidate=&g_entities[i];float distance;
  if(i==actor->s.number||!Player(candidate)||candidate->health<=0||candidate->client->sess.sessionTeam==TEAM_SPECTATOR||states[i].mode==2)continue;
  if(AimBounds(start,delta,candidate,nearest,&distance)){nearest=distance;found=i;}
 }
 if(found<0||!engine->GenerationForClient(found,out->generation))return 0;
 out->slot=found;return 1;
}
static int Execute(const STVerifiedAction* action,STGameResult* result){
 gentity_t* actor;gentity_t* target=NULL;staffState_t* state;vec3_t point;unsigned char generation[16];int i;
 if(!action||!result)return 0;memset(result,0,sizeof(*result));Q_strncpyz(result->message,"Action denied",sizeof(result->message));
 if(!engine||action->actorSlot<0||action->actorSlot>=level.maxclients||engine->RoleForClient(action->actorSlot)!=action->role||action->role<1)return 1;
 actor=&g_entities[action->actorSlot];if(!Player(actor))return 1;
 if(action->command==ST_CMD_TOURNAMENT)return ST_EventStaff(action,result);
 if(action->command==ST_CMD_GHOST_OFF){if(states[actor->s.number].mode!=2){Q_strncpyz(result->message,"Ghost is already off",sizeof(result->message));return 1;}ST_StaffClearClient(actor->s.number);result->ok=1;Q_strncpyz(result->message,"Ghost off",sizeof(result->message));return 1;}
 if(ST_StaffBlocked(actor)||Competing(actor)||Carrier(actor)||actor->health<=0||actor->client->sess.sessionTeam==TEAM_SPECTATOR){Q_strncpyz(result->message,"Leave combat, objectives and restricted movement before intervening",sizeof(result->message));return 1;}
 if(action->command==ST_CMD_RESOLVE_AIM){
  STTargetRef aimed;char hex[33];
  if(!ResolveAim(actor,&aimed)){Q_strncpyz(result->message,"No player under your aim. Aim directly at a visible player, or use freeze/unfreeze #client-ID",sizeof(result->message));return 1;}
  for(i=0;i<16;i++)Com_sprintf(hex+i*2,3,"%02x",aimed.generation[i]);
  result->ok=1;Com_sprintf(result->message,sizeof(result->message),"%d %s",aimed.slot,hex);return 1;
 }
 if(action->command==ST_CMD_FREEZE||action->command==ST_CMD_UNFREEZE||action->command==ST_CMD_SUMMON||action->command==ST_CMD_TRAVEL_PLAYER){
  int slot=action->target.slot;if(slot<0||slot>=level.maxclients||slot==actor->s.number||!engine->GenerationForClient(slot,generation)||memcmp(generation,action->target.generation,16)){Q_strncpyz(result->message,"Cannot target yourself or a player who has disconnected",sizeof(result->message));return 1;}target=&g_entities[slot];
  if(!Player(target)||target->health<=0||target->client->sess.sessionTeam==TEAM_SPECTATOR){Q_strncpyz(result->message,"Target must be alive and playing",sizeof(result->message));return 1;}
  if(engine->RoleForClient(slot)>=action->role){Q_strncpyz(result->message,"Cannot target staff of equal or higher rank",sizeof(result->message));return 1;}
  if(Competing(target)||Carrier(target)){Q_strncpyz(result->message,"Target is in a protected duel, tournament, vehicle or objective role",sizeof(result->message));return 1;}
 }
 if(action->command==ST_CMD_UNFREEZE){if(states[target->s.number].mode!=1){Q_strncpyz(result->message,"That player is not frozen",sizeof(result->message));return 1;}ST_StaffClearClient(target->s.number);}
 else if(action->command==ST_CMD_FREEZE||action->command==ST_CMD_GHOST_ON){
  gentity_t* subject=target?target:actor;if(ST_StaffBlocked(subject)||!Safe(subject,subject->client->ps.origin))return 1;
  if(subject->client->ps.saberInFlight){Q_strncpyz(result->message,"Recall the thrown saber first",sizeof(result->message));return 1;}
  state=&states[subject->s.number];state->mode=target?1:2;state->actorSlot=action->actorSlot;Q_strncpyz(state->owner,action->account,sizeof(state->owner));VectorCopy(subject->client->ps.origin,state->origin);state->contents=subject->r.contents;state->svFlags=subject->r.svFlags;state->eFlags=subject->client->ps.eFlags;ST_StaffThink(subject);
 }
 else if(action->command==ST_CMD_SUMMON||action->command==ST_CMD_TRAVEL_PLAYER){gentity_t* subject=action->command==ST_CMD_SUMMON?target:actor;gentity_t* destination=action->command==ST_CMD_SUMMON?actor:target;if(ST_StaffBlocked(target)||!Near(subject,destination->client->ps.origin,point))return 1;Place(subject,point);}
 else if(action->command==ST_CMD_TRAVEL_COORDS){
  for(i=0;i<3;i++){char* end;point[i]=strtof(action->args[i],&end);if(!*action->args[i]||*end||!isfinite(point[i]))return 1;}if(!Safe(actor,point))return 1;Place(actor,point);
 }else return 1;
 result->ok=1;
 if(action->command==ST_CMD_FREEZE||action->command==ST_CMD_UNFREEZE)Com_sprintf(result->message,sizeof(result->message),"%s #%d (%s)",action->command==ST_CMD_FREEZE?"Frozen":"Unfrozen",target->s.number,target->client->pers.netname);
 else Q_strncpyz(result->message,"Staff action completed",sizeof(result->message));return 1;
}
static void Revoke(const char* id,int actorSlot){int i;for(i=0;i<MAX_CLIENTS;i++)if(states[i].mode&&!strcmp(states[i].owner,id)&&(actorSlot<0||states[i].actorSlot==actorSlot))ST_StaffClearClient(i);}
Q_EXPORT const STGameAPI* GetSaberTrialsStaffAPI(const STStaffImports* imports){
 static const STGameAPI api={ST_STAFF_API_VERSION,sizeof(STGameAPI),Execute,Resolve,Revoke,ST_StaffResetAll};
 if(!imports||imports->version!=ST_STAFF_API_VERSION||imports->size!=sizeof(STStaffImports)||!imports->RoleForClient||!imports->GenerationForClient)return NULL;engine=imports;return &api;
}
