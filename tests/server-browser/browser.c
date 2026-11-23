#include "st_browser.h"
#include <stdio.h>
#include <string.h>

#define CHECK(expr) do { if (!(expr)) { fprintf(stderr, "line %d: %s\n", __LINE__, #expr); return 1; } } while (0)

int main(void)
{
    static const unsigned char packet[] =
        "\xff\xff\xff\xff" "getserversResponse\n"
        "\\" "\x01\x02\x03\x04\x71\x8e"
        "\\" "\x01\x02\x03\x04\x71\x8e"
        "\\" "\x01\x02\x03\x04\x71\x8f" "\\EOT";
    static const unsigned char split[] =
        "\xff\xff\xff\xff" "getserversResponse\\"
        "\x11\x22\x33\x44\x71\x8e";
    stb_address addresses[8];
    stb_filter filter = {-1, 0, 0, 0, -1, -1, 0};
    stb_server server = {760, 5, 15, 32, 3, 0, 1, STB_EUROPE, 0, 0};
    stb_server slower = {920, 25, 25, 32, 3, 0, 1, STB_NORTH_AMERICA, 0, 0};
    unsigned char ranges[] = {0,0,0,10, 0,0,0,20,STB_RUSSIA,
                              0,0,0,25, 0,0,0,30,STB_ASIA};

    CHECK(stb_parse_master(packet, sizeof(packet)-1, addresses, 8) == 2);
    CHECK(addresses[0].bytes[5] == 0x8e && addresses[1].bytes[5] == 0x8f);
    CHECK(stb_parse_master(split, sizeof(split)-1, addresses, 8) == 1);
    CHECK(stb_parse_master(split, sizeof(split)-2, addresses, 8) == -1);
    CHECK(stb_parse_master(packet+1, sizeof(packet)-2, addresses, 8) == -1);
    CHECK(stb_waiting(100, 1000) && !stb_waiting(1000, 1000));
    CHECK(!stb_waiting(100, 0));
    CHECK(stb_ping_budget(3000, 20) == 2000);
    CHECK(stb_ping_budget(0, 450) == 450);
    CHECK(stb_humans(15, "5") == 5 && stb_humans(15, "") == -1);
    CHECK(stb_humans(0, "") == 0 && stb_humans(15, "16") == -1);
    CHECK(stb_humans(15, "5bots") == -1 && stb_humans(15, "-1") == -1);
    CHECK(stb_humans_from_counts(6, "", "6") == 0);
    CHECK(stb_humans_from_counts(6, "", "4") == 2);
    CHECK(stb_humans_from_counts(6, "1", "6") == 1);
    CHECK(stb_humans_from_counts(6, "invalid", "6") == 0);
    CHECK(stb_humans_from_counts(6, "", "") == -1);
    CHECK(stb_humans_from_counts(6, "", "7") == -1);
    CHECK(stb_humans_from_counts(6, "", "-1") == -1);
    CHECK(stb_humans_from_counts(0, "", "") == 0);
    CHECK(stb_number("9999999999999999999", 64) == -1);
    CHECK(stb_number("5", 1) == -1);
    CHECK(stb_direct_address("127.0.0.1:29070") && stb_direct_address("jka.example.com"));
    CHECK(!stb_direct_address("server;quit") && !stb_direct_address("server:65536"));
    CHECK(stb_region(ranges, 2, 20) == STB_RUSSIA && stb_region(ranges, 2, 24) == 0);
    CHECK(stb_region(ranges, 2, 25) == STB_ASIA);

    CHECK(stb_matches(&server, &filter, 1));
    CHECK(stb_better(&server, &slower, STB_NORTH_AMERICA));
    filter.region = STB_NORTH_AMERICA;
    CHECK(stb_matches(&server, &filter, 1));  /* Preference can fall back worldwide. */
    filter.strict_region = 1;
    CHECK(!stb_matches(&server, &filter, 1) && stb_matches(&slower, &filter, 1));
    filter.strict_region = 0;
    filter.max_ping = 500;
    CHECK(!stb_matches(&server, &filter, 1));
    filter.max_ping = 0;
    filter.min_humans = 6;
    CHECK(!stb_matches(&server, &filter, 1));
    filter.min_humans = 0;
    filter.game = 8;
    CHECK(!stb_matches(&server, &filter, 1));
    filter.game = -1;
    filter.combat = 0;
    CHECK(!stb_matches(&server, &filter, 1));
    filter.combat = -1;
    filter.password = 0;
    server.password = -1;
    CHECK(!stb_matches(&server, &filter, 1));
    filter.password = -1;
    CHECK(!stb_matches(&server, &filter, 1));
    server.password = 1;
    CHECK(stb_matches(&server, &filter, 1));
    server.max_server_ping = 700;
    CHECK(!stb_matches(&server, &filter, 1));
    server.max_server_ping = 0;
    server.occupied = 32;
    CHECK(!stb_matches(&server, &filter, 1) && stb_matches(&server, &filter, 0));
    server.occupied = 15;
    server.ping = 0;
    CHECK(!stb_matches(&server, &filter, 1) && stb_matches(&server, &filter, 0));
    return 0;
}
