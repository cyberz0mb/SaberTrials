#include "st_staff_game_api.h"
#include "check.h"
static int execute(const STVerifiedAction*, STGameResult*) { return 1; }
static int resolve(const char*, STTargetRef*) { return 1; }
static void revoke(const char*,int) {}
static void reset() {}
RUN_TEST(
    STGameAPI api = {};
    CHECK(!ST_ValidGameAPI(&api));
    api.version = ST_STAFF_API_VERSION;
    api.size = sizeof(api);
    api.Execute = execute; api.ResolveTarget = resolve; api.Revoke = revoke;
    CHECK(!ST_ValidGameAPI(&api));
    api.ResetSessions = reset;
    CHECK(ST_ValidGameAPI(&api));
    api.version++;
    CHECK(!ST_ValidGameAPI(&api));
)
