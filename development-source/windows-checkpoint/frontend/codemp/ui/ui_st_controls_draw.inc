/* Native presentation of the approved Controls design. Coordinates are 640x480. */
static const char* scuSettingLabels[]={
 "Sensitivity","Acceleration","Invert mouse","Smoothing","Horizontal turn speed",
 "Vertical look speed","Turn-speed modifier","Horizontal scale","Acceleration curve",
 "Acceleration offset","Always run","Free mouse look","Forward movement scale",
 "Strafe movement scale","Mouse input mode","Release window capture","Legacy joystick",
 "Analog joystick axes","Joystick deadzone","Enable controller","Horizontal sensitivity",
 "Vertical sensitivity","Stick deadzone","Invert vertical look","Button labels"
};
static const char* scuSettingHelp[]={
 "Overall mouse response.","Zero disables acceleration.","Negative m_pitch inverts vertical look.","Average mouse movement between frames.",
 "Turning with bound left / right keys.","Looking with bound up / down keys.","Multiplier while walk / run is held.",
 "Scale horizontal mouse movement.","Legacy or power acceleration.","Offset used by the power curve.","Default movement speed.",
 "Move the mouse to look around.","Mouse movement when free look is off.","Mouse movement while strafing.",
 "Changing this restarts mouse input.","Release capture in windowed mode.","Older joystick path; restarts input.",
 "Use analog axes on the legacy path.","Ignore small legacy axis movements.","Use normalized gamepad input.",
 "Right-stick horizontal look speed.","Right-stick vertical look speed.","Ignore small stick movements.",
 "Reverse right-stick vertical look.","Labels do not change assignments."
};
static void SCUI_Setting(float x,float y,float w,int row,stcReply_t r,qboolean basic){
 const char* value=r.text;float vx=x+w-106;
 SCUI_Fit(x+4,y+2,w-114,.62f,r.a==2&&!basic?"Vertical mouse scale":scuSettingLabels[r.a],scuText);
 SCUI_Fit(x+4,y+15,w-114,.46f,r.name,scuCyan);
 SCUI_Fit(x+4,y+29,w-8,.48f,scuSettingHelp[r.a],scuMuted);
 if(r.b==1)value=r.number?"On":"Off";
 if(r.a==24)value=r.number==1?"PlayStation":r.number==2?"Generic":"Xbox";
 if(r.a==14)value=r.number==0?"Off":r.number==2?"Compat.":"Raw";
 if(r.a==8)value=r.number?"Power":"Legacy";
 if(r.a==2){
  if(basic)value=r.number<0?"On":"Off";
 }
 if(r.b==3){
  float low=r.a==22?0:1,high=r.a==22?.95f:10,ratio=Com_Clamp(0,1,(r.number-low)/(high-low));

  UI_FillRect(vx,y+13,45,2,scuLine);UI_FillRect(vx,y+13,45*ratio,2,scuCyan);
  SCUI_Hit(vx,y,45,24,600+row,r.a,3);SCUI_Fit(vx+48,y+6,22,.49f,value,scuText);
 }else if(scui.field==11&&!strcmp(scui.fieldName,r.name))SCUI_Field(vx,y,64,r.text,11,r.a,r.name);
 else if(r.b==0&&!(r.a==2&&basic)){UI_FillRect(vx,y,64,24,scuPanel);SCUI_Border(vx,y,64,24,scuLine);SCUI_Fit(vx+6,y+6,52,.57f,value,scuText);SCUI_Hit(vx,y,64,24,600+row,r.a,r.b);}
 else SCUI_Button(vx,y,64,24,value,600+row,r.a,r.b,qfalse);
 SCUI_Button(x+w-36,y,36,24,"Reset",700+row,r.a,0,qfalse);
 UI_FillRect(x,y+42,w,1,scuLine);
}
static void SCUI_Group(float x,float y,float w,const char* text,int group,qboolean open){
 char label[128];Com_sprintf(label,sizeof(label),"%s  %s",open?"-":"+",text);
 SCUI_Button(x,y,w,22,label,1900+group,group,0,qfalse);
}
static void SCUI_MouseScrollbar(void){
 const float x=611,w=12,center=x+w/2,top=177,bottom=411,buttonH=22,gap=4;
 const float trackY=top+buttonH+gap,trackH=bottom-buttonH-gap-trackY;
 const float thumbH=trackH*(bottom-top)/(bottom-top+127);
 for(int i=0;i<2;++i){
  float y=i?bottom-buttonH:top;int id=i?1921:1920;const char* arrow=i?"v":"^";
  vec4_t color;MSUI_Color(color,false,SCUI_Over(x,y,w,buttonH)||(!scui.pointerMode&&scui.focus==id));
  SCUI_Text(center-RUI_Width(arrow,.5f)/2,y+6,.5f,arrow,color);
  SCUI_Hit(x,y,w,buttonH,id,0,0);
 }
 stmenu::configure(scui.scrollbar,x,trackY,w,trackH,bottom-top,127);
 UI_FillRect(center-2,trackY,4,trackH,scuLine);
 UI_FillRect(center-3,trackY+(trackH-thumbH)*scui.mouseScroll/127.f,6,thumbH,scuCyan);
}
static void SCUI_Draw(void){
 int i,count=0,scope=STC_ACTIONS,per=SCUI_PageSize();stcReply_t r;char line[256];
 float left=20,width=600,start=187;
 if(!SCUI_IsMenu()){if(scui.active){SCUI_Call(STC_CANCEL,0,0,0,NULL,NULL);scui.active=0;}return;}
 if(!scui.active||Q_stricmp(scui.menu,Menu_GetFocused()->window.name))SCUI_Start();
 scui.hitsCount=0;scui.scrollbar.visible=false;RUI_Shell();
 if(!Q_stricmp(scui.menu,"controlsMenu")){
  const char* nav[]={"Play","Profile","Controls","Setup"};
  for(i=0;i<4;++i){float x=211+i*67;vec4_t color;MSUI_Color(color,i==2,SCUI_Over(x,17,64,26)||(!scui.pointerMode&&scui.focus==1800+i));SCUI_Fit(x+4,23,60,.67f,nav[i],color);SCUI_Hit(x,17,64,26,1800+i,i,0);if(i==2)RUI_Control(x,42,62,2,"tab",true,false);}
 }
 SCUI_Text(35,72,1.18f,"Controls",scuText);
 SCUI_Text(35,99,.52f,"Fine-tune input settings without typing console commands.",scuMuted);
 {float x=20;static float widths[]={85,61,111,47,73,90,85};for(i=0;i<7;++i){SCUI_Button(x,119,widths[i],23,scuTabs[i],100+i,i,0,scui.tab==i);x+=widths[i]+3;}}
 scope=scui.tab==0?STC_ACTIONS:scui.tab==1?STC_BINDLIST:scui.tab==2?STC_SERVER:scui.tab==6?STC_CONFIGS:scui.tab==4&&scui.cat==99?STC_PAD:STC_SETTINGS;
 if(scui.tab==0){left=153;width=467;for(i=0;i<7;++i)SCUI_Button(20,183+i*27,120,23,scuCats[i],200+i,i,0,scui.cat==i);}
 if(scope==STC_ACTIONS||scope==STC_BINDLIST||scope==STC_SERVER||scui.tab==5)
  SCUI_Field(left,152,width,scui.search[0]?scui.search:scope==STC_BINDLIST?"Search current keys or commands...":scui.tab==5?"Search input settings or console names...":"Search actions...",10,0,NULL);
 if(scope==STC_SETTINGS){
  const char* group=scui.tab==3?"Mouse":scui.tab==4?"Controller":"Advanced";
  r=SCUI_Row(scope,-1,group);count=r.count;scui.page=0;
  if(scui.tab==3){
   float sy=177-scui.mouseScroll;int extra=0;
   if(!scui.mouseScroll)SCUI_Text(22,153,.65f,"Basic Settings",scuText);
   for(i=0;i<4;++i){r=SCUI_Row(scope,i,group);float y=sy+(i/2)*47;if(y>=177&&y+43<=411)SCUI_Setting(20+(i%2)*302,y,286,i,r,qtrue);}
   sy+=101;
   if(sy>=177&&sy+22<=411)SCUI_Group(20,sy,588,"Advanced settings",0,(scui.fold[3]&1)!=0);
   if(scui.fold[3]&1){
    for(i=4;i<count;++i){r=SCUI_Row(scope,i,group);float y=sy+29+(extra/2)*47;if(y>=177&&y+43<=411)SCUI_Setting(20+(extra%2)*302,y,286,i,r,qfalse);++extra;}
    r=SCUI_Row(scope,2,group);{float y=sy+29+4*47;if(y>=177&&y+43<=411)SCUI_Setting(20,y,286,12,r,qfalse);}
    SCUI_MouseScrollbar();
   }
  }else{
   int rows[2]={0,0};const char* titles[2];float top=scui.tab==4?198:184;
   if(scui.tab==4){char device[256];trap->Cvar_VariableStringBuffer("st_controllerDevice",device,sizeof(device));SCUI_Fit(20,150,600,.48f,device,scuMuted);SCUI_Button(20,167,130,22,"Sensitivity / settings",410,0,0,qtrue);SCUI_Button(156,167,130,22,"Button mapping",411,0,0,qfalse);SCUI_Button(450,167,170,22,"Stage controller defaults",412,0,0,qfalse);titles[0]="Look and movement";titles[1]="Device preferences";}
   else {titles[0]="Keyboard turning";titles[1]="Movement and legacy input";}
   for(i=0;i<2;++i)SCUI_Text(24+i*302,top+5,.62f,titles[i],scuMuted);
   for(i=0;i<count;++i){int col;r=SCUI_Row(scope,i,group);col=scui.tab==4?(r.a>=20&&r.a<=22?0:1):(r.a>=4&&r.a<=6?0:1);SCUI_Setting(20+col*302,top+29+rows[col]*44,286,i,r,qfalse);++rows[col];}
   if(!count)SCUI_Text(24,top+35,.6f,"No matching settings.",scuMuted);
  }
 }else{
  int columns=scope==STC_ACTIONS?1:2,rows=per/columns;float cw;
  const char* group=scui.tab==0?scuCats[scui.cat>6?0:scui.cat]:NULL;
  if(scope==STC_CONFIGS){SCUI_Field(20,156,245,scui.filename,12,0,NULL);SCUI_Text(270,161,.56f,".cfg",scuMuted);SCUI_Button(440,156,180,22,"Save current settings",400,0,0,qfalse);r=SCUI_Call(STC_STATE,0,0,0,NULL,NULL);SCUI_Fit(20,185,600,.45f,r.text,scuMuted);SCUI_Text(20,200,.47f,"Load into the editor for review, then Apply.",scuMuted);start=223;}
  if(scope==STC_PAD){SCUI_Button(20,153,130,22,"Sensitivity / settings",410,0,0,qfalse);SCUI_Button(156,153,130,22,"Button mapping",411,0,0,qtrue);SCUI_Button(450,153,170,22,"Stage controller defaults",412,0,0,qfalse);start=187;}
  r=SCUI_Row(scope,-1,group);count=r.count;
  if(scui.modal!=3&&scui.page*per>=count)scui.page=count?(count-1)/per:0;
  cw=(width-(columns-1)*14)/columns;
  if(scope==STC_ACTIONS||scope==STC_SERVER){for(i=0;i<columns;++i){
   float x=left+i*(cw+14),kw=scope==STC_ACTIONS?70:57;
   SCUI_Text(x+6,176,.45f,"Action",scuMuted);
   SCUI_Centered(x+cw-kw*2-4,172,kw,16,.45f,"Primary",scuMuted);
   SCUI_Centered(x+cw-kw,172,kw,16,.45f,"Secondary",scuMuted);
  }}
  for(i=0;i<per&&scui.page*per+i<count;++i){float x=left+(i/rows)*(cw+14),y=start+(i%rows)*21;r=SCUI_Row(scope,scui.page*per+i,group);UI_FillRect(x,y,cw,20,scuPanel);
   if(scope==STC_ACTIONS||scope==STC_SERVER){char key[64];float kw=scope==STC_ACTIONS?70:57;SCUI_Button(x,y,cw-kw*2-8,20,r.label,300+i,r.a,0,qfalse);if(r.b>=0)trap->Key_KeynumToStringBuf(r.b,key,sizeof(key));else Q_strncpyz(key,"--",sizeof(key));SCUI_Button(x+cw-kw*2-4,y,kw,20,key,500+i,r.a,0,qfalse);if(r.c>=0)trap->Key_KeynumToStringBuf(r.c,key,sizeof(key));else Q_strncpyz(key,"--",sizeof(key));SCUI_Button(x+cw-kw,y,kw,20,key,550+i,r.a,1,qfalse);}
   else if(scope==STC_BINDLIST){SCUI_Button(x,y,80,20,r.label,800+i,r.a,0,qfalse);SCUI_Fit(x+87,y+6,cw-129,.55f,r.text,scuText);SCUI_Button(x+cw-35,y,35,20,"Edit",900+i,r.a,r.b,qfalse);}
   else if(scope==STC_CONFIGS){SCUI_Fit(x+5,y+6,cw-55,.55f,r.label,scuText);SCUI_Button(x+cw-46,y,46,20,"Load",1000+i,r.a,0,qfalse);}
   else if(scope==STC_PAD){SCUI_Fit(x+5,y+6,99,.55f,r.label,scuText);SCUI_Button(x+105,y,cw-105,20,r.text[0]?r.text:"Unassigned",1100+i,r.a,0,qfalse);}
  }
  if(!count)SCUI_Text(left+4,start+12,.6f,"No matching entries.",scuMuted);
  else {Com_sprintf(line,sizeof(line),"%d-%d of %d",scui.page*per+1,(scui.page+1)*per<count?(scui.page+1)*per:count,count);SCUI_Text(left,407,.49f,line,scuMuted);}
  if(count>per){SCUI_Button(left+width-154,401,72,22,"Previous",1200,0,0,qfalse);SCUI_Button(left+width-76,401,72,22,"Next",1201,count,0,qfalse);}
 }
 RUI_Divider(20,433,600);
 SCUI_Fit(20,422,600,.48f,scui.status[0]?scui.status:scui.tab==5?"Network / FPS settings belong under Setup > Network.":"",scui.dirty?scuGold:scuMuted);
 SCUI_Button(20,443,56,22,"Back",1300,0,0,qfalse);
 SCUI_Text(86,449,.52f,scui.dirty?"Unsaved changes":"No pending changes",scui.dirty?scuGold:scuMuted);
 SCUI_Button(390,443,110,22,"Cancel changes",1301,0,0,qfalse);SCUI_Button(506,443,114,22,"Apply changes",1302,0,0,qtrue);
 #include "ui_st_controls_modals.inc"
}
