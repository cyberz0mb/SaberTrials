#include "qcommon/st_mvp_scene_wire.h"
static unsigned char stMvpReceive[ST_MVP_WIRE_LIMIT],stMvpScene[ST_MVP_WIRE_LIMIT];
static stMvpSample_t stMvpReceivedFrames[ST_MVP_FRAMES];
static stMvpClip_t stMvpReceivedResult;
static int stMvpNetId,stMvpReceiveSize,stMvpReceivePos,stMvpReceivedCount,stMvpReceivedReady;
static const void *stMvpPoseKeys[ST_MVP_RENDER_POSES];
static void *stMvpPoseValues[ST_MVP_RENDER_POSES];
static int stMvpPoseCacheCount;
static void ST_MvpNetClear(void) {
    stMvpNetId=stMvpReceiveSize=stMvpReceivePos=stMvpReceivedCount=stMvpReceivedReady=0;
    memset(&stMvpReceivedResult,0,sizeof(stMvpReceivedResult));
}
static qboolean ST_MvpDecodeScene(int size) {
    stMvpWire_t w;int i,j,n;
    ST_WInit(&w,stMvpScene,size);
    memset(&stMvpReceivedResult,0,sizeof(stMvpReceivedResult));
    ST_MvpReadResult(&w,&stMvpReceivedResult);
    if(!w.ok || stMvpReceivedResult.resultTime!=stMvpNetId)return qfalse;
    n=ST_RInt(&w);if(n<0 || n>ST_MVP_FRAMES)return qfalse;
    memset(stMvpReceivedFrames,0,sizeof(stMvpReceivedFrames));
    for(i=0;i<n && w.ok;++i) {
        stMvpSample_t *s=&stMvpReceivedFrames[i];unsigned int actors=0;
        s->time=ST_RInt(&w);s->count=ST_RInt(&w);
        if(s->time<0 || s->time>stMvpReceivedResult.resultTime || (i && s->time<=stMvpReceivedFrames[i-1].time) ||
           s->count<0 || s->count>ST_MVP_ACTORS)return qfalse;
        for(j=0;j<s->count && w.ok;++j) {
            ST_MvpReadActor(&w,&s->actors[j]);
            if(!w.ok)return qfalse;
            if(actors&(1u<<s->actors[j].clientNum))return qfalse;
            actors|=1u<<s->actors[j].clientNum;
        }
        s->limbCount=ST_RInt(&w);if(s->limbCount<0 || s->limbCount>ST_MVP_LIMBS)return qfalse;
        for(j=0;j<s->limbCount;++j) {
            stMvpLimb_t *p=&s->limbs[j];
            p->entityNum=ST_RInt(&w);p->owner=ST_RInt(&w);p->part=ST_RInt(&w);ST_RVec(&w,p->origin);ST_RVec(&w,p->angles);
            if(p->owner<0 || p->owner>=ST_MVP_ACTORS || p->part<G2_MODELPART_HEAD || p->part>G2_MODELPART_RLEG)return qfalse;
        }
        s->propCount=ST_RInt(&w);if(s->propCount<0 || s->propCount>ST_MVP_PROPS)return qfalse;
        for(j=0;j<s->propCount;++j) {
            stMvpProp_t *p=&s->props[j];
            p->entityNum=ST_RInt(&w);p->modelIndex=ST_RInt(&w);p->brush=ST_RInt(&w);
            p->type=ST_RInt(&w);p->weapon=ST_RInt(&w);p->flags=ST_RInt(&w);ST_RVec(&w,p->velocity);
            ST_RVec(&w,p->origin);ST_RVec(&w,p->angles);ST_RVec(&w,p->scale);p->pose=ST_MvpReadPose(&w,&p->poseBytes);
            if(p->entityNum<0 || p->entityNum>=MAX_GENTITIES || p->modelIndex<0 || p->modelIndex>=MAX_MODELS)return qfalse;
        }
    }
    if(!w.ok || w.pos!=size || (!n && !stMvpReceivedResult.cardOnly))return qfalse;
    stMvpReceivedCount=n;stMvpReceivedResult.retainedBytes=size;return qtrue;
}
qboolean ST_MvpServerCommand(const char *command) {
    char arg[800];int id,size,offset,n;
    if(Q_stricmp(command,"st_mvp_begin") && Q_stricmp(command,"st_mvp_data"))return qfalse;
    trap->Cmd_Argv(1,arg,sizeof(arg));id=atoi(arg);
    if(!Q_stricmp(command,"st_mvp_begin")) {
        trap->Cmd_Argv(2,arg,sizeof(arg));size=atoi(arg);
        if(id<=0 || size<=0 || size>ST_MVP_WIRE_LIMIT || cg.demoPlayback)return qtrue;
        if(id==stMvpNetId)return qtrue;
        ST_MvpStop();ST_MvpNetClear();stMvpNetId=id;stMvpReceiveSize=size;
        return qtrue;
    }
    if(id!=stMvpNetId || !stMvpReceiveSize || stMvpReceivedReady)return qtrue;
    trap->Cmd_Argv(2,arg,sizeof(arg));offset=atoi(arg);
    if(offset!=stMvpReceivePos)return qtrue;
    trap->Cmd_Argv(3,arg,sizeof(arg));
    n=ST_MvpDecode(arg,stMvpReceive+offset,Q_min(ST_MVP_CHUNK,stMvpReceiveSize-offset));
    if(n<=0) {trap->SendClientCommand(va("st_mvp_done %d",id));ST_MvpNetClear();return qtrue;}
    stMvpReceivePos+=n;
    if(stMvpReceivePos==stMvpReceiveSize) {
        size=trap->ST_MvpDecompress(stMvpReceive,stMvpReceiveSize,stMvpScene,sizeof(stMvpScene));
        if(size<=0 || !ST_MvpDecodeScene(size)) {
            if (ST_MvpDebug()) trap->Print("MVP_TRANSFER rejected id=%d\n",id);
            trap->SendClientCommand(va("st_mvp_done %d",id));ST_MvpNetClear();return qtrue;
        }
        stMvpReceivedReady=1;
        if (ST_MvpDebug()) trap->Print("MVP_TRANSFER received id=%d bytes=%d frames=%d\n",id,stMvpReceiveSize,stMvpReceivedCount);
    }
    trap->SendClientCommand(va("st_mvp_ack %d %d",id,stMvpReceivePos));
    return qtrue;
}
static qboolean ST_MvpRemoteRead(int time,stMvpClip_t *clip) {
    int i;
    // The host already owns the history in this process. Use it immediately;
    // only remote viewers need the bounded network transfer.
    if(trap->ST_MvpRead(time,clip))return qtrue;
    if(!stMvpReceivedReady)return qfalse;
    *clip=stMvpReceivedResult;
    if(clip->cardOnly)return qtrue;
    if(!time)time=clip->firstTime;
    for(i=0;i<stMvpReceivedCount;++i) {
        const stMvpSample_t *s=&stMvpReceivedFrames[i];
        if(s->time<=time && (!clip->before || s->time>clip->before->time))clip->before=s;
        if(s->time>=time && (!clip->after || s->time<clip->after->time))clip->after=s;
    }
    if(!clip->before)clip->before=clip->after;
    if(!clip->after)clip->after=clip->before;
    return clip->before && clip->after && clip->after->time-clip->before->time<=ST_MVP_MAX_GAP;
}
static void *ST_MvpResolvePose(const void *data,int bytes) {
    int i;void *pose;
    if(!data)return NULL;
    if(!bytes)return (void *)data; // borrowed local server pose, never freed here
    if(bytes<0)return NULL;
    for(i=0;i<stMvpPoseCacheCount;++i)if(stMvpPoseKeys[i]==data)return stMvpPoseValues[i];
    if(stMvpRenderPoseCount>=ST_MVP_RENDER_POSES || stMvpPoseCacheCount>=ST_MVP_RENDER_POSES)return NULL;
    pose=trap->ST_MvpUnpackPose((const unsigned char *)data,bytes);
    if(pose)stMvpRenderPoses[stMvpRenderPoseCount++]=pose;
    stMvpPoseKeys[stMvpPoseCacheCount]=data;stMvpPoseValues[stMvpPoseCacheCount++]=pose;
    return pose;
}
