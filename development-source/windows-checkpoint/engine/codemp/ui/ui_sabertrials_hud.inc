/* Native HUD menu actions. GPL-2.0-or-later. Included after input helpers. */
static qboolean ST_UIHudScript(const char *name) {
    if (!Q_stricmp(name, "stHudInit") || !Q_stricmp(name, "stHudReset")) {
        trap->Cvar_Register(NULL, "st_hudStyle", "1", CVAR_ARCHIVE);
        trap->Cvar_Register(NULL, "st_hudScale", "100", CVAR_ARCHIVE);
        trap->Cvar_Register(NULL, "st_hudOpacity", "55", CVAR_ARCHIVE);
        trap->Cvar_Register(NULL, "st_hudPulse", "1", CVAR_ARCHIVE);
        trap->Cvar_Register(NULL, "cg_drawScores", "1", CVAR_ARCHIVE);
        if (!Q_stricmp(name, "stHudReset")) {
            trap->Cvar_Set("st_hudStyle", "1");
            trap->Cvar_Set("st_hudScale", "100");
            trap->Cvar_Set("st_hudOpacity", "55");
            trap->Cvar_Set("st_hudPulse", "1");
            trap->Cvar_Set("cg_drawScores", "1");
            trap->Cvar_Set("cg_drawStatus", "1");
        }
        ST_UIInputValue("st_uiHudScale", "st_hudScale");
        ST_UIInputValue("st_uiHudOpacity", "st_hudOpacity");
        trap->Cvar_Set("st_uiHudStatus", "Drag or type a value, then Apply. Size: 75-125%.");
        return qtrue;
    }
    if (!Q_stricmp(name, "stHudApply")) {
        char size[64], opacity[64], *sizeEnd, *opacityEnd;
        double s, o;
        trap->Cvar_VariableStringBuffer("st_uiHudScale", size, sizeof(size));
        trap->Cvar_VariableStringBuffer("st_uiHudOpacity", opacity, sizeof(opacity));
        s = strtod(size, &sizeEnd); o = strtod(opacity, &opacityEnd);
        if (sizeEnd == size || *sizeEnd || opacityEnd == opacity || *opacityEnd ||
            s != s || o != o || s < 75 || s > 125 || o < 0 || o > 100) {
            trap->Cvar_Set("st_uiHudStatus", "Enter size 75-125 and panel opacity 0-100.");
        } else {
            trap->Cvar_Set("st_hudScale", va("%.6g", s));
            trap->Cvar_Set("st_hudOpacity", va("%.6g", o));
            ST_UIInputValue("st_uiHudScale", "st_hudScale");
            ST_UIInputValue("st_uiHudOpacity", "st_hudOpacity");
            trap->Cvar_Set("st_uiHudStatus", "HUD appearance applied.");
        }
        return qtrue;
    }
    return qfalse;
}
