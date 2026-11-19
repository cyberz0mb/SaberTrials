#include "st_hybrid.h"
#include "st_combat_core.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef int qboolean;
enum {qfalse,qtrue};
enum {SABER_SINGLE=1,SS_FAST=1,SS_STRONG=3,SS_DESANN=4,SS_TAVION=5,SS_DUAL=6,SS_STAFF=7,
      FORCE_LEVEL_1=1,FORCE_LEVEL_2=2,FORCE_LEVEL_3=3,WP_SABER=2,PM_NORMAL=0,PM_FREEZE=1,
      STAT_HEALTH=0,HANDEXTEND_NONE=0,LS_NONE=0,LS_READY=1,LS_A_TL2BR=10,
      LS_A_L2R=11,LS_A_BL2TR=12,LS_A_BR2TL=13,LS_A_R2L=14,LS_A_TR2BL=15,LS_A_T2B=16,LS_R_TL2BR=30,LS_R_T2B=36,LS_T_LINK=50,LS_S_TL2BR=60,BLK_NO=0,
      BUTTON_ATTACK=1,BUTTON_ALT_ATTACK=2,BUTTON_FEINT=4096};
typedef struct {int type,numBlades;} saberInfo_t;
typedef struct {int saberAnimLevel,saberDrawAnimLevel,saberAnimLevelBase;} forcedata;
typedef struct {int serverTime,buttons,weapon;} usercmd_t;
typedef struct {STH_State stHybrid;STC_State stCombat;int stCombatFlags,clientNum,pm_type,weapon;
 int saberHolstered,saberInFlight,forceHandExtend,stats[4],saberLockTime,saberLockFrame;
 int legsAnim,torsoAnim,torsoTimer,saberMove,saberBlocked,saberBlocking,weaponTime,saberAttackChainCount,m_iVehicleNum;forcedata fd;} playerState_t;
