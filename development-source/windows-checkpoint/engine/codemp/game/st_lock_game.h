#ifndef ST_LOCK_GAME_H
#define ST_LOCK_GAME_H
#include "ghoul2/st_lock_pose.h"
#include "st_lock_logic.h"
extern qboolean BG_CheckIncrementLockAnim(int anim,int winOrLose);
static float ST_GameLockProgress(const animation_t* set,int anim,int frame) {
    int forward;
    if(anim<0||anim>=MAX_TOTALANIMATIONS)return .5f;
    forward=BG_InSaberLockOld(anim)?
        (anim!=BOTH_CCWCIRCLELOCK && anim!=BOTH_BF2LOCK):
        BG_CheckIncrementLockAnim(anim,SABERLOCK_WIN);
    return ST_LockProgress(frame,set[anim].firstFrame,set[anim].numFrames,forward);
}
static qboolean ST_GameLockParams(stLockPoseParams_t* out,const animation_t* set,
    int anim,int hand,int saberStyle,const saberInfo_t saber[2],const vec3_t a,const vec3_t b,
    const vec3_t origin,float yaw,const vec3_t scale) {
    int i,j;
    float uniform=ST_LockUniformScale(scale);
    if(anim<0||anim>=MAX_TOTALANIMATIONS||!BG_InSaberLock(anim)||set[anim].numFrames<2)return qfalse;
    /* Ghoul2 scales bolt origins, but the game's luminous blade length remains
     * in world units. Nonuniform model deformation is not a rigid hilt frame. */
    if(!uniform)return qfalse;
    memset(out,0,sizeof(*out));out->size=sizeof(*out);out->version=ST_LOCK_POSE_VERSION;
    out->mode=ST_LOCK_POSE_UPDATE;out->seedFrame=set[anim].firstFrame+(set[anim].numFrames-1)/2;
    out->handedness=hand;out->weight=1;
    out->style=saberStyle==SS_DUAL?ST_LOCK_DUAL:(saberStyle==SS_STAFF?ST_LOCK_STAFF:ST_LOCK_SINGLE);
    for(i=0;i<2;i++) {
        out->hiltModel[i]=i+1;out->bladeLength[i]=saber[i].blade[0].lengthMax/uniform;
        if(i==0||out->style==ST_LOCK_DUAL) {
            if(saber[i].numBlades<1||saber[i].numBlades>8)return qfalse;
            out->bladeCount[i]=saber[i].numBlades;
            for(j=0;j<saber[i].numBlades;j++)out->allBladeLength[i][j]=saber[i].blade[j].lengthMax/uniform;
        }
    }
    return ST_LockContacts(a,b,origin,yaw,scale,out->firstContact,out->lastContact)?qtrue:qfalse;
}
static qboolean ST_GameLockOpponent(stLockPoseParams_t* out,void* opponent,const animation_t* set,
    int anim,int hand,const vec3_t actor,float yaw,const vec3_t scale,
    const vec3_t enemy,float enemyYaw,const vec3_t enemyScale) {
    if(!opponent||anim<0||anim>=MAX_TOTALANIMATIONS||!BG_InSaberLock(anim)||set[anim].numFrames<2)return qfalse;
    out->opponentGhoul2=opponent;out->opponentModelIndex=0;
    out->opponentSeedFrame=set[anim].firstFrame+(set[anim].numFrames-1)/2;
    out->opponentHandedness=hand;
    return ST_LockOpponentTransform(actor,yaw,scale,enemy,enemyYaw,enemyScale,out->opponentTransform)?qtrue:qfalse;
}
#endif
