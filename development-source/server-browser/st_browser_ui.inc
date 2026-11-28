/* Included by ui_main.c after the stock Join Server action. */
#define ST_BROWSER_STORAGE "ui/st-browser-regions.bin"
#define ST_BROWSER_MAX_REGION_BYTES (4 * 1024 * 1024)
#define ST_BROWSER_REUSE_MS 30000

static unsigned char *stRegionData;
static int stRegionRows;
static qboolean stRegionLoaded;
static int stLocalReadyAt;
static int stLatestWorldwide;
static int stQuickSearching;
static char stQuickAddress[MAX_ADDRESSLENGTH];
static qboolean stQuickPassword;
static stb_filter stQuickFilter;
static char stServerSearch[64];

static void UI_BrowserLoadRegions(void)
{
    fileHandle_t file = 0;
    int bytes = trap->FS_Open(ST_BROWSER_STORAGE, &file, FS_READ);
    stRegionLoaded = qtrue;
    if (!file)
        return;
    if (bytes > 0 && bytes <= ST_BROWSER_MAX_REGION_BYTES && !(bytes % 9)) {
        stRegionData = (unsigned char *)malloc(bytes);
        if (stRegionData && trap->FS_Read(stRegionData, bytes, file) == bytes) {
            stRegionRows = bytes / 9;
        }
    }
    trap->FS_Close(file);
}

static void UI_BrowserFreeRegions(void)
{
    free(stRegionData);
    stRegionData = NULL;
    stRegionRows = 0;
    stRegionLoaded = qfalse;
}

static int UI_BrowserRegion(const char *address)
{
    unsigned char ip[4];
    int i;
    for (i = 0; i < 4; ++i) {
        unsigned int part = 0, digits = 0;
        while (*address >= '0' && *address <= '9') {
            part = part * 10 + *address++ - '0';
            if (++digits > 3)
                return STB_WORLDWIDE;
        }
        if (!digits || part > 255 || *address++ != (i == 3 ? ':' : '.'))
            return STB_WORLDWIDE;
        ip[i] = part;
    }
    if (!stRegionLoaded)
        UI_BrowserLoadRegions();
    return stb_region(stRegionData, stRegionRows, stb_ipv4(ip));
}

static int UI_BrowserCompareServers(int source, int column, int descending, int left, int right)
{
    char address[MAX_ADDRESSLENGTH];
    int leftRegion, rightRegion, order;
    if (column != STB_SORT_REGION)
        return trap->LAN_CompareServers(source, column, descending, left, right);
    trap->LAN_GetServerAddressString(source, left, address, sizeof(address));
    leftRegion = UI_BrowserRegion(address);
    trap->LAN_GetServerAddressString(source, right, address, sizeof(address));
    rightRegion = UI_BrowserRegion(address);
    order = stb_compare_regions(leftRegion, rightRegion, descending);
    if (!order)
        order = trap->LAN_CompareServers(source, SORT_HOST, 0, left, right);
    return (order > 0) - (order < 0);
}

static int UI_BrowserInt(const char *key, int low, int high, int fallback)
{
    char value[24];
    int number;
    trap->Cvar_VariableStringBuffer(key, value, sizeof(value));
    if (low < 0 && !strcmp(value, "-1"))
        return -1;
    number = stb_number(value, high);
    return number >= low && number >= 0 ? number : fallback;
}

static stb_filter UI_BrowserFilter(void)
{
    stb_filter filter;
    filter.game = UI_BrowserInt("ui_stMatchGame", -1, GT_MAX_GAME_TYPE - 1, -1);
    filter.region = UI_BrowserInt("ui_stMatchRegion", 0, STB_REGION_COUNT - 1, 0);
    filter.max_ping = UI_BrowserInt("ui_stMatchMaxPing", 0, 9999, 0);
    filter.min_humans = UI_BrowserInt("ui_stMatchHumans", 0, 9999, 0);
    filter.password = UI_BrowserInt("ui_stMatchPassword", -1, 1, -1);
    filter.combat = UI_BrowserInt("ui_stMatchCombat", -1, 1, -1);
    filter.strict_region = UI_BrowserInt("ui_stMatchRegionOnly", 0, 1, 0);
    return filter;
}

