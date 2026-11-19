/* Server early-return adapter; compiled in g_active.c and the native harness. */
static void G_STFeintStoppedState(gentity_t* ent) {
 unsigned guards;
 if(!ent->client || !ent->client->ps.stCombat.epoch)return;
 ent->client->ps.stCombatFlags=level.stTournamentPhase==ST_TOURNAMENT_PAUSED?STC_GUARD_PAUSED:0;
 guards=(unsigned)ent->client->ps.stCombatFlags;
 if(ent->client->ps.stats[ST_STAFF_STAT]==ST_STAFF_FROZEN)guards|=STC_GUARD_FROZEN;
 if(ent->client->ps.stats[ST_STAFF_STAT]==ST_STAFF_GHOST)guards|=STC_GUARD_GHOST;
 if(ent->health<=0)guards|=STC_GUARD_DEAD;
 if(ent->client->sess.sessionTeam==TEAM_SPECTATOR)guards|=STC_GUARD_SPECIAL;
 if(guards) {
  /* This runs before ClientThink's normal clamp and before staff strips the
   * buttons. Bound a copy now, retaining the original input edge. Use wide
   * arithmetic so malformed commands cannot overflow the bounds comparison. */
  usercmd_t bounded=ent->client->pers.cmd;
  int64_t now=level.time;
  if((int64_t)bounded.serverTime>now+200)bounded.serverTime=(int)(now+200);
  if((int64_t)bounded.serverTime<now-1000)bounded.serverTime=(int)(now-1000);
  BG_ST_FeintStopped(&ent->client->ps,&bounded,guards);
 }
}
