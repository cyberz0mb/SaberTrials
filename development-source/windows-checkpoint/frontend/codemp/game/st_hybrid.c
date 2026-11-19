#include "st_hybrid.h"
#include <string.h>
int STH_SelectionValid(int style) {return style>=1 && style<=6;}
int STH_LoadoutValid(const int32_t loadout[3]) {
 return loadout && STH_SelectionValid(loadout[0]) && STH_SelectionValid(loadout[1]) &&
        STH_SelectionValid(loadout[2]) && loadout[0]!=loadout[1] &&
        loadout[0]!=loadout[2] && loadout[1]!=loadout[2];
}
static int STH_Space(char c) {return c==' ' || c=='\t' || c=='\r' || c=='\n' || c=='\f' || c=='\v';}
int STH_LoadoutParse(const char* text,int32_t out[3]) {
 int32_t parsed[3];int i;
 if(!text || !out)return 0;
 while(STH_Space(*text))text++;
 for(i=0;i<3;i++) {
  if(*text<'1' || *text>'6')return 0;
  parsed[i]=*text++-'0';
  if(i<2 && !STH_Space(*text))return 0;
  while(STH_Space(*text))text++;
 }
 if(*text || !STH_LoadoutValid(parsed))return 0;
 memcpy(out,parsed,sizeof parsed);return 1;
}
void STH_LoadoutDefault(int32_t out[3],int legacyHybrid) {
 out[0]=legacyHybrid>=4 && legacyHybrid<=6?legacyHybrid:1;out[1]=2;out[2]=3;
}
int STH_LoadoutHas(const int32_t loadout[3],int style) {
 return STH_LoadoutValid(loadout) && STH_SelectionValid(style) &&
        (loadout[0]==style || loadout[1]==style || loadout[2]==style);
}
int STH_LoadoutPick(const int32_t loadout[3],unsigned availableMask,int current) {
 int i;
 if(!STH_LoadoutValid(loadout))return 0;
 if(STH_LoadoutHas(loadout,current) && (availableMask&(1u<<current)))return current;
 for(i=0;i<3;i++)if(availableMask&(1u<<loadout[i]))return loadout[i];
 return 0;
}
int STH_LoadoutNext(const int32_t loadout[3],unsigned availableMask,int current) {
 int i,next;
 if(!STH_LoadoutValid(loadout))return 0;
 for(i=0;i<3;i++)if(loadout[i]==current) {
  for(next=1;next<=3;next++)if(availableMask&(1u<<loadout[(i+next)%3]))return loadout[(i+next)%3];
  return 0;
 }
 return STH_LoadoutPick(loadout,availableMask,0);
}
int STH_SetLoadout(STH_State* s,const int32_t loadout[3]) {
 if(!s->enabled || !STH_LoadoutValid(loadout))return 0;
 /* A menu edit never pays or discards a committed attack's recovery debt. */
 memcpy(s->loadout,loadout,sizeof s->loadout);return 1;
}
static int STH_SelectionAllowed(const STH_State* s,int style) {
 if(!STH_SelectionValid(style) || !(s->availableMask&(1u<<style)))return 0;
 if(STH_LoadoutHas(s->loadout,style))return 1;
 /* Server restrictions can make all three choices unusable. The adapter may
    explicitly request a legal stock fallback, never an unselected hybrid. */
 return style<=3 && STH_LoadoutValid(s->loadout) && !STH_LoadoutPick(s->loadout,s->availableMask,0);
}
int STH_RequestSelection(STH_State* s,int style) {
 if(!s->enabled || !STH_SelectionAllowed(s,style))return 0;
 s->requestedSelection=style;s->requestedStyle=style>=4?style:0;return 1;
}
int STH_ApplySelection(STH_State* s,int safe) {
 int hybrid;
 if(!s->enabled || !safe || s->committed || s->chainPending || s->recoveryMs || !STH_SelectionAllowed(s,s->requestedSelection))return 0;
 hybrid=s->requestedSelection>=4?s->requestedSelection:0;
 if(s->selectedStyle==s->requestedSelection && s->style==hybrid)return 0;
 s->selectedStyle=s->requestedSelection;s->style=hybrid;s->requestedStyle=hybrid;return 1;
}
int STH_StyleValid(int s) {return s==0 || s==4 || s==5 || s==6;}
int STH_ParentStyle(int s) {return s==4?2:s==5?1:s==6?3:0;}
int STH_ChainLimit(int s) {return s==4?6:s==5?2:s==6?4:0;}
unsigned STH_AllowedStyles(int offense,unsigned forbidden,unsigned learned,unsigned classMask,int forcedFamily) {
 unsigned mask=0;int style;
 /* Stock forced dual/staff families never become single-saber hybrids. */
 if(forcedFamily>3 || learned==(1u<<6) || learned==(1u<<7))return 0;
 for(style=4;style<=6;style++) {
  int parent=STH_ParentStyle(style);
  if(forbidden&(1u<<parent))continue;
  if(classMask ? !(classMask&(1u<<parent)) : offense<parent)continue;
  mask|=1u<<style;
 }
 return mask;
}
int STH_OrdinaryDamage(int s,int p) {
 int peak=s==5?120:s==6?90:0;
 if(s==4)return 47;
 if(!peak)return 0;
 if(p<0)p=0; if(p>1000)p=1000;
 if(p>500)p=1000-p;
 p=peak*p/500;
 return p<2?2:p;
}
float STH_PowerFactor(int s) {return s==4?3.75f:s==5?7.5f:s==6?6.25f:0.0f;}
void STH_Init(STH_State* s,uint32_t now,int enabled) {
 memset(s,0,sizeof(*s));
 if(enabled) {s->lastTime=now;s->clockSet=1;s->enabled=1;STH_LoadoutDefault(s->loadout,0);}
}
void STH_Request(STH_State* s,int style) {
 if(s->enabled)s->requestedStyle=STH_StyleValid(style)?style:0;
}
int STH_ApplyRequest(STH_State* s,int safe) {
 if(!s->enabled || !safe || s->committed || s->chainPending || s->recoveryMs || s->style==s->requestedStyle)return 0;
 if(s->requestedStyle && !(s->allowedMask&(1u<<s->requestedStyle)))return 0;
 s->style=s->requestedStyle;return 1;
}
int STH_Commit(STH_State* s,int style,int anim,int move,int durationMs) {
 if(!s->enabled || !style || !STH_StyleValid(style) || !(s->allowedMask&(1u<<style)) || s->recoveryMs || durationMs<=0)return 0;
 if((s->committed || s->chainPending) && s->attackStyle==STH_PURPLE &&
    (style!=STH_PURPLE || !STH_CanFollowup(s)))return 0;
 if(style==STH_PURPLE) {
  if(s->comboCount && !STH_CanFollowup(s))return 0;
  s->comboCount++;s->chainPending=0;
 }
 s->attackStyle=style;s->attackAnim=anim;s->attackMove=move;
 s->strikeMs=durationMs>10000?10000:durationMs;s->committed=1;return 1;
}
int STH_CanFollowup(const STH_State* s) {
 return s->enabled && s->attackStyle==STH_PURPLE && s->comboCount==1 &&
        s->chainPending && !s->committed && !s->strikeMs && !s->recoveryMs;
}
int STH_Link(STH_State* s,int anim,int move,int durationMs) {
 if(!STH_CanFollowup(s) || s->chainPending!=1 || durationMs<=0)return 0;
 s->attackAnim=anim;s->attackMove=move;
 s->chainPending=2;s->strikeMs=durationMs>10000?10000:durationMs;return 1;
}
void STH_Interrupt(STH_State* s) {
 if((s->committed || s->chainPending) && s->attackStyle==STH_PURPLE && s->recoveryMs<STH_PURPLE_RECOVERY_MS)
  s->recoveryMs=STH_PURPLE_RECOVERY_MS;
 s->strikeMs=0;s->committed=0;s->comboCount=0;s->chainPending=0;
}
unsigned STH_Advance(STH_State* s,uint32_t now,int stopped) {
 return STH_AdvanceCombo(s,now,stopped,0);
}
unsigned STH_AdvanceCombo(STH_State* s,uint32_t now,int stopped,int continueAttack) {
 uint32_t elapsed,total;
 if(!s->clockSet) {s->clockSet=1;s->lastTime=now;return 0;}
 elapsed=now-s->lastTime;
 /* Ignore stale serial time, including signed command-time wrap. */
 if(elapsed>=0x80000000u)return 0;
 s->lastTime=now;
 if(stopped)return 0;
 /* ClientThink bounds commands; refuse absurd jumps rather than erase debt. */
 if(elapsed>1000u)elapsed=1000u;
 total=elapsed;
 /* The adapter must accept a connecting move or second strike in the same
    movement step as the offer. A failed animation cannot leave free debt. */
 if(s->chainPending && !s->strikeMs)STH_Interrupt(s);
 if(s->committed || s->chainPending) {
  if(elapsed<(uint32_t)s->strikeMs) {s->strikeMs-=(int)elapsed;return elapsed;}
  elapsed-=(uint32_t)s->strikeMs;
  if(s->attackStyle==STH_PURPLE && s->comboCount==1 &&
     (s->chainPending || continueAttack)) {
   s->strikeMs=0;s->committed=0;
   if(!s->chainPending)s->chainPending=1;
   return total;
  }
  STH_Interrupt(s);
 }
 if(s->recoveryMs>0)s->recoveryMs=elapsed>=(uint32_t)s->recoveryMs?0:s->recoveryMs-(int)elapsed;
 return total;
}
