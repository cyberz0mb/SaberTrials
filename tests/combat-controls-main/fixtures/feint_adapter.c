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
 saberMove,torsoTimer,legsTimer,weaponTime,clientNum,legsAnim,commandTime;
 struct {int saberAnimLevel;} fd;
 struct {int style;} stHybrid;
} playerState_t;
typedef struct {int serverTime,buttons,forwardmove,rightmove,upmove,weapon;} usercmd_t;
typedef struct {playerState_t* ps;usercmd_t cmd;} pmove_t;
static pmove_t movement,*pm=&movement;static playerState_t ps;
static saberInfo_t saber={SABER_SINGLE,1};static int second,failAnimation,draws,knocked,rolling,lastParts;
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
static void PM_SetAnim(int parts,int anim,int flags){lastParts=parts;(void)anim;(void)flags;draws++;}
#include "bg_st_feint.inc"
#include "feint_clock_fixture.inc"
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
 second=failAnimation=draws=knocked=rolling=0;ps.commandTime=pm->cmd.serverTime=1000;
 STC_Init(&ps.stCombat,1,1000);PM_SetSaberMove(LS_S_TL2BR);ps.weaponTime=200;
}
static void mobility(void) {
 const int styles[]={1,2,3,4,6};int i,context,changing,repeat;
 for(i=0;i<5;i++)for(context=1;context<5;context++)for(changing=0;changing<2;changing++) {
  reset();STC_Init(&ps.stCombat,1,1000);
  ps.stHybrid.style=styles[i]>=4?styles[i]:0;
  ps.fd.saberAnimLevel=styles[i]>=4?(styles[i]==4?2:3):styles[i];
  if(!changing) {
   ps.groundEntityNum=context>=2?ENTITYNUM_NONE:0;
   ps.pm_flags=(context==1||context==3)?PMF_DUCKED:0;
   pm->cmd.upmove=context==1||context==3?-127:context==4?127:0;
  }
  PM_SetSaberMove(LS_S_TL2BR);ps.weaponTime=200;
  CHECK(ps.stCombat.phase==STC_WINDUP);
  ps.groundEntityNum=context>=2?ENTITYNUM_NONE:0;
  ps.pm_flags=(context==1||context==3)?PMF_DUCKED:0;
  pm->cmd.upmove=context==1||context==3?-127:context==4?127:0;
  ps.legsTimer=777;ps.legsAnim=1234;
  ps.commandTime=pm->cmd.serverTime=1150;
  pm->cmd.buttons=BUTTON_FEINT|BUTTON_ATTACK;
  CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.phase==STC_RECOVERY);
  CHECK(lastParts==SETANIM_TORSO && ps.legsTimer==777 && ps.legsAnim==1234);
  /* A fresh tap cancels each successive redirected wind-up. No artificial
     one-use lockout or residual cooldown may swallow the second/third press. */
  for(repeat=0;repeat<3;repeat++) {
   ps.commandTime=pm->cmd.serverTime=1350+repeat*220;
   pm->cmd.buttons=BUTTON_ATTACK;CHECK(PM_ST_FeintFrame());
   CHECK(ps.stCombat.phase==STC_WINDUP);
   ps.commandTime=pm->cmd.serverTime=1360+repeat*220;
   CHECK(!PM_ST_FeintFrame()); /* no fresh press */
   ps.commandTime=pm->cmd.serverTime=1370+repeat*220;
   pm->cmd.buttons|=BUTTON_FEINT;CHECK(PM_ST_FeintFrame());
   CHECK(ps.stCombat.phase==STC_RECOVERY && ps.stCombat.recoveryMs==200);
   CHECK(ps.stCombat.attack==1 && STC_StateValid(&ps.stCombat));
   CHECK(ps.legsTimer==777 && lastParts==SETANIM_TORSO);
  }
 }
}
int main(int argc,char** argv){
 STC_State saved;
 if(argc>1 && !strcmp(argv[1],"mobility")) {mobility();printf("Mobility checks: %d passed.\n",checks);return 0;}
 /* Stock Yellow/Red chain checks mutate cmd.serverTime through Q_random.
    Feint must use the stable Pmove timestamp even after that exact routine. */
 {
  const int styles[]={1,2,3,4,6};int i;
  for(i=0;i<5;i++) {
   reset();ps.fd.saberAnimLevel=styles[i]<=3?styles[i]:styles[i]==4?2:3;
   ps.stHybrid.style=styles[i]>=4?styles[i]:0;
   STC_Init(&ps.stCombat,1,1000);
   PM_irand_timesync(2,5);
   CHECK(pm->cmd.serverTime!=ps.commandTime);
   PM_SetSaberMove(LS_S_TL2BR);
   CHECK(ps.stCombat.lastTime==1000);
   ps.commandTime=pm->cmd.serverTime=1050;
   pm->cmd.buttons=BUTTON_FEINT|BUTTON_ATTACK;pm->cmd.rightmove=-127;
   CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.feintsUsed==1);
  }
 }

 reset();CHECK(ps.stCombat.phase==STC_WINDUP && ps.stCombat.windupMs==200);
 ps.commandTime=pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_ATTACK|BUTTON_FEINT;
 pm->cmd.rightmove=-127;pm->cmd.forwardmove=127;
 CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.phase==STC_RECOVERY);
 CHECK(ps.stCombat.redirect==STC_TR_BL && ps.weaponTime>=200 && draws>0);
 saved=ps.stCombat;CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.attack==saved.attack);
 ps.commandTime=pm->cmd.serverTime=1249;CHECK(PM_ST_FeintFrame());CHECK(ps.saberMove==LS_READY);
 CHECK(ps.weaponTime==1);
 ps.commandTime=pm->cmd.serverTime=1250;CHECK(PM_ST_FeintFrame());
 CHECK(ps.saberMove==LS_S_TL2BR+STC_TR_BL && ps.stCombat.phase==STC_WINDUP);
 CHECK(ps.stCombat.attack==1 && ps.stCombat.feintsUsed==1 && ps.weaponTime==200);
 PM_SetSaberMove(LS_A_TL2BR+STC_TR_BL);CHECK(ps.stCombat.phase==STC_ACTIVE);
 reset();STC_Contact(&ps.stCombat);ps.commandTime=pm->cmd.serverTime=1050;
 pm->cmd.buttons=BUTTON_ATTACK|BUTTON_FEINT;pm->cmd.rightmove=-127;
 CHECK(!PM_ST_FeintFrame());CHECK(ps.stCombat.phase==STC_WINDUP);
 reset();ps.commandTime=pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT|BUTTON_ATTACK;pm->cmd.rightmove=-127;
 CHECK(PM_ST_FeintFrame());ps.saberHolstered=2;ps.weaponTime=0;
 ps.commandTime=pm->cmd.serverTime=1100;CHECK(PM_ST_FeintFrame());CHECK(ps.weaponTime>=150);
 ps.saberHolstered=0;ps.commandTime=pm->cmd.serverTime=1250;CHECK(!PM_ST_FeintFrame());
 CHECK(ps.stCombat.phase==STC_CANCELLED);
 reset();ps.commandTime=pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT|BUTTON_ATTACK;pm->cmd.rightmove=-127;
 CHECK(PM_ST_FeintFrame());failAnimation=1;ps.commandTime=pm->cmd.serverTime=1250;
 CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.phase==STC_CANCELLED);
 reset();second=1;ps.commandTime=pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT;pm->cmd.rightmove=-127;
 CHECK(!PM_ST_FeintFrame());CHECK(ps.stCombat.feintsUsed==0);
 reset();knocked=1;ps.commandTime=pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT;pm->cmd.rightmove=-127;
 CHECK(!PM_ST_FeintFrame());CHECK(!ps.stCombat.feintsUsed);
 reset();rolling=1;ps.commandTime=pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT;pm->cmd.rightmove=-127;
 CHECK(!PM_ST_FeintFrame());CHECK(!ps.stCombat.feintsUsed);
 reset();memset(&ps.stCombat,0,sizeof(ps.stCombat));saved=ps.stCombat;
 CHECK(!PM_ST_FeintFrame());CHECK(!memcmp(&saved,&ps.stCombat,sizeof(saved)));
 /* Failed withdrawal still pays recovery and never redirects a failed pose. */
 reset();failAnimation=1;ps.commandTime=pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT|BUTTON_ATTACK;pm->cmd.rightmove=-127;
 CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.phase==STC_RECOVERY);
 CHECK(ps.stCombat.redirect==STC_DIRECTION_NONE && ps.weaponTime==200);
 ps.commandTime=pm->cmd.serverTime=1250;CHECK(!PM_ST_FeintFrame());CHECK(ps.weaponTime==0);
 /* Inputs received while frozen/paused cannot become fresh presses on return. */
 reset();ps.commandTime=pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT|BUTTON_ATTACK;pm->cmd.rightmove=-127;
 BG_ST_FeintStopped(&ps,&pm->cmd,STC_GUARD_FROZEN);
 ps.commandTime=pm->cmd.serverTime=1100;CHECK(!PM_ST_FeintFrame());CHECK(!ps.stCombat.feintsUsed && ps.stCombat.held);
 reset();ps.commandTime=pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT|BUTTON_ATTACK;pm->cmd.rightmove=-127;
 CHECK(PM_ST_FeintFrame());ps.commandTime=pm->cmd.serverTime=2050;
 BG_ST_FeintStopped(&ps,&pm->cmd,STC_GUARD_PAUSED);
 CHECK(ps.stCombat.recoveryMs==200 && ps.stCombat.cooldownMs==200);
 ps.commandTime=pm->cmd.serverTime=2150;CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.recoveryMs==100);
 ps.commandTime=pm->cmd.serverTime=2250;CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.phase==STC_WINDUP);
 /* Weapon switching cannot skip the paid recovery, or resume the redirect. */
 reset();ps.commandTime=pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT|BUTTON_ATTACK;pm->cmd.rightmove=-127;
 CHECK(PM_ST_FeintFrame());pm->cmd.weapon=3;ps.commandTime=pm->cmd.serverTime=1100;
 CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.recoveryMs==150 && ps.stCombat.redirect==STC_DIRECTION_NONE);
 ps.commandTime=pm->cmd.serverTime=1250;CHECK(!PM_ST_FeintFrame());CHECK(ps.weaponTime==0);
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
   pm->cmd.buttons=BUTTON_ATTACK|BUTTON_FEINT;ps.commandTime=pm->cmd.serverTime=1050;
   CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.redirect==dir);snapshot=ps;
   for(i=1;i<=4;i++){ps.commandTime=pm->cmd.serverTime=1050+50*i;CHECK(PM_ST_FeintFrame());}
   expected=ps;ps=snapshot;
   for(i=1;i<=4;i++){ps.commandTime=pm->cmd.serverTime=1050+50*i;CHECK(PM_ST_FeintFrame());}
   CHECK(!memcmp(&expected,&ps,sizeof(ps)));CHECK(STC_StateValid(&ps.stCombat));
  }
 }
 /* Authoritative contact correction removes a locally predicted redirect. */
 reset();{
  playerState_t authoritative=ps;
  ps.commandTime=pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT|BUTTON_ATTACK;pm->cmd.rightmove=-127;
  CHECK(PM_ST_FeintFrame());ps=authoritative;STC_Contact(&ps.stCombat);
  CHECK(!PM_ST_FeintFrame());CHECK(!ps.stCombat.feintsUsed && ps.stCombat.contacted);
 }
 /* Actual server early-return hook must sanitize before consuming raw input. */
 {
  int pause;
  for(pause=0;pause<2;pause++) {
   gclient_t client;gentity_t entity;
   reset();ps.commandTime=pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_FEINT|BUTTON_ATTACK;pm->cmd.rightmove=-127;
   CHECK(PM_ST_FeintFrame());memset(&client,0,sizeof(client));client.ps=ps;client.pers.cmd=pm->cmd;
   entity.client=&client;entity.health=100;level.time=1100;level.stTournamentPhase=pause?ST_TOURNAMENT_PAUSED:0;
   client.ps.stats[ST_STAFF_STAT]=pause?0:ST_STAFF_FROZEN;
   client.pers.cmd.serverTime=1000000;G_STFeintStoppedState(&entity);
   CHECK(client.ps.stCombat.lastTime<=1300 && client.ps.stCombat.lastInputTime<=1300);
   CHECK(client.ps.stCombat.held && client.ps.stCombat.recoveryMs==200);
   CHECK(client.pers.cmd.serverTime==1000000); /* caller command remains intact */
   client.ps.stats[ST_STAFF_STAT]=0;level.stTournamentPhase=0;
   client.pers.cmd.serverTime=1350;G_STFeintStoppedState(&entity);
   ps=client.ps;ps.commandTime=pm->cmd.serverTime=1350;CHECK(PM_ST_FeintFrame());
   CHECK(ps.stCombat.recoveryMs==150);ps.commandTime=pm->cmd.serverTime=1500;
   CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.phase==STC_WINDUP);
  }
 }

 /* All supported logical styles retain identity, and release stops followup. */
 {
  const int styles[]={1,2,3,4,6};int i,release;
  for(i=0;i<5;i++)for(release=0;release<2;release++) {
   reset();ps.stHybrid.style=styles[i];
   ps.fd.saberAnimLevel=styles[i]==6?3:styles[i]==4?1:styles[i];
   STC_Init(&ps.stCombat,1,1000);PM_SetSaberMove(LS_S_TL2BR);ps.weaponTime=200;
   CHECK(ps.stCombat.style==styles[i]);
   ps.commandTime=pm->cmd.serverTime=1050;pm->cmd.buttons=BUTTON_ATTACK|BUTTON_FEINT;pm->cmd.rightmove=-127;
   CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.phase==STC_RECOVERY);
   ps.commandTime=pm->cmd.serverTime=1250;pm->cmd.buttons=release?0:BUTTON_ATTACK;
   PM_ST_FeintFrame();CHECK(ps.stCombat.phase==(release?STC_CANCELLED:STC_WINDUP));
   CHECK(ps.stCombat.style==styles[i]);
  }
 }
 /* A real START move remains cancellable through its full wind-up, including
    long Red starts. Test both a redirect and keeping the original direction;
    sample the first millisecond, the old cutoff and the commitment boundary. */
 {
  const int styles[]={1,2,3,4,6},durations[]={100,250,600,900};
  const int right[7]={127,127,127,-127,-127,-127,0};
  const int forward[7]={127,0,-127,-127,0,127,0};
  int i,d,n,dir,same,release;
  for(i=0;i<5;i++)for(d=0;d<4;d++)for(dir=0;dir<7;dir++)
  for(same=0;same<2;same++)for(n=0;n<4;n++)for(release=0;release<2;release++) {
   int duration=durations[d],elapsed=n==0?duration*3/4:n==1?1:n==2?duration-1:duration;
   int target=same?dir:(dir+1)%7;
   playerState_t authoritative,expected;
   reset();ps.stHybrid.style=styles[i]>=4?styles[i]:0;
   ps.fd.saberAnimLevel=styles[i]>=4?(styles[i]==4?2:3):styles[i];
   STC_Init(&ps.stCombat,1,1000);
   ps.saberMove=LS_S_TL2BR+dir;ps.torsoTimer=ps.weaponTime=duration;
   PM_ST_FeintMove(ps.saberMove);
   ps.commandTime=pm->cmd.serverTime=1000+elapsed;
   ps.torsoTimer=ps.weaponTime=duration-elapsed;
   pm->cmd.buttons=BUTTON_FEINT|(release?0:BUTTON_ATTACK);
   pm->cmd.rightmove=right[target];pm->cmd.forwardmove=forward[target];
   authoritative=ps;
   if(elapsed==duration) {
    CHECK(!PM_ST_FeintFrame());CHECK(!ps.stCombat.feintsUsed);
    CHECK(ps.stCombat.phase==STC_ACTIVE);continue;
   }
   CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.phase==STC_RECOVERY);
   CHECK(ps.saberMove==LS_READY && ps.stCombat.redirect==target);
   CHECK(ps.weaponTime==200 && ps.stCombat.cooldownMs==200 && draws>0);
   CHECK(STC_StateValid(&ps.stCombat));expected=ps;
   /* Snapshot correction/replay reaches the same result as prediction. */
   ps=authoritative;CHECK(PM_ST_FeintFrame());CHECK(!memcmp(&expected,&ps,sizeof(ps)));
   ps.commandTime=pm->cmd.serverTime=1200+elapsed;pm->cmd.buttons=release?0:BUTTON_ATTACK;
   PM_ST_FeintFrame();CHECK(ps.stCombat.phase==(release?STC_CANCELLED:STC_WINDUP));
   CHECK(ps.stCombat.feintsUsed==1 && ps.stCombat.attack==1);
   if(!release) {
    ps.commandTime=pm->cmd.serverTime=1201+elapsed;pm->cmd.buttons|=BUTTON_FEINT;
    CHECK(PM_ST_FeintFrame());CHECK(ps.stCombat.phase==STC_RECOVERY);
    CHECK(ps.stCombat.recoveryMs==200);
   }
  }
  /* Neither early engine commitment nor contact may be undone by the wider
     window, even while a leftover torso timer still resembles a wind-up. */
  for(n=0;n<2;n++) {
   reset();ps.commandTime=pm->cmd.serverTime=1050;
   if(n)STC_Contact(&ps.stCombat);else PM_SetSaberMove(LS_A_TL2BR);
   ps.torsoTimer=ps.weaponTime=150;pm->cmd.buttons=BUTTON_FEINT|BUTTON_ATTACK;
   pm->cmd.forwardmove=pm->cmd.rightmove=127;
   CHECK(!PM_ST_FeintFrame());CHECK(!ps.stCombat.feintsUsed);
  }
 }
 mobility();
 printf("Production feint adapter: %d checks passed.\n",checks);return 0;
}
