#include "st_gla_compat.h"
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iterator>
#include <string>

#define CHECK(x) do { if (!(x)) { std::fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x); std::exit(1); } } while(0)
using namespace st_gla_compat;
typedef std::vector<unsigned char> Bytes;

static Bytes fixture(size_t frames) {
    const size_t bones=53, boneLen=172, ofsFrames=312+bones*boneLen, pool=ofsFrames+frames*bones*3;
    Bytes b(pool+28,0);
    std::memcpy(b.data(),"2LGA",4); put32(b.data()+4,6);
    put32(b.data()+72,0x3f800000); put32(b.data()+76,uint32_t(frames));
    put32(b.data()+80,uint32_t(ofsFrames)); put32(b.data()+84,53);
    put32(b.data()+88,uint32_t(pool)); put32(b.data()+92,312); put32(b.data()+96,uint32_t(b.size()));
    for(size_t i=0;i<bones;++i) {
        size_t off=312+i*boneLen; put32(b.data()+100+i*4,uint32_t(off-100));
        std::snprintf(reinterpret_cast<char*>(b.data()+off),64,"bone%02u",unsigned(i));
        if(i==16) std::strcpy(reinterpret_cast<char*>(b.data()+off),"ceyebrow");
        put32(b.data()+off+68,i?uint32_t(i-1):0xffffffffu);
    }
    std::memset(b.data()+pool,0x15,14); std::memset(b.data()+pool+14,0x27,14);
    for(size_t f=22374;f<frames;++f) for(size_t i=0;i<bones;++i)
        put24(b.data()+ofsFrames+(f*bones+i)*3,1);
    return b;
}
static void validatePreservation(const Bytes& original,const Bytes& donor,const Bytes& extended) {
    Gla a,c,o; CHECK(a.load(original.data(),original.size())); CHECK(c.load(donor.data(),donor.size())); CHECK(o.load(extended.data(),extended.size()));
    CHECK(o.frames==c.frames && o.bones==a.bones);
    CHECK(std::memcmp(original.data()+100,extended.data()+100,a.frameOffset-100)==0);
    CHECK(std::memcmp(original.data()+a.frameOffset,extended.data()+o.frameOffset,a.frames*a.bones*3)==0);
    CHECK(std::memcmp(original.data()+a.poolOffset,extended.data()+o.poolOffset,a.size-a.poolOffset)==0);
    for(size_t f=0;f<a.frames;++f) for(size_t i=0;i<a.bones;++i) CHECK(std::memcmp(a.pose(f,i),o.pose(f,i),14)==0);
    for(size_t f=a.frames;f<c.frames;++f) for(size_t i=0;i<a.bones;++i) CHECK(std::memcmp(c.pose(f,i),o.pose(f,i),14)==0);
}
static Bytes read(const char* path) {
    std::ifstream stream(path,std::ios::binary); CHECK(stream.good());
    return Bytes(std::istreambuf_iterator<char>(stream),std::istreambuf_iterator<char>());
}
int main(int argc,char**argv) {
    Bytes a,c,out,bad;
    if(argc==3) {
        a=read(argv[1]); c=read(argv[2]);
        CHECK(extend(a.data(),a.size(),c.data(),c.size(),out)==extended);
        validatePreservation(a,c,out);
        std::printf("PASS installed Akaza: original facial skeleton/tracks and all body frames preserved; canonical missing frames appended (%zu -> %zu bytes).\n",a.size(),out.size());
        return 0;
    }
    a=fixture(21376); c=fixture(22443);
    CHECK(extend(a.data(),a.size(),c.data(),c.size(),out)==extended);
    validatePreservation(a,c,out);
    Gla h; CHECK(h.load(a.data(),a.size()));
    // A private facial pivot and expression are allowed and survive extension.
    put32(a.data()+h.boneOffset[16]+72,0x3f000000);
    put24(a.data()+h.frameOffset+16*3,1);
    CHECK(extend(a.data(),a.size(),c.data(),c.size(),out)==extended);
    validatePreservation(a,c,out);
    bad=a; put32(bad.data()+h.boneOffset[2]+72,0x3f000000);
    CHECK(extend(bad.data(),bad.size(),c.data(),c.size(),out)==incompatible && out.empty());
    bad=a; put24(bad.data()+h.frameOffset+(50*53+16)*3,1);
    CHECK(extend(bad.data(),bad.size(),c.data(),c.size(),out)==incompatible);
    bad=a; put24(bad.data()+h.frameOffset+2*3,1);
    CHECK(extend(bad.data(),bad.size(),c.data(),c.size(),out)==incompatible);
    bad=a; bad[h.boneOffset[2]]='X';
    CHECK(extend(bad.data(),bad.size(),c.data(),c.size(),out)==incompatible);
    bad=a; put32(bad.data()+h.boneOffset[2]+68,2);
    CHECK(extend(bad.data(),bad.size(),c.data(),c.size(),out)==invalid);
    bad=a; put24(bad.data()+h.frameOffset,0xffffffu);
    CHECK(extend(bad.data(),bad.size(),c.data(),c.size(),out)==invalid);
    bad=a; put32(bad.data()+80,0xfffffff0u);
    CHECK(extend(bad.data(),bad.size(),c.data(),c.size(),out)==invalid);
    bad=a; put32(bad.data()+100,0xffffffffu);
    CHECK(extend(bad.data(),bad.size(),c.data(),c.size(),out)==invalid);
    bad=a; put32(bad.data()+h.boneOffset[2]+168,0xffffffffu);
    CHECK(extend(bad.data(),bad.size(),c.data(),c.size(),out)==invalid);
    CHECK(extend(a.data(),99,c.data(),c.size(),out)==invalid);
    CHECK(extend(a.data(),a.size()-1,c.data(),c.size(),out)==invalid);
    bad=a; put32(bad.data()+84,75);
    CHECK(extend(bad.data(),bad.size(),c.data(),c.size(),out)==invalid);
    CHECK(extend(c.data(),c.size(),c.data(),c.size(),out)==unchanged && out.empty());
    bad=fixture(21377);
    CHECK(extend(bad.data(),bad.size(),c.data(),c.size(),out)==incompatible);
    a=fixture(22374);
    CHECK(extend(a.data(),a.size(),c.data(),c.size(),out)==extended);
    validatePreservation(a,c,out);
    std::puts("PASS synthetic: private expressions, original frames/pool, extension poses, donor remapping, incompatible rigs, malformed/truncated buffers, known prefix lengths.");
    return 0;
}
