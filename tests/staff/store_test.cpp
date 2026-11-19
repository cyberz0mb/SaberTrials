#include "st_staff_store.h"
#include "check.h"
#include <cstdio>
#include <fstream>
RUN_TEST(
    std::remove("staff-test.db");
    const std::string owner(64,'1'), admin(64,'2'), mod(64,'3');
    st::Store db;
    CHECK(db.Open("staff-test.db"));
    CHECK(db.BootstrapOwner(owner,"Owner"));
    CHECK(db.Change(owner,admin,st::Role::Admin,"Admin",true));
    CHECK(db.Change(admin,mod,st::Role::Moderator,"Mod",true));
    CHECK(!db.Change(admin,mod,st::Role::Admin,"Mod",true));
    CHECK(!db.Change(mod,admin,st::Role::None,"Admin",false));
    CHECK(!db.Change(admin,owner,st::Role::None,"Owner",false));
    CHECK(!db.Change(owner,owner,st::Role::None,"Owner",false));
    CHECK(db.Get(mod).role == st::Role::Moderator);
    const auto rev = db.Get(mod).revision;
    db.FailNextWriteForTest();
    CHECK(!db.Change(owner,mod,st::Role::None,"Mod",false));
    CHECK(db.Get(mod).revision == rev);
    CHECK(db.Change(owner,mod,st::Role::None,"Mod",false));
    CHECK(!db.Get(mod).enabled);
    db.Close();
    CHECK(db.Open("staff-test.db"));
    CHECK(db.Get(owner).role == st::Role::Owner);
    CHECK(!db.Get(mod).enabled);
    CHECK(db.Get(mod).revision > rev);
    CHECK(!db.Change(owner,mod,st::Role::Admin,"^1Color",true));
    CHECK(db.AuditCount() == 4);
    CHECK(!db.ConsoleChange(owner,st::Role::None,"Owner",false));
    CHECK(!db.ConsoleChange(owner,st::Role::Admin,"Owner",true));
    const std::string secondOwner(64,'4');
    CHECK(db.BootstrapOwner(secondOwner,"Recovery owner"));
    CHECK(db.ConsoleChange(owner,st::Role::Admin,"Former owner",true));
    CHECK(!db.Change(admin,owner,st::Role::None,"Peer admin",false));
    CHECK(!db.Change(admin,mod,st::Role::Owner,"Promoted",true));
    CHECK(!db.Change(secondOwner,secondOwner,st::Role::Admin,"Self",true));
    CHECK(db.Change(secondOwner,owner,st::Role::None,"Former owner",false));
    CHECK(db.Get(secondOwner).enabled&&db.Get(secondOwner).role==st::Role::Owner);
    db.Close(); std::remove("staff-test.db");
    { std::ofstream f("staff-test.db");f<<"corrupted"; }
    CHECK(!db.Open("staff-test.db"));
    { std::ifstream f("staff-test.db");std::string s;f>>s;CHECK(s=="corrupted"); }
    db.Close();std::remove("staff-test.db");
)
