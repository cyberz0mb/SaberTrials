// Included at the end of each renderer's tr_ghoul2.cpp. This is the common
// native pose path used by rendered skin, bolt evaluation and server traces.
#include "../ghoul2/paired_lock_clearance.h"
#include <functional>

// Preview builds may opt into bounded rejection diagnostics. Release builds
// retain the same validation and do not create a cvar or print runtime data.
static bool ST_LockReject(const char*stage,int a=-1,int b=-1) {
#ifdef ST_LOCK_DIAGNOSTICS
    static int remaining=128;
    if(remaining-->0)ri.Printf(PRINT_ALL,"ST_LOCK_REJECT stage=%s a=%d b=%d\n",stage,a,b);
#else
    (void)stage;(void)a;(void)b;
#endif
    return false;
}

struct STLockRuntime {
    stLockPoseParams_t key;
    const model_t* models[4];
    const mdxaHeader_t* headers[4];
    int links[2];
    int parents[53],joint[2][3];
    const mdxaSkel_t* skeleton[53];
    stlock::M seedLocal[53],seedGlobal[53];
    stlock::Actor actor;
    stlock::WeaponTrack track[2];
    stlock::LockGeometry geometry[2];
    stlock::V firstContact,lastContact;
    bool wristFollowers[2][53];
    mdxaBone_t hiltLocal[2][53];
    int hiltBones[2];
};

static stlock::M ST_LockMatrix(const mdxaBone_t&m) {
    stlock::M r;for(int c=0;c<3;c++)r.c[c]=stlock::V(m.matrix[0][c],m.matrix[1][c],m.matrix[2][c]);
    r.p=stlock::V(m.matrix[0][3],m.matrix[1][3],m.matrix[2][3]);return r;
}
static void ST_LockStore(const stlock::M&m,mdxaBone_t&out) {
    for(int c=0;c<3;c++){out.matrix[0][c]=(float)m.c[c].x;out.matrix[1][c]=(float)m.c[c].y;out.matrix[2][c]=(float)m.c[c].z;}
    out.matrix[0][3]=(float)m.p.x;out.matrix[1][3]=(float)m.p.y;out.matrix[2][3]=(float)m.p.z;
}
static stlock::V ST_LockVector(const float*v){return stlock::V(v[0],v[1],v[2]);}
static const mdxaSkel_t* ST_LockSkel(const mdxaHeader_t*h,int bone) {
    const mdxaSkelOffsets_t*off=(const mdxaSkelOffsets_t*)((const byte*)h+sizeof(*h));
    return (const mdxaSkel_t*)((const byte*)off+off->offsets[bone]);
}
static bool ST_LockSample(const mdxaHeader_t*h,int frame,bool mirror,std::vector<stlock::M>&local,std::vector<stlock::M>&global) {
    if(!h||h->numBones<1||h->numBones>53||frame<0||frame>=h->numFrames)return false;
    int map[53];if(mirror&&!ST_MirrorGLAMap(h,map))return false;
    local.resize(h->numBones);global.resize(h->numBones);std::vector<int>done(h->numBones,0);
    for(int i=0;i<h->numBones;i++){mdxaBone_t m;UnCompressBone(m.matrix,mirror?map[i]:i,h,frame);if(mirror)ST_MirrorMatrix(m.matrix,m.matrix);local[i]=ST_LockMatrix(m);}
    std::function<bool(int)> eval=[&](int i){
        if(done[i]==2)return true;if(done[i]==1)return false;done[i]=1;int p=ST_LockSkel(h,i)->parent;
        if(p>=h->numBones||p< -1)return false;
        if(p<0)global[i]=local[i];else{if(!eval(p))return false;global[i]=stlock::mul(global[p],local[i]);}done[i]=2;return true;
    };
    for(int i=0;i<h->numBones;i++)if(!eval(i))return false;return true;
}
static int ST_LockBone(const mdxaHeader_t*h,const char*name){for(int i=0;i<h->numBones;i++)if(!strcmp(ST_LockSkel(h,i)->name,name))return i;return -1;}
static bool ST_LockDescendant(const mdxaHeader_t*h,int bone,int ancestor){for(int n=0;n<h->numBones&&bone>=0;n++,bone=ST_LockSkel(h,bone)->parent)if(bone==ancestor)return true;return false;}
static int ST_LockSurface(const model_t*model,const char*name){
    const mdxmHeader_t*h=model?ST_LOCK_MODEL_HEADER(model):NULL;if(!h)return -1;
    const mdxmHierarchyOffsets_t*ofs=(const mdxmHierarchyOffsets_t*)((const byte*)h+sizeof(*h));
    for(int i=0;i<h->numSurfaces;i++){const mdxmSurfHierarchy_t*s=(const mdxmSurfHierarchy_t*)((const byte*)ofs+ofs->offsets[i]);if(!strcmp(s->name,name))return i;}
    return -1;
}

