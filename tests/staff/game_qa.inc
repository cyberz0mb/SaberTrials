// Included only by the isolated QA game. All mutations are test-fixture setup.
static int staffQATouches;
extern qboolean ST_QAPush(gentity_t* check,gentity_t* pusher,vec3_t move,vec3_t amove);
static void ST_QATouch(gentity_t* self,gentity_t* other,trace_t* trace) { staffQATouches++; }
static qboolean ST_StaffQA(void) {
 char cmd[64],op[64],value[64];int i,slot;
 trap->Argv(0,cmd,sizeof(cmd));if(Q_stricmp(cmd,"st_staffqa"))return qfalse;
 trap->Argv(1,op,sizeof(op));trap->Argv(2,value,sizeof(value));slot=atoi(value);
 if(slot<0||slot>=level.maxclients)return qtrue;
 if(!Q_stricmp(op,"time")){Com_Printf("STAFF_CLOCK level=%d\n",level.time);return qtrue;}
 if(!Q_stricmp(op,"place")){vec3_t p;for(i=0;i<3;i++){trap->Argv(i+3,value,sizeof(value));p[i]=atof(value);}VectorCopy(p,g_entities[slot].client->ps.origin);VectorCopy(p,g_entities[slot].r.currentOrigin);VectorClear(g_entities[slot].client->ps.velocity);trap->LinkEntity((sharedEntity_t*)&g_entities[slot]);}
 else if(!Q_stricmp(op,"hit")){int attacker,damage;trap->Argv(3,value,sizeof(value));attacker=atoi(value);trap->Argv(4,value,sizeof(value));damage=atoi(value);if(attacker>=0&&attacker<level.maxclients)G_Damage(&g_entities[slot],&g_entities[attacker],&g_entities[attacker],NULL,NULL,damage,DAMAGE_NO_ARMOR,MOD_BLASTER);}
 else if(!Q_stricmp(op,"health")){trap->Argv(3,value,sizeof(value));g_entities[slot].health=g_entities[slot].client->ps.stats[STAT_HEALTH]=atoi(value);}
 else if(!Q_stricmp(op,"duel")){int other=slot==1?2:1;trap->Argv(3,value,sizeof(value));g_entities[slot].client->ps.duelInProgress=g_entities[other].client->ps.duelInProgress=atoi(value);g_entities[slot].client->ps.duelIndex=other;g_entities[other].client->ps.duelIndex=slot;g_entities[slot].client->ps.duelTime=g_entities[other].client->ps.duelTime=level.time+30000;}
 else if(!Q_stricmp(op,"objective")){trap->Argv(3,value,sizeof(value));g_entities[slot].client->ps.powerups[PW_REDFLAG]=atoi(value)?level.time+60000:0;}
 else if(!Q_stricmp(op,"tournament")){trap->Argv(3,value,sizeof(value));level.stTournamentPhase=atoi(value)?ST_TOURNAMENT_RUNNING:ST_TOURNAMENT_OFF;level.stTournamentActiveA=slot;level.stTournamentActiveB=-1;}
 else if(!Q_stricmp(op,"disarm")){g_entities[slot].client->ps.weapon=WP_MELEE;g_entities[slot].client->ps.stats[STAT_WEAPONS]=1<<WP_MELEE;g_entities[slot].client->ps.stats[STAT_ARMOR]=0;g_entities[slot].client->ps.fd.forcePowersActive=0;g_entities[slot].client->ps.fd.forcePowersKnown=0;}
 else if(!Q_stricmp(op,"missile")){
  vec3_t start,dir;gentity_t* missile;int target;
  trap->Argv(3,value,sizeof(value));target=atoi(value);if(target<0||target>=level.maxclients)return qtrue;
  VectorCopy(g_entities[target].client->ps.origin,start);start[1]+=100;
  VectorSet(dir,0,-1,0);missile=CreateMissile(start,dir,50,5000,&g_entities[slot],qfalse);
  missile->classname="staff_qa_missile";missile->s.weapon=WP_BLASTER;missile->damage=20;
  missile->dflags=DAMAGE_NO_ARMOR;missile->methodOfDeath=MOD_BLASTER;missile->clipmask=MASK_SHOT;
  {trace_t path;trap->Trace(&path,start,NULL,NULL,g_entities[target].client->ps.origin,slot,MASK_SHOT,qfalse,0,0);Com_Printf("STAFF_MISSILE target=%d trace=%d fraction=%.2f\n",target,path.entityNum,path.fraction);}
 }
 else if(!Q_stricmp(op,"trigger")){
  gentity_t* trigger=G_Spawn();int before=staffQATouches;
  VectorCopy(g_entities[slot].client->ps.origin,trigger->r.currentOrigin);
  VectorSet(trigger->r.mins,-32,-32,-32);VectorSet(trigger->r.maxs,32,32,48);
  trigger->r.contents=CONTENTS_TRIGGER;trigger->touch=ST_QATouch;trap->LinkEntity((sharedEntity_t*)trigger);
  G_TouchTriggers(&g_entities[slot]);Com_Printf("STAFF_CONTACT touches=%d\n",staffQATouches-before);G_FreeEntity(trigger);
 }
 else if(!Q_stricmp(op,"obstacle")){
  gentity_t* obstacle=G_Spawn();vec3_t p;for(i=0;i<3;i++){trap->Argv(i+3,value,sizeof(value));p[i]=atof(value);}
  VectorCopy(p,obstacle->r.currentOrigin);VectorSet(obstacle->r.mins,-32,-32,-32);VectorSet(obstacle->r.maxs,32,32,48);
  obstacle->classname="staff_qa_obstacle";obstacle->r.contents=CONTENTS_SOLID;trap->LinkEntity((sharedEntity_t*)obstacle);
 }
 else if(!Q_stricmp(op,"clearobstacles")){for(i=MAX_CLIENTS;i<level.num_entities;i++)if(g_entities[i].inuse&&g_entities[i].classname&&!strcmp(g_entities[i].classname,"staff_qa_obstacle"))G_FreeEntity(&g_entities[i]);}
 else if(!Q_stricmp(op,"push")){
  gentity_t* pusher=G_Spawn();vec3_t move={0,8,0},angles={0,0,0};float before=g_entities[slot].client->ps.origin[1];
  qboolean allowed=ST_QAPush(&g_entities[slot],pusher,move,angles);
  Com_Printf("STAFF_PUSH allowed=%d dy=%.2f\n",allowed,g_entities[slot].client->ps.origin[1]-before);G_FreeEntity(pusher);
 }
 else if(!Q_stricmp(op,"pickup")){
  gentity_t* item=G_Spawn();trace_t tr;int before=g_entities[slot].health;memset(&tr,0,sizeof(tr));
  item->item=BG_FindItem("item_medpak_instant");if(!item->item){G_FreeEntity(item);Com_Printf("STAFF_PICKUP fixture_unavailable\n");return qtrue;}item->s.modelindex=item->item-bg_itemlist;item->s.eType=ET_ITEM;
  Touch_Item(item,&g_entities[slot],&tr);Com_Printf("STAFF_PICKUP health=%d\n",g_entities[slot].health-before);G_FreeEntity(item);
 }
 else if(!Q_stricmp(op,"forcecheck")){
  int target;trap->Argv(3,value,sizeof(value));target=atoi(value);if(target<0||target>=level.maxclients)return qtrue;
  g_entities[slot].client->ps.fd.forcePowersKnown|=1<<FP_PUSH;g_entities[slot].client->ps.fd.forcePowerLevel[FP_PUSH]=3;
  Com_Printf("STAFF_FORCE allowed=%d\n",ForcePowerUsableOn(&g_entities[slot],&g_entities[target],FP_PUSH));
 }
 for(i=0;i<level.maxclients;i++){gentity_t* e=&g_entities[i];if(!e->inuse||!e->client)continue;trace_t clearance;trap->Trace(&clearance,e->client->ps.origin,e->r.mins,e->r.maxs,e->client->ps.origin,i,MASK_PLAYERSOLID|CONTENTS_LAVA|CONTENTS_SLIME|CONTENTS_TRIGGER,qfalse,0,0);Com_Printf("STAFF_QA slot=%d mode=%d pm=%d health=%d x=%.2f y=%.2f z=%.2f vx=%.2f vy=%.2f vz=%.2f contents=%d flags=%d team=%d solid=%d traceEnt=%d role=%d duel=%d thrown=%d\n",i,e->client->ps.stats[15],e->client->ps.pm_type,e->health,e->client->ps.origin[0],e->client->ps.origin[1],e->client->ps.origin[2],e->client->ps.velocity[0],e->client->ps.velocity[1],e->client->ps.velocity[2],e->r.contents,e->r.svFlags,e->client->sess.sessionTeam,clearance.startsolid,clearance.entityNum,ST_StaffRoleForClient(i),e->client->ps.duelInProgress,e->client->ps.saberInFlight);}
 return qtrue;
}
