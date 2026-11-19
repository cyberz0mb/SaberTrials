// Exercise the exact runtime FS/zone ownership adapter, using synthetic assets.
#include <cstdarg>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <set>
static std::vector<unsigned char> donorFile;
static std::set<void*> live;
static int reads=0,frees=0,zoneAllocations=0;
enum { TAG_FILESYS=1,qfalse=0,PRINT_DEVELOPER=0 };
static void* allocate(size_t n) { void* p=std::malloc(n); if(!p)std::abort(); live.insert(p); return p; }
static void* Z_Malloc(int n,int,int) { ++zoneAllocations; return allocate(size_t(n)); }
static void freeFile(void* p) { if(live.erase(p)!=1)std::abort(); ++frees; std::free(p); }
static int readFile(const char*,void** p) {
    ++reads; if(donorFile.empty()){*p=NULL;return -1;}
    *p=allocate(donorFile.size());std::memcpy(*p,donorFile.data(),donorFile.size());return int(donorFile.size());
}
static void print(int,const char*,...) {}
static struct { int(*FS_ReadFile)(const char*,void**); void(*FS_FreeFile)(void*); void(*Printf)(int,const char*,...); } ri={readFile,freeFile,print};
#define ST_GLA_COMPAT_ENGINE
#define main synthetic_main
#include "compat.cpp"
#undef main
int main() {
    Bytes model=fixture(21376); donorFile=fixture(22443);
    void* raw=allocate(model.size());std::memcpy(raw,model.data(),model.size());
    void* original=raw;
    ST_GLA_CompatRead("models/players/_humanoid/private_face.gla",&raw,int(model.size()));
    CHECK(raw!=original && !live.count(original) && live.count(raw));
    CHECK(reads==1 && frees==2 && zoneAllocations==1 && live.size()==1);
    Gla h; size_t bytes=u32(static_cast<unsigned char*>(raw)+96);CHECK(h.load(raw,bytes));CHECK(h.frames==22443);
    Bytes result(static_cast<unsigned char*>(raw),static_cast<unsigned char*>(raw)+bytes);
    validatePreservation(model,donorFile,result);
    // Simulate registration cache retaining the replacement. Cached reads do
    // not enter the disk adapter, and the cache can release it normally.
    freeFile(raw);CHECK(live.empty());
    raw=allocate(model.size());std::memcpy(raw,model.data(),model.size());original=raw;
    ST_GLA_CompatRead("models/players/_humanoid/_humanoid.gla",&raw,int(model.size()));
    CHECK(raw==original && reads==1);freeFile(raw);
    donorFile.clear();raw=allocate(model.size());std::memcpy(raw,model.data(),model.size());original=raw;
    ST_GLA_CompatRead("models/players/_humanoid/private_face.gla",&raw,int(model.size()));
    CHECK(raw==original && live.size()==1);freeFile(raw);CHECK(live.empty());
    std::puts("PASS loader: original and donor FS buffers freed once, only replacement transferred to cache, canonical recursion excluded, missing donor preserved.");
}
