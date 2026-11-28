// UI transitions are deferred until the next refresh. An action can still
// hold pointers to the current item and script until Menu_HandleKey returns.
static const char *themeDestination;
static bool themeInterface;

static bool ThemeRoot(const char *name) {
    return !Q_stricmp(name,"main") || !Q_stricmp(name,"mainMenu") || !Q_stricmp(name,"ingame");
}

static void ThemeFrame() {
    bool classic = trap->Cvar_VariableValue("st_menuTheme") == 0;
    if (classic == themeClassic && !themeDestination) return;
    menuDef_t *focused = Menu_GetFocused();
    char destination[MAX_QPATH] = {};
    if (themeDestination) Q_strncpyz(destination,themeDestination,sizeof(destination));
    else if (focused) Q_strncpyz(destination,focused->window.name,sizeof(destination));
    if (themeClassic != classic) themeExtensions = false;
    themeClassic = classic;
    themeDestination = NULL;
    scui.active = ssui.active = spui.active = 0;
    UI_LoadPage(destination);
    if (*destination && !Menu_GetFocused())
        Menus_ActivateByName(uiInfo.inGameLoad ? "ingame" : "main");
    if (themeInterface && !ST_ClassicLayout() && SSUI_IsMenu()) {
        SSUI_Start();
        ssui.tab = 2;
        ssui.focus = 2002;
    }
    themeInterface = false;
}

static bool ThemeAction(const char *name) {
    if (!Q_stricmp(name,"stThemeModern")) {
        // Both selectors commit through the same engine-owned settings service.
        SSUI_Call(100);
        for (int i=0; i<SS_COUNT; ++i) {
            if (Q_stricmp(ssSettings[i].name,"st_menuTheme")) continue;
            auto result = SSUI_Call(102,i,0,0,"st_menuTheme","1");
            if (result.status >= 0) SSUI_Call(103,uiInfo.inGameLoad);
            break;
        }
        themeDestination = uiInfo.inGameLoad ? "ingame_setup" : "setup_menu";
        themeInterface = true;
        return true;
    }
    if (!Q_stricmp(name,"stHostPresetChanged")) {
        trap->Cvar_Set("ui_stHostPresetSet","1");
        return true;
    }
    if (!Q_stricmp(name,"stThemeExtensions") || !Q_stricmp(name,"stThemeInterface")) {
        auto menu = Menu_GetFocused();
        if (menu && themeClassic) {
            const bool ingame = uiInfo.inGameLoad || !Q_stricmpn(menu->window.name,"ingame",6);
            themeExtensions = true;
            themeInterface = !Q_stricmp(name,"stThemeInterface");
            themeDestination = themeInterface ? (ingame ? "ingame_setup" : "setup_menu")
                                             : (ingame ? "ingame" : "main");
        }
        return true;
    }
    return false;
}

static bool ThemeReturnVisible() {
    auto menu = Menu_GetFocused();
    return themeClassic && themeExtensions && menu && ThemeRoot(menu->window.name);
}

// The retail multi-choice control uses the pointer to test activation even
// when it has keyboard focus. Move the virtual cursor to the focused item.
static int ThemeNativeKey(int key, bool classic) {
    auto menu = Menu_GetFocused();
    if (!menu || Display_KeyBindPending()) return key;
    if (key != A_JOY0 && key != A_JOY13 && key != A_JOY14 && key != A_ENTER) return key;
    for (int i=0; i<menu->itemCount; ++i) {
        auto item = menu->items[i];
        if (!(item->window.flags & WINDOW_HASFOCUS)) continue;
        if (!classic && (!item->window.name || Q_stricmp(item->window.name,"stHostPreset"))) return key;
        if (item->type != ITEM_TYPE_MULTI) return key;
        const auto rect = item->window.rect;
        uiInfo.uiDC.cursorx = rect.x + rect.w/2;
        uiInfo.uiDC.cursory = rect.y + rect.h/2;
        return key == A_JOY13 ? A_MOUSE2 : A_MOUSE1;
    }
    return key;
}

static bool ThemeReturnKey(int key, qboolean down) {
    if (!ThemeReturnVisible()) return false;
    bool click = key == A_MOUSE1 && uiInfo.uiDC.cursorx >= 228 && uiInfo.uiDC.cursorx <= 412
                               && uiInfo.uiDC.cursory >= 450 && uiInfo.uiDC.cursory <= 479;
    if (!click && key != A_ESCAPE && key != A_JOY1) return false;
    if (down) {
        themeDestination = !Q_stricmp(Menu_GetFocused()->window.name,"ingame") ? "ingame" : "main";
        themeExtensions = false;
    }
    return true;
}
