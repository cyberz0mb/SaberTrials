/* Generated from the hash-locked ready-pose library; no combat replacements. */
#ifndef ST_STANCE_RUNTIME_H
#define ST_STANCE_RUNTIME_H
#include "st_stance_policy.h"
static int ST_IsReadyPose(int anim) {return anim>=BOTH_ST_READY_01 && anim<=BOTH_ST_READY_15;}
static int ST_StanceLibraryValid(const animation_t* anims) {
    static const int expected[15][4]={
    {22374,1,50,0},
    {22375,1,17,-1},
    {22376,1,17,-1},
    {22377,2,17,-1},
    {22379,1,17,-1},
    {22380,1,50,-1},
    {22381,4,34,-1},
    {22385,12,34,-1},
    {22397,15,17,-1},
    {22412,21,50,-1},
    {22433,1,50,-1},
    {22434,4,34,-1},
    {22438,1,50,-1},
    {22439,2,50,-1},
    {22441,2,1000,0},
    };
    int i;
    if(!anims)return 0;
    for(i=0;i<15;i++) {
        const animation_t* a=&anims[BOTH_ST_READY_01+i];
        if(a->firstFrame!=expected[i][0] || a->numFrames!=expected[i][1] ||
           a->frameLerp!=expected[i][2] || a->loopFrames!=expected[i][3])return 0;
    }
    return 1;
}
#endif
