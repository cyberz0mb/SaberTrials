/* Approved main-menu shell; native actions/input and cinematic playback remain native. */
#include "st_main_core.h"
#include "st_main_geometry.h"
static const vec4_t smWhite={.89f,.96f,1,1},smCyan={.03f,.80f,1,1},smGold={1,.75f,.22f,1};
static struct {int heads;stmain::Point first;bool motion;char focus[32];} smFrame;
static bool SMUI_IsRoot(menuDef_t* m){return m&&(!Q_stricmp(m->window.name,"main")||!Q_stricmp(m->window.name,"mainMenu"));}
static void SMUI_Image(const char* name,float x,float y,float w,float h,const float* color=NULL){
 int shader=trap->R_RegisterShaderNoMip(name);if(!shader)return;trap->R_SetColor(color);UI_DrawHandlePic(x,y,w,h,shader);trap->R_SetColor(NULL);
}
static void SMUI_Text(float x,float y,float width,float scale,const char* text,const float* color,int font=FONT_SMALL2,bool center=false){
 vec4_t c;memcpy(c,color,sizeof(c));float length=Text_Width(text,scale,font);if(length>width){scale*=width/length;length=width;}
 Text_Paint(center?x+(width-length)/2:x,y,scale,c,text,0,0,ITEM_TEXTSTYLE_NORMAL,font);
}
static void SMUI_Icon(const char* name,float cx,float y,float height,const float* color=smWhite){
 float width=height*uiInfo.uiDC.yscale/uiInfo.uiDC.xscale;SMUI_Image(name,cx-width/2,y,width,height,color);
}
static void SMUI_Beam(const std::vector<stmain::Point>& path,float phase,float tail,float size,const float* color){
 float total=stmain::length(path,uiInfo.uiDC.xscale,uiInfo.uiDC.yscale);if(total<=0)return;
 float fraction=tail*uiInfo.uiDC.xscale/total;
 for(int i=23;i>=0;--i){float t=i/23.f;auto p=stmain::sample(path,phase-t*fraction,uiInfo.uiDC.xscale,uiInfo.uiDC.yscale);
  vec4_t c={color[0],color[1],color[2],.20f*(1-t)*(1-t)};
  float w=size*uiInfo.uiDC.yscale/uiInfo.uiDC.xscale;SMUI_Image("ui/assets/sabertrials/main/glow",p.x-w/2,p.y-size/2,w,size,c);
  c[0]=1+(color[0]-1)*t;c[1]=1+(color[1]-1)*t;c[2]=1+(color[2]-1)*t;c[3]=.40f*(1-t)*(1-t);
  float core=size*.38f;w=core*uiInfo.uiDC.yscale/uiInfo.uiDC.xscale;SMUI_Image("ui/assets/sabertrials/main/glow",p.x-w/2,p.y-core/2,w,core,c);
  if(i==0){if(!smFrame.heads)smFrame.first=p;++smFrame.heads;c[0]=c[1]=c[2]=1;c[3]=.9f;auto next=stmain::sample(path,phase+.002f,uiInfo.uiDC.xscale,uiInfo.uiDC.yscale);bool horizontal=fabs((next.x-p.x)*uiInfo.uiDC.xscale)>=fabs((next.y-p.y)*uiInfo.uiDC.yscale);float h=horizontal?3.f:24.f;w=(horizontal?24.f:3.f)*uiInfo.uiDC.yscale/uiInfo.uiDC.xscale;SMUI_Image("ui/assets/sabertrials/main/glow",p.x-w/2,p.y-h/2,w,h,c);}
 }
}
static void SMUI_Draw(menuDef_t* root){
 smFrame.heads=0;smFrame.motion=trap->Cvar_VariableValue("st_menuMotion")!=0;smFrame.focus[0]=0;
 SMUI_Image("ui/assets/sabertrials/main/frame",0,0,640,480);
 // Both title lines and the intervening diamond share the exact center, x=320.
 RUI_Image("logo",180,28,280,85);
 bool active=Menu_GetFocused()==root;
 for(const auto& button:smButtons){
  itemDef_t* item=Menu_FindItemByName(root,button.name);bool focus=active&&item&&(item->window.flags&WINDOW_HASFOCUS);
  float width=focus?153.f:145.f;
  SMUI_Image(focus?"ui/assets/sabertrials/main/button_focus":"ui/assets/sabertrials/main/button_idle",17,button.y-6,157*width/145,52);
  char path[MAX_QPATH];Com_sprintf(path,sizeof(path),"ui/assets/sabertrials/%s",button.icon);SMUI_Icon(path,44,button.y+11,18);
  Com_sprintf(path,sizeof(path),"ui/assets/sabertrials/main/label_%s",button.name);
  float height=25,w=height*4*uiInfo.uiDC.yscale/uiInfo.uiDC.xscale;SMUI_Image(path,66,button.y+7,w,height,smWhite);
  if(focus){Q_strncpyz(smFrame.focus,button.name,sizeof(smFrame.focus));if(smFrame.motion){
   std::vector<stmain::Point> perimeter={{23,button.y},{23+width-16,button.y},{23+width,button.y+40},{23,button.y+40},{23,button.y}};
   SMUI_Beam(perimeter,stmain::phase(uiInfo.uiDC.realTime,true,2400),33,10,smCyan);
  }}
 }
 itemDef_t* account=Menu_FindItemByName(root,"account_link");bool accountFocus=active&&account&&(account->window.flags&WINDOW_HASFOCUS);
 SCUI_Label(522,33,81,.68f,"Account / Log in",accountFocus?smGold:smWhite);
 SMUI_Icon("ui/assets/sabertrials/player",611,27,20);
 SMUI_Icon("ui/assets/sabertrials/main/emblem",36,433,28,smCyan);
 RUI_Text(55,441,.85f,"MULTIPLAYER",smWhite);
 char motion[80];trap->Cvar_VariableStringBuffer("st_uiMenuMotionLabel",motion,sizeof(motion));
 itemDef_t* motionItem=Menu_FindItemByName(root,"motion");bool motionFocus=active&&motionItem&&(motionItem->window.flags&WINDOW_HASFOCUS);
 if(motionFocus)Q_strncpyz(smFrame.focus,"motion",sizeof(smFrame.focus));
 SCUI_Label(524,443,88,.66f,motion,motionFocus?smGold:smWhite);
 if(smFrame.motion){
  for(int i=0;i<4;++i)SMUI_Beam(smOuter,stmain::phase(uiInfo.uiDC.realTime,true,10500)+i*.25f,24,8,smCyan);
  for(int i=0;i<2;++i)SMUI_Beam(smInner,stmain::phase(uiInfo.uiDC.realTime,true,14000)+i*.5f,18,7,smCyan);
  if(accountFocus)SMUI_Beam(smAccount,stmain::phase(uiInfo.uiDC.realTime,true,2200),22,8,smGold);
  SMUI_Beam(smGoldBottom,stmain::phase(uiInfo.uiDC.realTime,true,8000),25,7,smGold);
 }
}
static bool SMUI_Paint(){
 menuDef_t* top=Menu_GetFocused();if(!top)return false;menuDef_t* root=SMUI_IsRoot(top)?top:NULL;
 if(!root&&(!Q_stricmp(top->window.name,"st_main_exit")||!Q_stricmp(top->window.name,"st_main_account"))){
  for(const char* name:{"main","mainMenu"}){menuDef_t* m=Menus_FindByName(name);if(m&&(m->window.flags&WINDOW_VISIBLE)){root=m;break;}}
 }
 if(!root)return false;Menu_Paint(root,qtrue);SMUI_Draw(root);if(top!=root)Menu_Paint(top,qtrue);return true;
}
// The legacy setfocus script leaves cursorItem stale on reopening. Synchronize
// it before native navigation; translate the same gamepad keys as the other pages.
static qboolean SMUI_Key(int key,qboolean down){
 menuDef_t* m=Menu_GetFocused();if(!SMUI_IsRoot(m)&&(!m||(Q_stricmp(m->window.name,"st_main_exit")&&Q_stricmp(m->window.name,"st_main_account"))))return qfalse;
 int translated=key;
 if(key==A_JOY0)translated=A_ENTER;else if(key==A_JOY1)translated=A_ESCAPE;
 else if(key==A_JOY11)translated=A_CURSOR_UP;else if(key==A_JOY12)translated=A_CURSOR_DOWN;
 else if(key!=A_CURSOR_UP&&key!=A_CURSOR_DOWN&&key!=A_TAB&&key!=A_ENTER&&key!=A_KP_ENTER)return qfalse;
 for(int i=0;i<m->itemCount;++i)if(m->items[i]->window.flags&WINDOW_HASFOCUS){m->cursorItem=i;break;}
 Menu_HandleKey(m,translated,down);return qtrue;
}
#ifdef ST_CONTROLS_QA
static const char* SMUI_Arg(int n){static char a[4][256];trap->Cmd_Argv(n,a[n%4],sizeof(a[0]));return a[n%4];}
qboolean ST_MainQA(){
 if(Q_stricmp(SMUI_Arg(0),"st_mainqa"))return qfalse;const char* op=SMUI_Arg(1);const char* a=SMUI_Arg(2);
 auto fail=[](const char* why){Com_Printf("ST_MAIN_FAIL %s\n",why);};menuDef_t* m=Menu_GetFocused();
 if(!strcmp(op,"click")||!strcmp(op,"focus")){
  itemDef_t* item=m?Menu_FindItemByName(m,a):NULL;if(!item)fail("native target missing");
  else{uiInfo.uiDC.cursorx=item->window.rect.x+item->window.rect.w*.4f;uiInfo.uiDC.cursory=item->window.rect.y+item->window.rect.h/2;
   Menu_HandleMouseMove(m,uiInfo.uiDC.cursorx,uiInfo.uiDC.cursory);if(!strcmp(op,"click")){Menu_HandleKey(m,A_MOUSE1,qtrue);Menu_HandleKey(m,A_MOUSE1,qfalse);}}
 }else if(!strcmp(op,"next")){if(m)SMUI_Key(A_CURSOR_DOWN,qtrue);else fail("keyboard menu missing");}
 else if(!strcmp(op,"controller")){if(m)SMUI_Key(A_JOY0,qtrue);else fail("controller menu missing");}
 else if(!strcmp(op,"assertmenu")){if(!m||Q_stricmp(a,m->window.name))fail("native destination mismatch");}
 else if(!strcmp(op,"assertroot")){if(!SMUI_IsRoot(m))fail("main-menu alias missing");}
 else if(!strcmp(op,"assertmotion")){if(smFrame.motion!=(atoi(a)!=0))fail("motion state mismatch");if(smFrame.motion?smFrame.heads<6:smFrame.heads!=0)fail("border lights ignore motion preference");}
 else if(!strcmp(op,"sample"))Com_Printf("ST_MAIN_ANIM motion=%d heads=%d x=%.3f y=%.3f focus=%s\n",smFrame.motion,smFrame.heads,smFrame.first.x,smFrame.first.y,smFrame.focus);
 else if(!strcmp(op,"assertfocus")){if(strcmp(a,smFrame.focus))fail("hover does not light native button");}
 else fail("unknown QA operation");return qtrue;
}
#endif
