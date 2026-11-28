#include "st_browser.h"

#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#define CHECK(expr) do { if (!(expr)) { std::fprintf(stderr, "line %d: %s\n", __LINE__, #expr); return 1; } } while (0)

enum { AS_LOCAL, AS_GLOBAL, AS_FAVORITES, NS_CLIENT, PROTOCOL_VERSION = 26, MAX_PINGREQUESTS = 32, BIG_INFO_STRING = 8192 };
struct netadr_t { unsigned int ip, port; };
struct msg_t { const char *data; int readcount, cursize; };
struct serverInfo_t {
    netadr_t adr;
    int ping, clients, maxClients, humans, bots, populationProbed;
};
static struct {
    serverInfo_t localServers[2], globalServers[64], favoriteServers[2];
    int numlocalservers, numglobalservers, numfavoriteservers;
} cls;

struct Request { netadr_t address; std::string challenge; };
static std::vector<Request> requests;
static unsigned int now;
static bool dirty;

static unsigned int Sys_Milliseconds() { return now; }
static bool NET_CompareAdr(const netadr_t *a, const netadr_t *b) { return a->ip == b->ip && a->port == b->port; }
static void Cvar_Set(const char *, const char *value) { dirty = *value == '1'; }

static void Com_sprintf(char *buffer, size_t size, const char *format, ...)
{
    va_list args;
    va_start(args, format);
    std::vsnprintf(buffer, size, format, args);
    va_end(args);
}

static void Q_strncpyz(char *out, const char *value, size_t capacity)
{
    Com_sprintf(out, capacity, "%s", value);
}

static const char *Info_ValueForKey(const char *info, const char *key)
{
    static std::string values[2];
    static unsigned int next;
    std::string &result = values[next++ % 2];
    result.clear();
    while (*info == '\\') {
        const char *separator = std::strchr(++info, '\\');
        if (!separator)
            break;
        const char *value = separator + 1;
        const char *end = std::strchr(value, '\\');
        if (!end)
            end = value + std::strlen(value);
        if (std::string(info, separator) == key) {
            result.assign(value, end);
            break;
        }
        info = end;
    }
    return result.c_str();
}

static void NET_OutOfBandPrint(int, const netadr_t *address, const char *, const char *challenge)
{
    requests.push_back({*address, challenge});
}

#include "st_browser_population.inc"

static serverInfo_t server(unsigned int port, int occupied, int humans = -1, int ping = 140)
{
    return {{1, port}, ping, occupied, 32, humans, humans < 0 ? -1 : occupied - humans, 0};
}

static bool status(const netadr_t &from, const char *roster, const std::string &challenge = "", bool manual = false,
                   const char *settings = "\\sv_maxclients\\32")
{
    std::string data = "statusResponse\n\\protocol\\26";
    data += settings;
    if (!challenge.empty())
        data += "\\challenge\\" + challenge;
    data += '\n';
    data += roster;
    const msg_t message{data.data(), 15, static_cast<int>(data.size())};
    return CL_BrowserPopulationReply(&from, &message, manual);
}

