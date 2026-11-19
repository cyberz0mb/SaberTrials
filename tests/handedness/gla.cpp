// Read-only regression against the user's local game animation data.
#include "qcommon/q_shared.h"
#define MDXABONEDEF
#include "rd-common/mdx_format.h"
#include "st_mirror_gla.h"
#include <array>
#include <vector>
#include <fstream>
#include <iostream>
#include <cmath>
#include <stdexcept>
#include <cstdint>
#include <functional>
typedef std::array<std::array<float,4>,3> Matrix;
static void check(bool v,const char* m){if(!v)throw std::runtime_error(m);}
static Matrix product(const Matrix&a,const Matrix&b){
    Matrix out={};for(int i=0;i<3;i++)for(int j=0;j<4;j++){
        out[i][j]=j==3?a[i][3]:0;
        for(int k=0;k<3;k++)out[i][j]+=a[i][k]*b[k][j];
    }return out;
}
static Matrix reflect(const Matrix&a){Matrix b;ST_MirrorMatrix((const float(*)[4])a.data(),(float(*)[4])b.data());return b;}
static Matrix decode(const unsigned char* b){
    uint16_t v[7];memcpy(v,b,sizeof(v));
    const float w=v[0]/16383.f-2.f,x=v[1]/16383.f-2.f,y=v[2]/16383.f-2.f,z=v[3]/16383.f-2.f;
    return {{{{1-2*(y*y+z*z),2*(x*y-w*z),2*(x*z+w*y),v[4]/64.f-512.f}},
             {{2*(x*y+w*z),1-2*(x*x+z*z),2*(y*z-w*x),v[5]/64.f-512.f}},
             {{2*(x*z-w*y),2*(y*z+w*x),1-2*(x*x+y*y),v[6]/64.f-512.f}}}};
}
int main(int argc,char**argv){try{
    check(argc==2,"expected GLA path");std::ifstream f(argv[1],std::ios::binary);
    check(bool(f),"missing local GLA fixture");
    std::vector<unsigned char>b((std::istreambuf_iterator<char>(f)),{});
    auto integer=[&](size_t at){check(at+4<=b.size(),"truncated GLA");int v;memcpy(&v,&b[at],4);return v;};
    check(b.size()>100,"header missing");const int frames=integer(76),frameOffset=integer(80),count=integer(84),pool=integer(88);
    check(count==53&&frames>100&&integer(96)==int(b.size()),"unexpected fixture header");
    const char*names[53];int parents[53],pairs[53];Matrix bind[53];
    for(int i=0;i<count;i++){
        size_t at=100+integer(100+4*i);check(at+172<=b.size(),"invalid bone offset");
        names[i]=(const char*)&b[at];check(memchr(names[i],0,64)!=nullptr,"unterminated name");
        parents[i]=integer(at+68);memcpy(bind[i].data(),&b[at+72],48);
    }
    check(ST_BuildMirrorMap(names,parents,count,pairs),"real humanoid anatomy rejected");
    check(ST_MirrorGLAMap((const mdxaHeader_t*)b.data(),pairs),"real renderer capability validation rejected humanoid");
    std::vector<unsigned char> asymmetric=b;
    float offset=19;size_t handBaseX=100+integer(100+4*29)+72+12;
    memcpy(&asymmetric[handBaseX],&offset,4);
    int invalidPairs[53];
    check(!ST_MirrorGLAMap((const mdxaHeader_t*)asymmetric.data(),invalidPairs),"asymmetric joint layout was accepted");
    int altered[53];memcpy(altered,parents,sizeof(altered));altered[29]=0;
    int unused[53];check(!ST_BuildMirrorMap(names,altered,count,unused),"mismatched parent pairing accepted");
    check(!ST_BuildMirrorMap(names,parents,52,unused),"incomplete rig accepted");
    // Evaluate every animation frame and all bones. No mesh reflection is used.
    float worst=0;
    for(int frame=0;frame<frames;frame++){
        Matrix local[53],original[53],mirrored[53];
        for(int i=0;i<count;i++){
            size_t off=frameOffset+3*(size_t(frame)*count+i);check(off+3<=b.size(),"frame outside file");
            size_t index=b[off]|(b[off+1]<<8)|(b[off+2]<<16);size_t mat=pool+14*index;
            check(mat+14<=b.size(),"bone pool outside file");local[i]=decode(&b[mat]);
        }
        bool done[53]={};
        std::function<void(int)> evaluate=[&](int i){
            if(done[i])return;
            if(parents[i]>=0)evaluate(parents[i]);
            original[i]=parents[i]<0?local[i]:product(original[parents[i]],local[i]);
            Matrix m=reflect(local[pairs[i]]);
            mirrored[i]=parents[i]<0?m:product(mirrored[parents[i]],m);
            done[i]=true;
        };
        for(int i=0;i<count;i++){
            evaluate(i);evaluate(pairs[i]);
            Matrix expected=reflect(original[pairs[i]]);
            for(int r=0;r<3;r++)for(int c=0;c<4;c++)
                check(std::fabs(mirrored[i][r][c]-expected[r][c])<.002f,"hierarchy reflection mismatch");
            // Anatomical hand locations must be reflection of the other hand.
            if(!strcmp(names[i],"lhand")||!strcmp(names[i],"rhand")){
                Matrix a=product(mirrored[i],bind[i]),o=product(original[pairs[i]],bind[pairs[i]]);
                for(int r=0;r<3;r++){
                    float delta=std::fabs(a[r][3]-(r==0?-o[r][3]:o[r][3]));
                    worst=std::fmax(worst,delta);check(delta<.15f,"hand location disagrees with mirrored animation");
                }
            }
        }
    }
    std::cout<<"PASS: "<<frames<<" frames x 53 bones; maximum hand error "<<worst<<" units\n";
    return 0;
}catch(const std::exception&e){std::cerr<<"FAIL: "<<e.what()<<"\n";return 1;}}
