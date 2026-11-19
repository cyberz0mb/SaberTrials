#include "qcommon/qcommon.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>

#define CHECK(condition) do { \
    if (!(condition)) { std::fprintf(stderr, "Failed at line %d: %s\n", __LINE__, #condition); return EXIT_FAILURE; } \
} while (false)

int main() {
    byte buffer[2048] = {};
    msg_t packet = {};
    packet.data = buffer;
    packet.maxsize = sizeof(buffer);
    constexpr int offset = 12;
    const char userinfo[] = "\"\\protocol\\26\\qport\\55673\\challenge\\1234123412"
        "\\name\\GuardTester\\model\\kyle/default\\saber1\\single_1\\saber2\\none"
        "\\rate\\25000\\snaps\\40\\forcepowers\\7-1-032330000000001333"
        "\\password\\S3y@2YlZNq8RdK5xPQ1M\"";
    const size_t userinfoSize = sizeof(userinfo) - 1;
    std::memcpy(buffer + offset, userinfo, userinfoSize);
    packet.cursize = offset + userinfoSize;
    Huff_Compress(&packet, offset);
    const int encodedSize = packet.cursize;
    byte encoded[sizeof(buffer)];
    std::memcpy(encoded, buffer, encodedSize);
    CHECK(Huff_Decompress(&packet, offset));
    CHECK(packet.cursize == offset + userinfoSize);
    CHECK(std::memcmp(buffer + offset, userinfo, userinfoSize) == 0);

    for (int size = offset; size < encodedSize - 1; ++size) {
        std::memcpy(buffer, encoded, encodedSize);
        packet.cursize = size;
        CHECK(!Huff_Decompress(&packet, offset));
        CHECK(packet.cursize == size);
    }
    std::memcpy(buffer, encoded, encodedSize);
    packet.cursize = encodedSize;
    buffer[offset] = 255;
    CHECK(!Huff_Decompress(&packet, offset));
}
