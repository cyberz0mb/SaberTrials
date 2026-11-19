/* Saber Trials combat HUD. GPL-2.0-or-later. Included by cg_draw.c.
 * Presentation only: reads received player state, never changes gameplay.
 * Dimensions use a height-based canvas to keep icons and lettering undistorted.
 */
typedef enum {
    ST_HUD_HEALTH, ST_HUD_ARMOR, ST_HUD_WEAPON, ST_HUD_SCORE, ST_HUD_TEAM, ST_HUD_PANEL_COUNT
} stHudPanel_t;

typedef struct {
    qhandle_t frame[ST_HUD_PANEL_COUNT], fill[ST_HUD_PANEL_COUNT], font;
    qhandle_t health, armor, saber, dual, staff, ammo;
    qhandle_t track, healthMeter, armorMeter, reticle;
    qhandle_t chatFrame, chatFill, chatHeader;
} stHudMedia_t;
static stHudMedia_t st_hudMedia;
static const vec4_t st_hudCyan = { .40f, .81f, 1, 1 };
static const vec4_t st_hudWhite = { .93f, .98f, 1, 1 };
static const vec4_t st_hudMuted = { .59f, .75f, .83f, 1 };
static const vec4_t st_hudRed = { 1, .25f, .36f, 1 };
static const vec4_t st_hudGold = { 1, .76f, .27f, 1 };

void ST_HudRegister(void) {
    const char *const panels[] = {"health", "armor", "weapon", "score", "team"};
    for (int i = 0; i < ST_HUD_PANEL_COUNT; ++i) {
        st_hudMedia.frame[i] = trap->R_RegisterShaderNoMip(va("gfx/sabertrials/hud_theme/%s_frame", panels[i]));
        st_hudMedia.fill[i] = trap->R_RegisterShaderNoMip(va("gfx/sabertrials/hud_theme/%s_frame_fill", panels[i]));
    }
#define ST_HUD_SHADER(field, name) st_hudMedia.field = trap->R_RegisterShaderNoMip("gfx/sabertrials/hud_theme/" name)
    ST_HUD_SHADER(font, "letters");
    ST_HUD_SHADER(health, "health_mark");
    ST_HUD_SHADER(armor, "armor_mark");
    ST_HUD_SHADER(saber, "saber_mark");
    ST_HUD_SHADER(dual, "dual_mark");
    ST_HUD_SHADER(staff, "staff_mark");
    ST_HUD_SHADER(ammo, "ammo_mark");
    ST_HUD_SHADER(track, "meter_track");
    ST_HUD_SHADER(healthMeter, "meter_health");
    ST_HUD_SHADER(armorMeter, "meter_armor");
    ST_HUD_SHADER(reticle, "reticle");
    ST_HUD_SHADER(chatFrame, "chat_frame");
    ST_HUD_SHADER(chatFill, "chat_frame_fill");
    ST_HUD_SHADER(chatHeader, "chat_header");
#undef ST_HUD_SHADER
}

static float ST_HudClamp(float value, float lo, float hi) {
    if (value != value) return lo;
    return value < lo ? lo : value > hi ? hi : value;
}
static float ST_HudScale(void) { return ST_HudClamp(st_hudScale.value, 75, 125) * .01f; }
int ST_HudSelectLift(void) {
    return st_hudStyle.integer == 1 && cg_drawStatus.integer ? (int)(12 + 55 * ST_HudScale()) : 0;
}
static float ST_HudAspect(void) { return cgs.screenXScale > 0 ? cgs.screenYScale / cgs.screenXScale : 1; }
static float ST_HudRatio(int value, int maximum) {
    return ST_HudClamp(value / (float)Q_max(1, maximum), 0, 1);
}

