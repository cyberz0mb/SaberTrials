// Personal camera presentation for client game modules that supply their own view.
#include "../ui/st_setup_catalog.h"
#include <map>
#include <cmath>

namespace personalCamera {
static std::map<int,const char *> settings;
static int hudHandle=-1,modeHandle=-1,editorFrame=-10,captureFrames,cleanUntil;
static bool orbitReady;
static float yaw,pitch,distance;
static cvar_t *mode,*preview;
static const int restricted=CVAR_ROM|CVAR_CHEAT|CVAR_SYSTEMINFO|CVAR_SERVER_CREATED|CVAR_PROTECTED|CVAR_INIT|CVAR_INTERNAL;
static bool spectator(){
    if(!cl.snap.valid)return false;
    return cl.snap.ps.persistant[PERS_TEAM]==TEAM_SPECTATOR || (cl.snap.ps.pm_flags&PMF_FOLLOW);
}
static bool nativeCamera(){
    return CL_TrialsGame() && (clc.demoplaying || spectator() || Cvar_VariableIntegerValue("st_photoSolo"));
}
static bool attached(){return mode && mode->integer && cls.state==CA_ACTIVE && CL_TrialsGame() && !nativeCamera();}
static bool canOrbit(){
    return cl.snap.valid && cl.snap.ps.pm_type==PM_NORMAL && !spectator() &&
        !cl.snap.ps.m_iVehicleNum && cl.snap.ps.weapon!=WP_EMPLACED_GUN &&
        !(Cvar_Flags("cg_thirdPerson")&restricted);
}
static bool orbit(){return orbitReady && attached() && canOrbit();}
static bool editing(){return cls.state==CA_ACTIVE && CL_TrialsGame() && (Key_GetCatcher()&KEYCATCH_UI) && editorFrame>=cls.framecount-1;}
static void reset(){
    settings.clear(); hudHandle=modeHandle=-1; editorFrame=-10; captureFrames=cleanUntil=0;
    orbitReady=false;
    mode=Cvar_Get("st_photoMode","0",0);
    preview=Cvar_Get("st_setupCameraPreview","",CVAR_ROM|CVAR_TEMP|CVAR_INTERNAL);
}
static void remember(vmCvar_t *v,const char *name){
    if(!v)return;
    if(!Q_stricmp(name,"cg_draw2D"))hudHandle=v->handle;
    if(!Q_stricmp(name,"st_photoMode"))modeHandle=v->handle;
    for(const auto &s:ssSettings)if(s.tab==6 && !Q_stricmp(name,s.name)){
        settings[v->handle]=s.name;break;
    }
}
static void apply(vmCvar_t *v){
    if(!v)return;
    const char *value=nullptr;
    if((v->handle==hudHandle || v->handle==modeHandle) && attached())value="0";
    else if(orbit()){
        const auto it=settings.find(v->handle);
        if(it!=settings.end() && !(Cvar_Flags(it->second)&restricted)){
            const char *name=it->second;
            if(!Q_stricmp(name,"cg_thirdPerson"))value="1";
            else if(!Q_stricmp(name,"cg_thirdPersonAngle"))value=va("%f",yaw);
            else if(!Q_stricmp(name,"cg_thirdPersonPitchOffset"))value=va("%f",pitch);
            else if(!Q_stricmp(name,"cg_thirdPersonRange"))value=va("%f",distance);
        }
    }
    else if(preview && preview->string[0] && (Key_GetCatcher()&KEYCATCH_UI)){
        auto it=settings.find(v->handle);
        if(it!=settings.end() && !(Cvar_Flags(it->second)&restricted))
            value=Info_ValueForKey(preview->string,it->second);
    }
    if(value && *value){
        Q_strncpyz(v->string,value,sizeof(v->string));v->value=atof(value);v->integer=atoi(value);
        // Ask Cvar_Update to restore the real value on the next unmasked frame.
        v->modificationCount=-1;
    }
}
static void nativeRegister(vmCvar_t *v,const char *name,const char *initial,uint32_t flags){
    Cvar_Register(v,name,initial,flags);remember(v,name);
}
static void nativeUpdate(vmCvar_t *v){
    Cvar_Update(v);
    if(attached())apply(v);
}
static void begin(){
    if(!attached() || !canOrbit()){orbitReady=false;return;}
    if(!orbitReady){
        yaw=AngleNormalize180(Cvar_VariableValue("cg_thirdPersonAngle"));
        pitch=Com_Clamp(-75,75,Cvar_VariableValue("cg_thirdPersonPitchOffset"));
        distance=Com_Clamp(32,240,Cvar_VariableValue("cg_thirdPersonRange"));
        orbitReady=true;
    }
}
static float setting(const char *saved,const char *draft,const char *fallback,float low,float high){
    const float applied=Com_Clamp(low,high,Cvar_Get(saved,fallback,CVAR_ARCHIVE)->value);
    if(!editing())return applied;
    const char *text=Cvar_VariableString(draft);
    char *end;const double v=strtod(text,&end);
    return end!=text && !*end && std::isfinite(v) && v>=low && v<=high ? (float)v : applied;
}
static void render(const refdef_t *scene){
    if((!attached() && !editing()) || (scene->rdflags&(RDF_NOWORLDMODEL|RDF_AUTOMAP)) ||
        scene->width<=0 || scene->height<=0){re->RenderScene(scene);return;}
    refdef_t view=*scene;
    // Use the delivered camera origin and visibility set, including follow views.
    vectoangles(scene->viewaxis[0],view.viewangles);
    view.viewangles[ROLL]=setting("st_photoRoll","st_uiPhotoRoll","0",-45,45);
    AnglesToAxis(view.viewangles,view.viewaxis);
    if(!(Cvar_Flags("cg_fov")&restricted)){
        const float aspect=(float)view.width/view.height;
        float tangent=tanf(setting("st_photoFov","st_uiPhotoFov","90",20,120)*M_PI/360.f);
        if(Cvar_VariableIntegerValue("cg_fovAspectAdjust"))tangent*=.75f*aspect;
        view.fov_x=atanf(tangent)*360.f/M_PI;
        view.fov_y=atanf(tangent/aspect)*360.f/M_PI;
    }
    re->RenderScene(&view);
}
static void capture(){Cvar_Set("st_photoMode","1");captureFrames=3;}
static bool command(){
    if(cls.state!=CA_ACTIVE)return false;
    const char *name=Cmd_Argv(0);
    if(!Q_stricmp(name,"st_photoSpectate")){
        Com_Printf("Spectate & fly has been removed.\n");
        return true;
    }
    const bool takePhoto=!Q_stricmp(name,"st_photoCapture");
    if(!takePhoto && Q_stricmp(name,"st_photo"))return false;
    if(!CL_TrialsGame()){
        Com_Printf("Photo Mode requires a Saber Trials server.\n");
        return true;
    }
    if(nativeCamera())return false;
    if(takePhoto){capture();return true;}
    Cvar_Set("st_photoMode",attached()?"0":"1");return true;
}
}

