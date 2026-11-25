/* Actual server adapter/decision bodies with explicit animation/contact seams. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "st_hybrid.h"
#include "st_combat_core.h"
typedef int qboolean;
typedef float vec3_t[3];
#define qtrue 1
#define qfalse 0
enum {BUTTON_ATTACK=1,BUTTON_TALK=2,BUTTON_WALKING=16,BUTTON_ALT_ATTACK=128,
 BUTTON_FEINT=4096,BUTTON_BLOCK=8192,WP_SABER=2,PM_NORMAL=0,PM_FREEZE=1,
 STAT_HEALTH=0,TEAM_SPECTATOR=3,PMF_FOLLOW=1,SVF_BOT=8,ET_NPC=12,
 ST_TOURNAMENT_PAUSED=4,HANDEXTEND_NONE=0,LS_NONE=0,LS_READY=1,
 LS_PARRY_UP=10,LS_REFLECT_LL=20,FP_SABER_DEFENSE=0,FORCE_LEVEL_1=1,
 FORCE_LEVEL_2=2,FORCE_LEVEL_3=3,ST_COMBAT_DEFENSE=0,WEAPON_RAISING=1,
 LS_S_TL2BR=30,LS_S_T2B=36,SABER_NONATTACK_DAMAGE=2,
 BLOCKED_NONE=0,BLOCKED_PARRY_BROKEN=2,SEF_PARRIED=1,SEF_BLOCKED=2,
 SETANIM_TORSO=1,SETANIM_FLAG_OVERRIDE=1,SETANIM_FLAG_HOLD=2};
typedef struct {int buttons,weapon,forwardmove,rightmove,upmove,serverTime;} usercmd_t;
typedef struct {
 int stats[16],pm_flags,pm_type,weapon,saberEntityNum,saberHolstered,saberInFlight;
 int m_iVehicleNum,emplacedIndex,forceHandExtend,saberLockFrame,saberLockTime;
 int saberMove,torsoAnim,legsAnim,torsoTimer,weaponTime,saberBlocked,saberBlocking,saberBlockTime,weaponstate,saberEventFlags;
 vec3_t origin,viewangles,velocity;
 STC_State stCombat;
 STH_State stHybrid;
 struct {int forcePowerLevel[4];} fd;
} playerState_t;
typedef struct {
 playerState_t ps;
 struct {int sessionTeam;} sess;
 struct {usercmd_t cmd;int stPerfectParries;} pers;
 int buttons,stManualBlockHeld,stParryWindowEnd,stParryCooldownEnd;
 int stParryAttackHeld,stAttackParryEnd;
 int stPerfectParrySuccessTime,stCounterWindowEnd;
} gclient_t;
typedef struct {gclient_t *client;int health;struct {int svFlags;} r;struct {int eType;} s;} gentity_t;
static struct {int time,intermissiontime,stTournamentPhase;} level;
static struct {int integer;} g_manualBlocking,st_parryWindow,st_parryCooldown,st_counterWindow,d_saberGhoul2Collision,st_attackParry,st_attackParryWindow,st_masterParryStagger;
static int enabled,knocked,rolling,checks,master;
static struct {int animToUse;} saberMoveData[400];
static qboolean ST_MasterEnabled(void){return master;}
static int G_GetParryForBlock(int block){return block?LS_PARRY_UP:LS_NONE;}
static int BG_BrokenParryForAttack(int move){(void)move;return 300;}
static void G_SetAnim(gentity_t *ent,usercmd_t *cmd,int parts,int anim,int flags,int blend){
 (void)cmd;(void)parts;(void)flags;(void)blend;ent->client->ps.torsoAnim=anim;
}
static float facing,lastFactor;
static int Com_Clampi(int lo,int hi,int x){return x<lo?lo:x>hi?hi:x;}
static qboolean ST_CombatOption(int option){(void)option;return enabled;}
static qboolean BG_SabersOff(playerState_t *ps){return ps->saberHolstered!=0;}
static qboolean BG_SaberInAttack(int move){return move==100;}
static qboolean BG_SaberInSpecial(int move){return move==200;}
static qboolean BG_SaberInSpecialAttack(int anim){return anim==200;}
static qboolean BG_InRoll(playerState_t *ps,int anim){(void)ps;(void)anim;return rolling;}
qboolean PM_InKnockDown(playerState_t *ps){(void)ps;return knocked;}
static qboolean PM_SaberInBrokenParry(int move){return move==300;}
static qboolean PM_InSaberAnim(int anim){return anim!=0;}
static qboolean SaberAttacking(gentity_t *ent){return BG_SaberInAttack(ent->client->ps.saberMove);}
static qboolean InFront(vec3_t point,vec3_t origin,vec3_t angles,float factor){
 (void)point;(void)origin;(void)angles;lastFactor=factor;return facing>factor;
}
static void WP_SaberBlockNonRandom(gentity_t *ent,vec3_t point,qboolean missile){(void)point;(void)missile;ent->client->ps.saberBlocked=1;}
#include "g_st_manualblock.inc"
#include "manual_block_production.inc"
static gclient_t client;
static gentity_t entity;
static vec3_t contact={10,0,0};
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"manual block line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
static void reset(void){
 memset(&client,0,sizeof client);memset(&entity,0,sizeof entity);memset(&level,0,sizeof level);
 entity.client=&client;entity.health=client.ps.stats[STAT_HEALTH]=100;
 client.ps.weapon=client.pers.cmd.weapon=WP_SABER;client.ps.saberEntityNum=20;
 client.ps.fd.forcePowerLevel[FP_SABER_DEFENSE]=3;client.ps.saberMove=LS_READY;
 level.time=1000;enabled=g_manualBlocking.integer=d_saberGhoul2Collision.integer=1;
 st_parryWindow.integer=350;st_parryCooldown.integer=750;st_counterWindow.integer=550;
 st_attackParry.integer=0;st_attackParryWindow.integer=150;master=0;st_masterParryStagger.integer=700;
 saberMoveData[LS_PARRY_UP].animToUse=99;
 knocked=rolling=0;facing=1;
}
static void input(int buttons){client.pers.cmd.buttons=buttons;ST_UpdateParryInput(&entity,&client.pers.cmd);}
static void attack_parry_tests(void){
 int mode,held,step;
 gclient_t enemyClient;
 gentity_t enemy;
 playerState_t before;
 memset(&enemyClient,0,sizeof enemyClient);memset(&enemy,0,sizeof enemy);
 enemy.client=&enemyClient;enemy.health=100;enemyClient.ps.saberMove=100;
 /* Both input choices in every server mode, outside Master. The contact
    wrapper is extracted from the actual server saber trace, not re-created. */
 for(mode=0;mode<3;mode++)for(held=0;held<2;held++) {
  reset();g_manualBlocking.integer=mode;st_attackParry.integer=1;
  input(held?BUTTON_BLOCK:0);CHECK(!client.stParryWindowEnd && !client.stAttackParryEnd);
  input(BUTTON_ATTACK|(held?BUTTON_BLOCK:0));CHECK(client.stAttackParryEnd==1150);
  CHECK(client.stParryCooldownEnd==1750);
  client.ps.saberMove=LS_S_TL2BR;client.ps.torsoAnim=30;client.ps.weaponTime=250;
  level.time=1149;
  CHECK(ST_TryAttackParryContact(&enemy,&entity,contact,60,qfalse));
  CHECK(!ST_TryAttackParryContact(&enemy,&entity,contact,60,qfalse));
  CHECK(client.pers.stPerfectParries==1);
  ST_ResolvePerfectParry(&enemy,&entity,contact);
  CHECK(client.ps.saberMove==LS_PARRY_UP && client.ps.torsoAnim==99 && !client.ps.weaponTime);
  CHECK(enemyClient.ps.saberBlocked==BLOCKED_PARRY_BROKEN && (enemyClient.ps.saberEventFlags&SEF_BLOCKED));
  CHECK(client.stCounterWindowEnd==1699);
  enemyClient.ps.saberMove=100;
 }
 reset();st_attackParry.integer=1;input(BUTTON_ATTACK);level.time=1150;
 CHECK(!ST_TryAttackParryContact(&enemy,&entity,contact,60,qfalse));
 level.time=2000;input(BUTTON_ATTACK);CHECK(!client.stAttackParryEnd); /* holding never renews */
 input(0);input(BUTTON_ATTACK);CHECK(client.stAttackParryEnd==2150);
 reset();st_attackParry.integer=1;input(BUTTON_ATTACK);input(0);level.time=1100;
 CHECK(ST_TryAttackParryContact(&enemy,&entity,contact,60,qfalse)); /* a tap can be released */
 input(BUTTON_ATTACK);CHECK(!client.stAttackParryEnd); /* cooldown survives release */
 /* Wrong facing, idle touches, throw, unblockable and own blade all fail. */
 reset();st_attackParry.integer=1;input(BUTTON_ATTACK);
 facing=-1;CHECK(!ST_TryAttackParryContact(&enemy,&entity,contact,60,qfalse));facing=1;
 CHECK(!ST_TryAttackParryContact(&enemy,&entity,contact,2,qfalse));
 CHECK(!ST_TryAttackParryContact(&enemy,&entity,contact,60,qtrue));
 CHECK(!ST_TryAttackParryContact(&entity,&entity,contact,60,qfalse));
 enemyClient.ps.saberInFlight=1;CHECK(!ST_TryAttackParryContact(&enemy,&entity,contact,60,qfalse));enemyClient.ps.saberInFlight=0;
 enemyClient.ps.saberMove=LS_READY;CHECK(!ST_TryAttackParryContact(&enemy,&entity,contact,60,qfalse));enemyClient.ps.saberMove=100;
 CHECK(!WP_SaberCanBlock(&entity,contact,0,0,qtrue,0));
 CHECK(!WP_SaberCanBlock(&entity,contact,0,0,qfalse,999));
 CHECK(client.stAttackParryEnd==1150 && !client.pers.stPerfectParries);
 /* Beginning an active swing or special spends eligibility, not debt. */
 for(step=0;step<11;step++) {
  reset();st_attackParry.integer=1;input(BUTTON_ATTACK);
  switch(step) {
   case 0:client.ps.saberMove=100;break;
   case 1:client.ps.saberMove=200;break;
   case 2:client.ps.stCombat.recoveryMs=200;break;
   case 3:client.ps.stHybrid.recoveryMs=500;break;
   case 4:client.ps.saberMove=300;break;
   case 5:client.ps.saberInFlight=1;break;
   case 6:client.ps.stats[ST_STAFF_STAT]=ST_STAFF_GHOST;break;
   case 7:level.stTournamentPhase=ST_TOURNAMENT_PAUSED;break;
   case 8:client.pers.cmd.buttons|=BUTTON_ALT_ATTACK;break;
   case 9:client.pers.cmd.buttons|=BUTTON_FEINT;break;
   case 10:client.ps.fd.forcePowerLevel[FP_SABER_DEFENSE]=0;break;
  }
  before=client.ps;
  CHECK(!ST_TryAttackParryContact(&enemy,&entity,contact,60,qfalse));
  CHECK(!memcmp(&before,&client.ps,sizeof before));
 }
 reset();st_attackParry.integer=1;level.stTournamentPhase=ST_TOURNAMENT_PAUSED;
 client.pers.cmd.buttons=BUTTON_ATTACK;ST_ManualBlockStopped(&entity);
 level.stTournamentPhase=0;input(BUTTON_ATTACK);CHECK(!client.stAttackParryEnd);
 input(0);input(BUTTON_ATTACK);CHECK(client.stAttackParryEnd==1150);
 reset();st_attackParry.integer=1;master=1;input(BUTTON_ATTACK);
 CHECK(ST_TryAttackParryContact(&enemy,&entity,contact,60,qfalse));
 enemyClient.ps.weaponTime=0;ST_ResolvePerfectParry(&enemy,&entity,contact);
 CHECK(enemyClient.ps.weaponTime==700 && client.stCounterWindowEnd==1700);
 reset();st_attackParry.integer=1;enabled=0;input(BUTTON_ATTACK);CHECK(!client.stAttackParryEnd);
 reset();st_attackParry.integer=1;entity.r.svFlags=SVF_BOT;input(BUTTON_WALKING);CHECK(client.stParryWindowEnd==1350 && !client.stAttackParryEnd);
 reset();st_attackParry.integer=1;st_attackParryWindow.integer=9000;input(BUTTON_ATTACK);CHECK(client.stAttackParryEnd==1200);
 reset();st_attackParry.integer=1;st_attackParryWindow.integer=-1;input(BUTTON_ATTACK);CHECK(client.stAttackParryEnd==1060);
}
int main(void){
 int i;playerState_t before;usercmd_t cmd;
 /* Three server modes, both combat presets, melee/thrown/projectile defense.
    Only mode 2 removes non-contact automatic defense without a held input. */
 {
  int mode,trials,kind,held;
  for(mode=0;mode<=2;mode++)for(trials=0;trials<2;trials++)
   for(kind=0;kind<3;kind++)for(held=0;held<2;held++){
    reset();g_manualBlocking.integer=mode;enabled=trials;
    input(held?BUTTON_BLOCK:0);
    CHECK(WP_SaberCanBlock(&entity,contact,0,0,kind==2,kind==0?1:kind==1?999:0)==(mode!=2||held));
   }
  reset();g_manualBlocking.integer=2;entity.r.svFlags=SVF_BOT;
  input(0);CHECK(!WP_SaberCanBlock(&entity,contact,0,0,qfalse,1));
  input(BUTTON_WALKING);CHECK(WP_SaberCanBlock(&entity,contact,0,0,qfalse,1));
  reset();g_manualBlocking.integer=2;input(BUTTON_BLOCK);
  input(0);CHECK(!WP_SaberCanBlock(&entity,contact,0,0,qfalse,1));
  reset();g_manualBlocking.integer=-1;input(BUTTON_BLOCK);
  CHECK(ST_BlockingMode()==0 && !ST_ActiveGuard(&entity));
  CHECK(WP_SaberCanBlock(&entity,contact,0,0,qfalse,1));
  reset();g_manualBlocking.integer=99;CHECK(ST_BlockingMode()==0);
  g_manualBlocking.integer=2;CHECK(!ST_BlockInputAllowed(NULL,NULL));
  client.pers.cmd.buttons=BUTTON_BLOCK;
  CHECK(ST_BlockInputAllowed(&entity,&client.pers.cmd));
  client.ps.stCombat.recoveryMs=100;CHECK(!ST_BlockInputAllowed(&entity,&client.pers.cmd));
 }
 reset();input(0);CHECK(!ST_ActiveGuard(&entity));
 CHECK(WP_SaberCanBlock(&entity,contact,0,0,qfalse,1)); /* automatic defense retained */
 facing=-1;CHECK(!WP_SaberCanBlock(&entity,contact,0,0,qfalse,1));
 reset();input(BUTTON_BLOCK);CHECK(ST_ActiveGuard(&entity));
 CHECK(client.stParryWindowEnd==1350 && client.stParryCooldownEnd==1750);
 level.time=1100;input(BUTTON_BLOCK);CHECK(client.stParryWindowEnd==1350);
 CHECK(ST_ConsumePerfectParry(&entity,contact));CHECK(client.pers.stPerfectParries==1);
 CHECK(!ST_ConsumePerfectParry(&entity,contact));
 CHECK(client.stCounterWindowEnd==1650);
 client.ps.saberMove=LS_PARRY_UP;client.ps.weaponTime=200;input(BUTTON_ATTACK);
 CHECK(client.ps.weaponTime==0 && client.stCounterWindowEnd==0);
 reset();input(BUTTON_BLOCK);input(0);CHECK(client.stParryWindowEnd==0);
 level.time=1100;input(BUTTON_BLOCK);CHECK(!client.stParryWindowEnd); /* cooldown survives release */
 level.time=1800;input(BUTTON_BLOCK);CHECK(!client.stParryWindowEnd); /* held is not a new press */
 input(0);input(BUTTON_BLOCK);CHECK(client.stParryWindowEnd==2150);
 reset();input(BUTTON_WALKING);CHECK(!ST_ActiveGuard(&entity)&&!client.stParryWindowEnd);
 entity.r.svFlags=SVF_BOT;input(0);input(BUTTON_WALKING);CHECK(ST_ActiveGuard(&entity)&&client.stParryWindowEnd);
 reset();g_manualBlocking.integer=0;input(BUTTON_WALKING);CHECK(ST_ActiveGuard(&entity)&&client.stParryWindowEnd);
 reset();enabled=0;input(BUTTON_BLOCK);CHECK(!ST_ActiveGuard(&entity)&&!client.stParryWindowEnd);
 CHECK(WP_SaberCanBlock(&entity,contact,0,0,qfalse,1));
 /* After the timed window expires, held guard still uses the existing wider
    frontal defense. Releasing returns to the unchanged passive threshold. */
 reset();input(BUTTON_BLOCK);level.time=1400;input(BUTTON_BLOCK);facing=0.1f;
 CHECK(WP_SaberCanBlock(&entity,contact,0,0,qfalse,1));CHECK(lastFactor<0.1f);
 input(0);CHECK(!WP_SaberCanBlock(&entity,contact,0,0,qfalse,1));CHECK(lastFactor>0.1f);
 facing=1;CHECK(WP_SaberCanBlock(&entity,contact,0,0,qfalse,1));
 /* Every rejection preserves timers/movement and cannot spend/open a parry. */
 for(i=0;i<26;i++){
  if(i==2)continue;
  reset();client.pers.cmd.buttons=BUTTON_BLOCK;
  switch(i){
   case 0:client.ps.stCombat.recoveryMs=200;break;
   case 1:client.ps.stHybrid.recoveryMs=900;break;

   case 3:client.ps.saberMove=100;break;
   case 4:client.ps.saberMove=200;break;
   case 5:client.ps.saberMove=300;break;
   case 6:client.ps.weaponTime=200;break;
   case 7:client.ps.saberHolstered=2;break;
   case 8:client.ps.saberInFlight=1;break;
   case 9:client.ps.pm_type=PM_FREEZE;break;
   case 10:client.ps.stats[ST_STAFF_STAT]=ST_STAFF_GHOST;break;
   case 11:client.ps.stats[ST_STAFF_STAT]=ST_STAFF_FROZEN;break;
   case 12:level.stTournamentPhase=ST_TOURNAMENT_PAUSED;break;
   case 13:level.intermissiontime=1;break;
   case 14:client.ps.stats[STAT_HEALTH]=0;break;
   case 15:client.ps.forceHandExtend=1;break;
   case 16:knocked=1;break;
   case 17:rolling=1;break;
   case 18:client.ps.saberLockTime=2000;break;
   case 19:client.pers.cmd.buttons|=BUTTON_ATTACK;break;
   case 20:client.pers.cmd.buttons|=BUTTON_ALT_ATTACK;break;
   case 21:client.pers.cmd.buttons|=BUTTON_FEINT;break;
   case 22:client.ps.fd.forcePowerLevel[FP_SABER_DEFENSE]=0;break;
   case 23:client.pers.cmd.weapon=3;break;
   case 24:client.ps.weaponstate=WEAPON_RAISING;break;
   case 25:client.ps.saberBlocked=1;break;
  }
  before=client.ps;cmd=client.pers.cmd;ST_UpdateParryInput(&entity,&cmd);
  CHECK(!client.stParryWindowEnd && !ST_ActiveGuard(&entity));
  CHECK(!ST_ConsumePerfectParry(&entity,contact));
  CHECK(!memcmp(&before,&client.ps,sizeof before));CHECK(!memcmp(&cmd,&client.pers.cmd,sizeof cmd));
 }
 /* Freeze/pause early returns consume the held edge, including after recovery. */
 reset();input(BUTTON_BLOCK);level.stTournamentPhase=ST_TOURNAMENT_PAUSED;
 ST_ManualBlockStopped(&entity);CHECK(!client.stParryWindowEnd&&client.stManualBlockHeld);
 level.time=3000;level.stTournamentPhase=0;input(BUTTON_BLOCK);CHECK(!client.stParryWindowEnd);
 input(0);input(BUTTON_BLOCK);CHECK(client.stParryWindowEnd==3350);
 /* No counter token may wipe offensive or feint debt. */
 reset();client.stCounterWindowEnd=1600;client.ps.stHybrid.recoveryMs=500;client.ps.weaponTime=500;
 input(BUTTON_ATTACK|BUTTON_BLOCK);CHECK(client.ps.weaponTime==500 && client.ps.stHybrid.recoveryMs==500);
 reset();client.stCounterWindowEnd=1600;client.ps.stCombat.recoveryMs=200;client.ps.weaponTime=200;
 input(BUTTON_ATTACK|BUTTON_BLOCK);CHECK(client.ps.weaponTime==200 && client.ps.stCombat.recoveryMs==200);
 /* Holding guard does not rewrite the user's command, locomotion or aim. */
 reset();client.ps.velocity[0]=250;client.ps.viewangles[1]=70;
 client.pers.cmd.buttons=BUTTON_BLOCK;client.pers.cmd.forwardmove=127;client.pers.cmd.rightmove=-127;
 before=client.ps;cmd=client.pers.cmd;ST_UpdateParryInput(&entity,&cmd);
 CHECK(!memcmp(&before,&client.ps,sizeof before));CHECK(!memcmp(&cmd,&client.pers.cmd,sizeof cmd));
 attack_parry_tests();
 printf("Manual block / attack parry production decisions: %d checks passed.\n",checks);return 0;
}
