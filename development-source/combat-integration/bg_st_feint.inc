/* Shared server/prediction adapter. Included by bg_saber.c. No damage changes. */
#include "st_combat_wire.h"

static unsigned PM_ST_FeintGuards(void) {
 unsigned guards=(unsigned)pm->ps->stCombatFlags;
 saberInfo_t* first=BG_MySaber(pm->ps->clientNum,0);
 saberInfo_t* second=BG_MySaber(pm->ps->clientNum,1);
 if(pm->ps->stats[STAT_HEALTH]<=0 || pm->ps->pm_type==PM_DEAD)guards|=STC_GUARD_DEAD;
 if(pm->ps->pm_type==PM_FREEZE)guards|=STC_GUARD_FROZEN;
 if(pm->ps->pm_type==PM_NOCLIP || pm->ps->stats[ST_STAFF_STAT]==ST_STAFF_GHOST)guards|=STC_GUARD_GHOST;
 if(pm->ps->pm_type!=PM_NORMAL && pm->ps->pm_type!=PM_FREEZE)guards|=STC_GUARD_SPECIAL;
 if(pm->ps->weapon!=WP_SABER || pm->cmd.weapon!=WP_SABER)guards|=STC_GUARD_WEAPON;
 if(pm->ps->saberHolstered)guards|=STC_GUARD_HOLSTER;
 if(pm->ps->saberInFlight)guards|=STC_GUARD_THROWN;
 if(pm->ps->saberLockFrame || pm->ps->saberLockTime>pm->cmd.serverTime)guards|=STC_GUARD_LOCK;
 if(pm->ps->saberBlocked || pm->ps->forceHandExtend!=HANDEXTEND_NONE)guards|=STC_GUARD_STAGGER;
 if(PM_InKnockDown(pm->ps) || BG_InRoll(pm->ps,pm->ps->legsAnim))guards|=STC_GUARD_STAGGER;
 if(pm->ps->m_iVehicleNum)guards|=STC_GUARD_VEHICLE;
 if(pm->ps->groundEntityNum==ENTITYNUM_NONE || (pm->ps->pm_flags&PMF_DUCKED) || pm->cmd.upmove)
  guards|=STC_GUARD_SPECIAL;
 if(!first || first->type!=SABER_SINGLE || first->numBlades!=1 || second ||
    pm->ps->fd.saberAnimLevel<SS_FAST || pm->ps->fd.saberAnimLevel>SS_STRONG)guards|=STC_GUARD_ASSET;
 return guards;
}

static STC_Direction PM_ST_FeintDirection(void) {
 /* Same logical directions as ordinary attacks. The existing renderer and
  * saber geometry mirror the entire pose for left-handers: do not mirror twice. */
 if(pm->cmd.rightmove>0)
  return pm->cmd.forwardmove>0?STC_TL_BR:pm->cmd.forwardmove<0?STC_BL_TR:STC_L_R;
 if(pm->cmd.rightmove<0)
  return pm->cmd.forwardmove>0?STC_TR_BL:pm->cmd.forwardmove<0?STC_BR_TL:STC_R_L;
 return STC_T_B;
}

static void PM_ST_FeintMove(int move) {
 STC_State* s=&pm->ps->stCombat;
 unsigned guards;
 if(!s->epoch)return;
 guards=PM_ST_FeintGuards();
 if(move>=LS_S_TL2BR && move<=LS_S_T2B && pm->ps->torsoTimer>0) {
  STC_Direction direction=(STC_Direction)(move-LS_S_TL2BR);
  if(s->phase==STC_REDIRECT_READY && s->redirect==direction) {
   if(!STC_StartRedirect(s,(uint32_t)pm->cmd.serverTime,(unsigned)pm->ps->torsoTimer,guards))
    STC_Interrupt(s);
  } else {
   STC_FinishAttack(s);
   /* Never reuse an identity on serial wrap; disable until the next lifecycle. */
   if(s->attack==UINT32_MAX) {memset(s,0,sizeof(*s));return;}
   STC_BeginAttack(s,s->attack+1,(STC_Style)pm->ps->fd.saberAnimLevel,direction,
      (uint32_t)pm->cmd.serverTime,(unsigned)pm->ps->torsoTimer,guards);
  }
 } else if(move>=LS_A_TL2BR && move<=LS_A_T2B) {
  STC_Commit(s);
 } else if(s->phase!=STC_RECOVERY && s->phase!=STC_REDIRECT_READY) {
  if(move==LS_READY)STC_FinishAttack(s);else STC_Interrupt(s);
 }
}

