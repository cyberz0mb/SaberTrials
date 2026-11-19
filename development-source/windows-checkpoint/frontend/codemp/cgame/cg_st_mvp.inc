/* Historical scene for the local single-strike proof. GPL-2.0-or-later. */
#include "qcommon/st_mvp_api.h"
#include "qcommon/st_mvp_timing.h"
#include "qcommon/st_mvp_montage.h"
#include "ui/ui_shared.h"
#include "ui/ui_public.h"
extern void CG_DoSaber(vec3_t,vec3_t,float,float,float,saber_colors_t,int,qboolean);
static int stMvpStarted, stMvpSeenKill, stMvpPreviousSource;
static qboolean stMvpActive;
static stMvpClip_t stMvpCard;
static vec3_t stMvpForward, stMvpSide;
static int stMvpPreviousCatcher;
static stMvpPlan_t stMvpPlan;
static int stMvpCurrentShot, stMvpLingering;
typedef struct { int time; sfxHandle_t sound; vec3_t origin; } stMvpSound_t;
static stMvpSound_t stMvpSounds[256];
static int stMvpSoundCount;
static void *stMvpRenderPoses[ST_MVP_RENDER_POSES];
static int stMvpRenderPoseCount;
static qboolean ST_MvpDebug(void) {
    char value[16];
    trap->Cvar_VariableStringBuffer("developer",value,sizeof(value));
    return atoi(value)!=0;
}
#include "cg_st_mvp_network.inc"
#include "cg_st_mvp_effects.inc"
#include "cg_st_mvp_hud.inc"

qboolean ST_MvpDrawCard(void) {
    if (!stMvpActive || !stMvpCard.cardOnly) return qfalse;
    ST_MvpDrawHud(&stMvpCard);
    return qtrue;
}

static void ST_MvpReleaseFrame(void) {
    int i;
    for (i=0; i<stMvpRenderPoseCount; ++i)
        trap->G2API_CleanGhoul2Models(&stMvpRenderPoses[i]);
    stMvpRenderPoseCount = 0;
    stMvpPoseCacheCount = 0;
}

qboolean ST_MvpTestReady(void) {
    char enabled[8];
    trap->Cvar_VariableStringBuffer("st_mvpPrototype",enabled,sizeof(enabled));
    if (!atoi(enabled)) return qfalse;
    trap->OpenUIMenu(UIMENU_NONE);
    trap->Key_SetCatcher(0);
    return qtrue;
}

void ST_MvpRecordSound(const vec3_t origin,int entity,int channel,sfxHandle_t sound) {
    char enabled[8];
    trap->S_StartSound(origin,entity,channel,sound);
    trap->Cvar_VariableStringBuffer("st_mvpPrototype",enabled,sizeof(enabled));
    if (!cg.snap || cg.snap->ps.pm_type == PM_INTERMISSION || !sound ||
        !atoi(enabled) ||
        (channel != CHAN_AUTO && channel != CHAN_WEAPON && channel != CHAN_BODY)) return;
    {
        stMvpSound_t *record = &stMvpSounds[stMvpSoundCount++ % 256];
        record->time = cg.time;
        record->sound = sound;
        if (origin) VectorCopy(origin,record->origin);
        else if (entity >= 0 && entity < MAX_GENTITIES) VectorCopy(cg_entities[entity].lerpOrigin,record->origin);
        else VectorCopy(cg.snap->ps.origin,record->origin);
    }
}

void ST_MvpStop(void) {
    int i;
    if (stMvpActive) {
        trap->Key_SetCatcher((trap->Key_GetCatcher() & ~KEYCATCH_CGAME) |
            (stMvpPreviousCatcher & KEYCATCH_CGAME));
        for (i = 0; i < 4; ++i) trap->S_MuteSound(MAX_GENTITIES - 8 + i, CHAN_WEAPON);
        if (ST_MvpDebug()) trap->Print("MVP_PLAYBACK stopped elapsed=%d\n",trap->Milliseconds()-stMvpStarted);
        if (ST_MvpDebug()) trap->Print("MVP_EFFECTS trails=%d limbs=%d cuts=%d settings=%d/%d\n",
            stMvpTrailQuads,stMvpLimbDraws,stMvpBodyCuts,cg_saberTrail.integer,cg_dismember.integer);
        trap->SendClientCommand(va("st_mvp_done %d",stMvpCard.resultTime));
    }
    stMvpActive = qfalse;
}

