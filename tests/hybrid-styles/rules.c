#include "st_hybrid.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do { if(!(x)) { fprintf(stderr,"FAIL %s:%d %s\n",__FILE__,__LINE__,#x);exit(1); } } while(0)
int main(void) {
 STH_State s;
 CHECK(!STH_StyleValid(1) && STH_StyleValid(0) && STH_StyleValid(4) && !STH_StyleValid(7));
 CHECK(STH_ParentStyle(4)==2 && STH_ParentStyle(5)==1 && STH_ParentStyle(6)==3);
 CHECK(STH_OrdinaryDamage(4,0)==47 && STH_OrdinaryDamage(4,1000)==47);
 CHECK(STH_OrdinaryDamage(5,0)==2 && STH_OrdinaryDamage(5,500)==120 && STH_OrdinaryDamage(5,1000)==2);
 CHECK(STH_OrdinaryDamage(6,500)==90 && STH_OrdinaryDamage(0,500)==0);
 CHECK(STH_PowerFactor(4)==3.75f && STH_PowerFactor(5)==7.5f && STH_PowerFactor(6)==6.25f);
 CHECK(STH_ChainLimit(4)==6 && STH_ChainLimit(5)==2 && STH_ChainLimit(6)==4);
 CHECK(STH_AllowedStyles(0,0,0,0,1)==0);
 CHECK(STH_AllowedStyles(1,0,0,0,1)==(1u<<5));
 CHECK(STH_AllowedStyles(2,0,0,0,1)==((1u<<4)|(1u<<5)));
 CHECK(STH_AllowedStyles(3,1u<<3,0,0,1)==((1u<<4)|(1u<<5)));
 CHECK(STH_AllowedStyles(3,0,1u<<7,0,1)==0 && STH_AllowedStyles(3,0,0,0,7)==0);
 CHECK(STH_AllowedStyles(0,0,0,1u<<2,1)==(1u<<4)); /* class-controlled style */
 STH_Init(&s,1000,1); s.allowedMask=STH_AllowedStyles(3,0,0,0,1); STH_Request(&s,5); CHECK(STH_ApplyRequest(&s,1));
 CHECK(s.style==5 && STH_Commit(&s,5,99,4,300));
 STH_Request(&s,0); CHECK(!STH_ApplyRequest(&s,1));
 STH_Advance(&s,1200,0); CHECK(s.committed && s.strikeMs==100 && !s.recoveryMs);
 STH_Advance(&s,1300,0); CHECK(!s.committed && s.recoveryMs==350);
 CHECK(!STH_Commit(&s,5,99,4,100) && !STH_ApplyRequest(&s,1));
 STH_Advance(&s,1900,1); CHECK(s.recoveryMs==350); /* freeze does not pay debt */
 STH_Advance(&s,1850,0); CHECK(s.recoveryMs==350); /* stale time cannot rewind */
 STH_Advance(&s,2000,0); CHECK(s.recoveryMs==250);
 STH_Advance(&s,2250,0); CHECK(s.recoveryMs==0 && STH_ApplyRequest(&s,1) && s.style==0);
 STH_Request(&s,5); STH_ApplyRequest(&s,1); STH_Commit(&s,5,100,5,500);
 STH_Advance(&s,2600,0); STH_Interrupt(&s); CHECK(s.recoveryMs==350 && !s.committed);
 STH_Request(&s,6); STH_Interrupt(&s); CHECK(s.recoveryMs==350 && s.attackStyle==5);
 STH_Advance(&s,3250,0); CHECK(STH_ApplyRequest(&s,1) && s.style==6);
 CHECK(STH_Commit(&s,6,100,5,100)); STH_Advance(&s,3350,0); CHECK(!s.recoveryMs);
 STH_Init(&s,0xfffffff0u,1);s.allowedMask=1u<<5; STH_Request(&s,5);STH_ApplyRequest(&s,1);STH_Commit(&s,5,1,1,20);
 STH_Advance(&s,14,0); CHECK(s.recoveryMs==340); /* serial time wrap */
 STH_Init(&s,0,0);STH_Request(&s,5);CHECK(!STH_ApplyRequest(&s,1)&&!STH_Commit(&s,5,1,1,20));
 STH_Init(&s,1000,1);s.allowedMask=1u<<5;STH_Request(&s,6);CHECK(!STH_ApplyRequest(&s,1));
 CHECK(!STH_Commit(&s,6,1,1,100));
 /* Two completed swings, with a real connecting animation, retain one debt. */
 STH_Init(&s,1000,1);s.allowedMask=1u<<5;
 CHECK(STH_Commit(&s,5,99,10,300));CHECK(s.comboCount==1);
 CHECK(!STH_Commit(&s,5,100,11,300)); /* no restart/double commit */
 STH_AdvanceCombo(&s,1200,0,1);CHECK(!STH_CanFollowup(&s));
 STH_AdvanceCombo(&s,1300,0,1);CHECK(STH_CanFollowup(&s));
 CHECK(s.chainPending&&!s.committed&&!s.recoveryMs);
 CHECK(STH_Link(&s,150,50,100));CHECK(!STH_CanFollowup(&s));
 CHECK(!STH_Commit(&s,5,100,11,300));
 STH_AdvanceCombo(&s,1400,0,0);CHECK(STH_CanFollowup(&s));
 CHECK(!STH_Link(&s,151,51,100)); /* exactly one connecting transition */
 CHECK(STH_Commit(&s,5,100,11,300));CHECK(s.comboCount==2&&!s.chainPending);
 CHECK(!STH_Commit(&s,5,101,12,300));
 STH_AdvanceCombo(&s,1700,0,1);CHECK(s.recoveryMs==350&&!s.committed&&!s.chainPending);
 CHECK(!STH_Commit(&s,5,101,12,300));
 STH_Advance(&s,2050,0);CHECK(!s.recoveryMs);
 CHECK(STH_Commit(&s,5,99,10,300)&&s.comboCount==1);
 /* Direct opposite-direction follow-up also works; no transition is required. */
 STH_AdvanceCombo(&s,2350,0,1);CHECK(STH_Commit(&s,5,100,11,300));
 STH_Interrupt(&s);CHECK(s.recoveryMs==350&&!s.chainPending&&!s.comboCount);
 STH_Advance(&s,2700,0);CHECK(STH_Commit(&s,5,99,10,300));
 STH_AdvanceCombo(&s,3000,0,1);CHECK(STH_Link(&s,150,50,100));
 STH_AdvanceCombo(&s,3050,1,1);CHECK(s.strikeMs==100&&!s.recoveryMs);
 STH_Interrupt(&s);CHECK(s.recoveryMs==350); /* transition interrupt owes recovery */
 STH_Advance(&s,3400,0);CHECK(STH_Commit(&s,5,99,10,300));
 STH_AdvanceCombo(&s,3700,0,1);CHECK(STH_CanFollowup(&s));
 STH_AdvanceCombo(&s,3710,0,1);CHECK(s.recoveryMs==340); /* lost/invalid next move cannot leave an open chain */
 puts("hybrid selection, damage and recovery checks passed");return 0;
}
