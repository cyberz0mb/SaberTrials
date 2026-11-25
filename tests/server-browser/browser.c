#include "st_browser.h"
#include <stdio.h>
#include <string.h>

#define CHECK(expr) do { if (!(expr)) { fprintf(stderr, "line %d: %s\n", __LINE__, #expr); return 1; } } while (0)
#define STATUS(rows, occupied) stb_status_humans(rows, sizeof(rows) - 1, occupied, 0)
#define RESERVED_STATUS(rows, occupied, reserved) stb_status_humans(rows, sizeof(rows) - 1, occupied, reserved)

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
    CHECK(stb_valid_occupancy(13, 32) && stb_valid_occupancy(0, 32));
    CHECK(!stb_valid_occupancy(33, 32) && !stb_valid_occupancy(-1, 32));
    CHECK(!stb_valid_occupancy(0, -1));
    CHECK(stb_humans_from_counts(13, "3", "0") == 3);
    CHECK(stb_humans_from_counts(13, "invalid", "10") == 3);
    CHECK(stb_humans_from_counts(10, "", "10") == 0);
    CHECK(stb_humans_from_counts(9, "", "0") == 9);
    CHECK(stb_humans_from_counts(9, "", "10") == -1);
    CHECK(stb_humans_from_counts(9, "", "-1") == -1);
    CHECK(stb_humans_from_counts(9, "", "") == -1);
    CHECK(stb_humans_from_counts(0, "", "") == 0);
    CHECK(stb_humans_from_counts(-1, "0", "0") == -1);
    CHECK(STATUS("0 0 \"Bot One\"\n0 0 \"Bot Two\"\n", 2) == 0);
    CHECK(STATUS("-2 0 \"^1Bot\"\r\n10 850 \"Player Two\"\r\n\0", 2) == 1);
    CHECK(STATUS("0 1 \"First\"\n1 55 \"Second\"\n\n", 2) == 2);
    CHECK(STATUS("", 0) == 0 && STATUS("", 2) == -1);
    CHECK(STATUS("0 0 \"Bot\"\n", 2) == -1);
    CHECK(STATUS("0 0 \"Bot\"\n1 20 \"Extra\"\n", 1) == -1);
    CHECK(RESERVED_STATUS("0 0 \"Bot\"\n0 0 \"Extra bot\"\n", 1, 1) == 0);
    CHECK(RESERVED_STATUS("0 5 \"Human\"\n0 7 \"Extra human\"\n", 1, 1) == 1);
    CHECK(RESERVED_STATUS("0 0 \"Bot\"\n0 7 \"Extra human\"\n", 1, 1) == -1);
    CHECK(RESERVED_STATUS("0 0 \"Bot\"\n0 0 \"Extra bot\"\n", 3, 1) == -1);
    CHECK(STATUS("0 0 \"Bot\"", 1) == -1);
    CHECK(STATUS("0 -1 \"Connecting\"\n", 1) == -1);
    CHECK(STATUS("0 12345678901 \"Overflow\"\n", 1) == -1);
    CHECK(STATUS("invalid 0 \"Bot\"\n", 1) == -1);
    CHECK(STATUS("0 0 \"Broken\n", 1) == -1);
    CHECK(STATUS("0 0 \"Embedded\0NUL\"\n", 1) == -1);
    CHECK(stb_number("9999999999999999999", 64) == -1);
    CHECK(stb_number("5", 1) == -1);
    CHECK(stb_direct_address("127.0.0.1:29070") && stb_direct_address("jka.example.com"));
    CHECK(!stb_direct_address("server;quit") && !stb_direct_address("server:65536"));
    CHECK(stb_region(ranges, 2, 20) == STB_RUSSIA && stb_region(ranges, 2, 24) == 0);
    CHECK(stb_region(ranges, 2, 25) == STB_ASIA);
    CHECK(stb_compare_regions(STB_EUROPE, STB_RUSSIA, 0) == -1);
    CHECK(stb_compare_regions(STB_EUROPE, STB_RUSSIA, 1) == 1);
    CHECK(stb_compare_regions(STB_WORLDWIDE, STB_EUROPE, 0) == 1);
    CHECK(stb_compare_regions(STB_WORLDWIDE, STB_EUROPE, 1) == 1);
    CHECK(stb_compare_regions(STB_ASIA, STB_ASIA, 1) == 0);

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