static stb_server UI_BrowserServer(const char *info, int ping)
{
    stb_server server;
    server.ping = ping;
    server.occupied = stb_number(Info_ValueForKey(info, "clients"), 1024);
    server.capacity = stb_number(Info_ValueForKey(info, "sv_maxclients"), 1024);
    server.humans = ping > 0 && stb_valid_occupancy(server.occupied, server.capacity)
        ? stb_humans_from_counts(server.occupied, Info_ValueForKey(info, "g_humanplayers"),
            Info_ValueForKey(info, "bots")) : -1;
    server.game = stb_number(Info_ValueForKey(info, "gametype"), 255);
    server.password = stb_number(Info_ValueForKey(info, "needpass"), 1);
    server.combat = stb_number(Info_ValueForKey(info, "st_combatMode"), 1);
    server.region = UI_BrowserRegion(Info_ValueForKey(info, "addr"));
    server.min_server_ping = Q_max(0, stb_number(Info_ValueForKey(info, "minping"), 99999));
    server.max_server_ping = Q_max(0, stb_number(Info_ValueForKey(info, "maxping"), 99999));
    return server;
}

static void UI_BrowserFinishPopulationRefresh(void)
{
    int i, selected = -1;
    if (!trap->Cvar_VariableValue("cl_browserPopulationDirty")) {
        UI_BuildServerDisplayList(2);
        return;
    }

    i = uiInfo.serverStatus.currentServer;
    if (i >= 0 && i < uiInfo.serverStatus.numDisplayServers)
        selected = uiInfo.serverStatus.displayServers[i];

    // A row may have been displayed or filtered out before its status arrived.
    // Reapply filters, sorting, and the total once for the completed refresh.
    UI_BuildServerDisplayList(qtrue);
    for (i = 0; i < uiInfo.serverStatus.numDisplayServers; ++i) {
        if (uiInfo.serverStatus.displayServers[i] == selected) {
            Menu_SetFeederSelection(NULL, FEEDER_SERVERS, i, "joinserver");
            break;
        }
    }
}

static qboolean UI_BrowserSearchMatches(const char *info)
{
    char host[MAX_NAME_LENGTH];
    const char *name;
    size_t len = 0;
    if (!stServerSearch[0])
        return qtrue;
    for (name = Info_ValueForKey(info, "hostname"); *name && len < sizeof(host) - 1; ++name) {
        if (Q_IsColorString(name))
            ++name;
        else
            host[len++] = *name;
    }
    host[len] = 0;
    return Q_stristr(host, stServerSearch) ||
        Q_stristr(Info_ValueForKey(info, "mapname"), stServerSearch) ||
        Q_stristr(Info_ValueForKey(info, "addr"), stServerSearch);
}

static void UI_BrowserDirect(void)
{
    char address[MAX_ADDRESSLENGTH];
    trap->Cvar_VariableStringBuffer("ui_stDirectAddress", address, sizeof(address));
    if (stb_direct_address(address)) {
        trap->Cvar_Set("ui_stDirectMessage", "");
        UI_JoinAddress(address);
    } else {
        trap->Cvar_Set("ui_stDirectMessage", "Enter a server hostname or IPv4 address with an optional port.");
    }
}

static void UI_QuickStatus(const char *state, const char *message)
{
    trap->Cvar_Set("ui_stMatchState", state);
    trap->Cvar_Set("ui_stMatchMessage", message);
}

static void UI_QuickOpen(void)
{
    stQuickSearching = 0;
    stQuickAddress[0] = 0;
    stQuickPassword = qfalse;
    UI_QuickStatus("0", "");
    trap->Cvar_Set("ui_stMatchDetails", "");
}

static void UI_QuickFind(void)
{
    stQuickAddress[0] = 0;
    stQuickPassword = qfalse;
    stQuickSearching = 1;
    trap->Cvar_Set("ui_stMatchDetails", "");
    UI_QuickStatus("1", "Measuring server ping...");
    if (UI_SourceForLAN() != AS_GLOBAL) {
        trap->Cvar_Set("ui_netSource", "1");
        trap->Cvar_Update(&ui_netSource);
        UI_StartServerRefresh(qtrue);
    } else if (!uiInfo.serverStatus.refreshActive &&
               (!stLatestWorldwide || uiInfo.uiDC.realTime - stLatestWorldwide > ST_BROWSER_REUSE_MS)) {
        UI_StartServerRefresh(qtrue);
    }
}

static void UI_QuickClear(void)
{
    trap->Cvar_Reset("ui_stMatchGame");
    trap->Cvar_Reset("ui_stMatchRegion");
    trap->Cvar_Reset("ui_stMatchRegionOnly");
    trap->Cvar_Reset("ui_stMatchMaxPing");
    trap->Cvar_Reset("ui_stMatchHumans");
    trap->Cvar_Reset("ui_stMatchPassword");
    trap->Cvar_Reset("ui_stMatchCombat");
    UI_QuickFind();
}

