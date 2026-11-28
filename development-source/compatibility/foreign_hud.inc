namespace personalHud {
static cvar_t *style,*scale,*panelOpacity,*pulse,*showScore;
static int statusHandle=-1,scoreHandle=-1,gameType,fragLimit,redScore,blueScore;
static qhandle_t stockReticle;
static bool drawing,scoreHeld;
static qhandle_t art(const char *path){
    const char *name=strrchr(path,'/');
    return CL_PersonalArt(name?name+1:path);
}
static void picture(float x,float y,float w,float h,qhandle_t shader){
    re->DrawStretchPic(x,y,w,h,0,0,1,1,shader);
}
static void rectangle(float x,float y,float w,float h,const float *color){
    re->SetColor(color);picture(x,y,w,h,cls.whiteShader);re->SetColor(nullptr);
}
#include "foreign_hud_layout.inc"

static void reset(){
    statusHandle=scoreHandle=-1;scoreHeld=drawing=false;stockReticle=0;
    memset(&st_hudMedia,0,sizeof(st_hudMedia));
    style=Cvar_Get("st_personalHud","0",CVAR_ARCHIVE);
    scale=Cvar_Get("st_hudScale","100",CVAR_ARCHIVE);
    panelOpacity=Cvar_Get("st_hudOpacity","55",CVAR_ARCHIVE);
    pulse=Cvar_Get("st_hudPulse","1",CVAR_ARCHIVE);
    showScore=nullptr;
}
static void remember(vmCvar_t *v,const char *name){
    if(!v)return;
    if(!Q_stricmp(name,"cg_drawStatus"))statusHandle=v->handle;
    if(!Q_stricmp(name,"cg_drawScores")){scoreHandle=v->handle;showScore=Cvar_Get(name,"1",0);}
}
static const char *config(int index){return cl.gameState.stringData+cl.gameState.stringOffsets[index];}
static int teamScore(int index){const char *value=config(index);return *value?atoi(value):SCORE_NOT_PRESENT;}
static void begin(){
    drawing=false;
    if(!style || style->integer!=1 || !cl.snap.valid || cls.state!=CA_ACTIVE || CL_TrialsGame() ||
        statusHandle<0 || scoreHeld || Cvar_VariableIntegerValue("st_photoMode") ||
        !Cvar_VariableIntegerValue("cg_draw2D"))return;
    const playerState_t &ps=cl.snap.ps;
    if(ps.pm_type!=PM_NORMAL || ps.persistant[PERS_TEAM]==TEAM_SPECTATOR || ps.stats[STAT_HEALTH]<=0 ||
        ps.m_iVehicleNum || ps.weapon==WP_EMPLACED_GUN)return;
    const char *info=config(CS_SERVERINFO);
    gameType=atoi(Info_ValueForKey(info,"g_gametype"));
    if(gameType==GT_SIEGE)return; // preserve the mod's class and objective displays
    if(!st_hudMedia.font)ST_HudRegister();
    if(!st_hudMedia.font || !st_hudMedia.frame[ST_HUD_HEALTH])return;
    fragLimit=atoi(Info_ValueForKey(info,"fraglimit"));
    redScore=teamScore(CS_SCORES1);blueScore=teamScore(CS_SCORES2);
    drawing=true;
}
static void mask(vmCvar_t *v){
    if(!drawing || !v || (v->handle!=statusHandle && v->handle!=scoreHandle))return;
    Q_strncpyz(v->string,"0",sizeof(v->string));v->integer=0;v->value=0;v->modificationCount=-1;
}
static qhandle_t shader(const char *name){
    const qhandle_t handle=re->RegisterShaderNoMip(name);
    if(name && !Q_stricmp(name,"gfx/2d/crosshaira"))stockReticle=handle;
    return handle;
}
static void stretch(float x,float y,float w,float h,float s,float t,float u,float v,qhandle_t handle){
    if(drawing && stockReticle && handle==stockReticle && st_hudMedia.reticle && Cvar_VariableIntegerValue("cg_drawCrosshair")==1){
        const float width=w*ST_HudAspect();x+=(w-width)*.5f;w=width;handle=st_hudMedia.reticle;
    }
    re->DrawStretchPic(x,y,w,h,s,t,u,v,handle);
}
static void command(){
    if(!Q_stricmp(Cmd_Argv(0),"+scores"))scoreHeld=true;
    else if(!Q_stricmp(Cmd_Argv(0),"-scores"))scoreHeld=false;
}
}
void CL_DrawForeignHud(){
    using namespace personalHud;
    if(!drawing)return;
    if(Cvar_VariableIntegerValue("cg_drawStatus"))ST_DrawCombatHud();
    if(showScore && showScore->integer){
        // Keep the mod's upper-right leader portrait and notifications clear.
        const int rows=gameType>=GT_TEAM ? 2 : 1;
        const float scale=ST_HudScale();
        const float scoreY=467-(55+33*rows)*scale;
        const float right=640/ST_HudAspect()-5;
        ST_DrawHudScore(scoreY-8,right);
    }
}
