"""Apply the browser to reconstructed OpenJK-derived source trees."""
from pathlib import Path
import shutil

SOURCE = Path(__file__).resolve().parent


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Expected exactly one baseline anchor: {old[:150]!r}")
    return text.replace(old, new, 1)


def between(text, start, end, new):
    left = text.index(start)
    right = text.index(end, left + len(start))
    return text[:left] + new + text[right:]


def edit(root, name, transform):
    path = root / "codemp" / name
    text = transform(path.read_text(encoding="utf-8"))
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def server(root):
    def advertise(text):
        return replace(text, '\tInfo_SetValueForKey( infostring, "g_humanplayers", va("%i", humans) );',
                       '''\tInfo_SetValueForKey( infostring, "g_humanplayers", va("%i", humans) );
\tconst char *combat = Cvar_VariableString("st_combatMode");
\tif (!strcmp(combat, "0") || !strcmp(combat, "1")) {
\t\tInfo_SetValueForKey(infostring, "st_combatMode", combat);
\t}''')

    edit(root, "server/sv_main.cpp", advertise)


def engine(root):
    for name in ("st_browser.h", "st_browser_discovery.inc"):
        shutil.copyfile(SOURCE / name, root / "codemp/client" / name)

    def declarations(text):
        text = replace(text, "char\t\tinfo[MAX_INFO_STRING];\n} ping_t;",
                       "char\t\tinfo[MAX_INFO_STRING];\n\tint browser;\n\tchar challenge[24];\n} ping_t;")
        return replace(text, "int\t\t\thumans, bots;", "int\t\t\thumans, bots;\n\tint combatMode, passwordKnown;")

    def network(text):
        text = replace(text, "#include <winsock.h>", "#include <winsock2.h>\n\t#include <ws2tcpip.h>")
        anchor = "//=============================================================================\n\n/*\n==================\nNET_GetPacket"
        return replace(text, anchor, '''#ifndef DEDICATED
// Runs on browser DNS workers. getaddrinfo owns its result per call.
qboolean NET_ResolveBrowserMaster(const char *input, netadr_t *address)
{
\tchar host[MAX_STRING_CHARS];
\tQ_strncpyz(host, input, sizeof(host));
\tconst char *service = "29060";
\tif (char *port = strchr(host, ':')) {
\t\t*port = 0;
\t\tservice = port + 1;
\t}
\tif (!*host || !*service)
\t\treturn qfalse;
\taddrinfo hints = {}, *result = nullptr;
\thints.ai_family = AF_INET;
\thints.ai_socktype = SOCK_DGRAM;
\thints.ai_flags = AI_NUMERICSERV;
\tif (getaddrinfo(host, service, &hints, &result) != 0)
\t\treturn qfalse;
\tSockadrToNetadr(reinterpret_cast<sockaddr_in *>(result->ai_addr), address);
\tfreeaddrinfo(result);
\treturn qtrue;
}
#endif

''' + anchor)

    def discovery(text):
        text = replace(text, '#include "client.h"', '''#include "client.h"
#include <atomic>
#include <SDL_thread.h>
#include "st_browser.h"''')
        text = replace(text, "server->humans = server->bots = 0;",
                       "server->humans = server->bots = -1;\n\tserver->combatMode = -1;\n\tserver->passwordKnown = 0;")
        text = between(text, "#define MAX_SERVERSPERPACKET", "#ifndef MAX_STRINGED_SV_STRING",
                       '#include "st_browser_discovery.inc"\n\n')
        text = replace(text, "\tSE_CheckForLanguageUpdates();\t", "\tCL_BrowserMasterFrame();\n\tSE_CheckForLanguageUpdates();\t")
        text = replace(text, '\tcl_timeout = Cvar_Get (', '''\tCvar_Get("cl_browserBackupMaster", "master.jk2mv.org", CVAR_ARCHIVE_ND);
\tCvar_Get("cl_browserDiscoveryPending", "0", CVAR_ROM);
\tCvar_Get("cl_browserMasterReplies", "0", CVAR_ROM);

\tcl_timeout = Cvar_Get (''')
        text = between(text, "void CL_GlobalServers_f( void ) {", "/*\n==================\nCL_GetPing",
                       '''void CL_GlobalServers_f( void ) {
\tconst int master = stb_number(Cmd_Argv(1), MAX_MASTER_SERVERS);
\tconst int protocol = stb_number(Cmd_Argv(2), 999);
\tif (master < 0 || protocol < 0) {
\t\tCom_Printf("usage: globalservers <master# 0-%d> <protocol> [keywords]\\n", MAX_MASTER_SERVERS);
\t\treturn;
\t}
\tchar request[MAX_STRING_CHARS];
\tCom_sprintf(request, sizeof(request), "getservers %d %s", protocol, Cmd_ArgsFrom(3));
\tCL_BrowserQueryMasters(master, request);
}

''')
        text = replace(text, 'server->clients = atoi(Info_ValueForKey(info, "clients"));',
                       'server->clients = stb_number(Info_ValueForKey(info, "clients"), 1024);')
        text = replace(text, 'server->maxClients = atoi(Info_ValueForKey(info, "sv_maxclients"));',
                       'server->maxClients = stb_number(Info_ValueForKey(info, "sv_maxclients"), 1024);')
        text = replace(text, 'server->gameType = atoi(Info_ValueForKey(info, "gametype"));',
                       'server->gameType = stb_number(Info_ValueForKey(info, "gametype"), 255);')
        for key, member in (("minping", "minPing"), ("maxping", "maxPing")):
            text = replace(text, f'server->{member} = atoi(Info_ValueForKey(info, "{key}"));',
                           f'server->{member} = Q_max(0, stb_number(Info_ValueForKey(info, "{key}"), 99999));')
        text = replace(text, 'server->needPassword = (qboolean)atoi(Info_ValueForKey(info, "needpass" ));',
                       '''const int needPass = stb_number(Info_ValueForKey(info, "needpass"), 3);
\t\t\tserver->passwordKnown = needPass >= 0;
\t\t\tserver->needPassword = (needPass > 0) ? qtrue : qfalse;''')
        text = replace(text, '''server->humans = atoi( Info_ValueForKey( info, "g_humanplayers" ) );
\t\t\tserver->bots = atoi( Info_ValueForKey( info, "bots" ) );''',
                       '''server->humans = stb_humans(server->clients, Info_ValueForKey(info, "g_humanplayers"));
\t\t\tserver->bots = server->humans < 0 ? -1 : server->clients - server->humans;
\t\t\tserver->combatMode = stb_number(Info_ValueForKey(info, "st_combatMode"), 1);''')
        for cap, count, array in (("MAX_OTHER_SERVERS", "numlocalservers", "localServers"),
                                  ("MAX_OTHER_SERVERS", "numfavoriteservers", "favoriteServers"),
                                  ("MAX_GLOBAL_SERVERS", "numglobalservers", "globalServers")):
            text = replace(text, f'for (i = 0; i < {cap}; i++) {{\n\t\tif (NET_CompareAdr(from, &cls.{array}[i].adr))',
                           f'for (i = 0; i < cls.{count}; i++) {{\n\t\tif (NET_CompareAdr(from, &cls.{array}[i].adr))')
        text = replace(text, 'prot = atoi( Info_ValueForKey( infoString, "protocol" ) );',
                       'prot = stb_number(Info_ValueForKey(infoString, "protocol"), 999);')
        text = replace(text, '''\t\t\t// calc ping time
\t\t\tcl_pinglist[i].time = Sys_Milliseconds() - cl_pinglist[i].start;''',
                       '''\t\t\tconst char *challenge = Info_ValueForKey(infoString, "challenge");
\t\t\tif (cl_pinglist[i].browser && *challenge && strcmp(challenge, cl_pinglist[i].challenge))
\t\t\t\treturn;
\t\t\tcl_pinglist[i].time = Q_max(1, Sys_Milliseconds() - cl_pinglist[i].start);''')
        text = replace(text, '''\t\tmaxPing = Cvar_VariableIntegerValue( "cl_maxPing" );
\t\tif( maxPing < 100 ) {
\t\t\tmaxPing = 100;
\t\t}''', '\t\tmaxPing = stb_ping_budget(cl_pinglist[n].browser, Cvar_VariableIntegerValue("cl_maxPing"));')
        text = replace(text, 'CL_SetServerInfoByAddress(&cl_pinglist[n].adr, cl_pinglist[n].info, cl_pinglist[n].time);',
                       '''if (time)
\t\tCL_SetServerInfoByAddress(&cl_pinglist[n].adr, cl_pinglist[n].time ? cl_pinglist[n].info : nullptr,
\t\t\tcl_pinglist[n].time);''')
        text = replace(text, 'pingptr->time  = 0;', 'pingptr->time  = 0;\n\tpingptr->browser = 0;')
        text = replace(text, 'NET_OutOfBandPrint( NS_CLIENT, &cl_pinglist[j].adr, "getinfo xxx" );',
                       '''cl_pinglist[j].browser = 1;
\t\t\t\t\t\tcl_pinglist[j].info[0] = 0;
\t\t\t\t\t\tstatic unsigned int serial;
\t\t\t\t\t\tCom_sprintf(cl_pinglist[j].challenge, sizeof(cl_pinglist[j].challenge), "%x-%x",
\t\t\t\t\t\t\t(unsigned int)cl_pinglist[j].start, ++serial);
\t\t\t\t\t\tNET_OutOfBandPrint(NS_CLIENT, &cl_pinglist[j].adr, "getinfo %s", cl_pinglist[j].challenge);''')
        return text

    def lan(text):
        cache = '''// Keep the original record size so existing favorites survive the upgrade.
static constexpr int serverCacheRecord = offsetof(serverInfo_t, combatMode);

static void LAN_ReadCacheList(serverInfo_t *servers, int capacity, fileHandle_t file)
{
\tfor (int i = 0; i < capacity; ++i) {
\t\tserverInfo_t &server = servers[i];
\t\tFS_Read(&server, serverCacheRecord, file);
\t\tserver.hostName[sizeof(server.hostName) - 1] = 0;
\t\tserver.mapName[sizeof(server.mapName) - 1] = 0;
\t\tserver.game[sizeof(server.game) - 1] = 0;
\t\tserver.ping = server.humans = server.bots = server.combatMode = -1;
\t\tserver.passwordKnown = 0;
\t}
}

static void LAN_WriteCacheList(const serverInfo_t *servers, int capacity, fileHandle_t file)
{
\tfor (int i = 0; i < capacity; ++i)
\t\tFS_Write(&servers[i], serverCacheRecord, file);
}

void LAN_LoadCachedServers() {
\tfileHandle_t file;
\tconst int length = FS_SV_FOpenFileRead("servercache.dat", &file);
\tcls.numglobalservers = cls_nummplayerservers = cls.numfavoriteservers = 0;
\tcls.numGlobalServerAddresses = 0;
\tif (!file)
\t\treturn;
\tint header[4] = {};
\tconst int bytes = serverCacheRecord * (ARRAY_LEN(cls.globalServers) +
\t\tARRAY_LEN(cls_mplayerServers) + ARRAY_LEN(cls.favoriteServers));
\tif (length == bytes + sizeof(header) && FS_Read(header, sizeof(header), file) == sizeof(header) &&
\t\theader[3] == bytes && header[0] >= -1 && header[0] <= ARRAY_LEN(cls.globalServers) &&
\t\theader[1] >= 0 && header[1] <= ARRAY_LEN(cls_mplayerServers) &&
\t\theader[2] >= 0 && header[2] <= ARRAY_LEN(cls.favoriteServers)) {
\t\tcls.numglobalservers = Q_max(0, header[0]);
\t\tcls_nummplayerservers = header[1];
\t\tcls.numfavoriteservers = header[2];
\t\tLAN_ReadCacheList(cls.globalServers, ARRAY_LEN(cls.globalServers), file);
\t\tLAN_ReadCacheList(cls_mplayerServers, ARRAY_LEN(cls_mplayerServers), file);
\t\tLAN_ReadCacheList(cls.favoriteServers, ARRAY_LEN(cls.favoriteServers), file);
\t}
\tFS_FCloseFile(file);
}

void LAN_SaveServersToCache() {
\tconst fileHandle_t file = FS_SV_FOpenFileWrite("servercache.dat");
\tif (!file)
\t\treturn;
\tconst int header[] = {cls.numglobalservers, cls_nummplayerservers, cls.numfavoriteservers,
\t\tserverCacheRecord * (ARRAY_LEN(cls.globalServers) + ARRAY_LEN(cls_mplayerServers) +
\t\t\tARRAY_LEN(cls.favoriteServers))};
\tFS_Write(header, sizeof(header), file);
\tLAN_WriteCacheList(cls.globalServers, ARRAY_LEN(cls.globalServers), file);
\tLAN_WriteCacheList(cls_mplayerServers, ARRAY_LEN(cls_mplayerServers), file);
\tLAN_WriteCacheList(cls.favoriteServers, ARRAY_LEN(cls.favoriteServers), file);
\tFS_FCloseFile(file);
}

'''
        text = between(text, "void LAN_LoadCachedServers", "/*\n====================\nLAN_ResetPings", cache)
        text = replace(text, "int LAN_AddServer(int source", "extern void CL_InitServerInfo(serverInfo_t *, const netadr_t *);\n\nint LAN_AddServer(int source")
        text = replace(text, "\t\tNET_StringToAdr( address, &adr );",
                       "\t\tif (!NET_StringToAdr(address, &adr))\n\t\t\treturn -1;")
        text = replace(text, "servers[*count].adr = adr;", "CL_InitServerInfo(&servers[*count], &adr);")
        text = replace(text, "cls.favoriteServers[cls.numfavoriteservers].adr = adr;",
                       "CL_InitServerInfo(&cls.favoriteServers[cls.numfavoriteservers], &adr);")
        text = replace(text, 'Info_SetValueForKey( info, "needpass", va("%i", server->needPassword ) );',
                       '''Info_SetValueForKey( info, "needpass", va("%i", server->passwordKnown ? server->needPassword : -1) );
\t\tInfo_SetValueForKey(info, "st_combatMode", va("%i", server->combatMode));''')
        text = between(text, "\t\tcase SORT_CLIENTS:", "\n\t\tcase SORT_GAME:",
                       '''\t\tcase SORT_CLIENTS:
\t\t\tif ((server1->humans < 0) != (server2->humans < 0))
\t\t\t\treturn server1->humans < 0 ? 1 : -1;
\t\t\tres = server1->humans - server2->humans;
\t\t\tbreak;
''')
        return text

    edit(root, "client/client.h", declarations)
    edit(root, "qcommon/net_ip.cpp", network)
    edit(root, "client/cl_main.cpp", discovery)
    edit(root, "client/cl_lan.cpp", lan)
    cmake = root / "codemp/CMakeLists.txt"
    cmake.write_text(replace(cmake.read_text(), '"winmm" "wsock32"', '"winmm" "ws2_32"'), newline="\n")
    server(root)


