#include "game/st_lock_game.h"
static centity_t *CG_STLockPeer(centity_t *cent) {
    int n=cent->currentState.otherEntityNum;
    centity_t *enemy;
    if(!cent->currentState.forceFrame || n<0 || n>=ENTITYNUM_WORLD || n==cent->currentState.number)return NULL;
    enemy=&cg_entities[n];
    if(!enemy->currentValid || !enemy->currentState.forceFrame ||
       enemy->currentState.otherEntityNum!=cent->currentState.number)return NULL;
    return enemy;
}
/* Pure transform calculation: do not overwrite another actor's already
 * rendered interpolation/smoothing/scale state while preparing this pair. */
static void CG_STLockTransform(const centity_t *cent,vec3_t origin,vec3_t scale) {
    int i;
    for(i=0;i<3;i++)scale[i]=cent->currentState.iModelScale?cent->currentState.iModelScale/100.0f:0;
    ST_LockModelOrigin(cent->currentState.pos.trBase,scale,origin);
}
static void CG_STLockRenderTransform(centity_t *cent) {
    centity_t *enemy=CG_STLockPeer(cent);
    if(!enemy || !(ST_HandFromFlags(cent->currentState.eFlags2)||ST_HandFromFlags(enemy->currentState.eFlags2)))return;
    CG_STLockTransform(cent,cent->lerpOrigin,cent->modelScale);
    cent->lerpAngles[YAW]=cent->currentState.apos.trBase[YAW];
    VectorCopy(cent->lerpOrigin,cent->beamEnd);
}
static void CG_STOriginalLockFrame(centity_t *cent) {
    int bone,frame=cent->currentState.forceFrame;
    cent->pe.legs.lastForcedFrame=cent->pe.torso.lastForcedFrame=-1;
    cent->pe.legs.stPoseValid=cent->pe.torso.stPoseValid=qfalse;
    if(!cent->ghoul2 || !frame)return;
    for(bone=0;bone<3;bone++)trap->G2API_SetBoneAnim(cent->ghoul2,0,
        bone==0?"model_root":bone==1?"lower_lumbar":"Motion",
        frame,frame+1,BONE_ANIM_OVERRIDE_FREEZE,1.0f,cg.time,frame,0);
    cent->pe.legs.lastForcedFrame=cent->pe.torso.lastForcedFrame=frame;
}
static void CG_STClearLockPose(centity_t *cent) {
    stLockPoseParams_t clear;
    memset(&clear,0,sizeof(clear));clear.size=sizeof(clear);clear.version=ST_LOCK_POSE_VERSION;
    clear.mode=ST_LOCK_POSE_CLEAR;
    if(cent->ghoul2)trap->G2API_STLockPose(cent->ghoul2,&clear);
    cent->stLockPoseModel=cent->ghoul2;
    cent->stLockPoseActive=cent->stLockPoseFailed=qfalse;cent->stLockPoseRelease=0;
}
static qboolean CG_STLockCandidate(centity_t *cent,centity_t *enemy,centity_t *a,centity_t *b,stLockPoseParams_t *next) {
    clientInfo_t *ci;
    vec3_t ao,bo,own,other,ownScale,otherScale,unused;
    float yaw=cent->currentState.apos.trBase[YAW];
    if(!cent->ghoul2 || !enemy->ghoul2 || cent->localAnimIndex<0 || cent->localAnimIndex>=MAX_ANIM_FILES ||
       enemy->localAnimIndex<0 || enemy->localAnimIndex>=MAX_ANIM_FILES)return qfalse;
    ci=cent->currentState.eType==ET_NPC?cent->npcClient:&cgs.clientinfo[cent->currentState.clientNum];
    if(!ci)return qfalse;
    CG_STLockTransform(a,ao,unused);CG_STLockTransform(b,bo,unused);
    CG_STLockTransform(cent,own,ownScale);CG_STLockTransform(enemy,other,otherScale);
    if(!ST_GameLockParams(next,bgAllAnims[cent->localAnimIndex].anims,
        cent->currentState.torsoAnim,ST_HandFromFlags(cent->currentState.eFlags2),cent->currentState.fireflag,ci->saber,
        ao,bo,own,yaw,ownScale))return qfalse;
    if(!ST_GameLockOpponent(next,enemy->ghoul2,bgAllAnims[enemy->localAnimIndex].anims,
        enemy->currentState.torsoAnim,ST_HandFromFlags(enemy->currentState.eFlags2),
        own,yaw,ownScale,other,enemy->currentState.apos.trBase[YAW],otherScale))return qfalse;
    next->progress=ST_GameLockProgress(bgAllAnims[a->localAnimIndex].anims,a->currentState.torsoAnim,a->currentState.forceFrame);
    return qtrue;
}
static void CG_STAcceptLockPose(centity_t *cent,centity_t *enemy,const stLockPoseParams_t *next) {
    cent->stLockPose=*next;cent->stLockPose.resolvedContactPath=NULL;
    cent->stLockPoseModel=cent->ghoul2;cent->stLockPoseEnemy=enemy->currentState.number;
    cent->stLockPoseAnim=cent->currentState.torsoAnim;
    cent->stLockPoseActive=qtrue;cent->stLockPoseFailed=qfalse;cent->stLockPoseRelease=0;
    cent->stLockStandardPose=qfalse;
    CG_STSyncHandAttachments(cent,cent->ghoul2);
}
/* A local display fallback cannot change the server's active hand or saved
 * preference. Retry next render frame; matching server assets are still needed
 * for exact agreement between this temporary visual pose and collision. */
