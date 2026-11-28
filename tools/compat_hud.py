"""Build the existing combat HUD against the stock fields available to the engine."""


def between(text, start, end):
    return text[text.index(start):text.index(end, text.index(start))]


def generate(root, engine):
    source=(root/"dist/pug-01/frontend/codemp/cgame/cg_sabertrials_hud.inc").read_text()
    # Use the release drawings, glyph atlas, meter sizes and style colors.
    # Only the game module has DLC inventory, extra teams and the Force sound timer.
    for start,end,replacement in [
        ("int ST_HudSelectLift(", "static float ST_HudAspect", ""),
        ("    const char *label;", "    switch (style)", "    *color=st_hudCyan;\n"),
        ("    static char dlcName", "    switch (weapon)", ""),
        ("        const clientInfo_t *client", "    }\n    ST_HudPanel(x", """        const int style=ps->fd.saberDrawAnimLevel;
        icon=style==SS_DUAL?st_hudMedia.dual:style==SS_STAFF?st_hudMedia.staff:st_hudMedia.saber;
"""),
        ("    // Preserve the audible feedback", "    if (saber) ST_HudBar", ""),
        ("    if (cgs.tffaCount", "    // Siege has its own", ""),
    ]:
        source=source.replace(between(source,start,end),replacement,1)
    bindings={
        "static float ST_DrawHudScore(float top)":"static float ST_DrawHudScore(float top, float right)",
        "float s = ST_HudScale(), right = 640 / ST_HudAspect() - 4;":"float s = ST_HudScale();",
        "trap->R_RegisterShaderNoMip":"art","trap->R_SetColor":"re->SetColor",
        "trap->R_DrawStretchPic":"re->DrawStretchPic","CG_DrawPic":"picture","CG_FillRect":"rectangle",
        "st_hudScale.value":"scale->value","st_hudOpacity.value":"panelOpacity->value",
        "qboolean saber =":"bool saber =",
        "st_hudPulse.integer":"pulse->integer",
        "cgs.screenXScale > 0 ? cgs.screenYScale / cgs.screenXScale : 1":"(cls.glconfig.vidHeight/480.f)/(cls.glconfig.vidWidth/640.f)",
        "cg.time":"cl.serverTime","&cg.snap->ps":"&cl.snap.ps",
        "cg.predictedPlayerState.fd.saberDrawAnimLevel":"ps->fd.saberDrawAnimLevel",
        "ps->stHybrid.style":"0","weaponData[":"hudWeapons[",
        "ammo < 0 || ((ps->stats[ST_DLC_ALLOWED_STAT]&ST_DLC_INFINITE) && ST_DLCGun(weapon))":"ammo < 0",
        "saber && cg.forceHUDTotalFlashTime > cl.serverTime ? st_hudRed : st_hudWhite":"st_hudWhite",
        "cg_drawScores.integer":"showScore->integer","cg.showScores":"scoreHeld",
        "cgs.gametype":"gameType","cgs.fraglimit":"fragLimit","cgs.scores1":"redScore","cgs.scores2":"blueScore",
    }
    for before,after in bindings.items():
        if before not in source:raise ValueError("Combat HUD source changed: "+before)
        source=source.replace(before,after)
    # Ammo types and energy use come from the same stock weapon definitions as cgame.
    data=(engine/"codemp/game/bg_weapons.c").read_text()
    table=between(data,"weaponData_t weaponData[","};")+"};\n"
    out=engine/"codemp/client/foreign_hud_layout.inc"
    out.write_text(table.replace("weaponData_t weaponData[","static const weaponData_t hudWeapons[",1)+source)
