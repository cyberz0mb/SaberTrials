#pragma once

#include <stdint.h>

struct STGuardBucket {
    uint32_t debt;
    uint32_t lastMs;
};

// The bucket can hold one second of traffic. Each request costs 1000 units.
inline bool ST_GuardBlocked(STGuardBucket &bucket, unsigned rate, uint32_t now) {
    if (!rate) {
        bucket.debt = 0;
        return false;
    }
    const uint32_t elapsed = now - bucket.lastMs;
    bucket.lastMs = now;
    const unsigned recovered = elapsed >= 1000 ? bucket.debt : elapsed * rate;
    bucket.debt = recovered >= bucket.debt ? 0 : bucket.debt - recovered;
    if (bucket.debt > (rate - 1) * 1000) {
        return true;
    }
    bucket.debt += 1000;
    return false;
}

enum STGuardDrop {
    ST_GUARD_JOIN_RATE,
    ST_GUARD_RELIABLE_RATE,
    ST_GUARD_MALFORMED_CONNECT,
    ST_GUARD_SOURCE_LIMIT,
    ST_GUARD_DROP_COUNT
};

void SV_GuardCountDrop(STGuardDrop reason);
