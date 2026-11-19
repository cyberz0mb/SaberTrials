/* Included by g_client.c. This adapts collision pose playback, not game state. */
static void G_STUnmirrorAll(gentity_t *self)
{
    int channel;
    for (channel=0;channel<2;++channel) {
        stDirectionalPlayback_t *old=channel?&self->client->stTorsoPose:&self->client->stLegsPose,p;
        qboolean valid=channel?self->client->stTorsoPoseValid:self->client->stLegsPoseValid;
        int anim=channel?self->client->ps.torsoAnim:self->client->ps.legsAnim;
        const char *bone=channel?"lower_lumbar":"model_root";
        animation_t *animations=bgAllAnims[self->localAnimIndex].anims;
        float speed,frame=-1,sampled=0;
        if (channel && self->noLumbar) continue;
        if (anim<0 || anim>=MAX_TOTALANIMATIONS || !animations[anim].frameLerp) continue;
        speed=valid?old->canonicalSpeed:50.0f/animations[anim].frameLerp;
        if (ST_BuildDirectionalPlayback(animations,MAX_TOTALANIMATIONS,anim,0,speed,&p)) {
            if (valid && old->clocked) {
                sampled=ST_DirectionClockPose(old,level.time);
                ST_DirectionResumeFrame(old,&p,sampled,&frame);
            } else if (valid && trap->G2API_GetBoneFrame(self->ghoul2,bone,level.time,&sampled,NULL,0))
                ST_DirectionResumeFrame(old,&p,sampled,&frame);
            trap->G2API_SetBoneAnim(self->ghoul2,0,bone,p.poseFirst,p.poseEnd,
                p.looping?BONE_ANIM_OVERRIDE_LOOP:BONE_ANIM_OVERRIDE_FREEZE,p.poseSpeed,level.time,frame,0);
            if (channel && self->localAnimIndex<=1)
                trap->G2API_SetBoneAnim(self->ghoul2,0,"Motion",p.poseFirst,p.poseEnd,
                    p.looping?BONE_ANIM_OVERRIDE_LOOP:BONE_ANIM_OVERRIDE_FREEZE,p.poseSpeed,level.time,frame,0);
        }
    }
    /* Clear every track even when current animation metadata is corrupt. */
    for (channel=0;channel<3;++channel) {
        const char *bone=channel==0?"model_root":channel==1?"lower_lumbar":"Motion";
        float frame=0,speed=0;
        int first=0,end=0,flags=0;
        if (trap->G2API_GetBoneAnim(self->ghoul2,bone,level.time,&frame,&first,&end,&flags,&speed,NULL,0) &&
            (flags&BONE_ANIM_MIRROR))
            trap->G2API_SetBoneAnim(self->ghoul2,0,bone,first,end,
                flags&~(BONE_ANIM_MIRROR|BONE_ANIM_BLEND),speed,level.time,frame,0);
    }
    self->client->stLegsPoseValid=self->client->stTorsoPoseValid=qfalse;
    self->client->legsAnimExecute=self->client->torsoAnimExecute=-1;
}

static void G_STPoseFallback(gentity_t *self,int anim,const char *reason)
{
    if (!self->client->stHandPoseFallback) {
        self->client->stHandPoseFallback=qtrue;
        ++self->client->stHandPoseRevision;
        trap->Print("Saber Trials: entity %d handedness pose fallback (%s, anim %d); whole-actor right-hand attachment refresh required.\n",
            self->s.number,reason,anim);
        G_STUnmirrorAll(self);
        self->client->pers.stHand=ST_HAND_RIGHT;
        self->client->ps.eFlags2=ST_HandSetFlag(self->client->ps.eFlags2,ST_HAND_RIGHT);
        G_SaberModelSetup(self);
        if(self->s.number<MAX_CLIENTS)ClientUserinfoChanged(self->s.number);
    }
}

/* Call at model/spawn preflight and before attachment/bolt/collision work.
 * Parent integration must replicate a defensive fallback before continuing. */