typedef struct {playerState_t* ps;usercmd_t cmd;} pmove_t;
static pmove_t context,*pm=&context;
static saberInfo_t saber={SABER_SINGLE,1},second;
static int hasSecond,returnAnimations;
static saberInfo_t* BG_MySaber(int client,int index){(void)client;return index?(hasSecond?&second:NULL):&saber;}
static int BG_SaberInAttack(int move){return (move>=10&&move<=16)||move==20;}
static int BG_SaberInSpecial(int move){return move==20;}
static int BG_KickMove(int move){return move==21;}
static int PM_InKnockDown(playerState_t* ps){return ps->legsAnim==800;}
static int BG_InRoll(playerState_t* ps,int anim){(void)ps;return anim==801;}
static int PM_SaberInStart(int move){return move>=60&&move<=66;}
static int PM_SaberInTransition(int move){return move==LS_T_LINK;}
static int PM_SaberInReturn(int move){return move>=30&&move<=36;}
static int STH_AnimStyle(int anim){return anim==700?STH_PURPLE:0;}
static void PM_SetSaberMove(short move){pm->ps->saberMove=move;pm->ps->torsoAnim=move==LS_READY?701:700;pm->ps->torsoTimer=100;returnAnimations++;}
#include "bg_st_hybrid.inc"
#ifdef STH_CHAIN_FIXTURE
static int PM_irand_timesync(int lo,int hi){(void)hi;return lo;}
static int PM_SaberAttackChainAngle(int a,int b){(void)a;(void)b;return 180;}
#include "chain_fixture.inc"
#endif
static int checks;
#define CHECK(x) do {checks++;if(!(x)){fprintf(stderr,"adapter:%d %s\n",__LINE__,#x);exit(1);}}while(0)
static playerState_t state;
static void reset(void){memset(&state,0,sizeof(state));memset(pm,0,sizeof(*pm));pm->ps=&state;
 STH_Init(&state.stHybrid,1000,1);state.stHybrid.allowedMask=STH_AllowedStyles(3,0,0,0,1);state.stHybrid.style=state.stHybrid.requestedStyle=5;
 state.fd.saberAnimLevel=1;state.weapon=WP_SABER;state.stats[0]=100;
 state.saberMove=LS_A_TL2BR;state.torsoAnim=99;state.torsoTimer=300;state.weaponTime=300;
 pm->cmd.serverTime=1000;pm->cmd.weapon=WP_SABER;pm->cmd.buttons=0;
 hasSecond=returnAnimations=0;PM_ST_HybridMove(LS_A_TL2BR);CHECK(state.stHybrid.committed);
}
int main(void){
 reset();pm->cmd.serverTime=1300;state.torsoTimer=state.weaponTime=0;
 CHECK(!PM_ST_HybridFrame());CHECK(state.stHybrid.recoveryMs==350);CHECK(returnAnimations==0);
 CHECK(!(pm->cmd.buttons&BUTTON_ATTACK));CHECK(state.saberBlocking==BLK_NO);
 CHECK(!state.stCombat.epoch); /* recovery does not require feints */
 state.weaponTime=1500;pm->cmd.serverTime=1400;CHECK(!PM_ST_HybridFrame());CHECK(state.weaponTime==1500);
 state.pm_type=PM_FREEZE;pm->cmd.serverTime=1800;CHECK(PM_ST_HybridFrame());CHECK(state.stHybrid.recoveryMs==250);
 state.pm_type=PM_NORMAL;state.weapon=3;STH_Request(&state.stHybrid,0);pm->cmd.serverTime=1900;
 CHECK(!PM_ST_HybridFrame());CHECK(state.stHybrid.style==5&&state.stHybrid.recoveryMs==150);
 reset();state.torsoAnim=500;state.weaponTime=900;pm->cmd.serverTime=1100;
 CHECK(!PM_ST_HybridFrame());CHECK(state.stHybrid.recoveryMs==350);CHECK(state.torsoAnim==500&&state.weaponTime==900);
 reset();state.saberHolstered=1;pm->cmd.serverTime=1100;CHECK(!PM_ST_HybridFrame());CHECK(state.stHybrid.recoveryMs==350);
 reset();state.weapon=3;pm->cmd.serverTime=1100;CHECK(!PM_ST_HybridFrame());CHECK(state.stHybrid.recoveryMs==350);
 reset();state.stCombatFlags=STC_GUARD_PAUSED;pm->cmd.serverTime=1800;
 CHECK(PM_ST_HybridFrame());CHECK(state.stHybrid.strikeMs==300&&!state.stHybrid.recoveryMs);
 state.stCombatFlags=0;pm->cmd.serverTime=1900;CHECK(!PM_ST_HybridFrame());CHECK(state.stHybrid.strikeMs==200);
 reset();hasSecond=1;pm->cmd.serverTime=1100;CHECK(!PM_ST_HybridFrame());CHECK(state.stHybrid.recoveryMs==350);
 reset();state.stHybrid.allowedMask=0;state.stHybrid.originalStyle=3;state.fd.saberAnimLevel=2;
 state.stHybrid.committed=0;state.stHybrid.strikeMs=0;state.saberMove=LS_READY;state.weaponTime=state.torsoTimer=0;
 pm->cmd.serverTime=1100;CHECK(!PM_ST_HybridFrame());CHECK(!state.stHybrid.style&&state.fd.saberAnimLevel==2);
 reset();state.stHybrid.allowedMask=1u<<4;state.stHybrid.originalStyle=3;state.fd.saberAnimLevel=2;
 state.stHybrid.committed=0;state.stHybrid.strikeMs=0;state.saberMove=LS_READY;state.weaponTime=state.torsoTimer=0;
 pm->cmd.serverTime=1100;CHECK(!PM_ST_HybridFrame());CHECK(!state.stHybrid.style&&state.fd.saberAnimLevel==2);
 reset();STH_Init(&state.stHybrid,1000,0);pm->cmd.serverTime=5000;CHECK(!PM_ST_HybridFrame());CHECK(!state.stHybrid.clockSet);
#ifdef STH_CHAIN_FIXTURE
 reset();state.stHybrid.style=4;state.fd.saberAnimLevel=2;state.saberAttackChainCount=4;
 CHECK(!PM_SaberKataDone(LS_A_TL2BR,LS_A_T2B));hasSecond=1;
 CHECK(PM_SaberKataDone(LS_A_TL2BR,LS_A_T2B));
 reset();state.saberAttackChainCount=2;CHECK(PM_SaberKataDone(LS_A_TL2BR,LS_A_T2B));
 hasSecond=1;CHECK(!PM_SaberKataDone(LS_A_TL2BR,LS_A_T2B));
#endif
 /* Production adapter offers exactly one follow-up with Attack held. */
 reset();pm->cmd.buttons=BUTTON_ATTACK;
 CHECK(!PM_ST_HybridCanMove(LS_A_L2R));CHECK(!PM_ST_HybridCanMove(20));
 CHECK(!PM_ST_HybridCanMove(LS_T_LINK));
 pm->cmd.serverTime=1300;state.torsoTimer=0;state.weaponTime=0;
 CHECK(!PM_ST_HybridFrame());CHECK(STH_CanFollowup(&state.stHybrid));
 CHECK(PM_ST_HybridCanMove(LS_A_L2R));CHECK(PM_ST_HybridCanMove(LS_T_LINK));
 CHECK(!PM_ST_HybridCanMove(20));CHECK(!PM_ST_HybridCanMove(LS_S_TL2BR));
 state.saberMove=LS_T_LINK;state.torsoAnim=150;state.torsoTimer=100;
 PM_ST_HybridMove(LS_T_LINK);CHECK(state.stHybrid.chainPending==2&&!state.stHybrid.committed);
 CHECK(!PM_ST_HybridCanMove(LS_A_L2R));
 pm->cmd.serverTime=1400;state.torsoTimer=0;state.weaponTime=0;
 CHECK(!PM_ST_HybridFrame());CHECK(PM_ST_HybridCanMove(LS_A_L2R));
 CHECK(!PM_ST_HybridCanMove(LS_T_LINK)); /* cannot keep reconnecting indefinitely */
 state.saberMove=LS_A_L2R;state.torsoAnim=100;state.torsoTimer=300;
 PM_ST_HybridMove(LS_A_L2R);CHECK(state.stHybrid.comboCount==2&&state.stHybrid.committed);
 CHECK(!PM_ST_HybridCanMove(LS_A_R2L));
 pm->cmd.serverTime=1700;state.torsoTimer=0;state.weaponTime=0;
 CHECK(!PM_ST_HybridFrame());CHECK(state.stHybrid.recoveryMs==350&&returnAnimations==0);
 CHECK(!PM_ST_HybridCanMove(LS_A_R2L));CHECK(!PM_ST_HybridCanMove(LS_T_LINK));
 pm->cmd.serverTime=1800;state.torsoTimer=0;
 CHECK(!PM_ST_HybridFrame());CHECK(state.saberMove==LS_A_L2R&&state.torsoAnim==100); /* stock weapon path owns pose changes */
 CHECK(state.stHybrid.recoveryMs==250&&returnAnimations==0); /* debt never manufactures an extra weapon delay */
 /* Torso duration and strike clock can finish on different frames. Return
    must not depend on their becoming zero on exactly the same frame. */
 reset();pm->cmd.serverTime=1300;state.torsoTimer=1;state.weaponTime=0;
 CHECK(!PM_ST_HybridFrame());CHECK(returnAnimations==0);
 pm->cmd.serverTime=1310;state.torsoTimer=0;
 CHECK(!PM_ST_HybridFrame());CHECK(returnAnimations==0);
 /* Interrupt on the exact completion frame cannot open a combo. */
 reset();pm->cmd.buttons=BUTTON_ATTACK;pm->cmd.serverTime=1300;state.torsoAnim=500;
 CHECK(!PM_ST_HybridFrame());CHECK(state.stHybrid.recoveryMs==350&&!state.stHybrid.chainPending);
 CHECK(state.torsoAnim==500);
 /* Damage/stun during the link also keeps recovery owed. */
 reset();pm->cmd.buttons=BUTTON_ATTACK;pm->cmd.serverTime=1300;state.torsoTimer=0;
 CHECK(!PM_ST_HybridFrame());state.saberMove=LS_T_LINK;state.torsoAnim=150;state.torsoTimer=100;
 PM_ST_HybridMove(LS_T_LINK);state.forceHandExtend=1;pm->cmd.serverTime=1350;
 CHECK(!PM_ST_HybridFrame());CHECK(state.stHybrid.recoveryMs==350&&!state.stHybrid.chainPending);
 /* Pending weapon changes, rolls and saber bounces cannot buy a free second swing. */
 {int guard;for(guard=0;guard<5;guard++) {
  reset();pm->cmd.buttons=BUTTON_ATTACK;pm->cmd.serverTime=1300;state.torsoTimer=0;
  if(guard==0)pm->cmd.weapon=3;
  if(guard==1)state.saberBlocked=1;
  if(guard==2)state.legsAnim=800;
  if(guard==3)state.legsAnim=801;
  if(guard==4)state.stats[STAT_HEALTH]=0;
  CHECK(!PM_ST_HybridFrame());CHECK(!state.stHybrid.chainPending&&state.stHybrid.recoveryMs==350);
  CHECK(!returnAnimations);
 }}
 /* A mixed loadout switches the actual parent family only at a safe boundary. */
 reset();
 {int32_t slots[3]={2,5,6};
  STH_SetLoadout(&state.stHybrid,slots);state.stHybrid.availableMask=126;
  state.stHybrid.selectedStyle=state.stHybrid.requestedSelection=5;
  CHECK(STH_RequestSelection(&state.stHybrid,2));
  pm->cmd.serverTime=1100;CHECK(!PM_ST_HybridFrame());
  CHECK(state.stHybrid.style==5&&state.fd.saberAnimLevel==1);
  state.torsoTimer=state.weaponTime=0;pm->cmd.serverTime=1300;
  CHECK(!PM_ST_HybridFrame());CHECK(state.stHybrid.recoveryMs==350);
  CHECK(state.stHybrid.style==5&&state.fd.saberAnimLevel==1);
  state.torsoTimer=0;state.saberMove=LS_READY;pm->cmd.serverTime=1950;
  CHECK(!PM_ST_HybridFrame());
  CHECK(state.stHybrid.selectedStyle==2&&!state.stHybrid.style&&state.fd.saberAnimLevel==2);
  CHECK(state.fd.saberDrawAnimLevel==2&&state.fd.saberAnimLevelBase==2);
  CHECK(STH_RequestSelection(&state.stHybrid,6));state.weaponTime=250;
  pm->cmd.serverTime=2000;CHECK(!PM_ST_HybridFrame());CHECK(state.fd.saberAnimLevel==2);
  state.weaponTime=state.torsoTimer=0;pm->cmd.serverTime=2100;CHECK(!PM_ST_HybridFrame());
  CHECK(state.stHybrid.selectedStyle==6&&state.stHybrid.style==6&&state.fd.saberAnimLevel==3);
  /* Weapon changes suspend hybrids, and switching back must restore the chosen identity. */
  hasSecond=1;pm->cmd.serverTime=2200;CHECK(!PM_ST_HybridFrame());CHECK(!state.stHybrid.style);
  hasSecond=0;state.fd.saberAnimLevel=1;pm->cmd.serverTime=2300;
  CHECK(!PM_ST_HybridFrame());CHECK(state.stHybrid.style==6&&state.fd.saberAnimLevel==3);
  CHECK(STH_RequestSelection(&state.stHybrid,2));pm->cmd.serverTime=2400;
  CHECK(!PM_ST_HybridFrame());CHECK(state.fd.saberAnimLevel==2);
  hasSecond=1;state.fd.saberAnimLevel=6;pm->cmd.serverTime=2500;
  CHECK(!PM_ST_HybridFrame());CHECK(state.fd.saberAnimLevel==6);
  hasSecond=0;state.fd.saberAnimLevel=1;pm->cmd.serverTime=2600;
  CHECK(!PM_ST_HybridFrame());CHECK(state.fd.saberAnimLevel==2);
 }
 printf("hybrid production adapter: %d checks passed\n",checks);return 0;
}
