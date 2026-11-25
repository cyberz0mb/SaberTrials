#include "client/client.h"
#include "client_trace.h"
#include "detection.h"

namespace {
antiscript::Mode active = antiscript::Mode::Off;
antiscript::Execution execution;
antiscript::Claim pending;
int64_t nextShort = 0, nextLong = 0;
}
bool CL_ASCollecting() { return active != antiscript::Mode::Off; }
void CL_ASReset() {
    if (CL_ASCollecting()) Cbuf_ASReset();
    active = antiscript::Mode::Off;
    execution = {};
    pending = {};
    nextShort = nextLong = 0;
}
void CL_ASWait(uint32_t origin) { execution.wait(origin); }
void CL_ASAction(uint32_t origin,const char* command) {
    int e = antiscript::edge(command);
    if (e < 0) return;
    auto claim = execution.action(origin,e,cl.serverTime);
    if (!claim.signature.empty() && claim.signature.size() >= pending.signature.size()) pending = claim;
}
void CL_ASFrame() {
    auto mode = antiscript::Mode::Off;
    if (cls.state == CA_ACTIVE && !clc.demoplaying) {
        const char* info = cl.gameState.stringData + cl.gameState.stringOffsets[CS_SERVERINFO];
        mode = antiscript::mode(Info_ValueForKey(info,"sv_stAntiScript"));
    }
    if (mode != active) { CL_ASReset(); active = mode; }
    if (pending.signature.empty()) return;
    auto& next = pending.signature.size() > 2 ? nextLong : nextShort;
    if (cls.realtime >= next && clc.reliableSequence-clc.reliableAcknowledge < MAX_RELIABLE_COMMANDS/2) {
        CL_AddReliableCommand(va("st_as1 %d %s %u",pending.time,pending.signature.c_str(),pending.origin),qfalse);
        next = static_cast<int64_t>(cls.realtime) + (pending.signature.size() > 2 ? 250 : 2000);
    }
    pending = {};
}
