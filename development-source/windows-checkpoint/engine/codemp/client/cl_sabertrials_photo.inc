// Local Photo Mode pause ownership. GPL-2.0-or-later.
// Included in cl_main.cpp; eligibility is checked against real server clients.
extern qboolean SV_STPhotoSolo(void);
static qboolean stPhotoOwnsPause = qfalse;
static int stPhotoServerId;

static void ST_PhotoEngineReset(void) {
    Cvar_Set("st_photoMode", "0");
    Cvar_Set("st_photoFreeze", "0");
    Cvar_Set("st_photoSolo", "0");
    Cvar_Set("st_photoFrozen", "0");
    if (stPhotoOwnsPause) Cvar_Set("cl_paused", "0");
    stPhotoOwnsPause = qfalse;
}

static void ST_PhotoEngineInit(void) {
    Cvar_Get("st_photoEngine", "1", CVAR_ROM);
    Cvar_Set("st_photoEngine", "1");
    Cvar_Get("st_photoMode", "0", 0);
    Cvar_Get("st_photoFreeze", "0", 0);
    Cvar_Get("st_photoSolo", "0", CVAR_ROM);
    Cvar_Get("st_photoFrozen", "0", CVAR_ROM);
    ST_PhotoEngineReset();
}

static void ST_PhotoEngineFrame(void) {
    if (cls.state != CA_ACTIVE || !cls.cgameStarted) {
        ST_PhotoEngineReset();
        return;
    }
    const qboolean solo = (qboolean)(!clc.demoplaying && com_sv_running->integer &&
        clc.serverAddress.type == NA_LOOPBACK && SV_STPhotoSolo());
    const int serverId = Cvar_VariableIntegerValue("sv_serverid");
    // A paused server cannot send the map_restart message to cgame yet.
    // Release our pause here so that the new world can deliver its snapshots.
    if (stPhotoOwnsPause && serverId != stPhotoServerId) ST_PhotoEngineReset();
    stPhotoServerId = serverId;
    Cvar_Set("st_photoSolo", solo ? "1" : "0");
    if (!solo) Cvar_Set("st_photoFreeze", "0");
    const qboolean freeze = (qboolean)(solo && Cvar_VariableIntegerValue("st_photoMode") &&
        Cvar_VariableIntegerValue("st_photoFreeze"));
    if (freeze) {
        Cvar_Set("cl_paused", "1");
        stPhotoOwnsPause = qtrue;
    } else if (stPhotoOwnsPause) {
        Cvar_Set("cl_paused", "0");
        stPhotoOwnsPause = qfalse;
    }
    Cvar_Set("st_photoFrozen", freeze ? "1" : "0");
}
