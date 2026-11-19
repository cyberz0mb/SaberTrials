/* Compiles the production adapter with explicit animation/engine seams. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "st_combat_core.h"
#include "st_combat_wire.h"
typedef int qboolean;
#define qtrue 1
#define qfalse 0
enum {PM_NORMAL,PM_FREEZE,PM_NOCLIP,PM_DEAD,PM_SPECTATOR};
enum {WP_SABER=2,SS_FAST=1,SS_MEDIUM,SS_STRONG,SABER_SINGLE=1,
 LS_READY=1,LS_S_TL2BR=10,LS_S_T2B=16,LS_A_TL2BR=20,LS_A_T2B=26,
 STAT_HEALTH=0,ENTITYNUM_NONE=1023,HANDEXTEND_NONE=0,PMF_DUCKED=1,
 ST_STAFF_STAT=15,ST_STAFF_GHOST=2,ST_STAFF_FROZEN=1,
 BUTTON_ATTACK=1,BUTTON_ALT_ATTACK=128,BUTTON_FEINT=4096,
 SETANIM_TORSO=1,SETANIM_BOTH=3,SETANIM_FLAG_OVERRIDE=1,SETANIM_FLAG_HOLD=2};
typedef struct {int type,numBlades;} saberInfo_t;
typedef struct {
 STC_State stCombat;int stCombatFlags;
 int stats[16],weapon,saberHolstered,saberInFlight,saberLockTime,saberLockFrame,
 saberBlocked,forceHandExtend,m_iVehicleNum,groundEntityNum,pm_flags,pm_type,
 saberMove,torsoTimer,legsTimer,weaponTime,clientNum,legsAnim;
 struct {int saberAnimLevel;} fd;
} playerState_t;
typedef struct {int serverTime,buttons,forwardmove,rightmove,upmove,weapon;} usercmd_t;
typedef struct {playerState_t* ps;usercmd_t cmd;} pmove_t;
static pmove_t movement,*pm=&movement;static playerState_t ps;
static saberInfo_t saber={SABER_SINGLE,1};static int second,failAnimation,draws,knocked,rolling;
static saberInfo_t* BG_MySaber(int client,int n){(void)client;return n?(second?&saber:NULL):&saber;}
static int PM_InKnockDown(playerState_t* s){(void)s;return knocked;}
static int BG_InRoll(playerState_t* s,int anim){(void)s;(void)anim;return rolling;}
/* Production adapter's start/commit hook is called only on real success. */
static void PM_ST_FeintMove(int move);
static void PM_SetSaberMove(short move){
 if(failAnimation)return;
 ps.saberMove=move;ps.torsoTimer=move>=LS_S_TL2BR&&move<=LS_S_T2B?200:0;
 PM_ST_FeintMove(move);
}
static int PM_GetSaberStance(void){return 9;}
static void PM_SetAnim(int parts,int anim,int flags){(void)parts;(void)anim;(void)flags;draws++;}
#include "bg_st_feint.inc"
enum {TEAM_SPECTATOR=3,ST_TOURNAMENT_PAUSED=3};
typedef struct {playerState_t ps;struct {usercmd_t cmd;} pers;struct {int sessionTeam;} sess;} gclient_t;
typedef struct {gclient_t* client;int health;} gentity_t;
static struct {int time,stTournamentPhase;} level;
#include "g_st_feint.inc"
#define CHECK(x) do {++checks;if(!(x)){fprintf(stderr,"line %d: %s\n",__LINE__,#x);exit(1);}} while(0)
static int checks;
static void reset(void){
 memset(&ps,0,sizeof(ps));memset(&movement,0,sizeof(movement));pm->ps=&ps;
 ps.stats[STAT_HEALTH]=100;ps.weapon=pm->cmd.weapon=WP_SABER;
 ps.fd.saberAnimLevel=1;ps.pm_type=PM_NORMAL;ps.saberMove=LS_READY;
 second=failAnimation=draws=knocked=rolling=0;pm->cmd.serverTime=1000;
 STC_Init(&ps.stCombat,1,1000);PM_SetSaberMove(LS_S_TL2BR);ps.weaponTime=200;
}
int main(void){
 STC_State saved;
 reset();CHECK(ps.stCombat.phase==STC_WINDUP && ps.stCombat.windupMs==200);
 pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_ATTACK|BUTTON_FEINT;
 pm->cmd.rightmove=-127;pm->cmd.forwardmove=127;
 CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.phase==STC_RECOVERY);
 CHECK(ps.stCombat.redirect==STC_TR_BL && ps.weaponTime>=200 && draws>0);
 saved=ps.stCombat;CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.attack==saved.attack);
 pm->cmd.serverTime=1249;CHECK(PM_ST_FeintFrame());CHECK(ps.saberMove==LS_READY);
 CHECK(ps.weaponTime==1);
 pm->cmd.serverTime=1250;CHECK(PM_ST_FeintFrame());
 CHECK(ps.saberMove==LS_S_TL2BR+STC_TR_BL && ps.stCombat.phase==STC_WINDUP);
 CHECK(ps.stCombat.attack==1 && ps.stCombat.feintsUsed==1 && ps.weaponTime==200);
 PM_SetSaberMove(LS_A_TL2BR+STC_TR_BL);CHECK(ps.stCombat.phase==STC_ACTIVE);
 reset();STC_Contact(&ps.stCombat);pm->cmd.serverTime=1050;
 pm->cmd.buttons=BUTTON_ATTACK|BUTTON_FEINT;pm->cmd.rightmove=-127;
 CHECK(!PM_ST_FeintFrame());CHECK(ps.stCombat.phase==STC_WINDUP);
 reset();pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT|BUTTON_ATTACK;pm->cmd.rightmove=-127;
 CHECK(PM_ST_FeintFrame());ps.saberHolstered=2;ps.weaponTime=0;
 pm->cmd.serverTime=1100;CHECK(PM_ST_FeintFrame());CHECK(ps.weaponTime>=150);
 ps.saberHolstered=0;pm->cmd.serverTime=1250;CHECK(!PM_ST_FeintFrame());
 CHECK(ps.stCombat.phase==STC_CANCELLED);
 reset();pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT|BUTTON_ATTACK;pm->cmd.rightmove=-127;
 CHECK(PM_ST_FeintFrame());failAnimation=1;pm->cmd.serverTime=1250;
 CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.phase==STC_CANCELLED);
 reset();second=1;pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT;pm->cmd.rightmove=-127;
 CHECK(!PM_ST_FeintFrame());CHECK(ps.stCombat.feintsUsed==0);
 reset();knocked=1;pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT;pm->cmd.rightmove=-127;
 CHECK(!PM_ST_FeintFrame());CHECK(!ps.stCombat.feintsUsed);
 reset();rolling=1;pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT;pm->cmd.rightmove=-127;
 CHECK(!PM_ST_FeintFrame());CHECK(!ps.stCombat.feintsUsed);
 reset();memset(&ps.stCombat,0,sizeof(ps.stCombat));saved=ps.stCombat;
 CHECK(!PM_ST_FeintFrame());CHECK(!memcmp(&saved,&ps.stCombat,sizeof(saved)));
 /* Failed withdrawal still pays recovery and never redirects a failed pose. */
 reset();failAnimation=1;pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT|BUTTON_ATTACK;pm->cmd.rightmove=-127;
 CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.phase==STC_RECOVERY);
 CHECK(ps.stCombat.redirect==STC_DIRECTION_NONE && ps.weaponTime==200);
 pm->cmd.serverTime=1250;CHECK(!PM_ST_FeintFrame());CHECK(ps.weaponTime==0);
 /* Inputs received while frozen/paused cannot become fresh presses on return. */
 reset();pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT|BUTTON_ATTACK;pm->cmd.rightmove=-127;
 BG_ST_FeintStopped(&ps,&pm->cmd,STC_GUARD_FROZEN);
 pm->cmd.serverTime=1100;CHECK(!PM_ST_FeintFrame());CHECK(!ps.stCombat.feintsUsed && ps.stCombat.held);
 reset();pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT|BUTTON_ATTACK;pm->cmd.rightmove=-127;
 CHECK(PM_ST_FeintFrame());pm->cmd.serverTime=2050;
 BG_ST_FeintStopped(&ps,&pm->cmd,STC_GUARD_PAUSED);
 CHECK(ps.stCombat.recoveryMs==200 && ps.stCombat.cooldownMs==600);
 pm->cmd.serverTime=2150;CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.recoveryMs==100);
 pm->cmd.serverTime=2250;CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.phase==STC_WINDUP);
 /* Weapon switching cannot skip the paid recovery, or resume the redirect. */
 reset();pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT|BUTTON_ATTACK;pm->cmd.rightmove=-127;
 CHECK(PM_ST_FeintFrame());pm->cmd.weapon=3;pm->cmd.serverTime=1100;
 CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.recoveryMs==150 && ps.stCombat.redirect==STC_DIRECTION_NONE);
 pm->cmd.serverTime=1250;CHECK(!PM_ST_FeintFrame());CHECK(ps.weaponTime==0);
 /* All three normal single styles, all redirected directions, exact replay. */
 {
  int style,dir,i;
  playerState_t snapshot,expected;
  const int right[7]={127,127,127,-127,-127,-127,0};
  const int forward[7]={127,0,-127,-127,0,127,0};
  for(style=1;style<=3;style++)for(dir=1;dir<7;dir++) {
   reset();ps.fd.saberAnimLevel=style;
   STC_Init(&ps.stCombat,1,1000);PM_SetSaberMove(LS_S_TL2BR);ps.weaponTime=200;
   snapshot=ps;pm->cmd.rightmove=right[dir];pm->cmd.forwardmove=forward[dir];
   pm->cmd.buttons=BUTTON_ATTACK|BUTTON_FEINT;pm->cmd.serverTime=1050;
   CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.redirect==dir);snapshot=ps;
   for(i=1;i<=4;i++){pm->cmd.serverTime=1050+50*i;CHECK(PM_ST_FeintFrame());}
   expected=ps;ps=snapshot;
   for(i=1;i<=4;i++){pm->cmd.serverTime=1050+50*i;CHECK(PM_ST_FeintFrame());}
   CHECK(!memcmp(&expected,&ps,sizeof(ps)));CHECK(STC_StateValid(&ps.stCombat));
  }
 }
 /* Authoritative contact correction removes a locally predicted redirect. */
 reset();{
  playerState_t authoritative=ps;
  pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT|BUTTON_ATTACK;pm->cmd.rightmove=-127;
  CHECK(PM_ST_FeintFrame());ps=authoritative;STC_Contact(&ps.stCombat);
  CHECK(!PM_ST_FeintFrame());CHECK(!ps.stCombat.feintsUsed && ps.stCombat.contacted);
 }
 /* Actual server early-return hook must sanitize before consuming raw input. */
 {
  int pause;
  for(pause=0;pause<2;pause++) {
   gclient_t client;gentity_t entity;
   reset();pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT|BUTTON_ATTACK;pm->cmd.rightmove=-127;
   CHECK(PM_ST_FeintFrame());memset(&client,0,sizeof(client));client.ps=ps;client.pers.cmd=pm->cmd;
   entity.client=&client;entity.health=100;level.time=1100;level.stTournamentPhase=pause?ST_TOURNAMENT_PAUSED:0;
   client.ps.stats[ST_STAFF_STAT]=pause?0:ST_STAFF_FROZEN;
   client.pers.cmd.serverTime=1000000;G_STFeintStoppedState(&entity);
   CHECK(client.ps.stCombat.lastTime<=1300 && client.ps.stCombat.lastInputTime<=1300);
   CHECK(client.ps.stCombat.held && client.ps.stCombat.recoveryMs==200);
   CHECK(client.pers.cmd.serverTime==1000000); /* caller command remains intact */
   client.ps.stats[ST_STAFF_STAT]=0;level.stTournamentPhase=0;
   client.pers.cmd.serverTime=1350;G_STFeintStoppedState(&entity);
   ps=client.ps;pm->cmd.serverTime=1350;CHECK(PM_ST_FeintFrame());
   CHECK(ps.stCombat.recoveryMs==150);pm->cmd.serverTime=1500;
   CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.phase==STC_WINDUP);
  }
 }
 printf("Production feint adapter: %d checks passed.\n",checks);return 0;
}
