/* Saber Trials combat preset API. GPL-2.0, see LICENSE.txt. */
#ifndef G_STCOMBAT_H
#define G_STCOMBAT_H
typedef enum {
    ST_COMBAT_DEFENSE, ST_COMBAT_RECOVERY, ST_COMBAT_SHIELDS,
    ST_COMBAT_NOFALL, ST_COMBAT_SPEED, ST_COMBAT_FORCEREGEN,
    ST_COMBAT_OPTION_COUNT
} stCombatOption_t;
qboolean ST_CombatEnabled(void);
qboolean ST_CombatOption(stCombatOption_t option);
qboolean ST_MasterEnabled(void);
void ST_CombatInit(void);
void ST_CombatCancel(void);
qboolean ST_CombatPending(void);
void ST_CombatApply(void);
void ST_CombatStatus(void);
void Svcmd_STCombat_f(void);
void Svcmd_STCombatOption_f(void);
void BG_ST_SetParryRecovery(qboolean enabled);
#endif
