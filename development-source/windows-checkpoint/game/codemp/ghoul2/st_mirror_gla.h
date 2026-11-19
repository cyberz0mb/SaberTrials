// Include after mdx_format.h. The renderer has already validated the GLA buffer.
#ifndef ST_MIRROR_GLA_H
#define ST_MIRROR_GLA_H
#include "st_mirror.h"
static inline bool ST_MirrorGLAMap(const mdxaHeader_t* header,int map[53]) {
    if(!header || header->numBones!=53)return false;
    const char* names[53];int parents[53];const mdxaSkel_t* bones[53];
    const mdxaSkelOffsets_t* offsets=(const mdxaSkelOffsets_t*)((const unsigned char*)header+sizeof(mdxaHeader_t));
    for(int i=0;i<53;i++){
        bones[i]=(const mdxaSkel_t*)((const unsigned char*)offsets+offsets->offsets[i]);
        names[i]=bones[i]->name;parents[i]=bones[i]->parent;
    }
    if(!ST_BuildMirrorMap(names,parents,53,map))return false;
    // Refuse rigs whose joint positions are not anatomically symmetric. Their
    // hand tags would otherwise disagree with the reflected source hand.
    for(int i=0;i<53;i++)for(int axis=0;axis<3;axis++){
        const float a=bones[i]->BasePoseMat.matrix[axis][3];
        const float b=bones[map[i]]->BasePoseMat.matrix[axis][3]*(axis==0?-1.f:1.f);
        const float d=a-b;if(!(d>-.125f && d<.125f))return false;
    }
    return true;
}
#endif
