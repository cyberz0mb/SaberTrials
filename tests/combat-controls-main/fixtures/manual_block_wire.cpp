#define main existing_feint_wire_checks
#include "../feint-integration/protocol.cpp"
#undef main
#include "game/bg_public.h"
#include "game/bg_local.h"
#include "staff/st_staff_movement.h"
pmove_t *pm;
qboolean BG_SabersOff(playerState_t *ps) { return (qboolean)(ps->saberHolstered==2); }
qboolean BG_InRoll(playerState_t*,int) { return qfalse; }
qboolean PM_InKnockDown(playerState_t*) { return qfalse; }
qboolean BG_SaberInSpecialAttack(int) { return qfalse; }
int PM_GetSaberStance(void) { return BOTH_SABERFAST_STANCE; }
void PM_SetAnim(int parts,int anim,int flags) {
 CHECK(parts==SETANIM_TORSO && flags==SETANIM_FLAG_OVERRIDE);
 pm->ps->torsoAnim=anim;
}
#define BG_ST_SetManualGuard ST_TestManualGuard
#define qboolean int // C adapter uses integer booleans; retain real wire structs.
#include "bg_st_manualguard.inc"
#undef qboolean

static void guardAfterSnapshot(void) {
 byte bytes[16384];msg_t msg;playerState_t zero={},server={},client={};
 animation_t animations[MAX_TOTALANIMATIONS]={};pmove_t movement={};pm=&movement;
 movement.animations=animations;movement.cmd.weapon=WP_SABER;
 movement.cmd.buttons=BUTTON_BLOCK;movement.cmd.serverTime=1000;
 animations[BOTH_ST_GUARD_SINGLE].numFrames=animations[BOTH_ST_GUARD_SINGLE].loopFrames=1;
 server.stats[STAT_HEALTH]=100;server.weapon=WP_SABER;server.saberEntityNum=107;
 server.saberMove=LS_READY;server.fd.saberAnimLevel=SS_FAST;
 server.fd.forcePowerLevel[FP_SABER_DEFENSE]=3;
 server.fd.forcePowersKnown=1<<FP_SABER_DEFENSE;
 server.torsoAnim=BOTH_SABERFAST_STANCE;
 BG_ST_SetManualGuard(1,qtrue);
 movement.ps=&server;CHECK(PM_ST_ManualGuardFrame());
 MSG_Init(&msg,bytes,sizeof bytes);MSG_WriteDeltaPlayerstate(&msg,&zero,&server,qfalse);
 MSG_BeginReading(&msg);MSG_ReadDeltaPlayerstate(&msg,&zero,&client,qfalse);
 CHECK(client.fd.forcePowerLevel[FP_SABER_DEFENSE]==0); // Intentionally absent from JKA snapshots.
 CHECK(client.fd.forcePowersKnown==(1<<FP_SABER_DEFENSE));
 CHECK(client.torsoAnim==BOTH_ST_GUARD_SINGLE);
 movement.ps=&client;CHECK(PM_ST_ManualGuardFrame()); // Prediction must retain the server pose.
 CHECK(client.torsoAnim==BOTH_ST_GUARD_SINGLE);
 movement.cmd.buttons=0;CHECK(!PM_ST_ManualGuardFrame());
 CHECK(client.torsoAnim==BOTH_SABERFAST_STANCE);
 movement.cmd.buttons=BUTTON_BLOCK;client.fd.forcePowersKnown=0;
 CHECK(!PM_ST_ManualGuardFrame());
}
int main() {
 existing_feint_wire_checks();
 byte bytes[16384];msg_t msg;cvar_t shownet={};cl_shownet=&shownet;
 const int inputs[]={BUTTON_BLOCK,BUTTON_BLOCK|BUTTON_FEINT,
  BUTTON_BLOCK|BUTTON_ATTACK,BUTTON_BLOCK|BUTTON_WALKING,BUTTON_BLOCK|BUTTON_TALK,0};
 usercmd_t before={},after={},out={};
 for(int flags:inputs) {
  after=before;after.serverTime+=20;after.buttons=flags;
  after.forwardmove=127;after.rightmove=-127;after.angles[1]=12345;
  MSG_Init(&msg,bytes,sizeof bytes);MSG_WriteDeltaUsercmdKey(&msg,77,&before,&after);
  CHECK(!msg.overflowed);MSG_BeginReading(&msg);
  MSG_ReadDeltaUsercmdKey(&msg,77,&before,&out);
  CHECK(out.buttons==after.buttons && out.serverTime==after.serverTime);
  CHECK(out.forwardmove==127 && out.rightmove==-127 && out.angles[1]==12345);
  before=after;
 }
 guardAfterSnapshot();
 printf("Manual block and feint real engine wire: %d checks passed.\n",checks);
 return 0;
}
