#include "st_bsp_validate.h"
#include <cstdio>
#include <fstream>
#include <vector>

int main(int argc, char **argv) {
    if (argc < 2) {
        std::fprintf(stderr, "Usage: st-bsp-check MAP.bsp [...]\n");
        return 2;
    }
    int failures = 0;
    for (int i = 1; i < argc; ++i) {
        std::ifstream input(argv[i], std::ios::binary | std::ios::ate);
        const auto size = input.tellg();
        if (size < 0 || size > st_bsp::maxFileBytes) {
            std::fprintf(stderr, "%s: missing or exceeds BSP file capacity\n", argv[i]);
            ++failures;
            continue;
        }
        std::vector<byte> data(static_cast<size_t>(size));
        input.seekg(0);
        input.read(reinterpret_cast<char *>(data.data()), size);
        int version = 0;
        const char *error = input ? st_bsp::Validate(data.data(), static_cast<int>(size), version) : "short BSP read";
        if (error) {
            std::fprintf(stderr, "%s: %s\n", argv[i], error);
            ++failures;
        } else {
            std::printf("%s: valid RBSP %d (%lld bytes)\n", argv[i], version, static_cast<long long>(size));
        }
    }
    return failures ? 1 : 0;
}
