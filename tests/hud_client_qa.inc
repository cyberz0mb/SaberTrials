/* Isolated QA build only. Never installed. Read-only observation and fixtures. */
void ST_HudQA_f(void) {
    const char *op = CG_Argv(1);
    if (!Q_stricmp(op, "math")) {
        int failures = 0;
        qhandle_t icon; const float *color;
#define HUD_EXPECT(test) do { if (!(test)) failures++; } while (0)
        HUD_EXPECT(ST_HudRatio(25, 100) == .25f);
        HUD_EXPECT(ST_HudRatio(-30, 100) == 0);
        HUD_EXPECT(ST_HudRatio(200, 100) == 1);
        HUD_EXPECT(ST_HudRatio(0, 0) == 0);
        HUD_EXPECT(ST_HudRatio(50, 200) == .25f);
        HUD_EXPECT(ST_HudClamp(-100, 75, 125) == 75);
        HUD_EXPECT(ST_HudClamp(10000, 75, 125) == 125);
        HUD_EXPECT(!Q_stricmp(ST_HudStyle(SS_STAFF, &icon, &color), "STAFF") && icon == st_hudMedia.staff);
        HUD_EXPECT(!Q_stricmp(ST_HudStyle(SS_DUAL, &icon, &color), "DUAL") && icon == st_hudMedia.dual);
        HUD_EXPECT(!Q_stricmp(ST_HudWeaponName(WP_BLASTER), "BLASTER"));
        HUD_EXPECT(!Q_stricmp(ST_HudWeaponName(-1), "UNARMED"));
        Com_Printf("HUD_MATH cases=11 failures=%d\n", failures);
#undef HUD_EXPECT
        return;
    }
    if (cg.snap) {
        const playerState_t *ps = &cg.snap->ps;
        int weapon = ps->weapon, ammo = -1;
        if (weapon > WP_NONE && weapon < WP_NUM_WEAPONS) ammo = ps->ammo[weaponData[weapon].ammoIndex];
        Com_Printf("HUD_QA style=%d scale=%.3f opacity=%.3f health=%d armor=%d max=%d force=%d weapon=%d ammo=%d stance=%d score=%d team=%d follow=%d\n",
            st_hudStyle.integer, ST_HudScale(), st_hudOpacity.value, ps->stats[STAT_HEALTH], ps->stats[STAT_ARMOR],
            ps->stats[STAT_MAX_HEALTH], ps->fd.forcePower, weapon, ammo, cg.predictedPlayerState.fd.saberDrawAnimLevel,
            ps->persistant[PERS_SCORE], ps->persistant[PERS_TEAM], (ps->pm_flags & PMF_FOLLOW) != 0);
        Com_Printf("HUD_LAYOUT aspect=%.4f scoreBottom=%.1f media=%d/%d/%d gt=%d red=%d blue=%d\n",
            ST_HudAspect(), ST_DrawHudScore(0), st_hudMedia.frame[ST_HUD_HEALTH], st_hudMedia.font, st_hudMedia.health,
            cgs.gametype, cgs.scores1, cgs.scores2);
    }
}
