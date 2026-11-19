// Included by cl_main.cpp. DNS workers only resolve addresses. The frame
// thread owns UDP, deadlines and the global browser cache.
extern qboolean NET_ResolveBrowserMaster(const char *host, netadr_t *address);

static constexpr int STB_MASTER_COUNT = MAX_MASTER_SERVERS + 1;
static constexpr int STB_MASTER_TIMEOUT = 2500;
static constexpr int STB_DNS_TIMEOUT = 1200;

struct BrowserMaster {
    char host[MAX_STRING_CHARS];
    netadr_t resolved;
    std::atomic<int> dns{0}; // 0 idle, 1 running, 2 done
    netadr_t requested;
    bool active, sent;
};

static BrowserMaster browserMasters[STB_MASTER_COUNT];
static int browserMasterStart;
static int browserMasterDeadline;
static bool browserMasterReplacedList;
static char browserMasterRequest[MAX_STRING_CHARS];

static int SDLCALL CL_BrowserResolve(void *data)
{
    auto &master = *static_cast<BrowserMaster *>(data);
    master.resolved = {};
    NET_ResolveBrowserMaster(master.host, &master.resolved);
    master.dns.store(2);
    return 0;
}

static void CL_BrowserMasterFrame()
{
    if (!browserMasterDeadline)
        return;
    const int now = Sys_Milliseconds();
    if (!stb_waiting(now, browserMasterDeadline)) {
        browserMasterDeadline = 0;
        Cvar_Set("cl_browserDiscoveryPending", "0");
        return;
    }
    if (now - browserMasterStart >= STB_DNS_TIMEOUT)
        return;
    for (int i = 0; i < STB_MASTER_COUNT; ++i) {
        auto &master = browserMasters[i];
        if (!master.active || master.sent || master.dns.load() != 2 || !master.resolved.port)
            continue;
        master.sent = true;
        bool duplicate = false;
        for (const auto &other : browserMasters) {
            if (other.requested.port && NET_CompareAdr(&master.resolved, &other.requested)) {
                duplicate = true;
                break;
            }
        }
        if (!duplicate) {
            master.requested = master.resolved;
            NET_OutOfBandPrint(NS_SERVER, &master.requested, "%s", browserMasterRequest);
        }
    }
}

static void CL_BrowserQueryMasters(int selected, const char *request)
{
    cls.pingUpdateSource = AS_GLOBAL;
    for (auto &ping : cl_pinglist)
        if (ping.browser)
            ping.adr.port = 0;

    bool active = false;
    for (int i = 0; i < STB_MASTER_COUNT; ++i) {
        auto &master = browserMasters[i];
        master.active = master.sent = false;
        master.requested = {};
        if (selected && selected != i + 1)
            continue;
        const char *host = Cvar_VariableString(i == MAX_MASTER_SERVERS ?
            "cl_browserBackupMaster" : va("sv_master%d", i + 1));
        if (!*host)
            continue;
        if (master.dns.load() == 1) {
            // Keep one resolver per source even across repeated Refresh clicks.
            if (strcmp(host, master.host))
                continue;
        } else {
            Q_strncpyz(master.host, host, sizeof(master.host));
            master.dns.store(1);
            SDL_Thread *thread = SDL_CreateThread(CL_BrowserResolve, "Browser DNS", &master);
            if (!thread) {
                master.dns.store(0);
                continue;
            }
            SDL_DetachThread(thread);
        }
        active = master.active = true;
    }
    browserMasterReplacedList = false;
    browserMasterStart = Sys_Milliseconds();
    browserMasterDeadline = active ? browserMasterStart + STB_MASTER_TIMEOUT : 0;
    Q_strncpyz(browserMasterRequest, request, sizeof(browserMasterRequest));
    Cvar_Set("cl_browserMasterReplies", "0");
    Cvar_Set("cl_browserDiscoveryPending", active ? "1" : "0");
}

static void CL_ServersResponsePacket(const netadr_t *from, msg_t *msg)
{
    if (!stb_waiting(Sys_Milliseconds(), browserMasterDeadline))
        return;
    bool requested = false;
    for (const auto &master : browserMasters)
        if (master.requested.port && NET_CompareAdr(from, &master.requested))
            requested = true;
    if (!requested)
        return;

    stb_address addresses[256];
    const int count = stb_parse_master(msg->data, msg->cursize, addresses, ARRAY_LEN(addresses));
    if (count < 0)
        return;
    Cvar_Set("cl_browserMasterReplies", "1");
    for (int i = 0; i < count; ++i) {
        const unsigned char *entry = addresses[i].bytes;
        netadr_t address = {};
        address.type = NA_IP;
        memcpy(address.ip, entry, sizeof(address.ip));
        memcpy(&address.port, entry + 4, sizeof(address.port));
        if (!address.ip[0] || address.ip[0] >= 224 ||
            (!Sys_IsLANAddress(from) && Sys_IsLANAddress(&address)))
            continue;
        if (!browserMasterReplacedList) {
            // Keep the cache until a master supplies at least one usable address.
            cls.numglobalservers = 0;
            cls.numGlobalServerAddresses = 0;
            browserMasterReplacedList = true;
        }
        if (cls.numglobalservers >= MAX_GLOBAL_SERVERS)
            break;

        int existing = 0;
        for (; existing < cls.numglobalservers; ++existing)
            if (NET_CompareAdr(&cls.globalServers[existing].adr, &address))
                break;
        if (existing == cls.numglobalservers) {
            serverInfo_t &server = cls.globalServers[cls.numglobalservers++];
            CL_InitServerInfo(&server, &address);
            server.visible = qtrue;
        }
    }
}
