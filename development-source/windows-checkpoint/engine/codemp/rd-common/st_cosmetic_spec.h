// Saber Trials cosmetic mesh association v1. GPL-2.0-or-later.
#pragma once
#include <cstring>
#include <cstddef>
namespace st_cosmetic {
struct Spec { char classic[64], visual[64], skin[64]; };
inline bool path(const char* s,const char* prefix,const char* suffix) {
    const size_t n=std::strlen(s), p=std::strlen(prefix), e=std::strlen(suffix);
    if(n<=p+e || n>=64 || std::strncmp(s,prefix,p) || std::strcmp(s+n-e,suffix)) return false;
    if(std::strstr(s,"..") || std::strstr(s,"//")) return false;
    for(size_t i=0;i<n;++i) if(!((s[i]>='a'&&s[i]<='z') || (s[i]>='0'&&s[i]<='9') ||
        s[i]=='_' || s[i]=='-' || s[i]=='/' || s[i]=='.')) return false;
    return true;
}
inline bool parse(const void* input,size_t bytes,Spec& out) {
    if(!input || !bytes || bytes>256) return false;
    const char* s=static_cast<const char*>(input); char tokens[4][64]={}; size_t pos=0;
    for(int t=0;t<4;++t) {
        while(pos<bytes && (s[pos]==' '||s[pos]=='\r'||s[pos]=='\n'||s[pos]=='\t')) ++pos;
        size_t n=0;
        while(pos<bytes && s[pos]!=' '&&s[pos]!='\r'&&s[pos]!='\n'&&s[pos]!='\t') {
            if(!s[pos] || n>=63) return false;
            tokens[t][n++]=s[pos++];
        }
        if(!n) return false;
    }
    while(pos<bytes && (s[pos]==' '||s[pos]=='\r'||s[pos]=='\n'||s[pos]=='\t')) ++pos;
    if(pos!=bytes || std::strcmp(tokens[0],"STCOS1") ||
       !path(tokens[1],"models/players/",".glm") ||
       !path(tokens[2],"models/cosmetics/",".glm") ||
       !path(tokens[3],"models/cosmetics/",".skin")) return false;
    std::strcpy(out.classic,tokens[1]);std::strcpy(out.visual,tokens[2]);std::strcpy(out.skin,tokens[3]);
    return true;
}
enum State { enabled=1, identity=2, root=4, gore=8, shadows=16, lod=32, shader=64, overrides=128, skeleton=256 };
inline unsigned reject(bool on,bool match,int surfaceRoot,bool hasGore,int shadowMode,int level,bool customShader,int visualLods=1) {
    if(!on) return enabled;
    if(!match) return identity;
    if(surfaceRoot!=0) return root;
    if(hasGore) return gore;
    if(shadowMode==2) return shadows;
    // A one-LOD pilot retains its original distance fallback. A validated
    // authored chain uses the renderer's ordinary projected-size selection.
    if(level<0 || (level!=0 && visualLods<2)) return lod;
    if(customShader) return shader;
    return 0;
}
}
