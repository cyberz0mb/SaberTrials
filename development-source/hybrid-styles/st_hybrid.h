/* Saber Trials hybrid rules, shared by server and prediction. GPL-2.0-or-later. */
#ifndef ST_HYBRID_H
#define ST_HYBRID_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
enum { STH_ORIGINAL=0, STH_GREEN=4, STH_PURPLE=5, STH_ORANGE=6, STH_PURPLE_RECOVERY_MS=350 };
/* All fields are explicit 32-bit snapshot values. Never serialize padding. */
typedef struct STH_State {
 int32_t style, requestedStyle, attackStyle, attackAnim, attackMove;
 int32_t strikeMs, recoveryMs, committed, enabled, originalStyle;
 uint32_t lastTime, clockSet, allowedMask;
 /* Identities 1..6 are distinct from the original family used by animations.
    availableMask includes stock and hybrid choices; allowedMask remains hybrid-only. */
 int32_t loadout[3], selectedStyle, requestedSelection;
 uint32_t availableMask;
 /* Purple's second swing is offered only after the first completes. During a
    connecting animation strikeMs is its clock; committed remains false. */
 int32_t comboCount, chainPending;
} STH_State;
int STH_SelectionValid(int style);
int STH_LoadoutValid(const int32_t loadout[3]);
int STH_LoadoutParse(const char* text,int32_t out[3]);
void STH_LoadoutDefault(int32_t out[3],int legacyHybrid);
int STH_LoadoutHas(const int32_t loadout[3],int style);
/* Return 0 when no equipped choice is eligible. Never silently add a fourth. */
int STH_LoadoutPick(const int32_t loadout[3],unsigned availableMask,int current);
int STH_LoadoutNext(const int32_t loadout[3],unsigned availableMask,int current);
int STH_SetLoadout(STH_State* s,const int32_t loadout[3]);
int STH_RequestSelection(STH_State* s,int style);
int STH_ApplySelection(STH_State* s,int safe);
int STH_StyleValid(int style);
int STH_ParentStyle(int style);
int STH_ChainLimit(int style);
unsigned STH_AllowedStyles(int offense,unsigned forbidden,unsigned learned,unsigned classMask,int forcedFamily);
int STH_OrdinaryDamage(int style, int progressPermille);
float STH_PowerFactor(int style);
void STH_Init(STH_State* s,uint32_t now,int enabled);
void STH_Request(STH_State* s,int style);
int STH_ApplyRequest(STH_State* s,int safe);
int STH_Commit(STH_State* s,int style,int anim,int move,int durationMs);
int STH_CanFollowup(const STH_State* s);
int STH_Link(STH_State* s,int anim,int move,int durationMs);
void STH_Interrupt(STH_State* s);
unsigned STH_Advance(STH_State* s,uint32_t now,int stopped);
unsigned STH_AdvanceCombo(STH_State* s,uint32_t now,int stopped,int continueAttack);
#ifdef __cplusplus
}
#endif
#endif
