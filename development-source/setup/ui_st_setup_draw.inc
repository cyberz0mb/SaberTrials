static std::string SSUI_Lower(std::string s){for(char& c:s)c=tolower((unsigned char)c);return s;}
static void SSUI_Field(float x,float y,float w,const char* text,int id,int field,int setting=-1){
 UI_FillRect(x,y,w,23,scuPanel);SCUI_Border(x,y,w,23,ssui.field==field&&(field!=1||ssui.setting==setting)?scuCyan:scuLine);
 qboolean editing=ssui.field==field&&(field!=1||ssui.setting==setting);
 SCUI_Fit(x+5,y+5,w-10,.56f,editing?ssui.edit:text,scuText);SCUI_Hit(x,y,w,23,id,setting,0);
 if(editing&&((uiInfo.uiDC.realTime/400)&1)){char caret[2048];Q_strncpyz(caret,ssui.edit,sizeof(caret));caret[ssui.caret]=0;float cx=x+5+RUI_Width(caret,.56f);if(cx<x+w-5)UI_FillRect(cx,y+4,1,14,scuCyan);}
}
static std::string SSUI_Value(int i,stcReply_t r){
 if(!Q_stricmp(ssSettings[i].name,"r_mode")&&!strcmp(r.text,"-1")){auto w=SSUI_Call(101,2),h=SSUI_Call(101,3);return std::string(w.text)+" x "+h.text;}
 char choices[4096];SSUI_Choices(i,choices,sizeof(choices));char* p=choices;
 while(*p){char* end=strchr(p,'|');if(end)*end=0;char* eq=strchr(p,'=');if(eq){*eq=0;if(!strcmp(p,r.text))return eq+1;}if(!end)break;p=end+1;}
 return r.text;
}
#include "ui_st_chat_preview.inc"

