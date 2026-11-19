// Include after mdx_format.h. The renderer has already validated the GLA buffer.
#ifndef ST_MIRROR_GLA_H
#define ST_MIRROR_GLA_H
#include "st_mirror.h"
enum { ST_MIRROR_MAX_BONES=128 };
static inline bool ST_MirrorGLAFace(const char* name) {
    const char* names[]={"ceyebrow","jaw","lblip2","leye","rblip2","ltlip2","rtlip2","reye","face"};
    for(unsigned i=0;i<sizeof(names)/sizeof(names[0]);++i)if(!strcmp(name,names[i]))return true;
    return false;
}
// Accessories and expressions keep their authored local motion, following the
// posed body/head. They do not determine whether hands can be exchanged.
static inline bool ST_MirrorGLAReflectBone(const mdxaHeader_t* header,int bone) {
    if(bone<0 || bone>=53)return false;
    const mdxaSkelOffsets_t* offsets=(const mdxaSkelOffsets_t*)((const unsigned char*)header+sizeof(mdxaHeader_t));
    const mdxaSkel_t* skel=(const mdxaSkel_t*)((const unsigned char*)offsets+offsets->offsets[bone]);
    return !ST_MirrorGLAFace(skel->name);
}
template<size_t capacity>
static inline bool ST_MirrorGLAMap(const mdxaHeader_t* header,int (&map)[capacity]) {
    if(!header || header->numBones<53 || header->numBones>ST_MIRROR_MAX_BONES ||
       (size_t)header->numBones>capacity)return false;
    const char* names[53];int parents[53];const mdxaSkel_t* bones[53];
    const mdxaSkelOffsets_t* offsets=(const mdxaSkelOffsets_t*)((const unsigned char*)header+sizeof(mdxaHeader_t));
    for(int i=0;i<53;i++){
        bones[i]=(const mdxaSkel_t*)((const unsigned char*)offsets+offsets->offsets[i]);
        names[i]=bones[i]->name;parents[i]=bones[i]->parent;
    }
    if(!ST_BuildMirrorMap(names,parents,53,map))return false;
    // Refuse rigs whose joint positions are not anatomically symmetric. Their
    // hand tags would otherwise disagree with the reflected source hand.
    for(int i=0;i<53;i++)if(ST_MirrorGLAReflectBone(header,i))for(int axis=0;axis<3;axis++){
        const float a=bones[i]->BasePoseMat.matrix[axis][3];
        const float b=bones[map[i]]->BasePoseMat.matrix[axis][3]*(axis==0?-1.f:1.f);
        const float d=a-b;if(!(d>-.125f && d<.125f))return false;
    }
    // A model may append tail/face/accessory bones, but must retain the complete
    // stock body and a finite, acyclic hierarchy. No core joint is substituted.
    for(int i=53;i<header->numBones;i++) {
        int current=i;
        for(int hop=0;current>=0 && hop<=header->numBones;hop++) {
            if(current>=header->numBones || hop==header->numBones)return false;
            const mdxaSkel_t* skel=(const mdxaSkel_t*)((const unsigned char*)offsets+offsets->offsets[current]);
            current=skel->parent;
            if(current< -1)return false;
        }
        map[i]=i;
    }
    return true;
}
#endif
