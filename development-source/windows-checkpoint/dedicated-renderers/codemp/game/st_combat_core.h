/* Local combat prototype. No engine globals, allocation, damage or I/O.
 * A server/cgame adapter must supply authoritative lifecycle, phase and contact
 * information. This library alone does not enable a gameplay feature. */
#ifndef ST_COMBAT_CORE_H
#define ST_COMBAT_CORE_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define STC_RULESET_VERSION 1
typedef enum { STC_SINGLE, STC_DUAL, STC_STAFF } STC_Family;
/* Stable IDs, independent of JKA's SS_* enum and its existing masks. */
typedef enum {
 STC_STYLE_NONE, STC_SINGLE_BLUE, STC_SINGLE_YELLOW, STC_SINGLE_RED,
 STC_SINGLE_GREEN, STC_SINGLE_PURPLE, STC_SINGLE_ORANGE,
 STC_DUAL_BLUE, STC_DUAL_YELLOW, STC_DUAL_RED,
 STC_STAFF_BLUE, STC_STAFF_YELLOW, STC_STAFF_RED, STC_STYLE_COUNT
} STC_Style;
/* Same order as JKA's seven ordinary LS_A_* / LS_S_* / LS_R_* moves. */
typedef enum {
 STC_TL_BR, STC_L_R, STC_BL_TR, STC_BR_TL, STC_R_L, STC_TR_BL, STC_T_B,
 STC_DIRECTION_COUNT, STC_DIRECTION_NONE=255
} STC_Direction;
typedef struct {
 const char* name;
 STC_Family family;
 int stanceSlot;
 unsigned parentMask;
 int prototype;
} STC_StyleDef;
typedef struct { int animationGroup, damageGroup; } STC_MoveSource;
const STC_StyleDef* STC_StyleInfo(STC_Style style);
int STC_Source(STC_Style style, STC_Direction direction, STC_MoveSource* out);
/* Call once when converting physical left/right to the chosen hand's logical
 * direction; never mirror twice in the adapter's animation and input paths. */
STC_Direction STC_Mirror(STC_Direction direction, int leftHanded);

typedef enum {
 STC_IDLE, STC_WINDUP, STC_ACTIVE, STC_RECOVERY, STC_REDIRECT_READY,
 STC_CANCELLED, STC_FINISHED
} STC_Phase;
enum {
 STC_GUARD_DEAD=1u<<0, STC_GUARD_GHOST=1u<<1,
 STC_GUARD_FROZEN=1u<<2, STC_GUARD_PAUSED=1u<<3,
 STC_GUARD_THROWN=1u<<4, STC_GUARD_LOCK=1u<<5,
 STC_GUARD_STAGGER=1u<<6, STC_GUARD_HOLSTER=1u<<7,
 STC_GUARD_WEAPON=1u<<8, STC_GUARD_VEHICLE=1u<<9,
 STC_GUARD_SPECIAL=1u<<10, STC_GUARD_ASSET=1u<<11
};
typedef struct {
 unsigned version;
 int enabled;
 unsigned minWindupMs, windowPermille, recoveryMs, cooldownMs;
} STC_Rules;
typedef struct {
 uint32_t epoch, attack, lastTime, lastInputTime;
 STC_Style style;
 STC_Direction direction, redirect;
 STC_Phase phase;
 unsigned windupMs, elapsedMs, recoveryMs, cooldownMs;
 unsigned feintsUsed, contacted, held, inputSeen;
} STC_State;
typedef enum {
 STC_ACCEPTED, STC_NO_EDGE, STC_STALE_COMMAND, STC_DISABLED, STC_INVALID,
 STC_BLOCKED, STC_CONTACTED, STC_COMMITTED, STC_ALREADY_FEINTED,
 STC_TOO_EARLY, STC_SAME_DIRECTION, STC_COOLDOWN
} STC_Result;
STC_Rules STC_DefaultRules(void);
/* Only the lifecycle owner may reset epoch. Use a fresh nonzero epoch on
 * respawn, reconnect, slot reuse or map/time reset. Never reset it on holster,
 * style change or cancellation. Retire the epoch before attack serial wraps. */
void STC_Init(STC_State* state, uint32_t epoch, uint32_t now);
/* Times use modulo-2^32 monotonic milliseconds; backward/ambiguous jumps are
 * rejected. The caller must update at least once per 2^31 milliseconds. */
int STC_Advance(STC_State* state, uint32_t now, unsigned guards);
int STC_BeginAttack(STC_State* state, uint32_t attack, STC_Style style,
                    STC_Direction direction, uint32_t now, unsigned windupMs, unsigned guards);
STC_Result STC_Input(STC_State* state, uint32_t now, int pressed,
                     STC_Direction redirect, unsigned guards, const STC_Rules* rules);
/* Contact includes blocks as well as damaging hits, before damage filtering.
 * Mark actual engine commitment if it happens before the nominal timer. */
void STC_Contact(STC_State* state);
void STC_Commit(STC_State* state);
/* Supply current guards to every advancing call. StartRedirect does not change
 * the original attack identity or allow another cancellation. */
int STC_StartRedirect(STC_State* state, uint32_t now, unsigned windupMs, unsigned guards);
/* Interrupt/finish never erase outstanding recovery or cooldown. */
void STC_Interrupt(STC_State* state);
void STC_FinishAttack(STC_State* state);
#ifdef __cplusplus
}
#endif
#endif
