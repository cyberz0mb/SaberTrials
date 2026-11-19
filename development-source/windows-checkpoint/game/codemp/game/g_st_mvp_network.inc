/* Selected historical poses are sent only after the match, in acknowledged
 * bounded bursts. No hidden live-player information is added to snapshots. */
#include "qcommon/st_mvp_scene_wire.h"
#include "qcommon/st_mvp_montage.h"
static unsigned char stMvpRaw[ST_MVP_WIRE_LIMIT],stMvpPacked[ST_MVP_WIRE_LIMIT];
static int stMvpPackedSize,stMvpTransfer,stMvpPrepared,stMvpNetStarted;
static int stMvpSent[MAX_CLIENTS],stMvpAck[MAX_CLIENTS],stMvpReady[MAX_CLIENTS],stMvpSkipped[MAX_CLIENTS];
static void ST_MvpNetworkReset(void) {
    stMvpPackedSize=stMvpPrepared=stMvpTransfer=stMvpNetStarted=0;
    memset(stMvpSent,0,sizeof(stMvpSent));memset(stMvpAck,0,sizeof(stMvpAck));
    memset(stMvpReady,0,sizeof(stMvpReady));memset(stMvpSkipped,0,sizeof(stMvpSkipped));
}
static qboolean ST_MvpSampleNeeded(const stMvpPlan_t *plan,int time) {
    int i;for(i=0;i<plan->count;++i)if(time>=(int)ST_MvpShotSource(&plan->shots[i],0)-ST_MVP_MAX_GAP-300 &&
        time<=(int)ST_MvpShotSource(&plan->shots[i],plan->shots[i].duration)+ST_MVP_MAX_GAP)return qtrue;
    return qfalse;
}
static qboolean ST_MvpActorNeeded(const stMvpSample_t *s,int index) {
    const stMvpActor_t *a=&s->actors[index],*winner=ST_MvpFindActor(s,stMvpFinal.winner);
    int i;
    if(a->clientNum==stMvpFinal.winner)return qtrue;
    for(i=0;i<stMvpFinal.eventCount;++i)if(a->clientNum==stMvpFinal.events[i].victim &&
        s->time>=stMvpFinal.events[i].firstTime-300 && s->time<=stMvpFinal.events[i].lastTime+300)return qtrue;
    return winner && DistanceSquared(a->origin,winner->origin)<512*512;
}
static int ST_MvpMakePacket(void) {
    stMvpWire_t w;stMvpPlan_t plan;int i,j,n=0,indices[ST_MVP_FRAMES];
    ST_MvpBuildPlan(&stMvpFinal,&plan);
    ST_WInit(&w,stMvpRaw,sizeof(stMvpRaw));ST_MvpWriteResult(&w,&stMvpFinal);
    for(i=0;i<ST_MVP_FRAMES;++i)if(stMvpFrames[i].count && ST_MvpSampleNeeded(&plan,stMvpFrames[i].time))indices[n++]=i;
    for(i=1;i<n;++i) {int v=indices[i];j=i;while(j>0 && stMvpFrames[indices[j-1]].time>stMvpFrames[v].time){indices[j]=indices[j-1];--j;}indices[j]=v;}
    ST_WInt(&w,n);
    for(i=0;i<n && w.ok;++i) {
        const stMvpSample_t *s=&stMvpFrames[indices[i]];int actors=0;
        for(j=0;j<s->count;++j)if(ST_MvpActorNeeded(s,j))++actors;
        ST_WInt(&w,s->time);ST_WInt(&w,actors);
        for(j=0;j<s->count;++j)if(ST_MvpActorNeeded(s,j))ST_MvpWriteActor(&w,&s->actors[j],trap->ST_MvpPackPose);
        ST_WInt(&w,s->limbCount);
        for(j=0;j<s->limbCount;++j) {
            const stMvpLimb_t *p=&s->limbs[j];
            ST_WInt(&w,p->entityNum);ST_WInt(&w,p->owner);ST_WInt(&w,p->part);ST_WVec(&w,p->origin);ST_WVec(&w,p->angles);
        }
        ST_WInt(&w,s->propCount);
        for(j=0;j<s->propCount;++j) {
            const stMvpProp_t *p=&s->props[j];
            ST_WInt(&w,p->entityNum);ST_WInt(&w,p->modelIndex);ST_WInt(&w,p->brush);
            ST_WInt(&w,p->type);ST_WInt(&w,p->weapon);ST_WInt(&w,p->flags);ST_WVec(&w,p->velocity);
            ST_WVec(&w,p->origin);ST_WVec(&w,p->angles);ST_WVec(&w,p->scale);ST_MvpWritePose(&w,p->pose,trap->ST_MvpPackPose);
        }
    }
    if(!w.ok)return 0;
    return trap->ST_MvpCompress(stMvpRaw,w.pos,stMvpPacked,sizeof(stMvpPacked));
}
static void ST_MvpNetworkFrame(void) {
    int i;
    if(!level.intermissiontime || !ST_MvpLocalEnabled())return;
    if(!stMvpPrepared) {
        if(level.gametype==GT_DUEL && (!stMvpFinalized || !stMvpFinal.resultTime))return;
        if(!stMvpFinalized)ST_MvpFinalize();
        if(!stMvpFinal.resultTime)return;
        stMvpPrepared=1;stMvpTransfer=level.intermissiontime;stMvpNetStarted=level.time;
        while(!(stMvpPackedSize=ST_MvpMakePacket()) && stMvpFinal.eventCount>1) {
            --stMvpFinal.eventCount;memmove(stMvpFinal.events,stMvpFinal.events+1,stMvpFinal.eventCount*sizeof(stMvpFinal.events[0]));
        }
        if(!stMvpPackedSize) {stMvpFinal.eventCount=0;stMvpFinal.cardOnly=1;stMvpPackedSize=ST_MvpMakePacket();}
        if (trap->Cvar_VariableIntegerValue("developer")) trap->Print("MVP_TRANSFER id=%d bytes=%d actors=%d clips=%d mode=%d\n",stMvpTransfer,stMvpPackedSize,stMvpActorCount,stMvpFinal.eventCount,level.gametype);
    }
    if(stMvpPackedSize<=0)return;
    for(i=0;i<level.maxclients;++i) {
        int burst=0;
        if(level.clients[i].pers.connected!=CON_CONNECTED || (g_entities[i].r.svFlags&SVF_BOT) || stMvpSkipped[i])continue;
        if(level.clients[i].pers.localClient) {if(!stMvpReady[i])stMvpReady[i]=level.time;continue;}
        if(!stMvpSent[i]) {
            trap->SendServerCommand(i,va("st_mvp_begin %d %d",stMvpTransfer,stMvpPackedSize));
            stMvpSent[i]=1;
        }
        if(stMvpAck[i]!=stMvpSent[i]-1)continue;
        while(stMvpSent[i]-1<stMvpPackedSize && burst++<8) {
            int offset=stMvpSent[i]-1,n=Q_min(ST_MVP_CHUNK,stMvpPackedSize-offset);char text[800];
            if(ST_MvpEncode(stMvpPacked+offset,n,text,sizeof(text))<0)break;
            trap->SendServerCommand(i,va("st_mvp_data %d %d %s",stMvpTransfer,offset,text));stMvpSent[i]+=n;
        }
    }
}
qboolean ST_MvpNetCommand(int client,const char *command) {
    char arg[32];int id,offset;
    if(Q_stricmp(command,"st_mvp_ack") && Q_stricmp(command,"st_mvp_done"))return qfalse;
    if(client<0 || client>=level.maxclients || !level.intermissiontime)return qtrue;
    trap->Argv(1,arg,sizeof(arg));id=atoi(arg);
    if(id!=stMvpTransfer)return qtrue;
    if(!Q_stricmp(command,"st_mvp_done")) {stMvpSkipped[client]=1;return qtrue;}
    trap->Argv(2,arg,sizeof(arg));offset=atoi(arg);
    if(offset>=stMvpAck[client] && offset<=stMvpSent[client]-1)stMvpAck[client]=offset;
    if(offset==stMvpPackedSize && !stMvpReady[client])stMvpReady[client]=level.time;
    return qtrue;
}
static qboolean ST_MvpNetworkHold(void) {
    int i;
    ST_MvpNetworkFrame();
    if(!stMvpPrepared || !stMvpPackedSize || level.time-stMvpNetStarted>30000)return qfalse;
    for(i=0;i<level.maxclients;++i) {
        if(level.clients[i].pers.connected!=CON_CONNECTED || (g_entities[i].r.svFlags&SVF_BOT) || stMvpSkipped[i])continue;
        if(!stMvpReady[i] && level.time-stMvpNetStarted<12000)return qtrue;
        if(stMvpReady[i] && level.time-stMvpReady[i]<(stMvpFinal.cardOnly?ST_MVP_CARD_MS:ST_MVP_MAX_PLAYBACK_MS)+1000)return qtrue;
    }
    return qfalse;
}
