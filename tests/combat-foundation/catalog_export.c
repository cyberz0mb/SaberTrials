#include "st_combat_core.h"
#include <stdio.h>
int main(void) {
 int i,d;puts("{\"version\":1,\"enabled_in_game\":false,\"styles\":[");
 for(i=STC_SINGLE_BLUE;i<STC_STYLE_COUNT;i++) {
  const STC_StyleDef* s=STC_StyleInfo((STC_Style)i);
  printf("%s{\"id\":%d,\"name\":\"%s\",\"family\":%d,\"stance_slot\":%d,\"prototype\":%s,\"directions\":[",
   i==STC_SINGLE_BLUE?"":",",i,s->name,s->family,s->stanceSlot,s->prototype?"true":"false");
  for(d=0;d<STC_DIRECTION_COUNT;d++) {
   STC_MoveSource source;
   if(!STC_Source((STC_Style)i,(STC_Direction)d,&source))return 1;
   printf("%s{\"direction\":%d,\"animation_group\":%d,\"damage_group\":%d}",
    d?",":"",d,source.animationGroup,source.damageGroup);
  }
  puts("]}");
 }
 puts("]}");return 0;
}
