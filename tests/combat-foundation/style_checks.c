#include "st_combat_core.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do { ++checks;if(!(x)){fprintf(stderr,"line %d: %s\n",__LINE__,#x);exit(1);} } while(0)
int main(void) {
 int checks=0,i,d;STC_MoveSource source;
 CHECK(STC_StyleInfo(STC_STYLE_NONE)==NULL);
 CHECK(STC_StyleInfo((STC_Style)999)==NULL);
 CHECK(!STC_Source(STC_SINGLE_BLUE,(STC_Direction)-1,&source));
 CHECK(!STC_Source(STC_SINGLE_BLUE,STC_T_B,NULL));
 for(i=STC_SINGLE_BLUE;i<STC_STYLE_COUNT;i++) {
  const STC_StyleDef* style=STC_StyleInfo((STC_Style)i);
  int seen=0;
  CHECK(style && style->name && style->stanceSlot==i-1);
  for(d=0;d<STC_DIRECTION_COUNT;d++) {
   CHECK(STC_Source((STC_Style)i,(STC_Direction)d,&source));
   CHECK(source.damageGroup==source.animationGroup);
   CHECK(source.damageGroup>=1 && source.damageGroup<=7);
   CHECK(source.damageGroup!=4 && source.damageGroup!=5);
   seen|=1<<source.damageGroup;
   if(style->family==STC_DUAL)CHECK(source.damageGroup==6);
   if(style->family==STC_STAFF)CHECK(source.damageGroup==7);
  }
  CHECK(seen==style->parentMask);
  CHECK(style->prototype==(i>=STC_SINGLE_GREEN));
 }
 CHECK(STC_StyleInfo(STC_SINGLE_GREEN)->parentMask==((1<<1)|(1<<2)));
 CHECK(STC_StyleInfo(STC_SINGLE_PURPLE)->parentMask==((1<<1)|(1<<3)));
 CHECK(STC_StyleInfo(STC_SINGLE_ORANGE)->parentMask==((1<<2)|(1<<3)));
 printf("Style catalog: %d checks passed; prototype catalog is not an unlock.\n",checks);return 0;
}
