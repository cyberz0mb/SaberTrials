#include "qcommon/q_shared.h"
#define MDXABONEDEF
#include "rd-common/mdx_format.h"
#include "st_mirror_gla.h"
#include "st_gla_compat.h"
#include "rd-common/st_glm_validate.h"
#include "renderer_budget.h"
#include <cstdio>
#include <fstream>
#include <iterator>
#include <stdexcept>
using Bytes=std::vector<unsigned char>;
static void check(bool ok,const char *reason) {if(!ok)throw std::runtime_error(reason);}
static Bytes read(const char *path) {
    std::ifstream f(path,std::ios::binary);check(bool(f),"fixture missing");
    return Bytes(std::istreambuf_iterator<char>(f),std::istreambuf_iterator<char>());
}
int main(int argc,char **argv) {try {
    check(argc>=3,"expected test and model");auto a=read(argv[2]);
    if(!strcmp(argv[1],"mesh")) {
        const char *error=st_glm::validate(a.data(),a.size(),MAX_G2_BONES);
        check(!error,error?error:"Alien mesh rejected by Rend2");
        st_gla_compat::put32(a.data()+140,MAX_G2_BONES+1);
        check(st_glm::validate(a.data(),a.size(),MAX_G2_BONES)!=NULL,"over-budget mesh accepted");
        puts("PASS real Alien mesh and renderer palette boundary");return 0;
    }
    if(!strcmp(argv[1],"mirror")) {
        int map[128];auto h=(const mdxaHeader_t*)a.data();
        check(ST_MirrorGLAMap(h,map),"compatible humanoid body rejected for left hand");
        check(ST_MirrorGLAReflectBone(h,29),"hand motion must be reflected");
        for(int bone=0;bone<h->numBones;++bone) {
            auto offset=100+st_gla_compat::u32(a.data()+100+bone*4);
            if(bone>=53 || ST_MirrorGLAFace((const char*)a.data()+offset))
                check(!ST_MirrorGLAReflectBone(h,bone),"private accessory/expression motion reflected");
        }
        // Rejection must still protect actual limb/hand asymmetry.
        auto bad=a;int at=100+st_gla_compat::u32(bad.data()+100+29*4)+72+12;
        float x=19;memcpy(bad.data()+at,&x,4);
        check(!ST_MirrorGLAMap((const mdxaHeader_t*)bad.data(),map),"asymmetric hand was accepted");
        puts("PASS compatible body and invalid hand rejection");return 0;
    }
    auto c=read(argv[3]);Bytes out;
    if(!strcmp(argv[1],"incompatible")) {
        check(st_gla_compat::extend(a.data(),a.size(),c.data(),c.size(),out)==st_gla_compat::incompatible,
              "different limb bind must retain its own animation set");
        check(out.empty(),"incompatible model was altered");
        puts("PASS incompatible limb rig left intact");return 0;
    }
    check(st_gla_compat::extend(a.data(),a.size(),c.data(),c.size(),out)==st_gla_compat::extended,
          "compatible private model did not receive stance frames");
    // Compare bytes independently of the compatibility reader: private bones,
    // original frame indices, compressed poses and expressions must survive.
    auto u=st_gla_compat::u32;
    size_t frames=u(a.data()+76),bones=u(a.data()+84),fo=u(a.data()+80),pool=u(a.data()+88);
    size_t newPool=u(out.data()+88);
    check(u(out.data()+76)==22443 && u(out.data()+84)==bones,"wrong extended frame/bone count");
    check(!memcmp(a.data()+100,out.data()+100,fo-100),"private skeleton changed");
    check(!memcmp(a.data()+fo,out.data()+fo,frames*bones*3),"authored animation changed");
    check(!memcmp(a.data()+pool,out.data()+newPool,a.size()-pool),"private compressed poses changed");
    for(size_t i=fo;i<newPool;i+=3)
        check(newPool+st_gla_compat::u24(out.data()+i)*14+14<=out.size(),"invalid extended pose index");
    for(size_t f=frames;f<22443;++f)for(size_t b=53;b<bones;++b)
        check(!memcmp(out.data()+fo+(f*bones+b)*3,a.data()+fo+(15068*bones+b)*3,3),
              "appended pose lost the model's standing accessory motion");
    printf("PASS extension preserves %zu bones and %zu authored frames\n",bones,frames);
    return 0;
}catch(const std::exception &e){fprintf(stderr,"FAIL: %s\n",e.what());return 1;}}
