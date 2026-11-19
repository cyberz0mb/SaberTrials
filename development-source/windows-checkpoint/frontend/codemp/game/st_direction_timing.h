/* Pure C pose playback adapter. Include after anims.h and animation_t.
 * Keeps caller-owned semantic animation state, flags and gameplay timers intact.
 * Do not feed displayed speed into BG_SetAnimFinal or gameplay damage logic.
 */
#ifndef ST_DIRECTION_TIMING_H
#define ST_DIRECTION_TIMING_H
#include <math.h>
#include "st_direction_map.h"

typedef struct stDirectionalPlayback_s {
    int semanticAnim;
    int poseAnim;
    int mirrored;
    int looping;
    int hold;
    int canonicalFirst;
    int canonicalEnd;
    int poseFirst;
    int poseEnd;
    int canonicalSign;
    int poseSign;
    float canonicalSpan;
    float poseSpan;
    float canonicalSpeed;
    float poseSpeed;
    int warp; /* +1 LEFT -> RIGHT, -1 inverse, 0 ordinary proportional map */
    int clocked;
    int clockTime;
    float clockFrame;
} stDirectionalPlayback_t;

/* Model-load/spawn preflight. Both absent sides are harmless unused enum rows;
 * any available directional source requires a compatible counterpart. */
static inline int ST_DirectionValidateAnimationSet(const animation_t *animations,
    int animationCount, int *badAnim)
{
    int a;
    if (!animations || animationCount <= 0) return 0;
    for (a = 0; a < animationCount; ++a) {
        int b = ST_DirectionAnim(a);
        const animation_t *x, *y;
        if (b == a || !animations[a].numFrames) continue;
        if (b < 0 || b >= animationCount) { if (badAnim) *badAnim = a; return 0; }
        x = &animations[a]; y = &animations[b];
        if (!y->numFrames || !x->frameLerp || !y->frameLerp ||
            ((x->loopFrames != -1) != (y->loopFrames != -1)) ||
            ((x->numFrames == 1) != (y->numFrames == 1))) {
            if (badAnim) *badAnim = a;
            return 0;
        }
    }
    return 1;
}

static inline float ST_DirectionAbs(float v) { return v < 0.0f ? -v : v; }

/* Returns 0 if a counterpart is absent/empty or has incompatible topology.
 * effectiveCanonicalSpeed is the ORIGINAL signed Ghoul2 speed after applying
 * force/saber/broken-arm multipliers exactly once using the semantic anim ID.
 * Looping intentionally follows existing Ghoul2 call sites (loopFrames != -1),
 * which loop the whole clip and do not implement a partial loopFrames tail.
 */
