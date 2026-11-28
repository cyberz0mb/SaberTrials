/* Dedicated input for the existing authoritative active-defense system.
 * No damage modifiers, forced movement, animation cancels or client claims. */
#include "../staff/st_staff_movement.h"
qboolean PM_InKnockDown(playerState_t *ps);

int ST_BlockingMode(void) {
 /* Invalid config values fall back to the unchanged legacy defense mode. */
 return g_manualBlocking.integer==1 || g_manualBlocking.integer==2?g_manualBlocking.integer:0;
}

static qboolean ST_ManualBlockEnabled(void) {
 return ST_BlockingMode()!=0 && ST_CombatOption(ST_COMBAT_DEFENSE);
}

static int ST_ManualBlockMask(const gentity_t *ent) {
 /* Existing bots already produce timed Walk inputs; preserve that behavior. */
 return ((ent->r.svFlags&SVF_BOT) || ent->s.eType==ET_NPC)?BUTTON_WALKING:BUTTON_BLOCK;
}

static qboolean ST_BlockCommonSafe(gentity_t *ent) {
 playerState_t *ps;
 if(!ent || !ent->client)return qfalse;
 ps=&ent->client->ps;
 if(ent->health<=0 || ps->stats[STAT_HEALTH]<=0 ||
    ent->client->sess.sessionTeam==TEAM_SPECTATOR || (ps->pm_flags&PMF_FOLLOW) ||
    ps->pm_type!=PM_NORMAL || ps->stats[ST_STAFF_STAT] ||
    level.intermissiontime || level.stTournamentPhase==ST_TOURNAMENT_PAUSED ||
    ps->weapon!=WP_SABER || ps->weaponstate==WEAPON_RAISING || ps->saberBlocked ||
    !ps->saberEntityNum || BG_SabersOff(ps) || ps->saberInFlight ||
    ps->m_iVehicleNum || ps->emplacedIndex || ps->forceHandExtend!=HANDEXTEND_NONE ||
    ps->saberLockFrame || ps->saberLockTime>level.time ||
    ps->stCombat.recoveryMs || ps->stHybrid.recoveryMs ||
    BG_InRoll(ps,ps->legsAnim) ||
    PM_InKnockDown(ps))return qfalse;
 return qtrue;
}

static qboolean ST_ManualBlockSafe(gentity_t *ent) {
 playerState_t *ps;
 if(!ST_BlockCommonSafe(ent))return qfalse;
 ps=&ent->client->ps;
 if(BG_SaberInAttack(ps->saberMove) ||
    BG_SaberInSpecial(ps->saberMove) || BG_SaberInSpecialAttack(ps->torsoAnim))return qfalse;
 /* Recovery, bounce and broken-parry moves cannot become guard/counter resets. */
 return ps->saberMove==LS_READY || ps->saberMove==LS_NONE ||
        (ps->saberMove>=LS_PARRY_UP && ps->saberMove<=LS_REFLECT_LL);
}

qboolean ST_AttackParryEnabled(const gentity_t *ent) {
 /* Human Attack timing replaces human guard-press timing by default. Bots
    retain their existing Walk-based defense until their AI is upgraded. */
 return ent && ent->client && !(ent->r.svFlags&SVF_BOT) && ent->s.eType!=ET_NPC &&
   st_attackParry.integer && ST_CombatOption(ST_COMBAT_DEFENSE);
}

qboolean ST_AttackParryReady(gentity_t *ent) {
 playerState_t *ps;
 const STH_State *s;
 if(!ST_AttackParryEnabled(ent) || ent->client->stAttackParryEnd<=level.time ||
    !ST_BlockCommonSafe(ent))return qfalse;
 ps=&ent->client->ps;s=&ps->stHybrid;
 if(ent->client->pers.cmd.weapon!=WP_SABER ||
    (ent->client->pers.cmd.buttons&(BUTTON_ALT_ATTACK|BUTTON_FEINT|BUTTON_TALK)) ||
    ps->fd.forcePowerLevel[FP_SABER_DEFENSE]<=0)return qfalse;
 if(ST_ManualBlockSafe(ent))return qtrue;
 /* The ordinary attack may start normally. Its short parry token ends as
    soon as it can deal damage: never turn an active cut/recovery into guard. */
 return ps->saberMove>=LS_S_TL2BR && ps->saberMove<=LS_S_T2B &&
   !s->committed && !BG_SaberInSpecialAttack(ps->torsoAnim);
}

qboolean ST_ConsumeAttackParry(gentity_t *ent,vec3_t point) {
 gclient_t *cl;
 STH_State *s;
 if(!ST_AttackParryReady(ent) || !point ||
    !InFront(point,ent->client->ps.origin,ent->client->ps.viewangles,0.0f))return qfalse;
 cl=ent->client;s=&cl->ps.stHybrid;
 cl->stAttackParryEnd=0;cl->stParryWindowEnd=0;
 /* Only a verified, non-damaging startup reaches here. Preserve selections,
    input history, cooldowns and sequence identity; no recovery debt is owed. */
 s->committed=0;s->strikeMs=0;s->chainPending=0;
 s->attackStyle=0;s->attackAnim=0;s->attackMove=0;
 STC_Interrupt(&cl->ps.stCombat);
 cl->stPerfectParrySuccessTime=level.time;
 cl->stCounterWindowEnd=level.time+Com_Clampi(250,1000,st_counterWindow.integer);
 cl->pers.stPerfectParries++;
 return qtrue;
}

