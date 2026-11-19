// Exercise the production skin hook across listen-server/renderer lifetimes.
#include <cstdio>
#include <cstdarg>
#include <cstring>
#include <iostream>
constexpr int MAX_QPATH=64, PRINT_WARNING=1, PRINT_ALL=0;
using qhandle_t=int;
struct skin_t {
    char name[MAX_QPATH]="models/players/test/model_default.skin";
    int numSurfaces=1,stCosmeticModel=0,stCosmeticSkin=0;
    unsigned stCosmeticReported=0;
    char stCosmeticClassic[MAX_QPATH]={};
};
static struct { bool registered=false; } tr;
static int reads=0,frees=0,models=0,skins=0;
static const char manifest[]="STCOS1 models/players/test/model.glm models/cosmetics/test/model.glm models/cosmetics/test/model.skin\n";
static struct Imports {
    int FS_ReadFile(const char*,void** data) { ++reads;*data=(void*)manifest;return sizeof(manifest)-1; }
    void FS_FreeFile(void*) { ++frees; }
    void Printf(int,const char*,...) {}
} ri;
static void Com_sprintf(char* out,size_t bytes,const char* fmt,...) {
    va_list args;va_start(args,fmt);std::vsnprintf(out,bytes,fmt,args);va_end(args);
}
static void Q_strncpyz(char* out,const char* in,size_t bytes) { std::snprintf(out,bytes,"%s",in); }
static qhandle_t RE_RegisterModel(const char*) { ++models;return 17; }
static qhandle_t RE_RegisterSkin(const char*);
#include "st_cosmetic_load.h"
static qhandle_t RE_RegisterSkin(const char*) {
    ++skins;skin_t nested;ST_RegisterCosmetic(&nested);return 23;
}
int main() {
    skin_t serverSkin;
    // Hunk_Clear has invalidated shaders. Even reading the cosmetic dependency
    // here would enter the client model loader from the server's skin setup.
    ST_RegisterCosmetic(&serverSkin);
    if(reads || models || skins || serverSkin.stCosmeticModel) return 1;
    tr.registered=true;
    skin_t clientSkin;ST_RegisterCosmetic(&clientSkin);
    if(reads!=1 || frees!=1 || models!=1 || skins!=1) return 2;
    if(clientSkin.stCosmeticModel!=17 || clientSkin.stCosmeticSkin!=23 ||
       std::strcmp(clientSkin.stCosmeticClassic,"models/players/test/model.glm")) return 3;
    // A second map clears client skin handles, enters the server phase, then
    // rebuilds them after BeginRegistration. Dependency loading must resume.
    tr.registered=false;skin_t nextServer;ST_RegisterCosmetic(&nextServer);
    if(reads!=1 || models!=1 || skins!=1) return 4;
    tr.registered=true;skin_t nextClient;ST_RegisterCosmetic(&nextClient);
    if(reads!=2 || frees!=2 || models!=2 || skins!=2 || nextClient.stCosmeticModel!=17) return 5;
    std::cout<<"Inactive renderer isolation, re-registration and recursion guard passed\n";
}
