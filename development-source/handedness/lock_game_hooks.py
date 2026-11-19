"""Canonical mixed-hand lock callers; engine sampler owns pose synthesis."""
def apply(source,change):
    for path,marker in (('codemp/game/g_local.h','\tstDirectionalPlayback_t stLegsPose, stTorsoPose;'),
                        ('codemp/cgame/cg_local.h','\tqboolean stHandPoseFallback, stHandPoseValidated;')):
        change(source,path,'#include "game/st_direction_timing.h"' if '/cgame/' in path else '#include "st_direction_timing.h"',
               ('#include "game/st_direction_timing.h"' if '/cgame/' in path else '#include "st_direction_timing.h"')+'\n#include "ghoul2/st_lock_pose.h"')
        change(source,path,marker,marker+'''
    stLockPoseParams_t stLockPose;
    void *stLockPoseModel;
    qboolean stLockPoseActive, stLockPoseFailed;
    qboolean stLockStandardPose;
    int stLockPoseEnemy, stLockPoseAnim, stLockPoseRelease;
''')
    change(source,'codemp/game/g_client.c','#include "g_hand_anim.inc"',
           '#include "g_hand_anim.inc"\n#include "g_hand_lock.inc"')
    change(source,'codemp/game/g_local.h','qboolean G_STPrepareHandPose(gentity_t *self);',
           'qboolean G_STPrepareHandPose(gentity_t *self);\nqboolean G_STUpdateLockPose(gentity_t *self);')
    change(source,'codemp/game/w_saber.c','\tUpdateClientRenderinfo(self, properOrigin, properAngles);',
           '\tG_STUpdateLockPose(self);\n\tUpdateClientRenderinfo(self, properOrigin, properAngles);')
    change(source,'codemp/cgame/cg_players.c','#include "cg_hand_anim.inc"',
           '#include "cg_hand_anim.inc"\n#include "cg_hand_lock.inc"')
    marker='\tCG_G2PlayerAngles( cent, legs.axis, rootAngles );'
    change(source,'codemp/cgame/cg_players.c',marker,'\tCG_STUpdateLockPose(cent,cent->lerpAngles[YAW]);\n'+marker)
    change(source,'codemp/game/bg_misc.c','s->forceFrame = ps->saberLockFrame;',
           's->forceFrame = ps->saberLockFrame;\n'
           '\t// ET_PLAYER/NPC lock partner; otherEntityNum is otherwise unused for player state.\n'
           '\ts->otherEntityNum = ps->saberLockFrame ? ps->saberLockEnemy : ENTITYNUM_NONE;',2)
