// Candidate-only real renderer probe. Included after ui_qa.inc in ui_atoms.c.
#include "ghoul2/st_lock_pose.h"
#include "game/st_lock_logic.h"
extern animation_t uiHumanoidAnimations[MAX_TOTALANIMATIONS];
extern float UI_SaberBladeLengthForSaber(const char *saberName,int bladeNum);
static stLockPoseParams_t stLockQA;
static void *stLockQAModel;
static int stLockQACase,stLockQAOtherStyle,stLockQAOtherHand,stLockQATop,stLockQAActor;
static int stLockQAResult,stLockQAAnim;
static float stLockQADistance;
static float stLockQAScale=1;
static float stLockQAResolved[6];
typedef float stLockQAFingers_t[2][6][3][4];
static stLockQAFingers_t stLockQAFingerBase[2],stLockQAFingerPending[2];
static int stLockQAFingerReady[2],stLockQAFingerDeferred[2];
static qboolean ST_LockQAPairCommand(const char *action,itemDef_t *item);

// Independent native bolt evidence: compare actual seed finger/hilt transforms
// against actual posed transforms. No solver matrices are used as the oracle.
static qboolean ST_LockQAReadFingers(void *model,int style,int hand,float uniform,stLockQAFingers_t out) {
    static const char *suffix[6]={"d1_j1","d1_j2","d2_j1","d2_j2","d4_j1","d4_j2"};
    vec3_t zero={0,0,0},scale;int side,f,r,c,k;
    VectorSet(scale,uniform,uniform,uniform);
    for(side=0;side<2;side++) {
        mdxaBone_t hilt;int weapon=style==ST_LOCK_DUAL?(side^hand):0;
        int bolt=trap->G2API_AddBolt(model,weapon+1,"*blade1");
        if(bolt<0||!trap->G2API_GetBoltMatrix(model,weapon+1,bolt,&hilt,zero,zero,uiInfo.uiDC.realTime,NULL,scale))return qfalse;
        for(f=0;f<6;f++) {
            char name[32];mdxaBone_t finger;
            Com_sprintf(name,sizeof(name),"%c_%s",side?'l':'r',suffix[f]);bolt=trap->G2API_AddBolt(model,0,name);
            if(bolt<0||!trap->G2API_GetBoltMatrix(model,0,bolt,&finger,zero,zero,uiInfo.uiDC.realTime,NULL,scale))return qfalse;
            for(r=0;r<3;r++)for(c=0;c<4;c++) {
                float value=0;
                for(k=0;k<3;k++)value+=hilt.matrix[k][r]*(finger.matrix[k][c]-(c==3?hilt.matrix[k][3]:0));
                out[side][f][r][c]=value;
            }
        }
    }
    return qtrue;
}
static void ST_LockQAFingerDifference(const stLockQAFingers_t before,const stLockQAFingers_t after,
    int caseNumber,int actor,int hand,const char *label) {
    int side,f,r,c;
    for(side=0;side<2;side++) {
        float maxPosition=0,maxOrientation=0;
        for(f=0;f<6;f++) {
            float squared=0;
            for(r=0;r<3;r++) {
                float d=before[side][f][r][3]-after[side][f][r][3];squared+=d*d;
                for(c=0;c<3;c++){float delta=fabsf(before[side][f][r][c]-after[side][f][r][c]);if(delta>maxOrientation)maxOrientation=delta;}
            }
            if(sqrtf(squared)>maxPosition)maxPosition=sqrtf(squared);
        }
        trap->Print("FINGER_QA case=%d actor=%d label=%s hand=%d side=%d position=%.8f orientation=%.8f\n",
            caseNumber,actor,label,hand,side,maxPosition,maxOrientation);
    }
}
static void ST_LockQAFingerProbe(void *model,const char *label) {
    stLockQAFingers_t current;int hand=stLockQA.handedness;
    if(!ST_LockQAReadFingers(model,stLockQA.style,hand,stLockQAScale,current)) {
        trap->Print("LOCK_QA_ERROR finger-native-bolt-query\n");return;
    }
    if(!Q_stricmp(label,"baseline")||!Q_stricmp(label,"flipclear")) {
        memcpy(stLockQAFingerBase[hand],current,sizeof(current));stLockQAFingerReady[hand]=1;
        if(stLockQAFingerDeferred[hand]) {
            ST_LockQAFingerDifference(current,stLockQAFingerPending[hand],stLockQACase,stLockQAActor,hand,"flip");
            stLockQAFingerDeferred[hand]=0;
        }
    } else if(stLockQA.mode==ST_LOCK_POSE_UPDATE && stLockQA.weight==1) {
        if(stLockQAFingerReady[hand])ST_LockQAFingerDifference(stLockQAFingerBase[hand],current,stLockQACase,stLockQAActor,hand,label);
        else {
            // After changing hand, compare against the later real ordinary
            // pose at flipclear; neither side is generated from solver math.
            memcpy(stLockQAFingerPending[hand],current,sizeof(current));stLockQAFingerDeferred[hand]=1;
        }
    }
}