def frontend(root):
    for name in ("st_browser.h", "st_browser_ui.inc"):
        shutil.copyfile(SOURCE / name, root / "codemp/ui" / name)

    def cvars(text):
        text = replace(text, 'XCVAR_DEF( ui_netSource,\t\t\t\t\t"0",', 'XCVAR_DEF( ui_netSource,\t\t\t\t\t"1",')
        fields = []
        for name, value in (("Game", "-1"), ("Region", "0"), ("RegionOnly", "0"),
                            ("MaxPing", "0"), ("Humans", "0"), ("Password", "-1"),
                            ("Combat", "-1")):
            fields.append(f'XCVAR_DEF( ui_stMatch{name}, "{value}", NULL, CVAR_ARCHIVE|CVAR_INTERNAL )')
        return replace(text, "#undef XCVAR_DEF", "\n".join(fields) + '''
XCVAR_DEF( ui_stMatchFilterList, "0", NULL, CVAR_ARCHIVE|CVAR_INTERNAL )
XCVAR_DEF( ui_stServerSearch, "", NULL, CVAR_TEMP|CVAR_INTERNAL )
XCVAR_DEF( ui_stDirectAddress, "", NULL, CVAR_TEMP|CVAR_INTERNAL )

#undef XCVAR_DEF''')

    def ui(text):
        text = replace(text, '#include "ui_local.h"', '#include "ui_local.h"\n#include "st_browser.h"')
        text = replace(text, "void UI_Shutdown( void ) {", '''static void UI_BrowserFreeRegions(void);
void UI_Shutdown( void ) {
\tUI_BrowserFreeRegions();''')
        text = replace(text, '''\t\tchar buff[64];
\t\tQ_strncpyz(buff, UI_Cvar_VariableString(va("ui_lastServerRefresh_%i", ui_netSource.integer)),''',
                       '''\t\tchar buff[64];
\t\tif (UI_SourceForLAN() == AS_GLOBAL &&
\t\t\t!trap->Cvar_VariableValue("cl_browserMasterReplies") &&
\t\t\t*UI_Cvar_VariableString(va("ui_lastServerRefresh_%i", ui_netSource.integer))) {
\t\t\tText_Paint(rect->x, rect->y, scale, color, "No master replied. Checked saved server addresses.",
\t\t\t\t0, 0, textStyle, iMenuFont);
\t\t\treturn;
\t\t}
\t\tQ_strncpyz(buff, UI_Cvar_VariableString(va("ui_lastServerRefresh_%i", ui_netSource.integer)),''')
        text = between(text, "static const int numNetSources = 7;", "void AssetCache(void)", '''static const char *GetNetSourceString(int source)
{
\tif (source > UIAS_LOCAL && source < UIAS_FAVORITES)
\t\treturn "Worldwide";
\treturn GetCRDelineatedString("MP_INGAME", "NET_SOURCES", UI_SourceForLAN());
}

''')
        text = text.replace("ui_netSource.integer >= numNetSources", "ui_netSource.integer > UIAS_FAVORITES")
        text = between(text, "static qboolean UI_NetSource_HandleKey", "static qboolean UI_NetFilter_HandleKey",
                       '''static qboolean UI_NetSource_HandleKey(int flags, float *special, int key) {
\tstatic const int sources[] = {UIAS_LOCAL, UIAS_GLOBAL1, UIAS_FAVORITES};
\tint current, next;
\tif (key != A_MOUSE1 && key != A_MOUSE2 && key != A_ENTER && key != A_KP_ENTER)
\t\treturn qfalse;
\tcurrent = UI_SourceForLAN() == AS_LOCAL ? 0 : UI_SourceForLAN() == AS_GLOBAL ? 1 : 2;
\tnext = (current + (key == A_MOUSE2 ? 2 : 1)) % 3;
\ttrap->Cvar_Set("ui_netSource", va("%d", sources[next]));
\ttrap->Cvar_Update(&ui_netSource);
\tUI_StartServerRefresh(qtrue);
\tUI_BuildServerDisplayList(qtrue);
\treturn qtrue;
}

''')
        text = text.replace('if ( atoi(Info_ValueForKey(info, "needpass")) )', 'if (atoi(Info_ValueForKey(info, "needpass")) > 0)')
        text = between(text, "static void UI_JoinServer( void )", "int UI_SiegeClassNum",
                       '''static void UI_JoinAddress(const char *address)
{
\tif (!*address)
\t\treturn;
\ttrap->Cvar_Set("cg_cameraOrbit", "0");
\ttrap->Cvar_Set("ui_singlePlayerActive", "0");
\ttrap->Cmd_ExecuteText(EXEC_APPEND, va("connect %s\\n", address));
}

static void UI_JoinServer(void)
{
\tchar address[MAX_ADDRESSLENGTH];
\tint index = uiInfo.serverStatus.currentServer;
\tif (index >= 0 && index < uiInfo.serverStatus.numDisplayServers) {
\t\ttrap->LAN_GetServerAddressString(UI_SourceForLAN(), uiInfo.serverStatus.displayServers[index],
\t\t\taddress, sizeof(address));
\t\tUI_JoinAddress(address);
\t}
}

#include "st_browser_ui.inc"

''')
        text = replace(text, '\t\t} else if (Q_stricmp(name, "RefreshServers") == 0) {',
                       '''\t\t} else if (Q_stricmp(name, "QuickOpen") == 0) {
\t\t\tUI_QuickOpen();
\t\t} else if (Q_stricmp(name, "QuickFind") == 0) {
\t\t\tUI_QuickFind();
\t\t} else if (Q_stricmp(name, "QuickClear") == 0) {
\t\t\tUI_QuickClear();
\t\t} else if (Q_stricmp(name, "QuickJoin") == 0) {
\t\t\tUI_QuickJoin(qfalse);
\t\t} else if (Q_stricmp(name, "ServerDirect") == 0) {
\t\t\tUI_BrowserDirect();
\t\t} else if (Q_stricmp(name, "ServerRefilter") == 0) {
\t\t\tUI_BuildServerDisplayList(qtrue);
\t\t} else if (Q_stricmp(name, "RefreshServers") == 0) {''')
        text = replace(text, '''\t\tif( UI_CheckPassword() )''', '''\t\tstQuickPassword = qfalse;
\t\tif( UI_CheckPassword() )''')
        text = replace(text, '''\t\telse if (Q_stricmp(name, "JoinServer") == 0)
\t\t{
\t\t\tUI_JoinServer();''', '''\t\telse if (Q_stricmp(name, "JoinServer") == 0)
\t\t{
\t\t\tif (stQuickPassword)
\t\t\t\tUI_QuickJoin(qtrue);
\t\t\telse
\t\t\t\tUI_JoinServer();''')
        text = between(text, "static void UI_InsertServerIntoDisplayList(int num, int position) {",
                       "/*\n==================\nUI_RemoveServerFromDisplayList", '''static void UI_InsertServerIntoDisplayList(int num, int position) {
\tint size = uiInfo.serverStatus.numDisplayServers;
\tint *list = uiInfo.serverStatus.displayServers;
\tif (position < 0 || position > size || size >= MAX_DISPLAY_SERVERS)
\t\treturn;
\tmemmove(list + position + 1, list + position, (size - position) * sizeof(*list));
\tlist[position] = num;
\t++uiInfo.serverStatus.numDisplayServers;
}

''')
        text = replace(text, "int i, count, clients, maxClients, ping, game, len, passw/*, visible*/;",
                       "int i, count, ping, game, len;\n\tstb_filter filter;\n\tqboolean sharedFilters;")
        text = replace(text, "//\tvisible = qfalse;\n\tfor (i = 0; i < count; i++) {",
                       '''\tsharedFilters = trap->Cvar_VariableValue("ui_stMatchFilterList") != 0 ? qtrue : qfalse;
\tif (sharedFilters)
\t\tfilter = UI_BrowserFilter();
\tfor (i = 0; i < count; i++) {''')
        text = replace(text, "\t\t\t// don't list servers with invalid info", """\t\t\tconst stb_server server = UI_BrowserServer(info, ping);
\t\t\tif (!UI_BrowserSearchMatches(info) || (sharedFilters && !stb_matches(&server, &filter, 0))) {
\t\t\t\tif (ping > 0)
\t\t\t\t\ttrap->LAN_MarkServerVisible(lanSource, i, qfalse);
\t\t\t\tcontinue;
\t\t\t}

\t\t\t// don't list servers with invalid info""")
        text = between(text, '\t\t\tclients = atoi(Info_ValueForKey(info, "clients"));',
                       '\t\t\tif (uiInfo.joinGameTypes[ui_joinGametype.integer].gtEnum != -1)',
                       '''\t\t\tif ((!ui_browserShowEmpty.integer && server.humans == 0) ||
\t\t\t\t(!ui_browserShowFull.integer && ping > 0 && stb_allocation(&server) == 0) ||
\t\t\t\t(!ui_browserShowPasswordProtected.integer && server.password == 1)) {
\t\t\t\ttrap->LAN_MarkServerVisible(lanSource, i, qfalse);
\t\t\t\tcontinue;
\t\t\t}

''')
        text = replace(text, "\t\t\tUI_BinaryServerInsertion(i);", '''\t\t\tUI_BinaryServerInsertion(i);
\t\t\tif (server.humans >= 0)
\t\t\t\tuiInfo.serverStatus.numPlayersOnServers += server.humans;''')
        text = replace(text, "\tstatic int lastColumn = -1;\n\tstatic int lastTime = 0;",
                       "\tstatic int lastServer = -1;\n\tstatic int lastSource = -1;\n\tstatic int lastTime = -1;")
        text = between(text, "\t\t\tif (lastColumn != column", "\t\t\tping = atoi",
                       '''\t\t\tint source = UI_SourceForLAN();
\t\t\tint server = uiInfo.serverStatus.displayServers[index];
\t\t\tif (lastServer != server || lastSource != source || lastTime != uiInfo.uiDC.realTime) {
\t\t\t\ttrap->LAN_GetServerInfo(source, server, info, sizeof(info));
\t\t\t\tlastServer = server;
\t\t\t\tlastSource = source;
\t\t\t\tlastTime = uiInfo.uiDC.realTime;
\t\t\t}
''')
        text = between(text, "\t\t\t\tcase SORT_CLIENTS :", "\t\t\t\tcase SORT_GAME :",
                       '''\t\t\t\tcase SORT_CLIENTS : {
\t\t\t\t\tconst stb_server snapshot = UI_BrowserServer(info, ping);
\t\t\t\t\tif (ping <= 0 || snapshot.capacity <= 0)
\t\t\t\t\t\treturn "?";
\t\t\t\t\tif (snapshot.humans < 0)
\t\t\t\t\t\tCom_sprintf(clientBuff, sizeof(clientBuff), "?/%d", snapshot.capacity);
\t\t\t\t\telse
\t\t\t\t\t\tCom_sprintf(clientBuff, sizeof(clientBuff), "%d/%d", snapshot.humans, snapshot.capacity);
\t\t\t\t\treturn clientBuff;
\t\t\t\t}
\t\t\t\tcase 5:
\t\t\t\t\treturn stRegionNames[UI_BrowserRegion(Info_ValueForKey(info, "addr"))];
''')
        text = replace(text, 'return Info_ValueForKey(info, "ping");',
                       '''Com_sprintf(clientBuff, sizeof(clientBuff), "%d", ping);
\t\t\t\t\t\treturn clientBuff;''')
        text = replace(text, "\t\tUI_DoServerRefresh();", "\t\tUI_DoServerRefresh();\n\t\tUI_BrowserFrame();")
        text = between(text, "static void UI_DoServerRefresh( void )\n{",
                       "/*\n=================\nUI_StartServerRefresh", '''static void UI_DoServerRefresh( void )
{
\tint source;
\tif (!uiInfo.serverStatus.refreshActive)
\t\treturn;
\tsource = UI_SourceForLAN();
\tif ((source == AS_GLOBAL && trap->Cvar_VariableValue("cl_browserDiscoveryPending")) ||
\t\t(source == AS_LOCAL && uiInfo.uiDC.realTime < stLocalReadyAt))
\t\treturn;
\tif (trap->LAN_UpdateVisiblePings(source)) {
\t\tUI_BuildServerDisplayList(qfalse);
\t\treturn;
\t}
\tUI_BuildServerDisplayList(2);
\tUI_StopServerRefresh();
\tif (source == AS_GLOBAL)
\t\tstLatestWorldwide = uiInfo.uiDC.realTime;
}

''')
        text = replace(text, "int count;\n\n\tif (!uiInfo.serverStatus.refreshActive)", "\tif (!uiInfo.serverStatus.refreshActive)")
        text = between(text, '\tCom_Printf("%d servers listed in browser',
                       '\n}\n\n/*\n=================\nUI_DoServerRefresh',
                       '''\tCom_Printf("%d servers listed with %d known human players.\\n",
\t\tuiInfo.serverStatus.numDisplayServers, uiInfo.serverStatus.numPlayersOnServers);''')
        text = replace(text, '\t\tuiInfo.serverStatus.refreshtime = uiInfo.uiDC.realTime + 1000;\n\t\treturn;\n\t}\n\n\tuiInfo.serverStatus.refreshtime = uiInfo.uiDC.realTime + 5000;',
                       '\t\tstLocalReadyAt = uiInfo.uiDC.realTime + 1000;\n\t\treturn;\n\t}\n')
        text = replace(text, '\tchar\t*ptr;\n\tint\t\tlanSource;\n\n\tqtime_t q;',
                       '\tint lanSource;\n\n\tqtime_t q;')
        text = between(text, '\tif( ui_netSource.integer >= UIAS_GLOBAL1 && ui_netSource.integer <= UIAS_GLOBAL5 ) {\n\t\tptr',
                       '\n}\n\n/*\n============\nGetModuleAPI', '''\tif (lanSource == AS_GLOBAL) {
\t\tint protocol = (int)trap->Cvar_VariableValue("debug_protocol");
\t\tif (!protocol)
\t\t\tprotocol = (int)trap->Cvar_VariableValue("protocol");
\t\tstLatestWorldwide = 0;
\t\ttrap->Cmd_ExecuteText(EXEC_NOW, va("globalservers 0 %d full empty\\n", protocol));
\t}''')
        return text

    def legacy(text):
        text = replace(text, ''' const float width=std::min(right-x+2,std::max(item->type==ITEM_TYPE_NUMERICFIELD?27.f:48.f,''',
                       ''' const bool search = LUI_Name(item->window.name, "server_search");
 const bool fill = search ||
   (item->cvar && LUI_Name(item->cvar, "ui_stDirectAddress"));
 const float width=fill ? right-x+2 : std::min(right-x+2,std::max(item->type==ITEM_TYPE_NUMERICFIELD?27.f:48.f,''')
        text = replace(text, ''' const float height=std::max(12.f,4.f+Text_Height("0",item->textscale,item->iMenuFont));''',
                       ''' const float height=std::max(search ? 20.f : 12.f,4.f+Text_Height("0",item->textscale,item->iMenuFont));''')
        return between(text, "void ST_LegacyBrowserPanel(const char* info){", "#ifdef ST_CONTROLS_QA",
                       '''void ST_LegacyBrowserPanel(const char* info){
 LUI_Panel(446,134,178,241,true);
 if(!info||!*info){SCUI_Label(458,149,154,.66f,"Select a server",scuMuted);return;}
 const int ping=atoi(Info_ValueForKey(info,"ping"));
 if(ping<=0){RUI_Text(458,149,.65f,"Awaiting reply",ruCyan);return;}
 SCUI_Fit(458,140,154,.59f,Info_ValueForKey(info,"hostname"),ruWhite);
 char map[MAX_QPATH];
 Q_strncpyz(map,Info_ValueForKey(info,"mapname"),sizeof(map));
 if(map[0]&&!strstr(map,"..")&&!strchr(map,'\\\\')&&!strchr(map,':')){
  const qhandle_t shot=trap->R_RegisterShaderNoMip(va("levelshots/%s",map));
  if(shot){
   float h=86,w=h*4/3*uiInfo.uiDC.yscale/uiInfo.uiDC.xscale;
   if(w>150){h*=150/w;w=150;}
   UI_DrawHandlePic(535-w/2,159,w,h,shot);
  }
  else RUI_Text(458,180,.53f,"Map preview unavailable",scuMuted);
 }
 RUI_Divider(458,248,152);
 const int password=atoi(Info_ValueForKey(info,"needpass"));
 RUI_Text(458,257,.55f,password>0?"Password required":password==0?"Open access":"Password unknown",ruWhite);
 const int combat=stb_number(Info_ValueForKey(info,"st_combatMode"),1);
 if(combat>=0)
  RUI_Text(458,278,.55f,combat==1?"Manual combat":"Classic combat",ruCyan);
 RUI_Text(458,305,.53f,atoi(Info_ValueForKey(info,"wdisable"))?"Weapons: restricted":"Weapons: unrestricted",scuMuted);
 RUI_Text(458,326,.53f,atoi(Info_ValueForKey(info,"fdisable"))?"Force: restricted":"Force: unrestricted",scuMuted);
}
''')

    edit(root, "ui/ui_xcvar.h", cvars)
    edit(root, "ui/ui_main.c", ui)
    edit(root, "ui/ui_st_legacy.inc", legacy)
    edit(root, "ui/ui_shared.c", lambda text: replace(text,
         '\t\t\t(!Q_stricmp(g_editItem->cvar, "st_uiYawSpeed") ||',
         '\t\t\t(!Q_stricmp(g_editItem->cvar, "ui_stServerSearch") ||\n'
         '\t\t\t !Q_stricmp(g_editItem->cvar, "st_uiYawSpeed") ||'))
