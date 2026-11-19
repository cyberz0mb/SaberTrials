#include <algorithm>
#include <sstream>
#include <string>
#include <vector>
extern "C" {
#include "cg_local.h"
#include "ghoul2/G2.h"
}
#include "qcommon/st_emotes.h"

struct CGEmoteState {
    std::string message;
    void* model = nullptr;
    bool applied = false;
    int start = 0, until = 0;
    const stemote::Clip* clip = nullptr;
};
static CGEmoteState stCgEmotes[MAX_CLIENTS];
static std::vector<stemote::Clip> stCgCatalog;

extern "C" void CG_EmotesInit() {
    stCgCatalog = stemote::catalog(trap->Cvar_VariableStringBuffer);
    std::fill_n(stCgEmotes,MAX_CLIENTS,CGEmoteState());
}

static void CG_ResetEmotePose(centity_t* cent, CGEmoteState& state) {
    if (!state.applied) return;
    if (state.clip->stationary()) {
        cent->pe.legs.animationNumber = -1;
        cent->pe.legs.stPoseValid = qfalse;
    }
    cent->pe.torso.animationNumber = -1;
    cent->pe.torso.stPoseValid = qfalse;
    state.applied = false;
}

extern "C" qboolean CG_EmotePose(centity_t* cent, qboolean torsoOnly) {
    const auto& es = cent->currentState;
    const int num = es.clientNum;
    if (es.eType != ET_PLAYER || es.number != num || num < 0 || num >= MAX_CLIENTS || !cent->ghoul2) return qfalse;
    auto& state = stCgEmotes[num];
    const char* message = CG_ConfigString(stemote::playerString+num);
    if (state.message != message || state.model != cent->ghoul2) {
        CG_ResetEmotePose(cent,state);
        state.message = message;
        state.model = cent->ghoul2;
        state.clip = nullptr;
        char token[48];
        if (std::sscanf(message,"%47s %d %d",token,&state.start,&state.until) == 3 &&
            state.start >= 0 && state.until > state.start && state.until-state.start <= 24000) {
            for (const auto& clip : stCgCatalog) if (clip.token() == token) {
                state.clip = &clip;
                break;
            }
        }
    }
    if (!state.clip || cg.time < state.start || cg.time >= state.until ||
        (es.eFlags & EF_DEAD) || (state.clip->stationary() && es.groundEntityNum == ENTITYNUM_NONE)) {
        CG_ResetEmotePose(cent,state);
        return qfalse;
    }
    if ((torsoOnly != qfalse) == state.clip->stationary()) return qfalse;
    if (state.applied) return qtrue;
    const auto& clip = *state.clip;
    int first = clip.first, frames = clip.frames, fps = clip.fps;
    if (clip.stock >= 0) {
        const auto& anim = bgAllAnims[cent->localAnimIndex].anims[clip.stock];
        if (anim.numFrames < 2 || anim.frameLerp <= 0) return qfalse;
        first = anim.firstFrame; frames = anim.numFrames; fps = 1000/anim.frameLerp;
    } else {
        char gla[MAX_QPATH] = {};
        trap->G2API_GetGLAName(cent->ghoul2,0,gla);
        // Private skeletons can have their own frames at the same numeric offsets.
        if (!stemote::sharedGla(gla)) return qfalse;
    }
    const float frame = std::min(float(first+frames-1),first+(cg.time-state.start)*fps*.001f);
    constexpr int flags = BONE_ANIM_OVERRIDE_FREEZE | BONE_ANIM_BLEND;
    if (torsoOnly && cent->noLumbar) return qfalse;
    if (!trap->G2API_SetBoneAnim(cent->ghoul2,0,torsoOnly?"lower_lumbar":"model_root",first,first+frames,
        flags,fps*.05f,cg.time,frame,90))
        return qfalse;
    if (!torsoOnly) {
        if (!cent->noLumbar) trap->G2API_SetBoneAnim(cent->ghoul2,0,"lower_lumbar",first,first+frames,flags,fps*.05f,cg.time,frame,90);
        if (cent->localAnimIndex <= 1) trap->G2API_SetBoneAnim(cent->ghoul2,0,"Motion",first,first+frames,flags,fps*.05f,cg.time,frame,90);
    }
    state.applied = true;
    char developer[16];
    trap->Cvar_VariableStringBuffer("developer",developer,sizeof(developer));
    if (atoi(developer))
        trap->Print("ST_EMOTE_POSE %d %s\n",num,clip.id.c_str());
    return qtrue;
}
