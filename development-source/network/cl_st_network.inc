// Included in the MP client. Uses native cvars so normal userinfo, VM queries,
// server restrictions and the lagometer all see the same live connection.
#include "st_network.h"

namespace {
using stnet::Profile;
struct NetSetting {
    const char* name;
    cvar_t* var = nullptr;
    std::string personal;
    bool owned = false, external = false;
};
NetSetting settings[] = {{"cl_timeNudge"}, {"cl_maxpackets"}, {"snaps"}, {"rate"}, {"cl_packetdup"}};
cvar_t *netMode, *netHud;
int netHudFont;
bool writingNet, measuring;
int lastMode = -1, startTime, lastSequence, lastArrival, lastServerTime, currentPing = -1;
int lastSnapshot, serverCount, latestMillis;
bool haveWindow;
stnet::Controller controller;
stnet::PacketBudget packetBudget;
stnet::Pacer pacer;
stnet::Window samples, latest;

bool netLocked(const NetSetting& s) {
    return s.var->flags & (CVAR_ROM | CVAR_INIT | CVAR_PROTECTED | CVAR_SYSTEMINFO |
                           CVAR_SERVER_CREATED | CVAR_CHEAT | CVAR_LATCH);
}
void restore(NetSetting& s) {
    if (!s.owned) return;
    s.owned = false;
    if (!netLocked(s)) {
        writingNet = true;
        Cvar_SetSafe(s.name, s.personal.c_str());
        writingNet = false;
    }
    s.personal.clear();
}
int serverValue(const char* name) {
    return atoi(Info_ValueForKey(cl.gameState.stringData + cl.gameState.stringOffsets[CS_SERVERINFO], name));
}
void applyProfile() {
    stnet::Values v = stnet::values(controller.active);
    int fps = serverValue("sv_fps"), maxSnaps = serverValue("sv_snapsMax");
    int minRate = serverValue("sv_minRate"), maxRate = serverValue("sv_maxRate");
    const int snaps = stnet::requestedSnaps(fps, serverValue("sv_snapsMin"), maxSnaps);
    const int rate = stnet::requestedRate(minRate, maxRate);
    if (controller.active == Profile::Personal) {
        auto& nudge = settings[0];
        int personal = nudge.owned ? atoi(nudge.personal.c_str()) : nudge.var->integer;
        v.nudge = Com_Clampi(0, 8, personal);
    }
    int desired[] = {v.nudge, packetBudget.target, snaps, rate, v.dup};
    const char* system = cl.gameState.stringData + cl.gameState.stringOffsets[CS_SYSTEMINFO];
    for (size_t i = 0; i < ARRAY_LEN(settings); ++i) {
        auto& s = settings[i];
        bool fixed = (i == 2 && serverValue("sv_snapsPolicy") == 1) ||
                     (i == 3 && serverValue("sv_ratePolicy") == 1);
        if ((controller.active == Profile::Personal && i == 4) || fixed || s.external || netLocked(s) ||
            *Info_ValueForKey(system, s.name)) {
            restore(s);
            continue;
        }
        if (!s.owned) { s.personal = s.var->string; s.owned = true; }
        writingNet = true;
        Cvar_SetSafe(s.name, va("%d", desired[i]));
        writingNet = false;
    }
}
void resetNet() {
    for (auto& s : settings) {
        restore(s);
        s.external = false;
    }
    measuring = haveWindow = false;
    samples = latest = {};
    controller = {};
    packetBudget = {};
    pacer = {};
    lastSequence = lastServerTime = lastSnapshot = lastArrival = 0;
    currentPing = -1;
}
void netFrame() {
    bool active = cls.state == CA_ACTIVE && !clc.demoplaying && !*clc.downloadTempName;
    if (lastMode != netMode->integer || (measuring && !active)) {
        resetNet();
        lastMode = netMode->integer;
    }
    if (!active) return;
    int now = Sys_Milliseconds();
    if (!measuring) {
        measuring = true;
        startTime = now;
        serverCount = cl.snap.snapFlags & SNAPFLAG_SERVERCOUNT;
        if (lastMode == 2 && clc.netchan.remoteAddress.type != NA_LOOPBACK) applyProfile();
        return;
    }
    if (now - startTime < 10000) return;
    latest = samples;
    latestMillis = now - startTime;
    haveWindow = true;
    samples = {};
    startTime = now;
    if (lastMode != 2 || clc.netchan.remoteAddress.type == NA_LOOPBACK) return;
    Profile previous = controller.active;
    const int previousPackets = packetBudget.target;
    packetBudget.evaluate(latest, latestMillis);
    controller.evaluate(latest);
    if (previous != controller.active || previousPackets != packetBudget.target) applyProfile();
}
void netMessage(int sequence) {
    if (!measuring || sequence <= lastSequence) return;
    if (lastSequence) samples.missing += sequence - lastSequence - 1;
    ++samples.received;
    lastSequence = sequence;
}
const char* modeText() {
    if (!netMode || netMode->integer == 0) return "Off";
    if (netMode->integer == 1) return "Manual";
    if (clc.netchan.remoteAddress.type == NA_LOOPBACK) return "Auto (loopback)";
    if (controller.active == Profile::Personal) return controller.cooldown ? "Auto (restored)" : "Auto (sampling)";
    return controller.trial ? "Auto (trial)" : "Auto";
}
void netLines(char* top, size_t topSize, char* bottom, size_t bottomSize, bool hud = false) {
    const auto& w = haveWindow ? latest : samples;
    char ping[24] = "--", jitter[24] = "--", loss[24] = "--";
    if (currentPing >= 0 && Sys_Milliseconds() - lastSnapshot < 2000)
        Com_sprintf(ping, sizeof(ping), "%d", currentPing);
    if (w.timingSamples) Com_sprintf(jitter, sizeof(jitter), "%.1f", w.jitter());
    if (w.received > 1) Com_sprintf(loss, sizeof(loss), "%.1f", w.loss());
    const int elapsed = haveWindow ? latestMillis : Sys_Milliseconds() - startTime;
    char actual[16] = "--";
    if (measuring && elapsed >= 1000)
        Com_sprintf(actual, sizeof(actual), "%.0f", 1000.0 * w.sent / elapsed);
    if (hud) {
        Com_sprintf(top, topSize, "%s   Ping %s ms   Jitter %s ms   Loss %s%%", modeText(), ping, jitter, loss);
        Com_sprintf(bottom, bottomSize, "Sent %s/s   Max %d   Snaps %d   Rate %d   Nudge %d   Dup %d",
            actual, cl_maxpackets->integer, settings[2].var->integer, settings[3].var->integer,
            Com_Clampi(-30, 30, cl_timeNudge->integer), cl_packetdup->integer);
        return;
    }
    Com_sprintf(top, topSize, "%s  Ping %s ms  Jitter %s ms  In loss %s%%", modeText(), ping, jitter, loss);
    Com_sprintf(bottom, bottomSize, "Nudge %d  MaxPPS %d  Snaps req %d  Rate req %d  Dup %d  Sent/s %s",
        Com_Clampi(-30, 30, cl_timeNudge->integer), cl_maxpackets->integer, settings[2].var->integer,
        settings[3].var->integer, cl_packetdup->integer, actual);
}
void netStatus() {
    char top[128], bottom[128];
    netLines(top, sizeof(top), bottom, sizeof(bottom));
    Com_Printf("%s\n%s\n", top, bottom);
}
void netInit() {
    netMode = Cvar_Get("st_netMode", "2", CVAR_ARCHIVE);
    netHud = Cvar_Get("st_netStats", "0", CVAR_ARCHIVE);
    Cvar_CheckRange(netMode, 0, 2, qtrue);
    Cvar_CheckRange(netHud, 0, 1, qtrue);
    settings[0].var = cl_timeNudge;
    settings[1].var = cl_maxpackets;
    settings[2].var = Cvar_Get("snaps", "40", CVAR_USERINFO | CVAR_ARCHIVE);
    settings[3].var = Cvar_Get("rate", "25000", CVAR_USERINFO | CVAR_ARCHIVE);
    settings[4].var = cl_packetdup;
    Cmd_AddCommand("st_netStatus", netStatus, "Show measured connection and current network settings");
}
}