static itemDef_t *ST_LockQAItem(void) {
    menuDef_t *menu=Menu_GetFocused();
    itemDef_t *item=menu?Menu_FindItemByName(menu,"st_hand_preview"):NULL;
    if(!item||!item->ghoul2){trap->Print("LOCK_QA_ERROR missing-preview\n");return NULL;}
    return item;
}
static int ST_LockQAAnim(int style,int other,int top,int actor) {
    static const int locks[3][3][2]={
        {{BOTH_LK_S_S_S_L_1,BOTH_LK_S_S_T_L_1},{BOTH_LK_S_DL_S_L_1,BOTH_LK_S_DL_T_L_1},{BOTH_LK_S_ST_S_L_1,BOTH_LK_S_ST_T_L_1}},
        {{BOTH_LK_DL_S_S_L_1,BOTH_LK_DL_S_T_L_1},{BOTH_LK_DL_DL_S_L_1,BOTH_LK_DL_DL_T_L_1},{BOTH_LK_DL_ST_S_L_1,BOTH_LK_DL_ST_T_L_1}},
        {{BOTH_LK_ST_S_S_L_1,BOTH_LK_ST_S_T_L_1},{BOTH_LK_ST_DL_S_L_1,BOTH_LK_ST_DL_T_L_1},{BOTH_LK_ST_ST_S_L_1,BOTH_LK_ST_ST_T_L_1}}
    };
    if(style==0&&other==0)return top?(actor?BOTH_BF1LOCK:BOTH_BF2LOCK):(actor?BOTH_CWCIRCLELOCK:BOTH_CCWCIRCLELOCK);
    if(style==other&&actor) {
        if(style==1)return top?BOTH_LK_DL_DL_T_L_2:BOTH_LK_DL_DL_S_L_2;
        return top?BOTH_LK_ST_ST_T_L_2:BOTH_LK_ST_ST_S_L_2;
    }
    return locks[style][other][top];
}
static qboolean ST_LockQAFreeze(itemDef_t *item) {
    int i;
    const char *bones[3]={"model_root","lower_lumbar","Motion"};
    for(i=0;i<3;i++)if(!trap->G2API_SetBoneAnim(item->ghoul2,0,bones[i],stLockQA.seedFrame,stLockQA.seedFrame+1,
        BONE_ANIM_OVERRIDE_FREEZE|(stLockQA.handedness?BONE_ANIM_MIRROR:0),1,uiInfo.uiDC.realTime,-1,0))return qfalse;
    return qtrue;
}
static void ST_LockQA_f(void) {
    char action[32];itemDef_t *item;int i,count;
    Q_strncpyz(action,UI_Argv(1),sizeof(action));
    item=ST_LockQAItem();if(!item)return;
    if(ST_LockQAPairCommand(action,item))return;
    if(!Q_stricmp(action,"seed")) {
        stLockPoseParams_t clear;
        int style=atoi(UI_Argv(3)),other=atoi(UI_Argv(4)),hand=atoi(UI_Argv(5));
        memset(&clear,0,sizeof(clear));clear.size=sizeof(clear);clear.version=ST_LOCK_POSE_VERSION;clear.mode=ST_LOCK_POSE_CLEAR;
        if(!trap->G2API_STLockPose(item->ghoul2,&clear)){trap->Print("LOCK_QA_ERROR seed-clear-rejected\n");return;}
        stLockQAScale=UI_Argv(10)[0]?atof(UI_Argv(10)):1.0f;
        if(!isfinite(stLockQAScale)||stLockQAScale<=0){trap->Print("LOCK_QA_ERROR invalid-uniform-scale\n");return;}
        VectorSet(item->typeData.model->g2scale,stLockQAScale,stLockQAScale,stLockQAScale);
        stLockQACase=atoi(UI_Argv(2));stLockQAOtherStyle=other;stLockQAOtherHand=atoi(UI_Argv(6));
        stLockQATop=atoi(UI_Argv(7));stLockQAActor=atoi(UI_Argv(8));stLockQADistance=atof(UI_Argv(9));
        if(style<0||style>2||other<0||other>2||hand<0||hand>1||stLockQATop<0||stLockQATop>1||stLockQAActor<0||stLockQAActor>1) {
            trap->Print("LOCK_QA_ERROR bad-seed-args\n");return;
        }
        memset(&stLockQA,0,sizeof(stLockQA));stLockQA.size=sizeof(stLockQA);stLockQA.version=ST_LOCK_POSE_VERSION;
        memset(stLockQAFingerReady,0,sizeof(stLockQAFingerReady));memset(stLockQAFingerDeferred,0,sizeof(stLockQAFingerDeferred));
        stLockQA.mode=ST_LOCK_POSE_CLEAR;stLockQA.style=style;stLockQA.handedness=hand;
        stLockQAAnim=ST_LockQAAnim(style,other,stLockQATop,stLockQAActor);
        if(uiHumanoidAnimations[stLockQAAnim].numFrames<2){trap->Print("LOCK_QA_ERROR missing-lock-animation %d\n",stLockQAAnim);return;}
        stLockQA.seedFrame=uiHumanoidAnimations[stLockQAAnim].firstFrame+(uiHumanoidAnimations[stLockQAAnim].numFrames-1)/2;
        {
            vec3_t a={0,0,0},b={0,0,0},origin={0,0,0},scale;
            a[0]=-stLockQADistance*.5f;b[0]=stLockQADistance*.5f;
            VectorCopy(stLockQAActor?b:a,origin);VectorSet(scale,stLockQAScale,stLockQAScale,stLockQAScale);
            if(!ST_LockContacts(a,b,origin,stLockQAActor?180:0,scale,stLockQA.firstContact,stLockQA.lastContact)) {
                trap->Print("LOCK_QA_ERROR scaled-contact-conversion\n");return;
            }
        }
        {
            int opponent=ST_LockQAAnim(other,style,stLockQATop,1-stLockQAActor);
            stLockQA.opponentGhoul2=item->ghoul2; // raw seed sampling only; both fixtures are Kyle
            stLockQA.opponentSeedFrame=uiHumanoidAnimations[opponent].firstFrame+(uiHumanoidAnimations[opponent].numFrames-1)/2;
            stLockQA.opponentHandedness=stLockQAOtherHand;
            stLockQA.opponentTransform[0][0]=stLockQA.opponentTransform[1][1]=-1;
            stLockQA.opponentTransform[2][2]=1;stLockQA.opponentTransform[0][3]=stLockQADistance/stLockQAScale;
            for(i=0;i<3;i++){stLockQAResolved[i]=stLockQA.firstContact[i];stLockQAResolved[i+3]=stLockQA.lastContact[i];}
            stLockQA.resolvedContactPath=stLockQAResolved;
        }
        for(i=0;i<2;i++) {
            int blade;
            char saber[MAX_QPATH];
            trap->Cvar_VariableStringBuffer(i?"ui_saber2":"ui_saber",saber,sizeof(saber));
            stLockQA.hiltModel[i]=i+1;stLockQA.bladeLength[i]=UI_SaberBladeLengthForSaber(saber,0)/stLockQAScale;
            stLockQA.bladeCount[i]=(i && style!=ST_LOCK_DUAL)?0:(style==ST_LOCK_STAFF?2:1);
            for(blade=0;blade<stLockQA.bladeCount[i];blade++)stLockQA.allBladeLength[i][blade]=UI_SaberBladeLengthForSaber(saber,blade)/stLockQAScale;
        }
        stLockQAModel=item->ghoul2;stLockQAResult=ST_LockQAFreeze(item);
        if(!stLockQAResult)trap->Print("LOCK_QA_ERROR seed-freeze-rejected\n");
        return;
    }
    if(item->ghoul2!=stLockQAModel){trap->Print("LOCK_QA_ERROR model-changed-without-seed\n");return;}
    if(!Q_stricmp(action,"update")) {
        stLockQA.mode=ST_LOCK_POSE_UPDATE;stLockQA.progress=atof(UI_Argv(2));stLockQA.weight=atof(UI_Argv(3));
        stLockQAResult=trap->G2API_STLockPose(item->ghoul2,&stLockQA);return;
    }
    if(!Q_stricmp(action,"clear")) {
        stLockQA.mode=ST_LOCK_POSE_CLEAR;stLockQA.weight=0;
        stLockQAResult=trap->G2API_STLockPose(item->ghoul2,&stLockQA);return;
    }
    if(!Q_stricmp(action,"flip")) {
        // Keep the same real model and existing override; replace its handedness
        // and attachment links before asking the renderer for the new solve.
        stLockQA.handedness=1-stLockQA.handedness;count=stLockQA.style==ST_LOCK_DUAL?2:1;
        for(i=0;i<count;i++) {
            int bolt=trap->G2API_AddBolt(item->ghoul2,0,(i^stLockQA.handedness)?"*l_hand":"*r_hand");
            if(bolt<0||!trap->G2API_AttachG2Model(item->ghoul2,i+1,item->ghoul2,bolt,0)) {
                trap->Print("LOCK_QA_ERROR flip-attachment-rejected\n");return;
            }
        }
        if(!ST_LockQAFreeze(item)){trap->Print("LOCK_QA_ERROR flip-freeze-rejected\n");return;}
        stLockQA.mode=ST_LOCK_POSE_UPDATE;stLockQA.progress=.5f;stLockQA.weight=1;
        stLockQAResult=trap->G2API_STLockPose(item->ghoul2,&stLockQA);return;
    }
    if(!Q_stricmp(action,"probe")) {
        char label[32];vec3_t zero={0,0,0},scale={1,1,1},contact,first,last;
        Q_strncpyz(label,UI_Argv(2),sizeof(label));
        VectorSet(scale,stLockQAScale,stLockQAScale,stLockQAScale);
        for(i=0;i<3;i++){
            first[i]=stLockQAScale*stLockQAResolved[i];last[i]=stLockQAScale*stLockQAResolved[i+3];
            contact[i]=first[i]+(last[i]-first[i])*stLockQA.progress;
        }
        count=stLockQA.style==ST_LOCK_DUAL?2:1;
        for(i=0;i<count;i++) {
            mdxaBone_t m;vec3_t origin,direction,delta,perpendicular;
            float projection,distance;int b,bolt=trap->G2API_AddBolt(item->ghoul2,i+1,"*blade1");
            if(bolt<0||!trap->G2API_GetBoltMatrix(item->ghoul2,i+1,bolt,&m,zero,zero,uiInfo.uiDC.realTime,NULL,scale)) {
                trap->Print("LOCK_QA_ERROR actual-blade-query-failed case=%d hilt=%d\n",stLockQACase,i);continue;
            }
            for(b=0;b<3;b++){origin[b]=m.matrix[b][3];direction[b]=-m.matrix[b][1];}
            VectorSubtract(contact,origin,delta);projection=DotProduct(delta,direction);
            VectorMA(delta,-projection,direction,perpendicular);distance=VectorLength(perpendicular);
            trap->Print("LOCK_QA case=%d label=%s actor=%d style=%d other=%d hand=%d otherhand=%d top=%d dist=%.3f scale=%.3f anim=%d seed=%d mode=%d result=%d progress=%.3f weight=%.3f hilt=%d contacting=%d length=%.6f perp=%.6f t=%.6f contact=%.6f,%.6f,%.6f first=%.6f,%.6f,%.6f last=%.6f,%.6f,%.6f origin=%.6f,%.6f,%.6f direction=%.6f,%.6f,%.6f\n",
                stLockQACase,label,stLockQAActor,stLockQA.style,stLockQAOtherStyle,stLockQA.handedness,stLockQAOtherHand,stLockQATop,stLockQADistance,stLockQAScale,
                stLockQAAnim,stLockQA.seedFrame,stLockQA.mode,stLockQAResult,stLockQA.progress,stLockQA.weight,i,i==0,stLockQA.bladeLength[i]*stLockQAScale,distance,projection,
                contact[0],contact[1],contact[2],first[0],first[1],first[2],last[0],last[1],last[2],origin[0],origin[1],origin[2],direction[0],direction[1],direction[2]);
        }
        ST_LockQAFingerProbe(item->ghoul2,label);
        return;
    }
    trap->Print("LOCK_QA_ERROR unknown-action %s\n",action);
}

