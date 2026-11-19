#include "st_combat_core.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do { ++checks; if(!(x)) {fprintf(stderr,"line %d: %s\n",__LINE__,#x);exit(1);} } while(0)
static int checks;
static STC_Rules rules;
static STC_State start(uint32_t now) {
 STC_State s; STC_Init(&s,4,now);
 CHECK(STC_BeginAttack(&s,1,STC_SINGLE_BLUE,STC_TL_BR,now,200,0));
 return s;
}
static void boundaries(void) {
 STC_State s=start(1000), before;
 CHECK(STC_Input(&s,1019,1,STC_TR_BL,0,&rules)==STC_TOO_EARLY);
 CHECK(STC_Input(&s,1020,1,STC_TR_BL,0,&rules)==STC_NO_EDGE);
 CHECK(STC_Input(&s,1021,0,STC_TR_BL,0,&rules)==STC_NO_EDGE);
 CHECK(STC_Input(&s,1022,1,STC_TR_BL,0,&rules)==STC_ACCEPTED);
 CHECK(s.phase==STC_RECOVERY && s.redirect==STC_TR_BL && s.feintsUsed==1);
 CHECK(s.recoveryMs==200 && s.cooldownMs==600 && s.attack==1 && s.epoch==4);
 before=s;
 CHECK(STC_Input(&s,1022,0,STC_T_B,0,&rules)==STC_STALE_COMMAND);
 CHECK(memcmp(&s,&before,sizeof(s))==0);
 CHECK(STC_Input(&s,1021,1,STC_T_B,0,&rules)==STC_STALE_COMMAND);
 CHECK(memcmp(&s,&before,sizeof(s))==0);
 CHECK(STC_Advance(&s,1221,0) && s.phase==STC_RECOVERY);
 CHECK(!STC_StartRedirect(&s,1221,200,0));
 CHECK(STC_StartRedirect(&s,1222,200,0));
 CHECK(s.phase==STC_WINDUP && s.direction==STC_TR_BL && s.feintsUsed==1);
 CHECK(STC_Input(&s,1242,0,STC_T_B,0,&rules)==STC_NO_EDGE);
 CHECK(STC_Input(&s,1243,1,STC_T_B,0,&rules)==STC_ALREADY_FEINTED);
 CHECK(STC_Advance(&s,1422,0) && s.phase==STC_ACTIVE);
 STC_FinishAttack(&s);
 /* Cooldown limits new feints, not legitimate attacks after recovery. */
 CHECK(STC_BeginAttack(&s,2,STC_SINGLE_RED,STC_T_B,1422,200,0));
 CHECK(STC_Input(&s,1442,0,STC_TR_BL,0,&rules)==STC_NO_EDGE);
 CHECK(STC_Input(&s,1443,1,STC_TR_BL,0,&rules)==STC_COOLDOWN);
 s=start(1000);
 CHECK(STC_Input(&s,1120,1,STC_TR_BL,0,&rules)==STC_ACCEPTED);
 s=start(1000);
 CHECK(STC_Input(&s,1121,1,STC_TR_BL,0,&rules)==STC_COMMITTED);
 s=start(1000);
 CHECK(STC_Input(&s,1200,1,STC_TR_BL,0,&rules)==STC_COMMITTED);
}
static void guards(void) {
 STC_State s; unsigned bit;
 for(bit=1;bit<=STC_GUARD_ASSET;bit<<=1) {
  s=start(1000);
  CHECK(STC_Input(&s,1050,1,STC_TR_BL,bit,&rules)==STC_BLOCKED);
  CHECK(s.phase==STC_WINDUP && s.feintsUsed==0);
  CHECK(STC_Input(&s,1051,1,STC_TR_BL,0,&rules)==STC_NO_EDGE);
 }
 s=start(1000);STC_Contact(&s);
 CHECK(STC_Input(&s,1050,1,STC_TR_BL,0,&rules)==STC_CONTACTED);
 s=start(1000);STC_Commit(&s);
 CHECK(STC_Input(&s,1050,1,STC_TR_BL,0,&rules)==STC_COMMITTED);
 s=start(1000);
 CHECK(STC_Input(&s,1050,1,STC_TL_BR,0,&rules)==STC_SAME_DIRECTION);
 s=start(1000);
 CHECK(STC_Input(&s,1050,1,(STC_Direction)99,0,&rules)==STC_INVALID);
 s=start(1000);rules.enabled=0;
 CHECK(STC_Input(&s,1050,1,STC_TR_BL,0,&rules)==STC_DISABLED);
 rules.enabled=1;
 CHECK(STC_Input(&s,1051,1,STC_TR_BL,0,&rules)==STC_NO_EDGE);
}
static void lifecycle(void) {
 STC_State s=start(1000), before;
 CHECK(STC_Input(&s,1050,1,STC_TR_BL,0,&rules)==STC_ACCEPTED);
 CHECK(STC_Advance(&s,5000,STC_GUARD_FROZEN));
 CHECK(s.recoveryMs==200 && s.cooldownMs==600);
 CHECK(STC_Advance(&s,9000,STC_GUARD_PAUSED));
 CHECK(s.recoveryMs==200 && s.cooldownMs==600);
 STC_Interrupt(&s);
 CHECK(!STC_BeginAttack(&s,2,STC_SINGLE_RED,STC_T_B,9001,200,0));
 CHECK(!STC_StartRedirect(&s,9200,200,0));
 CHECK(s.phase==STC_CANCELLED && s.cooldownMs==400);
 CHECK(STC_BeginAttack(&s,2,STC_SINGLE_RED,STC_T_B,9600,200,0));
 STC_FinishAttack(&s);
 CHECK(!STC_BeginAttack(&s,2,STC_SINGLE_RED,STC_T_B,9601,200,0));
 before=s;
 CHECK(!STC_Advance(&s,100,0));
 CHECK(memcmp(&s,&before,sizeof(s))==0);
 STC_Init(&s,5,100);
 CHECK(STC_BeginAttack(&s,1,STC_STAFF_RED,STC_T_B,100,300,0));
 CHECK(s.epoch==5 && s.attack==1 && s.feintsUsed==0);
 s=start(UINT32_MAX-50);
 CHECK(STC_Input(&s,UINT32_MAX-20,1,STC_TR_BL,0,&rules)==STC_ACCEPTED);
 CHECK(STC_StartRedirect(&s,179,200,0));
 CHECK(s.recoveryMs==0 && s.cooldownMs==400);
}
static void redirect_guards(void) {
 STC_State s=start(1000);unsigned bit;
 CHECK(STC_Input(&s,1050,1,STC_TR_BL,0,&rules)==STC_ACCEPTED);
 CHECK(!STC_StartRedirect(&s,5000,200,STC_GUARD_FROZEN));
 CHECK(s.recoveryMs==200 && s.cooldownMs==600);
 CHECK(!STC_StartRedirect(&s,5200,200,STC_GUARD_DEAD));
 CHECK(s.phase==STC_REDIRECT_READY);
 for(bit=1;bit<=STC_GUARD_ASSET;bit<<=1) {
  STC_State fresh;STC_Init(&fresh,1,1000);
  CHECK(!STC_BeginAttack(&fresh,1,STC_SINGLE_BLUE,STC_T_B,1100,200,bit));
  CHECK(!STC_StartRedirect(&s,5200,200,bit));
 }
 CHECK(STC_StartRedirect(&s,5200,200,0));
}
static void exhaustive(void) {
 int style,direction,target,hand;
 for(style=STC_SINGLE_BLUE;style<STC_STYLE_COUNT;style++)
 for(direction=0;direction<STC_DIRECTION_COUNT;direction++)
 for(target=0;target<STC_DIRECTION_COUNT;target++)
 for(hand=0;hand<2;hand++) {
  STC_State s;STC_Direction d=STC_Mirror((STC_Direction)direction,hand);
  STC_Direction t=STC_Mirror((STC_Direction)target,hand);
  STC_Init(&s,1,100);
  CHECK(STC_BeginAttack(&s,1,(STC_Style)style,d,100,200,0));
  CHECK(STC_Input(&s,150,1,t,0,&rules)==(d==t?STC_SAME_DIRECTION:STC_ACCEPTED));
  CHECK(STC_Mirror(d,hand)==direction);
 }
}
int main(void) {
 rules=STC_DefaultRules();CHECK(!rules.enabled);rules.enabled=1;
 boundaries();guards();lifecycle();redirect_guards();exhaustive();
 printf("Feint controller: %d checks passed (no game server launched).\n",checks);return 0;
}
