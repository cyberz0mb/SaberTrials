#include "st_combat_core.h"
#include <stddef.h>
#include <string.h>

static const STC_StyleDef styles[STC_STYLE_COUNT-1]={
 {"Blue",STC_SINGLE,0,1u<<1,0},
 {"Yellow",STC_SINGLE,1,1u<<2,0},
 {"Red",STC_SINGLE,2,1u<<3,0},
 {"Green",STC_SINGLE,3,(1u<<1)|(1u<<2),1},
 {"Purple",STC_SINGLE,4,(1u<<1)|(1u<<3),1},
 {"Orange",STC_SINGLE,5,(1u<<2)|(1u<<3),1},
 {"Dual Blue",STC_DUAL,6,1u<<6,1},
 {"Dual Yellow",STC_DUAL,7,1u<<6,1},
 {"Dual Red",STC_DUAL,8,1u<<6,1},
 {"Staff Blue",STC_STAFF,9,1u<<7,1},
 {"Staff Yellow",STC_STAFF,10,1u<<7,1},
 {"Staff Red",STC_STAFF,11,1u<<7,1}
};
/* Provisional source assignment, not a shipped moveset. Symmetric pairs keep
 * handedness neutral. Dual/staff variants retain their family's damage group;
 * distinct animation/timing profiles must be authored before enabling them. */
