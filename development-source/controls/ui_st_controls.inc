/* Native Controls surface; all edits use the engine's transactional model. GPL-2.0-only. */
#include "st_controls_api.h"
#include "st_controls_catalog.h"
#include "st_menu_interaction.h"
typedef struct {float x,y,w,h;int id,a,b;} stcHit_t;
static struct {int active,tab,cat,page,focus,field,caret,replace,modal,capture,action,slot,key,newkey,setting,dirty,drag,mouseActivation,fold[7],destination,mouseScroll;int pointerMode;stmenu::Scrollbar scrollbar;float sliderX,sliderW;char menu[64],search[80],edit[2048],fieldName[128],filename[64],status[4096];stcHit_t hits[128];int hitsCount;} scui;
static vec4_t scuInk={.027f,.063f,.098f,1},scuPanel={.047f,.094f,.137f,1},scuLine={.13f,.27f,.34f,1},scuCyan={.30f,.82f,.96f,1},scuText={.85f,.92f,.96f,1},scuMuted={.57f,.70f,.77f,1},scuGold={.95f,.76f,.44f,1};
static const char* scuTabs[]={"Key Bindings","Bindlist","Server Management","Mouse","Controller","Advanced Input","Saved Configs"};
static const char* scuCats[]={"All","Movement","Combat","Weapons","Force","Communication","Camera / UI"};
static stcReply_t SCUI_Call(int op,int a,int b,int c,const char* name,const char* text){stcRequest_t q;stcReply_t r;memset(&q,0,sizeof(q));memset(&r,0,sizeof(r));q.op=op;q.a=a;q.b=b;q.c=c;if(name)Q_strncpyz(q.name,name,sizeof(q.name));if(text)Q_strncpyz(q.text,text,sizeof(q.text));trap->Controls(&q,&r);scui.dirty=r.dirty;return r;}
static void SCUI_Status(stcReply_t r){Q_strncpyz(scui.status,r.text,sizeof(scui.status));}
#include "ui_st_rich.inc"
static void SCUI_Text(float x,float y,float scale,const char* text,const float* color){RUI_Text(x,y,scale,text,color);}
static void SCUI_Fit(float x,float y,float w,float scale,const char* text,const float* color){char s[512];Q_strncpyz(s,text,sizeof(s));if(RUI_Width(s,scale)>w){size_t n=strlen(s);while(n>3&&RUI_Width(s,scale)>w){--n;s[n-3]='.';s[n-2]='.';s[n-1]='.';s[n]=0;}}SCUI_Text(x,y,scale,s,color);}
static void SCUI_Label(float x,float y,float w,float scale,const char* text,const float* color){float width=RUI_Width(text,scale);if(width>w&&width>0)scale*=w/width;SCUI_Text(x,y,scale,text,color);}
static void SCUI_Centered(float x,float y,float w,float h,float scale,const char* text,const float* color){
 const float width=RUI_Width(text,scale);
 if(width>w-8)scale*=(w-8)/width;
 SCUI_Text(x+(w-RUI_Width(text,scale))/2,y+(h-17*scale)/2,scale,text,color);
}
static void SCUI_Border(float x,float y,float w,float h,const float* c){RUI_Control(x,y,w,h,"field",false,c==scuCyan);}
static void SCUI_Hit(float x,float y,float w,float h,int id,int a,int b){if(scui.hitsCount<128){stcHit_t* p=&scui.hits[scui.hitsCount++];p->x=x;p->y=y;p->w=w;p->h=h;p->id=id;p->a=a;p->b=b;}}
static qboolean SCUI_Over(float x,float y,float w,float h){return uiInfo.uiDC.cursorx>=x&&uiInfo.uiDC.cursorx<=x+w&&uiInfo.uiDC.cursory>=y&&uiInfo.uiDC.cursory<=y+h;}
#include "ui_st_menu_style.inc"
static void SCUI_Button(float x,float y,float w,float h,const char* text,int id,int a,int b,qboolean selected){
 const bool focus=SCUI_Over(x,y,w,h)||(!scui.pointerMode&&scui.focus==id);
 vec4_t color;MSUI_Color(color,selected,focus);
 const bool binding=id>=500&&id<570;
 const bool centered=binding||(id>=100&&id<107)||(id>=1200&&id<=1302)||
   (id>=2000&&id<2007)||(id>=2900&&id<=2906)||(id>=3200&&id<=3202)||id==3500;
 if(binding){
  const float width=std::min(w-4,std::max(30.f,14.f+RUI_Width(text,.57f)));
  RUI_FieldArt(focus?"field_focus":"field_idle",x+(w-width)/2,y+2,width,h-4);
 }else if((id>=100&&id<107)||(id>=2000&&id<2007)){
  RUI_Control(x,y,w,h,"tab",selected,focus);
 }else if((id>=600&&id<625)||(id>=2200&&id<2400)){
  const float width=std::min(w,std::max(42.f,16.f+RUI_Width(text,.57f)));
  RUI_Control(x,y,width,h,"field",selected,focus);
 }else if((w>=48&&h>=20&&!(id>=300&&id<320)&&!(id>=700&&id<725))||selected){
  const float width=w>=140?std::min(w,std::max(44.f,25.f+RUI_Width(text,.57f))):w;
  RUI_Control(centered?x+(w-width)/2:x,y,width,h,"action",selected,focus);
 }
 if(centered)SCUI_Centered(x,y,w,h,.57f,text,color);
 else SCUI_Label(x+6,y+(h-17*.57f)/2,w-12,.57f,text,color);
 SCUI_Hit(x,y,w,h,id,a,b);
}
static void SCUI_Field(float x,float y,float w,const char* text,int id,int a,const char* name){UI_FillRect(x,y,w,22,scuPanel);SCUI_Border(x,y,w,22,scui.field==id?scuCyan:scuLine);SCUI_Fit(x+5,y+4,w-10,.56f,scui.field==id?scui.edit:text,scuText);SCUI_Hit(x,y,w,22,id,a,0);if(scui.field==id){float cx=x+5;char caret[2048];Q_strncpyz(caret,scui.edit,sizeof(caret));caret[scui.caret]=0;cx+=RUI_Width(caret,.56f);if(cx<x+w-5&&((uiInfo.uiDC.realTime/400)&1))UI_FillRect(cx,y+4,1,14,scuCyan);}(void)name;}
static qboolean SCUI_IsMenu(void){menuDef_t* m=Menu_GetFocused();return m&&(!Q_stricmp(m->window.name,"controlsMenu")||!Q_stricmp(m->window.name,"ingame_controls"));}
static void SCUI_Start(void){menuDef_t* m=Menu_GetFocused();memset(&scui,0,sizeof(scui));scui.active=1;scui.destination=-1;scui.key=-1;scui.newkey=-1;scui.focus=100;Q_strncpyz(scui.menu,m->window.name,sizeof(scui.menu));SCUI_Status(SCUI_Call(STC_OPEN,0,0,0,NULL,NULL));}
static void SCUI_Close(void){qboolean ingame=!Q_stricmp(scui.menu,"ingame_controls");SCUI_Call(STC_CANCEL,0,0,0,NULL,NULL);Menus_CloseByName(scui.menu);scui.active=0;if(!ingame){const char* menus[]={"multiplayermenu","playerMenu","controlsMenu","setup_menu"};Menus_OpenByName(scui.destination>=0?menus[scui.destination]:"main");}}
static void SCUI_Edit(int field,const char* text,const char* name,int setting){scui.field=field;scui.setting=setting;scui.replace=field!=10;Q_strncpyz(scui.edit,text,sizeof(scui.edit));Q_strncpyz(scui.fieldName,name?name:"",sizeof(scui.fieldName));scui.caret=strlen(scui.edit);}
static qboolean SCUI_CommitField(void){stcReply_t r;if(!scui.field)return qtrue;if(scui.field==10){Q_strncpyz(scui.search,scui.edit,sizeof(scui.search));scui.page=0;}else if(scui.field==11){r=SCUI_Call(STC_VAR,0,0,0,scui.fieldName,scui.edit);SCUI_Status(r);if(r.status<0)return qfalse;}else if(scui.field==12){Q_strncpyz(scui.filename,scui.edit,sizeof(scui.filename));}scui.field=0;return qtrue;}
static stcReply_t SCUI_Row(int scope,int index,const char* group){return SCUI_Call(STC_ROWS,scope,index,0,group,scui.search);}
static float SCUI_SettingNumber(int index){
 const auto row=SCUI_Call(STC_ROWS,STC_SETTINGS,index,0,NULL,NULL);
 return row.number;
}
static void SCUI_SelectAction(int key){scui.key=key;scui.modal=3;scui.page=0;scui.field=0;scui.search[0]=0;}
static void SCUI_Result(stcReply_t r){SCUI_Status(r);if(r.status==2)scui.modal=2;else scui.capture=0;}
static int SCUI_PageSize(void){if(scui.modal==3)return 12;if(scui.tab==0)return 10;if(scui.tab==1)return 20;if(scui.tab==4&&scui.cat==99)return 18;if(scui.tab==3||scui.tab==4||scui.tab==5)return 25;return 12;}
#include "ui_st_controls_draw.inc"
static void SCUI_CaptureKey(int key){stcReply_t r;scui.newkey=key;if(scui.capture==1)r=SCUI_Call(STC_BIND,scui.action,scui.slot,key,NULL,"");else r=SCUI_Call(STC_MOVE,scui.key,key,0,NULL,NULL);SCUI_Result(r);if(r.status==2)scui.capture=0;}
static void SCUI_Click(stcHit_t hit){stcReply_t r;int id=hit.id;char value[128];
 if(id!=13&&id!=10&&id!=11&&id!=12&&!SCUI_CommitField())return;
 if(id>=100&&id<107){scui.tab=hit.a;scui.cat=0;scui.page=0;scui.mouseScroll=0;scui.search[0]=0;scui.status[0]=0;scui.drag=0;}
 else if(id>=200&&id<207){scui.cat=hit.a;scui.page=0;scui.search[0]=0;}
 else if(id==10)SCUI_Edit(10,scui.search,NULL,0);
 else if(id==12)SCUI_Edit(12,scui.filename,NULL,0);
 else if(id==13){scui.field=13;scui.replace=0;scui.caret=strlen(scui.edit);}
 else if((id>=500&&id<520)||(id>=550&&id<570)){scui.key=-1;scui.action=hit.a;scui.slot=hit.b;scui.capture=1;scui.modal=0;scui.field=0;}
 else if(id>=300&&id<320){r=SCUI_Row(scui.tab==2?STC_SERVER:STC_ACTIONS,scui.page*SCUI_PageSize()+id-300,scui.tab==0?scuCats[scui.cat]:NULL);Q_strncpyz(scui.status,r.help,sizeof(scui.status));scui.action=hit.a;scui.modal=8;}
 else if(id>=600&&id<625){r=SCUI_Row(STC_SETTINGS,scui.tab==3&&id==612?2:scui.page*SCUI_PageSize()+id-600,scui.tab==3?"Mouse":scui.tab==4?"Controller":"Advanced");if(scui.tab==3&&id==602){Com_sprintf(value,sizeof(value),"%.6g",r.number==0?-.022f:-r.number);SCUI_Status(SCUI_Call(STC_VAR,0,0,0,r.name,value));}else if(r.b==1||r.b==2){Com_sprintf(value,sizeof(value),"%d",((int)r.number+1)%(r.b==1?2:3));SCUI_Status(SCUI_Call(STC_VAR,0,0,0,r.name,value));}else if(r.b==3){scui.setting=hit.a;scui.drag=scui.mouseActivation;scui.sliderX=hit.x;scui.sliderW=hit.w;scui.fieldName[0]=0;Q_strncpyz(scui.fieldName,r.name,sizeof(scui.fieldName));}else SCUI_Edit(11,r.text,r.name,r.a);}
 else if(id>=700&&id<725)SCUI_Status(SCUI_Call(STC_RESETVAR,hit.a,0,0,NULL,NULL));
 else if(id>=800&&id<820){scui.action=-1;scui.key=hit.a;scui.capture=2;scui.modal=0;scui.field=0;}
 else if(id>=900&&id<920){if(hit.b>=sizeof(scui.edit)){Q_strncpyz(scui.status,"This command is too long for the text editor; it is preserved. Use change-key or clear.",sizeof(scui.status));return;}r=SCUI_Row(STC_BINDLIST,scui.page*SCUI_PageSize()+id-900,NULL);if(!STC_EditableCommand(r.text)){Q_strncpyz(scui.status,"Non-ASCII command preserved. This text editor supports ASCII; use change-key or clear.",sizeof(scui.status));return;}scui.key=hit.a;Q_strncpyz(scui.edit,r.text,sizeof(scui.edit));scui.modal=4;scui.field=13;scui.caret=strlen(scui.edit);scui.replace=0;}
 else if(id>=1000&&id<1012){r=SCUI_Row(STC_CONFIGS,scui.page*SCUI_PageSize()+id-1000,NULL);Q_strncpyz(scui.filename,r.text,sizeof(scui.filename));r=SCUI_Call(STC_LOAD,0,0,0,NULL,scui.filename);SCUI_Status(r);if(r.status==2)scui.modal=6;}
 else if(id>=1100&&id<1118)SCUI_SelectAction(hit.a);
 else if(id==1900&&scui.tab==3){scui.fold[3]^=1;if(!(scui.fold[3]&1))scui.mouseScroll=0;}
 else if(id==1920||id==1921){scui.mouseScroll=(int)Com_Clamp(0,127,scui.mouseScroll+(id==1921?47:-47));}
 else if(id==400){r=SCUI_Call(STC_SAVE,0,0,0,NULL,scui.filename);SCUI_Status(r);if(r.status==2)scui.modal=5;}
 else if(id==410||id==411){scui.cat=id==411?99:0;scui.page=0;}
 else if(id==412){scui.modal=7;Q_strncpyz(scui.status,"Replace the controller's button assignments with defaults?",sizeof(scui.status));}
 else if(id==1200){if(scui.page>0)--scui.page;}
 else if(id==1201){if((scui.page+1)*SCUI_PageSize()<hit.a)++scui.page;}
 else if(id==1300||(id>=1800&&id<1804)){scui.destination=id==1300?-1:id-1800;if(scui.destination==2)return;if(scui.dirty){scui.modal=1;Q_strncpyz(scui.status,"Discard pending controls changes and return?",sizeof(scui.status));}else SCUI_Close();}
 else if(id==1301){SCUI_Status(SCUI_Call(STC_CANCEL,0,0,0,NULL,NULL));scui.field=0;}
 else if(id==1302){SCUI_Status(SCUI_Call(STC_APPLY,0,0,0,NULL,NULL));scui.field=0;}
 else if(id==1400){int key=scui.key;if(scui.capture==1){r=SCUI_Call(STC_ACTIONINFO,scui.action,0,0,NULL,NULL);key=scui.slot?r.c:r.b;}if(key>=0)SCUI_Status(SCUI_Call(STC_RAW,key,0,0,NULL,""));scui.capture=0;}
 else if(id==1401){scui.modal=0;scui.capture=0;scui.field=0;scui.search[0]=0;}
 else if(id>=1500&&id<1512){r=SCUI_Row(STC_ACTIONS,scui.page*SCUI_PageSize()+id-1500,NULL);SCUI_Status(SCUI_Call(STC_RAW,scui.key,0,0,NULL,r.name));scui.modal=0;scui.field=0;scui.search[0]=0;scui.page=0;}
 else if(id==1600)SCUI_SelectAction(scui.key);
 else if(id==1601){SCUI_Status(SCUI_Call(STC_RAW,scui.key,0,0,NULL,""));scui.modal=0;scui.field=0;}
 else if(id==1602){SCUI_Status(SCUI_Call(STC_RAW,scui.key,0,0,NULL,scui.edit));scui.modal=0;scui.field=0;}
 else if(id==1701||id==1702){if(scui.key<0)r=SCUI_Call(STC_BIND,scui.action,scui.slot,scui.newkey,NULL,id==1701?"swap":"replace");else r=SCUI_Call(STC_MOVE,scui.key,scui.newkey,id==1701?2:1,NULL,NULL);SCUI_Status(r);scui.modal=0;scui.capture=0;scui.key=-1;}
 else if(id==1700){int modal=scui.modal;scui.modal=0;if(modal==1)SCUI_Close();else if(modal==5)SCUI_Status(SCUI_Call(STC_SAVE,0,0,1,NULL,scui.filename));else if(modal==6)SCUI_Status(SCUI_Call(STC_LOAD,0,0,1,NULL,scui.filename));else if(modal==8){r=SCUI_Call(STC_RESETACTION,scui.action,0,0,NULL,NULL);SCUI_Status(r);if(r.status==2)scui.modal=9;}else if(modal==9)SCUI_Status(SCUI_Call(STC_RESETACTION,scui.action,0,1,NULL,NULL));else if(modal==7)SCUI_Status(SCUI_Call(STC_PADDEFAULTS,0,0,0,NULL,NULL));}
}
static void SCUI_Mouse(void){scui.pointerMode=1;if(scui.active&&scui.scrollbar.dragging){stmenu::move(scui.scrollbar,uiInfo.uiDC.cursory,scui.mouseScroll);return;}if(scui.active&&scui.drag){char value[64];const auto& setting=stcSettings[scui.setting];float n=setting.min+Com_Clamp(0,1,(uiInfo.uiDC.cursorx-scui.sliderX)/scui.sliderW)*(setting.max-setting.min);Com_sprintf(value,sizeof(value),"%.2f",n);SCUI_Status(SCUI_Call(STC_VAR,0,0,0,scui.fieldName,value));}}
static qboolean SCUI_HandleKey(int key,qboolean down){int i,len;if(!SCUI_IsMenu())return qfalse;if(!scui.active)SCUI_Start();
 if(!down){if(key==A_MOUSE1){scui.drag=0;scui.scrollbar.dragging=false;}return qtrue;}
 if(key==A_ESCAPE){if(scui.capture||scui.modal){scui.capture=0;scui.modal=0;scui.field=0;}else if(scui.field){scui.field=0;}else{stcHit_t h;memset(&h,0,sizeof(h));h.id=1300;SCUI_Click(h);}return qtrue;}
 if(scui.capture){if(key==A_MOUSE1){for(i=scui.hitsCount-1;i>=0;--i){stcHit_t h=scui.hits[i];if((h.id==1400||h.id==1401)&&SCUI_Over(h.x,h.y,h.w,h.h)){SCUI_Click(h);return qtrue;}}}if(!(key&K_CHAR_FLAG))SCUI_CaptureKey(key);return qtrue;}
 if(scui.field&&scui.tab==3&&!scui.modal&&(key==A_MWHEELDOWN||key==A_MWHEELUP)&&!SCUI_CommitField())return qtrue;
 if(scui.field){len=strlen(scui.edit);if(key&K_CHAR_FLAG){int c=key&~K_CHAR_FLAG;if(c>=32&&c<127&&len<(scui.field==10?79:scui.field==12?40:2047)){if(scui.replace){scui.edit[0]=0;len=scui.caret=0;scui.replace=0;}memmove(scui.edit+scui.caret+1,scui.edit+scui.caret,len-scui.caret+1);scui.edit[scui.caret++]=(char)c;}}
  else if(key==A_BACKSPACE&&scui.caret>0){memmove(scui.edit+scui.caret-1,scui.edit+scui.caret,len-scui.caret+1);--scui.caret;scui.replace=0;}
  else if(key==A_DELETE&&scui.caret<len)memmove(scui.edit+scui.caret,scui.edit+scui.caret+1,len-scui.caret);
  else if(key==A_HOME)scui.caret=0;else if(key==A_END)scui.caret=len;else if(key==A_CURSOR_LEFT&&scui.caret>0)--scui.caret;else if(key==A_CURSOR_RIGHT&&scui.caret<len)++scui.caret;
  else if(key==A_ENTER||key==A_TAB){if(scui.field!=13)SCUI_CommitField();}
  if(scui.field==10){Q_strncpyz(scui.search,scui.edit,sizeof(scui.search));scui.page=0;}
  if(key!=A_MOUSE1)return qtrue;
 }
 if(key==A_MOUSE1){scui.pointerMode=1;if(!scui.modal&&scui.tab==3&&(scui.fold[3]&1)&&SCUI_CommitField()&&stmenu::begin(scui.scrollbar,uiInfo.uiDC.cursorx,uiInfo.uiDC.cursory,scui.mouseScroll))return qtrue;int first=0;for(i=scui.hitsCount-1;i>=first;--i){stcHit_t h=scui.hits[i];if(SCUI_Over(h.x,h.y,h.w,h.h)){scui.focus=h.id;scui.mouseActivation=1;SCUI_Click(h);SCUI_Mouse();scui.mouseActivation=0;break;}}return qtrue;}
 if(key==A_MWHEELDOWN||key==A_MWHEELUP){if(!SCUI_CommitField())return qtrue;if(scui.tab==3&&!scui.modal){if(scui.fold[3]&1)scui.mouseScroll=(int)Com_Clamp(0,127,scui.mouseScroll+(key==A_MWHEELDOWN?47:-47));}else if(key==A_MWHEELDOWN)++scui.page;else if(scui.page)--scui.page;return qtrue;}
 if(!scui.modal&&(key==A_CURSOR_LEFT||key==A_CURSOR_RIGHT||key==A_JOY13||key==A_JOY14)){for(i=0;i<scui.hitsCount;++i){stcHit_t h=scui.hits[i];if(h.id==scui.focus&&h.id>=600&&h.id<625&&h.b==3){stcReply_t r=SCUI_Row(STC_SETTINGS,scui.page*SCUI_PageSize()+h.id-600,"Controller");char value[64];const auto& setting=stcSettings[h.a];const float min=setting.min,max=setting.max,step=h.a==22?.01f:.25f;int direction=key==A_CURSOR_LEFT||key==A_JOY13?-1:1;Com_sprintf(value,sizeof(value),"%.2f",Com_Clamp(min,max,r.number+direction*step));SCUI_Status(SCUI_Call(STC_VAR,0,0,0,r.name,value));scui.drag=0;return qtrue;}}}
 if(key==A_TAB||key==A_CURSOR_DOWN||key==A_CURSOR_UP||key==A_JOY11||key==A_JOY12){scui.pointerMode=0;int at=-1;for(i=0;i<scui.hitsCount;++i)if(scui.hits[i].id==scui.focus)at=i;at+=(key==A_CURSOR_UP||key==A_JOY11)?-1:1;if(at<0)at=scui.hitsCount-1;if(at>=scui.hitsCount)at=0;if(scui.hitsCount)scui.focus=scui.hits[at].id;return qtrue;}
 if(key==A_ENTER||key==A_JOY0){for(i=0;i<scui.hitsCount;++i)if(scui.hits[i].id==scui.focus){SCUI_Click(scui.hits[i]);break;}}
 return qtrue;
}
static qboolean SCUI_Key(int key,qboolean down){qboolean handled=SCUI_HandleKey(key,down);if(handled)SCUI_Call(STC_CAPTURE,scui.capture!=0,0,0,NULL,NULL);return handled;}
#ifdef ST_CONTROLS_QA
static const char* SCUI_Argv(int n){static char args[4][2048];trap->Cmd_Argv(n,args[n%4],sizeof(args[0]));return args[n%4];}
qboolean ST_ControlsQA(void){const char* op;if(Q_stricmp(SCUI_Argv(0),"st_controlsqa"))return qfalse;op=SCUI_Argv(1);if(!strcmp(op,"click")){int id=atoi(SCUI_Argv(2)),i;for(i=0;i<scui.hitsCount;++i)if(scui.hits[i].id==id){uiInfo.uiDC.cursorx=scui.hits[i].x+scui.hits[i].w/2;uiInfo.uiDC.cursory=scui.hits[i].y+scui.hits[i].h/2;SCUI_Key(A_MOUSE1,qtrue);SCUI_Key(A_MOUSE1,qfalse);break;}}else if(!strcmp(op,"text")){const char* p=SCUI_Argv(2);for(;*p;++p)SCUI_Key((unsigned char)*p|K_CHAR_FLAG,qtrue);}else if(!strcmp(op,"key"))SCUI_Key(atoi(SCUI_Argv(2)),qtrue);else if(!strcmp(op,"ingame")){UI_LoadMenus("ui/jampingame.txt",qtrue);Menus_ActivateByName("ingame_controls");trap->Key_SetCatcher(KEYCATCH_UI);scui.active=0;}else if(!strcmp(op,"assertvar")){char value[2048];trap->Cvar_VariableStringBuffer(SCUI_Argv(2),value,sizeof(value));if(strcmp(value,SCUI_Argv(3)))Com_Printf("ST_CONTROLS_FAIL variable mismatch");}else if(!strcmp(op,"assertbind")){char value[2048];trap->Key_GetBindingBuf(atoi(SCUI_Argv(2)),value,sizeof(value));if(strcmp(value,SCUI_Argv(3)))Com_Printf("ST_CONTROLS_FAIL binding mismatch");}else if(!strcmp(op,"focus"))scui.focus=atoi(SCUI_Argv(2));else if(!strcmp(op,"assertpage")){if(scui.page!=atoi(SCUI_Argv(2)))Com_Printf("ST_CONTROLS_FAIL page mismatch");}else if(!strcmp(op,"assertstatus")){if(!strstr(scui.status,SCUI_Argv(2)))Com_Printf("ST_CONTROLS_FAIL status mismatch");}else if(!strcmp(op,"assertmenu")){if(!SCUI_IsMenu())Com_Printf("ST_CONTROLS_FAIL menu closed");}else if(!strcmp(op,"assertrows")){stcReply_t r=SCUI_Call(STC_ROWS,STC_SETTINGS,-1,0,SCUI_Argv(2),"");if(r.count!=atoi(SCUI_Argv(3)))Com_Printf("ST_CONTROLS_FAIL settings count");}else if(!strcmp(op,"asserthit")){int i,found=0;for(i=0;i<scui.hitsCount;++i)if(scui.hits[i].id==atoi(SCUI_Argv(2)))found=1;if(found!=atoi(SCUI_Argv(3)))Com_Printf("ST_CONTROLS_FAIL hit visibility");}else if(!strcmp(op,"state"))Com_Printf("ST_CONTROLS_QA menu=%s tab=%d dirty=%d modal=%d field=%d status=%s\n",scui.menu,scui.tab,scui.dirty,scui.modal,scui.field,scui.status);return qtrue;}
#endif
