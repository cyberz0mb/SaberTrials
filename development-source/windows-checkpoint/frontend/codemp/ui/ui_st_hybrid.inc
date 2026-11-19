/* Saber Trials single-saber combat selection. GPL-2.0-or-later.
 * The player chooses three styles and their cycle order; the server determines
 * eligibility and waits for a safe moment before changing the active style. */
static const char *st_hybridReturn="saberMenu", *st_hybridPage="st_hybrid_main";
static qboolean st_hybridPendingReturn=qfalse;

static const char *ST_UIHybridStyleName(int style) {
    switch(style) {
    case 1:return "Blue";case 2:return "Yellow";case 3:return "Red";
    case 4:return "Green";case 5:return "Purple";case 6:return "Orange";
    default:return "Choose a style";
    }
}
static const char *ST_UIHybridStyleNote(int style) {
    switch(style) {
    case 1:return "Original Blue style.";
    case 2:return "Original Yellow style.";
    case 3:return "Original Red style.";
    case 4:return "Quick combinations; more weight than Blue.";
    case 5:return "Two precise swings; vulnerable recovery.";
    case 6:return "Weightier attacks; less wind-up than Red.";
    default:return "Select one of the six styles.";
    }
}
static qboolean ST_UIHybridScript(const char *name) {
    if(!Q_stricmp(name,"stHybridOpenMain") || !Q_stricmp(name,"stHybridOpenGame")) {
        st_hybridReturn=!Q_stricmp(name,"stHybridOpenGame")?"ingame_saber":"saberMenu";
        st_hybridPage=!Q_stricmp(name,"stHybridOpenGame")?"st_hybrid_game":"st_hybrid_main";
        st_hybridPendingReturn=qfalse;
        ST_UIHybridGetCvar();
        trap->Cvar_Set("ui_hybridNotice","");
        ST_UIStanceCapability();
        Menus_ActivateByName(st_hybridPage);
        return qtrue;
    }
    if(!Q_stricmp(name,"stHybridReset")) {
        const int styles[3]={1,2,3};
        ST_UIHybridSetDraft(styles);
        trap->Cvar_Set("ui_hybridNotice","Blue, Yellow and Red selected. Apply to save.");
        return qtrue;
    }
    if(!Q_stricmp(name,"stHybridCancel")) {
        ST_UIHybridGetCvar();
        st_hybridPendingReturn=qtrue;
        return qtrue;
    }
    if(!Q_stricmp(name,"stHybridApply")) {
        int styles[3],valid=ST_UIHybridReadDraft(styles);
        if(valid<1) {
            trap->Cvar_Set("ui_hybridNotice",valid<0?
                "Choose a style for each of the three slots.":
                "Choose three different styles. Each style can fill only one slot.");
            return qtrue;
        }
        ST_UIStanceCapability();
        if(!st_hybridLibrary && (styles[0]>=4 || styles[1]>=4 || styles[2]>=4)) {
            trap->Cvar_Set("ui_hybridNotice","Matching style assets are missing. Your choices were not saved.");
            return qtrue;
        }
        /* One userinfo update carries the whole validated selection. */
        trap->Cvar_Set("saberStyleLoadout",va("%d %d %d",styles[0],styles[1],styles[2]));
        trap->Cvar_Set("st_uiPresentationNotice",
            "Three styles saved. Use your normal style-switch control to cycle them.");
        st_hybridPendingReturn=qtrue;
        return qtrue;
    }
    return qfalse;
}

static void ST_UIHybridRefresh(menuDef_t *menu) {
    int styles[3],valid;
    if(st_hybridPendingReturn && !trap->Key_IsDown(A_MOUSE1) && !trap->Key_IsDown(A_MOUSE2)) {
        st_hybridPendingReturn=qfalse;
        Menus_CloseByName(st_hybridPage);
        /* Reopening a Saber page normally reloads equipment. Preserve its drafts
         * while returning from this child page, including unsaved hilts/hand. */
        st_hybridKeepSaberDraft=qtrue;
        Menus_ActivateByName(st_hybridReturn);
        st_hybridKeepSaberDraft=qfalse;
        return;
    }
    if(!menu || Q_stricmp(menu->window.name,st_hybridPage))return;
    valid=ST_UIHybridReadDraft(styles);
    ST_UIStanceLabel(menu,"st_hybrid_slot1_note",ST_UIHybridStyleNote(styles[0]));
    ST_UIStanceLabel(menu,"st_hybrid_slot2_note",ST_UIHybridStyleNote(styles[1]));
    ST_UIStanceLabel(menu,"st_hybrid_slot3_note",ST_UIHybridStyleNote(styles[2]));
    ST_UIStanceLabel(menu,"st_hybrid_cycle",valid>0?
        va("Cycle: %s > %s > %s > repeat",ST_UIHybridStyleName(styles[0]),
            ST_UIHybridStyleName(styles[1]),ST_UIHybridStyleName(styles[2])):
        "Choose three different styles to complete your cycle.");
    ST_UIStanceLabel(menu,"st_hybrid_assets",st_hybridLibrary?
        "Supporting servers use this selection. Saber Offense requirements still apply.":
        "Matching style assets are missing. Blue, Yellow and Red remain available.");
}
