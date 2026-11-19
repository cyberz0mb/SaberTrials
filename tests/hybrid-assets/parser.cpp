// Runs the actual game parser/tokenizer and validators, using only an in-memory
// filesystem adapter. No engine startup, server, config writes or rendering.
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>
#include <climits>
#include "anims.h"
#define MAX_QPATH 64
#define MAX_ANIM_FILES 16
#define MAX_TOKEN_CHARS 1024
#define ERR_DROP 1
#define FS_READ 0
typedef int qboolean;
enum { qfalse=0, qtrue=1 };
typedef int fileHandle_t;
#ifdef ST_TEST_UI
#include "ui_parser_types_under_test.h"
#else
#include "parser_types_under_test.h"
#endif
#define ENUM2STRING(arg) { #arg, arg }
#include "animtable.h"
#include "st_hybrid_anims.h"
#include "st_stance_runtime.h"
static char com_token[MAX_TOKEN_CHARS];
static char com_parsename[MAX_TOKEN_CHARS];
static int com_lines=1, com_tokenline=0;
#ifdef ST_TEST_UI
qboolean UIPAFtextLoaded=qfalse;
animation_t uiHumanoidAnimations[MAX_TOTALANIMATIONS];
int uiNumAllAnims=1;
#else
qboolean BGPAFtextLoaded=qfalse;
animation_t bgHumanoidAnimations[MAX_TOTALANIMATIONS];
int bgNumAllAnims=2;
#endif
bgLoadedAnim_t bgAllAnims[MAX_ANIM_FILES];
static std::vector<char> currentCfg, gla;
static size_t offsets[3];
static int openCount;
static int Open(const char* name,fileHandle_t* file,int) {
    *file=std::strstr(name,"animation.cfg") ? 1 : std::strstr(name,"_humanoid.gla") ? 2 : 0;
    offsets[*file]=0;
    ++openCount;
    return *file ? static_cast<int>((*file==1?currentCfg:gla).size()) : -1;
}
static void Read(void* destination,int length,fileHandle_t file) {
    auto& bytes=file==1?currentCfg:gla;
    if(length<0 || offsets[file]+length>bytes.size()) throw std::runtime_error("filesystem read bounds");
    std::memcpy(destination,bytes.data()+offsets[file],length);
    offsets[file]+=length;
}
static void Close(fileHandle_t) {}
static struct Traps { decltype(&Open) FS_Open; decltype(&Read) FS_Read; decltype(&Close) FS_Close; }
    traps={Open,Read,Close}, *trap=&traps;
#include "st_stance_assets.h"
static animation_t* BG_AnimsetAlloc(void) { throw std::runtime_error("unexpected non-humanoid allocation"); }
static animation_t* UI_AnimsetAlloc(void) { throw std::runtime_error("unexpected non-humanoid allocation"); }
static void BG_AnimsetFree(animation_t*) { throw std::runtime_error("unexpected animation free"); }
static void Com_Error(int,const char* message,...) {
    char buffer[2048];va_list args;va_start(args,message);
    std::vsnprintf(buffer,sizeof(buffer),message,args);va_end(args);
    throw std::runtime_error(buffer);
}
static void Com_Printf(const char* message,...) {
    va_list args;va_start(args,message);std::vfprintf(stderr,message,args);va_end(args);
}
static void Com_sprintf(char* output,int size,const char* message,...) {
    va_list args;va_start(args,message);std::vsnprintf(output,size,message,args);va_end(args);
}
#ifdef ST_TEST_UI
#include "ui_parser_functions_under_test.h"
static void ResetParser(void) {
    std::memset(bgAllAnims,0,sizeof(bgAllAnims));
    UIPAFtextLoaded=qfalse;uiNumAllAnims=1;
}
#define ParseUnderTest UI_ParseAnimationFile
#define HumanoidArray uiHumanoidAnimations
#else
#include "parser_functions_under_test.h"
#define ResetParser BG_InitAnimsets
#define ParseUnderTest BG_ParseAnimationFile
#define HumanoidArray bgHumanoidAnimations
#endif
#define CHECK(condition) do { if(!(condition)) { std::fprintf(stderr,"line %d: %s\n",__LINE__,#condition);return 1; } } while(0)
static std::vector<char> Load(const std::string& path) {
    std::ifstream file(path,std::ios::binary);
    if(!file)throw std::runtime_error("Cannot read fixture "+path);
    return std::vector<char>(std::istreambuf_iterator<char>(file),{});
}
static int Run(int argc,char** argv) {
    if(argc!=2)return 2;
    const std::string folder=argv[1];
    const auto expanded=Load(folder+"/expanded.cfg"), baseline=Load(folder+"/baseline.cfg");
    gla=Load(folder+"/stance.gla");
    CHECK(ST_StanceAssetsCheck());
    CHECK(ST_StanceAssetsAvailable());
    gla[100]^=1;
    CHECK(!ST_StanceAssetsCheck());
    gla[100]^=1;
    for(int humanoid=0;humanoid<=1;++humanoid) {
        ResetParser();currentCfg=expanded;
        CHECK(ParseUnderTest("models/players/_humanoid/animation.cfg",humanoid?HumanoidArray:nullptr,humanoid)==0);
        CHECK(ST_StanceLibraryValid(bgAllAnims[0].anims));
        CHECK(STH_AnimationsValid(bgAllAnims[0].anims));
        const int before=openCount;
        CHECK(ParseUnderTest("models/players/_humanoid/animation.cfg",humanoid?HumanoidArray:nullptr,humanoid)==0);
        CHECK(openCount==before);
    }
    ResetParser();currentCfg=baseline;
    CHECK(ParseUnderTest("models/players/_humanoid/animation.cfg",nullptr,qfalse)==0);
    CHECK(ST_StanceLibraryValid(bgAllAnims[0].anims));
    CHECK(!STH_AnimationsValid(bgAllAnims[0].anims));
    // Preserve the bounded reader: padding below the limit remains parseable,
    // while exact-limit and larger data must fail before any buffer read.
    ResetParser();currentCfg=expanded;currentCfg.resize(131070,' ');
    CHECK(ParseUnderTest("models/players/_humanoid/animation.cfg",nullptr,qfalse)==0);
    CHECK(STH_AnimationsValid(bgAllAnims[0].anims));
    for(const size_t length : {size_t(131071),size_t(131072),size_t(140000)}) {
        ResetParser();currentCfg=expanded;currentCfg.resize(length,' ');
        bool refused=false;
        try { ParseUnderTest("models/players/_humanoid/animation.cfg",nullptr,qfalse); }
        catch(const std::runtime_error& error) { refused=std::string(error.what()).find("exceeds the allowed")!=std::string::npos; }
        CHECK(refused);
        CHECK(offsets[1]==0);
    }
#ifdef ST_TEST_UI
    std::puts("Actual menu UI_ParseAnimationFile: expanded CFG, both argument paths and cache pass; stance/hybrid/GLA validated; old CFG and corrupted GLA rejected.");
#else
    std::puts("Shared BG_ParseAnimationFile: expanded CFG, both argument paths and cache pass; stance/hybrid/GLA validated; old CFG and corrupted GLA rejected.");
#endif
    return 0;
}
int main(int argc,char** argv) {
    try { return Run(argc,argv); }
    catch(const std::exception& error) { std::fprintf(stderr,"Parser failed: %s\n",error.what());return 1; }
}
