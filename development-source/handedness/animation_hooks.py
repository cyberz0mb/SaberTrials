"""Strict pose-only client/server hooks. Called after state_hooks by prepare.

This module never resets a checkout or touches installed packages. Root owns
invocation order, synchronized fallback policy, attachments and saber locks.
"""
import re


def _replace(text, old, new, count=1):
    found = text.count(old)
    if found != count:
        raise RuntimeError(f"Hand animation hook changed: {old[:90]!r}: {found} != {count}")
    return text.replace(old, new)


def _function(source, relative, signature):
    text = (source / relative).read_text()
    if text.count(signature) != 1:
        raise RuntimeError(f"Hand animation function changed: {relative}: {signature}")
    start = text.index(signature)
    opening = text.index("{", start)
    depth = 0
    tokens = re.finditer(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]',
                         text[opening:], re.S)
    for match in tokens:
        value = match.group()
        if value == "{":
            depth += 1
        elif value == "}":
            depth -= 1
            if depth == 0:
                return text[start:opening + match.end()]
    raise RuntimeError(f"Unclosed hand animation function: {relative}: {signature}")


def apply(source, change):
    # Only local render/server bookkeeping grows; no playerState/entityState ABI.
    change(source, 'codemp/cgame/cg_local.h', '#include "game/bg_public.h"',
           '#include "game/bg_public.h"\n#include "game/st_direction_timing.h"')
    change(source, 'codemp/game/g_local.h', '#include "bg_public.h"',
           '#include "bg_public.h"\n#include "st_direction_timing.h"')
    change(source, 'codemp/cgame/cg_local.h', '\tqboolean\ttorsoYawing;\n} lerpFrame_t;',
           '\tqboolean\ttorsoYawing;\n'
           '\tstDirectionalPlayback_t stPose;\n'
           '\tqboolean stPoseValid, stPoseSkipEvents;\n'
           '\tvoid *stPoseModel;\n} lerpFrame_t;')
    change(source, 'codemp/cgame/cg_local.h', 'typedef struct centity_s {',
           'typedef struct centity_s {\n'
           '\tqboolean stHandPoseFallback, stHandPoseValidated;\n'
           '\tunsigned stHandPoseRevision;\n'
           '\tvoid *stHandPoseModel;')
    change(source, 'codemp/cgame/cg_local.h', '} centity_t;',
           '} centity_t;\nqboolean CG_STPrepareHandPose(centity_t *cent);')
    change(source, 'codemp/game/g_local.h', '\tqboolean\ttorsoLastFlip;',
           '\tqboolean\ttorsoLastFlip;\n'
           '\tstDirectionalPlayback_t stLegsPose, stTorsoPose;\n'
           '\tqboolean stLegsPoseValid, stTorsoPoseValid;\n'
           '\tqboolean stHandPoseFallback, stHandPoseValidated;\n'
           '\tunsigned stHandPoseRevision;\n'
           '\tvoid *stHandPoseModel;')
    change(source, 'codemp/game/g_local.h', 'void G_UpdateClientAnims(gentity_t *self, float animSpeedScale);',
           'void G_UpdateClientAnims(gentity_t *self, float animSpeedScale);\n'
           'qboolean G_STPrepareHandPose(gentity_t *self);')

    cg = 'codemp/cgame/cg_players.c'
    change(source, cg, 'static void CG_PlayerFootsteps( centity_t *cent, footstepType_t footStepType )',
           '#include "cg_hand_anim.inc"\n\n'
           'static void CG_PlayerFootsteps( centity_t *cent, footstepType_t footStepType )')
    signature = 'static void CG_SetLerpFrameAnimation( centity_t *cent, clientInfo_t *ci, lerpFrame_t *lf, int newAnimation, float animSpeedMult, qboolean torsoOnly, qboolean flipState) {'
    change(source, cg, signature, signature + '\n'
           '\tif (CG_STSetNormalAnimation(cent,ci,lf,newAnimation,animSpeedMult,torsoOnly,flipState)) return;')

    signature = 'static void CG_RunLerpFrame( centity_t *cent, clientInfo_t *ci, lerpFrame_t *lf, qboolean flipState, int newAnimation, float speedScale, qboolean torsoOnly)'
    old = _function(source, cg, signature)
    new = _replace(old, 'if (cent->currentState.forceFrame)\n\t{',
                   'if (cent->currentState.forceFrame)\n\t{\n'
                   '\t\tlf->stPoseValid=qfalse; lf->stPoseSkipEvents=qtrue; // lock/forced playback is separate')
    new = _replace(new, '(CG_FirstAnimFrame(lf, torsoOnly, speedScale)) )',
                   '(CG_FirstAnimFrame(lf, torsoOnly, speedScale)) ||\n'
                   '\t\t\tCG_STPoseNeedsRefresh(cent,lf,newAnimation,speedScale) )')
    change(source, cg, old, new)

    signature = 'void CG_TriggerAnimSounds( centity_t *cent )'
    old = _function(source, cg, signature)
    refreshed = old.replace('{', '{\n\tCG_STRefreshClockPoses(cent);', 1)
    marker = 'curFrame = floor( currentFrame );'
    if old.count(marker) != 2:
        raise RuntimeError('Hand event root/lumbar sample hooks changed')
    pieces = refreshed.split(marker)
    new = (pieces[0] + 'currentFrame=CG_STCanonicalEventFrame(cent,&cent->pe.legs,currentFrame);\n\t\t' + marker +
           pieces[1] + 'currentFrame=CG_STCanonicalEventFrame(cent,&cent->pe.torso,currentFrame);\n\t\t' + marker + pieces[2])
    change(source, cg, old, new)
    change(source, cg,
           'CG_PlayerFootsteps( cent, (footstepType_t)animEvent->eventData[AED_FOOTSTEP_TYPE] );',
           '{\n\t\t\tfootstepType_t stFoot=CG_STFootstepType(cent,animEvent);\n'
           '\t\t\tif (stFoot!=NUM_FOOTSTEP_TYPES) CG_PlayerFootsteps(cent,stFoot);\n\t\t}')

    game = 'codemp/game/g_client.c'
    signature = 'void G_UpdateClientAnims(gentity_t *self, float animSpeedScale)'
    change(source, game, signature + '\n{',
           '#include "g_hand_anim.inc"\n\n' + signature + '\n{\n'
           '\tif (G_STUpdateNormalAnimations(self,animSpeedScale)) return;')

    # Physical contact limbs are selected locally; anatomical bolt IDs stay put.
    saber = 'codemp/game/w_saber.c'
    signature = 'static void G_KickSomeMofos(gentity_t *ent)'
    old = _function(source, saber, signature)
    new = _replace(old, 'ri->handRBolt', 'stHiltHandBolt', 2)
    new = _replace(new, 'ri->footRBolt', 'stKickFootBolt', 16)
    new = _replace(new, 'ri->footLBolt', 'stKickFootBolt', 4)
    marker = 'renderInfo_t *ri = &ent->client->renderInfo;'
    new = _replace(new, marker, marker + '''
    const int stMirrored=G_STPrepareHandPose(ent);
    const int stKickAnim=ent->client->ps.torsoAnim==BOTH_A7_HILT?BOTH_A7_HILT:ent->client->ps.legsAnim;
    const int stContact=ST_DirectionKickLimb(stKickAnim,stMirrored,level.framenum&1);
    const int stKickFootBolt=stContact==ST_CONTACT_LEFT_FOOT?ri->footLBolt:ri->footRBolt;
    const int stHiltHandBolt=stContact==ST_CONTACT_LEFT_HAND?ri->handLBolt:ri->handRBolt;
''')
    new = _replace(new, '\tif ( doKick )\n\t{', '''\tif ( doKick )
\t{
        if (stMirrored && stKickAnim==BOTH_A7_KICK_S && stKickFootBolt==-1) {
            vec3_t stRight,stAngles;
            float side;
            VectorSet(stAngles,0,ent->client->ps.viewangles[YAW],0);
            AngleVectors(stAngles,NULL,stRight,NULL);
            side=DotProduct(kickDir,stRight);
            VectorMA(kickDir,-2.0f*side,stRight,kickDir);
        }''')
    change(source, saber, old, '#include "st_direction_kick.h"\n\n' + new)