// Same tag-triangle convention as G2_ProcessSurfaceBolt2. Stock hang-tag bones
// are children of the radius, beside the wrist. Record those tag-weight bones
// so the solver can carry them by the wrist's rigid motion as well. A tag may
// not borrow torso/upper-arm weights or the solved radius itself.
static bool ST_LockTag(const model_t*model,const mdxaHeader_t*header,const char*name,const std::vector<stlock::M>&deform,stlock::M&out,int&surfaceIndex,int wrist=-1,int elbow=-1,bool*siblings=NULL) {
    const mdxmHeader_t*h=model?ST_LOCK_MODEL_HEADER(model):NULL;if(!h)return ST_LockReject("tag-model");
    surfaceIndex=ST_LockSurface(model,name);
    if(surfaceIndex<0)return ST_LockReject("tag-name",wrist);const mdxmSurface_t*s=(const mdxmSurface_t*)G2_FindSurface_BC(model,surfaceIndex,0);
    if(!s||s->numVerts!=3||s->numTriangles!=1)return ST_LockReject("tag-shape",s?s->numVerts:-1,s?s->numTriangles:-1);
    const mdxmVertex_t*verts=(const mdxmVertex_t*)((const byte*)s+s->ofsVerts);const int*refs=(const int*)((const byte*)s+s->ofsBoneReferences);stlock::V p[3];
    for(int j=0;j<3;j++){
        int count=G2_GetVertWeights(&verts[j]);float total=0;
        for(int k=0;k<count;k++){
            int ref=G2_GetVertBoneIndex(&verts[j],k);if(ref<0||ref>=s->numBoneReferences)return ST_LockReject("tag-reference",ref,s->numBoneReferences);int bone=refs[ref];if(bone<0||bone>=(int)deform.size())return ST_LockReject("tag-bone",bone,(int)deform.size());
            float weight=G2_GetVertBoneWeight(&verts[j],k,total,count);
            if(weight>0&&wrist>=0&&!ST_LockDescendant(header,bone,wrist)){
                if(!siblings||elbow<0||bone==elbow||!ST_LockDescendant(header,bone,elbow))return ST_LockReject("tag-wrist",bone,wrist);
                siblings[bone]=true;
            }
            p[j]=p[j]+stlock::point(deform[bone],ST_LockVector(verts[j].vertCoords))*weight;
        }
    }
    stlock::V side0=p[1]-p[0],side2=p[0]-p[2],a0=stlock::unit(side0),a1=stlock::unit(side2);
    a0=stlock::unit(a0-a1*stlock::dot(a0,a1));stlock::V a2=stlock::unit(stlock::cross(side0,side2));
    out.c[0]=a1;out.c[1]=a0;out.c[2]=a2*-1;out.p=p[2];return stlock::rigid(out)?true:ST_LockReject("tag-rigid",surfaceIndex);
}
static bool ST_LockBladeTag(const model_t*model,const mdxaHeader_t*header,int blade,const std::vector<stlock::M>&deform,stlock::M&out){
    char name[32];Com_sprintf(name,sizeof(name),"*blade%d",blade+1);
    // Match the game's existing legacy first-blade attachment convention.
    if(blade==0&&ST_LockSurface(model,name)<0)Q_strncpyz(name,"*flash",sizeof(name));
    int surface;return ST_LockTag(model,header,name,deform,out,surface);
}
static stLockPoseParams_t ST_LockKey(const stLockPoseParams_t&p){stLockPoseParams_t k=p;k.progress=0;k.weight=0;k.mode=ST_LOCK_POSE_UPDATE;k.resolvedContactPath=NULL;return k;}
static bool ST_LockReferences(CGhoul2Info_v&g,const stLockPoseParams_t&p,STLockRuntime&r,bool needOpponent=true) {
    CGhoul2Info&body=g[p.modelIndex];r.models[0]=(const model_t*)body.currentModel;r.headers[0]=body.aHeader;
    int count=p.style==ST_LOCK_DUAL?2:1;
    for(int w=0;w<count;w++){
        int h=p.hiltModel[w];if(h<0||h>=g.size()||h==p.modelIndex||g[h].mModelindex<0)return false;
        if(w&&h==p.hiltModel[0])return false;r.models[w+1]=(const model_t*)g[h].currentModel;r.headers[w+1]=g[h].aHeader;r.links[w]=g[h].mModelBoltLink;
    }
    if(needOpponent){
        if(!p.opponentGhoul2)return false;CGhoul2Info_v&opponent=*(CGhoul2Info_v*)p.opponentGhoul2;
        if(p.opponentModelIndex<0||p.opponentModelIndex>=opponent.size()||!G2_SetupModelPointers(opponent)||opponent[p.opponentModelIndex].mModelindex<0)return false;
        r.models[3]=(const model_t*)opponent[p.opponentModelIndex].currentModel;r.headers[3]=opponent[p.opponentModelIndex].aHeader;
    }
    return true;
}
static bool ST_LockSameReferences(const STLockRuntime&track,const STLockRuntime&refs,int count,bool needOpponent){
    for(int i=0;i<count+1;i++)if(refs.models[i]!=track.models[i]||refs.headers[i]!=track.headers[i])return false;
    for(int i=0;i<count;i++)if(refs.links[i]!=track.links[i])return false;
    return !needOpponent||(refs.models[3]==track.models[3]&&refs.headers[3]==track.headers[3]);
}
static bool ST_LockAppendBodyCaps(const mdxaHeader_t*h,const std::vector<stlock::M>&global,const stlock::M&toActor,std::vector<stlock::Capsule>&caps){
    const char*names[4]={"pelvis","thoracic","cervical","cranium"};stlock::V points[4];
    double scale=stlock::length(toActor.c[0]);if(!std::isfinite(scale)||scale<=0)return false;
    for(int i=0;i<4;i++){int bone=ST_LockBone(h,names[i]);if(bone<0)return false;points[i]=stlock::mul(toActor,stlock::mul(global[bone],ST_LockMatrix(ST_LockSkel(h,bone)->BasePoseMat))).p;}
    stlock::V head=points[3]+stlock::unit(points[3]-points[2])*(3.*scale);
    caps.push_back(stlock::Capsule(points[0],points[1],7.*scale));caps.push_back(stlock::Capsule(points[1],points[2],5.*scale));caps.push_back(stlock::Capsule(head,head,5.5*scale));return true;
}
static bool ST_LockBuild(CGhoul2Info_v&g,const stLockPoseParams_t&p,STLockRuntime&r) {
    r.key=ST_LockKey(p);if(!ST_LockReferences(g,p,r))return ST_LockReject("build-references");
    const mdxaHeader_t*h=r.headers[0];int map[53];if(!ST_MirrorGLAMap(h,map))return ST_LockReject("build-rig",h?h->numBones:-1);
    std::vector<stlock::M>local,global;if(!ST_LockSample(h,p.seedFrame,p.handedness!=0,local,global))return ST_LockReject("build-sample",p.seedFrame,h->numFrames);
    stlock::M world=ST_LockMatrix(identityMatrix);
    for(int i=0;i<53;i++){r.seedLocal[i]=local[i];r.seedGlobal[i]=global[i];r.skeleton[i]=ST_LockSkel(h,i);r.parents[i]=r.skeleton[i]->parent;}
    const char*names[2][3]={{"rhumerus","rradius","rhand"},{"lhumerus","lradius","lhand"}};
    for(int a=0;a<2;a++){
        stlock::M m[3];for(int j=0;j<3;j++){int b=ST_LockBone(h,names[a][j]);if(b<0)return ST_LockReject("build-joint",a,j);r.joint[a][j]=b;m[j]=stlock::orthonormal(stlock::mul(world,stlock::mul(global[b],ST_LockMatrix(r.skeleton[b]->BasePoseMat))));if(!stlock::rigid(m[j]))return ST_LockReject("build-joint-rigid",a,j);}
        r.actor.arms[a].shoulder=m[0];r.actor.arms[a].elbow=m[1];r.actor.arms[a].wrist=m[2];r.actor.arms[a].pole=m[1].p-m[0].p;
    }
    stlock::M opponentTransform;for(int c=0;c<3;c++)opponentTransform.c[c]=stlock::V(p.opponentTransform[0][c],p.opponentTransform[1][c],p.opponentTransform[2][c]);opponentTransform.p=stlock::V(p.opponentTransform[0][3],p.opponentTransform[1][3],p.opponentTransform[2][3]);
    double opponentScale=stlock::length(opponentTransform.c[0]);stlock::M opponentRotation=opponentTransform;
    if(!std::isfinite(opponentScale)||opponentScale<=0)return ST_LockReject("opponent-scale");
    for(int c=0;c<3;c++)opponentRotation.c[c]=opponentRotation.c[c]/opponentScale;
    if(!stlock::rigid(opponentRotation,1e-4)||stlock::length(opponentRotation.c[2]-stlock::V(0,0,1))>1e-4)return ST_LockReject("opponent-transform");
    std::vector<stlock::M>opponentLocal,opponentGlobal;
    if(!ST_LockSample(r.headers[3],p.opponentSeedFrame,p.opponentHandedness!=0,opponentLocal,opponentGlobal))return ST_LockReject("opponent-seed",p.opponentSeedFrame);
    std::vector<stlock::Capsule>caps;
    if(!ST_LockAppendBodyCaps(h,global,world,caps)||!ST_LockAppendBodyCaps(r.headers[3],opponentGlobal,stlock::mul(opponentTransform,world),caps))return ST_LockReject("body-capsules");
    r.firstContact=ST_LockVector(p.firstContact);r.lastContact=ST_LockVector(p.lastContact);
    double lift=stlock::resolveContactLift(r.firstContact,r.lastContact,caps);r.firstContact.z+=lift;r.lastContact.z+=lift;
    r.actor.count=p.style==ST_LOCK_DUAL?2:1;
    memset(r.wristFollowers,0,sizeof(r.wristFollowers));
    for(int w=0;w<r.actor.count;w++){
        int hand=w^p.handedness;stlock::Weapon&weapon=r.actor.weapons[w];stlock::M tag;int surface=-1;
        if(!ST_LockTag(r.models[0],h,hand?"*l_hand":"*r_hand",global,tag,surface,r.joint[hand][2],r.joint[hand][1],r.wristFollowers[w]))return ST_LockReject("build-hand-tag",w,hand);
        int link=r.links[w],bolt=(link>>BOLT_SHIFT)&BOLT_AND;
        if(link<0||((link>>MODEL_SHIFT)&MODEL_AND)!=p.modelIndex||bolt>=(int)g[p.modelIndex].mBltlist.size()||g[p.modelIndex].mBltlist[bolt].surfaceNumber!=surface)return ST_LockReject("build-link",link,surface);
        weapon.seedHilt=stlock::mul(world,tag);weapon.count=p.style==ST_LOCK_DUAL?1:2;
        for(int a=0;a<weapon.count;a++){
            int arm=a?1-hand:hand;weapon.grips[a].arm=arm;weapon.grips[a].hiltToWrist=stlock::mul(stlock::inverse(weapon.seedHilt),r.actor.arms[arm].wrist);
            // Humanoid finger joints are radius children beside the wrist,
            // not wrist descendants. Preserve the seed grip under the same
            // rigid wrist motion, including the support hand on a staff.
            const char*digits[6]={"d1_j1","d1_j2","d2_j1","d2_j2","d4_j1","d4_j2"};
            for(int digit=0;digit<6;digit++){
                char name[32];Com_sprintf(name,sizeof(name),"%c_%s",arm?'l':'r',digits[digit]);int bone=ST_LockBone(h,name);
                if(bone<0||!ST_LockDescendant(h,bone,r.joint[arm][1]))return ST_LockReject("build-finger",arm,digit);
                r.wristFollowers[w][bone]=true;
            }
        }
        std::vector<stlock::M>wl,wg;if(!ST_LockSample(r.headers[w+1],p.hiltSeedFrame[w],false,wl,wg))return ST_LockReject("build-hilt-sample",p.hiltSeedFrame[w],r.headers[w+1]?r.headers[w+1]->numFrames:-1);r.hiltBones[w]=(int)wl.size();
        for(size_t b=0;b<wl.size();b++)ST_LockStore(wl[b],r.hiltLocal[w][b]);
        stlock::M emitter;
        if(!ST_LockBladeTag(r.models[w+1],r.headers[w+1],p.bladeIndex[w],wg,emitter))return ST_LockReject("build-blade-tag",w,p.bladeIndex[w]);
        // G2API_GetBoltMatrix applies its historical XY basis correction. Its
        // NEGATIVE_Y blade direction is the uncorrected tag's negative X.
        weapon.blade.origin=emitter.p;weapon.blade.direction=emitter.c[0]*-1;weapon.blade.length=p.bladeLength[w];weapon.blade.margin=std::min(1.,weapon.blade.length*.1);
        stlock::LockGeometry&geometry=r.geometry[w];geometry.bodies=caps;geometry.hand=p.handedness;
        geometry.role=stlock::dot(r.lastContact-r.firstContact,geometry.forward)>0?0:1;
        for(int b=0;b<p.bladeCount[w];b++)if(p.allBladeLength[w][b]>0){
            stlock::M bladeTag;
            if(!ST_LockBladeTag(r.models[w+1],r.headers[w+1],b,wg,bladeTag))return ST_LockReject("clearance-blade-tag",w,b);
            stlock::Blade full;full.origin=bladeTag.p;full.direction=bladeTag.c[0]*-1;full.length=p.allBladeLength[w][b];geometry.blades.push_back(full);
        }
        stlock::Config cfg;stlock::Status solved=w?stlock::solveClearGuardTrack(r.actor,weapon,(r.firstContact+r.lastContact)*.5,cfg,geometry,r.actor.weapons[0],r.track[0],r.track[w]):stlock::solveClearLockTrack(r.actor,weapon,r.firstContact,r.lastContact,cfg,geometry,r.track[w]);if(solved!=stlock::Ok)return ST_LockReject("build-solve",w,(int)solved);
    }
    return true;
}
static bool ST_LockPose(const STLockRuntime&r,float progress,mdxaBone_t output[53]) {
    stlock::M targets[53],posed[53];bool changed[53]={false};int done[53]={0};stlock::M raw=stlock::inverse(ST_LockMatrix(identityMatrix));
    for(int w=0;w<r.actor.count;w++){
        const stlock::WeaponTrack&t=r.track[w];const stlock::Weapon&weapon=r.actor.weapons[w];stlock::M h=t.firstHilt;h.p=t.firstHilt.p+(t.lastHilt.p-t.firstHilt.p)*progress;
        stlock::M tagDelta=stlock::mul(stlock::mul(stlock::mul(raw,h),stlock::inverse(weapon.seedHilt)),ST_LockMatrix(identityMatrix));
        for(int bone=0;bone<53;bone++)if(r.wristFollowers[w][bone]){targets[bone]=stlock::mul(tagDelta,r.seedGlobal[bone]);changed[bone]=true;}
        for(int a=0;a<weapon.count;a++){
            int arm=weapon.grips[a].arm;stlock::ArmPose pose;if(stlock::twoBone(r.actor.arms[arm],stlock::mul(h,weapon.grips[a].hiltToWrist),pose)!=stlock::Ok)return false;
            stlock::M m[3]={pose.shoulder,pose.elbow,pose.wrist};
            for(int j=0;j<3;j++){int bone=r.joint[arm][j];targets[bone]=stlock::mul(stlock::mul(raw,m[j]),ST_LockMatrix(r.skeleton[bone]->BasePoseMatInv));changed[bone]=true;}
        }
    }
    std::function<bool(int)> eval=[&](int i){
        if(done[i]==2)return true;if(done[i]==1)return false;done[i]=1;int parent=r.parents[i];if(parent>=0&&!eval(parent))return false;
        if(changed[i]){posed[i]=targets[i];if(parent>=0){stlock::M inv;if(!stlock::affineInverse(posed[parent],inv))return false;ST_LockStore(stlock::mul(inv,posed[i]),output[i]);}else ST_LockStore(posed[i],output[i]);}
        else{ST_LockStore(r.seedLocal[i],output[i]);posed[i]=parent>=0?stlock::mul(posed[parent],r.seedLocal[i]):r.seedLocal[i];}done[i]=2;return true;
    };
    for(int i=0;i<53;i++)if(!eval(i))return false;return true;
}
static void ST_LockInvalidate(CGhoul2Info_v&g){for(int i=0;i<g.size();i++){g[i].mSkelFrameNum=-1;g[i].mMeshFrameNum=-1;}}
qboolean G2API_STLockPose(CGhoul2Info_v&g,const stLockPoseParams_t*p) {
    if(!p||p->size!=sizeof(*p)||p->version!=ST_LOCK_POSE_VERSION||p->modelIndex<0||p->modelIndex>=g.size()){ST_LockReject("api-contract",p?p->size:-1,p?p->version:-1);return qfalse;}
    CGhoul2Info&body=g[p->modelIndex];
    if(p->mode==ST_LOCK_POSE_CLEAR||((p->mode==ST_LOCK_POSE_UPDATE||p->mode==ST_LOCK_POSE_CACHED)&&p->weight==0)){
        bool changed=false;for(int i=0;i<g.size();i++)if(g[i].mSTLockOwner==p->modelIndex){g[i].mSTLockActive=false;g[i].mSTLockOwner=-1;changed=true;}
        if(changed)ST_LockInvalidate(g);return qtrue;
    }
    if((p->mode!=ST_LOCK_POSE_UPDATE&&p->mode!=ST_LOCK_POSE_VALIDATE&&p->mode!=ST_LOCK_POSE_CACHED)||p->handedness<0||p->handedness>1||p->opponentHandedness<0||p->opponentHandedness>1||p->style<0||p->style>2||!std::isfinite(p->progress)||p->progress<0||p->progress>1||!std::isfinite(p->weight)||p->weight<0||p->weight>1){ST_LockReject("api-parameters",p->style,p->handedness);return qfalse;}
    if(!G2_SetupModelPointers(g)||body.mModelindex<0){ST_LockReject("api-model",body.mModelindex);return qfalse;}
    int count=p->style==ST_LOCK_DUAL?2:1;for(int w=0;w<count;w++)if(p->bladeIndex[w]<0||p->bladeIndex[w]>=8||!std::isfinite(p->bladeLength[w])||p->bladeLength[w]<=0){ST_LockReject("api-blade",w,p->bladeIndex[w]);return qfalse;}
    for(int w=0;w<count;w++){
        if(p->bladeCount[w]<1||p->bladeCount[w]>8||p->bladeIndex[w]>=p->bladeCount[w]||p->allBladeLength[w][p->bladeIndex[w]]<=0){ST_LockReject("api-blade-count",w,p->bladeCount[w]);return qfalse;}
        for(int b=0;b<p->bladeCount[w];b++)if(!std::isfinite(p->allBladeLength[w][b])||p->allBladeLength[w][b]<0){ST_LockReject("api-all-blade-length",w,b);return qfalse;}
        if(p->bladeLength[w]!=p->allBladeLength[w][p->bladeIndex[w]]){ST_LockReject("api-selected-blade-length",w,p->bladeIndex[w]);return qfalse;}
    }
    if(!body.mBoneCache)body.mBoneCache=new CBoneCache((const model_t*)body.currentModel,body.aHeader);
    CBoneCache&cache=*body.mBoneCache;stLockPoseParams_t key=ST_LockKey(*p);STLockRuntime refs={};bool cached=p->mode==ST_LOCK_POSE_CACHED||(p->mode==ST_LOCK_POSE_UPDATE&&p->weight<1);
    // Release consumes only our solved value-owned track. The opponent may
    // already have despawned, so do not dereference its cached native pointer.
    if(!ST_LockReferences(g,*p,refs,!cached)){ST_LockReject("api-references",p->hiltModel[0],p->hiltModel[1]);return qfalse;}
    bool rebuild=!cache.stLockRuntime||!ST_LockPoseSameTrack(&cache.stLockRuntime->key,&key)||!ST_LockSameReferences(*cache.stLockRuntime,refs,count,!cached);
    if(cached&&rebuild){ST_LockReject("cached-track-missing");return qfalse;}
    std::shared_ptr<STLockRuntime>selected=cache.stLockRuntime;
    if(rebuild){
        if(cache.stLockValidatedRuntime&&ST_LockPoseSameTrack(&cache.stLockValidatedRuntime->key,&key)&&ST_LockSameReferences(*cache.stLockValidatedRuntime,refs,count,true))selected=cache.stLockValidatedRuntime;
        else{std::shared_ptr<STLockRuntime>fresh(new STLockRuntime());if(!ST_LockBuild(g,*p,*fresh))return qfalse;selected=fresh;}
    }
    mdxaBone_t local[53];if(!ST_LockPose(*selected,p->progress,local)){ST_LockReject("api-pose");return qfalse;}
    if(p->resolvedContactPath){const stlock::V&first=selected->firstContact;const stlock::V&last=selected->lastContact;p->resolvedContactPath[0]=(float)first.x;p->resolvedContactPath[1]=(float)first.y;p->resolvedContactPath[2]=(float)first.z;p->resolvedContactPath[3]=(float)last.x;p->resolvedContactPath[4]=(float)last.y;p->resolvedContactPath[5]=(float)last.z;}
    // Exact same attachment and continuous-track feasibility checks as UPDATE,
    // but no visible pose or ownership change. Callers may preflight all lock
    // seeds for a new rig/hilt selection before committing that equipment.
    if(p->mode==ST_LOCK_POSE_VALIDATE){cache.stLockValidatedRuntime=selected;return qtrue;}
    // Publish only after the full local pose sample succeeds. A failed solve or
    // sample must preserve both the accepted matrices and its release track.
    cache.stLockRuntime=selected;cache.stLockValidatedRuntime.reset();
    // Clear previous owned attachments only after the replacement solve passed.
    // This also handles dual-to-single changes and a replaced character slot.
    for(int i=0;i<g.size();i++)if(g[i].mSTLockOwner==p->modelIndex){g[i].mSTLockActive=false;g[i].mSTLockOwner=-1;}
    memcpy(body.mSTLockLocal,local,sizeof(local));body.mSTLockParams=*p;body.mSTLockParams.resolvedContactPath=NULL;body.mSTLockActive=true;body.mSTLockOwner=p->modelIndex;
    for(int w=0;w<count;w++){CGhoul2Info&hilt=g[p->hiltModel[w]];memcpy(hilt.mSTLockLocal,cache.stLockRuntime->hiltLocal[w],cache.stLockRuntime->hiltBones[w]*sizeof(mdxaBone_t));hilt.mSTLockParams=*p;hilt.mSTLockParams.resolvedContactPath=NULL;hilt.mSTLockActive=true;hilt.mSTLockOwner=p->modelIndex;}
    ST_LockInvalidate(g);return qtrue;
}

// Called by the wrapper around G2_TransformBone. At weight one no original
// root/lumbar/Motion animation or angle override is consulted. During release
// the ordinary target pose is evaluated and blended through this same path.
static void ST_LockApplyFinal(int child,CBoneCache&cache) {
    if(!cache.stLockLocal||cache.stLockWeight<=0)return;mdxaBone_t locked;int parent=cache.mFinalBones[child].parent;
    const mdxaBone_t&base=parent>=0?cache.mFinalBones[parent].boneMatrix:cache.rootMatrix;
    ST_LockStore(stlock::mul(ST_LockMatrix(base),ST_LockMatrix(cache.stLockLocal[child])),locked);
    if(cache.stLockWeight>=1){cache.mFinalBones[child].boneMatrix=locked;return;}
    float t=cache.stLockWeight;mdxaBone_t&normal=cache.mFinalBones[child].boneMatrix;
    stlock::M m=stlock::interpolateRigid(ST_LockMatrix(normal),ST_LockMatrix(locked),t);
    if(stlock::rigid(m))ST_LockStore(m,normal);
}