static void ST_UpdateAttackParryInput(gentity_t *ent,const usercmd_t *cmd) {
 gclient_t *cl=ent->client;
 int held=(cmd->buttons&BUTTON_ATTACK)!=0;
 int fresh=held && !cl->stParryAttackHeld;
 cl->stParryAttackHeld=held;
 cl->stParryWindowEnd=0; /* Block alone guards, but does not earn a parry. */
 if(!ST_AttackParryReady(ent))cl->stAttackParryEnd=0;
 if(!ST_ManualBlockSafe(ent)) { cl->stCounterWindowEnd=0;return; }
 if(fresh && cmd->weapon==WP_SABER &&
    !(cmd->buttons&(BUTTON_ALT_ATTACK|BUTTON_FEINT|BUTTON_TALK)) &&
    cl->ps.fd.forcePowerLevel[FP_SABER_DEFENSE]>0) {
  if(cl->stCounterWindowEnd>level.time) {
   cl->ps.weaponTime=0;cl->stCounterWindowEnd=0;
  }
  if(cl->ps.weaponTime<=0 && cl->stParryCooldownEnd<=level.time) {
   int window=Com_Clampi(60,200,st_attackParryWindow.integer);
   cl->stAttackParryEnd=level.time+window;
   cl->stParryCooldownEnd=level.time+Com_Clampi(window+100,1500,st_parryCooldown.integer);
  }
 }
}

qboolean ST_ManualBlockEligible(gentity_t *ent, const usercmd_t *cmd) {
 return cmd && cmd->weapon==WP_SABER && ST_ManualBlockSafe(ent) && ent->client->ps.weaponTime<=0 &&
   ent->client->ps.fd.forcePowerLevel[FP_SABER_DEFENSE]>0 &&
   !(cmd->buttons&(BUTTON_ATTACK|BUTTON_ALT_ATTACK|BUTTON_FEINT|BUTTON_TALK)) &&
   (cmd->buttons&ST_ManualBlockMask(ent));
}

qboolean ST_BlockInputAllowed(gentity_t *ent,const usercmd_t *cmd) {
 /* The explicit manual-only rule also applies with Original JKA/defense-off.
    Those presets retain stock block angles and do not gain timed parries. */
 return ST_BlockingMode()!=2 || ST_ManualBlockEligible(ent,cmd);
}

qboolean ST_ActiveGuard(gentity_t *ent) {
 if(!ent || !ent->client)return qfalse;
 if(ST_ManualBlockEnabled())return ST_ManualBlockEligible(ent,&ent->client->pers.cmd);
 return (ent->client->pers.cmd.buttons&BUTTON_WALKING)!=0;
}

/* Consume held inputs on paths that skip normal client weapon processing. */
void ST_ManualBlockStopped(gentity_t *ent) {
 if(!ent || !ent->client)return;
 if(ST_AttackParryEnabled(ent)) {
  if(!ST_AttackParryReady(ent))ent->client->stAttackParryEnd=0;
  if(!ST_BlockCommonSafe(ent)) {
   ent->client->stParryAttackHeld=(ent->client->pers.cmd.buttons&BUTTON_ATTACK)!=0;
   ent->client->stCounterWindowEnd=0;
  }
 }
 if(!ST_ManualBlockEnabled())return;
 if(!ST_ManualBlockSafe(ent)) {
  ent->client->stParryWindowEnd=0;
  ent->client->stCounterWindowEnd=0;
  ent->client->stManualBlockHeld=(ent->client->pers.cmd.buttons&ST_ManualBlockMask(ent))!=0;
 }
}

static void ST_UpdateManualBlockInput(gentity_t *ent,const usercmd_t *cmd) {
 gclient_t *cl=ent->client;
 int held=(cmd->buttons&ST_ManualBlockMask(ent))!=0;
 int fresh=held && !cl->stManualBlockHeld;
 int window,cooldown;
 cl->stManualBlockHeld=held;
 /* A previously earned counter can shorten only a defensive parry reaction.
    It cannot clear offensive or feint recovery debt. */
 if(cl->stCounterWindowEnd>level.time && (cmd->buttons&BUTTON_ATTACK) &&
    cmd->weapon==WP_SABER && ST_ManualBlockSafe(ent)) {
  cl->ps.weaponTime=0;cl->stCounterWindowEnd=0;
 }
 if(!ST_ManualBlockEligible(ent,cmd)) {
  cl->stParryWindowEnd=0;
  if(!ST_ManualBlockSafe(ent))cl->stCounterWindowEnd=0;
  return;
 }
 if(fresh && cl->stParryCooldownEnd<=level.time) {
  window=Com_Clampi(100,450,st_parryWindow.integer);
  cooldown=Com_Clampi(window+100,1500,st_parryCooldown.integer);
  cl->stParryWindowEnd=level.time+window;
  cl->stParryCooldownEnd=level.time+cooldown;
 }
}