void ST_MvpClear(void) {
    ST_MvpStop();
    ST_MvpReleaseFrame();
    ST_MvpNetClear();
    stMvpSeenKill = stMvpSoundCount = 0;
    memset(stMvpSounds,0,sizeof(stMvpSounds));
    ST_MvpHudReset();
}

qboolean ST_MvpKey(int key,qboolean down) {
    if (!stMvpActive) return qfalse;
    if (down && (key == A_ESCAPE || key == A_ENTER || key == A_SPACE || key == A_MOUSE1)) ST_MvpStop();
    return qtrue;
}

static void ST_MvpFocus(const stMvpClip_t *clip,const stMvpShot_t *shot,float alpha,vec3_t focus) {
    int i,j,count=0;
    VectorClear(focus);
    for (i=0; i<clip->before->count; ++i) {
        const stMvpActor_t *a=&clip->before->actors[i], *b=ST_MvpFindActor(clip->after,a->clientNum);
        qboolean include=a->clientNum==clip->winner;
        if(!b)b=a;
        float blend=a->spawnId==b->spawnId ? alpha : 0;
        for (j=shot->firstEvent; j<=shot->lastEvent; ++j)
            if (clip->events[j].victim==a->clientNum) include=qtrue;
        if (!include) continue;
        for (j=0; j<3; ++j) focus[j]+=a->origin[j]*(1-blend)+b->origin[j]*blend;
        ++count;
    }
    if (count) VectorScale(focus,1.0f/count,focus);
    focus[2]+=24;
}

