/* Included by cg_players.c. Canonical game state is never remapped here. */
static void CG_STUnmirrorAll(centity_t *cent)
{
    int channel;
    for (channel=0; channel<2; ++channel) {
        lerpFrame_t *lf=channel?&cent->pe.torso:&cent->pe.legs;
        const char *bone=channel?"lower_lumbar":"model_root";
        int anim=channel?cent->currentState.torsoAnim:cent->currentState.legsAnim;
        stDirectionalPlayback_t p;
        float frame=-1, sampled=0, speed;
        animation_t *animations=bgAllAnims[cent->localAnimIndex].anims;
        if (channel && cent->noLumbar) continue;
        if (anim<0 || anim>=MAX_TOTALANIMATIONS || !animations[anim].frameLerp) continue;
        speed=lf->stPoseValid?lf->stPose.canonicalSpeed:50.0f/animations[anim].frameLerp;
        if (ST_BuildDirectionalPlayback(animations,MAX_TOTALANIMATIONS,anim,0,speed,&p)) {
            if (lf->stPoseValid && lf->stPose.clocked) {
                sampled=ST_DirectionClockPose(&lf->stPose,cg.time);
                ST_DirectionResumeFrame(&lf->stPose,&p,sampled,&frame);
            } else if (lf->stPoseValid && trap->G2API_GetBoneFrame(cent->ghoul2,bone,cg.time,&sampled,NULL,0))
                ST_DirectionResumeFrame(&lf->stPose,&p,sampled,&frame);
            trap->G2API_SetBoneAnim(cent->ghoul2,0,bone,p.poseFirst,p.poseEnd,
                p.looping?BONE_ANIM_OVERRIDE_LOOP:BONE_ANIM_OVERRIDE_FREEZE,p.poseSpeed,cg.time,frame,0);
            if (channel && cent->localAnimIndex<=1)
                trap->G2API_SetBoneAnim(cent->ghoul2,0,"Motion",p.poseFirst,p.poseEnd,
                    p.looping?BONE_ANIM_OVERRIDE_LOOP:BONE_ANIM_OVERRIDE_FREEZE,p.poseSpeed,cg.time,frame,0);
        }
        lf->stPoseValid=qfalse;
        lf->stPoseSkipEvents=qtrue;
    }
    /* Even corrupt/missing current clip metadata must not leave a mirrored
     * track behind. The ordinary setter will replace this temporary range. */
    for (channel=0;channel<3;++channel) {
        const char *bone=channel==0?"model_root":channel==1?"lower_lumbar":"Motion";
        float frame=0,speed=0;
        int first=0,end=0,flags=0;
        if (trap->G2API_GetBoneAnim(cent->ghoul2,bone,cg.time,&frame,&first,&end,&flags,&speed,NULL,0) &&
            (flags&BONE_ANIM_MIRROR))
            trap->G2API_SetBoneAnim(cent->ghoul2,0,bone,first,end,
                flags&~(BONE_ANIM_MIRROR|BONE_ANIM_BLEND),speed,cg.time,frame,0);
    }
    cent->pe.legs.stPoseValid=cent->pe.torso.stPoseValid=qfalse;
    cent->pe.legs.stPoseSkipEvents=cent->pe.torso.stPoseSkipEvents=qtrue;
}

static void CG_STPoseFallback(centity_t *cent,int anim,const char *reason)
{
    if (!cent->stHandPoseFallback) {
        cent->stHandPoseFallback=qtrue;
        ++cent->stHandPoseRevision;
        trap->Print("Saber Trials: entity %d handedness pose fallback (%s, anim %d); whole-actor right-hand attachment refresh required.\n",
            cent->currentState.number,reason,anim);
        CG_STUnmirrorAll(cent);
        trap->Error(ERR_DROP,"This animation pack cannot display left-handed saber combat. Use the matching Saber Trials animation files.");
    }
}

/* Call before attachment selection/render, not only from the anim setter.
 * Root integration owns synchronizing a defensive fallback with the server. */
qboolean CG_STPrepareHandPose(centity_t *cent)
{
    int bad=-1;
    if (!cent || !cent->ghoul2 || cent->localAnimIndex<0) return qfalse;
    if (cent->stHandPoseModel!=cent->ghoul2) {
        cent->stHandPoseModel=cent->ghoul2;
        cent->stHandPoseValidated=qfalse;
        cent->stHandPoseFallback=qfalse;
        ++cent->stHandPoseRevision;
        cent->pe.legs.stPoseValid=cent->pe.torso.stPoseValid=qfalse;
    }
    if (!ST_HandFromFlags(cent->currentState.eFlags2)) return qfalse;
    if (!cent->stHandPoseValidated) {
        cent->stHandPoseValidated=qtrue;
        if (cent->localAnimIndex>1 ||
            !ST_DirectionValidateAnimationSet(bgAllAnims[cent->localAnimIndex].anims,
                MAX_TOTALANIMATIONS,&bad))
            CG_STPoseFallback(cent,bad,"animation set preflight failed");
    }
    return !cent->stHandPoseFallback && cent->currentState.weapon==WP_SABER;
}

