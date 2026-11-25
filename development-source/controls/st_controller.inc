// SDL GameController input. GPL-2.0-only.
static SDL_GameController* stPad;
static bool stPadHeld[18];
static bool stPadBlocked[18];
static int stPadLastTime;
static float stPadCursorX, stPadCursorY;
static const int stPadAxes[] = {AXIS_SIDE, AXIS_FORWARD, AXIS_YAW, AXIS_PITCH};

static void STPadMenuStick(int x, int y) {
 static cvar_t* horizontal=Cvar_Get("st_uiRightStickX","0",CVAR_TEMP);
 static cvar_t* vertical=Cvar_Get("st_uiRightStickY","0",CVAR_TEMP);
 if(horizontal->integer!=x) Cvar_SetValue("st_uiRightStickX",x);
 if(vertical->integer!=y) Cvar_SetValue("st_uiRightStickY",y);
}

static void STPadMenuZoom(int value) {
 static cvar_t* zoom=Cvar_Get("st_uiBumperZoom","0",CVAR_TEMP);
 if(zoom->integer!=value)Cvar_SetValue("st_uiBumperZoom",value);
}

static void STPadRelease() {
 STPadMenuStick(0,0);
 STPadMenuZoom(0);
 stPadCursorX=stPadCursorY=0;
 stPadLastTime=0;
 for(int i=0;i<18;++i) if(stPadHeld[i]) {
  Sys_QueEvent(0,SE_GAMEPAD_BUTTON,i,qfalse,0,NULL);
  stPadHeld[i]=false;
 }
 for(bool& blocked:stPadBlocked)blocked=false;
 for(int axis:stPadAxes) Sys_QueEvent(0,SE_JOYSTICK_AXIS,axis,0,0,NULL);
}

#include "st_pad_devices.inc"

static void STPadPointer(int x,int y,int now,float speed,bool menuCursor=false) {
 const float dt=stPadLastTime?Com_Clamp(0,50,(float)(now-stPadLastTime))*.001f:0;
 stPadLastTime=now;
 const float magnitude=std::hypot((float)x,(float)y);
 if(magnitude<=0) {stPadCursorX=stPadCursorY=0;return;}
 const float deflection=Com_Clamp(0,1,magnitude/32767.f);
 // Give a small stick movement a prompt response while retaining fine control.
 const float response=menuCursor?deflection*(0.65f+0.35f*deflection):deflection*deflection;
 const float step=dt*(70+65*speed)*response/magnitude;
 stPadCursorX+=x*step;
 stPadCursorY+=y*step;
 const int dx=(int)stPadCursorX,dy=(int)stPadCursorY;
 stPadCursorX-=dx;
 stPadCursorY-=dy;
 if(dx||dy) Sys_QueEvent(0,SE_GAMEPAD_POINTER,dx,dy,0,NULL);
}

static bool STPadFrame(bool focused) {
 static cvar_t* deadzone=Cvar_Get("st_controllerDeadzone","0.15",CVAR_ARCHIVE);
 static cvar_t* cursorSpeed=Cvar_Get("st_controllerMenuSpeed","5",CVAR_ARCHIVE);
 if(!stPad)return false;
 const int catcher=Key_GetCatcher();
 const bool menu=(catcher&KEYCATCH_UI)&&!(catcher&KEYCATCH_CONSOLE);
 const bool consoleKeyboard=Con_PadKeyboardActive();
 const float dead=Com_Clamp(0,.95f,deadzone->value);
 int values[4];
 for(int i=0;i<4;++i){
  const float raw=focused?SDL_GameControllerGetAxis(stPad,(SDL_GameControllerAxis)i)/32767.f:0;
  const float magnitude=fabsf(raw);
  values[i]=magnitude<=dead?0:(int)(Com_Clamp(0,1,(magnitude-dead)/(1-dead))*32767*(raw<0?-1:1));
  Sys_QueEvent(0,SE_JOYSTICK_AXIS,stPadAxes[i],values[i],0,NULL);
 }
 STPadMenuStick(menu?values[2]:0,menu?values[3]:0);
 if((menu||consoleKeyboard)&&focused){
  const bool keyboard=consoleKeyboard||Cvar_VariableIntegerValue("st_uiNameKeyboard")!=0;
  const int horizontal=keyboard?0:SDL_GameControllerGetButton(stPad,SDL_CONTROLLER_BUTTON_DPAD_RIGHT)-SDL_GameControllerGetButton(stPad,SDL_CONTROLLER_BUTTON_DPAD_LEFT);
  const int vertical=keyboard?0:SDL_GameControllerGetButton(stPad,SDL_CONTROLLER_BUTTON_DPAD_DOWN)-SDL_GameControllerGetButton(stPad,SDL_CONTROLLER_BUTTON_DPAD_UP);
  STPadPointer(horizontal?horizontal*22000:values[0],vertical?vertical*22000:values[1],
   Sys_Milliseconds(),Com_Clamp(1,10,cursorSpeed->value),true);
 }
 else{stPadLastTime=0;stPadCursorX=stPadCursorY=0;}
 for(int i=0;i<18;++i){
  STPadButtonState(i,STPadPressed(stPad,i),focused);
 }
 STPadMenuZoom(menu?(int)stPadHeld[9]-(int)stPadHeld[10]:0);
 return true;
}
