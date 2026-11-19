#include <assert.h>
#include <stdio.h>
#include "st_mvp_scene_wire.h"
#include "st_mvp_retention.h"
static unsigned char bytes[16384];
static int pack(void *pose,unsigned char *out,int cap) {if(cap<12)return 0;memcpy(out,pose,12);return 12;}
int main(void) {
    stMvpWire_t w,r;stMvpActor_t a,b;stMvpClip_t result,decoded;
    unsigned char pose[12]={4,8,15,16,23,42};int size,i;
    memset(&a,0,sizeof(a));a.clientNum=31;a.alive=1;a.spawnId=8;a.bladeCount=16;a.pose=pose;
    a.origin[0]=-32768;a.origin[1]=32768;
    for(i=0;i<16;++i){a.blades[i].length=48+i;a.blades[i].radius=3;a.blades[i].dir[2]=1;a.blades[i].duration=150;a.blades[i].color=i%6;}
    ST_WInit(&w,bytes,sizeof(bytes));ST_MvpWriteActor(&w,&a,pack);assert(w.ok);size=w.pos;
    memset(&b,0,sizeof(b));ST_WInit(&r,bytes,size);ST_MvpReadActor(&r,&b);
    assert(r.ok && r.pos==size && b.clientNum==31 && b.bladeCount==16 && b.poseBytes==12);
    assert(!memcmp(b.pose,pose,12) && b.blades[15].length==63 && b.origin[0]==-32768);
    for(i=0;i<size;++i) {ST_WInit(&r,bytes,i);memset(&b,0,sizeof(b));ST_MvpReadActor(&r,&b);assert(!r.ok);}
    bytes[0]=32;ST_WInit(&r,bytes,size);ST_MvpReadActor(&r,&b);assert(!r.ok);bytes[0]=31;
    memset(&result,0,sizeof(result));result.winner=31;result.totalKills=240;result.resultTime=100000;
    strcpy(result.name,"^5Custom MVP");result.eventCount=32;
    for(i=0;i<32;++i){stMvpEvent_t *e=&result.events[i];e->killTime=5000+i*2500;e->firstTime=e->killTime-2000;e->lastTime=e->killTime+500;e->attacker=31;e->victim=i%31;}
    ST_WInit(&w,bytes,sizeof(bytes));ST_MvpWriteResult(&w,&result);assert(w.ok);size=w.pos;
    memset(&decoded,0,sizeof(decoded));ST_WInit(&r,bytes,size);ST_MvpReadResult(&r,&decoded);
    assert(r.ok && r.pos==size && decoded.totalKills==240 && decoded.eventCount==32 && decoded.lastTime==83000);
    for(i=0;i<size;++i){ST_WInit(&r,bytes,i);memset(&decoded,0,sizeof(decoded));ST_MvpReadResult(&r,&decoded);assert(!r.ok);}
    result.events[31].lastTime=100001;ST_WInit(&w,bytes,sizeof(bytes));ST_MvpWriteResult(&w,&result);
    memset(&decoded,0,sizeof(decoded));ST_WInit(&r,bytes,w.pos);ST_MvpReadResult(&r,&decoded);assert(!r.ok);
    {
        stMvpEvent_t events[32];int count=1;
        memset(events,0,sizeof(events));events[0].attacker=0;events[0].killTime=123;
        for(i=0;i<1000;++i) {
            if(count==32){int drop=ST_MvpRetireIndex(events,count,0);assert(drop!=0);--count;memmove(events+drop,events+drop+1,(count-drop)*sizeof(events[0]));}
            events[count].attacker=1+i%31;events[count++].killTime=1000+i;
            assert(events[0].killTime==123);
        }
        assert(ST_MvpRetireIndex(events,count,1)==0);
    }
    puts("Scene bounds, malformed data and passive-leader retention passed.");return 0;
}
