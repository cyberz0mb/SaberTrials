#include "st_lock_game.h"
/* Presentation/trace pose only. PM_SaberLocked remains the sole rule owner. */
static void G_STClearLockPose(gentity_t *self) {
    gclient_t *cl=self->client;
    stLockPoseParams_t clear;
    memset(&clear,0,sizeof(clear));clear.size=sizeof(clear);clear.version=ST_LOCK_POSE_VERSION;
    clear.mode=ST_LOCK_POSE_CLEAR;
    if(self->ghoul2)trap->G2API_STLockPose(self->ghoul2,&clear);
    cl->stLockPoseActive=cl->stLockPoseFailed=qfalse;cl->stLockPoseRelease=0;
}

static qboolean G_STLockCandidate(gentity_t *self,gentity_t *enemy,gentity_t *a,gentity_t *b,
    stLockPoseParams_t *next) {
    gclient_t *cl=self->client;
    vec3_t ao,bo,own,other;
    if(!self->ghoul2 || !enemy->ghoul2 || self->localAnimIndex<0 || self->localAnimIndex>=MAX_ANIM_FILES ||
       enemy->localAnimIndex<0 || enemy->localAnimIndex>=MAX_ANIM_FILES)return qfalse;
    ST_LockModelOrigin(a->client->ps.origin,a->modelScale,ao);
    ST_LockModelOrigin(b->client->ps.origin,b->modelScale,bo);
    ST_LockModelOrigin(cl->ps.origin,self->modelScale,own);
    ST_LockModelOrigin(enemy->client->ps.origin,enemy->modelScale,other);
    if(!ST_GameLockParams(next,bgAllAnims[self->localAnimIndex].anims,
        cl->ps.torsoAnim,ST_HandFromFlags(cl->ps.eFlags2),cl->ps.fd.saberAnimLevel,cl->saber,
        ao,bo,own,cl->ps.viewangles[YAW],self->modelScale))return qfalse;
    if(!ST_GameLockOpponent(next,enemy->ghoul2,bgAllAnims[enemy->localAnimIndex].anims,
        enemy->client->ps.torsoAnim,ST_HandFromFlags(enemy->client->ps.eFlags2),
        own,cl->ps.viewangles[YAW],self->modelScale,
        other,enemy->client->ps.viewangles[YAW],enemy->modelScale))return qfalse;
    next->progress=ST_GameLockProgress(bgAllAnims[a->localAnimIndex].anims,
        a->client->ps.torsoAnim,a->client->ps.saberLockFrame);
    return qtrue;
}

static void G_STAcceptLockPose(gentity_t *self,gentity_t *enemy,const stLockPoseParams_t *next) {
    gclient_t *cl=self->client;
    cl->stLockPose=*next;cl->stLockPose.resolvedContactPath=NULL;cl->stLockPoseModel=self->ghoul2;
    cl->stLockPoseEnemy=enemy->s.number;cl->stLockPoseAnim=cl->ps.torsoAnim;
    cl->stLockPoseActive=qtrue;cl->stLockPoseFailed=qfalse;cl->stLockPoseRelease=0;
    cl->stLegsPoseValid=cl->stTorsoPoseValid=qfalse;
    cl->legsAnimExecute=cl->torsoAnimExecute=-1;
}

/* Exceptional custom geometry can be impossible without changing equipment,
 * roots or arm lengths. Preserve the complete stock lock for BOTH actors:
 * publish the temporary physical grip, keep the saved spawn preference, and
 * restore it after the canonical lock ends. Never end or disable a lock. */
static void G_STCompatibleLockPair(gentity_t *a,gentity_t *b) {
    gentity_t *actors[2]={a,b};int i;
    for(i=0;i<2;i++) {
        gentity_t *self=actors[i];gclient_t *cl=self->client;
        G_STClearLockPose(self);cl->stLockStandardPose=qtrue;
        cl->ps.eFlags2=ST_HandSetFlag(cl->ps.eFlags2,ST_HAND_RIGHT);
        if(self->ghoul2 && self->localAnimIndex>=0 && self->localAnimIndex<MAX_ANIM_FILES) {
            int bone;
            G_STSyncHandAttachments(self);
            /* An unchanged canonical frame must replace every normal track
             * immediately; a blend would retain the former mirrored sample. */
            for(bone=0;bone<3;bone++)trap->G2API_SetBoneAnim(self->ghoul2,0,
                bone==0?"model_root":bone==1?"lower_lumbar":"Motion",
                cl->ps.saberLockFrame,cl->ps.saberLockFrame+1,BONE_ANIM_OVERRIDE_FREEZE,
                1.0f,level.time,cl->ps.saberLockFrame,0);
            cl->stLegsPoseValid=cl->stTorsoPoseValid=qfalse;
            cl->legsAnimExecute=cl->torsoAnimExecute=-1;
        }
    }
}

