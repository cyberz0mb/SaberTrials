// Saber Trials pose reflection. Skin geometry, weights and materials stay intact.
#ifndef ST_MIRROR_H
#define ST_MIRROR_H
#include <stddef.h>
#include <string.h>

static inline void ST_MirrorMatrix(const float source[3][4], float dest[3][4]) {
    // GLA's anatomical lateral axis is X. S * deformation * S preserves an
    // ordinary rotation (positive determinant), unlike a negative mesh scale.
    // This also works in-place: each output depends on the same input element.
    int row, column;
    for(row=0;row<3;row++) for(column=0;column<4;column++)
        dest[row][column]=source[row][column]*((row==0)?-1.0f:1.0f)
            *((column==0)?-1.0f:1.0f);
}

static inline int ST_MirrorBoneName(const char* name, char* other, size_t size) {
    static const char* const suffixes[]={
        "femurYZ","femurX","tibia","talus","clavical","humerus","humerusX",
        "radius","radiusX","hand","_d1_j1","_d1_j2","_d2_j1","_d2_j2",
        "_d4_j1","_d4_j2","hang_tag_bone","tail","blip2","tlip2","eye"
    };
    size_t i;
    if(!name || !other || !size) return 0;
    other[0]=0;
    if(name[0]!='l' && name[0]!='r') return 0;
    for(i=0;i<sizeof(suffixes)/sizeof(suffixes[0]);i++) {
        if(!strcmp(name+1,suffixes[i]) && strlen(name)<size) {
            strcpy(other,name);other[0]=(name[0]=='l')?'r':'l';return 1;
        }
    }
    return 0;
}

// Accept only the complete JA humanoid anatomy. A partially understood rig
// must never produce half a mirrored skeleton and mismatched saber collision.
static inline int ST_BuildMirrorMap(const char* const* names, const int* parents,
                                   int count, int* map) {
    static const char* const central[]={"model_root","pelvis","Motion",
        "lower_lumbar","upper_lumbar","thoracic","cervical","cranium",
        "ceyebrow","jaw","face"};
    int i,j;size_t c;char pair[64];
    if(count!=53) return 0;
    for(i=0;i<count;i++) {
        map[i]=-1;
        if(!names[i] || parents[i]>=count || parents[i]<-1) return 0;
        for(j=0;j<i;j++) if(!strcmp(names[i],names[j])) return 0;
        if(ST_MirrorBoneName(names[i],pair,sizeof(pair))) {
            for(j=0;j<count;j++) if(names[j]&&!strcmp(pair,names[j])) {map[i]=j;break;}
        } else {
            for(c=0;c<sizeof(central)/sizeof(central[0]);c++)
                if(!strcmp(names[i],central[c])) {map[i]=i;break;}
        }
        if(map[i]<0) return 0;
    }
    for(i=0;i<count;i++) {
        if(map[map[i]]!=i) return 0;
        if(parents[i]<0) {
            if(strcmp(names[i],"model_root") || parents[map[i]]!=-1) return 0;
        } else if(parents[map[i]]!=map[parents[i]]) return 0;
        // Verify ancestry terminates (no malformed cycles).
        j=i;
        for(c=0;c<(size_t)count && j>=0;c++) j=parents[j];
        if(j>=0) return 0;
    }
    return 1;
}
#endif
