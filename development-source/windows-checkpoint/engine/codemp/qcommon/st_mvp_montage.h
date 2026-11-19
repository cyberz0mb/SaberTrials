/* Adaptive local montage schedule. GPL-2.0-or-later. */
#ifndef ST_MVP_MONTAGE_H
#define ST_MVP_MONTAGE_H
#include <string.h>
#include "st_mvp_api.h"
#include "st_mvp_timing.h"
#define ST_MVP_MAX_PLAYBACK_MS 15000
#define ST_MVP_LINGER_MS 2500
#define ST_MVP_ACTION_BUDGET_MS (ST_MVP_MAX_PLAYBACK_MS-ST_MVP_LINGER_MS)
typedef struct {
    int firstEvent,lastEvent,firstKill,lastKill,start,duration,fullDuration,trim,legacy;
} stMvpShot_t;
typedef struct { int count,kills,duration; stMvpShot_t shots[ST_MVP_EVENTS]; } stMvpPlan_t;

/* Every presentation keeps its final captured scene before showing results.
 * Clamp the source clock, not the real-time clock used by skip and completion. */
static int ST_MvpShotElapsed(const stMvpShot_t *shot,int elapsed) {
    int t=elapsed-shot->start;
    return t<0 ? 0 : t>shot->duration ? shot->duration : t;
}

static double ST_MvpShotSource(const stMvpShot_t *shot,int elapsed) {
    double t=elapsed+shot->trim;
    double slow=1500.0+4.0*(shot->lastKill-shot->firstKill);
    double approach=shot->fullDuration-slow-250;
    double ramp=approach-250, lead, progress;
    double fast=ST_MVP_APPROACH_SPEED;
    double accelDistance=250*(1+fast)*.5;
    // Ease earlier instead of extending the montage. Very short shots already
    // ramp immediately after acceleration, so use only their available time.
    if (ramp>750) ramp=750;
    lead=accelDistance+(approach-250-ramp)*fast+ramp*(fast+.25)*.5;
    if (shot->legacy==2) return shot->firstKill+(t<500 ?
        ST_MvpSourceOffset(0)-500+t : ST_MvpSourceOffset((int)t-500));
    if (shot->legacy) return shot->firstKill+ST_MvpSourceOffset((int)t);
    if (t<0) t=0;
    if (t>shot->fullDuration) t=shot->fullDuration;
    if (t<250) progress=ST_MvpRamp(t,250,1,fast);
    else if (t<approach-ramp) progress=accelDistance+(t-250)*fast;
    else if (t<approach) progress=accelDistance+(approach-ramp-250)*fast+ST_MvpRamp(t-approach+ramp,ramp,fast,.25);
    else if (t<approach+slow) progress=lead+(t-approach)*.25;
    else progress=lead+slow*.25+ST_MvpRamp(t-approach-slow,250,.25,1);
    return shot->firstKill-187.5-lead+progress;
}

static void ST_MvpTrimPlan(const stMvpClip_t *clip,stMvpPlan_t *plan) {
    int i,previousEnd=0;
    plan->duration=0;
    for (i=0; i<plan->count; ++i) {
        stMvpShot_t *shot=&plan->shots[i];
        int first=clip->events[shot->firstEvent].firstTime;
        int last=clip->events[shot->lastEvent].lastTime;
        int lo=0,hi=shot->fullDuration,end;
        shot->trim=0;
        if (first<=previousEnd) first=previousEnd+1;
        while (lo<hi) { int mid=(lo+hi)/2; if (ST_MvpShotSource(shot,mid)<first) lo=mid+1; else hi=mid; }
        shot->trim=lo;
        lo=0; hi=shot->fullDuration-shot->trim;
        while (lo<hi) { int mid=(lo+hi+1)/2; if (ST_MvpShotSource(shot,mid)>last) hi=mid-1; else lo=mid; }
        end=lo;
        shot->start=plan->duration;
        shot->duration=end;
        plan->duration+=end;
        previousEnd=(int)ST_MvpShotSource(shot,end);
    }
}

static void ST_MvpBuildPlan(const stMvpClip_t *clip,stMvpPlan_t *plan) {
    int start,i,extra;
    memset(plan,0,sizeof(*plan));
    if (clip->cardOnly) { plan->duration=ST_MVP_CARD_MS; return; }
    if (clip->eventCount<=0 || clip->eventCount>ST_MVP_EVENTS) return;
    if (clip->presentation!=ST_MVP_PRESENT_MVP) {
        // Duel adapters provide only the deciding event. Defensively choose
        // the latest if a future caller supplies multiple events.
        stMvpShot_t *shot=&plan->shots[0];
        plan->count=plan->kills=1;
        shot->firstEvent=shot->lastEvent=clip->eventCount-1;
        shot->firstKill=shot->lastKill=clip->events[shot->firstEvent].killTime;
        shot->legacy=2; shot->fullDuration=ST_MVP_WINNER_MS;
        ST_MvpTrimPlan(clip,plan);
        plan->duration+=ST_MVP_LINGER_MS;
        return;
    }
    for (start=0; start<clip->eventCount; ++start) {
        plan->count=0; plan->kills=clip->eventCount-start;
        for (i=start; i<clip->eventCount; ++i) {
            stMvpShot_t *shot=plan->count ? &plan->shots[plan->count-1] : NULL;
            if (!shot || clip->events[i].killTime-shot->lastKill>600) {
                shot=&plan->shots[plan->count++];
                memset(shot,0,sizeof(*shot));
                shot->firstEvent=i; shot->firstKill=clip->events[i].killTime;
            }
            shot->lastEvent=i; shot->lastKill=clip->events[i].killTime;
            shot->fullDuration=2500+4*(shot->lastKill-shot->firstKill);
        }
        ST_MvpTrimPlan(clip,plan);
        if (plan->duration<=ST_MVP_ACTION_BUDGET_MS) break;
    }
    extra=ST_MVP_ACTION_BUDGET_MS-plan->duration;
    for (i=0; i<plan->count; ++i) {
        int add=extra/(plan->count-i);
        if (add>1500) add=1500;
        plan->shots[i].fullDuration+=add;
        extra-=add;
    }
    if (plan->kills==1) { plan->shots[0].legacy=1; plan->shots[0].fullDuration=4500; }
    ST_MvpTrimPlan(clip,plan);
    if(plan->count && plan->duration)plan->duration+=ST_MVP_LINGER_MS;
}
#endif
