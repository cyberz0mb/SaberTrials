#ifndef ST_MVP_SCENE_WIRE_H
#define ST_MVP_SCENE_WIRE_H
#include "st_mvp_wire.h"
#include "st_mvp_api.h"
typedef int (*stMvpPoseWriter_t)(void *,unsigned char *,int);
static void ST_MvpWritePose(stMvpWire_t *w,void *pose,stMvpPoseWriter_t pack) {
    int position=w->pos,n=0;
    ST_WInt(w,0);
    if(!w->ok)return;
    if(pose) n=pack(pose,w->data+w->pos,w->size-w->pos<ST_MVP_POSE_LIMIT?w->size-w->pos:ST_MVP_POSE_LIMIT);
    if(pose && n<=0) { w->ok=0;return; }
    w->pos=position;ST_WInt(w,n);w->pos+=n;
}
static void *ST_MvpReadPose(stMvpWire_t *w,int *size) {
    *size=ST_RInt(w);
    if(*size<0 || *size>ST_MVP_POSE_LIMIT) {w->ok=0;return NULL;}
    return *size ? (void *)ST_RBytes(w,*size) : NULL;
}
static void ST_MvpWriteActor(stMvpWire_t *w,const stMvpActor_t *a,stMvpPoseWriter_t pack) {
    int i;
    ST_WInt(w,a->clientNum);ST_WInt(w,a->alive);ST_WInt(w,a->spawnId);
    ST_WInt(w,a->weapon);
    ST_WVec(w,a->origin);ST_WVec(w,a->angles);ST_WVec(w,a->scale);
    ST_WInt(w,a->bladeCount);
    for(i=0;i<a->bladeCount;++i) {
        const stMvpBlade_t *b=&a->blades[i];
        ST_WVec(w,b->base);ST_WVec(w,b->dir);ST_WFloat(w,b->length);ST_WFloat(w,b->radius);ST_WFloat(w,b->duration);
        ST_WInt(w,b->color);ST_WInt(w,b->style);ST_WInt(w,b->strong);ST_WInt(w,b->flags);
    }
    ST_MvpWritePose(w,a->pose,pack);
}
static void ST_MvpReadActor(stMvpWire_t *w,stMvpActor_t *a) {
    int i;
    a->clientNum=ST_RInt(w);a->alive=ST_RInt(w);a->spawnId=ST_RInt(w);
    a->weapon=ST_RInt(w);if(a->weapon<0 || a->weapon>=32)w->ok=0;
    ST_RVec(w,a->origin);ST_RVec(w,a->angles);ST_RVec(w,a->scale);
    a->bladeCount=ST_RInt(w);
    if(a->clientNum<0 || a->clientNum>=ST_MVP_ACTORS || a->bladeCount<0 || a->bladeCount>ST_MVP_BLADES) { w->ok=0;return; }
    for(i=0;i<a->bladeCount;++i) {
        stMvpBlade_t *b=&a->blades[i];
        ST_RVec(w,b->base);ST_RVec(w,b->dir);b->length=ST_RFloat(w);b->radius=ST_RFloat(w);b->duration=ST_RFloat(w);
        b->color=ST_RInt(w);b->style=ST_RInt(w);b->strong=ST_RInt(w);b->flags=ST_RInt(w);
        if(b->length<0 || b->length>4096 || b->radius<0 || b->radius>128 || b->duration<0 || b->duration>10000) w->ok=0;
    }
    a->pose=ST_MvpReadPose(w,&a->poseBytes);
}
static void ST_MvpWriteResult(stMvpWire_t *w,const stMvpClip_t *c) {
    int i;
    ST_WInt(w,0x53544d56);ST_WInt(w,ST_MVP_WIRE_VERSION);
    ST_WInt(w,c->resultTime);ST_WInt(w,c->presentation);ST_WInt(w,c->winner);ST_WInt(w,c->totalKills);
    ST_WInt(w,c->winnerScore);ST_WInt(w,c->loserScore);ST_WInt(w,c->cardOnly);ST_WInt(w,c->forfeit);
    ST_WText(w,c->name,sizeof(c->name));ST_WInt(w,c->eventCount);
    for(i=0;i<c->eventCount;++i) {
        const stMvpEvent_t *e=&c->events[i];
        ST_WInt(w,e->killTime);ST_WInt(w,e->firstTime);ST_WInt(w,e->lastTime);ST_WInt(w,e->attacker);ST_WInt(w,e->victim);
    }
}
static void ST_MvpReadResult(stMvpWire_t *w,stMvpClip_t *c) {
    int i;
    if(ST_RInt(w)!=0x53544d56 || ST_RInt(w)!=ST_MVP_WIRE_VERSION) { w->ok=0;return; }
    c->resultTime=ST_RInt(w);c->presentation=ST_RInt(w);c->winner=ST_RInt(w);c->totalKills=ST_RInt(w);
    c->winnerScore=ST_RInt(w);c->loserScore=ST_RInt(w);c->cardOnly=ST_RInt(w);c->forfeit=ST_RInt(w);
    ST_RText(w,c->name,sizeof(c->name));c->eventCount=ST_RInt(w);
    if(c->winner<0 || c->winner>=ST_MVP_ACTORS || c->eventCount<0 || c->eventCount>ST_MVP_EVENTS ||
       c->presentation<0 || c->presentation>ST_MVP_PRESENT_CHAMPION || c->resultTime<0 || c->resultTime>0x7ffff000) {w->ok=0;return;}
    for(i=0;i<c->eventCount;++i) {
        stMvpEvent_t *e=&c->events[i];
        e->killTime=ST_RInt(w);e->firstTime=ST_RInt(w);e->lastTime=ST_RInt(w);e->attacker=ST_RInt(w);e->victim=ST_RInt(w);
        if(e->firstTime<0 || e->lastTime<e->firstTime || e->lastTime>c->resultTime ||
           e->killTime<e->firstTime || e->killTime>e->lastTime ||
           e->attacker<0 || e->attacker>=ST_MVP_ACTORS || e->victim<0 || e->victim>=ST_MVP_ACTORS ||
           (i && e->killTime<c->events[i-1].killTime)) w->ok=0;
        if(!c->firstTime || e->firstTime<c->firstTime)c->firstTime=e->firstTime;
        if(e->lastTime>c->lastTime)c->lastTime=e->lastTime;
        c->killTime=e->killTime;
    }
}
static const stMvpActor_t *ST_MvpFindActor(const stMvpSample_t *sample,int client) {
    int i;for(i=0;i<sample->count;++i)if(sample->actors[i].clientNum==client)return &sample->actors[i];
    return NULL;
}
#endif
