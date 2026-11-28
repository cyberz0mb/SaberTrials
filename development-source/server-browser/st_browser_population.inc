// Browser probes use their own slots so Server Info and Find Player retain
// the original status-request queue and retries.
static constexpr unsigned int ST_POPULATION_TIMEOUT = 2000;
static struct {
    netadr_t address;
    unsigned int sentAt;
    bool retried;
    int occupied, capacity;
    char challenge[24];
} stPopulationProbes[MAX_PINGREQUESTS];
static int stPopulationSource = -1;
static bool stPopulationFinishing;
static unsigned int stPopulationFinishAt;

void CL_BrowserResetPopulation(void)
{
    memset(stPopulationProbes, 0, sizeof(stPopulationProbes));
    stPopulationSource = -1;
    stPopulationFinishing = false;
    Cvar_Set("cl_browserPopulationDirty", "0");
}

static serverInfo_t *CL_BrowserPopulationServers(int source, int &count)
{
    switch (source) {
        case AS_LOCAL: count = cls.numlocalservers; return cls.localServers;
        case AS_GLOBAL: count = cls.numglobalservers; return cls.globalServers;
        case AS_FAVORITES: count = cls.numfavoriteservers; return cls.favoriteServers;
        default: count = 0; return nullptr;
    }
}

static bool CL_BrowserPopulationFrame(int source, bool pingBusy)
{
    const unsigned int now = Sys_Milliseconds();
    if (source != stPopulationSource) {
        CL_BrowserResetPopulation();
        stPopulationSource = source;
    }
    if (pingBusy) {
        stPopulationFinishing = false;
    } else if (!stPopulationFinishing) {
        stPopulationFinishing = true;
        stPopulationFinishAt = now;
    } else if (now - stPopulationFinishAt >= ST_POPULATION_TIMEOUT) {
        memset(stPopulationProbes, 0, sizeof(stPopulationProbes));
        return false;
    }

    bool pending = false;
    int count, next = 0;
    serverInfo_t *servers = CL_BrowserPopulationServers(source, count);
    for (auto &probe : stPopulationProbes) {
        if (probe.address.port && now - probe.sentAt >= ST_POPULATION_TIMEOUT)
            probe.address.port = 0;
        if (probe.address.port) {
            if (!probe.retried && now - probe.sentAt >= ST_POPULATION_TIMEOUT / 2) {
                probe.retried = true;
                NET_OutOfBandPrint(NS_CLIENT, &probe.address, "getstatus %s", probe.challenge);
            }
            pending = true;
            continue;
        }
        while (next < count) {
            serverInfo_t &server = servers[next++];
            if (server.ping <= 0 || server.humans >= 0 || server.populationProbed ||
                !stb_valid_occupancy(server.clients, server.maxClients) || !server.clients)
                continue;
            server.populationProbed = 1;
            probe.address = server.adr;
            probe.sentAt = now;
            probe.retried = false;
            probe.occupied = server.clients;
            probe.capacity = server.maxClients;
            static unsigned int serial;
            Com_sprintf(probe.challenge, sizeof(probe.challenge), "stp-%x-%x", now, ++serial);
            NET_OutOfBandPrint(NS_CLIENT, &probe.address, "getstatus %s", probe.challenge);
            pending = true;
            break;
        }
    }
    return pending;
}

static bool CL_BrowserPopulationReply(const netadr_t *from, const msg_t *message, bool manualPending)
{
    if (message->readcount >= message->cursize)
        return false;
    const char *data = reinterpret_cast<const char *>(message->data) + message->readcount;
    const size_t length = message->cursize - message->readcount;
    const char *newline = static_cast<const char *>(memchr(data, '\n', length));
    if (!newline || newline == data || *data != '\\' || newline - data >= BIG_INFO_STRING)
        return false;
    char header[BIG_INFO_STRING];
    size_t headerLength = newline - data;
    if (data[headerLength - 1] == '\r')
        --headerLength;
    if (memchr(data, 0, headerLength))
        return false;
    memcpy(header, data, headerLength);
    header[headerLength] = 0;

    char challenge[24];
    const char *value = Info_ValueForKey(header, "challenge");
    const bool tagged = !strncmp(value, "stp-", 4);
    if (!tagged && (*value || manualPending))
        return false;
    if (strlen(value) >= sizeof(challenge))
        return tagged;
    Q_strncpyz(challenge, value, sizeof(challenge));

    const unsigned int now = Sys_Milliseconds();
    for (auto &probe : stPopulationProbes) {
        if (!probe.address.port || !NET_CompareAdr(from, &probe.address) ||
            now - probe.sentAt >= ST_POPULATION_TIMEOUT || (tagged && strcmp(challenge, probe.challenge)))
            continue;

        const char *protocol = Info_ValueForKey(header, "protocol");
        if (*protocol && stb_number(protocol, 999) != PROTOCOL_VERSION)
            return true;
        const char *roster = newline + 1;
        const int advertised = stb_humans_from_counts(probe.occupied,
            Info_ValueForKey(header, "g_humanplayers"), Info_ValueForKey(header, "bots"));
        int humans = stb_status_humans(roster, length - (roster - data), probe.occupied, 0);
        if (humans >= 0 && advertised >= 0)
            humans = advertised;
        if (humans < 0) {
            const int total = stb_number(Info_ValueForKey(header, "sv_maxclients"), 1024);
            const char *privateSlots = Info_ValueForKey(header, "sv_privateClients");
            const int reserved = total - probe.capacity;
            if (reserved > 0 && (!*privateSlots || stb_number(privateSlots, total) == reserved))
                humans = stb_status_humans(roster, length - (roster - data), probe.occupied, reserved);
        }
        if (humans < 0)
            return true;

        int count;
        serverInfo_t *servers = CL_BrowserPopulationServers(stPopulationSource, count);
        for (int i = 0; i < count; ++i) {
            serverInfo_t &server = servers[i];
            if (server.populationProbed && server.ping > 0 && server.humans < 0 &&
                server.clients == probe.occupied && server.maxClients == probe.capacity &&
                NET_CompareAdr(from, &server.adr)) {
                server.humans = humans;
                server.bots = server.clients - humans;
                Cvar_Set("cl_browserPopulationDirty", "1");
                break;
            }
        }
        probe.address.port = 0;
        return true;
    }
    return tagged;
}
