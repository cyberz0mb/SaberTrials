/* Ready-pose editor. All draft/preview state is separate from saved equipment. */
#include "game/st_stance_runtime.h"
#include "game/st_stance_assets.h"
#include "ui_st_stance_catalog.h"
static int st_stanceDraft[ST_STANCE_SLOTS];
static int st_hybridLibrary;
static const char* st_stanceReturn="saberMenu";
static const char* st_stancePage="st_stances_main";
static int st_stanceLibrary=-1, st_stanceRevision, st_stanceCycleStart, st_stancePendingReturn;
extern qboolean UI_SaberValidForPlayerInMP(const char* saberName);
static int ST_UIStanceSlot(void) {
    int family=(int)trap->Cvar_VariableValue("ui_stanceFamily");
    int style=(int)trap->Cvar_VariableValue("ui_stanceStyle");
    if(family==1)return 6;
    if(family==2)return 9;
    return style>=0 && style<=5?style:0;
}
static void ST_UIStanceCapability(void) {
    if(st_stanceLibrary<0) {
        int index=UI_ParseAnimationFile("models/players/_humanoid/animation.cfg",NULL,qfalse);
        st_stanceLibrary=index>=0 && ST_StanceLibraryValid(bgAllAnims[index].anims) && ST_StanceAssetsAvailable();
        st_hybridLibrary=st_stanceLibrary && STH_AnimationsValid(bgAllAnims[index].anims);
    }
    trap->Cvar_Set("st_stanceProtocol",st_stanceLibrary?ST_STANCE_VERSION:"0");
    trap->Cvar_Set("st_hybridAssets",st_hybridLibrary?ST_HYBRID_ASSET_VERSION:"0");
}
static void ST_UIStanceLabel(menuDef_t* menu,const char* name,const char* text) {
    itemDef_t* item=Menu_FindItemByName(menu,name);
    if(item) {item->text=text;item->textRect.w=0;}
}
static void ST_UIStanceReturn(void) {
    /* The parent has outOfBoundsClick. Do not deliver this button's release to it. */
    st_stancePendingReturn=1;
}
static qboolean ST_UIStanceScript(const char* name) {
    if(!Q_stricmp(name,"stStanceOpenMain") || !Q_stricmp(name,"stStanceOpenGame")) {
        char saved[64],type[16];
        st_stanceReturn=!Q_stricmp(name,"stStanceOpenGame")?"ingame_saber":"saberMenu";
        st_stancePage=!Q_stricmp(name,"stStanceOpenGame")?"st_stances_game":"st_stances_main";
        st_stancePendingReturn=0;
        trap->Cvar_VariableStringBuffer("saberStances",saved,sizeof(saved));
        ST_StanceParse(saved,st_stanceDraft);
        trap->Cvar_VariableStringBuffer("ui_saber_type",type,sizeof(type));
        trap->Cvar_Set("ui_stanceFamily",!Q_stricmp(type,"dual")?"1":!Q_stricmp(type,"staff")?"2":"0");
        trap->Cvar_Set("ui_stanceStyle",va("%d",ST_UIHybridFirstStyle()-1));
        trap->Cvar_Set("ui_stanceHand",trap->Cvar_VariableValue("saberHand")==1?"1":"0");
        trap->Cvar_Set("ui_stanceMotion","0");trap->Cvar_Set("ui_stanceRotate","0");
        trap->Cvar_Set("ui_stanceExperimental","0");
        st_stanceRevision++;st_stanceCycleStart=uiInfo.uiDC.realTime;
        ST_UIStanceCapability();Menus_ActivateByName(st_stancePage);return qtrue;
    }
    if(!Q_stricmp(name,"stStanceCancel")) {ST_UIStanceReturn();return qtrue;}
    if(!Q_stricmp(name,"stStanceApply")) {
        char saved[ST_STANCE_SLOTS+1];
        if(!st_stanceLibrary) {trap->Cvar_Set("ui_stanceNotice","Matching stance assets are missing. Choices were not saved.");return qtrue;}
        ST_StanceFormat(st_stanceDraft,saved);trap->Cvar_Set("saberStances",saved);
        trap->Cvar_Set("st_uiPresentationNotice","Stances saved. Applies next spawn on a supporting server.");
        ST_UIStanceReturn();return qtrue;
    }
    if(!Q_stricmp(name,"stStanceReset")) {
        int i;for(i=0;i<ST_STANCE_SLOTS;i++)st_stanceDraft[i]=0;
        trap->Cvar_Set("ui_stanceExperimental","0");return qtrue;
    }
    if(!Q_stricmp(name,"stStanceNext") || !Q_stricmp(name,"stStancePrevious")) {
        int slot=ST_UIStanceSlot(),id=st_stanceDraft[slot],n;
        int step=!Q_stricmp(name,"stStancePrevious")?-1:1;
        for(n=0;n<16;n++) {id=(id+step+15)%15;if(ST_StanceAllowed(slot,id))break;}
        st_stanceDraft[slot]=id;trap->Cvar_Set("ui_stanceExperimental","0");return qtrue;
    }
    return qfalse;
}
static void ST_UIStanceRefresh(menuDef_t* menu) {
    static itemDef_t* cached;
    static char previous[512];
    static int previousAnim=-1;
    static int rigValid;
    itemDef_t* item;modelDef_t* def;
    char selection[MAX_QPATH],model[MAX_QPATH],path[MAX_QPATH*2],key[512],*skin;
    char sabers[2][MAX_QPATH],type[MAX_QPATH];
    int family,slot,id,hand,anim,num,i,duration,bolts[2],index;
    ST_UIStanceCapability();
    if(st_stancePendingReturn && !trap->Key_IsDown(A_MOUSE1) && !trap->Key_IsDown(A_MOUSE2)) {
        st_stancePendingReturn=0;
        Menus_CloseByName(st_stancePage);Menus_ActivateByName(st_stanceReturn);cached=NULL;return;
    }
    if(!menu || Q_stricmp(menu->window.name,st_stancePage)){cached=NULL;return;}
    family=(int)trap->Cvar_VariableValue("ui_stanceFamily");if(family<0 || family>2)family=0;
    slot=ST_UIStanceSlot();id=st_stanceDraft[slot];
    if(family==0 && trap->Cvar_VariableValue("ui_stanceExperimental")==1)id=15;
    ST_UIStanceLabel(menu,"st_stance_name",st_stanceNames[id]);
    ST_UIStanceLabel(menu,"st_stance_credit",st_stanceAuthors[id]);
    ST_UIStanceLabel(menu,"st_stance_family_note",family?"Current dual/staff combat; variants are planned.":(slot>=3?"Ready-pose choice only. Choose combat behavior in Combat styles.":"The original style keeps its original combat behavior."));
    ST_UIStanceLabel(menu,"st_stance_note",!st_stanceLibrary?"Assets missing or overridden. Showing Stock; Apply cannot save.":id==15?"Experimental preview only. Apply keeps your regular selection.":"Saved choices take effect next spawn on supporting servers.");
    item=Menu_FindItemByName(menu,"st_stance_preview");if(!item || !item->typeData.model)return;
    def=item->typeData.model;
    hand=trap->Cvar_VariableValue("ui_stanceHand")==1;
    trap->Cvar_VariableStringBuffer("model",selection,sizeof(selection));
    if(!selection[0])Q_strncpyz(selection,"kyle/default",sizeof(selection));
    num=family==1?2:1;
    trap->Cvar_VariableStringBuffer("ui_saber",sabers[0],sizeof(sabers[0]));
    trap->Cvar_VariableStringBuffer("ui_saber2",sabers[1],sizeof(sabers[1]));
    for(i=0;i<num;i++) {
        type[0]=0;UI_SaberTypeForSaber(sabers[i],type);
        if(!UI_SaberValidForPlayerInMP(sabers[i]) ||
           (family==2?Q_stricmp(type,"SABER_STAFF"):Q_stricmp(type,"SABER_SINGLE")))
            Q_strncpyz(sabers[i],family==2?"dual_1":"single_1",sizeof(sabers[i]));
        trap->Cvar_Set(i?"ui_stanceHilt2":"ui_stanceHilt",sabers[i]);
        {
            char ready[MAX_QPATH]={0};
            if(WP_SaberParseParm(sabers[i],"readyAnim",ready) && ready[0])
                ST_UIStanceLabel(menu,"st_stance_family_note","Weapon's own ready pose overrides this preview in play.");
        }
    }
    anim=family==1?BOTH_SABERDUAL_STANCE:family==2?BOTH_SABERSTAFF_STANCE:
         (slot==0 || slot==4)?BOTH_SABERFAST_STANCE:(slot==2 || slot==5)?BOTH_SABERSLOW_STANCE:BOTH_STAND2;
    if(id && st_stanceLibrary)anim=BOTH_ST_READY_01+id-1;
    if(bgAllAnims[0].anims && trap->Cvar_VariableValue("ui_stanceMotion")==1 && id!=15) {
        int attack=family==1?BOTH_A6_T__B_:family==2?BOTH_A7_T__B_:
                   (slot==0 || slot==4)?BOTH_A1_T__B_:(slot==2 || slot==5)?BOTH_A3_T__B_:BOTH_A2_T__B_;
        if(family==0 && slot>=3 && st_hybridLibrary)attack=STH_AnimForStyle(slot+1,attack);
        animation_t* a=&bgAllAnims[0].anims[attack];
        int length=a->numFrames*a->frameLerp;
        int phase=(uiInfo.uiDC.realTime-st_stanceCycleStart)%(2500+(length>0?length:1000));
        if(phase>=2000 && phase<2000+length)anim=attack;
    }
    if(item->window.rect.h>2 && uiInfo.uiDC.yscale>0) {
        float ratio=(item->window.rect.w-2)*uiInfo.uiDC.xscale/((item->window.rect.h-2)*uiInfo.uiDC.yscale);
        def->fov_x=atan(tan(def->fov_y*M_PI/360)*ratio)*360/M_PI;
    }
    def->rotationSpeed=trap->Cvar_VariableValue("ui_stanceRotate")==1?140:0;
    Com_sprintf(key,sizeof(key),"%s|%s|%s|%d|%d|%d",selection,sabers[0],num==2?sabers[1]:"",hand,family,st_stanceRevision);
    if(cached!=item || strcmp(previous,key)) {
        cached=item;Q_strncpyz(previous,key,sizeof(previous));previousAnim=-1;rigValid=0;
        Q_strncpyz(model,selection,sizeof(model));skin=strchr(model,'/');
        if(skin)*skin++=0;else skin="default";
        if(strchr(skin,'|'))Com_sprintf(path,sizeof(path),"models/players/%s/|%s",model,skin);
        else Com_sprintf(path,sizeof(path),"models/players/%s/model_%s.skin",model,skin);
        def->g2skin=trap->R_RegisterSkin(path);def->g2anim=anim;def->angle=180;
        Com_sprintf(path,sizeof(path),"models/players/%s/model.glm",model);
        trap->Cvar_Set("ui_stanceSupported","0");ItemParse_asset_model_go(item,path,&duration);
        if(!item->ghoul2)return;
        path[0]=0;trap->G2API_GetGLAName(item->ghoul2,0,path);
        if(!strstr(path,"players/_humanoid/")) {trap->Cvar_Set("ui_stanceSupported","0");return;}
        for(i=0;i<num;i++) {
            bolts[i]=trap->G2API_AddBolt(item->ghoul2,0,(i^hand)?"*l_hand":"*r_hand");
            if(bolts[i]<0){trap->Cvar_Set("ui_stanceSupported","0");return;}
        }
        for(i=0;i<num;i++) {
            char skinPath[MAX_QPATH];int saber;
            if(!UI_SaberModelForSaber(sabers[i],path))continue;
            saber=trap->G2API_InitGhoul2Model(&item->ghoul2,path,0,0,0,0,0);
            if(saber<1)continue;
            if(UI_SaberSkinForSaber(sabers[i],skinPath))trap->G2API_SetSkin(item->ghoul2,saber,0,trap->R_RegisterSkin(skinPath));
            trap->G2API_AttachG2Model(item->ghoul2,saber,item->ghoul2,bolts[i],0);
        }
        rigValid=1;
    }
    if(!item->ghoul2 || !rigValid || !bgAllAnims[0].anims || previousAnim==anim)return;
    /* Read the model's actual animation set; never apply humanoid frame offsets to another rig. */
    trap->G2API_GetGLAName(item->ghoul2,0,path);
    if(!strstr(path,"players/_humanoid/")) {trap->Cvar_Set("ui_stanceSupported","0");return;}
    index=0;
    if(anim>=BOTH_ST_READY_01 && !ST_StanceLibraryValid(bgAllAnims[index].anims))return;
    {
        animation_t* a=&bgAllAnims[index].anims[anim];
        int flags=BONE_ANIM_OVERRIDE_FREEZE;
        if(a->loopFrames!=-1 && a->numFrames>1)flags|=BONE_ANIM_OVERRIDE_LOOP;
        if(hand)flags|=BONE_ANIM_MIRROR;
        if(trap->G2API_SetBoneAnim(item->ghoul2,0,"model_root",a->firstFrame,a->firstFrame+a->numFrames,
                                 flags,50.0f/a->frameLerp,uiInfo.uiDC.realTime,-1,150)) {
            previousAnim=anim;def->g2anim=anim;trap->Cvar_Set("ui_stanceSupported","1");
        } else trap->Cvar_Set("ui_stanceSupported","0");
    }
}