qboolean G_STUpdateLockPose(gentity_t* self) {
    gclient_t* cl=self->client;
    gentity_t *enemy,*a,*b;
    int n=cl->ps.saberLockEnemy;
    if(cl->stLockStandardPose && !cl->ps.saberLockFrame) {
        cl->stLockStandardPose=qfalse;
        cl->ps.eFlags2=ST_HandSetFlag(cl->ps.eFlags2,cl->pers.stHand);
        cl->stLegsPoseValid=cl->stTorsoPoseValid=qfalse;
        cl->legsAnimExecute=cl->torsoAnimExecute=-1;
        G_STSyncHandAttachments(self);
        if(self->ghoul2 && self->localAnimIndex>=0 && self->localAnimIndex<MAX_ANIM_FILES)
            G_UpdateClientAnims(self,1.0f);
    }
    if(cl->stLockPoseModel!=self->ghoul2) {
        cl->stLockPoseModel=self->ghoul2;
        cl->stLockPoseActive=cl->stLockPoseFailed=qfalse;cl->stLockPoseRelease=0;
    }
    if(!self->ghoul2)return qfalse;
    if(cl->stLockStandardPose && cl->ps.saberLockFrame)return qfalse;
    if(cl->ps.saberLockFrame && n>=0 && n<ENTITYNUM_WORLD && n!=self->s.number) {
        enemy=&g_entities[n];
        if(enemy->inuse && enemy->client && enemy->client->ps.saberLockFrame &&
           enemy->client->ps.saberLockEnemy==self->s.number &&
           (ST_HandFromFlags(cl->ps.eFlags2)||ST_HandFromFlags(enemy->client->ps.eFlags2))) {
            stLockPoseParams_t na,nb;
            a=self->s.number<n?self:enemy;b=self->s.number<n?enemy:self;
            if(!G_STLockCandidate(a,b,a,b,&na)||!G_STLockCandidate(b,a,a,b,&nb))goto compatible;
            na.mode=nb.mode=ST_LOCK_POSE_VALIDATE;
            if(!trap->G2API_STLockPose(a->ghoul2,&na)||!trap->G2API_STLockPose(b->ghoul2,&nb))goto compatible;
            na.mode=nb.mode=ST_LOCK_POSE_UPDATE;
            /* Seeds and attachments are immutable through these two calls.
             * Even a defensive second-commit failure clears BOTH overrides. */
            if(!trap->G2API_STLockPose(a->ghoul2,&na)||!trap->G2API_STLockPose(b->ghoul2,&nb))goto compatible;
            G_STAcceptLockPose(a,b,&na);G_STAcceptLockPose(b,a,&nb);return qtrue;
compatible:
            G_STCompatibleLockPair(a,b);return qfalse;
        }
    }
    if(cl->stLockPoseActive) {
        if(!cl->stLockPoseRelease)cl->stLockPoseRelease=level.time;
        cl->stLockPose.weight=1.0f-(level.time-cl->stLockPoseRelease)/150.0f;
        n=cl->stLockPoseEnemy;
        if(cl->stLockPose.weight<=0 || (cl->ps.eFlags&EF_DEAD) || n<0 || n>=ENTITYNUM_WORLD ||
           !g_entities[n].inuse || !g_entities[n].client || !g_entities[n].ghoul2 ||
           g_entities[n].ghoul2!=cl->stLockPose.opponentGhoul2) {
            G_STClearLockPose(self);
        } else {
            stLockPoseParams_t cached=cl->stLockPose;cached.mode=ST_LOCK_POSE_CACHED;
            if(!trap->G2API_STLockPose(self->ghoul2,&cached))G_STClearLockPose(self);
        }
    }
    return qfalse;
}
