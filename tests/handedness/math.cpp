#include "st_mirror.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

static void require(bool ok, const char* what) {
    if (!ok) { std::fprintf(stderr, "FAIL: %s\n", what); std::exit(1); }
}
static bool near(float a, float b) { return std::fabs(a-b)<0.00001f; }
static void product(const float a[3][4],const float b[3][4],float out[3][4]) {
    for(int i=0;i<3;i++) for(int j=0;j<4;j++) {
        out[i][j]=(j==3)?a[i][3]:0;
        for(int k=0;k<3;k++) out[i][j]+=a[i][k]*b[k][j];
    }
}
static void same(const float a[3][4],const float b[3][4],const char* why) {
    for(int i=0;i<3;i++) for(int j=0;j<4;j++) require(near(a[i][j],b[i][j]),why);
}
int main() {
    const float identity[3][4]={{1,0,0,0},{0,1,0,0},{0,0,1,0}};
    const float pose[3][4]={{0,-1,0,13},{1,0,0,7},{0,0,1,2}};
    float mirror[3][4],twice[3][4];
    ST_MirrorMatrix(identity,mirror);same(identity,mirror,"rest skin deformation stays identity");
    ST_MirrorMatrix(pose,mirror);ST_MirrorMatrix(mirror,twice);same(pose,twice,"reflection is an involution");
    require(near(mirror[0][3],-13)&&near(mirror[1][3],7)&&near(mirror[2][3],2),"only anatomical lateral translation flips");
    require(near(mirror[0][1],1)&&near(mirror[1][0],-1),"rotation reflected without changing handedness of matrix");
    float child[3][4]={{1,0,0,-3},{0,0,-1,5},{0,1,0,9}};
    float composed[3][4],expected[3][4],childMirror[3][4],actual[3][4];
    product(pose,child,composed);ST_MirrorMatrix(composed,expected);
    ST_MirrorMatrix(child,childMirror);product(mirror,childMirror,actual);
    same(expected,actual,"mirrored local hierarchy equals mirrored global deformation");
    char other[64];
    require(ST_MirrorBoneName("rhand",other,sizeof(other))&&!std::strcmp(other,"lhand"),"anatomical hand pair");
    require(ST_MirrorBoneName("l_d4_j2",other,sizeof(other))&&!std::strcmp(other,"r_d4_j2"),"finger pair");
    require(!ST_MirrorBoneName("lower_lumbar",other,sizeof(other)),"central lumbar is never guessed as a left bone");
    require(!ST_MirrorBoneName("root",other,sizeof(other)),"root is central");
    require(!ST_MirrorBoneName("custom_left_socket",other,sizeof(other)),"unknown rigs must be explicitly supported");
    std::puts("PASS: mirror mathematics and anatomical names");
}
