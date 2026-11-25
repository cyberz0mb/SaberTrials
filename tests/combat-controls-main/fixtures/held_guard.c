/* Shared held-pose adapter, with explicit engine animation/weapon seams. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "st_hybrid.h"
#include "st_combat_core.h"
typedef int qboolean;
#define qtrue 1
#define qfalse 0
enum {WP_SABER=2,PM_NORMAL=0,PM_FREEZE=1,PMF_FOLLOW=1,STAT_HEALTH=0,
 ST_STAFF_STAT=15,STC_UNUSED=0,FP_SABER_DEFENSE=0,HANDEXTEND_NONE=0,
 LS_READY=1,LS_NONE=0,LS_PARRY_UP=10,LS_REFLECT_LL=20,
 WEAPON_RAISING=1,WEAPON_DROPPING=2,BUTTON_ATTACK=1,BUTTON_ALT_ATTACK=128,
 BUTTON_FEINT=4096,BUTTON_BLOCK=8192,BUTTON_TALK=2,SS_DUAL=6,SS_STAFF=7,
 SETANIM_TORSO=1,SETANIM_FLAG_OVERRIDE=1,BOTH_ST_GUARD_SINGLE=100,
 BOTH_ST_GUARD_DUAL=101,BOTH_ST_GUARD_STAFF=102};
typedef struct {int firstFrame,numFrames,loopFrames,frameLerp;} animation_t;
typedef struct {int buttons,weapon,serverTime,forwardmove,rightmove,upmove;} usercmd_t;
typedef struct {
 int stats[16],pm_type,pm_flags,weapon,weaponstate,saberEntityNum,saberInFlight,saberHolstered;
 int saberLockFrame,saberLockTime,saberBlocked,saberMove,weaponTime,torsoTimer,legsTimer;
 int torsoAnim,legsAnim,forceHandExtend,m_iVehicleNum,emplacedIndex,stCombatFlags;
 float velocity[3],viewangles[3];
 struct {int saberAnimLevel,forcePowerLevel[4],forcePowersKnown;} fd;
 STH_State stHybrid;STC_State stCombat;
} playerState_t;
typedef struct {playerState_t *ps;usercmd_t cmd;animation_t *animations;} pmove_t;
static playerState_t ps;static animation_t anims[110];static pmove_t movement,*pm=&movement;
static int rolling,knocked,draws,checks;
static qboolean BG_SabersOff(playerState_t *s){return s->saberHolstered==2;}
static qboolean BG_InRoll(playerState_t *s,int a){(void)s;(void)a;return rolling;}
static qboolean PM_InKnockDown(playerState_t *s){(void)s;return knocked;}
static qboolean BG_SaberInSpecialAttack(int a){return a==90;}
static int PM_GetSaberStance(void){return 50;}
static void PM_SetAnim(int parts,int anim,int flags){
 if(parts!=SETANIM_TORSO || flags!=SETANIM_FLAG_OVERRIDE)exit(2);
 if(ps.torsoAnim!=anim){ps.torsoAnim=anim;draws++;}
}
#ifdef ST_GUARD_POSE_PRESENT
#include "bg_st_manualguard.inc"
#else
/* Pre-change source has no pose adapter: this is the observed baseline. */
static void BG_ST_SetManualGuard(int mode,qboolean active){(void)mode;(void)active;}
static qboolean PM_ST_ManualGuardFrame(void){return qfalse;}
#endif
#define CHECK(x) do {checks++;if(!(x)){fprintf(stderr,"held guard line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
static void reset(void){
 memset(&ps,0,sizeof ps);memset(&movement,0,sizeof movement);memset(anims,0,sizeof anims);
 pm->ps=&ps;pm->animations=anims;ps.stats[STAT_HEALTH]=100;
 ps.weapon=pm->cmd.weapon=WP_SABER;ps.saberMove=LS_READY;ps.saberEntityNum=17;
 ps.fd.forcePowerLevel[FP_SABER_DEFENSE]=3;ps.fd.forcePowersKnown=1<<FP_SABER_DEFENSE;
 ps.fd.saberAnimLevel=1;ps.torsoAnim=50;
 ps.legsAnim=60;ps.legsTimer=100;ps.velocity[0]=250;ps.viewangles[1]=45;
 pm->cmd.buttons=BUTTON_BLOCK;pm->cmd.forwardmove=127;pm->cmd.rightmove=-127;
 pm->cmd.serverTime=1000;rolling=knocked=draws=0;
 anims[100].numFrames=anims[101].numFrames=anims[102].numFrames=1;
 anims[100].loopFrames=anims[101].loopFrames=anims[102].loopFrames=1;
 BG_ST_SetManualGuard(1,qtrue);
}
int main(void){
 int family,i,mode,active;playerState_t before;usercmd_t command;
 for(family=0;family<3;family++){
  reset();ps.fd.saberAnimLevel=family==0?1:family==1?SS_DUAL:SS_STAFF;
  before=ps;command=pm->cmd;
  CHECK(PM_ST_ManualGuardFrame());CHECK(ps.torsoAnim==100+family);
  CHECK(PM_ST_ManualGuardFrame());CHECK(draws==1); /* held pose does not restart */
  before.torsoAnim=ps.torsoAnim;CHECK(!memcmp(&before,&ps,sizeof ps));
  CHECK(!memcmp(&command,&pm->cmd,sizeof command)); /* no movement/input rewrite */
  pm->cmd.buttons=0;CHECK(!PM_ST_ManualGuardFrame());CHECK(ps.torsoAnim==50);
  CHECK(!ps.weaponTime && !ps.torsoTimer && ps.legsAnim==60 && ps.legsTimer==100);
 }
 for(mode=0;mode<=3;mode++)for(active=0;active<=1;active++){
  reset();BG_ST_SetManualGuard(mode,active);
  CHECK(PM_ST_ManualGuardFrame()==(mode==2 || (mode==1&&active)));
 }
 for(i=0;i<22;i++){
  if(i==8)continue;
  reset();CHECK(PM_ST_ManualGuardFrame());
  switch(i){
   case 0:pm->cmd.buttons|=BUTTON_ATTACK;break;
   case 1:pm->cmd.buttons|=BUTTON_ALT_ATTACK;break;
   case 2:pm->cmd.buttons|=BUTTON_FEINT;break;
   case 3:pm->cmd.buttons|=BUTTON_TALK;break;
   case 4:ps.weaponTime=100;break;
   case 5:ps.saberMove=30;break;
   case 6:ps.stCombat.recoveryMs=200;break;
   case 7:ps.stHybrid.recoveryMs=400;break;

   case 9:ps.saberInFlight=1;break;
   case 10:ps.saberHolstered=2;break;
   case 11:ps.saberEntityNum=0;break;
   case 12:ps.forceHandExtend=1;break;
   case 13:ps.stats[ST_STAFF_STAT]=1;break;
   case 14:ps.stCombatFlags=STC_GUARD_PAUSED;break;
   case 15:ps.saberLockTime=2000;break;
   case 16:ps.weaponstate=WEAPON_RAISING;break;
   case 17:ps.fd.forcePowerLevel[FP_SABER_DEFENSE]=0;ps.fd.forcePowersKnown=0;break;
   case 18:rolling=1;break;
   case 19:knocked=1;break;
   case 20:ps.m_iVehicleNum=1;break;
   case 21:pm->cmd.weapon=3;break;
  }
  before=ps;CHECK(!PM_ST_ManualGuardFrame());CHECK(ps.torsoAnim==50);
  before.torsoAnim=ps.torsoAnim;CHECK(!memcmp(&before,&ps,sizeof ps));
 }
 reset();ps.saberMove=LS_PARRY_UP;ps.torsoAnim=70;ps.torsoTimer=150;
 CHECK(!PM_ST_ManualGuardFrame());CHECK(ps.torsoAnim==70 && ps.torsoTimer==150);
 reset();anims[100].numFrames=0;CHECK(!PM_ST_ManualGuardFrame());CHECK(ps.torsoAnim==50);
 reset();pm->cmd.upmove=-127;CHECK(PM_ST_ManualGuardFrame()); /* crouch remains available */
 reset();pm->cmd.upmove=127;CHECK(PM_ST_ManualGuardFrame()); /* normal jump remains available */
 printf("Held guard production adapter: %d checks passed.\n",checks);return 0;
}
