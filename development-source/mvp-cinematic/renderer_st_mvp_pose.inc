/* Portable pose snapshots: never transmit allocator addresses or model handles. */
#include "qcommon/st_mvp_wire.h"
static bool ST_MvpAssetPath(const char *s) {
    if (!s[0]) return true;
    if (s[0]=='/' || s[0]=='\\' || strstr(s,"..") || strchr(s,':')) return false;
    for (;*s;++s) if ((unsigned char)*s<32 || *s=='"') return false;
    return true;
}
static void ST_MvpWriteBone(stMvpWire_t *w,const boneInfo_t &b) {
    ST_WInt(w,b.boneNumber); ST_WInt(w,b.flags);
    for(int a=0;a<3;++a) for(int c=0;c<4;++c) ST_WFloat(w,b.matrix.matrix[a][c]);
    ST_WInt(w,b.startFrame); ST_WInt(w,b.endFrame); ST_WInt(w,b.startTime); ST_WInt(w,b.pauseTime);
    ST_WFloat(w,b.animSpeed); ST_WFloat(w,b.blendFrame); ST_WInt(w,b.blendLerpFrame);
    ST_WInt(w,b.blendTime); ST_WInt(w,b.blendStart); ST_WInt(w,b.boneBlendTime); ST_WInt(w,b.boneBlendStart);
}
static boneInfo_t ST_MvpReadBone(stMvpWire_t *w) {
    boneInfo_t b;
    memset(&b,0,sizeof(b));
    b.boneNumber=ST_RInt(w); b.flags=ST_RInt(w);
    for(int a=0;a<3;++a) for(int c=0;c<4;++c) b.matrix.matrix[a][c]=ST_RFloat(w);
    // Render-side Ghoul2 uses newMatrix for angle overrides. Network bone
    // reconstruction in the engine initializes it from the captured matrix.
    memcpy(&b.newMatrix,&b.matrix,sizeof(b.matrix));
    b.startFrame=ST_RInt(w); b.endFrame=ST_RInt(w); b.startTime=ST_RInt(w); b.pauseTime=ST_RInt(w);
    b.animSpeed=ST_RFloat(w); b.blendFrame=ST_RFloat(w); b.blendLerpFrame=ST_RInt(w);
    b.blendTime=ST_RInt(w); b.blendStart=ST_RInt(w); b.boneBlendTime=ST_RInt(w); b.boneBlendStart=ST_RInt(w);
    // Ragdoll runtime contains process-local pointers; replay uses the captured
    // animation/angle override and never starts a second physics simulation.
    b.flags&=~BONE_ANGLES_RAGDOLL;
    return b;
}
int ST_MvpPackPose(void *input,unsigned char *data,int cap) {
    stMvpWire_t w;
    CGhoul2Info_v *pose=(CGhoul2Info_v *)input;
    if(!pose || !pose->IsValid() || pose->size()<1 || pose->size()>8) return 0;
    ST_WInit(&w,data,cap); ST_WInt(&w,ST_MVP_WIRE_VERSION); ST_WInt(&w,pose->size());
    for(int i=0;i<pose->size();++i) {
        CGhoul2Info &m=(*pose)[i];
        bool active=m.mModelindex>=0 && m.mFileName[0] && G2_SetupModelPointers(&m);
        ST_WInt(&w,active);
        if(!active) continue;
        if(m.mSlist.size()>1024 || m.mBlist.size()>256 || m.mBltlist.size()>256) return 0;
        ST_WText(&w,m.mFileName,MAX_QPATH);
        ST_WText(&w,m.mCustomSkin ? R_GetSkinByHandle(m.mCustomSkin)->name : "",MAX_QPATH);
        ST_WInt(&w,m.mModelBoltLink); ST_WInt(&w,m.mSurfaceRoot); ST_WInt(&w,m.mNewOrigin);
        ST_WInt(&w,m.mAnimFrameDefault); ST_WInt(&w,m.mFlags);
        ST_WInt(&w,(int)m.mSlist.size());
        for(size_t n=0;n<m.mSlist.size();++n) { ST_WInt(&w,m.mSlist[n].surface); ST_WInt(&w,m.mSlist[n].offFlags); }
        ST_WInt(&w,(int)m.mBlist.size());
        for(size_t n=0;n<m.mBlist.size();++n) ST_MvpWriteBone(&w,m.mBlist[n]);
        ST_WInt(&w,(int)m.mBltlist.size());
        for(size_t n=0;n<m.mBltlist.size();++n) {
            ST_WInt(&w,m.mBltlist[n].boneNumber); ST_WInt(&w,m.mBltlist[n].surfaceNumber);
            ST_WInt(&w,m.mBltlist[n].surfaceType); ST_WInt(&w,m.mBltlist[n].boltUsed);
        }
        ST_WInt(&w,m.mSTLockActive ? 1 : 0);
        ST_WFloat(&w,m.mSTLockActive ? m.mSTLockParams.weight : 0);
        if(m.mSTLockActive) for(int n=0;n<53;++n)
            for(int a=0;a<3;++a) for(int c=0;c<4;++c) ST_WFloat(&w,m.mSTLockLocal[n].matrix[a][c]);
    }
    return w.ok ? w.pos : 0;
}
void *ST_MvpUnpackPose(const unsigned char *data,int size) {
    stMvpWire_t w;
    CGhoul2Info_v *pose=NULL;
    int count;
    if(!data || size<8 || size>ST_MVP_POSE_LIMIT) return NULL;
    ST_WInit(&w,(void *)data,size);
    if(ST_RInt(&w)!=ST_MVP_WIRE_VERSION) return NULL;
    count=ST_RInt(&w); if(count<1 || count>8) return NULL;
    pose=new CGhoul2Info_v; pose->resize(count);
    for(int i=0;i<count && w.ok;++i) {
        CGhoul2Info &m=(*pose)[i];
        char file[MAX_QPATH],skin[MAX_QPATH]; int bones,surfaces,n;
        if(!ST_RInt(&w)) continue;
        ST_RText(&w,file,sizeof(file)); ST_RText(&w,skin,sizeof(skin));
        if(!w.ok || !file[0] || !ST_MvpAssetPath(file) || !ST_MvpAssetPath(skin)) { w.ok=0; break; }
        Q_strncpyz(m.mFileName,file,sizeof(m.mFileName)); m.mModelindex=i;
        bool fallback=false;
        if(!G2_SetupModelPointers(&m)) {
            if(i) { w.ok=0; break; }
            Q_strncpyz(m.mFileName,"models/players/kyle/model.glm",sizeof(m.mFileName));
            Q_strncpyz(skin,"models/players/kyle/model_default.skin",sizeof(skin));
            m.mModelindex=i; fallback=true;
            if(!G2_SetupModelPointers(&m)) { w.ok=0; break; }
        }
        bones=m.aHeader->numBones; surfaces=ST_MVP_MODEL_HEADER(m.currentModel)->numSurfaces;
        m.mCustomSkin=skin[0] ? RE_RegisterSkin(skin) : 0;
        m.mSkin=m.mCustomSkin;
        m.mModelBoltLink=ST_RInt(&w); m.mSurfaceRoot=ST_RInt(&w); m.mNewOrigin=ST_RInt(&w);
        m.mAnimFrameDefault=ST_RInt(&w); m.mFlags=ST_RInt(&w)&(GHOUL2_NORENDER|GHOUL2_NEWORIGIN);
        if(m.mSurfaceRoot<0 || m.mSurfaceRoot>=surfaces) m.mSurfaceRoot=0;
        if(m.mAnimFrameDefault<0 || m.mAnimFrameDefault>=m.aHeader->numFrames) m.mAnimFrameDefault=0;
        n=ST_RInt(&w); if(n<0 || n>1024) { w.ok=0; break; }
        for(int j=0;j<n;++j) {
            surfaceInfo_t s; s.surface=ST_RInt(&w); s.offFlags=ST_RInt(&w);
            if(s.surface>=0 && s.surface<surfaces && !fallback) m.mSlist.push_back(s);
        }
        n=ST_RInt(&w); if(n<0 || n>256) { w.ok=0; break; }
        for(int j=0;j<n;++j) {
            boneInfo_t b=ST_MvpReadBone(&w);
            if(b.boneNumber>=-1 && b.boneNumber<bones && b.startFrame>=0 &&
               b.endFrame>=0 && b.endFrame<=m.aHeader->numFrames && b.startFrame<m.aHeader->numFrames &&
               b.blendFrame>=0 && b.blendFrame<m.aHeader->numFrames &&
               b.blendLerpFrame>=0 && b.blendLerpFrame<m.aHeader->numFrames &&
               b.blendTime>=0 && b.blendTime<=60000 && b.boneBlendTime>=0 && b.boneBlendTime<=60000 &&
               b.animSpeed>=-100 && b.animSpeed<=100) m.mBlist.push_back(b);
            else if(!fallback && b.boneNumber!=-1) w.ok=0;
        }
        n=ST_RInt(&w); if(n<0 || n>256) { w.ok=0; break; }
        for(int j=0;j<n;++j) {
            boltInfo_t b; b.boneNumber=ST_RInt(&w); b.surfaceNumber=ST_RInt(&w);
            b.surfaceType=ST_RInt(&w); b.boltUsed=ST_RInt(&w);
            if(b.boneNumber<-1 || b.boneNumber>=bones) b.boneNumber=-1;
            if(b.surfaceNumber<-1 || b.surfaceNumber>=surfaces) b.surfaceNumber=-1;
            b.surfaceType=0; b.boltUsed=Com_Clampi(0,1024,b.boltUsed); m.mBltlist.push_back(b);
        }
        if(m.mNewOrigin<-1 || m.mNewOrigin>=n) { m.mNewOrigin=-1; m.mFlags&=~GHOUL2_NEWORIGIN; }
        m.mSTLockActive=ST_RInt(&w)!=0;
        m.mSTLockParams.weight=Com_Clamp(0,1,ST_RFloat(&w));
        if(m.mSTLockActive) for(int j=0;j<53;++j)
            for(int a=0;a<3;++a) for(int c=0;c<4;++c) m.mSTLockLocal[j].matrix[a][c]=ST_RFloat(&w);
        if(fallback) m.mSTLockActive=false;
        m.mSkelFrameNum=m.mMeshFrameNum=-1;
    }
    for(int i=1;i<count && w.ok;++i) {
        CGhoul2Info &m=(*pose)[i];
        if(m.mModelBoltLink<0) continue;
        int parent=(m.mModelBoltLink>>MODEL_SHIFT)&MODEL_AND;
        int bolt=(m.mModelBoltLink>>BOLT_SHIFT)&BOLT_AND;
        if(parent>=i || bolt>=(int)(*pose)[parent].mBltlist.size()) m.mModelBoltLink=-1;
    }
    if(!w.ok || w.pos!=size || (*pose)[0].mModelindex<0) { G2API_CleanGhoul2Models(&pose); return NULL; }
    return pose;
}
