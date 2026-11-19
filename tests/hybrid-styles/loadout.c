#include "st_hybrid.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int checks;
#define CHECK(x) do { ++checks; if(!(x)) { fprintf(stderr,"loadout:%d %s\n",__LINE__,#x);exit(1); } } while(0)
static const unsigned all=0x7e;
static void parsing(void) {
 int32_t out[3]={6,5,4},before[3];int i;
 const char *bad[]={"","1","1 2","1 2 3 4","1 1 2","0 2 3","1 2 7","-1 2 3","+1 2 3","01 2 3","1,2,3","123","1 2 3x","1 2 3;quit","99999999999999999 2 3","1 2 3.0",NULL};
 CHECK(STH_LoadoutParse("1 2 3",out)&&out[0]==1&&out[1]==2&&out[2]==3);
 CHECK(STH_LoadoutParse(" \t6  4 5\r\n",out)&&out[0]==6&&out[1]==4&&out[2]==5);
 memcpy(before,out,sizeof out);
 for(i=0;bad[i];i++) {CHECK(!STH_LoadoutParse(bad[i],out));CHECK(!memcmp(before,out,sizeof out));}
 CHECK(!STH_LoadoutParse(NULL,out));CHECK(!STH_LoadoutParse("1 2 3",NULL));
 for(i=0;i<=7;i++) {
  STH_LoadoutDefault(out,i);CHECK(STH_LoadoutValid(out));
  CHECK(out[0]==(i>=4&&i<=6?i:1)&&out[1]==2&&out[2]==3);
 }
 out[0]=out[1]=1;CHECK(!STH_LoadoutValid(out));
 CHECK(!STH_LoadoutValid(NULL));CHECK(!STH_LoadoutHas(NULL,1));
}
static void combinations(void) {
 int a,b,c,i,current,got,first,expected,nextStep;unsigned mask;int32_t slots[3];
 /* All 120 ordered three-style choices and every subset of the six styles. */
 for(a=1;a<=6;a++)for(b=1;b<=6;b++)for(c=1;c<=6;c++) {
  if(a==b||b==c||a==c)continue;
  slots[0]=a;slots[1]=b;slots[2]=c;
  CHECK(STH_LoadoutValid(slots));
  for(mask=0;mask<=all;mask+=2) {
   first=0;
   for(i=0;i<3;i++)if(mask&(1u<<slots[i])) {first=slots[i];break;}
   CHECK(STH_LoadoutPick(slots,mask,0)==first);
   for(current=0;current<=6;current++) {
    expected=first;
    if((current==a||current==b||current==c)&&(mask&(1u<<current)))expected=current;
    CHECK(STH_LoadoutPick(slots,mask,current)==expected);
    expected=first;
    for(i=0;i<3;i++)if(slots[i]==current) {
     expected=0;
     for(nextStep=1;nextStep<=3;nextStep++)if(mask&(1u<<slots[(i+nextStep)%3])) {expected=slots[(i+nextStep)%3];break;}
     break;
    }
    got=STH_LoadoutNext(slots,mask,current);CHECK(got==expected);
    if(got)CHECK(STH_LoadoutHas(slots,got)&&(mask&(1u<<got)));
   }
  }
 }
}
static void recovery_and_authority(void) {
 STH_State s,before;int32_t slots[3]={5,2,6},replacement[3]={1,4,3},bad[3]={1,1,2};
 STH_Init(&s,1000,1);s.availableMask=all;s.allowedMask=(1u<<4)|(1u<<5)|(1u<<6);
 CHECK(STH_SetLoadout(&s,slots));CHECK(STH_RequestSelection(&s,5));
 CHECK(!STH_ApplySelection(&s,0));CHECK(STH_ApplySelection(&s,1));
 CHECK(s.selectedStyle==5&&s.style==5&&s.requestedStyle==5);
 CHECK(!STH_ApplySelection(&s,1));CHECK(STH_Commit(&s,5,99,13,300));
 CHECK(STH_RequestSelection(&s,2));CHECK(!STH_ApplySelection(&s,1));
 CHECK(s.selectedStyle==5&&s.attackStyle==5&&s.strikeMs==300);
 STH_Advance(&s,1300,0);CHECK(s.recoveryMs==350&&!s.committed);
 CHECK(!STH_ApplySelection(&s,1));
 before=s;CHECK(!STH_SetLoadout(&s,bad));CHECK(!memcmp(&before,&s,sizeof s));
 CHECK(STH_SetLoadout(&s,replacement));CHECK(s.recoveryMs==350);
 CHECK(STH_RequestSelection(&s,4));CHECK(!STH_ApplySelection(&s,1));
 STH_Advance(&s,1900,1);CHECK(s.recoveryMs==350&&!STH_ApplySelection(&s,1));
 STH_Advance(&s,2250,0);CHECK(!s.recoveryMs&&STH_ApplySelection(&s,1));
 CHECK(s.selectedStyle==4&&s.style==4);
 CHECK(STH_RequestSelection(&s,1));CHECK(STH_ApplySelection(&s,1));
 CHECK(s.selectedStyle==1&&!s.style&&!s.requestedStyle);
 CHECK(!STH_RequestSelection(&s,5)); /* Not one of the three equipped choices. */
 CHECK(!STH_RequestSelection(&s,2)); /* Unselected stock is not an extra fourth choice. */
 s.availableMask=1u<<2;CHECK(STH_LoadoutPick(s.loadout,s.availableMask,1)==0);
 CHECK(STH_RequestSelection(&s,2));CHECK(STH_ApplySelection(&s,1));
 CHECK(s.selectedStyle==2&&!s.style); /* Only explicit no-choice stock fallback. */
 s.availableMask=1u<<5;CHECK(!STH_RequestSelection(&s,5)); /* Never hidden hybrid fallback. */
 s.availableMask=all;CHECK(STH_RequestSelection(&s,4));s.availableMask=1u<<1;
 CHECK(!STH_ApplySelection(&s,1));CHECK(s.selectedStyle==2); /* Server eligibility changed while queued. */
 CHECK(!STH_RequestSelection(&s,0)&&!STH_RequestSelection(&s,7));
 STH_Init(&s,0,0);before=s;CHECK(!STH_SetLoadout(&s,slots));CHECK(!STH_RequestSelection(&s,5));
 CHECK(!STH_ApplySelection(&s,1));CHECK(!memcmp(&before,&s,sizeof s));
}
int main(void) {parsing();combinations();recovery_and_authority();printf("loadout: %d checks passed\n",checks);return 0;}
