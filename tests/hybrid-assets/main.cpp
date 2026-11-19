// Pure mapping/ABI checks. No game startup, server, rendering or installed writes.
#include <cstdio>
#include <cstdlib>
#include "anims.h"
struct animation_t { unsigned short firstFrame, numFrames; short frameLerp; signed char loopFrames; };
#include "st_hybrid_anims.h"
#include "st_direction_map.h"
#define CHECK(x) do { if(!(x)) { std::fprintf(stderr,"line %d: %s\n",__LINE__,#x); return 1; } } while(0)
int main() {
    const int legacyStarts[3]={BOTH_A1_T__B_,BOTH_A2_T__B_,BOTH_A3_T__B_};
    const int aliasStarts[3]={BOTH_ST_GREEN_A2_T__B_,BOTH_ST_PURPLE_A1_T__B_,BOTH_ST_ORANGE_A3_T__B_};
    const int parents[3]={1,0,2};
    CHECK(BOTH_ST_GREEN_A2_T__B_==BOTH_ST_READY_15+1);
    CHECK(BOTH_ST_PURPLE_A1_T__B_==BOTH_ST_GREEN_D2_B____+1);
    CHECK(BOTH_ST_ORANGE_A3_T__B_==BOTH_ST_PURPLE_D1_B____+1);
    CHECK(MAX_ANIMATIONS<2048);
    for(int style=0;style<3;++style) for(int o=0;o<77;++o) {
        int alias=aliasStarts[style]+o;
        CHECK(STH_AnimStyle(alias)==style+4);
        CHECK(STH_OriginalAnim(alias)==legacyStarts[parents[style]]+o);
        CHECK(STH_AnimForStyle(style+4,alias)==alias);
        CHECK(STH_AnimForStyle(0,alias)==STH_OriginalAnim(alias));
        CHECK(ST_DirectionAnim(ST_DirectionAnim(alias))==alias);
        CHECK(STH_AnimStyle(ST_DirectionAnim(alias))==style+4);
        CHECK(STH_OriginalAnim(ST_DirectionAnim(alias))==ST_DirectionAnim(STH_OriginalAnim(alias)));
        for(int parent=0;parent<3;++parent) {
            CHECK(STH_AnimForStyle(style+4,legacyStarts[parent]+o)==alias);
            CHECK(STH_AnimForStyle(style+4,aliasStarts[parent]+o)==alias);
        }
    }
    for(int anim=0;anim<BOTH_ST_GREEN_A2_T__B_;++anim) {
        CHECK(STH_OriginalAnim(anim)==anim);
        CHECK(STH_AnimStyle(anim)==0);
        CHECK(STH_AnimForStyle(0,anim)==anim);
    }
    CHECK(!STH_AnimationsValid(nullptr));
    animation_t missing[MAX_TOTALANIMATIONS]={};
    CHECK(!STH_AnimationsValid(missing));
    std::puts("Hybrid aliases: 231 mappings, all original IDs, cross-family mapping and missing assets passed.");
    return 0;
}