static void SSUI_Setting(float x,float y,int i,bool compact){
 auto& s=ssSettings[i];auto r=SSUI_Call(101,i);const bool camera=s.tab==SSUI_CameraTab;
 const float offset=compact?112:camera?142:180,vx=x+offset,rowWidth=compact?238:286;
 const float labelWidth=offset-9;const float* color=r.c?scuMuted:scuText;
 SCUI_Fit(x+4,y+(compact?6:1),labelWidth,.61f,s.label,color);
 if(!compact){SCUI_Fit(x+4,y+14,labelWidth,.44f,s.name,scuCyan);SCUI_Fit(x+4,y+28,rowWidth-8,.45f,r.help,scuMuted);}
 std::string value=SSUI_Value(i,r);
 if(r.c){SCUI_Fit(vx+5,y+5,96,.53f,value.c_str(),scuMuted);}
 else if(s.kind==3){
  const float slider=compact?45:51,number=compact?39:49;
  float ratio=Com_Clamp(0,1,(r.number-s.low)/(s.high-s.low));UI_FillRect(vx,y+11,slider,2,scuLine);UI_FillRect(vx,y+11,slider*ratio,2,scuCyan);
  if(camera||SSUI_ChatSetting(i))UI_FillRect(vx+(slider-3)*ratio,y+6,3,12,scuCyan);
  SCUI_Hit(vx,y,slider,23,2400+i,i,0);
  SSUI_Field(vx+slider+5,y,number,r.text,2200+i,1,i);
 }else if(!s.choices[0])SSUI_Field(vx,y,s.kind==5?58:106,r.text,2200+i,1,i);
 else SCUI_Button(vx,y,camera?88:106,23,value.c_str(),2200+i,i,0,qfalse);
 if(camera&&!r.c)SCUI_Button(x+rowWidth-34,y,34,23,"Reset",3700+i,i,0,qfalse);
 UI_FillRect(x,y+(compact?26:40),rowWidth,1,scuLine);
}
static void SSUI_Scrollbar(float top=183,float bottom=410,float x=611){
 if(ssui.maxScroll<=0)return;const float w=12,c=x+w/2,button=22,gap=4,trackY=top+button+gap,trackH=bottom-button-gap-trackY;
 float visible=bottom-top,thumb=std::max(24.f,trackH*visible/(visible+ssui.maxScroll));
 for(int i=0;i<2;++i){float y=i?bottom-button:top;const char* a=i?"v":"^";vec4_t color;MSUI_Color(color,false,SCUI_Over(x,y,w,button)||(!scui.pointerMode&&ssui.focus==2800+i));SCUI_Text(c-RUI_Width(a,.5f)/2,y+6,.5f,a,color);SCUI_Hit(x,y,w,button,2800+i,0,0);}
 stmenu::configure(ssui.scrollbar,x,trackY,w,trackH,visible,ssui.maxScroll);
 UI_FillRect(c-2,trackY,4,trackH,scuLine);UI_FillRect(c-3,trackY+(trackH-thumb)*ssui.scroll/ssui.maxScroll,6,thumb,scuCyan);
}
static void SSUI_DrawSettings(){
 const bool compact=SSUI_CameraView();
 const int columns=compact?1:2, rowHeight=compact?29:43;
 float top=ssui.tab==0?211:183,bottom=410;std::vector<int> rows;std::vector<std::pair<std::string,float>> groups;float y=top;
 for(int i=0;i<SS_COUNT;++i)ssui.itemY[i]=-1;
 for(int i=0;i<SS_COUNT;){
  if(ssSettings[i].tab!=ssui.tab){++i;continue;}std::string group=ssSettings[i].group;groups.push_back({group,y});y+=24;int n=0;
  const int groupColumns=group=="Chat"?1:columns;
  while(i<SS_COUNT&&ssSettings[i].tab==ssui.tab&&group==ssSettings[i].group){
   if(group!="Advanced video"||ssui.advanced){ssui.itemY[i]=(int)(y+(n/groupColumns)*rowHeight);rows.push_back(i);++n;}++i;
  }y+=((n+groupColumns-1)/groupColumns)*rowHeight+9;
 }
 ssui.maxScroll=std::max(0,(int)(y-bottom-11));
 if(ssui.scroll<0){ssui.scroll=SSUI_ChatSetting(ssui.setting)?0:std::max(0,ssui.itemY[ssui.setting]-(int)top);}
 ssui.scroll=std::max(0,std::min(ssui.maxScroll,ssui.scroll));
 if(ssui.tab==0){SCUI_Button(20,181,100,22,"Performance",2910,0,0,qfalse);SCUI_Button(126,181,100,22,"Balanced",2911,0,0,qfalse);SCUI_Button(232,181,100,22,"Quality",2912,0,0,qfalse);SCUI_Button(510,181,98,22,"Driver info",2906,0,0,qfalse);}
 for(auto& g:groups){float gy=g.second-ssui.scroll;if(gy>=top&&gy+22<=bottom){if(g.first=="Advanced video")SCUI_Button(20,gy,588,22,ssui.advanced?"-  Advanced video":"+  Advanced video",2907,0,0,qfalse);else SCUI_Text(24,gy+4,.62f,g.first.c_str(),scuMuted);}}
 int col=0;std::string previous;
 const bool chatPreview=ssui.tab==2&&ssui.scroll<110;
 for(int i:rows){
  if(previous!=ssSettings[i].group){previous=ssSettings[i].group;col=0;}
  const float ry=ssui.itemY[i]-ssui.scroll;
  const bool chat=SSUI_ChatSetting(i);
  const int column=chat?0:col%columns;
  if(ry>=top&&ry+rowHeight-2<=bottom&&!(chatPreview&&column))SSUI_Setting(20+column*302,ry,i,compact);
  ++col;
 }
 if(chatPreview)SSUI_ChatPreview();
 SSUI_Scrollbar(top,bottom,compact?259.f:611.f);
 if(compact)UI_FillRect(273,183,1,245,scuLine);
 if(ssui.tab==5){
  uiClientState_t state;trap->GetClientState(&state);char player[MAX_INFO_STRING];trap->GetConfigString(CS_PLAYERS+state.clientNum,player,sizeof(player));
  if(state.connState==CA_ACTIVE&&atoi(Info_ValueForKey(player,"t"))==TEAM_SPECTATOR){SCUI_Button(20,412,100,18,"Free Camera",2920,0,0,qfalse);SCUI_Button(126,412,100,18,"Previous Player",2921,0,0,qfalse);SCUI_Button(232,412,100,18,"Next Player",2922,0,0,qfalse);}
 }
}
static void SSUI_DrawSearch(){
 std::vector<int> matches;std::string query=SSUI_Lower(ssui.search);
 for(int i=0;i<SS_COUNT;++i){auto& s=ssSettings[i];if(SSUI_Lower(std::string(s.label)+" "+s.name+" "+s.help).find(query)!=std::string::npos)matches.push_back(i);}
 ssui.maxScroll=std::max(0,((int)matches.size()-6)*34);ssui.scroll=std::min(ssui.scroll,ssui.maxScroll);
 int start=ssui.scroll/34;
 for(int n=0;n<6&&start+n<(int)matches.size();++n){int i=matches[start+n];float y=183+n*36;char label[256];Com_sprintf(label,sizeof(label),"%s  >  %s",ssTabs[ssSettings[i].tab],ssSettings[i].label);SCUI_Button(20,y,588,29,label,2600+i,i,0,qfalse);}
 if(matches.empty())SCUI_Text(24,190,.6f,"No matching settings.",scuMuted);SSUI_Scrollbar();
}
static void SSUI_DrawConfigs(){
 SSUI_Field(20,151,272,ssui.filename,2102,3);SCUI_Text(298,156,.55f,".cfg",scuMuted);SCUI_Button(450,151,170,23,"Save current settings",3100,0,0,qfalse);
 auto path=SSUI_Call(STC_STATE);SCUI_Fit(20,182,600,.43f,path.text,scuMuted);
 auto r=SSUI_Call(STC_ROWS,STC_CONFIGS,-1);int count=r.count;ssui.maxScroll=std::max(0,(count-12)*21);ssui.scroll=std::min(ssui.scroll,ssui.maxScroll);
 int start=ssui.scroll/21;
 for(int i=0;i<12&&start+i<count;++i){r=SSUI_Call(STC_ROWS,STC_CONFIGS,start+i);float x=20+(i/6)*302,y=207+(i%6)*29;SCUI_Fit(x+4,y+5,225,.56f,r.label,scuText);SCUI_Button(x+237,y,49,24,"Load",3000+i,i,0,qfalse);}
 if(!count)SCUI_Text(24,218,.6f,"No saved personal configs.",scuMuted);SSUI_Scrollbar(207,405);
}
static void SSUI_DrawModal(){
 if(!ssui.modal)return;scui.hitsCount=0;UI_FillRect(45,135,550,288,scuInk);ssui.scrollbar.dragging=false;
 const char* title=ssui.modal==1?"Discard pending changes?":ssui.modal==2?"Reset this tab?":ssui.modal==3?"Replace saved config?":ssui.modal==4?"Replace pending config edits?":ssui.modal==6?"Keep display changes?":ssui.modal==7?"Installed mods":ssui.modal==9?"Switch mod?":"Driver information";
 SCUI_Text(65,152,.78f,title,scuCyan);
 if(ssui.modal==6){auto state=SSUI_Call(106);char msg[100];Com_sprintf(msg,sizeof(msg),"Reverting in %d seconds.",state.a);SCUI_Text(65,192,.62f,msg,scuText);SCUI_Button(65,373,130,26,"Revert",3202,0,0,qfalse);SCUI_Button(425,373,150,26,"Keep changes",3201,0,0,qtrue);return;}
 if(ssui.modal==7){
  if(!uiInfo.modCount)UI_LoadMods();int n=std::min(8,uiInfo.modCount);ssui.modalScroll=std::min(ssui.modalScroll,std::max(0,uiInfo.modCount-8));for(int i=0;i<n;++i){int index=ssui.modalScroll+i;SCUI_Button(65,187+i*23,510,21,uiInfo.modList[index].modDescr,3400+i,index,0,qfalse);}
  SCUI_Button(65,389,100,23,"Close",3200,0,0,qfalse);if(uiInfo.modCount>8){SCUI_Button(365,389,100,23,"Previous",3600,0,0,qfalse);SCUI_Button(475,389,100,23,"Next",3601,0,0,qfalse);}return;
 }
 if(ssui.modal==9){SCUI_Fit(65,195,510,.64f,uiInfo.modList[ssui.modIndex].modDescr,scuText);SCUI_Text(65,230,.55f,"This restarts the game client.",scuMuted);SCUI_Button(65,373,120,26,"Cancel",3200,0,0,qfalse);SCUI_Button(425,373,150,26,"Switch mod",3500,0,0,qtrue);return;}
 if(ssui.modal==8){glconfig_t config;trap->GetGlconfig(&config);SCUI_Fit(65,192,510,.55f,config.renderer_string,scuText);SCUI_Fit(65,223,510,.55f,config.vendor_string,scuText);SCUI_Fit(65,254,510,.55f,config.version_string,scuText);SCUI_Button(65,373,120,26,"Close",3200,0,0,qfalse);return;}
 SCUI_Fit(65,195,510,.61f,ssui.modal==2?ssTabs[ssui.tab]:ssui.modal==3?ssui.filename:ssui.modal==4?ssui.loadname:"Return to editing to keep your pending changes.",scuText);
 SCUI_Button(65,373,120,26,"Cancel",3200,0,0,qfalse);SCUI_Button(425,373,150,26,ssui.modal==1?"Discard":ssui.modal==2?"Stage defaults":"Confirm",3201,0,0,qtrue);
}
static void SSUI_Draw(){
 auto display=SSUI_Call(106);
 if((display.b||display.number)&&!SSUI_IsMenu()){
  if(display.c)UI_LoadMenus("ui/jampingame.txt",qtrue);
  Menus_ActivateByName(display.c?"ingame_setup":"setup_menu");trap->Key_SetCatcher(KEYCATCH_UI);ssui.active=0;
 }
 if(!SSUI_IsMenu()){if(ssui.active)SSUI_End();return;}
 if(!ssui.active||Q_stricmp(ssui.menu,Menu_GetFocused()->window.name))SSUI_Start();
 if(display.b)ssui.modal=6;else if(ssui.modal==6)ssui.modal=0;
 SSUI_Call(115,SSUI_CameraView());
 scui.hitsCount=0;scui.focus=ssui.focus;ssui.scrollbar.visible=false;RUI_Shell();
 if(!SSUI_Ingame()){const char* nav[]={"Play","Profile","Controls","Setup"};for(int i=0;i<4;++i){float x=211+i*67;vec4_t color;MSUI_Color(color,i==3,SCUI_Over(x,17,64,26)||(!scui.pointerMode&&ssui.focus==3300+i));SCUI_Text(x+4,23,.67f,nav[i],color);if(i!=3)SCUI_Hit(x,17,64,26,3300+i,i,0);else RUI_Control(x,42,62,2,"tab",true,false);}}
 SCUI_Text(35,72,1.18f,ssui.manager?"Saved Configs":"Setup",scuText);
 if(!ssui.manager){float x=20;const float widths[]={64,64,82,100,82,93,73};for(int i=0;i<SSUI_TabCount;++i){SCUI_Button(x,119,widths[i],23,ssTabs[i],2000+i,i,0,ssui.tab==i);x+=widths[i]+6;}SSUI_Field(20,151,600,ssui.search[0]?ssui.search:"Search Setup settings or console names...",2100,2);if(ssui.search[0])SSUI_DrawSearch();else SSUI_DrawSettings();}
 else SSUI_DrawConfigs();
 UI_FillRect(20,433,600,1,scuLine);SCUI_Fit(20,422,600,.47f,ssui.status[0]?ssui.status:SSUI_Dirty()?"Unsaved changes":"",scuGold);
 SCUI_Button(20,443,56,22,"Back",2900,0,0,qfalse);
 if(!ssui.manager){SCUI_Button(82,443,92,22,"Reset this tab",2903,0,0,qfalse);SCUI_Button(180,443,48,22,"Mods",2905,0,0,qfalse);SCUI_Button(234,443,96,22,"Saved Configs",2904,0,0,qfalse);}
 SCUI_Button(390,443,110,22,"Cancel changes",2901,0,0,qfalse);SCUI_Button(506,443,114,22,"Apply changes",2902,0,0,qtrue);
 SSUI_DrawModal();
}
