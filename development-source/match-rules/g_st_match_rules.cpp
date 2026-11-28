// Keep C++ validation separate from the existing C game translation units.
#include "st_match_server_policy.h"
extern "C" {
#include "g_local.h"
}
#include "g_st_match_rules.inc"
#include "g_st_match_live.inc"
