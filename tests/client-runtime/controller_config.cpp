#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <map>
#include <string>
struct cvar_t { int integer; float value; };
struct usercmd_t { int rightmove=0,forwardmove=0,buttons=0; };
constexpr int CVAR_ARCHIVE=1,KEYCATCH_UI=1,KEYCATCH_CONSOLE=2,KEYCATCH_MESSAGE=4,KEYCATCH_CGAME=8;
constexpr int AXIS_SIDE=0,AXIS_FORWARD=1,AXIS_YAW=2,AXIS_PITCH=3,YAW=0,PITCH=1,BUTTON_WALKING=1;
static std::map<std::string,cvar_t> vars;
static int registrations=0,catcher=0;
static bool archiveDirty=false;
static cvar_t* Cvar_Get(const char* name,const char* value,int flags) {
 ++registrations;archiveDirty|=(flags&CVAR_ARCHIVE)!=0;
 return &vars.emplace(name,cvar_t{std::atoi(value),(float)std::atof(value)}).first->second;
}
static int Key_GetCatcher(){return catcher;}
static int Cvar_VariableIntegerValue(const char* name){const auto v=vars.find(name);return v==vars.end()?0:v->second.integer;}
static float Com_Clamp(float lo,float hi,float x){return std::max(lo,std::min(hi,x));}
static int ClampChar(int x){return std::max(-128,std::min(127,x));}
static struct {int frametime=16;} cls;
static struct {int joystickAxis[4]={};float viewangles[2]={};} cl;
static struct {int active=0;} in_speed;
static cvar_t run={1,1};static cvar_t* cl_run=&run;
#include "../../development-source/client-runtime/st_controller_move.inc"
using SDL_GameController=int;using SDL_GameControllerButton=int;using SDL_GameControllerAxis=int;
constexpr int CVAR_ROM=2,CVAR_TEMP=4,SE_GAMEPAD_BUTTON=1,SE_JOYSTICK_AXIS=2,SE_GAMEPAD_POINTER=3,qfalse=0;
constexpr int SDL_INIT_GAMECONTROLLER=1,SDL_CONTROLLER_AXIS_TRIGGERLEFT=4,SDL_CONTROLLER_AXIS_TRIGGERRIGHT=5;
constexpr int SDL_CONTROLLER_BUTTON_DPAD_UP=11,SDL_CONTROLLER_BUTTON_DPAD_DOWN=12,SDL_CONTROLLER_BUTTON_DPAD_LEFT=13,SDL_CONTROLLER_BUTTON_DPAD_RIGHT=14;
static int controller=1,closed=0,axisEvent=0,deviceAxis=16384;
static void Sys_QueEvent(int,int type,int,int value,int,void*){if(type==SE_JOYSTICK_AXIS)axisEvent=value;}
static void Cvar_Set(const char*,const char*){}
static void Cvar_SetValue(const char* name,float value){vars.at(name)={int(value),value};}
static void Key_ClearStates(){}
static cvar_t legacyJoystick={0,0};static cvar_t* in_joystick=&legacyJoystick;
static int Sys_Milliseconds(){static int now=0;return now+=16;}
static bool Con_PadKeyboardActive(){return false;}
static int SDL_WasInit(int flags){return flags;}
static int SDL_InitSubSystem(int){return 0;}
static bool SDL_GameControllerGetAttached(SDL_GameController*){return true;}
static int SDL_NumJoysticks(){return 1;}
static bool SDL_IsGameController(int){return true;}
static SDL_GameController* SDL_GameControllerOpen(int){return &controller;}
static const char* SDL_GameControllerName(SDL_GameController*){return "Mock controller";}
static void SDL_GameControllerClose(SDL_GameController*){++closed;}
static void SDL_GameControllerUpdate(){}
static int SDL_GameControllerGetButton(SDL_GameController*,int){return 0;}
static int SDL_GameControllerGetAxis(SDL_GameController*,int axis){return axis<4?deviceAxis:0;}
#include "../../development-source/controls/st_controller.inc"
static void require(bool ok,const char* what){if(!ok){std::fprintf(stderr,"FAIL: %s\n",what);std::exit(1);}}
int main(){
 usercmd_t cmd;
 require(!STPadMove(&cmd),"disabled controller falls through");
 archiveDirty=false;
 for(int i=0;i<1000;++i)require(!STPadMove(&cmd),"disabled frame");
 require(!archiveDirty&&registrations==0,"idle frames do not rewrite settings");
 STPadFrame(true);
 cl.joystickAxis[AXIS_YAW]=cl.joystickAxis[AXIS_PITCH]=32767;
 require(STPadMove(&cmd),"enable change takes effect without restart");
 require(std::fabs(cl.viewangles[YAW]+2.4f)<.001f,"original horizontal sensitivity");
 archiveDirty=false;const int afterOpen=registrations;
 for(int i=0;i<1000;++i)STPadMove(&cmd);
 require(!archiveDirty&&registrations==afterOpen,"active frames do not register settings again");
 vars.at("st_controllerHorizontal").value=10;vars.at("st_controllerInvert").integer=1;
 cl.viewangles[YAW]=cl.viewangles[PITCH]=0;STPadMove(&cmd);
 require(std::fabs(cl.viewangles[YAW]+4.8f)<.001f&&std::fabs(cl.viewangles[PITCH]+2.4f)<.001f,"live sensitivity and inversion");
 vars.at("st_controllerHorizontal").value=30;vars.at("st_controllerVertical").value=45;
 cl.viewangles[YAW]=cl.viewangles[PITCH]=0;STPadMove(&cmd);
 require(std::fabs(cl.viewangles[YAW]+14.4f)<.001f&&std::fabs(cl.viewangles[PITCH]+14.4f)<.001f,"expanded look range and upper clamp");
 catcher=KEYCATCH_UI;cl.viewangles[YAW]=0;STPadMove(&cmd);
 require(cl.viewangles[YAW]==0,"menu blocks controller look");
 vars.at("st_controllerEnabled").integer=2;STPadFrame(true);archiveDirty=false;
 int before=registrations;
 for(int i=0;i<1000;++i)require(!STPadFrame(true),"disabled SDL input falls through");
 require(!archiveDirty&&registrations==before,"SDL polling does not save idle config");
 vars.at("st_controllerEnabled").integer=1;STPadFrame(true);archiveDirty=false;before=registrations;
 for(int i=0;i<1000;++i)STPadFrame(true);
 require(!archiveDirty&&registrations==before&&axisEvent>0,"active SDL polling reuses live cvars");
 vars.at("st_controllerDeadzone").value=.75f;STPadFrame(true);
 require(axisEvent==0,"deadzone changes take effect live");
 vars.at("st_controllerEnabled").integer=2;STPadFrame(true);
 require(closed==2&&axisEvent==0,"disable releases input and closes controller");
 std::puts("Controller config lifecycle passed");
}