// Two separately owned native Ghoul2 instances, never aliases of menu storage.
extern void UI_DoSaber(vec3_t origin,vec3_t dir,float length,float lengthMax,float radius,saber_colors_t color);
extern void UI_ScaleModelAxis(refEntity_t *ent);
extern float UI_SaberBladeRadiusForSaber(const char *saberName,int bladeNum);
typedef struct {
    void *model;
    stLockPoseParams_t pose;
    qhandle_t skin;
    int caseNumber,result;
    float distance,scale,length[2][2],radius[2][2],resolved[6];
    stLockQAFingers_t fingers;
} stLockQAPairActor_t;
static stLockQAPairActor_t stLockQAPair[2];
static int stLockQAPairVisible,stLockQAPairCamera,stLockQAPairDraws;

static void ST_LockQAPairClean(int actor) {
    stLockQAPairActor_t *a=&stLockQAPair[actor];
    if(a->model) {
        stLockPoseParams_t clear=a->pose;clear.mode=ST_LOCK_POSE_CLEAR;clear.weight=0;
        trap->G2API_STLockPose(a->model,&clear);
        trap->G2API_CleanGhoul2Models(&a->model);
    }
    memset(a,0,sizeof(*a));
}
static qboolean ST_LockQAPairMatrix(int actor,int hilt,int blade,mdxaBone_t *m) {
    stLockQAPairActor_t *a=&stLockQAPair[actor];
    vec3_t origin={0,0,0},angles={0,0,0},scale={1,1,1};
    int bolt;
    origin[0]=(actor?.5f:-.5f)*a->distance;angles[YAW]=actor?180:0;
    VectorSet(scale,a->scale,a->scale,a->scale);
    bolt=trap->G2API_AddBolt(a->model,hilt+1,blade?"*blade2":"*blade1");
    return bolt>=0 && trap->G2API_GetBoltMatrix(a->model,hilt+1,bolt,m,angles,origin,uiInfo.uiDC.realTime,NULL,scale);
}
static qboolean ST_LockQAPairCommand(const char *action,itemDef_t *item) {
    int i,h,b;
    if(!Q_stricmp(action,"pairreset")) {
        stLockQAPairVisible=0;ST_LockQAPairClean(0);ST_LockQAPairClean(1);return qtrue;
    }
    if(!Q_stricmp(action,"paircapture")) {
        stLockQAPairActor_t *a;
        stLockPoseParams_t clear;
        int actor=atoi(UI_Argv(2));
        if(actor<0||actor>1||item->ghoul2!=stLockQAModel) {trap->Print("LOCK_QA_ERROR invalid-pair-capture\n");return qtrue;}
        ST_LockQAPairClean(actor);a=&stLockQAPair[actor];
        trap->G2API_DuplicateGhoul2Instance(item->ghoul2,&a->model);
        if(!a->model||a->model==item->ghoul2||a->model==stLockQAPair[1-actor].model) {
            trap->Print("LOCK_QA_ERROR pair-clone-alias-or-missing\n");a->model=NULL;return qtrue;
        }
        // The source remains ordinary and owns no procedural clone state.
        clear=stLockQA;clear.mode=ST_LOCK_POSE_CLEAR;clear.weight=0;
        if(!trap->G2API_STLockPose(item->ghoul2,&clear))trap->Print("LOCK_QA_ERROR pair-source-clear-rejected\n");
        a->pose=stLockQA;memcpy(a->resolved,stLockQAResolved,sizeof(a->resolved));a->pose.resolvedContactPath=a->resolved;a->pose.mode=ST_LOCK_POSE_UPDATE;a->pose.progress=.5f;a->pose.weight=1;
        a->caseNumber=stLockQACase;a->distance=stLockQADistance;a->scale=stLockQAScale;a->skin=item->typeData.model->g2skin;
        for(h=0;h<2;h++)for(b=0;b<2;b++) {
            char saber[MAX_QPATH];trap->Cvar_VariableStringBuffer(h?"ui_saber2":"ui_saber",saber,sizeof(saber));
            a->length[h][b]=UI_SaberBladeLengthForSaber(saber,b);a->radius[h][b]=UI_SaberBladeRadiusForSaber(saber,b);
        }
        a->result=0; // Pair solve occurs only after both real clones exist.
        if(!ST_LockQAReadFingers(a->model,a->pose.style,a->pose.handedness,a->scale,a->fingers))
            trap->Print("LOCK_QA_ERROR pair-finger-baseline-query\n");
        return qtrue;
    }
    if(!Q_stricmp(action,"pairshow")) {
        if(!stLockQAPair[0].model||!stLockQAPair[1].model||stLockQAPair[0].caseNumber!=stLockQAPair[1].caseNumber) {
            trap->Print("LOCK_QA_ERROR incomplete-pair-scene\n");return qtrue;
        }
        for(i=0;i<2;i++) {
            stLockQAPairActor_t *a=&stLockQAPair[i],*other=&stLockQAPair[1-i];
            a->pose.opponentGhoul2=other->model;a->pose.opponentSeedFrame=other->pose.seedFrame;
            a->pose.opponentHandedness=other->pose.handedness;
            a->result=trap->G2API_STLockPose(a->model,&a->pose);
            if(!a->result)trap->Print("LOCK_QA_ERROR pair-clone-pose-rejected actor=%d case=%d\n",i,a->caseNumber);
        }
        stLockQAPairCamera=atoi(UI_Argv(2));stLockQAPairDraws=0;stLockQAPairVisible=1;return qtrue;
    }
    if(!Q_stricmp(action,"paircamera")) {stLockQAPairCamera=atoi(UI_Argv(2));return qtrue;}
    if(!Q_stricmp(action,"pairprobe")) {
        trap->Print("PAIR_QA_STATE case=%d drawn=%d visible=%d camera=%d separate=%d\n",stLockQAPair[0].caseNumber,
            stLockQAPairDraws,stLockQAPairVisible,stLockQAPairCamera,stLockQAPair[0].model!=stLockQAPair[1].model);
        for(i=0;i<2;i++) {
            stLockQAPairActor_t *a=&stLockQAPair[i];
            int hilts=a->pose.style==ST_LOCK_DUAL?2:1,blades=a->pose.style==ST_LOCK_STAFF?2:1;
            for(h=0;h<hilts;h++)for(b=0;b<blades;b++) {
                mdxaBone_t m;vec3_t first,last;int k;
                for(k=0;k<3;k++){first[k]=a->resolved[k]*a->scale;last[k]=a->resolved[k+3]*a->scale;}
                first[0]=(i?-first[0]:first[0])+(i?.5f:-.5f)*a->distance;
                last[0]=(i?-last[0]:last[0])+(i?.5f:-.5f)*a->distance;
                if(i){first[1]=-first[1];last[1]=-last[1];}
                if(!ST_LockQAPairMatrix(i,h,b,&m)){trap->Print("LOCK_QA_ERROR pair-blade-query-failed\n");continue;}
                trap->Print("PAIR_QA case=%d actor=%d style=%d hand=%d hilt=%d blade=%d contacting=%d result=%d progress=%.3f dist=%.3f scale=%.3f length=%.6f first=%.6f,%.6f,%.6f last=%.6f,%.6f,%.6f origin=%.6f,%.6f,%.6f direction=%.6f,%.6f,%.6f\n",
                    a->caseNumber,i,a->pose.style,a->pose.handedness,h,b,h==0&&b==0,a->result,a->pose.progress,a->distance,a->scale,a->length[h][b],first[0],first[1],first[2],last[0],last[1],last[2],
                    m.matrix[0][3],m.matrix[1][3],m.matrix[2][3],-m.matrix[0][1],-m.matrix[1][1],-m.matrix[2][1]);
            }
            {
                stLockQAFingers_t current;
                if(ST_LockQAReadFingers(a->model,a->pose.style,a->pose.handedness,a->scale,current))
                    ST_LockQAFingerDifference(a->fingers,current,a->caseNumber,i,a->pose.handedness,"pair");
                else trap->Print("LOCK_QA_ERROR pair-finger-posed-query\n");
            }
        }
        return qtrue;
    }
    return qfalse;
}