// x and width here are in a 480-high virtual space. Only this layer converts
// them to OpenJK's stretched 640x480 canvas; every glyph uses the same transform.
static void ST_HudPic(float x, float y, float w, float h, qhandle_t shader, const vec4_t color) {
    trap->R_SetColor(color);
    CG_DrawPic(x * ST_HudAspect(), y, w * ST_HudAspect(), h, shader);
    trap->R_SetColor(NULL);
}
static void ST_HudRect(float x, float y, float w, float h, const vec4_t color) {
    CG_FillRect(x * ST_HudAspect(), y, w * ST_HudAspect(), h, color);
}
static float ST_HudTextWidth(const char *text, float h) { return strlen(text) * h * .66f; }
static void ST_HudText(float x, float y, float h, const char *text, const vec4_t color) {
    const char *alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-/:+?.core";
    float aspect = ST_HudAspect();
    trap->R_SetColor(color);
    for (; *text; text++, x += h * .66f) {
        const char *glyph = strchr(alphabet, *text);
        if (glyph) {
            int n = (int)(glyph - alphabet);
            // Atlas cells are 32x64. Crop their padding to a 24x44 glyph box.
            float u = ((n % 16) * 32 + 4) / 512.0f;
            float v = ((n / 16) * 64 + 10) / 256.0f;
            // OpenJK's cgame import already scales these 640x480 coordinates.
            trap->R_DrawStretchPic(x * aspect, y, h * .65f * aspect, h,
                u, v, u + 24 / 512.0f, v + 44 / 256.0f, st_hudMedia.font);
        }
    }
    trap->R_SetColor(NULL);
}
static void ST_HudFitText(float x, float y, float h, float width, const char *text, const vec4_t color) {
    float length = ST_HudTextWidth(text, h);
    if (length > width) h *= width / length;
    ST_HudText(x, y, h, text, color);
}
static void ST_HudCenteredText(float center, float y, float h, float width, const char *text, const vec4_t color) {
    float length = ST_HudTextWidth(text, h);
    if (length > width) h *= width / length;
    ST_HudText(center - ST_HudTextWidth(text, h) * .5f, y, h, text, color);
}
static void ST_HudPanel(float x, float y, float w, float h, stHudPanel_t panel) {
    vec4_t opacity = {1, 1, 1, ST_HudClamp(st_hudOpacity.value, 0, 100) * .01f};
    ST_HudPic(x, y, w, h, st_hudMedia.fill[panel], opacity);
    ST_HudPic(x, y, w, h, st_hudMedia.frame[panel], colorWhite);
}
static void ST_HudBar(float x, float y, float w, float h, float ratio, const vec4_t color) {
    vec4_t track = { .30f, .55f, .67f, .18f }, glow, core;
    memcpy(glow, color, sizeof(vec4_t)); glow[3] *= .18f;
    memcpy(core, color, sizeof(vec4_t)); core[0] = (core[0] + 1) * .5f; core[1] = (core[1] + 1) * .5f;
    ST_HudRect(x, y, w, h, track);
    if (ratio <= 0) return;
    ST_HudRect(x, y - h * .65f, w * ratio, h * 2.3f, glow);
    ST_HudRect(x, y, w * ratio, h, color);
    ST_HudRect(x, y + h * .3f, w * ratio, h * .3f, core);
}

static const char *ST_HudStyle(int style, qhandle_t *icon, const float **color) {
    *icon = st_hudMedia.saber; *color = st_hudCyan;
    switch (style) {
    case SS_MEDIUM: *color = st_hudGold; return "MEDIUM";
    case SS_STRONG: *color = st_hudRed; return "STRONG";
    case SS_DESANN: *color = st_hudRed; return "DESANN";
    case SS_TAVION: return "TAVION";
    case SS_DUAL: *icon = st_hudMedia.dual; *color = st_hudGold; return "DUAL";
    case SS_STAFF: *icon = st_hudMedia.staff; *color = st_hudGold; return "STAFF";
    default: return "FAST";
    }
}
static const char *ST_HudWeaponName(int weapon) {
    switch (weapon) {
    case WP_STUN_BATON: return "BATON";
    case WP_MELEE: return "MELEE";
    case WP_BRYAR_PISTOL: case WP_BRYAR_OLD: return "PISTOL";
    case WP_BLASTER: return "BLASTER";
    case WP_DISRUPTOR: return "DISRUPTOR";
    case WP_BOWCASTER: return "BOWCASTER";
    case WP_REPEATER: return "REPEATER";
    case WP_DEMP2: return "DEMP2";
    case WP_FLECHETTE: return "FLECHETTE";
    case WP_ROCKET_LAUNCHER: return "ROCKET";
    case WP_THERMAL: return "THERMAL";
    case WP_TRIP_MINE: return "TRIP MINE";
    case WP_DET_PACK: return "DET PACK";
    case WP_EMPLACED_GUN: case WP_TURRET: return "TURRET";
    default: return "UNARMED";
    }
}

