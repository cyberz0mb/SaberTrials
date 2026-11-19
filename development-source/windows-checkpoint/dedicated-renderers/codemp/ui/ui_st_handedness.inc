// Isolated handedness preview; the saved character and hilt selections are read only.
extern qboolean UI_SaberModelForSaber(const char*,char*);
extern qboolean UI_SaberSkinForSaber(const char*,char*);
static void ST_UIHandPreview(menuDef_t* menu) {
    static itemDef_t* cached;
    static char previous[512];
    itemDef_t* item;modelDef_t* def;
    char selection[MAX_QPATH],model[MAX_QPATH],path[MAX_QPATH*2],key[512],type[16];
    char sabers[2][MAX_QPATH],*skin;
    int hand,style,num,i,duration,anim,bolts[2];
    if(!menu || Q_stricmp(menu->window.name,"st_handedness")){cached=NULL;return;}
    item=Menu_FindItemByName(menu,"st_hand_preview");
    if(!item || !item->typeData.model)return;
    def=item->typeData.model;
    hand=trap->Cvar_VariableValue("ui_saberHand")==1;
    trap->Cvar_VariableStringBuffer("model",selection,sizeof(selection));
    if(!selection[0])Q_strncpyz(selection,"kyle/default",sizeof(selection));
    trap->Cvar_VariableStringBuffer("ui_saber_type",type,sizeof(type));
    style=!Q_stricmp(type,"dual")?2:!Q_stricmp(type,"staff")?3:1;
    num=style==2?2:1;
    trap->Cvar_VariableStringBuffer("ui_saber",sabers[0],sizeof(sabers[0]));
    trap->Cvar_VariableStringBuffer("ui_saber2",sabers[1],sizeof(sabers[1]));
    anim=style==2?BOTH_SABERDUAL_STANCE:style==3?BOTH_SABERSTAFF_STANCE:BOTH_STAND2;
    if(trap->Cvar_VariableValue("ui_handAttack"))anim=style==2?BOTH_A6_T__B_:style==3?BOTH_A7_T__B_:BOTH_A1_T__B_;
    Com_sprintf(key,sizeof(key),"%s|%s|%s|%d|%d|%d",selection,sabers[0],sabers[1],hand,style,anim);
    if(item->window.rect.h>2 && uiInfo.uiDC.yscale>0){
        float ratio=(item->window.rect.w-2)*uiInfo.uiDC.xscale/((item->window.rect.h-2)*uiInfo.uiDC.yscale);
        def->fov_x=atan(tan(def->fov_y*M_PI/360)*ratio)*360/M_PI;
    }
    // Retry a failed load only after selection changes or the page is reopened.
    if(cached==item && !strcmp(previous,key))return;
    cached=item;Q_strncpyz(previous,key,sizeof(previous));
    Q_strncpyz(model,selection,sizeof(model));skin=strchr(model,'/');
    if(skin)*skin++=0;else skin="default";
    if(strchr(skin,'|'))Com_sprintf(path,sizeof(path),"models/players/%s/|%s",model,skin);
    else Com_sprintf(path,sizeof(path),"models/players/%s/model_%s.skin",model,skin);
    def->g2skin=trap->R_RegisterSkin(path);def->g2anim=anim;
    def->rotationSpeed=0;def->angle=180;
    Com_sprintf(path,sizeof(path),"models/players/%s/model.glm",model);
    trap->Cvar_Set("ui_handSupported","0");
    ItemParse_asset_model_go(item,path,&duration);
    if(!item->ghoul2)return;
    if(trap->Cvar_VariableValue("ui_handSupported")!=1)return;
    // Validate the complete requested grip before creating any weapon models.
    // A valid humanoid GLA alone does not guarantee this GLM has hand tags.
    for(i=0;i<num;i++){
        bolts[i]=trap->G2API_AddBolt(item->ghoul2,0,(i^hand)?"*l_hand":"*r_hand");
        if(bolts[i]<0){trap->Cvar_Set("ui_handSupported","0");return;}
    }
    for(i=0;i<num;i++){
        char skinPath[MAX_QPATH];int saber;
        if(!UI_SaberModelForSaber(sabers[i],path))continue;
        saber=trap->G2API_InitGhoul2Model(&item->ghoul2,path,0,0,0,0,0);
        if(saber<1)continue;
        if(UI_SaberSkinForSaber(sabers[i],skinPath))trap->G2API_SetSkin(item->ghoul2,saber,0,trap->R_RegisterSkin(skinPath));
        trap->G2API_AttachG2Model(item->ghoul2,saber,item->ghoul2,bolts[i],0);
    }
}
