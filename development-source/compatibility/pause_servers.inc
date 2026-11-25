// Keep browser filters, favorites, password handling and server selection in
// the same menu and LAN cache used by the main frontend.
void UI_ParseMenu(const char *menuFile);

static struct {
    menuDef_t *menu;
    const char *escape;
    const char *back;
    bool quitVisible;
} pauseBrowser;

static void ST_ReleasePauseBrowser() {
    if (!pauseBrowser.menu) return;
    auto *menu = pauseBrowser.menu;
    menu->onESC = pauseBrowser.escape;
    if (auto *back = Menu_FindItemByName(menu, "back")) back->action = pauseBrowser.back;
    if (pauseBrowser.quitVisible) {
        if (auto *quit = Menu_FindItemByName(menu, "exitgamebutton")) quit->window.flags |= WINDOW_VISIBLE;
    }
    pauseBrowser = {};
}

static void ST_OpenPauseBrowser() {
    const struct { const char *menu, *file; } pages[] = {
        {"joinserver", "joinserver"}, {"password_request", "password_request"},
        {"password_popmenu", "password"}, {"serverinfo_popmenu", "serverinfo"},
        {"createfavorite_popmenu", "createfavorite"}, {"findplayer_popmenu", "findplayer"}
    };
    trap->PC_LoadGlobalDefines(ThemeAsset("ui/jamp/menudef.h"));
    for (const auto &page : pages) {
        if (!Menus_FindByName(page.menu))
            UI_ParseMenu(va("ui/jamp/%s.menu", page.file));
    }
    trap->PC_RemoveAllGlobalDefines();
    menuDef_t *menu = Menus_FindByName("joinserver");
    if (!menu) return;
    if (!pauseBrowser.menu) {
        pauseBrowser.menu = menu;
        pauseBrowser.escape = menu->onESC;
        menu->onESC = "uiScript stBackToPause ;";
        if (auto *back = Menu_FindItemByName(menu, "back")) {
            pauseBrowser.back = back->action;
            back->action = menu->onESC;
        }
        if (auto *quit = Menu_FindItemByName(menu, "exitgamebutton")) {
            pauseBrowser.quitVisible = (quit->window.flags & WINDOW_VISIBLE) != 0;
            quit->window.flags &= ~WINDOW_VISIBLE;
        }
    }
    Menus_CloseByName("ingame");
    Menus_ActivateByName("joinserver");
}

static void ST_BackToPause() {
    UI_StopServerRefresh();
    uiInfo.serverStatus.nextDisplayRefresh = 0;
    uiInfo.nextServerStatusRefresh = 0;
    uiInfo.nextFindPlayerRefresh = 0;
    ST_ReleasePauseBrowser();
    Menus_CloseByName("joinserver");
    Menus_ActivateByName("ingame");
}

static void ST_AddPauseBrowserButton() {
    auto *menu = Menus_FindByName("ingame");
    if (!menu || ST_ClassicLayout() || Menu_FindItemByName(menu, "find_server")) return;
    const auto *join = Menu_FindItemByName(menu, "join");
    const auto *icon = Menu_FindItemByName(menu, "join_icon");
    auto *exit = Menu_FindItemByName(menu, "exit");
    auto *resume = Menu_FindItemByName(menu, "resume");
    if (!join || !icon || !exit || !resume || menu->itemCount + 2 > MAX_MENUITEMS) return;
    auto *button = static_cast<itemDef_t *>(UI_Alloc(sizeof(itemDef_t)));
    auto *mark = static_cast<itemDef_t *>(UI_Alloc(sizeof(itemDef_t)));
    if (!button || !mark) return;
    *button = *join;
    *mark = *icon;
    button->window.name = "find_server";
    button->text = "Find a Server";
    button->window.rectClient.y = 315;
    button->onFocus = "show focus_glow ; setitemrect focus_glow 20 315 210 27 ;";
    button->action = "play sound/interface/button1.wav ; uiScript stBrowseFromPause ;";
    mark->window.name = "find_server_icon";
    mark->window.rectClient.y = 319.5f;
    exit->window.rectClient.y = 343;
    exit->onFocus = "show focus_glow ; setitemrect focus_glow 20 343 210 27 ;";
    if (auto *exitIcon = Menu_FindItemByName(menu, "exit_icon")) exitIcon->window.rectClient.y += 28;
    if (auto *exitLine = Menu_FindItemByName(menu, "exit_line")) exitLine->window.rectClient.y += 28;
    resume->window.rectClient.y = 371;
    resume->onFocus = "show focus_glow ; setitemrect focus_glow 20 371 210 24 ;";
    // Keep keyboard and controller focus in the visual row order.
    int pos = 0;
    while (menu->items[pos] != exit) ++pos;
    memmove(menu->items + pos + 2, menu->items + pos, (menu->itemCount - pos) * sizeof(menu->items[0]));
    menu->items[pos] = mark;
    menu->items[pos + 1] = button;
    menu->itemCount += 2;
    Menu_PostParse(menu);
}
