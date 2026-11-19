// Normalized gamepad buttons are routed using the catcher at dispatch time.
static int stPadMenuKeys[18];
static int stPadClickButton=-1;

static void CL_GamepadPointer(int dx,int dy) {
 if(Con_PadKeyboardActive())Con_PadKeyboardMove(dx,dy);
 else if(cls.uiStarted&&(Key_GetCatcher()&(KEYCATCH_UI|KEYCATCH_CONSOLE))==KEYCATCH_UI)
  UIVM_MouseEvent(dx,dy);
}

static void CL_GamepadButton(int button,qboolean down,unsigned time) {
 if(button<0||button>=18)return;
 const int raw=A_JOY0+button;
 const bool menu=cls.uiStarted&&(Key_GetCatcher()&(KEYCATCH_UI|KEYCATCH_CONSOLE))==KEYCATCH_UI;
 if(!down){
  const int key=stPadMenuKeys[button];
  stPadMenuKeys[button]=0;
  if(key){
   if(key==A_MOUSE1)stPadClickButton=-1;
   if(menu)UIVM_KeyEvent(key,qfalse);
  }else if(Key_IsDown(raw))CL_KeyEvent(raw,qfalse,time);
  return;
 }
 const int accept=Cvar_VariableIntegerValue("st_controllerMenuLayout")==1?1:0;
 const char* binding=Key_GetBinding(raw);
 if(!STC_IsCapturing()&&binding&&!(Key_GetCatcher()&(KEYCATCH_CONSOLE|KEYCATCH_UI|KEYCATCH_CGAME))&&cls.state==CA_ACTIVE){
  const char* chatBindings[]={"messagemode","messagemode2","messagemode3","messagemode4"};
  for(const char* command:chatBindings)if(!Q_stricmp(binding,command)){
   if(Key_GetCatcher()&KEYCATCH_MESSAGE)Message_Key(A_ESCAPE);
   else{
    Cmd_ExecuteString(command);
    if((Key_GetCatcher()&KEYCATCH_MESSAGE)&&Con_AutoKeyboard(true))Con_SetPadKeyboard(KEYCATCH_MESSAGE);
   }
   return;
  }
 }
 if(!STC_IsCapturing()&&binding&&!Q_stricmp(binding,"toggleconsole")) {
  const bool opening=!(Key_GetCatcher()&KEYCATCH_CONSOLE);
  Con_ToggleConsole_f();
  if(opening&&(Key_GetCatcher()&KEYCATCH_CONSOLE)&&Con_AutoKeyboard(true))Con_OpenPadKeyboard();
  return;
 }
 if(!STC_IsCapturing()&&binding&&!Q_stricmp(binding,"togglemenu")&&
    !(Key_GetCatcher()&KEYCATCH_CONSOLE)&&cls.state==CA_ACTIVE&&!clc.demoplaying){
  if(Key_GetCatcher()&KEYCATCH_MESSAGE)Message_Key(A_ESCAPE);
  if(!(Key_GetCatcher()&KEYCATCH_UI)||menu)Cmd_ExecuteString("togglemenu");
  return;
 }
 if(Con_PadKeyboardActive()){Con_PadKeyboardButton(button,accept);return;}
 if((Key_GetCatcher()&KEYCATCH_MESSAGE)&&button==1-accept){Message_Key(A_ESCAPE);return;}
 if(!menu){
  if(button==6&&!Key_GetCatcher()&&cls.state==CA_ACTIVE&&!clc.demoplaying&&(!binding||!*binding))
   UIVM_SetActiveMenu(UIMENU_INGAME);
  else CL_KeyEvent(raw,qtrue,time);
  return;
 }

 int key=raw;
 if(!STC_IsCapturing()){
  if(button==accept)key=A_MOUSE1;
  else if(button==1-accept||button==6)key=A_ESCAPE;
  else if(button>=11&&button<=14&&!Cvar_VariableIntegerValue("st_uiNameKeyboard"))return;
 }
 if(key==A_MOUSE1){if(stPadClickButton>=0)return;stPadClickButton=button;}
 stPadMenuKeys[button]=key;
 if(key==A_MOUSE1){static cvar_t* marker=Cvar_Get("st_uiPadClick","0",CVAR_TEMP);(void)marker;Cvar_SetValue("st_uiPadClick",1);}
 UIVM_KeyEvent(key,qtrue);
 if(key==A_MOUSE1)Cvar_SetValue("st_uiPadClick",0);
}

static void CL_ReleaseGamepadMenuButtons() {
 if(stPadClickButton<0)return;
 stPadMenuKeys[stPadClickButton]=0;
 stPadClickButton=-1;
 if(cls.uiStarted&&(Key_GetCatcher()&KEYCATCH_UI))UIVM_KeyEvent(A_MOUSE1,qfalse);
}
