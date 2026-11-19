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

static void STPadClose() {
 if(!stPad) return;
 STPadRelease();
 SDL_GameControllerClose(stPad);
 stPad=NULL;
 Cvar_Set("st_controllerDevice","No compatible controller detected");
 Cvar_SetValue("st_controllerActive",0);
}

static void STPadPointer(int x,int y,int now,float speed) {
 const float dt=stPadLastTime?Com_Clamp(0,50,(float)(now-stPadLastTime))*.001f:0;
 stPadLastTime=now;
 const float magnitude=std::hypot((float)x,(float)y);
 if(magnitude<=0) {stPadCursorX=stPadCursorY=0;return;}
 const float deflection=Com_Clamp(0,1,magnitude/32767.f);
 const float step=dt*(70+65*speed)*deflection*deflection/magnitude;
 stPadCursorX+=x*step;
 stPadCursorY+=y*step;
 const int dx=(int)stPadCursorX,dy=(int)stPadCursorY;
 stPadCursorX-=dx;
 stPadCursorY-=dy;
 if(dx||dy) Sys_QueEvent(0,SE_GAMEPAD_POINTER,dx,dy,0,NULL);
}

static bool STPadFrame(bool focused) {
 // Legacy 0 and 1 both select automatic detection. 2 is the explicit opt-out.
 static cvar_t* mode=Cvar_Get("st_controllerEnabled","1",CVAR_ARCHIVE);
 static cvar_t* deadzone=Cvar_Get("st_controllerDeadzone","0.15",CVAR_ARCHIVE);
 static cvar_t* cursorSpeed=Cvar_Get("st_controllerMenuSpeed","5",CVAR_ARCHIVE);
 static cvar_t* device=Cvar_Get("st_controllerDevice","No compatible controller detected",CVAR_ROM);
 static cvar_t* active=Cvar_Get("st_controllerActive","0",CVAR_ROM);
 (void)device;(void)active;
 if(mode->integer==2){STPadClose();return false;}
 if(!(SDL_WasInit(SDL_INIT_GAMECONTROLLER)&SDL_INIT_GAMECONTROLLER)&&SDL_InitSubSystem(SDL_INIT_GAMECONTROLLER)<0)return false;
 if(stPad&&!SDL_GameControllerGetAttached(stPad))STPadClose();
 if(!stPad){
  for(int i=0;i<SDL_NumJoysticks();++i)
   if(SDL_IsGameController(i)&&(stPad=SDL_GameControllerOpen(i)))break;
  if(!stPad)return false;
  if(in_joystick->integer)Key_ClearStates();
  Cvar_Set("st_controllerDevice",SDL_GameControllerName(stPad));
  Cvar_SetValue("st_controllerActive",1);
 }
 SDL_GameControllerUpdate();
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
   Sys_Milliseconds(),Com_Clamp(1,10,cursorSpeed->value));
 }
 else{stPadLastTime=0;stPadCursorX=stPadCursorY=0;}
 for(int i=0;i<18;++i){
  const bool pressed=i<15?SDL_GameControllerGetButton(stPad,(SDL_GameControllerButton)i)!=0:
   i>=16&&SDL_GameControllerGetAxis(stPad,i==16?SDL_CONTROLLER_AXIS_TRIGGERLEFT:SDL_CONTROLLER_AXIS_TRIGGERRIGHT)>8192;
  if(!focused||!pressed)stPadBlocked[i]=pressed;
  const bool held=focused&&pressed&&!stPadBlocked[i];
  if(held!=stPadHeld[i]){Sys_QueEvent(0,SE_GAMEPAD_BUTTON,i,held,0,NULL);stPadHeld[i]=held;}
 }
 STPadMenuZoom(menu?(int)stPadHeld[9]-(int)stPadHeld[10]:0);
 return true;
}