static void CG_STCompatibleLockPair(centity_t *a,centity_t *b) {
    centity_t *actors[2]={a,b};int i;
    for(i=0;i<2;i++) {
        centity_t *cent=actors[i];
        CG_STClearLockPose(cent);
        if(!cent->stLockStandardPose || cent->pe.legs.lastForcedFrame!=cent->currentState.forceFrame ||
           cent->pe.torso.lastForcedFrame!=cent->currentState.forceFrame)CG_STOriginalLockFrame(cent);
        cent->stLockStandardPose=qtrue;
        cent->stLockPoseFailed=qtrue;cent->stLockPoseRelease=cg.time;
        CG_STSyncHandAttachments(cent,cent->ghoul2);
    }
}
static void CG_STUpdateLockPose(centity_t* cent,float yaw) {
    centity_t *enemy,*a,*b;
    int n;
    (void)yaw; /* The pair always uses the same canonical trajectory yaw. */
    if(cent->stLockPoseModel!=cent->ghoul2) {
        qboolean wasStandard=cent->stLockStandardPose;
        cent->stLockPoseModel=cent->ghoul2;
        cent->stLockPoseActive=cent->stLockPoseFailed=cent->stLockStandardPose=qfalse;
        cent->stLockPoseRelease=0;
        if(wasStandard)CG_STSyncHandAttachments(cent,cent->ghoul2);
    }
    if(cent->stLockStandardPose && (!cent->currentState.forceFrame || (cent->currentState.eFlags&EF_DEAD))) {
        cent->stLockStandardPose=qfalse;cent->stLockPoseFailed=qfalse;cent->stLockPoseRelease=0;
        CG_STSyncHandAttachments(cent,cent->ghoul2);
    }
    if(!cent->ghoul2)return;
    enemy=CG_STLockPeer(cent);
    if(enemy && !(cent->currentState.eFlags&EF_DEAD) && !(enemy->currentState.eFlags&EF_DEAD)) {
        a=cent->currentState.number<enemy->currentState.number?cent:enemy;b=a==cent?enemy:cent;
        if(!(ST_HandFromFlags(a->currentState.eFlags2)||ST_HandFromFlags(b->currentState.eFlags2))) {
            if(a->stLockPoseActive || b->stLockPoseActive || a->stLockStandardPose || b->stLockStandardPose) {
                CG_STClearLockPose(a);CG_STClearLockPose(b);
                a->stLockStandardPose=b->stLockStandardPose=qfalse;
                CG_STOriginalLockFrame(a);CG_STOriginalLockFrame(b);
                CG_STSyncHandAttachments(a,a->ghoul2);CG_STSyncHandAttachments(b,b->ghoul2);
            }
            return;
        }
        if(a->stLockPoseFailed && b->stLockPoseFailed && a->stLockPoseRelease==cg.time && b->stLockPoseRelease==cg.time)return;
        if(a->stLockStandardPose || b->stLockStandardPose) {
            /* Validation reads destination hilt links. Restore BOTH desired
             * grips before retry, or the temporary right links reject every
             * subsequent left candidate and make fallback permanent. */
            a->stLockStandardPose=b->stLockStandardPose=qfalse;
            CG_STSyncHandAttachments(a,a->ghoul2);CG_STSyncHandAttachments(b,b->ghoul2);
        }
        {
            stLockPoseParams_t na,nb;
            qboolean candidates=CG_STLockCandidate(a,b,a,b,&na)&&CG_STLockCandidate(b,a,a,b,&nb);
            if(candidates) {
                na.mode=nb.mode=ST_LOCK_POSE_VALIDATE;
                if(trap->G2API_STLockPose(a->ghoul2,&na)&&trap->G2API_STLockPose(b->ghoul2,&nb)) {
                    na.mode=nb.mode=ST_LOCK_POSE_UPDATE;
                    if(trap->G2API_STLockPose(a->ghoul2,&na)&&trap->G2API_STLockPose(b->ghoul2,&nb)) {
                        CG_STAcceptLockPose(a,b,&na);CG_STAcceptLockPose(b,a,&nb);return;
                    }
                    /* The first commit may have changed its track. Do not hold
                     * a mixture of old/new tracks after second-commit failure. */
                    CG_STCompatibleLockPair(a,b);return;
                }
                if(a->stLockPoseActive && b->stLockPoseActive && a->stLockPoseModel==a->ghoul2 && b->stLockPoseModel==b->ghoul2 &&
                   ST_LockPoseSameTrack(&a->stLockPose,&na)&&ST_LockPoseSameTrack(&b->stLockPose,&nb)) {
                    stLockPoseParams_t ca=a->stLockPose,cb=b->stLockPose;
                    ca.mode=cb.mode=ST_LOCK_POSE_CACHED;ca.progress=cb.progress=na.progress;ca.weight=cb.weight=1;
                    if(trap->G2API_STLockPose(a->ghoul2,&ca)&&trap->G2API_STLockPose(b->ghoul2,&cb)) {
                        a->stLockPose.progress=ca.progress;b->stLockPose.progress=cb.progress;
                        a->stLockPoseFailed=b->stLockPoseFailed=qtrue;a->stLockPoseRelease=b->stLockPoseRelease=cg.time;
                        return;
                    }
                }
            }
            CG_STCompatibleLockPair(a,b);return;
        }
    }
    if(cent->stLockPoseActive) {
        if(!cent->stLockPoseRelease || cent->stLockPoseFailed)cent->stLockPoseRelease=cg.time;
        cent->stLockPoseFailed=qfalse;
        cent->stLockPose.weight=1.0f-(cg.time-cent->stLockPoseRelease)/150.0f;
        n=cent->stLockPoseEnemy;
        if(cent->stLockPose.weight<=0 || (cent->currentState.eFlags&EF_DEAD) || n<0 || n>=ENTITYNUM_WORLD ||
           !cg_entities[n].currentValid || !cg_entities[n].ghoul2 ||
           cg_entities[n].ghoul2!=cent->stLockPose.opponentGhoul2)CG_STClearLockPose(cent);
        else {
            stLockPoseParams_t cached=cent->stLockPose;cached.mode=ST_LOCK_POSE_CACHED;
            if(!trap->G2API_STLockPose(cent->ghoul2,&cached))CG_STClearLockPose(cent);
        }
    }
}