static void ST_HudVital(float x, float y, float s, int value, int maximum, qboolean armor) {
    char number[24];
    vec4_t accent;
    memcpy(accent, armor ? st_hudCyan : st_hudRed, sizeof(vec4_t));
    if (!armor && value <= maximum * .25f && st_hudPulse.integer)
        accent[3] = .72f + .28f * (.5f + .5f * sinf(cg.time * .006f));
    ST_HudPanel(x, y, 186*s, 29*s, armor ? ST_HUD_ARMOR : ST_HUD_HEALTH);
    const float row = y + (armor ? 0 : 3)*s;
    ST_HudPic(x + 20*s, row + 4*s, 17*s, 17*s, armor ? st_hudMedia.armor : st_hudMedia.health, accent);
    Com_sprintf(number, sizeof(number), "%d", Q_max(0, value));
    ST_HudFitText(x + 43*s, row + 6*s, 13*s, 31*s, number, st_hudWhite);
    ST_HudPic(x + 77*s, row + 9*s, 85*s, 11*s, st_hudMedia.track, colorWhite);
    const float fraction = ST_HudRatio(value, maximum);
    const vec4_t meterColor = {1, 1, 1, accent[3]};
    if (fraction > 0)
        ST_HudPic(x + 77*s, row + 9*s, 85*s*fraction, 11*s,
            armor ? st_hudMedia.armorMeter : st_hudMedia.healthMeter, meterColor);
}

static void ST_DrawCombatHud(void) {
    const playerState_t *ps = &cg.snap->ps;
    float s = ST_HudScale(), right = 640 / ST_HudAspect() - 5, x, y;
    int maximum = Q_max(1, ps->stats[STAT_MAX_HEALTH]);
    int weapon = ps->weapon, force = Q_max(0, ps->fd.forcePower);
    qboolean saber = weapon == WP_SABER, hasForce = ps->fd.forcePowersKnown != 0;
    const float *styleColor = st_hudCyan;
    qhandle_t icon = st_hudMedia.ammo;
    const char *title;
    char number[24];
    if (ps->persistant[PERS_TEAM] == TEAM_SPECTATOR) return;
    ST_HudVital(5, 467 - 53*s, s, ps->stats[STAT_HEALTH], maximum, qfalse);
    ST_HudVital(5, 467 - 29*s, s, ps->stats[STAT_ARMOR], maximum, qtrue);
    x = right - 148*s; y = 467 - 55*s;
    title = saber ? ST_HudStyle(cg.predictedPlayerState.fd.saberDrawAnimLevel, &icon, &styleColor) : ST_HudWeaponName(weapon);
    ST_HudPanel(x, y, 148*s, 55*s, ST_HUD_WEAPON);
    ST_HudPic(x + 21*s, y + 9*s, 35*s, 35*s, icon, st_hudCyan);
    ST_HudCenteredText(x + 94*s, y + 11*s, 12*s, 62*s, title, st_hudWhite);
    ST_HudRect(x + 71*s, y + 24*s, 46*s, .65f*s, styleColor);
    if (saber) {
        Com_sprintf(number, sizeof(number), "%d", force);
    } else {
        int ammo = -1;
        if (weapon > WP_NONE && weapon < WP_NUM_WEAPONS &&
            weaponData[weapon].ammoIndex >= 0 && weaponData[weapon].ammoIndex < MAX_AMMO &&
            (weaponData[weapon].energyPerShot || weaponData[weapon].altEnergyPerShot))
            ammo = ps->ammo[weaponData[weapon].ammoIndex];
        ST_HudText(x + 68*s, y + 30*s, 6*s, "AMMO", st_hudMuted);
        if (ammo < 0) Q_strncpyz(number, "--", sizeof(number));
        else Com_sprintf(number, sizeof(number), "%d", ammo);
    }
    if (saber && !hasForce) Q_strncpyz(number, "--", sizeof(number));
    ST_HudCenteredText(x + (saber ? 94 : 104)*s, y + 26*s, 17*s, (saber ? 58 : 38)*s, number,
        saber && cg.forceHUDTotalFlashTime > cg.time ? st_hudRed : st_hudWhite);
    // Preserve the audible feedback for a rejected Force action.
    if (hasForce && cg.forceHUDTotalFlashTime > cg.time && cg.forceHUDNextFlashTime < cg.time) {
        cg.forceHUDNextFlashTime = cg.time + 400;
        trap->S_StartSound(NULL, 0, CHAN_LOCAL, cgs.media.noforceSound);
    }
    if (saber) ST_HudBar(x + 72*s, y + 44*s, 44*s, .8f*s,
        hasForce ? ST_HudRatio(force, ps->fd.forcePowerMax > 0 ? ps->fd.forcePowerMax : 100) : 0, st_hudCyan);
    else if (hasForce) {
        Com_sprintf(number, sizeof(number), "FORCE %d", force);
        ST_HudFitText(x + 68*s, y + 40*s, 6*s, 36*s, number, st_hudCyan);
    }
}

