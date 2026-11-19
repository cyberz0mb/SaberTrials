#include "../../development-source/staff/codemp/server/st_guard_traffic.h"
#include <cstdlib>
#include <limits>

static void Check(bool condition) {
    if (!condition) std::abort();
}

int main() {
    STGuardBucket bucket = {};
    for (int i = 0; i < 32; ++i) Check(!ST_GuardBlocked(bucket, 32, 0));
    Check(ST_GuardBlocked(bucket, 32, 0));
    Check(ST_GuardBlocked(bucket, 32, 31));
    Check(!ST_GuardBlocked(bucket, 32, 32));
    Check(ST_GuardBlocked(bucket, 32, 32));
    Check(!ST_GuardBlocked(bucket, 32, 1032));

    STGuardBucket disabled = {};
    for (int i = 0; i < 100; ++i) Check(!ST_GuardBlocked(disabled, 0, 0));
    Check(!ST_GuardBlocked(disabled, 1, 0));
    Check(ST_GuardBlocked(disabled, 1, 0));

    STGuardBucket wrap = {};
    Check(!ST_GuardBlocked(wrap, 2, std::numeric_limits<uint32_t>::max() - 100));
    Check(!ST_GuardBlocked(wrap, 2, 100));
    Check(ST_GuardBlocked(wrap, 2, 100));
    Check(!ST_GuardBlocked(wrap, 2, 399));
}
