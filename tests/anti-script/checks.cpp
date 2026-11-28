#include "detection.h"
#include "ledger.h"
#include "sqlite3.h"
#include "tag_buffer.h"
#include <filesystem>
#include <chrono>
#include <iostream>
#include <vector>

using namespace antiscript;
#define CHECK(x) do { if (!(x)) throw std::runtime_error(#x); } while (0)
static void cfg() {
    TagBuffer<16> q;
    q.append(0,4,1); q.append(4,2,2);
    CHECK(q.take(3,4)==1);
    q.prepend(12,3);
    CHECK(q.take(11,12)==3 && q.take(1,2)==2);
    q.append(0,2,4); q.append(2,2,5);
    CHECK(q.take(3,4)==0); // mixed origin, including after wrap
    q.reset(); CHECK(q.take(1,1)==0);
    Execution ex;
    int tick=10;
    auto action=[&](uint32_t root,const char* name){return ex.action(root,edge(name),++tick).signature;};
    for (auto* name : {"exec","vstr","bind","sensitivity","seta","cg_drawHUD","say","saberAttackCycle"})
        CHECK(action(1,name).empty());
    CHECK(action(1,"+attack").empty()); ex.wait(1);
    CHECK(action(2,"-attack").empty()); // physical release belongs to a new event
    CHECK(action(3,"+forward").empty()); CHECK(action(3,"+attack").empty());
    CHECK(action(4,"-forward").empty()); CHECK(action(4,"-attack").empty());
    CHECK(action(7,"+BUTTON0").empty()); ex.wait(7);
    CHECK(action(7,"-attack")=="01"); ex.wait(7);
    CHECK(action(7,"+forward").empty()); ex.wait(7);
    CHECK(action(7,"-forward")=="0145");
    CHECK(action(0,"+attack").empty()); ex.wait(1); CHECK(action(0,"-attack").empty());
    ex={}; CHECK(action(3,"+moveup").empty()); ex.wait(4); CHECK(action(3,"-moveup").empty());
    CHECK(mode("2")==Mode::Enforce && mode("1")==Mode::Monitor && mode("0")==Mode::Off && mode("9")==Mode::Off);
}
static Pattern samples(const std::vector<int>& masks,int jitter=0) {
    Behavior b; int time=100; b.sample(0,time,time); Pattern result;
    for (int r=0;r<3;++r) for (int m:masks) {
        time+=40+r*jitter; result=b.sample(m,time,time);
    }
    return result;
}
static void behavior() {
    auto p=samples({1,0,4,0});
    CHECK(p.signature=="0145" && !p.intervals.empty());
    CHECK(corroborates({"0145",p.time},p));
    CHECK(!corroborates({"0145",p.time+101},p) && !corroborates({"0167",p.time},p));
    CHECK(!corroborates({},p) && !corroborates({"0145",20},{}));
    CHECK(samples({1,0,4,0},12).signature.empty()); // ordinary timing variation
    CHECK(samples({5,0,5,0}).signature.empty()); // chord
    CHECK(samples({1,0,4,0},260).signature.empty()); // hitches
    auto movement=samples({16,0,64,0}); CHECK(corroborates({"89cd",movement.time},movement));
    auto attack=samples({1,0,1,0}); CHECK(!corroborates({attack.signature,attack.time},attack));
    Behavior burst;
    burst.sample(0,100,100); int stamp=100;
    for (int i=0;i<3;++i) for(int m:{1,0,4,0}) {
        stamp+=40; CHECK(burst.sample(m,stamp,100).signature.empty());
    }
    Behavior held; for (int t=0;t<500;++t) CHECK(held.sample(5,t,t).signature.empty());
    for (auto s : {"","00","10","zz","0123456789ab","0;","0\"","\n1"}) CHECK(!balanced(s));
}
static void ledger() {
    auto directory=std::filesystem::temp_directory_path()/("st-as-ledger-"+std::to_string(
        std::chrono::steady_clock::now().time_since_epoch().count()));
    CHECK(std::filesystem::create_directory(directory));
    auto file=directory/"ledger.sqlite";
    const std::string a(32,'a'), other(32,'b');
    auto p=samples({1,0,4,0}); Claim claim{p.signature,p.time};
    int64_t now=1700000000;
    {
        Ledger store(file.string());
        CHECK(!store.confirm(Mode::Off,a,"off",claim,p,now));
        CHECK(!store.confirm(Mode::Monitor,a,"monitor",claim,p,now));
        CHECK(!store.confirm(Mode::Enforce,"guest","guest",claim,p,now));
        CHECK(!store.confirm(Mode::Enforce,a,"single",{},p,now));
        int rows=0; store.evidence(a,INT64_MAX,[&](auto& v){++rows;CHECK(v.find("observe")!=v.npos);}); CHECK(rows==1);
    }
    // A competing writer cannot leave a penalty without its evidence record.
    {
        Ledger store(file.string());
        sqlite3* otherWriter=nullptr;
        CHECK(sqlite3_open_v2(file.string().c_str(),&otherWriter,SQLITE_OPEN_READWRITE,nullptr)==SQLITE_OK);
        CHECK(sqlite3_exec(otherWriter,"BEGIN IMMEDIATE",nullptr,nullptr,nullptr)==SQLITE_OK);
        bool blocked=false;
        try { store.confirm(Mode::Enforce,a,"locked",claim,p,now); }
        catch(const std::runtime_error&) { blocked=true; }
        CHECK(sqlite3_exec(otherWriter,"ROLLBACK",nullptr,nullptr,nullptr)==SQLITE_OK);
        CHECK(sqlite3_close(otherWriter)==SQLITE_OK);
        CHECK(blocked && store.lookup(a).strikes==0);
    }
    for (int strike=1;strike<=4;++strike) {
        Ledger store(file.string()); // restart/reconnect each time
        now+=601;
        CHECK(store.confirm(Mode::Enforce,a,std::to_string(strike),claim,p,now)==strike);
        CHECK(!store.confirm(Mode::Enforce,a,std::to_string(strike),claim,p,now));
        CHECK(!store.confirm(Mode::Enforce,a,"cool"+std::to_string(strike),claim,p,now+1));
        CHECK(store.lookup(a).strikes==strike && !store.lookup(other).strikes);
    }
    {
        Ledger store(file.string());
        auto state=store.lookup(a);
        CHECK(state.banUntil==now+30LL*86400 && state.banned(state.banUntil-1));
        CHECK(!store.confirm(Mode::Enforce,a,"banned",claim,p,now+3600));
        now=state.banUntil;
        CHECK(!state.banned(now) && state.strikes==4);
        CHECK(store.confirm(Mode::Enforce,a,"permanent",claim,p,now)==5);
    }
    {
        Ledger store(file.string());
        CHECK(store.lookup(a).banned(now+10LL*365*86400));
        CHECK(store.overrideState(a,false,now)); CHECK(store.lookup(a).strikes==5);
        CHECK(!store.lookup(a).banned(now) && !store.overrideState(a,false,now));
        CHECK(store.confirm(Mode::Enforce,a,"fresh",claim,p,now+601)==5);
        CHECK(store.overrideState(a,true,now+602)); CHECK(store.lookup(a).banned(now));
        CHECK(store.overrideState(a,false,now+603)); CHECK(!store.lookup(a).strikes);
        int rows=0; store.evidence(a,INT64_MAX,[&](auto&){++rows;}); CHECK(rows>=14);
        CHECK(!store.confirm(Mode::Enforce,a,"fresh",claim,p,now+99999)); // exact replay
    }
    std::filesystem::remove(file);
    std::filesystem::remove(directory);
}
int main(int argc,char** argv) {
    try {
        if (argc!=2) return 2;
        std::string suite=argv[1];
        if (suite=="cfg") cfg(); else if (suite=="behavior") behavior(); else if (suite=="ledger") ledger(); else return 2;
        return 0;
    } catch (const std::exception& e) { std::cerr<<e.what()<<'\n'; return 1; }
}
