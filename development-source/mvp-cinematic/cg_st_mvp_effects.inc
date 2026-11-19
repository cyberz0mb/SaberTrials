/* Replay-only presentation of captured saber motion and real severed parts.
 * GPL-2.0-or-later. Included by cg_st_mvp.inc. Kyle proof only. */
static int stMvpTrailQuads, stMvpLimbDraws, stMvpBodyCuts;

/* Rend2 requires a fresh skyportal view before the main view on portal maps.
 * Draw the static map sky at replay time without dispatching live entities/FX. */
static void ST_MvpDrawSky(refdef_t *view) {
    const char *text = CG_ConfigString(CS_SKYBOXORG);
    refdef_t sky;
    int i;
    if (!text || !text[0]) return;
    sky = *view;
    COM_BeginParseSession("MVP skyportal");
    for (i=0; i<3; ++i) {
        const char *token = COM_ParseExt(&text,qfalse);
        if (!token || !token[0]) return;
        sky.vieworg[i] = atof(token);
    }
    if (cg_skyOri) {
        vec3_t offset;
        VectorSubtract(view->vieworg,cg_skyOriPos,offset);
        VectorMA(sky.vieworg,cg_skyOriScale,offset,sky.vieworg);
    }
    sky.rdflags = RDF_SKYBOXPORTAL | RDF_DRAWSKYBOX;
    if (cg_noFogOutsidePortal) view->rdflags |= RDF_NOFOG;
    trap->R_RenderScene(&sky);
}

typedef struct { const char *surface, *cap, *stub, *bone; } stMvpPartStyle_t;
static const stMvpPartStyle_t stMvpParts[] = {
    {"head", "head_cap_torso", "torso_cap_head", "cranium"},
    {"torso", "torso_cap_hips", "hips_cap_torso", "thoracic"},
    {"l_arm", "l_arm_cap_torso", "torso_cap_l_arm", "lradius"},
    {"r_arm", "r_arm_cap_torso", "torso_cap_r_arm", "rradius"},
    {"r_hand", "r_hand_cap_r_arm", "r_arm_cap_r_hand", "rhand"},
    {"l_leg", "l_leg_cap_hips", "hips_cap_l_leg", "ltibia"},
    {"r_leg", "r_leg_cap_hips", "hips_cap_r_leg", "rtibia"}
};

static qboolean ST_MvpShowPart(int part) {
    return cg_dismember.integer > 0 && part >= G2_MODELPART_HEAD && part <= G2_MODELPART_RLEG &&
        (cg_dismember.integer >= 2 || (part != G2_MODELPART_HEAD && part != G2_MODELPART_WAIST));
}

/* These are temporary render copies, released at the next client frame after
 * the renderer has consumed the previous frame's deferred draw commands.
 * Never alter a retained pose or the live player's surfaces for viewer settings. */
static void *ST_MvpBodyPose(const stMvpActor_t *actor, const stMvpSample_t *sample) {
    void *pose = NULL;
    int i;
    if(actor->weapon!=WP_SABER) {
        void *original=ST_MvpResolvePose(actor->pose,actor->poseBytes);
        if(original)trap->G2API_DuplicateGhoul2Instance(original,&pose);
        if(pose) {
            for(i=2;i>=1;--i)if(trap->G2API_HasGhoul2ModelOnIndex(&pose,i))trap->G2API_RemoveGhoul2Model(&pose,i);
            if(actor->weapon>WP_NONE && actor->weapon<WP_NUM_WEAPONS) {
                CG_RegisterWeapon(actor->weapon);
                // Non-saber weapon instances are shared immutable models; the
                // normal helper only edits this temporary historical body.
                CG_CopyG2WeaponInstance(NULL,actor->weapon,pose);
            }
        }
    }
    for (i = 0; i < sample->limbCount; ++i) {
        const stMvpLimb_t *part = &sample->limbs[i];
        const stMvpPartStyle_t *style;
        if (part->owner != actor->clientNum || !ST_MvpShowPart(part->part)) continue;
        if (!pose) {
            void *original=ST_MvpResolvePose(actor->pose,actor->poseBytes);
            if(original)trap->G2API_DuplicateGhoul2Instance(original,&pose);
        }
        if (!pose) break;
        style = &stMvpParts[part->part - G2_MODELPART_HEAD];
        trap->G2API_SetSurfaceOnOff(pose,style->surface,0x00000100);
        trap->G2API_SetSurfaceOnOff(pose,style->stub,0);
        if ((part->part == G2_MODELPART_WAIST || part->part == G2_MODELPART_RARM ||
             part->part == G2_MODELPART_RHAND) && trap->G2API_HasGhoul2ModelOnIndex(&pose,1))
            trap->G2API_RemoveGhoul2Model(&pose,1);
        ++stMvpBodyCuts;
    }
    return pose;
}