qboolean G_STPrepareHandPose(gentity_t *self)
{
    int bad=-1;
    if (!self || !self->client || !self->ghoul2 || self->localAnimIndex<0) return qfalse;
    if (self->client->stHandPoseModel!=self->ghoul2) {
        self->client->stHandPoseModel=self->ghoul2;
        self->client->stHandPoseValidated=qfalse;
        self->client->stHandPoseFallback=qfalse;
        ++self->client->stHandPoseRevision;
        self->client->stLegsPoseValid=self->client->stTorsoPoseValid=qfalse;
    }
    if (!ST_HandFromFlags(self->client->ps.eFlags2)) return qfalse;
    if (!self->client->stHandPoseValidated) {
        self->client->stHandPoseValidated=qtrue;
        if (self->localAnimIndex>1 ||
            !ST_DirectionValidateAnimationSet(bgAllAnims[self->localAnimIndex].anims,
                MAX_TOTALANIMATIONS,&bad))
            G_STPoseFallback(self,bad,"animation set preflight failed");
    }
    return !self->client->stHandPoseFallback && self->client->ps.weapon==WP_SABER;
}

static qboolean G_STUpdateNormalAnimations(gentity_t *self,float canonicalScale)
{
    int channel,mirrored;
    if (!self->client || !self->ghoul2) return qfalse;
    if (self->client->ps.saberLockFrame) {
        self->client->stLegsPoseValid=self->client->stTorsoPoseValid=qfalse;
        return qfalse; /* Existing locks remain active, owned by lock adapter. */
    }
    if (!ST_HandFromFlags(self->client->ps.eFlags2) &&
        !self->client->stLegsPoseValid && !self->client->stTorsoPoseValid) return qfalse;
    if(self->client->ps.m_iVehicleNum || self->s.NPC_class==CLASS_VEHICLE) {
        if(self->client->stLegsPoseValid || self->client->stTorsoPoseValid)G_STUnmirrorAll(self);
        return qfalse; /* Preserve stock mounted animation, including vehicle-only rigs. */
    }
    mirrored=G_STPrepareHandPose(self);
    for (channel=0;channel<2;++channel) {
        stDirectionalPlayback_t next,*old=channel?&self->client->stTorsoPose:&self->client->stLegsPose;
        stDirectionalPlayback_t *other=channel?&self->client->stLegsPose:&self->client->stTorsoPose;
        qboolean *valid=channel?&self->client->stTorsoPoseValid:&self->client->stLegsPoseValid;
        qboolean otherValid=channel?self->client->stLegsPoseValid:self->client->stTorsoPoseValid;
        qboolean flip=channel?self->client->ps.torsoFlip:self->client->ps.legsFlip;
        qboolean oldFlip=channel?self->client->torsoLastFlip:self->client->legsLastFlip;
        qboolean otherFlip=channel?self->client->legsLastFlip:self->client->torsoLastFlip;
        qboolean expectedOtherFlip=channel?self->client->ps.legsFlip:self->client->ps.torsoFlip;
        int anim=channel?self->client->ps.torsoAnim:self->client->ps.legsAnim;
        const char *bone=channel?"lower_lumbar":"model_root";
        const char *otherBone=channel?"model_root":"lower_lumbar";
        animation_t *a;
        float speed,scale=canonicalScale,frame=-1,sampled=0;
        int flags,blend;
        qboolean continuing;
        const stDirectionalPlayback_t *clockSource=NULL;
        if (channel && self->noLumbar) continue;
        if (anim<0 || anim>=MAX_TOTALANIMATIONS) return qfalse;
        a=&bgAllAnims[self->localAnimIndex].anims[anim];
        if(ST_HandFromFlags(self->client->ps.eFlags2)) {
            const int rage=self->client->ps.fd.forcePowersActive&(1<<FP_RAGE);
            const int fast=self->client->ps.fd.forcePowersActive&(1<<FP_SPEED);
            if(channel)scale=rage?1.7f:1.0f;
            else if(PM_RunningAnim(anim)||PM_WalkingAnim(anim))scale=rage?1.3f:fast?1.7f:1.0f;
            else scale=1.0f;
        }
        if (channel || ST_HandFromFlags(self->client->ps.eFlags2)) BG_SaberStartTransAnim(self->s.number,self->client->ps.fd.saberAnimLevel,
            self->client->ps.weapon,anim,&scale,self->client->ps.brokenLimbs);
        speed=a->frameLerp?(50.0f/a->frameLerp)*scale:0;
        if (!ST_BuildDirectionalPlayback(bgAllAnims[self->localAnimIndex].anims,
            MAX_TOTALANIMATIONS,anim,mirrored,speed,&next)) {
            if (mirrored) G_STPoseFallback(self,anim,"current clip unsupported");
            return qfalse;
        }
        continuing=*valid && old->semanticAnim==anim && oldFlip==flip;
        if (continuing && old->mirrored==mirrored && !next.clocked &&
            fabs(old->canonicalSpeed-next.canonicalSpeed)<0.00001f) continue;
        if (continuing && old->clocked) {
            clockSource=old;
            sampled=ST_DirectionClockPose(old,level.time);
            ST_DirectionResumeFrame(old,&next,sampled,&frame);
        } else if (continuing &&
            trap->G2API_GetBoneFrame(self->ghoul2,bone,level.time,&sampled,NULL,0))
            ST_DirectionResumeFrame(old,&next,sampled,&frame);
        if (!self->noLumbar && self->client->ps.legsAnim==self->client->ps.torsoAnim &&
            otherValid && other->semanticAnim==anim && otherFlip==expectedOtherFlip) {
            if (other->clocked) {
                clockSource=other;
                sampled=ST_DirectionClockPose(other,level.time);
                ST_DirectionResumeFrame(other,&next,sampled,&frame);
            } else if (trap->G2API_GetBoneFrame(self->ghoul2,otherBone,level.time,&sampled,NULL,0))
                ST_DirectionResumeFrame(other,&next,sampled,&frame);
        }
        if (next.clocked) {
            float canonical=frame<0?(float)next.canonicalFirst:ST_DirectionCanonicalFrame(&next,frame);
            ST_DirectionClockContinue(&next,clockSource,canonical,level.time);
            frame=ST_DirectionPoseFrame(&next,canonical);
            next.poseSpeed=ST_DirectionSpeedAtFrame(&next,canonical);
        }
        flags=next.looping?BONE_ANIM_OVERRIDE_LOOP:BONE_ANIM_OVERRIDE_FREEZE;
        if (mirrored) flags|=BONE_ANIM_MIRROR;
        blend=(*valid && old->mirrored==mirrored && !BG_InDeathAnim(anim) &&
            !BG_InDeathAnim(old->semanticAnim))?100:0;
        if(blend && (BG_FlippingAnim(anim)||BG_FlippingAnim(old->semanticAnim)))blend=200;
        if (continuing && next.clocked) blend=0; /* Rebase, not a new transition. */
        if (blend) flags|=BONE_ANIM_BLEND;
        if (!trap->G2API_SetBoneAnim(self->ghoul2,0,bone,next.poseFirst,next.poseEnd,
            flags,next.poseSpeed,level.time,frame,blend)) {
            if (mirrored) G_STPoseFallback(self,anim,"Ghoul2 mirror rejected");
            return qfalse;
        }
        if (channel && self->localAnimIndex<=1 && !trap->G2API_SetBoneAnim(self->ghoul2,0,"Motion",
            next.poseFirst,next.poseEnd,flags,next.poseSpeed,level.time,frame,blend)) {
            if (mirrored) G_STPoseFallback(self,anim,"Motion mirror rejected");
            return qfalse;
        }
        *old=next; *valid=qtrue;
        if (channel) { self->client->torsoAnimExecute=anim; self->client->torsoLastFlip=flip; }
        else { self->client->legsAnimExecute=anim; self->client->legsLastFlip=flip; }
    }
    return qtrue;
}
