#ifndef ST_GLA_COMPAT_H
#define ST_GLA_COMPAT_H

// Extend a model-private, stock-body humanoid GLA in memory. Its original
// skeleton, face tracks and compressed poses remain the model author's data.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>

namespace st_gla_compat {
enum Result { unchanged, extended, invalid, incompatible };
static const size_t maxBytes = 128u * 1024u * 1024u;
inline uint32_t u32(const unsigned char* p) {
    return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24;
}
inline uint32_t u24(const unsigned char* p) {
    return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16;
}
inline void put32(unsigned char* p, uint32_t x) {
    for (int i=0;i<4;++i) p[i]=static_cast<unsigned char>(x>>(8*i));
}
inline void put24(unsigned char* p, uint32_t x) {
    for (int i=0;i<3;++i) p[i]=static_cast<unsigned char>(x>>(8*i));
}
struct Gla {
    const unsigned char* data;
    size_t size, frames, bones, frameOffset, poolOffset, poolCount;
    size_t boneOffset[53], boneSize[53];
    bool load(const void* input, size_t bytes) {
        if (!input || bytes<100 || bytes>maxBytes) return false;
        data=static_cast<const unsigned char*>(input); size=bytes;
        if (std::memcmp(data,"2LGA",4) || u32(data+4)!=6 || u32(data+96)!=size) return false;
        frames=u32(data+76); frameOffset=u32(data+80); bones=u32(data+84); poolOffset=u32(data+88);
        if (bones!=53 || frames<18 || frames>100000 || frameOffset<312 || frameOffset>size
            || poolOffset>size || poolOffset!=frameOffset+frames*bones*3 || (size-poolOffset)%14) return false;
        poolCount=(size-poolOffset)/14;
        if (!poolCount || poolCount>0xffffffu) return false;
        size_t roots=0;
        int32_t parents[53];
        for (size_t b=0;b<bones;++b) {
            size_t off=100+size_t(u32(data+100+b*4));
            if (off<312 || off>frameOffset || frameOffset-off<172) return false;
            if (!std::memchr(data+off,0,64)) return false;
            int32_t parent=static_cast<int32_t>(u32(data+off+68));
            parents[b]=parent;
            if (parent==-1) ++roots;
            else if (parent<0 || size_t(parent)>=bones || size_t(parent)==b) return false;
            size_t children=u32(data+off+168), length=172+children*4;
            if (children>bones || length>frameOffset-off) return false;
            for (size_t j=0;j<children;++j) if (u32(data+off+172+j*4)>=bones) return false;
            for (size_t j=0;j<24;++j) {
                uint32_t bits=u32(data+off+72+j*4); float f;
                std::memcpy(&f,&bits,4); if (!std::isfinite(f)) return false;
            }
            boneOffset[b]=off; boneSize[b]=length;
        }
        if (roots!=1 || u32(data+92)!=boneOffset[0]) return false;
        // The humanoid face parent is bone52, after its children; index order
        // does not imply hierarchy order. Walk bounded parent chains instead.
        for (size_t b=0;b<bones;++b) {
            int32_t current=int32_t(b); size_t hops=0;
            while (current!=-1 && hops++<bones) current=parents[current];
            if (current!=-1) return false;
        }
        for (size_t i=0;i<frames*bones;++i)
            if (u24(data+frameOffset+i*3)>=poolCount) return false;
        return true;
    }
    const unsigned char* pose(size_t f,size_t b) const {
        return data+poolOffset+u24(data+frameOffset+(f*bones+b)*3)*14;
    }
    bool face(size_t b) const {
        const char* name=reinterpret_cast<const char*>(data+boneOffset[b]);
        static const char* names[]={"ceyebrow","jaw","lblip2","leye","rblip2","ltlip2","rtlip2","reye"};
        for (size_t i=0;i<8;++i) if (!std::strcmp(name,names[i])) return true;
        return false;
    }
};

inline Result extend(const void* model, size_t modelBytes, const void* donor, size_t donorBytes,
                     std::vector<unsigned char>& output) {
    output.clear();
    Gla a,c;
    if (!a.load(model,modelBytes) || !c.load(donor,donorBytes)) return invalid;
    // These are the stock JKA and community extension prefix lengths. A
    // differently organized custom animation set must not be guessed at.
    if (c.frames<=22374 || a.frames>=c.frames) return unchanged;
    if (a.frames!=21376 && a.frames!=22374) return incompatible;
    if (std::memcmp(a.data+72,c.data+72,4)) return incompatible;
    for (size_t b=0;b<a.bones;++b) {
        size_t ao=a.boneOffset[b], co=c.boneOffset[b];
        if (a.boneSize[b]!=c.boneSize[b]
            || std::memcmp(a.data+ao,c.data+co,72)
            || std::memcmp(a.data+ao+168,c.data+co+168,a.boneSize[b]-168)
            || (!a.face(b) && std::memcmp(a.data+ao+72,c.data+co+72,96))) return incompatible;
    }
    // Permit model-specific expression frames, but require every existing
    // body frame to mean exactly the same thing before importing more frames.
    for (size_t f=0;f<a.frames;++f) for (size_t b=0;b<a.bones;++b) {
        if (f<18 && a.face(b)) continue;
        if (std::memcmp(a.pose(f,b),c.pose(f,b),14)) return incompatible;
    }
    const size_t extraFrames=c.frames-a.frames, newPool=a.poolOffset+extraFrames*a.bones*3;
    const size_t initialSize=newPool+a.size-a.poolOffset;
    if (initialSize>maxBytes) return invalid;
    output.resize(initialSize);
    std::memcpy(output.data(),a.data,a.poolOffset);
    std::memcpy(output.data()+newPool,a.data+a.poolOffset,a.size-a.poolOffset);
    std::vector<int32_t> remap(c.poolCount,-1);
    size_t count=a.poolCount;
    for (size_t f=a.frames;f<c.frames;++f) for (size_t b=0;b<a.bones;++b) {
        const uint32_t source=u24(c.data+c.frameOffset+(f*c.bones+b)*3);
        if (remap[source]<0) {
            if (count>=0xffffffu || output.size()+14>maxBytes) { output.clear(); return invalid; }
            remap[source]=static_cast<int32_t>(count++);
            const unsigned char* p=c.data+c.poolOffset+source*14;
            output.insert(output.end(),p,p+14);
        }
        put24(output.data()+a.frameOffset+(f*a.bones+b)*3,uint32_t(remap[source]));
    }
    put32(output.data()+76,uint32_t(c.frames));
    put32(output.data()+88,uint32_t(newPool));
    put32(output.data()+96,uint32_t(output.size()));
    return extended;
}
}

