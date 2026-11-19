// Windows exposes attached physical and virtual keyboard devices through Raw Input.
static void ST_UpdatePhysicalKeyboard() {
 static cvar_t* detected=Cvar_Get("st_physicalKeyboard","1",CVAR_ROM);
 static unsigned next=0;
 const unsigned now=Sys_Milliseconds();
 if(next&&(int)(now-next)<0)return;
 next=now+1000;
#ifdef _WIN32
 UINT count=0;
 if(GetRawInputDeviceList(NULL,&count,sizeof(RAWINPUTDEVICELIST))!=(UINT)0)return;
 std::vector<RAWINPUTDEVICELIST> devices(count);
 if(count&&GetRawInputDeviceList(devices.data(),&count,sizeof(RAWINPUTDEVICELIST))==(UINT)-1)return;
 bool present=false;
 for(UINT i=0;i<count;++i)if(devices[i].dwType==RIM_TYPEKEYBOARD){present=true;break;}
 if(detected->integer!=int(present))Cvar_SetValue("st_physicalKeyboard",present?1:0);
#else
 (void)detected;
#endif
}
