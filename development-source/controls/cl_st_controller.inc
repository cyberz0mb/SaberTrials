// Dedicated look sensitivity: independent of mouse and keyboard turn cvars.
static bool STPadMove(usercmd_t* cmd) {
 if(!Cvar_Get("st_controllerEnabled","0",CVAR_ARCHIVE)->integer)return false;
 if(Key_GetCatcher()&(KEYCATCH_UI|KEYCATCH_CONSOLE|KEYCATCH_MESSAGE))return true;
 float dt=Com_Clamp(0,100,(float)cls.frametime)*.001f;
 float horizontal=Com_Clamp(1,30,Cvar_Get("st_controllerHorizontal","5",CVAR_ARCHIVE)->value);
 float vertical=Com_Clamp(1,30,Cvar_Get("st_controllerVertical","5",CVAR_ARCHIVE)->value);
 float invert=Cvar_Get("st_controllerInvert","0",CVAR_ARCHIVE)->integer?-1.f:1.f;
 cmd->rightmove=ClampChar(cmd->rightmove+(int)(cl.joystickAxis[AXIS_SIDE]*127.f/32767));
 cmd->forwardmove=ClampChar(cmd->forwardmove-(int)(cl.joystickAxis[AXIS_FORWARD]*127.f/32767));
 if(!(in_speed.active^cl_run->integer))cmd->buttons|=BUTTON_WALKING;
 cl.viewangles[YAW]-=cl.joystickAxis[AXIS_YAW]/32767.f*30*horizontal*dt;
 cl.viewangles[PITCH]+=cl.joystickAxis[AXIS_PITCH]/32767.f*30*vertical*dt*invert;
 return true;
}
