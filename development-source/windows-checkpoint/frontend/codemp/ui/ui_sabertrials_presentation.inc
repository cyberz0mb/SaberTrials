/* Saber Trials UI presentation. GPL-2.0-only. */
#include "st_presentation_draw.inc"
#include "st_presentation_notices.inc"
static void STP_UIFill(float x,float y,float w,float h,const float*c){UI_FillRect(x,y,w,h,c);}
static void STP_UIText(float x,float y,float width,float scale,const char*text,const float*c,int right) {
 vec4_t color;float w=Text_Width(text,scale,FONT_SMALL2);memcpy(color,c,sizeof(color));
 if(w>width&&w>0){scale*=width/w;w=width;}
 Text_Paint(right?x+width-w:x,y,scale,color,text,0,0,ITEM_TEXTSTYLE_NORMAL,FONT_SMALL2);
}
static void STP_UIIcon(float x,float y,float size,int icon,const float*c) {
 float w=size*uiInfo.uiDC.yscale/uiInfo.uiDC.xscale;
 trap->R_SetColor(c);UI_DrawHandlePic(x+(size-w)/2,y,w,size,icon);trap->R_SetColor(NULL);
}
static const STPPainter stpUIPainter={STP_UIFill,STP_UIText,STP_UIIcon};
extern void ST_LegacyBrowserPanel(const char* info);
static void ST_UIPresentation(void) {
 menuDef_t*menu=Menu_GetFocused();
 trap->Cvar_Register(NULL,"st_notifications","1",CVAR_ARCHIVE);
 STP_ObserveNotices(trap->Cvar_VariableStringBuffer,uiInfo.uiDC.realTime);
 if(menu&&!Q_stricmp(menu->window.name,"joinserver")){
  char info[MAX_STRING_CHARS]="";int index=uiInfo.serverStatus.currentServer;
  if(index>=0&&index<uiInfo.serverStatus.numDisplayServers)
   trap->LAN_GetServerInfo(UI_SourceForLAN(),uiInfo.serverStatus.displayServers[index],info,sizeof(info));
  ST_LegacyBrowserPanel(info);
 }
 if(trap->Cvar_VariableValue("st_notifications")!=0)STP_DrawNoticeAt(&stpUIPainter,&stpNotice,uiInfo.uiDC.realTime,210,427,402);
}