static void *ST_MvpDrawPart(const stMvpLimb_t *part, const stMvpClip_t *clip, float alpha) {
    const stMvpActor_t *actor = NULL;
    const stMvpLimb_t *next = part;
    const stMvpPartStyle_t *style;
    refEntity_t entity;
    vec3_t angles;
    void *pose = NULL;
    int i, bolt;
    if (!ST_MvpShowPart(part->part)) return NULL;
    for (i=0; i<clip->before->count; ++i)
        if (clip->before->actors[i].clientNum == part->owner) actor = &clip->before->actors[i];
    if (!actor) return NULL;
    for (i=0; i<clip->after->limbCount; ++i)
        if (clip->after->limbs[i].entityNum == part->entityNum &&
            clip->after->limbs[i].owner == part->owner && clip->after->limbs[i].part == part->part)
            next = &clip->after->limbs[i];
    style = &stMvpParts[part->part-G2_MODELPART_HEAD];
    { void *original=ST_MvpResolvePose(actor->pose,actor->poseBytes);
      if(original)trap->G2API_DuplicateGhoul2Instance(original,&pose); }
    if (!pose) return NULL;
    bolt = trap->G2API_AddBolt(pose,0,style->bone);
    if (bolt < 0 || !trap->G2API_SetRootSurface(pose,0,style->surface) ||
        !trap->G2API_SetNewOrigin(pose,bolt)) {
        trap->G2API_CleanGhoul2Models(&pose);
        return NULL;
    }
    trap->G2API_SetSurfaceOnOff(pose,style->cap,0);
    memset(&entity,0,sizeof(entity));
    for (i=0; i<3; ++i) {
        entity.origin[i] = part->origin[i]*(1-alpha)+next->origin[i]*alpha;
        angles[i] = LerpAngle(part->angles[i],next->angles[i],alpha);
    }
    VectorCopy(entity.origin,entity.lightingOrigin);
    VectorCopy(actor->scale,entity.modelScale);
    AnglesToAxis(angles,entity.axis);
    entity.ghoul2 = pose;
    entity.radius = 200;
    entity.renderfx = RF_LIGHTING_ORIGIN | RF_NOSHADOW;
    entity.shaderRGBA[0]=entity.shaderRGBA[1]=entity.shaderRGBA[2]=entity.shaderRGBA[3]=255;
    trap->R_AddRefEntityToScene(&entity);
    ++stMvpLimbDraws;
    return pose;
}

static qboolean ST_MvpTrailPoint(int source, int client, int blade, vec3_t base, vec3_t tip,
                                float *duration, int *style, int *color) {
    stMvpClip_t clip;
    const stMvpActor_t *a, *b;
    const stMvpBlade_t *ba,*bb;
    vec3_t direction;
    float alpha;
    int i;
    if (!ST_MvpRemoteRead(source,&clip) || source < clip.firstTime || source > clip.lastTime) return qfalse;
    a=ST_MvpFindActor(clip.before,client); b=ST_MvpFindActor(clip.after,client);
    if(!a || !b || a->spawnId!=b->spawnId || blade>=a->bladeCount || blade>=b->bladeCount)return qfalse;
    ba=&a->blades[blade];bb=&b->blades[blade];
    if (!a->alive || ba->length <= 0 || ba->style > 1 || ba->duration <= 0) return qfalse;
    alpha = clip.after->time > clip.before->time ?
        (float)(source-clip.before->time)/(clip.after->time-clip.before->time) : 0;
    for (i=0; i<3; ++i) {
        base[i]=ba->base[i]*(1-alpha)+bb->base[i]*alpha;
        direction[i]=ba->dir[i]*(1-alpha)+bb->dir[i]*alpha;
    }
    if(VectorNormalize(direction)<.5f)return qfalse;
    VectorMA(base,ba->length+3,direction,tip);
    *duration = ba->duration * (ba->style == 1 ? 2 : 1);
    *style = ba->style;
    *color = ba->color;
    if (cg_saberTrail.integer == 2 && cg_shadows.integer != 2 && cgs.glconfig.stencilBits >= 4) {
        *style = 2;
        *duration = ba->strong ? 300 : 40;
    }
    return qtrue;
}

/* Sample in source time, so trail lifetime and motion follow the slow-motion
 * curve rather than accumulating live-time FX across replay frames. */
static void ST_MvpDrawTrail(int source, int client, int blade) {
    static const byte colors[6][3] = {{255,0,0},{255,64,0},{255,255,0},
        {0,255,0},{0,64,255},{220,0,255}};
    int age, i, channel, style, color, oldStyle, oldColor;
    float duration, oldDuration;
    vec3_t base, tip, oldBase, oldTip;
    if (cg_saberTrail.integer <= 0) return;
    for (age=0; age<300; age+=12) {
        polyVert_t vertices[4];
        qhandle_t shader;
        if (!ST_MvpTrailPoint(source-age,client,blade,base,tip,&duration,&style,&color) || age >= duration ||
            !ST_MvpTrailPoint(source-age-12,client,blade,oldBase,oldTip,&oldDuration,&oldStyle,&oldColor)) continue;
        memset(vertices,0,sizeof(vertices));
        VectorCopy(base,vertices[0].xyz); VectorCopy(tip,vertices[1].xyz);
        VectorCopy(oldTip,vertices[2].xyz); VectorCopy(oldBase,vertices[3].xyz);
        for (i=0; i<4; ++i) {
            float fade = Com_Clamp(0,1,1-(age+(i>=2 ? 12 : 0))/duration);
            vertices[i].st[0] = (age+(i>=2 ? 12 : 0))/duration;
            vertices[i].st[1] = (i==0 || i==3) ? 1 : 0;
            for (channel=0; channel<3; ++channel)
                vertices[i].modulate[channel] = (byte)((style==1 ? 32 : colors[Com_Clampi(0,5,color)][channel])*fade);
            vertices[i].modulate[3] = (byte)(255*fade);
        }
        shader = style==1 ? cgs.media.swordTrailShader : cgs.media.saberBlurShader;
        if (style==2) {
            trap->R_SetRefractionProperties(1,0,qtrue,qtrue);
            shader = 2;
        }
        trap->R_AddPolysToScene(shader,4,vertices,1);
        ++stMvpTrailQuads;
    }
    trap->G2API_SetTime(source,1);
}