static float CG_STCanonicalSpeed(centity_t *cent,int anim,float multiplier)
{
    float speed;
    animation_t *a=&bgAllAnims[cent->localAnimIndex].anims[anim];
    if (!a->frameLerp) return 0;
    speed=(50.0f/a->frameLerp)*multiplier;
    BG_SaberStartTransAnim(cent->currentState.number,cent->currentState.fireflag,
        cent->currentState.weapon,anim,&speed,cent->currentState.brokenLimbs);
    return speed;
}

static qboolean CG_STPoseNeedsRefresh(centity_t *cent,lerpFrame_t *lf,int anim,float multiplier)
{
    int mirrored;
    if((cent->currentState.m_iVehicleNum || cent->currentState.NPC_class==CLASS_VEHICLE) && !lf->stPoseValid)return qfalse;
    if (!ST_HandFromFlags(cent->currentState.eFlags2) && !lf->stPoseValid) return qfalse;
    mirrored=CG_STPrepareHandPose(cent);
    if (!lf->stPoseValid || lf->stPoseModel!=cent->ghoul2) return qtrue;
    if (anim<0 || anim>=MAX_TOTALANIMATIONS) return qtrue;
    return lf->stPose.clocked || lf->stPose.mirrored!=mirrored || lf->stPose.semanticAnim!=anim ||
        fabs(lf->stPose.canonicalSpeed-CG_STCanonicalSpeed(cent,anim,multiplier))>0.00001f;
}