/* Called at the common weapon entry, before saber or other weapon behavior. */
qboolean PM_ST_FeintFrame(void) {
 STC_State* s=&pm->ps->stCombat;
 STC_Rules rules=STC_DefaultRules();
 STC_Result result;
 unsigned guards;
 unsigned priorRecovery;
 int move;
 if(!s->epoch)return qfalse;
 if(!STC_StateValid(s)) {memset(s,0,sizeof(*s));return qfalse;}
 priorRecovery=s->recoveryMs;
 guards=PM_ST_FeintGuards();rules.enabled=1;
 if((guards&~(STC_GUARD_FROZEN|STC_GUARD_PAUSED)) ||
    (s->attack && s->style!=(STC_Style)pm->ps->fd.saberAnimLevel))STC_Interrupt(s);
 if(s->phase==STC_WINDUP &&
    (pm->ps->saberMove!=LS_S_TL2BR+(int)s->direction || pm->ps->torsoTimer<=0 || pm->ps->weaponTime<=0))
  STC_Commit(s);
 result=STC_Input(s,(uint32_t)pm->cmd.serverTime,(pm->cmd.buttons&BUTTON_FEINT)!=0,
      PM_ST_FeintDirection(),guards,&rules);
 /* The common weapon gate skips stock weaponTime decay. Advance only the
  * timer we own; a longer external stun/weapon delay must stay intact. */
 if(priorRecovery && pm->ps->weaponTime==(int)priorRecovery)
  pm->ps->weaponTime=(int)s->recoveryMs;
 if(result==STC_ACCEPTED) {
  /* Blend the current wind-up back to the chosen ready pose. Movement keeps
   * its normal locomotion; only a stationary grounded player resets legs. */
  pm->ps->torsoTimer=0;pm->ps->weaponTime=0;
  PM_SetSaberMove(LS_READY);
  if(pm->ps->saberMove!=LS_READY) {STC_Interrupt(s);}
  else {
   int parts=SETANIM_TORSO;
   if(!pm->cmd.forwardmove && !pm->cmd.rightmove) {parts=SETANIM_BOTH;pm->ps->legsTimer=0;}
   PM_SetAnim(parts,PM_GetSaberStance(),SETANIM_FLAG_OVERRIDE|SETANIM_FLAG_HOLD);
  }
 }
 if(s->phase==STC_RECOVERY) {
  if(pm->ps->weaponTime<(int)s->recoveryMs)pm->ps->weaponTime=(int)s->recoveryMs;
  return qtrue;
 }
 if(guards&(STC_GUARD_FROZEN|STC_GUARD_PAUSED))return qtrue;
 if(s->phase==STC_REDIRECT_READY) {
  if(guards || !(pm->cmd.buttons&BUTTON_ATTACK)) {STC_Interrupt(s);return qfalse;}
  move=LS_S_TL2BR+(int)s->redirect;
  pm->ps->weaponTime=pm->ps->torsoTimer=0;
  PM_SetSaberMove((short)move);
  if(pm->ps->saberMove!=move || s->phase!=STC_WINDUP)STC_Interrupt(s);
  else pm->ps->weaponTime=pm->ps->torsoTimer;
  return qtrue;
 }
 return qfalse;
}

/* Handles paths that skip the weapon function. It consumes held input during
 * freeze/pause instead of manufacturing a fresh press when control returns. */
void BG_ST_FeintStopped(playerState_t* ps,const usercmd_t* cmd,unsigned guards) {
 STC_Rules rules=STC_DefaultRules();
 if(!ps->stCombat.epoch)return;
 if(!STC_StateValid(&ps->stCombat)) {memset(&ps->stCombat,0,sizeof(ps->stCombat));return;}
 if(guards&~(STC_GUARD_FROZEN|STC_GUARD_PAUSED))STC_Interrupt(&ps->stCombat);
 STC_Input(&ps->stCombat,(uint32_t)cmd->serverTime,(cmd->buttons&BUTTON_FEINT)!=0,STC_T_B,guards,&rules);
}
