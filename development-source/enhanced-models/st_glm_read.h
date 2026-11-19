#pragma once
#include "st_glm_validate.h"
inline void ST_GLM_Preflight(const char* path, void** buffer, int bytes, size_t maxBones=1024) {
    if (!*buffer) return;
    const size_t n=std::strlen(path);
    const bool glm=n>=4 && !Q_stricmp(path+n-4,".glm");
    if (!glm && (bytes<4 || std::memcmp(*buffer,"2LGM",4))) return;
    const char* error=st_glm::validate(*buffer,bytes<0?0:size_t(bytes),maxBones);
    if(error) {
        ri.Printf(PRINT_WARNING,"Saber Trials rejected %s: %s\n",path,error);
        ri.FS_FreeFile(*buffer);
        *buffer=nullptr;
    }
}