void CL_PhotoEditorFrame(bool visible){personalCamera::editorFrame=visible?cls.framecount:-10;}
bool CL_PhotoOrbitInput(){return personalCamera::orbit();}
bool CL_PhotoOrbitMouse(int dx,int dy){
    using namespace personalCamera;
    if(!orbit() || Key_GetCatcher())return false;
    yaw=AngleNormalize180(yaw-dx*.25f);
    pitch=Com_Clamp(-75,75,pitch+dy*.2f);
    return true;
}
bool CL_ForeignPhotoKey(int key){
    using namespace personalCamera;
    if(mode && mode->integer && cls.state==CA_ACTIVE && CL_TrialsGame() && spectator() &&
       !clc.demoplaying && !Cvar_VariableIntegerValue("st_photoSolo") && !Key_GetCatcher() &&
       (key==A_ENTER || key==A_MOUSE1)){
        Cbuf_ExecuteText(EXEC_INSERT,"st_photoCapture\n");return true;
    }
    if(!attached() || Key_GetCatcher())return false;
    if(key==A_ESCAPE){Cvar_Set("st_photoMode","0");captureFrames=0;return true;}
    if(key==A_ENTER || key==A_MOUSE1){capture();return true;}
    if(key==A_TAB){UIVM_SetActiveMenu(UIMENU_INGAME);Cbuf_ExecuteText(EXEC_INSERT,"ui_openmenu st_photo\n");return true;}
    if(!orbit())return false;
    if(key==A_MWHEELUP || key==A_MWHEELDOWN)distance=Com_Clamp(32,240,distance+(key==A_MWHEELUP?-12:12));
    if(key==A_CURSOR_LEFT || key==A_CURSOR_RIGHT)yaw=AngleNormalize180(yaw+(key==A_CURSOR_LEFT?12:-12));
    if(key==A_CURSOR_UP || key==A_CURSOR_DOWN)pitch=Com_Clamp(-75,75,pitch+(key==A_CURSOR_UP?-6:6));
    return true;
}
bool CL_ForeignPhotoFrame(){
    using namespace personalCamera;
    if(!attached()){captureFrames=cleanUntil=0;return false;}
    if(Key_GetCatcher())return true;
    if(captureFrames>0){
        if(!--captureFrames){Cbuf_ExecuteText(EXEC_INSERT,"screenshot_png\n");cleanUntil=cls.realtime+500;}
        return true;
    }
    if(cls.realtime<cleanUntil)return true;
    if(Cvar_VariableIntegerValue("st_photoGuides")){
        const float w=640,h=480;
        const float tint[]={.45f,.83f,1,.35f};
        re->SetColor(tint);
        for(int n=1;n<=2;n++){
            re->DrawStretchPic(n*w/3,0,1,h,0,0,1,1,cls.whiteShader);
            re->DrawStretchPic(0,n*h/3,w,1,0,0,1,1,cls.whiteShader);
        }
        re->SetColor(nullptr);
    }
    if(Cvar_Get("st_photoHelp","1",CVAR_ARCHIVE)->integer){
        const float tint[]={.8f,.94f,1,1};
        CL_PersonalText(orbit()?"Mouse or arrows: orbit    Wheel: distance    Enter: photo    Tab: settings    Esc: exit":
            "Movement keys: move    Enter: photo    Tab: settings    Esc: exit",.60f,320,452,tint,true);
    }
    return true;
}
