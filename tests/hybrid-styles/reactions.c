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
      LS_A_L2R=11,LS_A_BL2TR=12,LS_A_BR2TL=13,LS_A_R2L=14,LS_A_TR2BL=15,LS_A_T2B=16,LS_R_TL2BR=30,LS_R_T2B=36,LS_R_BL2TR=32,LS_R_BR2TL=33,LS_T_LINK=50,LS_S_TL2BR=60,LS_S_T2B=66,BLK_NO=0,
      BUTTON_ATTACK=1,BUTTON_ALT_ATTACK=2,BUTTON_FEINT=4096};
typedef struct {int type,numBlades;} saberInfo_t;
typedef struct {int saberAnimLevel,saberDrawAnimLevel,saberAnimLevelBase,forcePowerLevel[1];} forcedata;
typedef struct {int serverTime,buttons,weapon;} usercmd_t;
typedef struct {STH_State stHybrid;STC_State stCombat;int stCombatFlags,clientNum,pm_type,weapon;
 int saberHolstered,saberInFlight,forceHandExtend,stats[4],saberLockTime,saberLockFrame;
 int weaponstate,legsAnim,torsoAnim,torsoTimer,saberMove,saberBlocked,saberBlocking,weaponTime,saberAttackChainCount,m_iVehicleNum;forcedata fd;} playerState_t;
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
static int PM_ST_HybridCanMove(int move);
static void PM_ST_HybridMove(int move);
static void PM_SetSaberMove(short move);
#include "bg_st_hybrid.inc"

enum {BLOCKED_NONE=0,BLOCKED_BOUNCE_MOVE=1,BLOCKED_PARRY_BROKEN=2,BLOCKED_ATK_BOUNCE=3,
 BLOCKED_UPPER_RIGHT=4,BLOCKED_UPPER_LEFT=5,BLOCKED_LOWER_RIGHT=6,BLOCKED_LOWER_LEFT=7,BLOCKED_TOP=8,
 BLOCKED_UPPER_RIGHT_PROJ=9,BLOCKED_UPPER_LEFT_PROJ=10,BLOCKED_LOWER_RIGHT_PROJ=11,BLOCKED_LOWER_LEFT_PROJ=12,BLOCKED_TOP_PROJ=13,
 LS_T1_BR__R=70,LS_BOUNCE=75,LS_BROKEN=80,LS_PARRY_UR=90,LS_PARRY_UL=91,LS_PARRY_LR=92,LS_PARRY_LL=93,LS_PARRY_UP=94,
 LS_REFLECT_UR=100,LS_REFLECT_UL=101,LS_REFLECT_LR=102,LS_REFLECT_LL=103,LS_REFLECT_UP=104,
 FP_SABER_DEFENSE=0,WEAPON_READY=1,WEAPON_FIRING=2,WEAPON_IDLE=3,Q_BR=0,Q_T=3,Q_TL=4,Q_BL=6};
typedef int saberMoveName_t;
static struct {int startQuad,chain_attack,chain_idle,blocking;} saberMoveData[128];
static int transitionMove[8][8],bg_parryDebounce[4]={150,150,150,150};
static struct {int msec;} pml;
static int PM_SaberInBounce(int move){return move==LS_BOUNCE;}
static int PM_SaberInBrokenParry(int move){return move==LS_BROKEN;}
static int PM_BrokenParryForParry(int move){(void)move;return LS_BROKEN;}
static int PM_SaberBounceForAttack(saberMoveName_t move){(void)move;return LS_BOUNCE;}
static int PM_SaberMoveQuadrantForMovement(usercmd_t* cmd){(void)cmd;return Q_T;}
static int PM_irand_timesync(int lo,int hi){(void)lo;return hi;}
static void PM_SetSaberMove(short move) {
 if(!PM_ST_HybridCanMove(move))return;
 pm->ps->saberMove=move;pm->ps->torsoAnim=move==LS_READY?701:700;pm->ps->torsoTimer=100;
 PM_ST_HybridMove(move);
 #include "reaction_blocking.inc"
 returnAnimations++;
}
#include "reaction_fixture.inc"
static int checks;
#define CHECK(x) do{++checks;if(!(x)){fprintf(stderr,"reaction:%d %s\n",__LINE__,#x);exit(1);}}while(0)
static playerState_t state;
static void reset(void) {
 memset(&state,0,sizeof(state));memset(pm,0,sizeof(*pm));pm->ps=&state;
 STH_Init(&state.stHybrid,1000,1);state.stHybrid.allowedMask=1u<<5;
 state.stHybrid.style=state.stHybrid.requestedStyle=5;
 state.fd.saberAnimLevel=1;state.weapon=WP_SABER;state.stats[STAT_HEALTH]=100;
 state.saberMove=LS_A_TL2BR;state.torsoAnim=99;state.torsoTimer=300;state.weaponTime=300;
 pm->cmd.serverTime=1000;pm->cmd.weapon=WP_SABER;pm->cmd.buttons=BUTTON_ATTACK;
 {int i;for(i=0;i<128;i++)saberMoveData[i].blocking=1;}
 returnAnimations=hasSecond=0;PM_ST_HybridMove(LS_A_TL2BR);
 CHECK(state.stHybrid.committed);
}
static void step(int now) {
 pml.msec=now-pm->cmd.serverTime;pm->cmd.serverTime=now;
 if(state.torsoTimer>0) {state.torsoTimer-=pml.msec;if(state.torsoTimer<0)state.torsoTimer=0;}
 if(!PM_ST_HybridFrame())ProductionWeaponReactions();
}
int main(void) {
 int block;
 for(block=BLOCKED_BOUNCE_MOVE;block<=BLOCKED_TOP_PROJ;block++) {
  reset();state.saberBlocked=block;
  if(block==BLOCKED_BOUNCE_MOVE)state.saberMove=LS_BOUNCE;
  step(1100);
  CHECK(state.stHybrid.recoveryMs==350&&!state.stHybrid.committed);
  CHECK(state.saberBlocked==0&&returnAnimations==1);
  CHECK(state.saberMove!=LS_A_TL2BR);CHECK(state.saberBlocking==BLK_NO);
  CHECK(!(pm->cmd.buttons&BUTTON_ATTACK));
  CHECK(!PM_ST_HybridCanMove(LS_A_L2R));
  if(block==BLOCKED_PARRY_BROKEN)CHECK(state.saberMove==LS_BROKEN);
  if(block==BLOCKED_ATK_BOUNCE)CHECK(state.saberMove==LS_BOUNCE);
 }
 /* Normal strike return/ready continues while the independent debt is active. */
 reset();pm->cmd.buttons=0;step(1300);
 CHECK(state.stHybrid.recoveryMs==350&&state.saberMove==LS_R_TL2BR&&returnAnimations==1);
 step(1400);CHECK(state.stHybrid.recoveryMs==250&&state.saberMove==LS_READY&&returnAnimations==2);
 CHECK(state.saberBlocking==BLK_NO);
 /* External pain timer is decayed by the stock path exactly once. */
 reset();state.torsoAnim=500;state.weaponTime=900;step(1100);
 CHECK(state.torsoAnim==500&&state.weaponTime==800&&state.stHybrid.recoveryMs==350);
 /* Frozen frames do not enter the normal weapon path or consume the debt. */
 state.pm_type=PM_FREEZE;step(1200);CHECK(state.weaponTime==800&&state.stHybrid.recoveryMs==350);
 printf("production weapon reactions: %d checks passed\n",checks);return 0;
}
