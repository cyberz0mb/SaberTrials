/* Inserted in an isolated QA build only. Never shipped. */
extern int bg_parryDebounce[NUM_FORCE_POWER_LEVELS];
extern void ClientTimerActions(gentity_t *ent, int msec);
extern float ST_QAMasterDamage(void);

static void Svcmd_STCombatQA_f(void) {
    static gentity_t ent;
    static gclient_t client;
    usercmd_t cmd;
    vec3_t point = {40, 90, 0};
    char action[32];
    int i, regen, decay, passive, active, window, cooldownBypass;
    trap->Argv(1, action, sizeof(action));
    if (!Q_stricmp(action, "spawn")) {
        char number[16];
        trap->Argv(2, number, sizeof(number));
        i = atoi(number);
        if (i < 0 || i >= level.maxclients || !g_entities[i].client ||
            level.clients[i].pers.connected != CON_CONNECTED) return;
        /* Reinitialize from a no-Speed loadout, exactly as a round restart does. */
        { char info[MAX_INFO_STRING];
          trap->GetUserinfo(i, info, sizeof(info));
          Info_SetValueForKey(info, "forcepowers", "7-1-000000000000000333");
          trap->SetUserinfo(i, info);
        }
        ClientBegin(i, qfalse);
        trap->Print("QA spawn armor=%i speed=%i health=%i\n",
            level.clients[i].ps.stats[STAT_ARMOR], level.clients[i].ps.fd.forcePowerLevel[FP_SPEED],
            level.clients[i].ps.stats[STAT_HEALTH]);
        return;
    }
    memset(&ent, 0, sizeof(ent)); memset(&client, 0, sizeof(client)); memset(&cmd, 0, sizeof(cmd));
    ent.client = &client; ent.health = 100;
    client.ps.stats[STAT_HEALTH] = client.ps.stats[STAT_MAX_HEALTH] = 100;
    client.ps.stats[STAT_ARMOR] = 20;
    client.sess.sessionTeam = TEAM_FREE;
    ClientTimerActions(&ent, 1000); regen = client.ps.stats[STAT_ARMOR];
    client.ps.stats[STAT_ARMOR] = 60;
    ClientTimerActions(&ent, 1000); decay = client.ps.stats[STAT_ARMOR];
    client.ps.weapon = WP_SABER; client.ps.saberMove = LS_READY;
    client.ps.saberEntityNum = 1; client.ps.fd.forcePowerLevel[FP_SABER_DEFENSE] = FORCE_LEVEL_3;
    passive = WP_SaberCanBlock(&ent, point, 0, MOD_SABER, qfalse, 1);
    client.pers.cmd.buttons = BUTTON_WALKING;
    active = WP_SaberCanBlock(&ent, point, 0, MOD_SABER, qfalse, 1);
    cmd.buttons = BUTTON_WALKING;
    ST_UpdateParryInput(&ent, &cmd); window = client.stParryWindowEnd > level.time;
    client.ps.saberHolstered = 2;
    ST_UpdateParryInput(&ent, &cmd);
    client.ps.saberHolstered = 0;
    ST_UpdateParryInput(&ent, &cmd);
    cooldownBypass = client.stParryWindowEnd > level.time;
    /* A stale counter must never make Original combat attack-ready. */
    client.stCounterWindowEnd = level.time + 1000; client.ps.weaponTime = 500;
    cmd.buttons = BUTTON_ATTACK; ST_UpdateParryInput(&ent, &cmd);
    trap->Print("QA mode=%i recovery=%i,%i,%i,%i regen=%i decay=%i passive=%i active=%i window=%i counterWeaponTime=%i masterDamage=%.0f dmflags=%i forceRegen=%i cooldownBypass=%i\n",
        ST_CombatEnabled(), bg_parryDebounce[0], bg_parryDebounce[1], bg_parryDebounce[2], bg_parryDebounce[3],
        regen, decay, passive, active, window, client.ps.weaponTime, ST_QAMasterDamage(), dmflags.integer, g_forceRegenTime.integer, cooldownBypass);
}