const char* CL_NetPersonal(const cvar_t* var) {
    for (auto& s : settings) if (s.owned && s.var == var) return s.personal.c_str();
    return var->string;
}
void CL_NetCommandPacketSent() {
    if (measuring) ++samples.sent;
}
void CL_NetExternalSet(const cvar_t* var) {
    if (writingNet || !measuring || lastMode != 2) return;
    for (auto& s : settings) if (s.var == var && !netLocked(s)) {
        s.external = true;
        s.owned = false;
        s.personal.clear();
    }
}
void CL_NetPolicyChanged() {
    if (measuring && lastMode == 2 && clc.netchan.remoteAddress.type != NA_LOOPBACK) applyProfile();
}
void CL_NetSnapshot(bool matched) {
    if (!measuring) return;
    if (serverCount != (cl.snap.snapFlags & SNAPFLAG_SERVERCOUNT)) {
        resetNet();
        return;
    }
    const int now = Sys_Milliseconds();
    if (lastSnapshot && cl.snap.serverTime > lastServerTime) {
        int arrival = now - lastArrival, interval = cl.snap.serverTime - lastServerTime;
        if (arrival >= 0 && arrival < 2000 && interval < 2000) {
            samples.variation += std::abs(arrival - interval);
            ++samples.timingSamples;
        }
    }
    lastArrival = lastSnapshot = now;
    lastServerTime = cl.snap.serverTime;
    ++samples.snapshots;
    if (cl.snap.snapFlags & SNAPFLAG_RATE_DELAYED) ++samples.delayed;
    currentPing = matched ? cl.snap.ping : -1;
    if (currentPing >= 0) { ++samples.pingSamples; samples.pingSum += currentPing; }
}
bool CL_NetPacing(qboolean& ready) {
    if (!settings[1].owned || !measuring || !netMode || netMode->integer != 2) return false;
    ready = pacer.ready(Sys_Milliseconds(), cl_maxpackets->integer) ? qtrue : qfalse;
    return true;
}
void CL_NetDraw() {
    if (!measuring || !netHud->integer || !Cvar_VariableIntegerValue("cg_draw2D") ||
        Cvar_VariableIntegerValue("st_photoMode")) return;
    char top[128], bottom[128];
    netLines(top, sizeof(top), bottom, sizeof(bottom), true);
    const int font = netHudFont ? netHudFont : cls.menuFont;
    const float topScale = .54f, bottomScale = .48f;
    const int width = std::max(re->Font_StrLenPixels(top, font, topScale),
                               re->Font_StrLenPixels(bottom, font, bottomScale)) + 9;
    const int secondY = 5 + re->Font_HeightPixels(font, topScale);
    const int height = secondY + re->Font_HeightPixels(font, bottomScale) - 2;
    const vec4_t background = {.025f,.05f,.065f,.77f}, accent = {.23f,.82f,.94f,1};
    const vec4_t primary = {.94f,.98f,1,1}, secondary = {.75f,.85f,.90f,1};
    re->SetColor(background);
    re->DrawStretchPic(5, 3, width, height, 0, 0, 1, 1, cls.whiteShader);
    re->SetColor(accent);
    re->DrawStretchPic(5, 3, 1, height, 0, 0, 1, 1, cls.whiteShader);
    re->SetColor(nullptr);
    re->Font_DrawString(10, 4, top, primary, font, -1, topScale);
    re->Font_DrawString(10, secondY, bottom, secondary, font, -1, bottomScale);
}