int main()
{
    auto &list = cls.globalServers;
    const char *mixed = "0 0 \"Bot\"\n0 200 \"Human\"\n";
    const char *bots = "0 0 \"Bot One\"\n0 0 \"Bot Two\"\n";
    const char *humans = "0 25 \"One\"\n0 40 \"Two\"\n";
    now = 100;
    cls.numglobalservers = 8;
    list[0] = server(1000, 2);
    list[1] = server(1001, 2);
    list[2] = server(1002, 2);
    list[3] = server(1003, 2);
    list[4] = server(1004, 3, 2);
    list[5] = server(1005, 0, 0);
    list[6] = server(1006, 99);
    list[7] = server(1007, 2, -1, 0);
    CHECK(CL_BrowserPopulationFrame(AS_GLOBAL, true));
    CHECK(requests.size() == 4);
    CHECK(CL_BrowserPopulationFrame(AS_GLOBAL, false));
    CHECK(requests.size() == 4);
    const netadr_t differentIp{2, list[0].adr.port};
    CHECK(status(differentIp, bots, requests[0].challenge));
    CHECK(status(list[0].adr, bots, "stp-stale"));
    CHECK(!status(list[0].adr, bots, "", true));
    CHECK(list[0].humans == -1 && !dirty);
    CHECK(status(list[0].adr, bots));
    CHECK(list[0].humans == 0 && list[0].bots == 2 && list[0].ping == 140 && dirty);

    now += 1700;
    CHECK(status(list[1].adr, mixed, requests[1].challenge));
    CHECK(status(list[2].adr, humans, requests[2].challenge));
    CHECK(status(list[3].adr, "0 0 \"truncated\"\n", requests[3].challenge));
    CHECK(list[1].humans == 1 && list[2].humans == 2 && list[3].humans == -1);
    CHECK(CL_BrowserPopulationFrame(AS_GLOBAL, false));
    now = 2100;
    CHECK(!CL_BrowserPopulationFrame(AS_GLOBAL, false));
    CHECK(status(list[3].adr, humans, requests[3].challenge));
    CHECK(list[3].humans == -1 && requests.size() == 5);
    CHECK(requests.back().challenge == requests[3].challenge);

    CL_BrowserResetPopulation();
    CHECK(!dirty);
    requests.clear();
    cls.numglobalservers = 40;
    for (int i = 0; i < cls.numglobalservers; ++i)
        list[i] = server(2000 + i, 2);
    CHECK(CL_BrowserPopulationFrame(AS_GLOBAL, true));
    CHECK(requests.size() == MAX_PINGREQUESTS);
    CHECK(CL_BrowserPopulationFrame(AS_GLOBAL, false));
    CHECK(requests.size() == MAX_PINGREQUESTS);
    CHECK(status(list[0].adr, mixed, requests[0].challenge));
    CHECK(CL_BrowserPopulationFrame(AS_GLOBAL, false));
    CHECK(requests.size() == MAX_PINGREQUESTS + 1);
    CHECK(requests.back().address.port == 2032);
    cls.numfavoriteservers = 1;
    cls.favoriteServers[0] = server(2000, 2);
    const std::string prior = requests[0].challenge;
    CHECK(CL_BrowserPopulationFrame(AS_FAVORITES, false));
    CHECK(status(cls.favoriteServers[0].adr, bots, prior));
    CHECK(cls.favoriteServers[0].humans == -1);
    CHECK(status(cls.favoriteServers[0].adr, humans, requests.back().challenge));
    CHECK(cls.favoriteServers[0].humans == 2 && list[0].humans == 1);
    CHECK(!CL_BrowserPopulationFrame(AS_FAVORITES, false));

    std::string botsWithReserved, mixedWithReserved;
    for (int i = 0; i < 20; ++i) {
        botsWithReserved += "0 0 \"Bot\"\n";
        mixedWithReserved += i == 19 ? "2 58 \"Human\"\n" : "0 0 \"Bot\"\n";
    }
    const char *reserved = "\\sv_maxclients\\32\\sv_privateClients\\2";
    requests.clear();
    cls.numglobalservers = 5;
    for (int i = 0; i < cls.numglobalservers; ++i) {
        list[i] = server(3000 + i, 18);
        list[i].maxClients = 30;
    }
    CHECK(CL_BrowserPopulationFrame(AS_GLOBAL, false) && requests.size() == 5);
    CHECK(status(list[0].adr, botsWithReserved.c_str(), requests[0].challenge, false, reserved));
    CHECK(list[0].humans == 0 && list[0].maxClients == 30 && list[0].clients == 18);
    CHECK(status(list[1].adr, botsWithReserved.c_str(), requests[1].challenge));
    CHECK(list[1].humans == 0);
    CHECK(status(list[2].adr, mixedWithReserved.c_str(), requests[2].challenge, false, reserved));
    CHECK(list[2].humans == -1);
    CHECK(status(list[3].adr, botsWithReserved.c_str(), requests[3].challenge, false,
                 "\\sv_maxclients\\32\\sv_privateClients\\1"));
    CHECK(list[3].humans == -1);
    CHECK(status(list[4].adr, (botsWithReserved + "0 0 \"Extra\"\n").c_str(), requests[4].challenge,
                 false, reserved));
    CHECK(list[4].humans == -1);
    CL_BrowserResetPopulation();
    requests.clear();
    cls.numglobalservers = 1;
    list[0] = server(3100, 18);
    list[0].maxClients = 30;
    CHECK(CL_BrowserPopulationFrame(AS_GLOBAL, true));
    now += 1100;
    CHECK(CL_BrowserPopulationFrame(AS_GLOBAL, false) && requests.size() == 2);
    const std::string extended = std::string(reserved) + "\\mod_settings\\" + std::string(1200,'a');
    CHECK(status(list[0].adr, botsWithReserved.c_str(), requests.back().challenge, false, extended.c_str()));
    CHECK(list[0].humans == 0 && list[0].maxClients == 30);
    return 0;
}