static const unsigned char sources[STC_STYLE_COUNT-1][STC_DIRECTION_COUNT]={
 {1,1,1,1,1,1,1}, {2,2,2,2,2,2,2}, {3,3,3,3,3,3,3},
 {1,2,1,1,2,1,2}, {1,3,1,1,3,1,3}, {2,3,2,2,3,2,3},
 {6,6,6,6,6,6,6}, {6,6,6,6,6,6,6}, {6,6,6,6,6,6,6},
 {7,7,7,7,7,7,7}, {7,7,7,7,7,7,7}, {7,7,7,7,7,7,7}
};
static int validDirection(STC_Direction d) { return d>=0 && d<STC_DIRECTION_COUNT; }
const STC_StyleDef* STC_StyleInfo(STC_Style style) {
 return style>STC_STYLE_NONE && style<STC_STYLE_COUNT ? &styles[style-1] : NULL;
}
int STC_Source(STC_Style style,STC_Direction direction,STC_MoveSource* out) {
 if(!out || !STC_StyleInfo(style) || !validDirection(direction))return 0;
 out->damageGroup=out->animationGroup=sources[style-1][direction];return 1;
}
STC_Direction STC_Mirror(STC_Direction direction,int leftHanded) {
 static const STC_Direction mirrored[STC_DIRECTION_COUNT]={
  STC_TR_BL,STC_R_L,STC_BR_TL,STC_BL_TR,STC_L_R,STC_TL_BR,STC_T_B
 };
 if(!validDirection(direction))return STC_DIRECTION_NONE;
 return leftHanded ? mirrored[direction] : direction;
}
STC_Rules STC_DefaultRules(void) {
 STC_Rules r={STC_RULESET_VERSION,0,20,600,200,600};return r;
}
static int validRules(const STC_Rules* r) {
 return r && r->version==STC_RULESET_VERSION && r->minWindupMs<=1000 &&
  r->windowPermille>0 && r->windowPermille<1000 &&
  r->recoveryMs>=1 && r->recoveryMs<=2000 &&
  r->cooldownMs>=r->recoveryMs && r->cooldownMs<=10000;
}
void STC_Init(STC_State* s,uint32_t epoch,uint32_t now) {
 if(!s)return;
 memset(s,0,sizeof(*s));s->epoch=epoch;s->lastTime=now;
 s->direction=s->redirect=STC_DIRECTION_NONE;s->phase=STC_IDLE;
}
static unsigned subtract(unsigned value,uint32_t amount) {return amount>=value ? 0 : value-amount;}
int STC_Advance(STC_State* s,uint32_t now,unsigned guards) {
 uint32_t delta;
 if(!s || !s->epoch)return 0;
 delta=now-s->lastTime;
 if(delta>=UINT32_C(0x80000000))return 0;
 s->lastTime=now;
 if(guards&(STC_GUARD_FROZEN|STC_GUARD_PAUSED))return 1;
 s->cooldownMs=subtract(s->cooldownMs,delta);
 s->recoveryMs=subtract(s->recoveryMs,delta);
 if(s->phase==STC_RECOVERY && !s->recoveryMs)
  s->phase=validDirection(s->redirect)?STC_REDIRECT_READY:STC_CANCELLED;
 else if(s->phase==STC_WINDUP) {
  if(delta>=s->windupMs-s->elapsedMs) {s->elapsedMs=s->windupMs;s->phase=STC_ACTIVE;}
  else s->elapsedMs+=delta;
 }
 return 1;
}
int STC_BeginAttack(STC_State* s,uint32_t attack,STC_Style style,
                    STC_Direction direction,uint32_t now,unsigned windupMs,unsigned guards) {
 if(!s || !attack || !STC_StyleInfo(style) || !validDirection(direction) ||
    windupMs<1 || windupMs>10000 || !STC_Advance(s,now,guards))return 0;
 if(guards || attack<=s->attack || s->recoveryMs ||
    (s->phase!=STC_IDLE && s->phase!=STC_CANCELLED && s->phase!=STC_FINISHED))return 0;
 s->attack=attack;s->style=style;s->direction=direction;s->redirect=STC_DIRECTION_NONE;
 s->phase=STC_WINDUP;s->windupMs=windupMs;s->elapsedMs=0;
 s->feintsUsed=s->contacted=0;
 /* held/inputSeen deliberately survive: holding a key across attacks is not
  * a new button press, and duplicate commands cannot acquire a new identity. */
 return 1;
}
STC_Result STC_Input(STC_State* s,uint32_t now,int pressed,
                     STC_Direction redirect,unsigned guards,const STC_Rules* rules) {
 uint32_t inputDelta;unsigned rising;
 if(!s || !s->epoch)return STC_INVALID;
 inputDelta=now-s->lastInputTime;
 if(s->inputSeen && (inputDelta==0 || inputDelta>=UINT32_C(0x80000000)))return STC_STALE_COMMAND;
 if(!STC_Advance(s,now,guards))return STC_STALE_COMMAND;
 rising=pressed && !s->held;
 s->held=pressed!=0;s->inputSeen=1;s->lastInputTime=now;
 if(!rising)return STC_NO_EDGE;
 if(!validRules(rules) || !validDirection(redirect))return STC_INVALID;
 if(!rules->enabled)return STC_DISABLED;
 if(guards)return STC_BLOCKED;
 if(s->feintsUsed)return STC_ALREADY_FEINTED;
 if(s->cooldownMs)return STC_COOLDOWN;
 if(s->contacted)return STC_CONTACTED;
 if(s->phase!=STC_WINDUP || s->elapsedMs*1000u>s->windupMs*rules->windowPermille)
  return STC_COMMITTED;
 if(s->elapsedMs<rules->minWindupMs)return STC_TOO_EARLY;
 if(redirect==s->direction)return STC_SAME_DIRECTION;
 s->redirect=redirect;s->feintsUsed=1;s->phase=STC_RECOVERY;
 s->recoveryMs=rules->recoveryMs;s->cooldownMs=rules->cooldownMs;
 return STC_ACCEPTED;
}
void STC_Contact(STC_State* s) {if(s && s->attack)s->contacted=1;}
void STC_Commit(STC_State* s) {if(s && s->phase==STC_WINDUP)s->phase=STC_ACTIVE;}
int STC_StartRedirect(STC_State* s,uint32_t now,unsigned windupMs,unsigned guards) {
 if(!s || windupMs<1 || windupMs>10000 || !STC_Advance(s,now,guards) || guards ||
    s->phase!=STC_REDIRECT_READY || !validDirection(s->redirect))return 0;
 s->direction=s->redirect;s->redirect=STC_DIRECTION_NONE;
 s->phase=STC_WINDUP;s->windupMs=windupMs;s->elapsedMs=0;return 1;
}
void STC_Interrupt(STC_State* s) {
 if(!s)return;
 s->redirect=STC_DIRECTION_NONE;
 s->phase=s->recoveryMs?STC_RECOVERY:STC_CANCELLED;
}
void STC_FinishAttack(STC_State* s) {
 if(!s)return;
 s->redirect=STC_DIRECTION_NONE;
 s->phase=s->recoveryMs?STC_RECOVERY:STC_FINISHED;
}
