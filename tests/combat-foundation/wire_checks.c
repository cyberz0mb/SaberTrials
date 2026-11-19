#include "st_combat_wire.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do {++checks;if(!(x)){fprintf(stderr,"line %d: %s\n",__LINE__,#x);exit(1);}} while(0)
static int checks;
static uint32_t randomState=0x917f55u;
static uint32_t nextRandom(void) {
 randomState=randomState*1664525u+1013904223u;return randomState;
}
static void roundtrip(const STC_State* state) {
 unsigned char bytes[STC_WIRE_SIZE];STC_State restored;
 memset(&restored,0xcc,sizeof(restored));
 CHECK(STC_Encode(state,bytes,sizeof(bytes)));
 CHECK(bytes[0]=='S' && bytes[1]=='T' && bytes[2]=='C' && bytes[3]==1);
 CHECK(STC_Decode(&restored,bytes,sizeof(bytes)));
 CHECK(memcmp(&restored,state,sizeof(restored))==0);
}
int main(void) {
 STC_State s,other,before;STC_Rules rules=STC_DefaultRules();
 unsigned char bytes[STC_WIRE_SIZE];unsigned i,j;
 rules.enabled=1;
 STC_Init(&s,0x12345678u,UINT32_MAX-100);roundtrip(&s);
 CHECK(STC_BeginAttack(&s,42,STC_SINGLE_GREEN,STC_TL_BR,UINT32_MAX-100,200,0));roundtrip(&s);
 CHECK(STC_Input(&s,UINT32_MAX-50,1,STC_TR_BL,0,&rules)==STC_ACCEPTED);roundtrip(&s);
 STC_Contact(&s);roundtrip(&s);
 CHECK(STC_StartRedirect(&s,149,200,0));roundtrip(&s);
 STC_Interrupt(&s);roundtrip(&s);
 CHECK(STC_Encode(&s,bytes,sizeof(bytes)));
 STC_Init(&other,99,100);before=other;
 for(i=0;i<STC_WIRE_SIZE;i++) {
  CHECK(!STC_Decode(&other,bytes,i));CHECK(memcmp(&other,&before,sizeof(other))==0);
 }
 CHECK(!STC_Decode(&other,bytes,STC_WIRE_SIZE+1));
 bytes[3]=2;CHECK(!STC_Decode(&other,bytes,sizeof(bytes)));bytes[3]=1;
 /* Corrupt bounded enum/counter fields independently; no partial state write. */
 for(j=4;j<16;j++) {
  unsigned char bad[STC_WIRE_SIZE];memcpy(bad,bytes,sizeof(bad));
  memset(bad+8+4*j,0xff,4);
  CHECK(!STC_Decode(&other,bad,sizeof(bad)));
  CHECK(memcmp(&other,&before,sizeof(other))==0);
 }
 CHECK(!STC_Encode(NULL,bytes,sizeof(bytes)));
 CHECK(!STC_Decode(NULL,bytes,sizeof(bytes)));
 CHECK(!STC_Decode(&other,NULL,sizeof(bytes)));
 /* Repeated state transitions remain serializable, including pauses, time
  * wrap, cancellation and input arrival during recovery. Fixed seed. */
 STC_Init(&s,7,UINT32_MAX-4000);
 for(i=0;i<20000;i++) {
  uint32_t value=nextRandom(),now=s.lastTime+(value%51);
  unsigned guards=(value%19==0)?STC_GUARD_PAUSED:0;
  switch(value%7) {
  case 0:STC_BeginAttack(&s,s.attack+1,(STC_Style)(1+value%12),
                       (STC_Direction)(value%7),now,100+value%700,guards);break;
  case 1:STC_Input(&s,now,(value>>4)&1,(STC_Direction)((value>>8)%7),guards,&rules);break;
  case 2:STC_Advance(&s,now,guards);STC_Contact(&s);break;
  case 3:STC_Advance(&s,now,guards);STC_Commit(&s);break;
  case 4:STC_StartRedirect(&s,now,100+value%700,guards);break;
  case 5:STC_Advance(&s,now,guards);STC_Interrupt(&s);break;
  case 6:STC_Advance(&s,now,guards);STC_FinishAttack(&s);break;
  }
  roundtrip(&s);
 }
 printf("Combat snapshot codec: %d checks passed; engine transport is not yet connected.\n",checks);
 return 0;
}
