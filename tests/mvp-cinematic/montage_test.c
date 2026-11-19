#include <assert.h>
#include <math.h>
#include <stdio.h>
#include "st_mvp_montage.h"

static stMvpClip_t clip;
static stMvpPlan_t plan;
static void events(int count,int gap) {
    int i;
    memset(&clip,0,sizeof(clip));
    clip.eventCount=count;
    for (i=0; i<count; ++i) {
        clip.events[i].killTime=10000+i*gap;
        clip.events[i].firstTime=clip.events[i].killTime-4500;
        clip.events[i].lastTime=clip.events[i].killTime+600;
    }
}
static void verify(void) {
    int i,t;
    double previous=0;
    assert(plan.duration>0 && plan.duration<=15000);
    assert(plan.duration-plan.shots[plan.count-1].start-plan.shots[plan.count-1].duration==2500);
    for (i=0; i<plan.count; ++i) {
        stMvpShot_t *shot=&plan.shots[i];
        double source=ST_MvpShotSource(shot,0);
        assert(source>=previous);
        assert(source>=clip.events[shot->firstEvent].firstTime);
        for (t=1; t<=shot->duration; ++t) {
            double next=ST_MvpShotSource(shot,t),speed=next-source;
            assert(speed>=0 && speed<=1.501);
            if (source>=shot->firstKill-187 && next<=shot->lastKill+187)
                assert(fabs(speed-.25)<.001);
            source=next;
        }
        assert(source>=shot->lastKill+187 && source<=clip.events[shot->lastEvent].lastTime);
        previous=source;
    }
    {
        stMvpShot_t *last=&plan.shots[plan.count-1];
        double held=ST_MvpShotSource(last,last->duration);
        for(t=last->start+last->duration;t<plan.duration;++t)
            assert(ST_MvpShotSource(last,ST_MvpShotElapsed(last,t))==held);
    }
}
int main(void) {
    events(0,0); ST_MvpBuildPlan(&clip,&plan); assert(!plan.count);
    events(1,0); ST_MvpBuildPlan(&clip,&plan); assert(plan.duration==7000); verify();
    events(5,10000); ST_MvpBuildPlan(&clip,&plan); assert(plan.kills==5 && plan.duration==15000); verify();
    events(5,2000); ST_MvpBuildPlan(&clip,&plan); assert(plan.kills==5); verify();
    events(10,100); ST_MvpBuildPlan(&clip,&plan); assert(plan.kills==10 && plan.count==1); verify();
    events(20,10000); ST_MvpBuildPlan(&clip,&plan); assert(plan.kills==5 && plan.shots[0].firstEvent==15); verify();
    events(1,0); clip.events[0].firstTime=9812; clip.events[0].lastTime=10188;
    ST_MvpBuildPlan(&clip,&plan); assert(plan.duration>=4000 && plan.duration<4100); verify();
    events(3,10000); clip.presentation=ST_MVP_PRESENT_DUEL;
    ST_MvpBuildPlan(&clip,&plan);
    assert(plan.count==1 && plan.kills==1 && plan.duration==7500);
    assert(plan.shots[0].firstEvent==2 && plan.shots[0].lastEvent==2);
    assert(fabs(ST_MvpShotSource(&plan.shots[0],3750)-30000)<.001);
    verify();
    clip.presentation=ST_MVP_PRESENT_CHAMPION;
    ST_MvpBuildPlan(&clip,&plan); assert(plan.duration==7500); verify();
    clip.presentation=ST_MVP_PRESENT_MATCH;
    ST_MvpBuildPlan(&clip,&plan); assert(plan.duration==7500); verify();
    clip.cardOnly=1; clip.eventCount=0;
    ST_MvpBuildPlan(&clip,&plan); assert(plan.duration==3000 && plan.count==0 && plan.kills==0);
    puts("MVP montage timing, fast kills, trimming and 15-second bound passed.");
    return 0;
}