qboolean ST_MvpDraw(void) {
    stMvpClip_t clip;
    refdef_t view;
    vec3_t focus, desired, forward, side, direction, mins = {-6,-6,-6}, maxs = {6,6,6};
    trace_t trace;
    float alpha;
    int elapsed, source, i, axis, shotIndex;
    stMvpShot_t *shot;
    ST_MvpReleaseFrame();
    if (!cg.snap || cg.demoPlayback || cg.snap->ps.pm_type != PM_INTERMISSION ||
        !ST_MvpRemoteRead(0,&clip)) {
        ST_MvpStop();
        if (!cg.snap || cg.snap->ps.pm_type != PM_INTERMISSION) stMvpSeenKill = 0;
        return qfalse;
    }
    if (!stMvpActive && stMvpSeenKill == clip.resultTime) return qfalse;
    if (!stMvpActive) {
        ST_PhotoStop();
        ST_MvpBuildPlan(&clip,&stMvpPlan);
        stMvpSeenKill = clip.resultTime;
        if ((!stMvpPlan.count && !clip.cardOnly) || !stMvpPlan.duration) return qfalse;
        stMvpCard=clip;
        stMvpCurrentShot=-1;
        stMvpLingering=0;
        stMvpStarted = trap->Milliseconds();
        stMvpTrailQuads = stMvpLimbDraws = stMvpBodyCuts = 0;
        stMvpActive = qtrue;
        stMvpPreviousCatcher = trap->Key_GetCatcher();
        trap->Key_SetCatcher(trap->Key_GetCatcher() | KEYCATCH_CGAME);
        if (ST_MvpDebug()) trap->Print("MVP_PLAYBACK start kill=%d first=%d last=%d budgetBytes=%d shots=%d kills=%d duration=%d\n",
            clip.killTime,clip.firstTime,clip.lastTime,clip.retainedBytes,stMvpPlan.count,stMvpPlan.kills,stMvpPlan.duration);
    }
    elapsed = trap->Milliseconds() - stMvpStarted;
    if (elapsed >= stMvpPlan.duration) { ST_MvpStop(); return qfalse; }
    if (clip.cardOnly) return qfalse; // Draw over the normal intermission camera.
    for (shotIndex=0; shotIndex+1<stMvpPlan.count && elapsed>=stMvpPlan.shots[shotIndex+1].start; ++shotIndex) {}
    shot=&stMvpPlan.shots[shotIndex];
    source=(int)ST_MvpShotSource(shot,ST_MvpShotElapsed(shot,elapsed));
    if(!stMvpLingering && shotIndex==stMvpPlan.count-1 && elapsed>=shot->start+shot->duration) {
        stMvpLingering=1;
        if(ST_MvpDebug())trap->Print("MVP_LINGER started elapsed=%d source=%d\n",elapsed,source);
    }
    if (shotIndex!=stMvpCurrentShot) {
        trace_t alternative;
        int attacker=-1,victim=-1;
        if (!ST_MvpRemoteRead(shot->firstKill,&clip)) { ST_MvpStop(); return qfalse; }
        for (i=0; i<clip.before->count; ++i) {
            if (clip.before->actors[i].clientNum==clip.winner) attacker=i;
            if (clip.before->actors[i].clientNum==clip.events[shot->firstEvent].victim) victim=i;
        }
        if(attacker<0 || victim<0) { ST_MvpStop();return qfalse; }
        VectorSubtract(clip.before->actors[victim].origin,clip.before->actors[attacker].origin,stMvpForward);
        stMvpForward[2] = 0;
        if (VectorNormalize(stMvpForward) < 1) VectorSet(stMvpForward,1,0,0);
        VectorSet(stMvpSide,-stMvpForward[1],stMvpForward[0],0);
        ST_MvpFocus(&clip,shot,0,focus);
        VectorMA(focus,170,stMvpSide,desired);
        VectorMA(desired,-95,stMvpForward,desired);
        desired[2] += 55;
        trap->CM_Trace(&trace,focus,desired,mins,maxs,0,MASK_SOLID,qfalse);
        VectorMA(focus,-170,stMvpSide,desired);
        VectorMA(desired,-95,stMvpForward,desired);
        desired[2] += 55;
        trap->CM_Trace(&alternative,focus,desired,mins,maxs,0,MASK_SOLID,qfalse);
        if (alternative.fraction > trace.fraction) VectorScale(stMvpSide,-1,stMvpSide);
        stMvpPreviousSource=source-1;
        stMvpCurrentShot=shotIndex;
        for (i=0; i<4; ++i) trap->S_MuteSound(MAX_GENTITIES-8+i,CHAN_WEAPON);
        if (ST_MvpDebug()) trap->Print("MVP_SHOT index=%d kills=%d source=%d\n",shotIndex,
            shot->lastEvent-shot->firstEvent+1,source);
    }
    if (!ST_MvpRemoteRead(source,&clip)) { ST_MvpStop(); return qfalse; }
    alpha = clip.after->time > clip.before->time ?
        (float)(source-clip.before->time)/(clip.after->time-clip.before->time) : 0;
    alpha = Com_Clamp(0,1,alpha);
    ST_MvpFocus(&clip,shot,alpha,focus);
    VectorCopy(stMvpForward,forward);
    VectorCopy(stMvpSide,side);
    VectorMA(focus,170,side,desired);
    VectorMA(desired,-95,forward,desired);
    desired[2] += 55;
    trap->CM_Trace(&trace,focus,desired,mins,maxs,0,MASK_SOLID,qfalse);
    memset(&view,0,sizeof(view));
    VectorCopy(trace.endpos,view.vieworg);
    VectorSubtract(focus,view.vieworg,direction);
    vectoangles(direction,view.viewangles);
    AnglesToAxis(view.viewangles,view.viewaxis);
    view.width = cgs.glconfig.vidWidth;
    view.height = cgs.glconfig.vidHeight;
    view.fov_x = 65;
    view.fov_y = atan2f((float)view.height,(float)view.width/tanf(65.0f*M_PI/360.0f))*360.0f/M_PI;
    view.time = source;
    // Match CG_DrawActive: Rend2 otherwise suppresses non-sky geometry on
    // maps with a sky portal, including the captured actors and saber effects.
    view.rdflags = RDF_DRAWSKYBOX;
    trap->S_ClearLoopingSounds();
    trap->R_ClearScene();
    trap->G2API_SetTime(source,1);
    ST_MvpDrawSky(&view);
    for (i = 0; i < clip.before->count; ++i) {
        const stMvpActor_t *a = &clip.before->actors[i], *b = ST_MvpFindActor(clip.after,a->clientNum);
        refEntity_t entity;
        vec3_t angles, bladeBase, bladeDir;
        if(!b)b=a;
        float blend=a->spawnId==b->spawnId ? alpha : 0;
        memset(&entity,0,sizeof(entity));
        for (axis = 0; axis < 3; ++axis) {
            entity.origin[axis] = a->origin[axis]*(1-blend)+b->origin[axis]*blend;
            angles[axis] = LerpAngle(a->angles[axis],b->angles[axis],blend);
        }
        VectorCopy(a->scale,entity.modelScale);
        VectorCopy(entity.origin,entity.lightingOrigin);
        AnglesToAxis(angles,entity.axis);
        entity.ghoul2 = ST_MvpBodyPose(a,clip.before);
        if(entity.ghoul2)stMvpRenderPoses[stMvpRenderPoseCount++]=entity.ghoul2;
        else entity.ghoul2=ST_MvpResolvePose(a->pose,a->poseBytes);
        if(!entity.ghoul2)continue;
        entity.radius = 128;
        entity.renderfx = RF_LIGHTING_ORIGIN | RF_NOSHADOW;
        entity.shaderRGBA[0]=entity.shaderRGBA[1]=entity.shaderRGBA[2]=entity.shaderRGBA[3]=255;
        trap->R_AddRefEntityToScene(&entity);
        for(int blade=0;blade<a->bladeCount;++blade) {
            const stMvpBlade_t *ba=&a->blades[blade],*bb=blade<b->bladeCount?&b->blades[blade]:ba;
            for(axis=0;axis<3;++axis){bladeBase[axis]=ba->base[axis]*(1-blend)+bb->base[axis]*blend;bladeDir[axis]=ba->dir[axis]*(1-blend)+bb->dir[axis]*blend;}
            if(ba->length>0 && !(ba->flags&1) && VectorNormalize(bladeDir)>.5f)CG_DoSaber(bladeBase,bladeDir,ba->length,ba->length,ba->radius,(saber_colors_t)ba->color,0,!(ba->flags&2));
            ST_MvpDrawTrail(source,a->clientNum,blade);
        }
    }
    for (i=0; i<clip.before->limbCount; ++i) {
        void *part=ST_MvpDrawPart(&clip.before->limbs[i],&clip,alpha);
        if(part)stMvpRenderPoses[stMvpRenderPoseCount++]=part;
    }
    for(i=0;i<clip.before->propCount;++i) {
        const stMvpProp_t *p=&clip.before->props[i],*next=p;refEntity_t entity;vec3_t angles;
        for(int j=0;j<clip.after->propCount;++j)if(clip.after->props[j].entityNum==p->entityNum){next=&clip.after->props[j];break;}
        memset(&entity,0,sizeof(entity));
        for(axis=0;axis<3;++axis){entity.origin[axis]=p->origin[axis]*(1-alpha)+next->origin[axis]*alpha;angles[axis]=LerpAngle(p->angles[axis],next->angles[axis],alpha);}
        VectorCopy(p->scale,entity.modelScale);VectorCopy(entity.origin,entity.lightingOrigin);AnglesToAxis(angles,entity.axis);
        if(p->pose)entity.ghoul2=ST_MvpResolvePose(p->pose,p->poseBytes);
        else if(p->brush && p->modelIndex<cgs.numInlineModels)entity.hModel=cgs.inlineDrawModel[p->modelIndex];
        else entity.hModel=cgs.gameModels[p->modelIndex];
        if(p->type==ET_MISSILE && !entity.ghoul2 && p->weapon>WP_NONE && p->weapon<WP_NUM_WEAPONS) {
            vec3_t direction;CG_RegisterWeapon(p->weapon);VectorCopy(p->velocity,direction);
            if(VectorNormalize(direction)<.1f)VectorSet(direction,0,0,1);
            vectoangles(direction,angles);AnglesToAxis(angles,entity.axis);
            if(!entity.hModel)entity.hModel=(p->flags&EF_ALT_FIRING)?cg_weapons[p->weapon].altMissileModel:cg_weapons[p->weapon].missileModel;
            if(!entity.hModel) {
                saber_colors_t color=p->weapon==WP_BOWCASTER?SABER_GREEN:
                    (p->weapon==WP_REPEATER?SABER_ORANGE:(p->weapon==WP_DEMP2?SABER_BLUE:SABER_RED));
                CG_DoSaber(entity.origin,direction,12,12,1,color,0,qtrue);
            }
        }
        if(!entity.ghoul2 && !entity.hModel)continue;
        entity.radius=256;entity.renderfx=RF_LIGHTING_ORIGIN|RF_NOSHADOW;
        entity.shaderRGBA[0]=entity.shaderRGBA[1]=entity.shaderRGBA[2]=entity.shaderRGBA[3]=255;trap->R_AddRefEntityToScene(&entity);
    }
    trap->R_RenderScene(&view);
    trap->G2API_SetTime(cg.time,1);
    trap->S_Respatialize(cg.clientNum,view.vieworg,view.viewaxis,qfalse);
    for (i = 0; i < (stMvpSoundCount < 256 ? stMvpSoundCount : 256); ++i) {
        const stMvpSound_t *sound = &stMvpSounds[i];
        if (sound->time > stMvpPreviousSource && sound->time <= source)
            trap->S_StartSound(sound->origin,MAX_GENTITIES-8+i%4,CHAN_WEAPON,sound->sound);
    }
    stMvpPreviousSource = source;
    ST_MvpDrawHud(&clip);
    return qtrue;
}
