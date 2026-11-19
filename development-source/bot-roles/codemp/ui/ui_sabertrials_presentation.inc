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
static void ST_UIBrowserPanel(const char*info) {
 char map[MAX_QPATH],line[192];int gt,ping,shader=0,needpass;
 const float*accent;float badge[4]={.045f,.21f,.29f,.95f};
 STP_Box(&stpUIPainter,446,112,180,264,stpInk);
 if(!info||!*info){
  STP_UIText(458,132,156,.78f,"SELECT A SERVER",stpCyan,0);
  STP_UIText(458,161,156,.65f,"Map and rules appear here.",stpMuted,0);
  STP_UIText(458,191,156,.65f,"Refresh to find servers.",stpMuted,0);return;
 }
 Q_strncpyz(map,Info_ValueForKey(info,"mapname"),sizeof(map));
 gt=atoi(Info_ValueForKey(info,"gametype"));ping=atoi(Info_ValueForKey(info,"ping"));needpass=atoi(Info_ValueForKey(info,"needpass"));
 STP_UIFill(458,123,156,22,badge);
 Com_sprintf(line,sizeof(line),"MODE / %s",STP_Mode(gt,0,0));
 STP_UIText(466,126,140,.68f,line,stpCyan,0);
 if(map[0]&&!strstr(map,"..")&&!strchr(map,'\\'))shader=trap->R_RegisterShaderNoMip(va("levelshots/%s",map));
 if(shader){
  float w=86.f*(4.f/3.f)*uiInfo.uiDC.yscale/uiInfo.uiDC.xscale,h=86.f;
  if(w>156.f){h*=156.f/w;w=156.f;}
  STP_UIFill(458,154,156,86,stpInk);
  trap->R_SetColor(NULL);UI_DrawHandlePic(458+(156-w)/2,154+(86-h)/2,w,h,shader);
 }
 else{STP_UIFill(458,154,156,86,stpInk);STP_UIText(470,185,132,.65f,"Map preview unavailable",stpMuted,0);}
 STP_UIText(458,244,156,.74f,map[0]?map:"Map not reported",stpText,0);
 Com_sprintf(line,sizeof(line),"Players  %s / %s",Info_ValueForKey(info,"clients"),Info_ValueForKey(info,"sv_maxclients"));
 STP_UIText(458,266,156,.66f,line,stpText,0);
 accent=ping>150?stpGold:stpCyan;
 Com_sprintf(line,sizeof(line),"Ping  %s",ping>0?va("%d ms",ping):"Awaiting reply");STP_UIText(458,284,156,.66f,line,accent,0);
 STP_UIText(458,302,156,.63f,needpass?"[LOCK] Password required":"[OPEN] No password",stpText,0);
 Com_sprintf(line,sizeof(line),"Weapons: %s",atoi(Info_ValueForKey(info,"wdisable"))?"restricted":"all enabled");STP_UIText(458,320,156,.62f,line,stpMuted,0);
 Com_sprintf(line,sizeof(line),"Force: %s",atoi(Info_ValueForKey(info,"fdisable"))?"restricted":"all enabled");STP_UIText(458,337,156,.62f,line,stpMuted,0);
 STP_UIText(458,359,156,.55f,"Server-reported / rank unverified",stpMuted,0);
}
static void ST_UIPresentation(void) {
 menuDef_t*menu=Menu_GetFocused();
 trap->Cvar_Register(NULL,"st_notifications","1",CVAR_ARCHIVE);
 STP_ObserveNotices(trap->Cvar_VariableStringBuffer,uiInfo.uiDC.realTime);
 if(menu&&!Q_stricmp(menu->window.name,"joinserver")){
  char info[MAX_STRING_CHARS]="";int index=uiInfo.serverStatus.currentServer;
  if(index>=0&&index<uiInfo.serverStatus.numDisplayServers)
   trap->LAN_GetServerInfo(UI_SourceForLAN(),uiInfo.serverStatus.displayServers[index],info,sizeof(info));
  ST_UIBrowserPanel(info);
 }
 if(trap->Cvar_VariableValue("st_notifications")!=0)STP_DrawNoticeAt(&stpUIPainter,&stpNotice,uiInfo.uiDC.realTime,210,427,402);
}
