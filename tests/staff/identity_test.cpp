#include "st_staff_identity.h"
#include "check.h"
#include <fstream>
#include <iterator>
#include <cstdio>
#ifdef _WIN32
#include <windows.h>
#include <wincrypt.h>
#else
#include "st_private_linux.h"
#endif
#include <algorithm>
static void CheckProtectedIdentity(const std::string& path, st::Bytes& protectedBytes) {
#ifdef _WIN32
    DATA_BLOB encrypted={(DWORD)(protectedBytes.size()-5),protectedBytes.data()+5},plain={};
    CHECK(CryptUnprotectData(&encrypted,NULL,NULL,NULL,NULL,CRYPTPROTECT_UI_FORBIDDEN,&plain));
    CHECK(plain.cbData==64);
    CHECK(std::search(protectedBytes.begin(),protectedBytes.end(),plain.pbData,plain.pbData+plain.cbData)==protectedBytes.end());
    SecureZeroMemory(plain.pbData,plain.cbData);LocalFree(plain.pbData);
#else
    st::Bytes plain;CHECK(st::UnprotectFile(path,"STID",plain));CHECK(plain.size()==64);
    CHECK(std::search(protectedBytes.begin(),protectedBytes.end(),plain.begin(),plain.end())==protectedBytes.end());
#endif
}
RUN_TEST(
    const std::string path = "identity-test.key";
    std::remove(path.c_str()); std::remove("backup-test.key");
    st::Identity a;
    CHECK(!a.LoadOrCreate(path, false));
    CHECK(a.LoadOrCreate(path, true));
    const std::string pub = a.PublicId();
    st::Identity b;
    CHECK(b.LoadOrCreate(path, false));
    CHECK(pub == b.PublicId());
    st::Bytes protectedBytes;
    CHECK(st::ReadFileBytes(path,protectedBytes));
    CheckProtectedIdentity(path, protectedBytes);
    st::Bytes msg(20, 42); st::Bytes sig = a.Sign(msg);
    CHECK(st::Identity::Verify(pub, msg, sig));
    msg[0]++;
    CHECK(!st::Identity::Verify(pub, msg, sig));
    CHECK(a.ExportProtected("backup-test.key", "correct horse battery staple"));
    CHECK(!b.ImportProtected("backup-test.key", "wrong", path));
    CHECK(b.PublicId() == pub);
    st::Bytes unchanged;
    CHECK(st::ReadFileBytes(path,unchanged)&&unchanged==protectedBytes);
    std::remove("uncreated-identity.key");st::Identity empty;
    CHECK(!empty.ImportProtected("backup-test.key","wrong","uncreated-identity.key"));
    CHECK(!st::ReadFileBytes("uncreated-identity.key",unchanged));
    CHECK(b.ImportProtected("backup-test.key", "correct horse battery staple", path));
    { std::ofstream bad(path, std::ios::binary | std::ios::trunc); bad << "damaged"; }
    CHECK(!b.LoadOrCreate(path, true));
    CHECK(b.PublicId().empty());
    std::remove(path.c_str()); std::remove("backup-test.key");
)
