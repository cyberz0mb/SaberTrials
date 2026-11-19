// Native Setup interaction; paints through the accepted Controls primitives.
#include "st_setup_catalog.h"
#include <string>
#include <vector>
#include <algorithm>
static struct {int active,tab,manager,modal,field,caret,replace,focus,scroll,maxScroll,destination,dirty,drag,setting,advanced,modIndex,mouseActivation,modalScroll;stmenu::Scrollbar scrollbar;float sliderX,sliderW;char menu[64],search[80],edit[2048],filename[64],status[4096],loadname[128];int itemY[SS_COUNT];} ssui;
static const char* ssTabs[]={"Video","Sound","Interface","Game Options","Network","Recording","Camera"};
static const int SSUI_TabCount=sizeof(ssTabs)/sizeof(ssTabs[0]), SSUI_CameraTab=SSUI_TabCount-1;
static stcReply_t SSUI_Call(int op,int a=0,int b=0,int c=0,const char* name=NULL,const char* text=NULL){stcRequest_t q={};stcReply_t r={};q.op=op;q.a=a;q.b=b;q.c=c;if(name)Q_strncpyz(q.name,name,sizeof(q.name));if(text)Q_strncpyz(q.text,text,sizeof(q.text));trap->Controls(&q,&r);return r;}
static void SSUI_Status(stcReply_t r){Q_strncpyz(ssui.status,r.text,sizeof(ssui.status));}
static qboolean SSUI_IsMenu(){menuDef_t* m=Menu_GetFocused();return m&&(!Q_stricmp(m->window.name,"setup_menu")||!Q_stricmp(m->window.name,"ingame_setup"));}
static qboolean SSUI_Ingame(){return !Q_stricmp(ssui.menu,"ingame_setup");}
static bool SSUI_CameraView(){
 return ssui.active&&SSUI_IsMenu()&&SSUI_Ingame()&&ssui.tab==SSUI_CameraTab&&!ssui.manager&&!ssui.search[0]&&!ssui.modal&&RUI_Connected();
}
static int SSUI_Dirty(){return SSUI_Call(ssui.manager?STC_STATE:106).dirty;}
static void SSUI_Start(){menuDef_t* m=Menu_GetFocused();memset(&ssui,0,sizeof(ssui));ssui.active=1;ssui.setting=-1;ssui.focus=2000;ssui.destination=-99;Q_strncpyz(ssui.menu,m->window.name,sizeof(ssui.menu));SSUI_Call(100);}
static qboolean SSUI_Commit(){
 if(!ssui.field)return qtrue;
 if(ssui.field==1){auto r=SSUI_Call(102,ssui.setting,0,0,ssSettings[ssui.setting].name,ssui.edit);if(r.status<0){SSUI_Status(r);return qfalse;}}
 if(ssui.field==2)Q_strncpyz(ssui.search,ssui.edit,sizeof(ssui.search));
 if(ssui.field==3)Q_strncpyz(ssui.filename,ssui.edit,sizeof(ssui.filename));
 ssui.field=0;return qtrue;
}
static void SSUI_Edit(int field,const char* value,int setting=-1){ssui.field=field;ssui.setting=setting;ssui.replace=field!=2;Q_strncpyz(ssui.edit,value,sizeof(ssui.edit));ssui.caret=strlen(ssui.edit);}
static void SSUI_End(){SSUI_Call(ssui.manager?STC_CANCEL:104);ssui.active=0;ssui.field=0;}
static void SSUI_Go(int destination){
 if(destination==-2){ssui.manager=0;ssui.modal=0;ssui.status[0]=0;ssui.scroll=0;SSUI_Call(100);return;}
 if(destination==-3){SSUI_Call(109);ssui.manager=1;ssui.modal=0;ssui.status[0]=0;ssui.scroll=0;ssui.search[0]=0;return;}
 qboolean ingame=SSUI_Ingame();char old[64];Q_strncpyz(old,ssui.menu,sizeof(old));SSUI_End();Menus_CloseByName(old);
 if(destination>=0){const char* menus[]={"multiplayermenu","playerMenu","controlsMenu","setup_menu"};Menus_OpenByName(ingame&&destination==2?"ingame_controls":menus[destination]);}
 else if(!ingame)Menus_OpenByName("main");
}
static void SSUI_Navigate(int destination){if(!SSUI_Commit())return;ssui.destination=destination;if(SSUI_Dirty())ssui.modal=1;else SSUI_Go(destination);}
static void SSUI_FromControls(){qboolean ingame=!Q_stricmp(scui.menu,"ingame_controls");SCUI_Call(STC_CANCEL,0,0,0,NULL,NULL);scui.active=0;Menus_CloseByName(scui.menu);Menus_OpenByName(ingame?"ingame_setup":"setup_menu");SSUI_Start();SSUI_Go(-3);}
static void SSUI_Choices(int i,char* out,int size){
 Q_strncpyz(out,ssSettings[i].choices,size);
 if(!Q_stricmp(ssSettings[i].name,"se_language")){
  out[0]=0;for(int n=0;n<trap->SE_GetNumLanguages();++n){char language[128],item[280];trap->SE_GetLanguageName(n,language);Com_sprintf(item,sizeof(item),"%s%s=%s",n?"|":"",language,language);Q_strcat(out,size,item);}
 }
 if(!Q_stricmp(ssSettings[i].name,"r_mode")){
  // Query the driver's real list. Modes use -1 plus explicit dimensions.
  Q_strncpyz(out,"-2=Desktop|-1=Custom",size);
  char modes[4096];trap->Cvar_VariableStringBuffer("r_availableModes",modes,sizeof(modes));char* p=modes;
  while(*p){int w=0,h=0;if(sscanf(p,"%dx%d",&w,&h)==2){char item[64];Com_sprintf(item,sizeof(item),"|%dx%d=%d x %d",w,h,w,h);Q_strcat(out,size,item);}while(*p&&*p!=' ')++p;while(*p==' ')++p;}
 }
}
static void SSUI_Cycle(int i){
 auto r=SSUI_Call(101,i);if(r.c){SSUI_Status(r);return;}char choices[4096];SSUI_Choices(i,choices,sizeof(choices));
 char* p=choices;char first[128]={},next[128]={};qboolean found=qfalse;
 std::string current=r.text;
 if(!Q_stricmp(ssSettings[i].name,"r_mode")&&!strcmp(r.text,"-1")){
  auto w=SSUI_Call(101,2),h=SSUI_Call(101,3);current=std::string(w.text)+"x"+h.text;
 }
 while(*p){char* end=strchr(p,'|');if(end)*end=0;char* eq=strchr(p,'=');if(eq)*eq=0;if(!*first)Q_strncpyz(first,p,sizeof(first));if(found){Q_strncpyz(next,p,sizeof(next));break;}if(current==p)found=qtrue;if(!end)break;p=end+1;}
 if(!*next)Q_strncpyz(next,first,sizeof(next));
 if(!Q_stricmp(ssSettings[i].name,"r_mode")&&strchr(next,'x')){
  int w,h;sscanf(next,"%dx%d",&w,&h); // Stage custom dimensions before the Custom switch.
  auto mode=SSUI_Call(102,0,0,0,"r_mode","-1");if(mode.status<0){SSUI_Status(mode);return;}
  char value[32];Com_sprintf(value,sizeof(value),"%d",w);SSUI_Call(102,0,0,0,"r_customwidth",value);Com_sprintf(value,sizeof(value),"%d",h);SSUI_Status(SSUI_Call(102,0,0,0,"r_customheight",value));
 }else SSUI_Status(SSUI_Call(102,i,0,0,ssSettings[i].name,next));
}
static void SSUI_Click(stcHit_t h){
 qboolean sameField=(h.id==2100&&ssui.field==2)||(h.id==2102&&ssui.field==3)||(ssui.field==1&&h.id==2200+ssui.setting);
 if(sameField){ssui.focus=h.id;return;}
 if(h.id!=2901&&h.id!=3200&&h.id!=3202&&!SSUI_Commit())return;
 int id=h.id;ssui.focus=id;
 if(id>=2000&&id<2000+SSUI_TabCount){ssui.tab=id-2000;ssui.manager=0;ssui.scroll=0;ssui.search[0]=0;ssui.status[0]=0;}
 else if(id==2100)SSUI_Edit(2,ssui.search);
 else if(id==2101)SSUI_Edit(1,SSUI_Call(101,h.a).text,h.a);
 else if(id==2102)SSUI_Edit(3,ssui.filename);
 else if(id>=2200&&id<2200+SS_COUNT){auto r=SSUI_Call(101,h.a);if(r.c){SSUI_Status(r);return;}if(ssSettings[h.a].choices[0])SSUI_Cycle(h.a);else SSUI_Edit(1,r.text,h.a);}
 else if(id>=2400&&id<2400+SS_COUNT){auto r=SSUI_Call(101,h.a);if(!r.c){ssui.drag=ssui.mouseActivation;ssui.setting=h.a;ssui.sliderX=h.x;ssui.sliderW=h.w;}}
 else if(id>=2600&&id<2600+SS_COUNT){ssui.tab=ssSettings[h.a].tab;ssui.advanced=1;ssui.search[0]=0;ssui.field=0;ssui.scroll=-1;ssui.setting=h.a;ssui.focus=2200+h.a;}
 else if(id==2800)ssui.scroll=std::max(0,ssui.scroll-43);
 else if(id==2801)ssui.scroll=std::min(ssui.maxScroll,ssui.scroll+43);
 else if(id==2900)SSUI_Navigate(ssui.manager?-2:-1);
 else if(id==2901){SSUI_Call(ssui.manager?109:104);ssui.field=0;ssui.status[0]=0;}
 else if(id==2902)SSUI_Status(SSUI_Call(ssui.manager?112:103,SSUI_Ingame()));
 else if(id==2903)ssui.modal=2;
 else if(id==2904)SSUI_Navigate(-3);
 else if(id==2905){if(SSUI_Dirty()){Q_strncpyz(ssui.status,"Apply or cancel pending edits before switching mods.",sizeof(ssui.status));}else ssui.modal=7;}
 else if(id==2906)ssui.modal=8;
 else if(id==2907)ssui.advanced=!ssui.advanced;
 else if(id>=2910&&id<=2912)SSUI_Status(SSUI_Call(113,id-2910));
 else if(id>=2920&&id<=2922){const char* commands[]={"follow\n","followprev\n","follownext\n"};trap->Cmd_ExecuteText(EXEC_APPEND,commands[id-2920]);Menus_CloseAll();trap->Key_SetCatcher(0);}
 else if(id>=3000&&id<3012){auto r=SSUI_Call(STC_ROWS,STC_CONFIGS,ssui.scroll/21+id-3000);Q_strncpyz(ssui.loadname,r.text,sizeof(ssui.loadname));r=SSUI_Call(111,0,0,0,NULL,ssui.loadname);SSUI_Status(r);if(r.status==2)ssui.modal=4;}
 else if(id==3100){auto r=SSUI_Call(110,0,0,0,NULL,ssui.filename);SSUI_Status(r);if(r.status==2)ssui.modal=3;}
 else if(id==3200){ssui.modal=0;}
 else if(id==3201){int m=ssui.modal;ssui.modal=0;if(m==1){SSUI_Call(ssui.manager?109:104);SSUI_Go(ssui.destination);}else if(m==2)SSUI_Call(105,ssui.tab);else if(m==3)SSUI_Status(SSUI_Call(110,0,0,1,NULL,ssui.filename));else if(m==4)SSUI_Status(SSUI_Call(111,0,0,1,NULL,ssui.loadname));else if(m==6)SSUI_Status(SSUI_Call(107));}
 else if(id==3202){ssui.modal=0;SSUI_Call(108);}
 else if(id>=3300&&id<3304)SSUI_Navigate(id-3300);
 else if(id>=3400&&id<3464){ssui.modIndex=h.a;ssui.modal=9;}
 else if(id==3500){uiClientState_t state;trap->GetClientState(&state);char forced[128];trap->Cvar_VariableStringBuffer("fs_forcegame",forced,sizeof(forced));if(SSUI_Ingame()||state.connState>=CA_CONNECTED||*forced){Q_strncpyz(ssui.status,*forced?"Mod switching is unavailable in this isolated test profile.":"Switch mods from the disconnected main menu.",sizeof(ssui.status));ssui.modal=0;}else{trap->Cvar_Set("fs_game",uiInfo.modList[ssui.modIndex].modName);trap->Cmd_ExecuteText(EXEC_APPEND,"vid_restart\n");}}
 else if(id==3600||id==3601)ssui.modalScroll=std::max(0,std::min(std::max(0,uiInfo.modCount-8),ssui.modalScroll+(id==3601?1:-1)));
 else if(id>=3700&&id<3700+SS_COUNT)SSUI_Status(SSUI_Call(114,h.a));
}
static void SSUI_StageSlider(int i,float value){
 const auto& setting=ssSettings[i];
 char text[64];
 Com_sprintf(text,sizeof(text),!strcmp(setting.name,"cg_thirdPersonRange")?"%.0f":"%.3g",value);
 SSUI_Status(SSUI_Call(102,i,0,0,setting.name,text));
}
static void SSUI_Mouse(){scui.pointerMode=1;if(ssui.scrollbar.dragging){stmenu::move(ssui.scrollbar,uiInfo.uiDC.cursory,ssui.scroll);return;}if(ssui.drag&&ssui.setting>=0){auto& s=ssSettings[ssui.setting];float n=s.low+Com_Clamp(0,1,(uiInfo.uiDC.cursorx-ssui.sliderX)/ssui.sliderW)*(s.high-s.low);SSUI_StageSlider(ssui.setting,n);}}
#include "ui_st_setup_draw.inc"
static qboolean SSUI_Key(int key,qboolean down){
 if(!SSUI_IsMenu())return qfalse;if(!ssui.active)SSUI_Start();
 if(!down){if(key==A_MOUSE1){ssui.drag=0;ssui.scrollbar.dragging=false;}return qtrue;}
 if(key==A_ESCAPE){if(ssui.modal==6)SSUI_Call(108);else if(ssui.modal)ssui.modal=0;else if(ssui.field)ssui.field=0;else SSUI_Navigate(ssui.manager?-2:-1);return qtrue;}
 if(ssui.field){int len=strlen(ssui.edit);
  if(key&K_CHAR_FLAG){int c=key&~K_CHAR_FLAG;if(c>=32&&c<127&&len<(ssui.field==2?79:ssui.field==3?40:127)){if(ssui.replace){ssui.edit[0]=0;len=ssui.caret=0;ssui.replace=0;}memmove(ssui.edit+ssui.caret+1,ssui.edit+ssui.caret,len-ssui.caret+1);ssui.edit[ssui.caret++]=c;}}
  else if(key==A_BACKSPACE&&ssui.caret){memmove(ssui.edit+ssui.caret-1,ssui.edit+ssui.caret,len-ssui.caret+1);--ssui.caret;ssui.replace=0;}
  else if(key==A_DELETE&&ssui.caret<len)memmove(ssui.edit+ssui.caret,ssui.edit+ssui.caret+1,len-ssui.caret);
  else if(key==A_HOME)ssui.caret=0;else if(key==A_END)ssui.caret=len;else if(key==A_CURSOR_LEFT&&ssui.caret)--ssui.caret;else if(key==A_CURSOR_RIGHT&&ssui.caret<len)++ssui.caret;
  else if(key==A_ENTER||key==A_TAB)SSUI_Commit();
  if(ssui.field==2){Q_strncpyz(ssui.search,ssui.edit,sizeof(ssui.search));ssui.scroll=0;}
  if(key!=A_MOUSE1&&key!=A_MWHEELDOWN&&key!=A_MWHEELUP)return qtrue;
 }
 if(key==A_MOUSE1){scui.pointerMode=1;if(!ssui.modal&&SSUI_Commit()&&stmenu::begin(ssui.scrollbar,uiInfo.uiDC.cursorx,uiInfo.uiDC.cursory,ssui.scroll))return qtrue;for(int i=scui.hitsCount-1;i>=0;--i)if(SCUI_Over(scui.hits[i].x,scui.hits[i].y,scui.hits[i].w,scui.hits[i].h)){ssui.mouseActivation=1;SSUI_Click(scui.hits[i]);SSUI_Mouse();ssui.mouseActivation=0;break;}return qtrue;}
 if(key==A_MWHEELDOWN||key==A_MWHEELUP){if(ssui.modal==7)ssui.modalScroll=std::max(0,std::min(std::max(0,uiInfo.modCount-8),ssui.modalScroll+(key==A_MWHEELDOWN?1:-1)));else if(!ssui.modal&&SSUI_Commit())ssui.scroll=std::max(0,std::min(ssui.maxScroll,ssui.scroll+(key==A_MWHEELDOWN?43:-43)));return qtrue;}
 if(key==A_TAB||key==A_CURSOR_DOWN||key==A_CURSOR_UP||key==A_JOY11||key==A_JOY12){scui.pointerMode=0;int at=-1;for(int i=0;i<scui.hitsCount;++i)if(scui.hits[i].id==ssui.focus)at=i;at+=key==A_CURSOR_UP||key==A_JOY11?-1:1;if(at<0)at=scui.hitsCount-1;if(at>=scui.hitsCount)at=0;if(at>=0)ssui.focus=scui.hits[at].id;return qtrue;}
 if(key==A_ENTER||key==A_JOY0){for(int i=0;i<scui.hitsCount;++i)if(scui.hits[i].id==ssui.focus){SSUI_Click(scui.hits[i]);break;}return qtrue;}
 if(key==A_CURSOR_LEFT||key==A_CURSOR_RIGHT||key==A_JOY13||key==A_JOY14){for(int i=0;i<scui.hitsCount;++i){auto h=scui.hits[i];if(h.id==ssui.focus&&h.id>=2400&&h.id<2400+SS_COUNT){auto r=SSUI_Call(101,h.a);auto& s=ssSettings[h.a];SSUI_StageSlider(h.a,Com_Clamp(s.low,s.high,r.number+(key==A_CURSOR_LEFT||key==A_JOY13?-1:1)*(s.high-s.low)/100));return qtrue;}}}
 return qtrue;
}
#ifdef ST_CONTROLS_QA
static const char* SCUI_Argv(int);
extern void Item_RunScript(itemDef_t*,const char*);
qboolean ST_SetupQA(){
 if(Q_stricmp(SCUI_Argv(0),"st_setupqa"))return qfalse;const char* op=SCUI_Argv(1);
 if(!strcmp(op,"continue"))trap->Cmd_ExecuteText(EXEC_APPEND,va("exec %s\n",SCUI_Argv(2)));
 else if(!strcmp(op,"click")){int id=atoi(SCUI_Argv(2));qboolean found=qfalse;for(int i=0;i<scui.hitsCount;++i)if(scui.hits[i].id==id){SSUI_Click(scui.hits[i]);found=qtrue;break;}if(!found)Com_Printf("ST_SETUP_FAIL missing click %d\n",id);}
 else if(!strcmp(op,"dragstart")){
  int id=atoi(SCUI_Argv(2));
  for(int i=0;i<scui.hitsCount;++i){
   const auto& hit=scui.hits[i];
   if(hit.id!=id)continue;
   uiInfo.uiDC.cursorx=hit.x+hit.w*atof(SCUI_Argv(3));
   uiInfo.uiDC.cursory=hit.y+hit.h/2;
   SSUI_Key(A_MOUSE1,qtrue);
   break;
  }
  if(!ssui.drag)Com_Printf("ST_SETUP_FAIL slider did not capture pointer %d\n",id);
 }
 else if(!strcmp(op,"dragmove")){
  if(!ssui.drag)Com_Printf("ST_SETUP_FAIL slider lost pointer\n");
  else{uiInfo.uiDC.cursorx=ssui.sliderX+ssui.sliderW*atof(SCUI_Argv(2));SSUI_Mouse();}
 }
 else if(!strcmp(op,"dragend"))SSUI_Key(A_MOUSE1,qfalse);
 else if(!strcmp(op,"text")){const char* p=SCUI_Argv(2);for(;*p;++p)SSUI_Key((unsigned char)*p|K_CHAR_FLAG,qtrue);}
 else if(!strcmp(op,"scroll"))ssui.scroll=atoi(SCUI_Argv(2));
 else if(!strcmp(op,"assertvar")){char v[2048];trap->Cvar_VariableStringBuffer(SCUI_Argv(2),v,sizeof(v));if(strcmp(v,SCUI_Argv(3)))Com_Printf("ST_SETUP_FAIL variable %s=%s\n",SCUI_Argv(2),v);}
 else if(!strcmp(op,"set"))SSUI_Status(SSUI_Call(102,0,0,0,SCUI_Argv(2),SCUI_Argv(3)));
 else if(!strcmp(op,"assertstatus")){if(!strstr(ssui.status,SCUI_Argv(2)))Com_Printf("ST_SETUP_FAIL status=%s\n",ssui.status);}
 else if(!strcmp(op,"asserttab")){if(ssui.tab!=atoi(SCUI_Argv(2)))Com_Printf("ST_SETUP_FAIL tab\n");}
 else if(!strcmp(op,"assertdirty")){if(SSUI_Dirty()!=atoi(SCUI_Argv(2)))Com_Printf("ST_SETUP_FAIL dirty\n");}
 else if(!strcmp(op,"focus"))ssui.focus=atoi(SCUI_Argv(2));
 else if(!strcmp(op,"key"))SSUI_Key(atoi(SCUI_Argv(2)),qtrue);
 else if(!strcmp(op,"assertmanager")){if(ssui.manager!=atoi(SCUI_Argv(2)))Com_Printf("ST_SETUP_FAIL manager\n");}
 else if(!strcmp(op,"ingame")){UI_LoadMenus("ui/jampingame.txt",qtrue);Menus_ActivateByName("ingame_setup");ssui.active=0;}
 else if(!strcmp(op,"pause")){UI_LoadMenus("ui/jampingame.txt",qtrue);Menus_CloseAll();menuDef_t* menu=Menus_ActivateByName("ingame");
  // Offline QA has no world behind the popup; prevent the disconnected client
  // from replacing it with Main. Production pause-menu behavior is unchanged.
  if(menu)menu->fullScreen=qtrue;Com_Printf("ST_SETUP_PAUSE loaded=%s\n",menu?menu->window.name:"missing");trap->Key_SetCatcher(KEYCATCH_UI);ssui.active=0;}
 else if(!strcmp(op,"pauseclick")){menuDef_t* menu=Menu_GetFocused();itemDef_t* item=menu?Menu_FindItemByName(menu,SCUI_Argv(2)):NULL;if(item&&item->action)Item_RunScript(item,item->action);else Com_Printf("ST_SETUP_FAIL pause item %s missing in %s\n",SCUI_Argv(2),menu?menu->window.name:"none");}
 else if(!strcmp(op,"assertmenu")){menuDef_t* menu=Menu_GetFocused();if(!menu||Q_stricmp(menu->window.name,SCUI_Argv(2)))Com_Printf("ST_SETUP_FAIL focused menu=%s expected=%s\n",menu?menu->window.name:"none",SCUI_Argv(2));}
 else if(!strcmp(op,"state"))Com_Printf("ST_SETUP_STATE tab=%d manager=%d modal=%d dirty=%d scroll=%d status=%s\n",ssui.tab,ssui.manager,ssui.modal,SSUI_Dirty(),ssui.scroll,ssui.status);
 return qtrue;
}
#endif