static float ST_DrawHudScore(float top) {
    const playerState_t *ps = &cg.snap->ps;
    float s = ST_HudScale(), right = 640 / ST_HudAspect() - 4;
    float x = right - 128*s, y = top + 8, w = 128*s, h = 29*s;
    char number[32];
    if (!cg_drawScores.integer || cg.showScores) return top;
    if (ps->persistant[PERS_TEAM] != TEAM_SPECTATOR) {
        if (cgs.gametype == GT_DUEL && cgs.fraglimit > 0)
            Com_sprintf(number, sizeof(number), "%d/%d", ps->persistant[PERS_SCORE], cgs.fraglimit);
        else Com_sprintf(number, sizeof(number), "%d", ps->persistant[PERS_SCORE]);
        ST_HudPanel(x, y, w, h, ST_HUD_SCORE);
        ST_HudCenteredText(x + 42*s, y + 10*s, 10*s, 38*s, "Score", st_hudWhite);
        ST_HudCenteredText(x + 88*s, y + 7*s, 15*s, 42*s, number, st_hudWhite);
        y += h + 4*s;
    }
    // Siege has its own objective/timer HUD; never mislabel its scores as TFFA.
    if (cgs.gametype >= GT_TEAM && cgs.gametype != GT_SIEGE) {
        ST_HudPanel(x, y, w, h, ST_HUD_TEAM);
        ST_HudText(x + 22*s, y + 7*s, 7*s, "RED", st_hudRed);
        ST_HudText(x + 72*s, y + 7*s, 7*s, "BLUE", st_hudCyan);
        if (cgs.scores1 == SCORE_NOT_PRESENT) Q_strncpyz(number, "--", sizeof(number));
        else Com_sprintf(number, sizeof(number), "%d", cgs.scores1);
        ST_HudFitText(x + 22*s, y + 14*s, 9*s, 43*s, number, st_hudWhite);
        if (cgs.scores2 == SCORE_NOT_PRESENT) Q_strncpyz(number, "--", sizeof(number));
        else Com_sprintf(number, sizeof(number), "%d", cgs.scores2);
        ST_HudFitText(x + 72*s, y + 14*s, 9*s, 34*s, number, st_hudWhite);
        y += h + 4*s;
    }
    return y > top + 8 ? y : top;
}