static inline int ST_BuildDirectionalPlayback(const animation_t *animations,
    int animationCount, int semanticAnim, int mirrored,
    float effectiveCanonicalSpeed, stDirectionalPlayback_t *out)
{
    const animation_t *canonical;
    const animation_t *pose;
    stDirectionalPlayback_t p;
    int poseAnim;
    if (!animations || !out || semanticAnim < 0 || semanticAnim >= animationCount)
        return 0;
    poseAnim = ST_DirectionPoseAnim(semanticAnim, mirrored);
    if (poseAnim < 0 || poseAnim >= animationCount) return 0;
    canonical = &animations[semanticAnim];
    pose = &animations[poseAnim];
    if (!canonical->numFrames || !pose->numFrames ||
        !canonical->frameLerp || !pose->frameLerp) return 0;
    if ((canonical->loopFrames != -1) != (pose->loopFrames != -1)) return 0;
    /* A static canonical clip cannot drive a moving counterpart at equal phase. */
    if ((canonical->numFrames == 1) != (pose->numFrames == 1)) return 0;
    if (!(effectiveCanonicalSpeed > 0.0f || effectiveCanonicalSpeed < 0.0f) ||
        effectiveCanonicalSpeed > 1.0e20f || effectiveCanonicalSpeed < -1.0e20f)
        return 0; /* zero, NaN and infinities are not valid playing speeds */
    p.semanticAnim = semanticAnim;
    p.poseAnim = poseAnim;
    p.mirrored = !!mirrored;
    p.looping = canonical->loopFrames != -1;
    p.hold = canonical->numFrames == 1;
    p.canonicalSign = canonical->frameLerp < 0 ? -1 : 1;
    p.poseSign = pose->frameLerp < 0 ? -1 : 1;
    p.canonicalFirst = canonical->firstFrame +
        (p.canonicalSign < 0 ? canonical->numFrames : 0);
    p.canonicalEnd = canonical->firstFrame +
        (p.canonicalSign > 0 ? canonical->numFrames : 0);
    p.poseFirst = pose->firstFrame + (p.poseSign < 0 ? pose->numFrames : 0);
    p.poseEnd = pose->firstFrame + (p.poseSign > 0 ? pose->numFrames : 0);
    p.canonicalSpan = (float)(canonical->numFrames - (p.looping ? 0 : 1));
    p.poseSpan = (float)(pose->numFrames - (p.looping ? 0 : 1));
    p.canonicalSpeed = p.canonicalSign * ST_DirectionAbs(effectiveCanonicalSpeed);
    p.poseSpeed = p.poseSign * ST_DirectionAbs(effectiveCanonicalSpeed);
    if (!p.hold) p.poseSpeed *= p.poseSpan / p.canonicalSpan;
    /* Landmarks verified against stock and JA+ humanoid GLA. A different
     * animation layout retains the ordinary proportional mapping. */
    p.clocked = !p.looping && canonical->frameLerp == 50 &&
        ((semanticAnim == BOTH_BUTTERFLY_LEFT && canonical->firstFrame == 2021 && canonical->numFrames == 46) ||
         (semanticAnim == BOTH_BUTTERFLY_RIGHT && canonical->firstFrame == 2067 && canonical->numFrames == 56));
    p.warp = 0;
    if (p.clocked && mirrored && pose->frameLerp == 50) {
        if (semanticAnim == BOTH_BUTTERFLY_LEFT && pose->firstFrame == 2067 && pose->numFrames == 56) p.warp = 1;
        if (semanticAnim == BOTH_BUTTERFLY_RIGHT && pose->firstFrame == 2021 && pose->numFrames == 46) p.warp = -1;
    }
    p.clockTime = 0;
    p.clockFrame = (float)p.canonicalFirst;
    *out = p;
    return 1;
}

/* Phase is [0,1] for nonloops, [0,1) for loops. A one-frame pose is always 0.
 * The 1e-6 tolerance avoids treating tiny negative frame-query roundoff at the
 * start as a nearly complete cycle. A true previous loop phase is never needed
 * here: these helpers map one sampled frame, not elapsed loop count.
 */
static inline float ST_DirectionNormalizePhase(float phase, int looping, int hold)
{
    if (hold) return 0.0f;
    if (looping) {
        if (phase < 0.0f && phase > -0.000001f) return 0.0f;
        return phase - (float)floor((double)phase);
    }
    if (phase < 0.0f) return 0.0f;
    if (phase > 1.0f) return 1.0f;
    return phase;
}

static inline float ST_DirectionCanonicalPhase(const stDirectionalPlayback_t *p, float frame)
{
    if (p->hold) return 0.0f;
    return ST_DirectionNormalizePhase(
        (frame - p->canonicalFirst) * p->canonicalSign / p->canonicalSpan,
        p->looping, p->hold);
}

static inline float ST_DirectionPosePhase(const stDirectionalPlayback_t *p, float frame)
{
    if (p->hold) return 0.0f;
    return ST_DirectionNormalizePhase(
        (frame - p->poseFirst) * p->poseSign / p->poseSpan,
        p->looping, p->hold);
}

static inline float ST_DirectionCanonicalAtPhase(const stDirectionalPlayback_t *p, float phase)
{
    return p->canonicalFirst + p->canonicalSign * p->canonicalSpan *
        ST_DirectionNormalizePhase(phase, p->looping, p->hold);
}

static inline float ST_DirectionPoseAtPhase(const stDirectionalPlayback_t *p, float phase)
{
    return p->poseFirst + p->poseSign * p->poseSpan *
        ST_DirectionNormalizePhase(phase, p->looping, p->hold);
}

/* Before GetBoneFrame results enter CG_PlayerAnimEvents, inverse-map the FLOAT
 * frame, then floor it. pe.frames/events remain in semantic frame coordinates.
 */