static void UI_QuickRecommend(void)
{
    char info[MAX_INFO_STRING];
    int i, best = -1;
    stb_server winner = {0};
    int count = trap->LAN_GetServerCount(AS_GLOBAL);

    stQuickSearching = 0;
    stQuickFilter = UI_BrowserFilter();
    for (i = 0; i < count; ++i) {
        stb_server server;
        int ping = trap->LAN_GetServerPing(AS_GLOBAL, i);
        if (ping <= 0)
            continue;
        trap->LAN_GetServerInfo(AS_GLOBAL, i, info, sizeof(info));
        server = UI_BrowserServer(info, ping);
        if (stb_matches(&server, &stQuickFilter, 1) &&
            (best < 0 || stb_better(&server, &winner, stQuickFilter.region))) {
            winner = server;
            best = i;
        }
    }
    if (best < 0) {
        const char *message = count > 0 ? "No joinable server matches these filters." :
            "No worldwide servers responded. Try Refresh or Direct Connect.";
        UI_QuickStatus("2", message);
        return;
    }
    trap->LAN_GetServerAddressString(AS_GLOBAL, best, stQuickAddress, sizeof(stQuickAddress));
    trap->LAN_GetServerInfo(AS_GLOBAL, best, info, sizeof(info));
    UI_QuickStatus("3", va("Recommended: %.48s", Info_ValueForKey(info, "hostname")));
    trap->Cvar_Set("ui_stMatchDetails", va("%d ms  |  %s%s%s",
        winner.ping, winner.region ? stb_region_name(winner.region) : "Unknown region",
        winner.password ? "  |  Password required" : "",
        stQuickFilter.region && winner.region != stQuickFilter.region ? "  |  Worldwide result" : ""));
}

static void UI_QuickJoin(qboolean enteredPassword)
{
    int i, count = trap->LAN_GetServerCount(AS_GLOBAL);
    char address[MAX_ADDRESSLENGTH], info[MAX_INFO_STRING];
    stb_filter filter = UI_BrowserFilter();
    stQuickPassword = qfalse;
    if (!stQuickAddress[0])
        return;
    if (!uiInfo.serverStatus.refreshActive && stLatestWorldwide &&
        uiInfo.uiDC.realTime - stLatestWorldwide <= ST_BROWSER_REUSE_MS &&
        !memcmp(&filter, &stQuickFilter, sizeof(filter))) {
        for (i = 0; i < count; ++i) {
            stb_server server;
            trap->LAN_GetServerAddressString(AS_GLOBAL, i, address, sizeof(address));
            if (strcmp(address, stQuickAddress))
                continue;
            trap->LAN_GetServerInfo(AS_GLOBAL, i, info, sizeof(info));
            server = UI_BrowserServer(info, trap->LAN_GetServerPing(AS_GLOBAL, i));
            if (!stb_matches(&server, &filter, 1))
                break;
            if (server.password && !enteredPassword) {
                stQuickPassword = qtrue;
                Menus_OpenByName("password_request");
            } else {
                UI_JoinAddress(address);
            }
            return;
        }
    }
    stQuickAddress[0] = 0;
    trap->Cvar_Set("ui_stMatchDetails", "");
    UI_QuickStatus("2", "Search again to check the current filters and availability.");
}

static void UI_BrowserFrame(void)
{
    menuDef_t *browser = Menus_FindByName("joinserver");
    menuDef_t *quick = Menus_FindByName("st_quickmatch");
    menuDef_t *password = Menus_FindByName("password_request");
    if (!password || !(password->window.flags & WINDOW_VISIBLE))
        stQuickPassword = qfalse;
    if (browser && (browser->window.flags & WINDOW_VISIBLE)) {
        char search[sizeof(stServerSearch)];
        trap->Cvar_VariableStringBuffer("ui_stServerSearch", search, sizeof(search));
        if (strcmp(search, stServerSearch)) {
            Q_strncpyz(stServerSearch, search, sizeof(stServerSearch));
            UI_BuildServerDisplayList(qtrue);
        }
    }
    if (!quick || !(quick->window.flags & WINDOW_VISIBLE))
        stQuickSearching = 0;
    else if (stQuickSearching && !uiInfo.serverStatus.refreshActive)
        UI_QuickRecommend();
}