// Preview build calls this after Menu_PaintAll / ST_UIPresentation every frame.
void ST_LockQAPaint(void) {
    static const char *names[3]={"Single","Dual","Staff"};
    refdef_t ref;vec3_t target={0,0,18},delta,angles,light;
    vec4_t background={.018f,.023f,.03f,1},ink={.83f,.91f,1,1};
    char title[192];int i,h,b;
    if(!stLockQAPairVisible||!stLockQAPair[0].model||!stLockQAPair[1].model)return;
    UI_FillRect(0,0,SCREEN_WIDTH,SCREEN_HEIGHT,background);
    memset(&ref,0,sizeof(ref));ref.rdflags=RDF_NOWORLDMODEL;ref.time=uiInfo.uiDC.realTime;
    ref.x=16*uiInfo.uiDC.xscale;ref.y=58*uiInfo.uiDC.yscale;
    ref.width=608*uiInfo.uiDC.xscale;ref.height=384*uiInfo.uiDC.yscale;
    ref.fov_y=42;ref.fov_x=atan(tan(ref.fov_y*M_PI/360)*(float)ref.width/ref.height)*360/M_PI;
    if(stLockQAPairCamera)VectorSet(ref.vieworg,100,-140,68);
    else VectorSet(ref.vieworg,0,-160,38);
    VectorSubtract(target,ref.vieworg,delta);vectoangles(delta,angles);AnglesToAxis(angles,ref.viewaxis);
    trap->R_ClearScene();
    for(i=0;i<2;i++) {
        stLockQAPairActor_t *a=&stLockQAPair[i];refEntity_t ent;
        int hilts=a->pose.style==ST_LOCK_DUAL?2:1,blades=a->pose.style==ST_LOCK_STAFF?2:1;
        memset(&ent,0,sizeof(ent));ent.reType=RT_MODEL;ent.ghoul2=a->model;ent.radius=1000;ent.customSkin=a->skin;
        ent.renderfx=RF_LIGHTING_ORIGIN|RF_NOSHADOW;ent.shaderRGBA[0]=ent.shaderRGBA[1]=ent.shaderRGBA[2]=ent.shaderRGBA[3]=255;
        VectorSet(ent.modelScale,a->scale,a->scale,a->scale);VectorSet(angles,0,i?180:0,0);AnglesToAxis(angles,ent.axis);UI_ScaleModelAxis(&ent);
        VectorSet(ent.origin,(i?.5f:-.5f)*a->distance,0,0);VectorCopy(ent.origin,ent.oldorigin);VectorCopy(ent.origin,ent.lightingOrigin);
        trap->R_AddRefEntityToScene(&ent);
        for(h=0;h<hilts;h++)for(b=0;b<blades;b++) {
            mdxaBone_t m;vec3_t origin,direction;int k;
            if(!ST_LockQAPairMatrix(i,h,b,&m))continue;
            for(k=0;k<3;k++){origin[k]=m.matrix[k][3];direction[k]=-m.matrix[k][1];}
            UI_DoSaber(origin,direction,a->length[h][b],a->length[h][b],a->radius[h][b],
                i?(h?SABER_PURPLE:SABER_RED):(h?SABER_GREEN:SABER_BLUE));
        }
    }
    VectorSet(light,-60,-80,100);trap->R_AddLightToScene(light,320,.9f,.97f,1);
    VectorSet(light,70,70,50);trap->R_AddLightToScene(light,260,.65f,.75f,1);
    trap->R_RenderScene(&ref);++stLockQAPairDraws;
    Com_sprintf(title,sizeof(title),"LOCK PAIR  /  %s %s  vs  %s %s",names[stLockQAPair[0].pose.style],
        stLockQAPair[0].pose.handedness?"Left":"Right",names[stLockQAPair[1].pose.style],stLockQAPair[1].pose.handedness?"Left":"Right");
    uiInfo.uiDC.drawText(20,31,.65f,ink,title,0,0,ITEM_TEXTSTYLE_SHADOWED,1);
    Com_sprintf(title,sizeof(title),"Case %d  |  distance %.0f  |  scale %.2f  |  progress 0.5  |  %s view  |  native menu-only QA",
        stLockQAPair[0].caseNumber,stLockQAPair[0].distance,stLockQAPair[0].scale,stLockQAPairCamera?"oblique":"side");
    uiInfo.uiDC.drawText(20,463,.42f,ink,title,0,0,ITEM_TEXTSTYLE_SHADOWED,1);
}
