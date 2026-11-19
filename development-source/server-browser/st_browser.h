#ifndef ST_BROWSER_H
#define ST_BROWSER_H

#include <stddef.h>
#include <stdint.h>
#include <string.h>

enum {
    STB_WORLDWIDE, STB_NORTH_AMERICA, STB_SOUTH_AMERICA, STB_EUROPE,
    STB_RUSSIA, STB_ASIA, STB_OCEANIA, STB_AFRICA, STB_REGION_COUNT
};

typedef struct { unsigned char bytes[6]; } stb_address;
typedef struct {
    int ping, humans, occupied, capacity, game, password, combat, region;
    int min_server_ping, max_server_ping;
} stb_server;
typedef struct {
    int game, region, max_ping, min_humans, password, combat, strict_region;
} stb_filter;

static inline int stb_number(const char *text, int limit)
{
    int result = 0;
    if (!*text)
        return -1;
    while (*text) {
        int digit = *text++ - '0';
        if (digit < 0 || digit > 9 || result > limit / 10 ||
            (result == limit / 10 && digit > limit % 10))
            return -1;
        result = result * 10 + digit;
    }
    return result;
}

static inline int stb_humans(int occupied, const char *value)
{
    if (occupied <= 0)
        return occupied;
    return stb_number(value, occupied);
}

/* The engine's connect command accepts a hostname or IPv4 with optional port. */
static inline int stb_direct_address(const char *text)
{
    int length = 0;
    while ((*text >= 'a' && *text <= 'z') || (*text >= 'A' && *text <= 'Z') ||
           (*text >= '0' && *text <= '9') || *text == '.' || *text == '-') {
        ++text;
        ++length;
    }
    return length > 0 && (!*text || (*text == ':' && stb_number(text + 1, 65535) > 0));
}

/* JKHub can end an intermediate datagram immediately after the last port.
 * JK2MV can put a newline after the header and uses a short EOT marker. */
static inline int stb_parse_master(const unsigned char *data, size_t length,
                                   stb_address *out, int capacity)
{
    static const char prefix[] = "\xff\xff\xff\xff" "getserversResponse";
    size_t offset = sizeof(prefix) - 1;
    int count = 0;
    if (length <= offset || memcmp(data, prefix, offset))
        return -1;
    if (data[offset] == '\r')
        ++offset;
    if (offset < length && data[offset] == '\n')
        ++offset;
    if (offset == length)
        return -1;
    while (offset < length) {
        int i;
        size_t remaining = length - offset;
        if (data[offset++] != '\\')
            return -1;
        if (remaining >= 4 && remaining <= 7 && !memcmp(data + offset, "EOT", 3)) {
            size_t tail = offset + 3;
            while (tail < length && !data[tail])
                ++tail;
            if (tail == length)
                return count;
        }
        if (remaining < 7)
            return -1;
        for (i = 0; i < count; ++i)
            if (!memcmp(out[i].bytes, data + offset, 6))
                break;
        if (i == count && count < capacity &&
            (data[offset + 4] || data[offset + 5]))
            memcpy(out[count++].bytes, data + offset, 6);
        offset += 6;
    }
    return count;
}

static inline int stb_waiting(int now, int deadline)
{
    return deadline != 0 && now < deadline;
}

static inline int stb_ping_budget(int browser, int manual)
{
    return browser ? 2000 : (manual < 100 ? 100 : manual);
}

static inline int stb_allocation(const stb_server *server)
{
    return server->capacity > 0 && server->occupied >= 0 &&
        server->occupied <= server->capacity ? server->capacity - server->occupied : -1;
}

static inline int stb_matches(const stb_server *s, const stb_filter *f, int joining)
{
    if (f->game >= 0 && s->game != f->game)
        return 0;
    if (f->region && f->strict_region && s->region != f->region)
        return 0;
    if (f->max_ping && (s->ping <= 0 || s->ping > f->max_ping))
        return 0;
    if (f->min_humans && s->humans < f->min_humans)
        return 0;
    if (f->password >= 0 && s->password != f->password)
        return 0;
    if (f->combat >= 0 && s->combat != f->combat)
        return 0;
    return !joining || (s->ping > 0 && stb_allocation(s) > 0 && s->password >= 0 &&
        (!s->min_server_ping || s->ping >= s->min_server_ping) &&
        (!s->max_server_ping || s->ping <= s->max_server_ping));
}

static inline int stb_better(const stb_server *a, const stb_server *b, int region)
{
    if (a->ping != b->ping)
        return a->ping < b->ping;
    if (stb_allocation(a) != stb_allocation(b))
        return stb_allocation(a) > stb_allocation(b);
    if (a->humans != b->humans)
        return a->humans > b->humans;
    return region && a->region == region && b->region != region;
}

static inline uint32_t stb_ipv4(const unsigned char *data)
{
    return ((uint32_t)data[0] << 24) | ((uint32_t)data[1] << 16) |
        ((uint32_t)data[2] << 8) | data[3];
}

/* Sorted nine-byte records: first IPv4, last IPv4, browser region. */
static inline int stb_region(const unsigned char *data, int count, uint32_t address)
{
    int low = 0;
    while (low < count) {
        int mid = low + (count - low) / 2;
        const unsigned char *row = data + mid * 9;
        if (address < stb_ipv4(row))
            count = mid;
        else if (address > stb_ipv4(row + 4))
            low = mid + 1;
        else
            return row[8] < STB_REGION_COUNT ? row[8] : STB_WORLDWIDE;
    }
    return STB_WORLDWIDE;
}
#endif
