// Saber Trials model preflight. GPL-2.0-or-later.
// Reads little-endian bytes without casting untrusted disk structures.
#pragma once
#include <cstdint>
#include <cstring>
#include <cmath>
#include <vector>
namespace st_glm {
inline uint32_t read32(const unsigned char* p) {
    return uint32_t(p[0]) | uint32_t(p[1])<<8 | uint32_t(p[2])<<16 | uint32_t(p[3])<<24;
}
inline const char* validate(const void* input, size_t bytes, size_t maxBones=1024) {
    if (!input || bytes<164 || bytes>128u*1024u*1024u) return "GLM byte budget/header";
    const auto* d=static_cast<const unsigned char*>(input);
    auto u=[&](size_t p) { return read32(d+p); };
    auto span=[&](size_t p,size_t n,size_t end) { return p<=end && n<=end-p; };
    auto str=[&](size_t p) { return std::memchr(d+p,0,64)!=nullptr; };
    if (std::memcmp(d,"2LGM",4) || u(4)!=6) return "unsupported GLM format";
    if (u(160)!=bytes || !str(8) || !str(72)) return "GLM header bounds/name";
    const size_t bones=u(140), lods=u(144), ns=u(152), hstart=u(156);
    // Resource guardrails, not claims about format bit widths.
    if (!bones || bones>maxBones || !lods || lods>8 || !ns || ns>1024) return "GLM count budget";
    if (!span(164,ns*4,bytes) || hstart<164+ns*4) return "hierarchy table bounds";
    std::vector<int32_t> parents(ns);
    std::vector<size_t> incoming(ns,0);
    size_t h=hstart;
    for (size_t i=0;i<ns;++i) {
        if (!span(h,144,bytes) || 164+size_t(u(164+i*4))!=h) return "hierarchy offset";
        if (!str(h) || !str(h+68)) return "surface name/shader";
        parents[i]=static_cast<int32_t>(u(h+136));
        if (parents[i]<-1 || parents[i]>=int32_t(ns) || parents[i]==int32_t(i)) return "surface parent";
        const size_t nc=u(h+140);
        if (nc>ns || !span(h+144,nc*4,bytes)) return "surface children bounds";
        for(size_t c=0;c<nc;++c) {
            const size_t child=u(h+144+c*4);
            if(child>=ns || child==i || ++incoming[child]>1) return "surface child";
            // Parent consistency checked after reading all hierarchy records below.
        }
        h+=144+nc*4;
    }
    size_t walk=hstart;
    for(size_t i=0;i<ns;++i) {
        for(size_t c=0;c<u(walk+140);++c)
            if(parents[u(walk+144+c*4)]!=int32_t(i)) return "hierarchy disagreement";
        walk+=144+size_t(u(walk+140))*4;
        if(incoming[i]!=(parents[i]<0?0u:1u)) return "hierarchy missing edge";
        int32_t p=int32_t(i); size_t depth=0;
        while(p>=0) { if(++depth>ns || depth>128) return "hierarchy cycle/depth"; p=parents[p]; }
    }
    size_t lod=u(148);
    if(lod<h) return "LOD overlaps hierarchy";
    for(size_t l=0;l<lods;++l) {
        if(!span(lod,4+ns*4,bytes)) return "LOD header";
        size_t len=u(lod);
        if(len<4+ns*4 || !span(lod,len,bytes)) return "LOD span";
        size_t end=lod+len, s=lod+4+ns*4;
        std::vector<bool> seen(ns,false);
        for(size_t i=0;i<ns;++i) {
            if(!span(s,40,end)) return "surface header";
            size_t id=u(s+4), nv=u(s+12), nt=u(s+20), nr=u(s+28), sl=u(s+36);
            if(id>=ns || seen[id]) return "surface index";
            seen[id]=true;
            if(lod+4+size_t(u(lod+4+id*4))!=s || int64_t(s)+int32_t(u(s+8))!=0) return "surface back/lookup offset";
            if(sl<40 || !span(s,sl,end)) return "surface span";
            if(nv>=1000 || nt>=2000 || nr>32 || (nv && !nr)) return "classic surface batch budget";
            size_t vo=u(s+16), to=u(s+24), ro=u(s+32);
            if(vo<40 || to<40 || ro<40 || !span(vo,nv*40,sl) || !span(to,nt*12,sl) || !span(ro,nr*4,sl)) return "surface data bounds";
            auto overlap=[](size_t a,size_t an,size_t b,size_t bn) { return an && bn && a<b+bn && b<a+an; };
            if(overlap(vo,nv*40,to,nt*12) || overlap(vo,nv*40,ro,nr*4) || overlap(to,nt*12,ro,nr*4)) return "surface data overlap";
            for(size_t t=0;t<nt*3;++t) if(u(s+to+t*4)>=nv) return "triangle index";
            for(size_t b=0;b<nr;++b) if(u(s+ro+b*4)>=bones) return "bone reference";
            for(size_t v=0;v<nv;++v) {
                size_t p=s+vo+v*32; uint32_t packed=u(p+24), nw=(packed>>30)+1, total=0;
                for(size_t k=0;k<nw;++k) {
                    if(((packed>>(5*k))&31)>=nr) return "vertex bone index";
                    if(k+1<nw) total+=d[p+28+k] | ((packed>>(12+2*k))&0x300);
                }
                if(total>1023) return "negative residual bone weight";
                for(size_t k=0;k<8;++k) {
                    uint32_t bits=u(k<6?p+4*k:s+vo+nv*32+v*8+(k-6)*4); float value;
                    std::memcpy(&value,&bits,4);
                    if(!std::isfinite(value)) return "nonfinite vertex/UV";
                }
            }
            s+=sl;
        }
        if(s!=end) return "LOD trailing data";
        lod=end;
    }
    if(lod!=bytes) return "GLM trailing data";
    return nullptr;
}
}