/* Return true when handled, false to retain the original ordinary path. */
static qboolean CG_STSetNormalAnimation(centity_t *cent,clientInfo_t *ci,lerpFrame_t *lf,
    int anim,float multiplier,qboolean torsoOnly,qboolean flipState)
{
    stDirectionalPlayback_t next;
    lerpFrame_t *other=torsoOnly?&cent->pe.legs:&cent->pe.torso;
    const char *bone=torsoOnly&&!cent->noLumbar?"lower_lumbar":"model_root";
    const char *otherBone=torsoOnly?"model_root":"lower_lumbar";
    float begin=-1, sampled=0, speed;
    int flags,blend=100,mirrored,oldAnim=lf->animationNumber;
    qboolean continuing,modeChange;
    const stDirectionalPlayback_t *clockSource=NULL;
    if (!ST_HandFromFlags(cent->currentState.eFlags2) && !lf->stPoseValid) return qfalse;
    if (!cent->ghoul2 || cent->localAnimIndex<0 || anim<0 || anim>=MAX_TOTALANIMATIONS) return qfalse;
    if(cent->currentState.m_iVehicleNum || cent->currentState.NPC_class==CLASS_VEHICLE) {
        if(cent->pe.legs.stPoseValid || cent->pe.torso.stPoseValid)CG_STUnmirrorAll(cent);
        return qfalse;
    }
    mirrored=CG_STPrepareHandPose(cent);
    speed=CG_STCanonicalSpeed(cent,anim,multiplier);
    if (!ST_BuildDirectionalPlayback(bgAllAnims[cent->localAnimIndex].anims,
        MAX_TOTALANIMATIONS,anim,mirrored,speed,&next)) {
        if (mirrored) CG_STPoseFallback(cent,anim,"current clip unsupported");
        return qfalse;
    }
    continuing=lf->stPoseValid && lf->stPoseModel==cent->ghoul2 &&
        lf->stPose.semanticAnim==anim && lf->lastFlip==flipState;
    modeChange=!lf->stPoseValid || lf->stPoseModel!=cent->ghoul2 || lf->stPose.mirrored!=mirrored;
    if (continuing && lf->stPose.clocked) {
        clockSource=&lf->stPose;
        sampled=ST_DirectionClockPose(&lf->stPose,cg.time);
        ST_DirectionResumeFrame(&lf->stPose,&next,sampled,&begin);
    } else if (continuing && trap->G2API_GetBoneFrame(cent->ghoul2,bone,cg.time,&sampled,NULL,0))
        ST_DirectionResumeFrame(&lf->stPose,&next,sampled,&begin);
    if (!cent->noLumbar && cent->currentState.legsAnim==cent->currentState.torsoAnim &&
        other->stPoseValid && other->stPoseModel==cent->ghoul2 && other->stPose.semanticAnim==anim &&
        other->lastFlip==(torsoOnly?cent->currentState.legsFlip:cent->currentState.torsoFlip)) {
        if (other->stPose.clocked) {
            clockSource=&other->stPose;
            sampled=ST_DirectionClockPose(&other->stPose,cg.time);
            ST_DirectionResumeFrame(&other->stPose,&next,sampled,&begin);
        } else if (trap->G2API_GetBoneFrame(cent->ghoul2,otherBone,cg.time,&sampled,NULL,0))
            ST_DirectionResumeFrame(&other->stPose,&next,sampled,&begin);
    }
    if (next.clocked) {
        float canonical=begin<0?(float)next.canonicalFirst:ST_DirectionCanonicalFrame(&next,begin);
        ST_DirectionClockContinue(&next,clockSource,canonical,cg.time);
        begin=ST_DirectionPoseFrame(&next,canonical);
        next.poseSpeed=ST_DirectionSpeedAtFrame(&next,canonical);
    }
    flags=next.looping?BONE_ANIM_OVERRIDE_LOOP:BONE_ANIM_OVERRIDE_FREEZE;
    if (mirrored) flags|=BONE_ANIM_MIRROR;
    if ((cg_animBlend.integer || ST_HandFromFlags(cent->currentState.eFlags2)) && !modeChange && !BG_InDeathAnim(anim) &&
        (oldAnim<0 || !BG_InDeathAnim(oldAnim))) flags|=BONE_ANIM_BLEND;
    if (BG_FlippingAnim(anim) || (oldAnim>=0 && BG_FlippingAnim(oldAnim))) blend=200;
    if (modeChange) blend=0;
    if (continuing && next.clocked) { blend=0; flags&=~BONE_ANIM_BLEND; }
    if (!trap->G2API_SetBoneAnim(cent->ghoul2,0,bone,next.poseFirst,next.poseEnd,
        flags,next.poseSpeed,cg.time,begin,blend)) {
        if (mirrored) CG_STPoseFallback(cent,anim,"Ghoul2 mirror rejected");
        return qfalse;
    }
    if (cent->localAnimIndex<=1 && cent->currentState.torsoAnim==anim && !cent->noLumbar) {
        if (!trap->G2API_SetBoneAnim(cent->ghoul2,0,"Motion",next.poseFirst,next.poseEnd,
            flags,next.poseSpeed,cg.time,begin,blend)) {
            if (mirrored) CG_STPoseFallback(cent,anim,"Motion mirror rejected");
            return qfalse;
        }
    }
    lf->animationNumber=anim;
    lf->animation=&bgAllAnims[cent->localAnimIndex].anims[anim];
    if (!continuing || !next.clocked)
        lf->animationTime=lf->frameTime+abs(lf->animation->frameLerp);
    if (torsoOnly) { lf->animationTorsoSpeed=multiplier; ci->torsoAnim=anim; }
    else { lf->animationSpeed=multiplier; ci->legsAnim=anim; }
    ci->brokenLimbs=cent->currentState.brokenLimbs;
    lf->stPose=next; lf->stPoseValid=qtrue; lf->stPoseModel=cent->ghoul2;
    if (!continuing || modeChange) {
        lf->frame=lf->oldFrame=(int)floor(begin<0?next.canonicalFirst:
            ST_DirectionCanonicalFrame(&next,begin));
        lf->stPoseSkipEvents=qtrue;
    }
    return qtrue;
}

/* Called before event processing: an event may query a foot bolt before the
 * ordinary animation update. Sample the exact current warp, not extrapolation
 * from a segment that finished during a skipped render frame. */
static void CG_STRefreshClockPoses(centity_t *cent)
{
    int channel;
    if (!cent || !cent->ghoul2 || cent->currentState.forceFrame) return;
    for (channel=0;channel<2;++channel) {
        lerpFrame_t *lf=channel?&cent->pe.torso:&cent->pe.legs;
        stDirectionalPlayback_t *p=&lf->stPose;
        const char *bone=channel?"lower_lumbar":"model_root";
        float canonical,frame,speed;
        int flags;
        if (!lf->stPoseValid || lf->stPoseModel!=cent->ghoul2 || !p->clocked ||
            (channel && cent->noLumbar)) continue;
        canonical=ST_DirectionClockFrame(p,cg.time);
        frame=ST_DirectionPoseFrame(p,canonical);
        speed=ST_DirectionSpeedAtFrame(p,canonical);
        flags=BONE_ANIM_OVERRIDE_FREEZE|(p->mirrored?BONE_ANIM_MIRROR:0);
        if (!trap->G2API_SetBoneAnim(cent->ghoul2,0,bone,p->poseFirst,p->poseEnd,
            flags,speed,cg.time,frame,0)) {
            CG_STPoseFallback(cent,p->semanticAnim,"timed pose refresh rejected");
            return;
        }
        if (channel && cent->localAnimIndex<=1 &&
            !trap->G2API_SetBoneAnim(cent->ghoul2,0,"Motion",p->poseFirst,p->poseEnd,
                flags,speed,cg.time,frame,0)) {
            CG_STPoseFallback(cent,p->semanticAnim,"timed Motion refresh rejected");
            return;
        }
    }
}

