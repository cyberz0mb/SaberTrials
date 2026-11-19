// SDL GameController input. GPL-2.0-only. Legacy joystick fallback is unchanged.
static SDL_GameController* stPad = NULL;
static bool stPadHeld[18] = {};
static bool stPadWasEnabled = false;
static const int stPadAxes[4] = {AXIS_SIDE, AXIS_FORWARD, AXIS_YAW, AXIS_PITCH};
// The native saber inspector reads the same deadzone-adjusted stick as gameplay.
static void STPadMenuStick(int x, int y) {
 static cvar_t* horizontal=Cvar_Get("st_uiRightStickX","0",CVAR_TEMP);
 static cvar_t* vertical=Cvar_Get("st_uiRightStickY","0",CVAR_TEMP);
 if(horizontal->integer!=x) Cvar_SetValue("st_uiRightStickX",x);
 if(vertical->integer!=y) Cvar_SetValue("st_uiRightStickY",y);
}
static void STPadRelease() {
 STPadMenuStick(0,0);
 for(int i=0;i<18;++i) if(stPadHeld[i]) {Sys_QueEvent(0,SE_KEY,A_JOY0+i,qfalse,0,NULL);stPadHeld[i]=false;}
 for(int i=0;i<4;++i) Sys_QueEvent(0,SE_JOYSTICK_AXIS,stPadAxes[i],0,0,NULL);
}
static void STPadClose() {STPadRelease();if(stPad)SDL_GameControllerClose(stPad);stPad=NULL;Cvar_Set("st_controllerDevice","No compatible controller detected");}
static bool STPadFrame() {
 // Re-registering an archived cvar dirties the config even if it has not changed.
 static cvar_t* enabledSetting=Cvar_Get("st_controllerEnabled","0",CVAR_ARCHIVE);
 static cvar_t* deviceSetting=Cvar_Get("st_controllerDevice","No compatible controller detected",CVAR_ROM);
 (void)deviceSetting;
 bool enabled=enabledSetting->integer!=0;
 if(!enabled){if(stPadWasEnabled)STPadClose();stPadWasEnabled=false;return false;}
 if(!stPadWasEnabled){STPadRelease();Key_ClearStates();}stPadWasEnabled=true;
 if(!(SDL_WasInit(SDL_INIT_GAMECONTROLLER)&SDL_INIT_GAMECONTROLLER)&&SDL_InitSubSystem(SDL_INIT_GAMECONTROLLER)<0)return true;
 if(stPad&&!SDL_GameControllerGetAttached(stPad))STPadClose();
 if(!stPad){for(int i=0;i<SDL_NumJoysticks();++i)if(SDL_IsGameController(i)&&(stPad=SDL_GameControllerOpen(i)))break;
  if(stPad)Cvar_Set("st_controllerDevice",SDL_GameControllerName(stPad));}
 if(!stPad)return true;
 SDL_GameControllerUpdate();
 for(int i=0;i<18;++i){bool held=i<15?SDL_GameControllerGetButton(stPad,(SDL_GameControllerButton)i)!=0:i>=16?SDL_GameControllerGetAxis(stPad,i==16?SDL_CONTROLLER_AXIS_TRIGGERLEFT:SDL_CONTROLLER_AXIS_TRIGGERRIGHT)>8192:false;
  if(held!=stPadHeld[i]){Sys_QueEvent(0,SE_KEY,A_JOY0+i,held,0,NULL);stPadHeld[i]=held;}}
 static cvar_t* deadzoneSetting=Cvar_Get("st_controllerDeadzone","0.15",CVAR_ARCHIVE);
 float dead=Com_Clamp(0,.95f,deadzoneSetting->value);
 int values[4];
 for(int i=0;i<4;++i){
  float raw=SDL_GameControllerGetAxis(stPad,(SDL_GameControllerAxis)i)/32767.0f;
  float mag=fabsf(raw);
  values[i]=mag<=dead?0:(int)(Com_Clamp(0,1,(mag-dead)/(1-dead))*32767*(raw<0?-1:1));
  Sys_QueEvent(0,SE_JOYSTICK_AXIS,stPadAxes[i],values[i],0,NULL);
 }
 if(Key_GetCatcher()&KEYCATCH_UI) STPadMenuStick(values[2],values[3]);
 else STPadMenuStick(0,0);
 return true;
}
