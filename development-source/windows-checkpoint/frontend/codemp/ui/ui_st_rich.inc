/* Original transparent UI artwork. Shared by the four approved menus. */
#include "st_rich_type.h"
#include "st_main_core.h"
static const vec4_t ruWhite={.91f,.97f,1,1},ruCyan={.02f,.83f,1,1},ruGold={1,.76f,.24f,1};
static bool RUI_Ascii(const char* s){for(;*s;++s)if((unsigned char)*s<32||(unsigned char)*s>126)return false;return true;}
static float RUI_Width(const char* s,float scale){
 if(!RUI_Ascii(s))return Text_Width(s,scale,FONT_MEDIUM);
 float w=0;for(;*s;++s){if(Q_IsColorString(s)){++s;continue;}w+=richAdvance[*s-32];}
 return w*scale*.43f*uiInfo.uiDC.yscale/uiInfo.uiDC.xscale;
}
static void RUI_Image(const char* name,float x,float y,float w,float h,const float* color=NULL){
 char path[MAX_QPATH];Com_sprintf(path,sizeof(path),"ui/assets/sabertrials/rich/%s",name);
 int shader=trap->R_RegisterShaderNoMip(path);if(!shader)return;trap->R_SetColor(color);UI_DrawHandlePic(x,y,w,h,shader);trap->R_SetColor(NULL);
}
// Preserve bevel widths when the same field art spans short values or long searches.
static void RUI_FieldArt(const char* name,float x,float y,float w,float h){
 char path[MAX_QPATH];Com_sprintf(path,sizeof(path),"ui/assets/sabertrials/rich/%s",name);int shader=trap->R_RegisterShaderNoMip(path);if(!shader)return;
 float edge=std::min(w*.2f,std::min(h,24.f)*.55f*uiInfo.uiDC.yscale/uiInfo.uiDC.xscale),vertical=std::min(h*.24f,6.f);
 float xs[]={x,x+edge,x+w-edge,x+w},us[]={0,.13f,.87f,1};
 float ys[]={y,y+vertical,y+h-vertical,y+h},vs[]={0,.24f,.76f,1};
 trap->R_SetColor(NULL);for(int j=0;j<3;++j)for(int i=0;i<3;++i)trap->R_DrawStretchPic(xs[i],ys[j],xs[i+1]-xs[i],ys[j+1]-ys[j],us[i],vs[j],us[i+1],vs[j+1],shader);
}
static void RUI_Text(float x,float y,float scale,const char* s,const float* color){
 if(!RUI_Ascii(s)){vec4_t c;memcpy(c,color,sizeof(c));Text_Paint(x,y,scale,c,s,0,0,ITEM_TEXTSTYLE_NORMAL,FONT_MEDIUM);return;}
 int shader=trap->R_RegisterShaderNoMip("ui/assets/sabertrials/rich/type");
 if(!shader){vec4_t c;memcpy(c,color,sizeof(c));Text_Paint(x,y,scale,c,s,0,0,ITEM_TEXTSTYLE_NORMAL,FONT_MEDIUM);return;}
 float unit=scale*.43f,aspect=uiInfo.uiDC.yscale/uiInfo.uiDC.xscale;vec4_t c;memcpy(c,color,sizeof(c));trap->R_SetColor(c);
 for(;*s;++s){if(Q_IsColorString(s)){int n=ColorIndex(s[1]);c[0]=g_color_table[n][0];c[1]=g_color_table[n][1];c[2]=g_color_table[n][2];trap->R_SetColor(c);++s;continue;}
  int i=*s-32;float u=(i%16)*64.f/1024,v=(i/16)*80.f/1024;
  trap->R_DrawStretchPic(x-6*unit*aspect,y-3*unit,64*unit*aspect,80*unit,u,v,u+64.f/1024,v+80.f/1024,shader);
  x+=richAdvance[i]*unit*aspect;
 }trap->R_SetColor(NULL);
}
static bool RUI_Motion(){return trap->Cvar_VariableValue("st_menuMotion")!=0;}
static void RUI_Light(const std::vector<stmain::Point>& path,float phase,const float* color,float size=6){
 float total=stmain::length(path,uiInfo.uiDC.xscale,uiInfo.uiDC.yscale);if(total<=0)return;
 float aspect=uiInfo.uiDC.yscale/uiInfo.uiDC.xscale;
 for(int i=15;i>=0;--i){float t=i/15.f;auto p=stmain::sample(path,phase-t*22*uiInfo.uiDC.xscale/total,uiInfo.uiDC.xscale,uiInfo.uiDC.yscale);
  vec4_t c={color[0],color[1],color[2],.26f*(1-t)*(1-t)};RUI_Image("glow",p.x-size*aspect,p.y-size,size*2*aspect,size*2,c);
  c[0]=c[1]=c[2]=1;c[3]=.65f*(1-t)*(1-t);RUI_Image("glow",p.x-1.2f*aspect,p.y-1.2f,2.4f*aspect,2.4f,c);
  if(!i){auto next=stmain::sample(path,phase+.002f,uiInfo.uiDC.xscale,uiInfo.uiDC.yscale);bool horizontal=fabs((next.x-p.x)*uiInfo.uiDC.xscale)>=fabs((next.y-p.y)*uiInfo.uiDC.yscale);float w=(horizontal?20.f:3.f)*aspect,h=horizontal?3.f:20.f;c[3]=.85f;RUI_Image("glow",p.x-w/2,p.y-h/2,w,h,c);}
 }
}
static void RUI_Control(float x,float y,float w,float h,const char* kind,bool selected,bool focus){
 char art[32];Com_sprintf(art,sizeof(art),"%s_%s",kind,selected||focus?"focus":"idle");
 if(!strcmp(kind,"field")||!strcmp(kind,"panel"))RUI_FieldArt(art,x-1,y-1,w+2,h+2);
 else RUI_Image(art,x-1,y-1,w+2,h+2);
 if((focus||selected)&&RUI_Motion()){
  std::vector<stmain::Point> p={{x+2,y},{x+w-2,y},{x+w,y+h-5},{x+w-5,y+h},{x,y+h},{x,y+5},{x+2,y}};
  RUI_Light(p,stmain::phase(uiInfo.uiDC.realTime,true,2800),ruCyan,3.5f);
 }
}
static int RUI_Page(){menuDef_t* m=Menu_GetFocused();if(!m)return 0;const char* n=m->window.name;
 if(!Q_stricmp(n,"playerMenu")||!Q_stricmp(n,"ingame_player"))return 1;
 if(!Q_stricmp(n,"controlsMenu")||!Q_stricmp(n,"ingame_controls"))return 2;
 if(!Q_stricmp(n,"setup_menu")||!Q_stricmp(n,"ingame_setup"))return 3;return 0;
}
static bool RUI_Connected(){uiClientState_t s;trap->GetClientState(&s);return s.connState==CA_ACTIVE;}
static qboolean RUI_IsFullscreen(){if(RUI_Page())return RUI_Connected()?qfalse:qtrue;return Menus_AnyFullScreenVisible();}
static bool SSUI_CameraView();
static void RUI_Background(){
 if(!RUI_Page())return;menuDef_t* m=Menu_GetFocused();m->fullScreen=qfalse;m->window.style=0;m->window.background=0;m->window.backColor[3]=0;
 const vec4_t plain={.023f,.055f,.078f,1},body={.023f,.059f,.082f,.97f},shade={.002f,.012f,.019f,.72f};
 const bool camera=SSUI_CameraView();
 if(!RUI_Connected())UI_FillRect(0,0,640,480,plain);
 else{
  UI_FillRect(0,0,640,camera?179:480,shade);
  // Darken the header edge behind the native HUD without changing HUD settings.
  for(int i=0;i<40;++i){vec4_t fade={plain[0],plain[1],plain[2],i/39.f};UI_FillRect(450+i*2.5f,0,2.5f,147,fade);}
  UI_FillRect(550,0,90,147,plain);
 }
 vec4_t opaque={body[0],body[1],body[2],1};
 if(camera){
  const vec4_t preview={.002f,.012f,.019f,.15f};
  UI_FillRect(0,179,274,254,opaque);
  UI_FillRect(274,179,366,254,preview);
  UI_FillRect(0,433,640,47,opaque);
 }else UI_FillRect(0,147,640,333,opaque);
}
static void RUI_Shell(){
 RUI_Image("page_frame",0,0,640,480);RUI_Image("wordmark",32,20,143,15);
 vec4_t glint={1,.74f,.22f,.8f};RUI_Image("glow",52,42,100,3,glint);
 if(RUI_Motion()){
  const std::vector<stmain::Point> p={{6,27},{19,9},{620,9},{634,27},{634,451},{620,468},{21,468},{6,451},{6,27}};
  for(int i=0;i<4;++i)RUI_Light(p,stmain::phase(uiInfo.uiDC.realTime,true,12000)+i*.25f,ruCyan);
 }
}
static void RUI_Divider(float x,float y,float w){const vec4_t c={.08f,.38f,.46f,.8f};UI_FillRect(x,y,w,.45f,c);}
