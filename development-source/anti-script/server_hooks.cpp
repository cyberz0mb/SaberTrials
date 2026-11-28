#include "server/server.h"
#include "server/sv_gameapi.h"
#include "server/sv_staff.h"
#include "server/sv_account.h"
#include "server_hooks.h"
#include "server_storage.h"
#include "st_staff_types.h"
#include "ledger.h"
#include <algorithm>
#include <array>
#include <chrono>
#include <climits>
#include <memory>

namespace {
using namespace antiscript;
struct Signals {
    Behavior behavior;
    Claim claim;
    std::array<Pattern,8> patterns;
    unsigned index = 0;
    int64_t lastPacket = 0, nextReport = 0;
};
struct Session {
    Signals signals;
    std::string account;
    bool deferred = false, admitted = false;
    Mode mode = Mode::Off;
    int64_t deadline = 0, nextSave = 0;
};
std::array<Session,MAX_CLIENTS> sessions;
cvar_t* setting;
bool activeLastFrame=false;
std::unique_ptr<Ledger> db;
int dbPort = -1;
int64_t retryStorage = 0;
// Per-slot log limits survive reconnects. A report has no target/account field.
std::array<int64_t,MAX_CLIENTS> nextClientLog{}, nextServerLog{};
int64_t mono() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
}
int64_t utc() {
    return std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
}
Mode current() {
    if (!setting || !setting->integer) return Mode::Off;
    if (!strcmp(setting->string,"2")) return Mode::Enforce;
    return !strcmp(setting->string,"1") ? Mode::Monitor : Mode::Off;
}
void storageError(const std::exception& e) {
    if (mono() < retryStorage) return;
    Com_Printf("Anti-script storage error: %s\n",e.what());
    retryStorage = mono()+5000;
    db.reset();
}
Ledger& store() {
    int port = Cvar_VariableIntegerValue("net_port");
    if (db && dbPort == port) return *db;
    if (mono() < retryStorage) throw std::runtime_error("storage retry pending");
    auto path = staccount::ServerCredentialPath(port);
    if (path.empty()) throw std::runtime_error("private server directory unavailable");
    db.reset(new Ledger(path.substr(0,path.find_last_of('/')+1)+"anti-script.sqlite"));
    dbPort = port;
    return *db;
}
bool human(int slot) {
    return svs.clients && slot >= 0 && slot < sv_maxclients->integer &&
        svs.clients[slot].netchan.remoteAddress.type != NA_BOT;
}
void observe(int i,bool client,const std::string& detail) {
    auto& next = (client ? nextClientLog : nextServerLog)[i];
    if (mono() < next) return;
    next = mono()+30000;
    auto& a = sessions[i].account;
    try { store().observe(a.empty()?"guest":a,client?"script-report":"repeated-input",
                          "slot="+std::to_string(i)+" "+detail,utc()); }
    catch (const std::exception& e) { storageError(e); }
}
std::string displayName(const char* raw) {
    char name[MAX_NAME_LENGTH];
    Q_strncpyz(name,raw,sizeof(name));
    Q_CleanStr(name);
    std::string clean;
    for (unsigned char c : std::string(name))
        if (c >= 32 && c < 127 && c != '"' && c != '\\' && c != ';' && c != '@' && c != '^') clean += char(c);
    return clean.empty()?"Player":clean;
}
void notify(int i,int strike) {
    static const char* messages[] = {"",""," has been detected cheating."," has been kicked for cheating.",
                                    " has been temp-banned for cheating."," has been perma-banned for cheating."};
    auto* cl = &svs.clients[i];
    std::string message = strike == 1 ? "Warning: Anti-cheating is active. You have been warned." :
                                        displayName(cl->name)+messages[strike];
    auto* audience = strike == 1 ? cl : nullptr;
    SV_SendServerCommand(audience,"cp \"%s\"",message.c_str());
    if (strike < 3) SV_SendServerCommand(audience,"print \"%s\n\"",message.c_str());
    else {
        const auto account=sessions[i].account;
        SV_DropClient(cl,messages[strike]+1);
        if (strike >= 4) {
            for (int j=0;j<sv_maxclients->integer;++j) {
                if (j!=i && human(j) && svs.clients[j].state==CS_ACTIVE &&
                    SV_VerifiedPlayerAccount(j)==account)
                    SV_DropClient(&svs.clients[j],"Active anti-script ban on this account.");
            }
        }
    }
}
void match(int i,const Pattern& p) {
    auto& s = sessions[i];
    auto& c = s.signals.claim;
    if (!corroborates(c,p) || std::llabs(int64_t(sv.time)-p.time)>1500) return;
    if (s.account.empty() || s.account != SV_VerifiedPlayerAccount(i)) return;
    auto now = mono();
    if (now < s.nextSave || !c.origin) return;
    unsigned char generation[16];
    if (!SV_StaffGeneration(i,generation)) return;
    // A client origin can only suppress a repeat for this authenticated slot.
    // Fresh origins still pass through the persisted account-wide cooldown.
    std::string incident=st::Hex(generation,sizeof(generation))+"-"+std::to_string(c.origin);
    try {
        int strike = store().confirm(current(),s.account,incident,c,p,utc());
        s.nextSave = now+15000;
        if (strike) notify(i,strike);
    } catch (const std::exception& e) { storageError(e); }
}
bool eligible(int i) {
    if (current()==Mode::Off || !human(i) || svs.clients[i].state!=CS_ACTIVE || !SV_ASAllowed(i)) return false;
    auto* ps = SV_GameClientNum(i);
    return ps && ps->pm_type == PM_NORMAL && ps->stats[STAT_HEALTH] > 0 &&
        ps->persistant[PERS_TEAM] != TEAM_SPECTATOR && !ps->m_iVehicleNum && !(ps->pm_flags & PMF_FOLLOW);
}
bool integer(const char* input,int64_t& result) {
    result = 0;
    if (!*input) return false;
    for (; *input; ++input) {
        if (*input<'0' || *input>'9' || result>(INT64_MAX-9)/10) return false;
        result = result*10 + (*input-'0');
    }
    return true;
}
void admin() {
    std::string op = Cmd_Argv(1), a = Cmd_Argv(2);
    if (op=="players" && Cmd_Argc()==2) {
        if (svs.clients) for (int i=0;i<sv_maxclients->integer;++i) if (human(i)&&svs.clients[i].state==CS_ACTIVE)
            Com_Printf("#%d %s %s\n",i,displayName(svs.clients[i].name).c_str(),SV_VerifiedPlayerAccount(i).c_str());
        return;
    }
    int64_t before = INT64_MAX;
    if ((validAccount(a) || (a=="guest" && op=="evidence")) &&
        (Cmd_Argc()==3 || (Cmd_Argc()==4 && op=="evidence" && integer(Cmd_Argv(3),before)))) {
        try {
            if (op=="evidence") {
                if (a!="guest") {
                    auto s=store().lookup(a);
                    Com_Printf("strikes=%d ban_until=%lld active=%d\n",s.strikes,(long long)s.banUntil,int(s.banned(utc())));
                }
                store().evidence(a,before,[](const std::string& line){Com_Printf("%s\n",line.c_str());});
                return;
            }
            if (op=="clear" || op=="revoke") {
                bool changed=store().overrideState(a,op=="clear",utc());
                Com_Printf("Anti-script: %s\n",changed?"override saved":"no matching state to change");
                return;
            }
        } catch (const std::exception& e) { storageError(e); return; }
    }
    Com_Printf("st_as players | evidence <account|guest> [before-event-id] | clear <account> | revoke <account>\n");
}
}
void SV_ASInit() {
    setting = Cvar_Get("sv_stAntiScript","0",CVAR_SERVERINFO,"Anti-script: 0 off, 1 monitor, 2 enforce");
    Cmd_AddCommand("st_as",admin,"Inspect anti-script evidence and manage strikes/bans");
}
void SV_ASReset(int i) { if (i>=0 && i<MAX_CLIENTS) sessions[i] = {}; }
bool SV_ASDeferBegin(int i) {
    if (current()!=Mode::Enforce || !human(i)) return false;
    activeLastFrame=true;
    sessions[i].deferred=true;
    return true;
}
bool SV_ASAllowed(int i) {
    return current()!=Mode::Enforce || !human(i) || sessions[i].admitted;
}
void SV_ASAccountChanged(int i) {
    if (current()==Mode::Off || !human(i)) return;
    auto& s=sessions[i];
    if (!s.account.empty() && s.account!=SV_VerifiedPlayerAccount(i)) {
        s.signals={};
        if (current()==Mode::Enforce && s.admitted)
            SV_DropClient(&svs.clients[i],"Account verification ended. Reconnect to verify.");
    }
}
void SV_ASFrame() {
    if (!svs.clients) return;
    auto m = current();
    if (m==Mode::Off && !activeLastFrame) return;
    activeLastFrame=(m!=Mode::Off);
    for (int i=0;i<sv_maxclients->integer;++i) {
        auto& s=sessions[i];
        if (!human(i) || svs.clients[i].state!=CS_ACTIVE) continue;
        if (m == Mode::Off && s.mode==m && !s.deferred) continue;
        std::string account = m==Mode::Off ? "" : SV_VerifiedPlayerAccount(i);
        if (s.mode!=m || s.account!=account) {
            if (s.mode==Mode::Enforce && m==s.mode && s.admitted && s.account!=account) {
                SV_DropClient(&svs.clients[i],"Account verification ended. Reconnect to verify.");
                continue;
            }
            bool deferred=s.deferred;
            s={}; s.mode=m; s.deferred=deferred; s.account=account;
        }
        if (m==Mode::Enforce && !s.admitted) {
            if (!s.deadline) {
                s.deadline=mono()+90000;
                SV_SendServerCommand(&svs.clients[i],"cp \"Verifying Saber Trials account for anti-script enforcement.\"");
            }
            if (mono() >= s.deadline) {
                SV_DropClient(&svs.clients[i],"Verified Saber Trials account required to play.");
                continue;
            }
            if (account.empty() || mono()<retryStorage) continue;
            try {
                auto state=store().lookup(account);
                if (state.banned(utc())) {
                    SV_DropClient(&svs.clients[i],state.banUntil==-1?"Permanently banned for cheating.":"Temporarily banned for cheating.");
                    continue;
                }
            } catch (const std::exception& e) { storageError(e); continue; }
            s.admitted=true;
        }
        if (s.deferred) { s.deferred=false; GVM_ClientBegin(i); }
    }
}
bool SV_ASCommand(int i) {
    if (Q_stricmp(Cmd_Argv(0),"st_as1")) return false;
    if (Cmd_Argc()!=4 || !eligible(i)) return true;
    auto& sig=sessions[i].signals;
    auto now=mono();
    if (now<sig.nextReport) return true;
    sig.nextReport=now+100;
    int64_t stamp, origin;
    std::string shape=Cmd_Argv(2);
    if (!integer(Cmd_Argv(3),origin) || origin < 1 || origin > UINT32_MAX) return true;
    if (!balanced(shape) || !integer(Cmd_Argv(1),stamp) || stamp>INT_MAX ||
        std::llabs(stamp-sv.time)>1500) return true;
    sig.claim={shape,int(stamp),static_cast<uint32_t>(origin)};
    observe(i,true,"shape="+shape+" cmd_time="+std::to_string(stamp));
    for (const auto& p : sig.patterns) if (corroborates(sig.claim,p)) { match(i,p); break; }
    return true;
}
void SV_ASSample(int i,const usercmd_s& cmd) {
    if (current()==Mode::Off || !human(i)) return;
    auto& sig=sessions[i].signals;
    if (!eligible(i) || (cmd.buttons & BUTTON_TALK) || std::llabs(int64_t(sv.time)-cmd.serverTime)>250) {
        sig={}; return;
    }
    auto now=mono();
    if (sig.lastPacket && now-sig.lastPacket>250) sig={};
    sig.lastPacket=now;
    int mask=0;
    if (cmd.buttons & BUTTON_ATTACK) mask |= 1;
    if (cmd.buttons & BUTTON_ALT_ATTACK) mask |= 2;
    if (cmd.forwardmove>0) mask |= 4;
    if (cmd.forwardmove<0) mask |= 8;
    if (cmd.rightmove<0) mask |= 16;
    if (cmd.rightmove>0) mask |= 32;
    if (cmd.upmove>0) mask |= 64;
    if (cmd.upmove<0) mask |= 128;
    auto p=sig.behavior.sample(mask,cmd.serverTime,sv.time);
    if (p.signature.empty()) return;
    sig.patterns[sig.index++ % sig.patterns.size()]=p;
    observe(i,false,"shape="+p.signature+" cmd_time="+std::to_string(p.time)+" repeats=3 intervals_ms="+p.intervals);
    match(i,p);
}
