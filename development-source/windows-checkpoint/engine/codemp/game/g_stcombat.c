/* Saber Trials combat presets. GPL-2.0, see LICENSE.txt. */
#include "g_local.h"
#include "g_stcombat.h"

static const char *optionNames[ST_COMBAT_OPTION_COUNT] = {
    "defense", "recovery", "shields", "nofall", "speed", "forceregen"
};
static const char *optionCvarNames[ST_COMBAT_OPTION_COUNT] = {
    "st_activeDefense", "st_parryRecovery", "st_shields",
    "st_noFallDamage", "st_forceSpeed", "st_fastForceRegen"
};
static vmCvar_t *optionCvars[ST_COMBAT_OPTION_COUNT] = {
    &st_activeDefense, &st_parryRecovery, &st_shields,
    &st_noFallDamage, &st_forceSpeed, &st_fastForceRegen
};
static int pendingMode = -1;
static int pendingOptions[ST_COMBAT_OPTION_COUNT];

static const char *ST_CombatName(int mode) {
    return mode == 1 ? "Saber Trials Combat" : "Original JKA";
}

qboolean ST_CombatEnabled(void) {
    return st_combatMode.integer == 1;
}

qboolean ST_CombatOption(stCombatOption_t option) {
    return option >= 0 && option < ST_COMBAT_OPTION_COUNT &&
        ST_CombatEnabled() && optionCvars[option]->integer == 1;
}

qboolean ST_MasterEnabled(void) {
    return ST_CombatEnabled() && st_masterModeActive.integer == ST_MASTER_ON;
}

void ST_CombatCancel(void) {
    int i;
    pendingMode = -1;
    for (i = 0; i < ST_COMBAT_OPTION_COUNT; ++i) pendingOptions[i] = -1;
}

void ST_CombatInit(void) {
    int flags = dmflags.integer & ~DF_NO_FALLING;
    ST_CombatCancel();
    if (ST_CombatOption(ST_COMBAT_NOFALL)) flags |= DF_NO_FALLING;
    trap->Cvar_Set("dmflags", va("%i", flags));
    trap->Cvar_Update(&dmflags);
    trap->Cvar_Set("g_forceRegenTime", va("%i",
        ST_CombatOption(ST_COMBAT_FORCEREGEN) ?
        Com_Clampi(50, 1000, st_forceRegenInterval.integer) : 200));
    trap->Cvar_Update(&g_forceRegenTime);
    BG_ST_SetParryRecovery(ST_CombatOption(ST_COMBAT_RECOVERY));
}

qboolean ST_CombatPending(void) {
    int i;
    if (pendingMode != -1) return qtrue;
    for (i = 0; i < ST_COMBAT_OPTION_COUNT; ++i)
        if (pendingOptions[i] != -1) return qtrue;
    return qfalse;
}

void ST_CombatApply(void) {
    int i;
    if (pendingMode != -1) {
        trap->Cvar_Set("st_combatMode", va("%i", pendingMode));
        trap->SendServerCommand(-1, va("print \"Combat preset: %s begins after this restart.\n\"", ST_CombatName(pendingMode)));
    }
    for (i = 0; i < ST_COMBAT_OPTION_COUNT; ++i) {
        if (pendingOptions[i] != -1)
            trap->Cvar_Set(optionCvarNames[i], pendingOptions[i] ? "1" : "0");
    }
    ST_CombatCancel();
}

void Svcmd_STCombat_f(void) {
    char value[32];
    int mode = -1;
    trap->Argv(1, value, sizeof(value));
    if (!Q_stricmp(value, "original") || !Q_stricmp(value, "jka") || !Q_stricmp(value, "0")) mode = 0;
    if (!Q_stricmp(value, "trials") || !Q_stricmp(value, "sabertrials") || !Q_stricmp(value, "1")) mode = 1;
    if (trap->Argc() != 2 || mode == -1) {
        trap->Print("Usage: st_combat <original|trials> (queues next round; st_applyrules restarts now)\n");
        return;
    }
    pendingMode = mode;
    trap->SendServerCommand(-1, va("print \"%s queued for the next round.\n\"", ST_CombatName(mode)));
    trap->Print("Combat preset queued: %s\n", ST_CombatName(mode));
}

void Svcmd_STCombatOption_f(void) {
    char option[32], value[16];
    int i, enabled = -1;
    trap->Argv(1, option, sizeof(option));
    trap->Argv(2, value, sizeof(value));
    if (!Q_stricmp(value, "on") || !Q_stricmp(value, "1")) enabled = 1;
    if (!Q_stricmp(value, "off") || !Q_stricmp(value, "0")) enabled = 0;
    if (trap->Argc() == 3 && enabled != -1) {
        if (!Q_stricmp(option, "master")) {
            ST_QueueMasterMode(enabled);
            return;
        }
        for (i = 0; i < ST_COMBAT_OPTION_COUNT; ++i) {
            if (!Q_stricmp(option, optionNames[i])) {
                pendingOptions[i] = enabled;
                trap->Print("Combat option queued: %s %s. Effective only in Saber Trials Combat.\n", optionNames[i], enabled ? "on" : "off");
                return;
            }
        }
    }
    trap->Print("Usage: st_combatoption <defense|recovery|shields|nofall|speed|forceregen|master> <on|off>\n");
}

void ST_CombatStatus(void) {
    int i;
    trap->Print("Combat preset: %s\n", ST_CombatName(st_combatMode.integer));
    trap->Print("Queued combat preset: %s\n", pendingMode == -1 ? "none" : ST_CombatName(pendingMode));
    for (i = 0; i < ST_COMBAT_OPTION_COUNT; ++i) {
        trap->Print("  %s: %s (saved %s; queued %s)\n", optionNames[i],
            ST_CombatOption((stCombatOption_t)i) ? "on" : "off",
            optionCvars[i]->integer == 1 ? "on" : "off",
            pendingOptions[i] == -1 ? "none" : pendingOptions[i] ? "on" : "off");
    }
    trap->Print("  master: %s (saved %s)\n", ST_MasterEnabled() ? "on" : "off",
        st_masterModeActive.integer == ST_MASTER_ON ? "on" : "off");
    trap->Print("Force regeneration interval: %ims\n", g_forceRegenTime.integer);
}
