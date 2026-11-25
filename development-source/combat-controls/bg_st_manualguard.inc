/* Shared server + prediction: a ready upper-body pose, never a combat move.
 * Leaves the user's command, legs, movement, attack and recovery timers alone. */
static qboolean stManualGuardPoseEnabled=qfalse;

void BG_ST_SetManualGuard(int mode,qboolean activeDefense) {
 stManualGuardPoseEnabled=mode==2 || (mode==1 && activeDefense);
}

static qboolean ST_IsManualGuardAnim(int anim) {
 return anim==BOTH_ST_GUARD_SINGLE || anim==BOTH_ST_GUARD_DUAL || anim==BOTH_ST_GUARD_STAFF;
}

static qboolean PM_ST_ManualGuardFrame(void) {
 playerState_t *ps=pm->ps;
 int anim=ps->fd.saberAnimLevel==SS_DUAL?BOTH_ST_GUARD_DUAL:
          ps->fd.saberAnimLevel==SS_STAFF?BOTH_ST_GUARD_STAFF:BOTH_ST_GUARD_SINGLE;
 qboolean eligible=stManualGuardPoseEnabled && (pm->cmd.buttons&BUTTON_BLOCK) &&
   !(pm->cmd.buttons&(BUTTON_ATTACK|BUTTON_ALT_ATTACK|BUTTON_FEINT|BUTTON_TALK)) &&
   ps->stats[STAT_HEALTH]>0 && ps->pm_type==PM_NORMAL && !(ps->pm_flags&PMF_FOLLOW) &&
   !ps->stats[ST_STAFF_STAT] && !(ps->stCombatFlags&STC_GUARD_PAUSED) &&
   ps->weapon==WP_SABER && pm->cmd.weapon==WP_SABER &&
   ps->weaponstate!=WEAPON_RAISING && ps->weaponstate!=WEAPON_DROPPING &&
   ps->saberEntityNum && !BG_SabersOff(ps) && !ps->saberInFlight &&
   !ps->m_iVehicleNum && !ps->emplacedIndex && ps->forceHandExtend==HANDEXTEND_NONE &&
   !ps->saberLockFrame && ps->saberLockTime<=pm->cmd.serverTime && !ps->saberBlocked &&
   !ps->stCombat.recoveryMs && !ps->stHybrid.recoveryMs &&
   /* Defense levels are server-only. The known-power bit is replicated, so
      prediction must use it or it will erase the authoritative guard pose. */
   ps->weaponTime<=0 && ps->torsoTimer==0 && (ps->fd.forcePowersKnown&(1<<FP_SABER_DEFENSE)) &&
   (ps->saberMove==LS_READY || ps->saberMove==LS_NONE) &&
   !BG_SaberInSpecialAttack(ps->torsoAnim) &&
   !BG_InRoll(ps,ps->legsAnim) && !PM_InKnockDown(ps) &&
   pm->animations && pm->animations[anim].numFrames==1 && pm->animations[anim].loopFrames==1;
 if(eligible) {
  /* One stable looping sample, blended by Ghoul2. No HOLD flag or artificial
     timer: the next Attack/Alt/Feint input is processed immediately. */
  PM_SetAnim(SETANIM_TORSO,anim,SETANIM_FLAG_OVERRIDE);
  return qtrue;
 }
 if(ST_IsManualGuardAnim(ps->torsoAnim)) {
  /* Only undo our own ready pose. A contact reaction, death, roll or Force
     animation with a different ID retains ownership of its channel. */
  PM_SetAnim(SETANIM_TORSO,PM_GetSaberStance(),SETANIM_FLAG_OVERRIDE);
 }
 return qfalse;
}