static inline float ST_DirectionLandmark(float offset, int reverse, float *slope)
{
    static const float left[8] = {0,11,19,24,29,35,44,45};
    static const float right[8] = {0,13,20,26,32,36,52,55};
    const float *x = reverse ? right : left, *y = reverse ? left : right;
    int segment = 0;
    float rate;
    if (offset < 0) offset = 0;
    if (offset > x[7]) offset = x[7];
    while (segment < 6 && offset >= x[segment+1]) ++segment;
    rate = (y[segment+1]-y[segment])/(x[segment+1]-x[segment]);
    if (slope) *slope = rate;
    return y[segment] + (offset-x[segment])*rate;
}

static inline float ST_DirectionCanonicalFrame(const stDirectionalPlayback_t *p, float poseFrame)
{
    if (p->semanticAnim == p->poseAnim) return poseFrame;
    if (p->warp) return p->canonicalFirst + ST_DirectionLandmark(
        poseFrame-p->poseFirst, p->warp > 0, 0);
    return ST_DirectionCanonicalAtPhase(p, ST_DirectionPosePhase(p, poseFrame));
}

/* For callers synchronizing a semantic frame into a displayed animation. */
static inline float ST_DirectionPoseFrame(const stDirectionalPlayback_t *p, float canonicalFrame)
{
    if (p->semanticAnim == p->poseAnim) return canonicalFrame;
    if (p->warp) return p->poseFirst + ST_DirectionLandmark(
        canonicalFrame-p->canonicalFirst, p->warp < 0, 0);
    return ST_DirectionPoseAtPhase(p, ST_DirectionCanonicalPhase(p, canonicalFrame));
}

/* Speed/hand/weapon-mode changes while a canonical clip continues. Caller must
 * additionally require matching semantic flip/restart state. Do not use this
 * for a newly restarted clip. beginFrame MUST remain float at the call site.
 */
static inline int ST_DirectionResumeFrame(const stDirectionalPlayback_t *oldPlayback,
    const stDirectionalPlayback_t *newPlayback, float oldPoseFrame, float *newPoseFrame)
{
    if (!oldPlayback || !newPlayback || !newPoseFrame ||
        oldPlayback->semanticAnim != newPlayback->semanticAnim ||
        oldPlayback->looping != newPlayback->looping) return 0;
    *newPoseFrame = ST_DirectionPoseFrame(newPlayback,
        ST_DirectionCanonicalFrame(oldPlayback, oldPoseFrame));
    return 1;
}

/* A local semantic clock prevents drift when Ghoul2's current segment speed
 * extrapolates past several knots between updates. Never changes ps timers. */
static inline float ST_DirectionClockFrame(const stDirectionalPlayback_t *p, int now)
{
    float elapsed = now >= p->clockTime ? (float)(now-p->clockTime) : 0.0f;
    float frame = p->clockFrame + elapsed*p->canonicalSpeed/50.0f;
    return ST_DirectionCanonicalAtPhase(p, ST_DirectionCanonicalPhase(p, frame));
}

static inline void ST_DirectionClockAnchor(stDirectionalPlayback_t *p, float canonicalFrame, int now)
{
    p->clockFrame = canonicalFrame;
    p->clockTime = now;
}

static inline void ST_DirectionClockContinue(stDirectionalPlayback_t *p,
    const stDirectionalPlayback_t *previous, float canonicalFrame, int now)
{
    if (previous && previous->clocked && previous->semanticAnim == p->semanticAnim &&
        previous->canonicalSpeed == p->canonicalSpeed) {
        /* Keep the original anchor instead of accumulating float roundoff at
         * every display refresh. The same elapsed time gives the same pose. */
        p->clockFrame = previous->clockFrame;
        p->clockTime = previous->clockTime;
    } else ST_DirectionClockAnchor(p, canonicalFrame, now);
}

static inline float ST_DirectionClockPose(const stDirectionalPlayback_t *p, int now)
{
    return ST_DirectionPoseFrame(p, ST_DirectionClockFrame(p, now));
}

static inline float ST_DirectionSpeedAtFrame(const stDirectionalPlayback_t *p, float canonicalFrame)
{
    float slope;
    if (!p->warp) return p->poseSpeed;
    ST_DirectionLandmark(canonicalFrame-p->canonicalFirst, p->warp < 0, &slope);
    return p->canonicalSpeed*slope;
}

#endif
