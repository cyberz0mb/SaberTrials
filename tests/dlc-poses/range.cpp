#include "qcommon/q_shared.h"
#define MDXABONEDEF
#include "rd-common/mdx_format.h"
#include "st_mirror_gla.h"
#include <vector>
#include <cstdio>
#define BONE_ANIM_MIRROR 0x40000000
#define BONE_ANIM_BLEND 0x80
#define GHOUL2_RAG_STARTED 1
#define _PLEASE_SHUT_THE_HELL_UP
struct CGhoul2Info {mdxaHeader_t *aHeader;int mFlags,mSkelFrameNum,mBlist;};
using CGhoul2Info_v=std::vector<CGhoul2Info>;
static int writes=0;
qboolean G2_SetupModelPointers(CGhoul2Info*) {return qtrue;}
qboolean G2_Get_Bone_Anim(CGhoul2Info*,int,const char*,int,float*,int*,int*,int*,float*,int*,int) {return qfalse;}
qboolean G2_Set_Bone_Anim(CGhoul2Info*,int,const char*,int,int,int,float,int,float,int) {++writes;return qtrue;}
#include "setter.inc"
int main() {
    mdxaHeader_t h={};h.numFrames=21376;
    CGhoul2Info_v g(1);g[0].aHeader=&h;
    if(G2API_SetBoneAnim(g,0,"model_root",22374,22375,0,1,100,-1,0) || writes) {
        puts("FAIL: missing stance frames were accepted and replaced the valid pose");return 1;
    }
    if(!G2API_SetBoneAnim(g,0,"model_root",15068,15070,0,1,100,-1,0) || writes!=1) {
        puts("FAIL: normal stock animation was rejected");return 1;
    }
    puts("PASS: missing frames leave the existing pose untouched");return 0;
}
