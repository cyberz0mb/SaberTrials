/* Included by bg_saber.c. Server and client prediction execute this same code. */
static int PM_ST_LoadoutGeometry(void) {
 saberInfo_t* a=BG_MySaber(pm->ps->clientNum,0);
 saberInfo_t* b=BG_MySaber(pm->ps->clientNum,1);
 return a && a->type==SABER_SINGLE && a->numBlades==1 && !b &&
        pm->ps->fd.saberAnimLevel>=SS_FAST && pm->ps->fd.saberAnimLevel<=SS_STRONG;
}
static int PM_ST_HybridUsable(void) {
 saberInfo_t* a=BG_MySaber(pm->ps->clientNum,0);
 saberInfo_t* b=BG_MySaber(pm->ps->clientNum,1);
 return pm->ps->stHybrid.enabled && pm->ps->stHybrid.allowedMask &&
        (!pm->ps->stHybrid.style || (pm->ps->stHybrid.allowedMask&(1u<<pm->ps->stHybrid.style))) &&
        (!pm->ps->stHybrid.style || pm->ps->fd.saberAnimLevel==STH_ParentStyle(pm->ps->stHybrid.style)) &&
        a && a->type==SABER_SINGLE && a->numBlades==1 && !b &&
        pm->ps->fd.saberAnimLevel>=SS_FAST && pm->ps->fd.saberAnimLevel<=SS_STRONG;
}
static int PM_ST_HybridCanMove(int move) {
 const STH_State* s=&pm->ps->stHybrid;
 int attack=BG_SaberInAttack(move),special=BG_SaberInSpecial(move),
     start=PM_SaberInStart(move),link=PM_SaberInTransition(move);
 if(s->recoveryMs && (attack || special || start || link))return 0;
 if(s->attackStyle==STH_PURPLE && (s->committed || s->chainPending)) {
  if(move>=LS_A_TL2BR && move<=LS_A_T2B)return STH_CanFollowup(s);
  if(attack || special || start)return 0;
  if(link)return STH_CanFollowup(s) && s->chainPending==1;
 }
 return 1;
}
static void PM_ST_HybridMove(int move) {
 STH_State* s=&pm->ps->stHybrid;
 if(!s->enabled)return;
 /* Only actual committed attacks incur debt, not cancellable wind-ups. */
 if((BG_SaberInAttack(move) || BG_SaberInSpecial(move)) && !BG_KickMove(move)) {
  if(PM_ST_HybridUsable() && s->style && !s->recoveryMs)
   STH_Commit(s,s->style,pm->ps->torsoAnim,move,pm->ps->torsoTimer);
 } else if(s->chainPending && PM_SaberInTransition(move)) {
  if(!STH_Link(s,pm->ps->torsoAnim,move,pm->ps->torsoTimer))STH_Interrupt(s);
 } else if(s->committed || s->chainPending)STH_Interrupt(s);
}
void BG_ST_HybridStopped(playerState_t* ps,const usercmd_t* cmd,unsigned guards) {
 if(!ps->stHybrid.enabled)return;
 STH_Advance(&ps->stHybrid,(uint32_t)cmd->serverTime,
             (guards&(STC_GUARD_FROZEN|STC_GUARD_PAUSED))!=0);
 if(guards&~(STC_GUARD_FROZEN|STC_GUARD_PAUSED))STH_Interrupt(&ps->stHybrid);
}
qboolean PM_ST_HybridFrame(void) {
 STH_State* s=&pm->ps->stHybrid;
 int oldStyle,safe,oldMove,restoreIdentity,interrupted,continueAttack;
 if(!s->enabled)return qfalse;
 oldMove=s->attackMove;
 interrupted=(pm->ps->torsoAnim!=s->attackAnim || pm->ps->saberMove!=s->attackMove ||
    pm->ps->weapon!=WP_SABER || pm->ps->saberHolstered || pm->ps->saberInFlight ||
    pm->ps->forceHandExtend!=HANDEXTEND_NONE || pm->ps->stats[STAT_HEALTH]<=0 ||
    pm->ps->saberLockTime>pm->cmd.serverTime || pm->ps->saberLockFrame);
 if(s->attackStyle==STH_PURPLE && (s->committed || s->chainPending) &&
    (!PM_ST_HybridUsable() || pm->cmd.weapon!=WP_SABER || pm->ps->saberBlocked ||
     pm->ps->pm_type!=PM_NORMAL || PM_InKnockDown(pm->ps) ||
     BG_InRoll(pm->ps,pm->ps->legsAnim)))interrupted=1;
 continueAttack=!interrupted && PM_ST_HybridUsable() &&
    (pm->cmd.buttons&BUTTON_ATTACK) && oldMove>=LS_A_TL2BR && oldMove<=LS_A_T2B;
 STH_AdvanceCombo(s,(uint32_t)pm->cmd.serverTime,
  pm->ps->pm_type==PM_FREEZE || (pm->ps->stCombatFlags&STC_GUARD_PAUSED),continueAttack);
 if(pm->ps->pm_type==PM_FREEZE || (pm->ps->stCombatFlags&STC_GUARD_PAUSED))return qtrue;
 if((s->committed || s->chainPending) && interrupted)STH_Interrupt(s);
 if(s->recoveryMs) {
  STC_Interrupt(&pm->ps->stCombat);
  pm->cmd.buttons&=~(BUTTON_ATTACK|BUTTON_ALT_ATTACK|BUTTON_FEINT);
  pm->ps->saberBlocking=BLK_NO;
  /* Debt gates attacks, not reactions. Stock weapon code must still advance
     weaponTime and play bounce, broken-parry, pain and return animations.
     Do not decay or extend its timer here: that would run it twice or pin a
     completed strike for the entire recovery period. */
  return qfalse;
 }
 oldStyle=s->style;
 safe=!s->committed && !s->chainPending && pm->ps->weaponTime<=0 && pm->ps->torsoTimer<=0 &&
      !pm->ps->saberLockFrame && pm->ps->saberLockTime<=pm->cmd.serverTime &&
      !pm->ps->saberInFlight && pm->ps->forceHandExtend==HANDEXTEND_NONE &&
      pm->ps->stats[STAT_HEALTH]>0 &&
      (pm->ps->saberMove<=LS_READY || pm->ps->weapon!=WP_SABER);
 /* Loadout selection is independent of a hybrid's stock animation family.
  * Keep the saved choice while using dual/staff; never reinterpret their IDs
  * (6/7) as a single-saber selection. Returning to single restores it safely. */
 if(s->requestedSelection && PM_ST_LoadoutGeometry() &&
    (s->availableMask&(1u<<s->requestedSelection))) {
  int applied=STH_ApplySelection(s,safe);
  int parent=s->selectedStyle>=STH_GREEN?STH_ParentStyle(s->selectedStyle):s->selectedStyle;
  if(applied || (safe && s->selectedStyle==s->requestedSelection &&
      (STH_LoadoutHas(s->loadout,s->selectedStyle) ||
       (!STH_LoadoutPick(s->loadout,s->availableMask,0) && s->selectedStyle<=3)) &&
      pm->ps->fd.saberAnimLevel!=parent)) {
   pm->ps->fd.saberAnimLevelBase=pm->ps->fd.saberAnimLevel=
    parent;
   pm->ps->fd.saberDrawAnimLevel=pm->ps->fd.saberAnimLevel;
   s->originalStyle=pm->ps->fd.saberAnimLevel;
   pm->ps->saberAttackChainCount=0;
  }
  return qfalse;
 }
 if(!PM_ST_HybridUsable())STH_Request(s,0);
 if(STH_ApplyRequest(s,safe)) {
  if(s->style) {
   if(!oldStyle)s->originalStyle=pm->ps->fd.saberAnimLevel;
   pm->ps->fd.saberAnimLevelBase=pm->ps->fd.saberAnimLevel=STH_ParentStyle(s->style);
  } else if(s->originalStyle>=SS_FAST && s->originalStyle<=SS_STRONG &&
            pm->ps->fd.saberAnimLevel>=SS_FAST && pm->ps->fd.saberAnimLevel<=SS_STRONG) {
   restoreIdentity=s->originalStyle==SS_FAST?STH_PURPLE:s->originalStyle==SS_STRONG?STH_ORANGE:STH_GREEN;
   if(s->allowedMask&(1u<<restoreIdentity))
    pm->ps->fd.saberAnimLevelBase=pm->ps->fd.saberAnimLevel=s->originalStyle;
  }
  pm->ps->fd.saberDrawAnimLevel=pm->ps->fd.saberAnimLevel;
  pm->ps->saberAttackChainCount=0;
 }
 return qfalse;
}
