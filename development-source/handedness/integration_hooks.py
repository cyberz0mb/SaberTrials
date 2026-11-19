"""Cross-cutting state/pose synchronization, after state and animation hooks."""
LOCK_END_RECONCILE = '''    /* Pmove can end a compatibility lock after this frame's saber update.
     * Restore the saved active hand before any ClientEndFrame early return or
     * state publication, including spectator/intermission/staff paths. */
    if(ent->client && ent->client->stLockStandardPose && !ent->client->ps.saberLockFrame) {
        G_STUpdateLockPose(ent);
        ent->s.eFlags2=ST_HandSetFlag(ent->s.eFlags2,ent->client->pers.stHand);
    }
'''

def apply(source,change):
    game='codemp/game/g_client.c'
    change(source,'codemp/game/g_active.c','void ClientEndFrame( gentity_t *ent ) {',
           'void ClientEndFrame( gentity_t *ent ) {\n'+LOCK_END_RECONCILE)
    change(source,game,'#include "g_hand_anim.inc"',
           '#include "g_hand_attachment.inc"\n#include "g_hand_anim.inc"')
    change(source,'codemp/cgame/cg_players.c','#include "cg_hand_anim.inc"',
           '#include "cg_hand_attachment.inc"\n#include "cg_hand_anim.inc"')
    change(source,'codemp/cgame/cg_hand_attachment.inc',
           'hand=ST_HandEffective(cent->currentState.eFlags2,cent->currentState.m_iVehicleNum);',
           'hand=cent->stLockStandardPose?ST_HAND_RIGHT:ST_HandEffective(cent->currentState.eFlags2,cent->currentState.m_iVehicleNum);')
    change(source,'codemp/cgame/cg_local.h','qboolean CG_STPrepareHandPose(centity_t *cent);',
           'qboolean CG_STPrepareHandPose(centity_t *cent);\nvoid CG_STSyncHandAttachments(centity_t *cent,void *instance);')
    change(source,game,'\tif (G_STUpdateNormalAnimations(self,animSpeedScale)) return;',
           '\tG_STSyncHandAttachments(self);\n\tif (G_STUpdateNormalAnimations(self,animSpeedScale)) return;')
    change(source,'codemp/game/g_hand_anim.inc','    mirrored=G_STPrepareHandPose(self);',
           '''    if(self->client->ps.m_iVehicleNum || self->s.NPC_class==CLASS_VEHICLE) {
        if(self->client->stLegsPoseValid || self->client->stTorsoPoseValid)G_STUnmirrorAll(self);
        return qfalse; /* Preserve stock mounted animation, including vehicle-only rigs. */
    }
    mirrored=G_STPrepareHandPose(self);''')
    change(source,'codemp/cgame/cg_hand_anim.inc','    mirrored=CG_STPrepareHandPose(cent);\n    speed=',
           '''    if(cent->currentState.m_iVehicleNum || cent->currentState.NPC_class==CLASS_VEHICLE) {
        if(cent->pe.legs.stPoseValid || cent->pe.torso.stPoseValid)CG_STUnmirrorAll(cent);
        return qfalse;
    }
    mirrored=CG_STPrepareHandPose(cent);
    speed=''')
    change(source,'codemp/cgame/cg_hand_anim.inc','    int mirrored;\n    if (!ST_HandFromFlags',
           '''    int mirrored;
    if((cent->currentState.m_iVehicleNum || cent->currentState.NPC_class==CLASS_VEHICLE) && !lf->stPoseValid)return qfalse;
    if (!ST_HandFromFlags''')
    marker='\t// check for malformed or illegal info strings'
    change(source,game,marker,'''    if(g_saberHandedness.integer && !(ent->r.svFlags&SVF_BOT) &&
       strcmp(Info_ValueForKey(userinfo,"st_handProtocol"),"1")) {
        trap->DropClient(clientNum,"This server requires the updated Saber Trials renderer and client.");
        return qfalse;
    }
'''+marker)
    change(source,'codemp/game/g_hand_anim.inc','        G_STUnmirrorAll(self);',
           '''        G_STUnmirrorAll(self);
        self->client->pers.stHand=ST_HAND_RIGHT;
        self->client->ps.eFlags2=ST_HandSetFlag(self->client->ps.eFlags2,ST_HAND_RIGHT);
        G_SaberModelSetup(self);
        if(self->s.number<MAX_CLIENTS)ClientUserinfoChanged(self->s.number);''')
    change(source,'codemp/cgame/cg_hand_anim.inc','        CG_STUnmirrorAll(cent);',
           '''        CG_STUnmirrorAll(cent);
        trap->Error(ERR_DROP,"This animation pack cannot display left-handed saber combat. Use the matching Saber Trials animation files.");''')
    # Reused heap addresses do not prove the same G2 model instance/rig.
    change(source,game,'\t//Attach the instance to this entity num so we can make use of client-server',
           '''    if(ent->client) {
        ent->client->stHandPoseValidated=qfalse;
        ent->client->stHandPoseFallback=qfalse;
        ent->client->stLegsPoseValid=ent->client->stTorsoPoseValid=qfalse;
        ent->client->stLockPoseActive=qfalse;
        ent->client->stLockPoseFailed=qfalse;
        ent->client->stLockPoseModel=NULL;
        ent->client->stLockPoseRelease=0;
    }
\t//Attach the instance to this entity num so we can make use of client-server''')
    change(source,'codemp/cgame/cg_local.h','qboolean CG_STPrepareHandPose(centity_t *cent);',
           'qboolean CG_STPrepareHandPose(centity_t *cent);\nvoid CG_STResetHandModel(centity_t *cent);')
    change(source,'codemp/cgame/cg_players.c','#include "cg_hand_lock.inc"',
           '''#include "cg_hand_lock.inc"
void CG_STResetHandModel(centity_t *cent) {
    cent->stHandPoseModel=NULL;
    cent->stHandPoseValidated=cent->stHandPoseFallback=qfalse;
    cent->pe.legs.stPoseValid=cent->pe.torso.stPoseValid=qfalse;
    cent->pe.legs.stPoseSkipEvents=cent->pe.torso.stPoseSkipEvents=qtrue;
    cent->stLockPoseModel=NULL;
    cent->stLockPoseActive=cent->stLockPoseFailed=qfalse;
    cent->stLockPoseRelease=0;
    ++cent->stHandPoseRevision;
}
''')
    # Explicit lifecycle reset also covers an allocator reusing the old address.
    for path,call,entity,count in (
        ('codemp/cgame/cg_players.c','trap->G2API_DuplicateGhoul2Instance(ci->ghoul2Model, &cg_entities[clientNum].ghoul2);','&cg_entities[clientNum]',3),
        ('codemp/cgame/cg_players.c','trap->G2API_DuplicateGhoul2Instance(ci->ghoul2Model, &cent->ghoul2);','cent',3),
        ('codemp/cgame/cg_players.c','trap->G2API_InitGhoul2Model(&cent->ghoul2, modelName, 0, skinID, 0, 0, 0);','cent',1),
        ('codemp/cgame/cg_ents.c','trap->G2API_DuplicateGhoul2Instance(clEnt->ghoul2, &cent->ghoul2);','cent',1),
    ):
        change(source,path,call,call+'\n\t\tCG_STResetHandModel('+entity+');',count)
    # The left-hand path uses one pose-speed/blend policy on both sides. Physics
    # timers, input and ordinary right-hand playback are unchanged.
    change(source,'codemp/game/g_hand_anim.inc','        if (channel) BG_SaberStartTransAnim',
           '''        if(ST_HandFromFlags(self->client->ps.eFlags2)) {
            const int rage=self->client->ps.fd.forcePowersActive&(1<<FP_RAGE);
            const int fast=self->client->ps.fd.forcePowersActive&(1<<FP_SPEED);
            if(channel)scale=rage?1.7f:1.0f;
            else if(PM_RunningAnim(anim)||PM_WalkingAnim(anim))scale=rage?1.3f:fast?1.7f:1.0f;
            else scale=1.0f;
        }
        if (channel || ST_HandFromFlags(self->client->ps.eFlags2)) BG_SaberStartTransAnim''')
    change(source,'codemp/game/g_hand_anim.inc','        blend=(*valid && old->mirrored==mirrored)?150:0;',
           '''        blend=(*valid && old->mirrored==mirrored && !BG_InDeathAnim(anim) &&
            !BG_InDeathAnim(old->semanticAnim))?100:0;
        if(blend && (BG_FlippingAnim(anim)||BG_FlippingAnim(old->semanticAnim)))blend=200;''')
    change(source,'codemp/cgame/cg_hand_anim.inc','if (cg_animBlend.integer && !modeChange && !BG_InDeathAnim(anim) &&',
           'if ((cg_animBlend.integer || ST_HandFromFlags(cent->currentState.eFlags2)) && !modeChange && !BG_InDeathAnim(anim) &&')
    change(source,game,'#include "g_hand_anim.inc"',
           'qboolean PM_WalkingAnim(int anim);\n#include "g_hand_anim.inc"')
    # Update the collision pose before this frame's bolt/trace queries.
    change(source,'codemp/game/w_saber.c','\tG_STUpdateLockPose(self);',
           '\tif(ST_HandFromFlags(self->client->ps.eFlags2) && !self->client->ps.saberLockFrame)G_UpdateClientAnims(self,animSpeedScale);\n\tG_STUpdateLockPose(self);\n\tif(self->client->ps.saberLockFrame && self->client->stLockPoseActive)ST_LockModelOrigin(self->client->ps.origin,self->modelScale,properOrigin);')
    change(source,'codemp/game/w_saber.c','#include "g_local.h"',
           '#include "g_local.h"\n#include "st_lock_logic.h"')
    change(source,'codemp/game/w_saber.c','\tif (BG_KickingAnim(self->client->ps.legsAnim))\n\t{ //do some kick traces',
           '\tif(ST_HandFromFlags(self->client->ps.eFlags2) && !self->client->ps.saberLockFrame)G_UpdateClientAnims(self,animSpeedScale);\n\tif (BG_KickingAnim(self->client->ps.legsAnim))\n\t{ //do some kick traces')
    cg='codemp/cgame/cg_players.c'
    change(source,cg,'\tif (cent->currentState.m_iVehicleNum &&\n\t\tcent->currentState.NPC_class != CLASS_VEHICLE)',
           '\tCG_STLockRenderTransform(cent);\n\tif (cent->currentState.m_iVehicleNum &&\n\t\tcent->currentState.NPC_class != CLASS_VEHICLE)')
    change(source,cg,'void CG_Player( centity_t *cent ) {',
           'void CG_Player( centity_t *cent ) {\n\tqboolean stHandEarlyAnimation=qfalse;')
    change(source,cg,'\tCG_STUpdateLockPose(cent,cent->lerpAngles[YAW]);',
           '''    CG_STSyncHandAttachments(cent,cent->ghoul2);
    stHandEarlyAnimation=ST_HandFromFlags(cent->currentState.eFlags2) ||
        cent->pe.legs.stPoseValid || cent->pe.torso.stPoseValid || cent->stLockPoseActive;
    if(stHandEarlyAnimation) {
        int unusedOld,unusedFrame;float unusedLerp;
        /* Consume the old animation's events once, then establish today's pose
         * before IK, cached hand matrices, saber effects and blade queries. */
        CG_TriggerAnimSounds(cent);
        CG_PlayerAnimation(cent,&legs.oldframe,&legs.frame,&legs.backlerp,
            &unusedOld,&unusedFrame,&unusedLerp);
    }
\tCG_STUpdateLockPose(cent,cent->lerpAngles[YAW]);''')
    change(source,cg,'''\t//trigger animation-based sounds, done before next lerp frame.
\tCG_TriggerAnimSounds(cent);

\t// get the animation state (after rotation, to allow feet shuffle)
\tCG_PlayerAnimation( cent, &legs.oldframe, &legs.frame, &legs.backlerp,
\t\t &torso.oldframe, &torso.frame, &torso.backlerp );''',
           '''    if(!stHandEarlyAnimation) {
        // Ordinary right-handed playback retains its original ordering.
        CG_TriggerAnimSounds(cent);
        CG_PlayerAnimation(cent,&legs.oldframe,&legs.frame,&legs.backlerp,
            &torso.oldframe,&torso.frame,&torso.backlerp);
    } else {
        torso.oldframe=cent->pe.torso.oldFrame;
        torso.frame=cent->pe.torso.frame;
        torso.backlerp=cent->pe.torso.backlerp;
    }''')
    change(source,cg,'trap->G2API_GetBoltMatrix(cent->ghoul2, 0, ci->bolt_rhand, &boltMatrix, tAng, cent->lerpOrigin, cg.time, cgs.gameModels, cent->modelScale);',
           'trap->G2API_GetBoltMatrix(cent->ghoul2, 0, ST_HandEffective(cent->currentState.eFlags2,cent->currentState.m_iVehicleNum)?ci->bolt_lhand:ci->bolt_rhand, &boltMatrix, tAng, cent->lerpOrigin, cg.time, cgs.gameModels, cent->modelScale);')
    change(source,cg,'trap->G2API_CopySpecificGhoul2Model(CG_G2WeaponInstance(cent, WP_SABER), 0, cent->ghoul2, 1);',
           'trap->G2API_CopySpecificGhoul2Model(CG_G2WeaponInstance(cent, WP_SABER), 0, cent->ghoul2, 1);\n                CG_STSyncHandAttachments(cent,cent->ghoul2);')
    # This cached matrix is used by the Force effects only. Anatomical arm IK
    # elsewhere still uses its original named bone and is not reassigned.
    mirrored='(cent->currentState.weapon==WP_SABER && ST_HandEffective(cent->currentState.eFlags2,cent->currentState.m_iVehicleNum))'
    old='trap->G2API_GetBoltMatrix(cent->ghoul2, 0, ci->bolt_lhand, &lHandMatrix, cent->turAngles, cent->lerpOrigin, cg.time, cgs.gameModels, cent->modelScale);'
    change(source,cg,old,old.replace('ci->bolt_lhand',mirrored+'?ci->bolt_rhand:ci->bolt_lhand'),4)
    old='trap->G2API_GetBoltMatrix(cent->ghoul2, 0, ci->bolt_rhand, &rHandMatrix, cent->turAngles, cent->lerpOrigin, cg.time, cgs.gameModels, cent->modelScale);'
    change(source,cg,old,old.replace('ci->bolt_rhand',mirrored+'?ci->bolt_lhand:ci->bolt_rhand'))