#ifdef ST_GLA_COMPAT_ENGINE
// Invoked after FS_ReadFile, before model-cache ownership/tag conversion and
// endian swapping. The caller and cache receive the replacement allocation.
static void ST_GLA_CompatRead(const char* name, void** buffer, int bytes) {
    static const char* canonical="models/players/_humanoid/_humanoid.gla";
    if (!buffer || !*buffer || bytes<100 || !name || !std::strcmp(name,canonical)) return;
    size_t len=std::strlen(name);
    if (len<4 || std::strcmp(name+len-4,".gla")) return;
    const unsigned char* raw=static_cast<const unsigned char*>(*buffer);
    if (std::memcmp(raw,"2LGA",4) || (st_gla_compat::u32(raw+76)!=21376 && st_gla_compat::u32(raw+76)!=22374)) return;
    void* source=NULL;
    int sourceBytes=ri.FS_ReadFile(canonical,&source);
    if (sourceBytes<100 || !source) { if(source) ri.FS_FreeFile(source); return; }
    std::vector<unsigned char> extended;
    st_gla_compat::Result result=st_gla_compat::extend(*buffer,size_t(bytes),source,size_t(sourceBytes),extended);
    ri.FS_FreeFile(source);
    if (result==st_gla_compat::extended) {
        void* replacement=Z_Malloc(int(extended.size()),TAG_FILESYS,qfalse);
        std::memcpy(replacement,extended.data(),extended.size());
        ri.FS_FreeFile(*buffer); *buffer=replacement;
        ri.Printf(PRINT_DEVELOPER,"Saber Trials: added compatible stance frames to %s in memory.\n",name);
    } else if (result==st_gla_compat::incompatible) {
        ri.Printf(PRINT_DEVELOPER,"Saber Trials: retained incompatible private animation set %s; no stance frames imported.\n",name);
    }
}
#endif
#endif
