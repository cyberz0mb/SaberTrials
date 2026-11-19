#ifndef ST_LOCK_POSE_H
#define ST_LOCK_POSE_H

/* Native-only, versioned renderer lock-pose API. Coordinates match a zero-angle
 * G2API_GetBoltMatrix call: +X forward, +Y left, +Z up, relative to this actor's
 * origin and yaw. Both actors must receive transforms of the SAME contact path.
 * The API changes pose sampling only, never lock IDs, timers, or handedness. */
#define ST_LOCK_POSE_VERSION 2
#define ST_LOCK_POSE_CLEAR 0
#define ST_LOCK_POSE_UPDATE 1
#define ST_LOCK_POSE_VALIDATE 2
#define ST_LOCK_POSE_CACHED 3
#define ST_LOCK_SINGLE 0
#define ST_LOCK_DUAL 1
#define ST_LOCK_STAFF 2
typedef struct stLockPoseParams_s {
    int size;                 /* sizeof(stLockPoseParams_t) */
    int version;              /* ST_LOCK_POSE_VERSION */
    int mode;                 /* CLEAR, UPDATE, VALIDATE or CACHED */
    int modelIndex;           /* character model in this Ghoul2 instance */
    int seedFrame;            /* canonical lock's midpoint GLA frame */
    int handedness;           /* 0 right, 1 left; anatomical primary grip */
    int style;                /* SINGLE, DUAL or STAFF */
    int hiltModel[2];          /* logical primary/secondary model indices */
    int hiltSeedFrame[2];      /* selected hilt's GLA sample, normally zero */
    int bladeIndex[2];         /* zero-based actual contacting blade tag */
    float bladeLength[2];     /* active luminous blade lengths, not hilt span */
    float firstContact[3];
    float lastContact[3];
    float progress;           /* common canonical pair progress in [0,1] */
    float weight;             /* 1 locked, (0,1) release blend, 0 normal pose */
    void *opponentGhoul2;      /* native G2 instance; sampled at seed, not cache */
    int opponentModelIndex;
    int opponentSeedFrame;
    int opponentHandedness;
    float opponentTransform[3][4]; /* opponent unscaled G2 local -> own local */
    int bladeCount[2];
    float allBladeLength[2][8]; /* all active blade lengths in own local units */
    float *resolvedContactPath; /* optional output: first XYZ then last XYZ */
} stLockPoseParams_t;

#if defined(_MSC_VER)
#define ST_LOCK_INLINE static __inline
#else
#define ST_LOCK_INLINE static inline
#endif
/* Shared native/game/client identity. Structure padding, presentation mode,
 * progress, weight and the caller's transient output buffer are not identity. */
ST_LOCK_INLINE int ST_LockPoseSameTrack(const stLockPoseParams_t*a,const stLockPoseParams_t*b){
    int w,blade,i,j;
    if(!a||!b)return 0;
    if(a->size!=b->size||a->version!=b->version||a->modelIndex!=b->modelIndex||a->seedFrame!=b->seedFrame||a->handedness!=b->handedness||a->style!=b->style||
       a->opponentGhoul2!=b->opponentGhoul2||a->opponentModelIndex!=b->opponentModelIndex||a->opponentSeedFrame!=b->opponentSeedFrame||a->opponentHandedness!=b->opponentHandedness)return 0;
    for(w=0;w<2;w++){
        if(a->hiltModel[w]!=b->hiltModel[w]||a->hiltSeedFrame[w]!=b->hiltSeedFrame[w]||a->bladeIndex[w]!=b->bladeIndex[w]||a->bladeLength[w]!=b->bladeLength[w]||a->bladeCount[w]!=b->bladeCount[w])return 0;
        for(blade=0;blade<8;blade++)if(a->allBladeLength[w][blade]!=b->allBladeLength[w][blade])return 0;
    }
    for(i=0;i<3;i++){
        if(a->firstContact[i]!=b->firstContact[i]||a->lastContact[i]!=b->lastContact[i])return 0;
        for(j=0;j<4;j++)if(a->opponentTransform[i][j]!=b->opponentTransform[i][j])return 0;
    }
    return 1;
}
#undef ST_LOCK_INLINE

/* CACHED samples only a previously accepted track. Supply its saved params,
 * changing mode/progress/weight/output pointer only. The renderer checks own
 * model/header/attachment identity, never reads the opponent and never solves.
 * A failure preserves the old pose. CACHED weight zero clears it. VALIDATE may
 * keep a separate pending result for a following UPDATE; it does not replace
 * the accepted track or visible pose. */

#endif
