/* Server identity/configuration adapter, included once by g_client.c. */
static unsigned G_ST_HybridAllowed(gentity_t* ent) {
 unsigned classMask=0;
 saberInfo_t* first=&ent->client->saber[0];
 if(!first->model[0] || first->type!=SABER_SINGLE || first->numBlades!=1 ||
    ent->client->saber[1].model[0])return 0;
 if(level.gametype==GT_SIEGE && ent->client->siegeClass>=0)
  classMask=bgSiegeClasses[ent->client->siegeClass].saberStance;
 return STH_AllowedStyles(ent->client->ps.fd.forcePowerLevel[FP_SABER_OFFENSE],
  ent->client->saber[0].stylesForbidden,ent->client->saber[0].stylesLearned,classMask,
  ent->client->ps.fd.saberAnimLevelBase);
}
static int G_ST_HybridEligible(gentity_t* ent,int style) {
 saberInfo_t* a=&ent->client->saber[0];
 return g_hybridStyles.integer && ent->localAnimIndex>=0 && ent->localAnimIndex<=1 &&
        a->model[0] && a->type==SABER_SINGLE && a->numBlades==1 && !ent->client->saber[1].model[0] &&
        (!style || (G_ST_HybridAllowed(ent)&(1u<<style))) &&
        ST_StanceAssetsAvailable() && STH_AnimationsValid(bgAllAnims[ent->localAnimIndex].anims);
}
static void G_ST_LoadoutAvailability(gentity_t* ent) {
 STH_State* s=&ent->client->ps.stHybrid;
 unsigned mask=G_ST_HybridAllowed(ent);
 int style;
 s->allowedMask=G_ST_HybridEligible(ent,0)?mask:0;
 s->availableMask=s->allowedMask;
 for(style=4;style<=6;style++)
  if(mask&(1u<<style))s->availableMask|=1u<<STH_ParentStyle(style);
}
static int G_ST_LoadoutPick(STH_State* s,int current) {
 int choice=STH_LoadoutPick(s->loadout,s->availableMask,current),stock;
 if(choice)return choice;
 /* No equipped style is legal (for example offense level one). Keep the
  * saved loadout, but let the player use the first server-allowed stock style. */
 for(stock=1;stock<=3;stock++)if(s->availableMask&(1u<<stock))return stock;
 return 0;
}
void G_ST_HybridUserinfo(gentity_t* ent,const char* userinfo) {
 STH_State* s=&ent->client->ps.stHybrid;
 const char* value=Info_ValueForKey(userinfo,"saberStyleLoadout");
 int32_t slots[3];int choice,legacy=0;
 if(!s->enabled)return;
 if(!STH_LoadoutParse(value,slots)) {
  if(!*value) {
   const char* old=Info_ValueForKey(userinfo,"saberCombatStyle");
   if(!strcmp(old,"4")||!strcmp(old,"5")||!strcmp(old,"6"))legacy=atoi(old);
  }
  STH_LoadoutDefault(slots,legacy);
 }
 STH_SetLoadout(s,slots);G_ST_LoadoutAvailability(ent);
 choice=G_ST_LoadoutPick(s,s->requestedSelection?s->requestedSelection:s->selectedStyle);
 if(choice) {
  ent->client->saberCycleQueue=0;
  STH_RequestSelection(s,choice);
 }
}
qboolean G_ST_HybridCycle(gentity_t* ent) {
 STH_State* s=&ent->client->ps.stHybrid;
 int choice;
 if(!s->enabled)return qfalse;
 G_ST_LoadoutAvailability(ent);
 if(!s->availableMask)return qfalse;
 choice=STH_LoadoutNext(s->loadout,s->availableMask,
                      s->requestedSelection?s->requestedSelection:s->selectedStyle);
 if(!choice)choice=G_ST_LoadoutPick(s,0);
 if(choice)STH_RequestSelection(s,choice);
 ent->client->saberCycleQueue=0;
 return qtrue;
}
void G_ST_HybridRememberStyle(gentity_t* ent) {
 gclient_t* client=ent->client;
 const STH_State* s=&client->ps.stHybrid;
 if(s->enabled && client->sess.sessionTeam!=TEAM_SPECTATOR) {
  client->sess.stSaberStyle=s->availableMask && client->ps.fd.saberAnimLevelBase<=SS_STRONG
                          ?s->selectedStyle:0;
 }
}
void G_ST_HybridSpawn(gentity_t* ent,const char* userinfo) {
 STH_State* s=&ent->client->ps.stHybrid;
 STH_Init(s,(uint32_t)ent->client->ps.commandTime,g_hybridStyles.integer);
 if(!g_hybridStyles.integer)return;
 if(!ST_StanceAssetsAvailable() || !STH_AnimationsValid(bgAllAnims[0].anims)) {
  trap->Error(ERR_DROP,"Hybrid styles require the matching Saber Trials stance library and animation package.");
  return;
 }
 G_ST_HybridUserinfo(ent,userinfo);
 /* An unavailable saved selection leaves the normal loadout fallback queued. */
 STH_RequestSelection(s,ent->client->sess.stSaberStyle);
 s->originalStyle=ent->client->ps.fd.saberAnimLevel;
 if(s->availableMask && STH_ApplySelection(s,1)) {
  int parent=s->selectedStyle>=4?STH_ParentStyle(s->selectedStyle):s->selectedStyle;
  ent->client->ps.fd.saberAnimLevelBase=ent->client->ps.fd.saberAnimLevel=parent;
  ent->client->ps.fd.saberDrawAnimLevel=parent;
 }
}
void G_ST_HybridThink(gentity_t* ent) {
 unsigned guards=0;
 usercmd_t bounded;
 int64_t now=level.time;
 STH_State* s;
 if(!ent->client || !ent->client->ps.stHybrid.enabled)return;
 s=&ent->client->ps.stHybrid;
 G_ST_LoadoutAvailability(ent);
 if(ent->health>0)G_ST_HybridRememberStyle(ent);
 /* Never discard outstanding Purple recovery when geometry changes. */
 if(!s->availableMask)STH_Request(s,0);
 else {
  int choice=G_ST_LoadoutPick(s,s->requestedSelection?s->requestedSelection:s->selectedStyle);
  if(choice)STH_RequestSelection(s,choice);
  ent->client->saberCycleQueue=0;
 }
 if(level.stTournamentPhase==ST_TOURNAMENT_PAUSED)guards|=STC_GUARD_PAUSED;
 ent->client->ps.stCombatFlags=(int)(guards&STC_GUARD_PAUSED);
 if(ent->client->ps.stats[ST_STAFF_STAT]==ST_STAFF_FROZEN)guards|=STC_GUARD_FROZEN;
 if(ent->client->ps.stats[ST_STAFF_STAT]==ST_STAFF_GHOST)guards|=STC_GUARD_GHOST;
 if(ent->health<=0)guards|=STC_GUARD_DEAD;
 if(ent->client->sess.sessionTeam==TEAM_SPECTATOR)guards|=STC_GUARD_SPECIAL;
 if(guards) {
  bounded=ent->client->pers.cmd;
  if((int64_t)bounded.serverTime>now+200)bounded.serverTime=(int)(now+200);
  if((int64_t)bounded.serverTime<now-1000)bounded.serverTime=(int)(now-1000);
  BG_ST_HybridStopped(&ent->client->ps,&bounded,guards);
 }
}
int G_ST_HybridDamageStyle(gentity_t* ent,int saberNum) {
 const playerState_t* p=&ent->client->ps;
 const STH_State* s=&p->stHybrid;
 return saberNum==0 && s->enabled && s->committed && !p->saberInFlight &&
        p->saberMove>=LS_A_TL2BR && p->saberMove<=LS_A_T2B &&
        s->attackMove==p->saberMove && s->attackAnim==p->torsoAnim &&
        STH_AnimStyle(p->torsoAnim)==s->attackStyle ? s->attackStyle:0;
}