static float CG_STCanonicalEventFrame(centity_t *cent,lerpFrame_t *lf,float sampled)
{
    if (lf->stPoseValid && lf->stPoseModel==cent->ghoul2)
        sampled=lf->stPose.clocked?ST_DirectionClockFrame(&lf->stPose,cg.time):
            ST_DirectionCanonicalFrame(&lf->stPose,sampled);
    if (lf->stPoseSkipEvents) {
        lf->frame=lf->oldFrame=(int)floor(sampled);
        lf->stPoseSkipEvents=qfalse;
    }
    return sampled;
}

/* Keep canonical event timing, choose the reflected counterpart's named foot.
 * Source footstep labels come from the loaded event table; shared events are
 * never mutated. Missing counterpart evidence suppresses the spatial event. */
static footstepType_t CG_STFootstepType(centity_t *cent,const animevent_t *event)
{
    lerpFrame_t *lf=&cent->pe.legs;
    int sourceType=event->eventData[AED_FOOTSTEP_TYPE],i;
    qboolean heavy=sourceType==FOOTSTEP_HEAVY_R || sourceType==FOOTSTEP_HEAVY_L;
    if (!lf->stPoseValid || !lf->stPose.mirrored) return (footstepType_t)sourceType;
    if (lf->stPose.warp) {
        /* Butterfly clips have different numbers of footfalls. Choose the
         * lower actual rendered foot, never an unrelated nearest event label.
         * The ordinary footstep trace decides whether it contacts the world. */
        mdxaBone_t left,right;
        vec3_t angles={0,0,0};
        int l=trap->G2API_AddBolt(cent->ghoul2,0,"*l_leg_foot");
        int r=trap->G2API_AddBolt(cent->ghoul2,0,"*r_leg_foot");
        angles[YAW]=cent->pe.legs.yawAngle;
        if (l<0 || r<0 ||
            !trap->G2API_GetBoltMatrix(cent->ghoul2,0,l,&left,angles,cent->lerpOrigin,
                cg.time,cgs.gameModels,cent->modelScale) ||
            !trap->G2API_GetBoltMatrix(cent->ghoul2,0,r,&right,angles,cent->lerpOrigin,
                cg.time,cgs.gameModels,cent->modelScale)) return NUM_FOOTSTEP_TYPES;
        return left.matrix[2][3]<=right.matrix[2][3]?
            (heavy?FOOTSTEP_HEAVY_L:FOOTSTEP_L):(heavy?FOOTSTEP_HEAVY_R:FOOTSTEP_R);
    }
    if (lf->stPose.poseAnim!=lf->stPose.semanticAnim) {
        const animevent_t *events=bgAllEvents[cent->eventAnimIndex].legsAnimEvents;
        const animation_t *a=&bgAllAnims[cent->localAnimIndex].anims[lf->stPose.poseAnim];
        float wanted=ST_DirectionPoseFrame(&lf->stPose,(float)event->keyFrame),best=1e20f;
        int selected=-1;
        for (i=0;i<MAX_ANIM_EVENTS && events[i].eventType!=AEV_NONE;++i) {
            float d;
            if (events[i].eventType!=AEV_FOOTSTEP || events[i].keyFrame<a->firstFrame ||
                events[i].keyFrame>=a->firstFrame+a->numFrames) continue;
            d=fabs((float)events[i].keyFrame-wanted);
            if (lf->stPose.looping && d>lf->stPose.poseSpan*0.5f) d=lf->stPose.poseSpan-d;
            if (d<best) {best=d;selected=events[i].eventData[AED_FOOTSTEP_TYPE];}
        }
        if (selected<0) return NUM_FOOTSTEP_TYPES;
        sourceType=selected;
    }
    if (sourceType==FOOTSTEP_R || sourceType==FOOTSTEP_HEAVY_R)
        return heavy?FOOTSTEP_HEAVY_L:FOOTSTEP_L;
    return heavy?FOOTSTEP_HEAVY_R:FOOTSTEP_R;
}
