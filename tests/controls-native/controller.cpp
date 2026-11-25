// Contract tests exercise the production adapter with simulated SDL hardware.
// These do not establish physical device/driver compatibility.
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <map>
#include <string>
#include <vector>
typedef bool qboolean;
const bool qtrue=true,qfalse=false;
enum {AXIS_SIDE,AXIS_FORWARD,AXIS_UP,AXIS_ROLL,AXIS_YAW,AXIS_PITCH};
enum {A_JOY0=256,A_MOUSE1=10,A_ESCAPE=27,SE_KEY=1,SE_JOYSTICK_AXIS=2,SE_GAMEPAD_BUTTON=3,SE_GAMEPAD_POINTER=4,CVAR_ARCHIVE=1,CVAR_ROM=2,CVAR_TEMP=4};
enum {SDL_INIT_GAMECONTROLLER=512,SDL_CONTROLLER_AXIS_TRIGGERLEFT=4,SDL_CONTROLLER_AXIS_TRIGGERRIGHT=5,SDL_CONTROLLER_AXIS_MAX=6,SDL_CONTROLLER_BUTTON_MAX=15};
enum {SDL_CONTROLLERDEVICEADDED, SDL_CONTROLLERDEVICEREMOVED, SDL_CONTROLLERAXISMOTION, SDL_CONTROLLERBUTTONDOWN, SDL_CONTROLLERBUTTONUP};
typedef int SDL_JoystickID;
struct SDL_Event { int type; struct {int which;} cdevice; struct {int which,axis,value;} caxis; struct {int which,button;} cbutton; };
enum {SDL_CONTROLLER_BUTTON_DPAD_UP=11,SDL_CONTROLLER_BUTTON_DPAD_DOWN,SDL_CONTROLLER_BUTTON_DPAD_LEFT,SDL_CONTROLLER_BUTTON_DPAD_RIGHT};
enum {KEYCATCH_UI=1,KEYCATCH_CONSOLE=2,KEYCATCH_MESSAGE=4,KEYCATCH_CGAME=8,BUTTON_WALKING=1,YAW=1,PITCH=0,CA_ACTIVE=5,UIMENU_INGAME=1};
typedef int SDL_GameControllerButton;
typedef int SDL_GameControllerAxis;
struct SDL_GameController {bool attached=false;int axes[6]={};bool buttons[15]={};} device, secondDevice;
struct cvar_t {float value=0;int integer=0;};
static std::map<std::string,cvar_t> vars;
static cvar_t* Cvar_Get(const char* n,const char* d,int){auto p=vars.emplace(n,cvar_t{(float)atof(d),atoi(d)});return &p.first->second;}
static void Cvar_Set(const char* n,const char* value){auto p=Cvar_Get(n,value,0);p->value=(float)atof(value);p->integer=atoi(value);}
static void Cvar_SetValue(const char* name, float value){
 const auto text=std::to_string(value);
 Cvar_Set(name,text.c_str());
}
static float Com_Clamp(float lo,float hi,float n){return std::max(lo,std::min(hi,n));}
static bool initialized=false;
static int SDL_InitSubSystem(int){initialized=true;return 0;}
static void SDL_QuitSubSystem(int){initialized=false;}
static int SDL_NumJoysticks(){return int(device.attached)+int(secondDevice.attached);}
static SDL_JoystickID SDL_JoystickGetDeviceInstanceID(int index){return 100+index;}
static bool SDL_IsGameController(int){return true;}
static SDL_GameController* SDL_GameControllerOpen(int index){return index?&secondDevice:&device;}
static void SDL_GameControllerClose(SDL_GameController*){}
static const char* SDL_GameControllerName(SDL_GameController*){return "Simulated gamepad";}
static bool SDL_GameControllerGetButton(SDL_GameController* p,int i){return p->buttons[i];}
static int SDL_GameControllerGetAxis(SDL_GameController* p,int i){return p->axes[i];}
struct Event{int type,key,value;};static std::vector<Event> events;
static void Sys_QueEvent(int,int type,int key,int value,int,void*){events.push_back({type,key,value});}
static int cleared=0,catcher=0;
static cvar_t* in_joystick=Cvar_Get("in_joystick","0",0);
static void Key_ClearStates(){++cleared;}
static int Key_GetCatcher(){return catcher;}
static int Cvar_VariableIntegerValue(const char* name){const auto v=vars.find(name);return v==vars.end()?0:v->second.integer;}
static int Sys_Milliseconds(){static int now=0;return now+=16;}
static bool padKeyboard=false;
static bool Con_PadKeyboardActive(){return padKeyboard&&(catcher&KEYCATCH_CONSOLE);}
static void Con_OpenPadKeyboard(){padKeyboard=true;}
static bool Con_AutoKeyboard(bool gamepad){return gamepad;}
static void Con_SetPadKeyboard(int){padKeyboard=true;}
static void Message_Key(int){catcher&=~KEYCATCH_MESSAGE;}
static void Cmd_ExecuteString(const char*){catcher|=KEYCATCH_MESSAGE;}
static void Con_ToggleMenu_f(){catcher^=KEYCATCH_UI;}
static void Con_ToggleConsole_f(){catcher^=KEYCATCH_CONSOLE;if(!(catcher&KEYCATCH_CONSOLE))padKeyboard=false;}
static bool Q_stricmp(const char* a,const char* b){return std::string(a)!=b;}
#include "st_controller.inc"
struct usercmd_t{int rightmove=0,forwardmove=0,buttons=0;};
static struct {int joystickAxis[6]={};float viewangles[3]={};} cl;
static struct {float frametime=16;bool uiStarted=true;int state=CA_ACTIVE;} cls;
static struct {bool demoplaying=false;} clc;
static struct {int active=0;} in_speed;
static cvar_t* cl_run=Cvar_Get("cl_run","1",0);
static int ClampChar(int n){return std::max(-127,std::min(127,n));}
#ifdef ST_RELEASE_CONTROLLER
static bool CL_EmoteWheelActive(){return false;}
#include "client/cl_st_controller.inc"
#else
#include "../../development-source/client-runtime/st_controller_move.inc"
#endif
static bool capturing=false;
static bool STC_IsCapturing(){return capturing;}
static bool gameplayDown[18];
static bool Key_IsDown(int key){return gameplayDown[key-A_JOY0];}
static bool consoleBound=false;
static bool faceShortcuts=false;
static const char* Key_GetBinding(int key){
 if(faceShortcuts&&key==A_JOY0)return "toggleconsole";
 if(faceShortcuts&&key==A_JOY0+1)return "togglemenu";
 return consoleBound&&key==A_JOY0+3?"toggleconsole":"";
}
static void CL_KeyEvent(int key,qboolean down,unsigned){gameplayDown[key-A_JOY0]=down;events.push_back({SE_KEY,key,down});}
static void UIVM_KeyEvent(int key,qboolean down){events.push_back({5,key,down});}
static void UIVM_MouseEvent(int x,int y){events.push_back({6,x,y});}
static void UIVM_SetActiveMenu(int menu){events.push_back({7,menu,0});}
static void Con_PadKeyboardMove(int x,int y){events.push_back({8,x,y});}
static void Con_PadKeyboardButton(int button,int confirm){events.push_back({9,button,confirm});}
#include "cl_st_pad_menu.inc"
static void check(bool ok,const char* message){if(!ok){std::cerr<<message<<'\n';std::exit(1);}}
static bool has(int type,int key,int value){for(auto e:events)if(e.type==type&&e.key==key&&e.value==value)return true;return false;}
int main(){
 STPadBeginFrame();
 check(!STPadFrame(true),"missing gamepad captured legacy input");
 Cvar_Set("st_controllerEnabled","0");device.attached=true;device.buttons[0]=true;device.axes[4]=20000;
 STPadHandleEvent({SDL_CONTROLLERDEVICEADDED,{0}},true);
 device.axes[0]=32767;device.axes[1]=-32768;device.axes[2]=1000;
 check(STPadFrame(true),"existing disabled default did not auto-detect a device");
 check(has(SE_GAMEPAD_BUTTON,0,1)&&has(SE_GAMEPAD_BUTTON,16,1),"button/trigger normalization failed");
 check(has(SE_JOYSTICK_AXIS,AXIS_SIDE,32767)&&has(SE_JOYSTICK_AXIS,AXIS_FORWARD,-32767)&&has(SE_JOYSTICK_AXIS,AXIS_YAW,0),"axis clamp/deadzone failed");
 events.clear();device.attached=false;STPadHandleEvent({SDL_CONTROLLERDEVICEREMOVED,{100}},true);STPadFrame(true);check(has(SE_GAMEPAD_BUTTON,0,0)&&has(SE_GAMEPAD_BUTTON,16,0)&&has(SE_JOYSTICK_AXIS,AXIS_SIDE,0),"disconnect left held input");
 events.clear();device.attached=true;STPadHandleEvent({SDL_CONTROLLERDEVICEADDED,{0}},true);STPadFrame(true);check(has(SE_GAMEPAD_BUTTON,0,1),"reconnect did not restore events");
 events.clear();Cvar_Set("st_controllerEnabled","2");STPadBeginFrame();check(!STPadFrame(true)&&has(SE_GAMEPAD_BUTTON,0,0),"disable left held button");
 Cvar_Set("st_controllerEnabled","1");STPadBeginFrame();STPadFrame(true);
 cl.joystickAxis[AXIS_SIDE]=32767;cl.joystickAxis[AXIS_FORWARD]=-32767;cl.joystickAxis[AXIS_YAW]=32767;cl.joystickAxis[AXIS_PITCH]=32767;
 Cvar_Set("st_controllerHorizontal","2");Cvar_Set("st_controllerVertical","8");Cvar_Set("sensitivity","999");Cvar_Set("cl_yawspeed","9999");cls.frametime=100;
 usercmd_t cmd;check(STPadMove(&cmd)&&cmd.rightmove==127&&cmd.forwardmove==127,"movement mapping failed");
 check(std::abs(cl.viewangles[YAW]+6)<.001&&std::abs(cl.viewangles[PITCH]-24)<.001,"look axes depend on incorrect setting");
 catcher=KEYCATCH_UI;auto yaw=cl.viewangles[YAW];STPadMove(&cmd);check(cl.viewangles[YAW]==yaw,"menu allowed gameplay look");
 catcher=0;Cvar_Set("st_controllerInvert","1");STPadMove(&cmd);check(std::abs(cl.viewangles[PITCH])<.001,"controller inversion failed");
#ifdef ST_RELEASE_CONTROLLER
 cls.frametime=10;
 auto checkLook=[&](const char* horizontal,const char* vertical,float yawDelta,float pitchDelta){
  Cvar_Set("st_controllerHorizontal",horizontal);Cvar_Set("st_controllerVertical",vertical);
  cl.viewangles[YAW]=cl.viewangles[PITCH]=0;
  STPadMove(&cmd);
  check(std::abs(cl.viewangles[YAW]-yawDelta)<.001f && std::abs(cl.viewangles[PITCH]-pitchDelta)<.001f,
   "right-stick sensitivity produced the wrong angle");
 };
 checkLook("30","5.25",-9.f,-1.575f);
 checkLook("60","45",-18.f,-13.5f);
 checkLook("0","100",-.3f,-18.f);
#endif
 catcher=KEYCATCH_UI;device.axes[1]=0;
 auto travel=[](){events.clear();for(int i=0;i<15;++i)STPadFrame(true);int sum=0;for(auto e:events)if(e.type==SE_GAMEPAD_POINTER)sum+=e.key;return sum;};
 Cvar_Set("st_controllerMenuSpeed","1");const int slow=travel();
 Cvar_Set("st_controllerMenuSpeed","10");check(slow>0&&travel()>slow*3,"menu pointer speed did not scale");
 device.axes[0]=1000;check(travel()==0,"stick drift moved the menu pointer");
 device.axes[0]=9000;Cvar_Set("st_controllerMenuSpeed","5");check(travel()>=6,"light stick movement was sluggish");
 device.axes[0]=1000;
 device.buttons[14]=true;check(travel()>0,"D-pad did not move the pointer");
 events.clear();STPadFrame(false);check(has(SE_GAMEPAD_BUTTON,0,0),"focus loss left held input");
 events.clear();STPadFrame(true);check(!has(SE_GAMEPAD_BUTTON,0,1),"focus gain replayed a held press");
 faceShortcuts=true;
 events.clear();CL_GamepadPointer(7,-4);CL_GamepadButton(0,true,0);CL_GamepadButton(0,false,0);CL_GamepadButton(1,true,0);
 check(has(6,7,-4)&&has(5,A_MOUSE1,1)&&has(5,A_MOUSE1,0)&&has(5,A_ESCAPE,1),"menu pointer/click/back dispatch failed");
 faceShortcuts=false;
 secondDevice.attached=true;STPadHandleEvent({SDL_CONTROLLERDEVICEADDED,{1}},true);
 STPadHandleEvent({SDL_CONTROLLERAXISMOTION,{},{101,0,900}},true);
 check(stPad==&device,"idle pad stole focus");
 events.clear();
 STPadHandleEvent({SDL_CONTROLLERBUTTONDOWN,{},{},{101,0}},true);
 STPadHandleEvent({SDL_CONTROLLERBUTTONUP,{},{},{101,0}},true);
 STPadFrame(true);
 check(stPad==&secondDevice,"first tap did not activate the other pad");
 std::vector<int> edges;
 for(auto event:events)if(event.type==SE_GAMEPAD_BUTTON&&event.key==0)edges.push_back(event.value);
 check(edges==std::vector<int>({1,0}),"sub-frame tap dropped or duplicated");
 STPadHandleEvent({SDL_CONTROLLERAXISMOTION,{},{100,1,19000}},true);
 check(stPad==&device,"stick did not activate its pad");
 STPadHandleEvent({SDL_CONTROLLERBUTTONDOWN,{},{},{101,1}},false);
 check(stPad==&device,"unfocused input claimed the controller");
 Cvar_Set("st_controllerMenuLayout","1");events.clear();CL_GamepadButton(1,true,0);CL_ReleaseGamepadMenuButtons();
 check(has(5,A_MOUSE1,1)&&has(5,A_MOUSE1,0),"swapped click did not release on context switch");
 capturing=true;events.clear();CL_GamepadButton(0,true,0);check(has(5,A_JOY0,1),"binding capture did not receive raw button");
 CL_GamepadButton(0,false,0);
 capturing=false;catcher=0;events.clear();CL_GamepadButton(0,true,0);CL_GamepadButton(0,false,0);CL_GamepadButton(6,true,0);
 check(has(SE_KEY,A_JOY0,1)&&has(SE_KEY,A_JOY0,0)&&has(7,UIMENU_INGAME,0),"gameplay binding or pause fallback failed");
 consoleBound=true;events.clear();CL_GamepadButton(3,true,0);CL_GamepadButton(3,false,0);
 check(Con_PadKeyboardActive(),"mapped console button did not open keyboard");
 CL_GamepadPointer(12,14);CL_GamepadButton(0,true,0);
 check(has(8,12,14)&&has(9,0,1),"console keyboard did not receive pointer or swapped button layout");
 CL_GamepadButton(3,true,0);check(!Con_PadKeyboardActive()&&!catcher,"mapped console button did not close both");
 std::cout<<"PASS: detection, deadzone, menu sensitivity, mappings, focus/disconnect release and gameplay bindings\n";
}
