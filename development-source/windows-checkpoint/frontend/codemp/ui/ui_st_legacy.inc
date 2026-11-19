/* Presentation bridge for the remaining native multiplayer menus. */
static struct {menuDef_t* top;itemDef_t* item;bool connected,bypass;qhandle_t focusArt[3];} lui;
#ifdef ST_CONTROLS_QA
static char luiLastTheme[64];
#endif

static bool LUI_Name(const char* a,const char* b){return a&&Q_stricmp(a,b)==0;}
static bool LUI_Menu(const menuDef_t* m){
 if(!m||!m->window.name||!m->window.name[0])return false;
 const char* n=m->window.name;
 return !LUI_Name(n,"main")&&!LUI_Name(n,"mainMenu")&&!LUI_Name(n,"playerMenu")&&!LUI_Name(n,"ingame_player")&&
  !LUI_Name(n,"controlsMenu")&&!LUI_Name(n,"ingame_controls")&&!LUI_Name(n,"setup_menu")&&!LUI_Name(n,"ingame_setup");
}
static bool LUI_Rail(const menuDef_t* m){return LUI_Name(m->window.name,"multiplayermenu")||LUI_Name(m->window.name,"ingame");}
static bool LUI_Full(const menuDef_t* m){return m->fullScreen||(m->window.rect.w>=630&&m->window.rect.h>=470&&!(m->window.flags&WINDOW_POPUP));}
static bool LUI_MainModal(const menuDef_t* m){return LUI_Name(m->window.name,"st_main_account")||LUI_Name(m->window.name,"st_main_exit");}
static void LUI_BeginFrame(menuDef_t* forced=NULL){
 lui.top=forced?forced:Menu_GetFocused();lui.item=NULL;lui.connected=RUI_Connected();lui.bypass=false;
 if(!LUI_Menu(lui.top)||LUI_MainModal(lui.top))return;
 lui.focusArt[0]=trap->R_RegisterShaderNoMip("ui/assets/sabertrials/focus");
 lui.focusArt[1]=trap->R_RegisterShaderNoMip("ui/assets/sabertrials/pause_focus");
 lui.focusArt[2]=trap->R_RegisterShaderNoMip("ui/assets/sabertrials/profile_name_glow");
 const vec4_t plain={.023f,.055f,.078f,1},shade={.002f,.012f,.019f,.72f};
 if(!lui.connected||!LUI_Name(lui.top->window.name,"multiplayermenu"))UI_FillRect(0,0,640,480,lui.connected?shade:plain);
}
static void LUI_EndFrame(){lui.top=NULL;lui.item=NULL;}
static qboolean LUI_IsFullscreen(){
 menuDef_t* m=Menu_GetFocused();if(LUI_Menu(m))return RUI_Connected()?qfalse:qtrue;
 return RUI_IsFullscreen();
}
qboolean ST_LegacyShouldPaint(menuDef_t* m){
 if(!LUI_Menu(lui.top)||m==lui.top||(lui.top->window.flags&WINDOW_POPUP))return qtrue;
 // The focused full page owns the canvas; legacy full pages sometimes leave
 // their parent visible. Keep underlying layers for actual popups.
 return !LUI_Full(lui.top)?qtrue:qfalse;
}
static void LUI_Panel(float x,float y,float w,float h,bool gold=false){
 if(w<=0||h<=0)return;
 const vec4_t panel={.008f,.032f,.048f,.98f};
 UI_FillRect(x+1,y+1,w-2,h-2,panel);
 RUI_FieldArt(gold?"panel_idle":"field_idle",x,y,w,h);
}
static void LUI_Frame(){
 SMUI_Image("ui/assets/sabertrials/rollout/frame",0,0,640,480);
 if(RUI_Motion()){
  static const std::vector<stmain::Point> p={{3,21},{17,5},{623,5},{637,21},{637,460},{623,478},{17,478},{3,460},{3,21}};
  float phase=stmain::phase(uiInfo.uiDC.realTime,true,12500);
  for(int i=0;i<3;++i)RUI_Light(p,phase+i/3.f,ruCyan);
 }
}
#include "ui_st_about_server.inc"

qboolean ST_LegacyMenuBegin(menuDef_t* m){
 if(!lui.top||!LUI_Menu(m))return qfalse;
 const auto& r=m->window.rect;
 if(LUI_Name(m->window.name,"multiplayermenu")){
  SMUI_Image("ui/assets/sabertrials/arena.tga",0,0,640,480);
  const vec4_t shade={.002f,.012f,.019f,.57f};UI_FillRect(0,0,640,480,shade);
  RUI_Image("logo",180,28,280,85);
 }else if(LUI_Name(m->window.name,"ingame")){
  if(trap->Cvar_VariableValue("st_uiPauseShell")!=0)RUI_Image("wordmark",30,63,153,15);
 }else if(LUI_Name(m->window.name,"joinserver")){
  RUI_Image("wordmark",18,10,132,13);
  SCUI_Label(162,10,90,.70f,"Find a Server",ruWhite);
 }else if(LUI_Name(m->window.name,"Connect")){
  ST_DrawBrand(105, 24, 153, 111, .62f);
 }else if(!LUI_Full(m)&&r.w>40&&r.h>26&&r.w<628){
  LUI_Panel(r.x,r.y,r.w,r.h,true);
  if(LUI_Name(m->window.name,"ingame_about"))LUI_AboutServer(r);
  if(LUI_Name(m->window.name,"ingame_playerforce"))for(int j=0;j<m->itemCount;++j){
   const auto* i=m->items[j];if(i->window.ownerDraw!=UI_FORCE_RANK_LEVITATION||i->text)continue;
   for(int rank=1;rank<=3;++rank){char label[2]={char('0'+rank),0};float cx=i->window.rect.x+i->textalignx+8+(rank-1)*20;RUI_Text(cx-RUI_Width(label,.64f)/2,r.y+112,.64f,label,ruCyan);}break;
  }
 }
 return qtrue;
}
void ST_LegacyMenuEnd(menuDef_t* m){
 if(!lui.top||!LUI_Menu(m))return;
#ifdef ST_CONTROLS_QA
 if(m==lui.top)Q_strncpyz(luiLastTheme,m->window.name,sizeof(luiLastTheme));
#endif
 if((m==lui.top||LUI_Rail(m))&&(LUI_Full(m)||LUI_Rail(m))&&!LUI_MainModal(m))LUI_Frame();
}
static bool LUI_EndWith(const char* s,const char* suffix){size_t n=s?strlen(s):0,k=strlen(suffix);return n>=k&&!Q_stricmp(s+n-k,suffix);}
static bool LUI_Ghost(const itemDef_t* i,const menuDef_t* m){
 if(!(i->window.flags&WINDOW_DECORATION))return false;
 if(i->window.background)for(qhandle_t shader:lui.focusArt)if(i->window.background==shader)return true;
 const char* n=i->window.name;if(!n)return false;
 if(LUI_EndWith(n,"_glow")||!Q_stricmpn(n,"mainhighlight",13)||LUI_Name(n,"button_glow2")||LUI_Name(n,"applyjoinbutton"))return true;
 if(LUI_Name(n,"st_editor_arena")||LUI_Name(n,"st_editor_shade")||LUI_Name(n,"st_editor_edge")||LUI_Name(n,"st_editor_cardedge")||LUI_Name(n,"arena")||LUI_Name(n,"shade"))return true;
 if(LUI_Name(m->window.name,"rulesMenu_games")&&(LUI_Name(n,"st_editor_ruledetails")||LUI_Name(n,"setup_background")))return true;
 if(LUI_Name(n,"background_pic"))return i->window.rect.w>=m->window.rect.w-3&&i->window.rect.h>=m->window.rect.h-3;
 if(LUI_Rail(m))return LUI_EndWith(n,"_icon")||LUI_EndWith(n,"_line")||LUI_Name(n,"rail")||LUI_Name(n,"rail_edge")||LUI_Name(n,"brand")||LUI_Name(n,"starwars")||LUI_Name(n,"multiplayer")||LUI_Name(n,"section")||LUI_Name(n,"subtitle")||LUI_Name(n,"rank_note");
 if(LUI_Name(m->window.name,"joinserver")&&LUI_Name(n,"join_title"))return true;
 if(LUI_Name(m->window.name,"Connect")&&LUI_Name(n,"miniFrame"))return true;
 // The two Force title items share a name; retain the title and omit the old instruction.
 if(LUI_Name(m->window.name,"ingame_playerforce")&&(LUI_Name(n,"forceranktitle2")||(LUI_Name(n,"playerconfigtitle")&&i->text&&LUI_Name(i->text,"@MENUS_SPEND_YOUR_POINTS_BY"))))return true;
 return false;
}
static const char* LUI_RailIcon(const char* n){
 struct Icon {const char* id;const char* art;};static const Icon icons[]={
  {"joinserver_button","join"},{"startserver_button","settings"},{"quickserver_button","play"},{"playdemo_button","camera"},{"ranked","rank"},{"tournament","trophy"},{"rules_button","info"},
  {"about","info"},{"join","join"},{"player","player"},{"vote","vote"},{"controls","controls"},{"setup","settings"},{"photo","camera"},{"respawn","refresh"},{"exit","exit"},{"account_link","player"}};
 for(const auto& e:icons)if(LUI_Name(n,e.id))return e.art;return NULL;
}
static bool LUI_Button(const itemDef_t* i){
 return !(i->window.flags&WINDOW_DECORATION)&&i->window.foreColor[3]>.05f&&i->text&&i->text[0]&&i->window.rect.w>=20&&i->window.rect.h>=13&&
  (i->type==ITEM_TYPE_BUTTON||(i->type==ITEM_TYPE_TEXT&&i->action));
}
static bool LUI_Value(const itemDef_t* i){return i->type==ITEM_TYPE_EDITFIELD||i->type==ITEM_TYPE_NUMERICFIELD||i->type==ITEM_TYPE_MULTI||i->type==ITEM_TYPE_YESNO||i->type==ITEM_TYPE_BIND;}
static bool LUI_Focus(const itemDef_t* i){return i->parent==lui.top&&(i->window.flags&WINDOW_HASFOCUS);}
static bool LUI_CenterAction(const char* name){
 return LUI_Name(name,"back")||LUI_Name(name,"apply")||LUI_Name(name,"cancel")||LUI_Name(name,"done")||
  LUI_Name(name,"yes")||LUI_Name(name,"no")||LUI_Name(name,"previous")||LUI_Name(name,"next");
}
static bool LUI_Selected(const itemDef_t* item){
 if(item->window.foreColor[0]<=.95f)return false;
 const char* group=item->window.group;
 const char* name=item->window.name;
 return LUI_EndWith(group,"_submenu")||LUI_Name(group,"grpbutton")||LUI_Name(group,"grpTabs")||
  (name&&!Q_stricmpn(name,"typebut_",8));
}
static bool LUI_Primary(const char* name){
 return LUI_Name(name,"applyjoin")||LUI_Name(name,"applycurrent")||LUI_Name(name,"newgame_begin")||
  LUI_Name(name,"join_button")||LUI_Name(name,"accept")||LUI_Name(name,"apply");
}
int ST_LegacyItemWindow(itemDef_t* i){
 auto* m=(menuDef_t*)i->parent;if(!lui.top||!LUI_Menu(m))return 0;
 if(LUI_Ghost(i,m))return 2;
 const auto& r=i->window.rect;bool focus=LUI_Focus(i);const char* n=i->window.name;
 if(r.w<4||r.h<4)return 0;
 if((i->window.flags&WINDOW_DECORATION)&&(LUI_Name(n,"brand")||LUI_Name(n,"st_editor_brand"))&&i->text){
  std::string wordmark;for(const char* p=i->text;*p;++p)if(*p!=' ')wordmark+=*p;
  if(LUI_Name(wordmark.c_str(),"SABERTRIALS")){RUI_Image("wordmark",r.x,r.y+2,std::min(153.f,r.w),16);return 2;}
 }
 if(LUI_Name(m->window.name,"ingame_playerforce")&&(LUI_Name(n,"forcedivlight")||LUI_Name(n,"forcedivdark"))){RUI_FieldArt("field_idle",r.x+7,r.y-5,r.w-14,r.h+5);return 1;}
 if(LUI_Button(i)){
  if(LUI_Rail(m)||i->text2){
   RUI_Control(r.x+1,r.y+1,r.w-2,r.h-2,"action",LUI_Primary(n),focus);
   if(LUI_Rail(m))if(const char* icon=LUI_RailIcon(n)){
    char path[MAX_QPATH];Com_sprintf(path,sizeof(path),"ui/assets/sabertrials/%s",icon);
    float h=std::min(17.f,r.h-5);SMUI_Icon(path,r.x+18,r.y+(r.h-h)/2,h,focus?ruCyan:ruWhite);
   }
  }
  return 1;
 }
 if(LUI_Value(i)&&!i->window.background)return 1;
 if(i->type==ITEM_TYPE_LISTBOX||i->type==ITEM_TYPE_TEXTSCROLL){LUI_Panel(r.x,r.y,r.w,r.h);return 1;}
 if((i->window.style==WINDOW_STYLE_FILLED||i->window.style==WINDOW_STYLE_GRADIENT)&&!i->window.background&&i->window.backColor[3]>.12f){
  if(r.w>=36&&r.h>=22&&i->window.backColor[0]<.20f&&i->window.backColor[1]<.29f){
   LUI_Panel(r.x,r.y,r.w,r.h,LUI_Name(n,"panel"));return 1;
  }
 }
 return 0;
}
itemDef_t* ST_LegacySetItem(itemDef_t* i){auto* prev=lui.item;lui.item=i;return prev;}
static bool LUI_UseItem(){return lui.top&&lui.item&&!lui.bypass&&LUI_Menu((menuDef_t*)lui.item->parent);}
void ST_LegacyEditField(itemDef_t* item,float x,float textY,const char* value){
 if(!LUI_UseItem()||item->window.background)return;
 const auto& r=item->window.rect;
 const float right=std::min(632.f,r.x+r.w);
 const float width=std::min(right-x+2,std::max(item->type==ITEM_TYPE_NUMERICFIELD?27.f:48.f,
   8.f+Text_Width(value,item->textscale,item->iMenuFont)));
 if(width<16)return;
 const float height=std::max(12.f,4.f+Text_Height("0",item->textscale,item->iMenuFont));
 // The renderer's text coordinate is the top of the line, including its font inset.
 RUI_FieldArt(LUI_Focus(item)?"field_focus":"field_idle",x-3,textY-1,width,height);
}
static void LUI_Fit(float x,float y,float w,float scale,const char* text,const float* color){
 if(w<=0||!text||!*text)return;
 bool saved=lui.bypass;lui.bypass=true;SCUI_Label(x,y,w,scale,text,color);lui.bypass=saved;
}
qboolean ST_LegacyText(float x,float y,float scale,vec4_t color,const char* text,int limit,int style,int font){
 if(!LUI_UseItem()||!text)return qfalse;
 auto* i=lui.item;auto* m=(menuDef_t*)i->parent;const auto& r=i->window.rect;
 if(LUI_Name(m->window.name,"ingame_callvote")&&LUI_Name(i->window.name,"error")&&LUI_Name(text,";"))return qtrue;
 if(!RUI_Ascii(text)||style==ITEM_TEXTSTYLE_BLINK||style==ITEM_TEXTSTYLE_PULSE){
  if(LUI_Button(i)&&!LUI_Rail(m)&&!i->text2)
   RUI_Control(r.x+1,r.y+1,r.w-2,r.h-2,"action",LUI_Primary(i->window.name)||LUI_Selected(i),LUI_Focus(i));
  return qfalse;
 }
 if(i->type==ITEM_TYPE_EDITFIELD||i->type==ITEM_TYPE_NUMERICFIELD||i->type==ITEM_TYPE_LISTBOX||i->type==ITEM_TYPE_TEXTSCROLL)return qfalse;
 float w=std::max(0.f,std::min(632.f,m->window.rect.x+m->window.rect.w-5)-x);
 if(LUI_Button(i)&&i->text2==NULL){
  float left=r.x+8,right=std::min(r.x+r.w-7,631.f);
  if(LUI_Rail(m)&&LUI_RailIcon(i->window.name))left=r.x+37;
  w=right-left;scale=std::min(.88f,std::max(.51f,r.h/34));
  float tw=RUI_Width(text,scale);if(tw>w&&tw>0)scale*=w/tw;
  bool centered=i->textalignment==ITEM_ALIGN_CENTER||LUI_CenterAction(i->window.name)||LUI_Name(text,"Cancel");
  tw=RUI_Width(text,scale);
  x=centered?left+(w-tw)/2:i->textalignment==ITEM_ALIGN_RIGHT?right-tw:left;
  y=r.y+(r.h-17*scale)/2;
  if(!LUI_Rail(m)){
   const bool navigation=LUI_Name(i->window.group,"toprow");
   const bool rulesCategory=LUI_Name(m->window.name,"rulesMenu")&&LUI_Name(i->window.group,"default_submenu");
   const float boxWidth=navigation?r.w-2:rulesCategory?r.w-14:std::min(right-left+12,std::max(27.f,tw+23.f));
   const float boxX=navigation||rulesCategory?r.x+(r.w-boxWidth)/2:
    centered?x+(tw-boxWidth)/2:i->textalignment==ITEM_ALIGN_RIGHT?x+tw+6-boxWidth:x-7;
   RUI_Control(std::max(r.x+1,boxX),r.y+1,boxWidth,r.h-2,"action",LUI_Primary(i->window.name)||LUI_Selected(i),LUI_Focus(i));
  }
  vec4_t c;MSUI_Color(c,LUI_Selected(i),LUI_Focus(i),color[0]>.4f||color[1]>.4f);c[3]=color[3];
  LUI_Fit(x,y,right-x,scale,text,c);return qtrue;
 }
 if(limit>0&&limit<(int)strlen(text))return qfalse;
 if(LUI_Name(m->window.name,"ingame_playerforce")&&LUI_Name(i->window.name,"playerconfigtitle")&&i->text&&LUI_Name(i->text,"@MENUS_CHOOSE_YOUR_FORCE_TRAINING"))text="Force Training";
 if(LUI_Name(m->window.name,"ingame_playerforce")&&LUI_Name(i->window.name,"forceranktitle")){
  float tw=std::min(92.f,RUI_Width(text,.64f));LUI_Fit(m->window.rect.x+340-tw,m->window.rect.y+112,tw,.64f,text,ruCyan);return qtrue;
 }
 const char* prefix="SABER TRIALS  /  ";if(!Q_stricmpn(text,prefix,strlen(prefix)))text+=strlen(prefix);
 const char* shorter="SABER TRIALS / ";if(!Q_stricmpn(text,shorter,strlen(shorter)))text+=strlen(shorter);
 if(LUI_Full(m)&&y<12&&i->type==ITEM_TYPE_TEXT&&(i->window.flags&WINDOW_DECORATION)){
  LUI_Fit(23,12,210,std::min(.56f,scale),text,ruWhite);return qtrue;
 }
 if(r.w>8&&x>=r.x-1&&x<r.x+r.w)w=std::min(w,r.x+r.w-x-3);
 // Native anchors for owner draws can represent individual rank/cost labels.
 // Keep their footprint and their light/dark/disabled colors.
 if(i->type==ITEM_TYPE_OWNERDRAW&&LUI_Name(i->window.name,"humanbotfield")&&r.h>=12){
  scale=std::min(scale,(r.h-3.f)/17.f);
  y=r.y+(r.h-17.f*scale)*.5f;
 }
 if(i->type==ITEM_TYPE_OWNERDRAW||LUI_Value(i))w=std::min(w,float(Text_Width(text,scale,font)));
 else if(i->textalignment==ITEM_ALIGN_CENTER&&r.w>16){float rw=RUI_Width(text,scale);if(rw>r.w-8)scale*=float(r.w-8)/rw;x=r.x+(r.w-RUI_Width(text,scale))/2;w=r.w;}
 if((i->type==ITEM_TYPE_MULTI||i->type==ITEM_TYPE_YESNO)&&!i->window.background&&r.h>=12){
  scale=std::min(scale,(r.h-4.f)/17.f);
  y=r.y+(r.h-17.f*scale)*.5f;
  if(!i->text||!*i->text||x>=i->textRect.x+i->textRect.w+7){
   const float width=std::min(std::min(632.f,r.x+r.w)-x+3,std::max(28.f,RUI_Width(text,scale)+11));
   const float height=std::min(r.h-2.f,std::max(12.f,17.f*scale+6.f));
   if(width>=18)RUI_FieldArt(LUI_Focus(i)?"field_focus":"field_idle",x-4,r.y+(r.h-height)*.5f,width,height);
  }
 }
 if(!(i->window.flags&WINDOW_DECORATION)&&LUI_Focus(i)&&(LUI_Value(i)||i->type==ITEM_TYPE_OWNERDRAW)){
  vec4_t focusColor;MSUI_Color(focusColor,false,true);focusColor[3]=color[3];
  LUI_Fit(x,y,w,scale,text,focusColor);
 }else LUI_Fit(x,y,w,scale,text,color);
 return qtrue;
}
qboolean ST_LegacyListText(itemDef_t* i,float x,float y,float width,const char* s){
 if(!LUI_UseItem()||!s||!RUI_Ascii(s))return qfalse;
 const float height=i->typeData.listbox->elementHeight;
 const float scale=std::min(i->textscale,height*.045f);
 SCUI_Fit(x,y+(height-17.f*scale)*.5f,std::max(8.f,width),scale,s,i->window.foreColor);return qtrue;
}
qboolean ST_LegacyForceRanks(const rectDef_t* r,int power,int value,int max){
 if(!LUI_UseItem()||!LUI_Name(((menuDef_t*)lui.item->parent)->window.name,"ingame_playerforce"))return qfalse;
 bool disabled=uiForcePowersDisabled[power]!=0;
 for(int rank=1;rank<=max;++rank){
  float x=r->x+(rank-1)*20,y=r->y+6;bool selected=rank<=value;const vec4_t dim={.29f,.42f,.49f,1};
  RUI_FieldArt(selected&&!disabled?"field_focus":"field_idle",x,y,16,13);
  char cost[8];Com_sprintf(cost,sizeof(cost),"%d",bgForcePowerCost[power][rank]);
  RUI_Text(x+8-RUI_Width(cost,.50f)/2,y+1.2f,.50f,cost,disabled?dim:selected?ruCyan:ruWhite);
 }
 return qtrue;
}
static void LUI_DrawPic(float x,float y,float w,float h,qhandle_t shader){
 if(LUI_UseItem()&&shader>0){
  auto& a=uiInfo.uiDC.Assets;
  if(shader==a.scrollBar){bool vert=h>w;const vec4_t c={.10f,.25f,.34f,1};UI_FillRect(vert?x+w*.45f:x,vert?y:y+h*.45f,vert?w*.10f:w,vert?h:h*.10f,c);return;}
  if(shader==a.scrollBarThumb){bool vert=lui.item->window.flags&WINDOW_HORIZONTAL?false:true;
   RUI_FieldArt("field_focus",vert?x+w*.26f:x,vert?y:y+h*.26f,vert?w*.48f:w,vert?h:h*.48f);return;}
  const char* label=shader==a.scrollBarArrowUp?"^":shader==a.scrollBarArrowDown?"v":shader==a.scrollBarArrowLeft?"<":shader==a.scrollBarArrowRight?">":NULL;
  if(label){RUI_Text(x+(w-RUI_Width(label,.55f))/2,y+(h-9)/2,.55f,label,ruCyan);return;}
 }
 UI_DrawHandlePic(x,y,w,h,shader);
}
void ST_LegacyBrowserPanel(const char* info){
 LUI_Panel(446,112,178,264,true);
 if(!info||!*info){SCUI_Label(458,126,154,.66f,"Select a server",scuMuted);return;}
 char map[MAX_QPATH],line[128];Q_strncpyz(map,Info_ValueForKey(info,"mapname"),sizeof(map));
 int gt=atoi(Info_ValueForKey(info,"gametype")),ping=atoi(Info_ValueForKey(info,"ping"));
 if(ping<=0&&!map[0]){RUI_Text(458,125,.69f,"Awaiting reply",ruCyan);return;}
 RUI_Text(458,124,.70f,STP_Mode(gt,0,0),ruCyan);RUI_Divider(458,145,152);
 if(map[0]&&!strstr(map,"..")&&!strchr(map,'\\')&&!strchr(map,':')){
  qhandle_t shot=trap->R_RegisterShaderNoMip(va("levelshots/%s",map));
  if(shot){float h=86,w=h*4/3*uiInfo.uiDC.yscale/uiInfo.uiDC.xscale;if(w>150){h*=150/w;w=150;}UI_DrawHandlePic(535-w/2,153,w,h,shot);}
  else RUI_Text(458,177,.53f,"Map preview unavailable",scuMuted);
 }
 SCUI_Fit(458,245,154,.68f,map[0]?map:"Map not reported",ruWhite);
 Com_sprintf(line,sizeof(line),"Players  %s / %s",Info_ValueForKey(info,"clients"),Info_ValueForKey(info,"sv_maxclients"));SCUI_Fit(458,270,154,.57f,line,ruWhite);
 Com_sprintf(line,sizeof(line),ping>0?"Ping  %d ms":"Awaiting reply",ping);RUI_Text(458,288,.57f,line,ping>150?ruGold:ruCyan);
 RUI_Text(458,307,.55f,atoi(Info_ValueForKey(info,"needpass"))?"Password required":"No password",ruWhite);
 RUI_Text(458,327,.53f,atoi(Info_ValueForKey(info,"wdisable"))?"Weapons: restricted":"Weapons: unrestricted",scuMuted);
 RUI_Text(458,346,.53f,atoi(Info_ValueForKey(info,"fdisable"))?"Force: restricted":"Force: unrestricted",scuMuted);
}
#ifdef ST_CONTROLS_QA
extern void ST_LegacyInventory();
extern int Item_ListBox_ThumbPosition(itemDef_t* item);
extern void UI_KeyEvent(int key,qboolean down);
qboolean ST_LegacyQA(){
 if(Q_stricmp(SMUI_Arg(0),"st_legacyqa"))return qfalse;
 const char* op=SMUI_Arg(1);const char* a=SMUI_Arg(2);auto* m=Menu_GetFocused();
 auto fail=[](const char* why){Com_Printf("ST_LEGACY_FAIL %s\n",why);};
 if(LUI_Name(op,"inventory")){Com_Printf("ST_LEGACY_INVENTORY %s\n",a);ST_LegacyInventory();}
 else if(LUI_Name(op,"assertmenu")){if(!m||!LUI_Name(m->window.name,a))fail(va("expected %s got %s",a,m?m->window.name:"none"));}
 else if(LUI_Name(op,"assertpaint")){if(!m||!LUI_Name(m->window.name,a)||!LUI_Name(luiLastTheme,a))fail(va("theme did not paint %s",a));}
 else if(LUI_Name(op,"asserttournament")){
  auto* item=m?Menu_FindItemByName(m,"tournament_desc"):NULL;
  auto* ffa=m?Menu_FindItemByName(m,"ffa_desc"):NULL;
  if(!item||!ffa||!(item->window.flags&WINDOW_VISIBLE)||(ffa->window.flags&WINDOW_VISIBLE)){
   fail("Tournament rules did not replace the previous description");return qtrue;
  }
  auto* scroll=item->typeData.textscroll;bool individual=false,team=false,reconnects=false;
  for(int j=0;j<scroll->iLineCount;++j)if(const char* line=scroll->pLines[j]){
   individual|=LUI_Name(line,"1v1 TOURNAMENT");
   team|=LUI_Name(line,"TEAM TOURNAMENT");
   reconnects|=LUI_Name(line,"RECONNECTS AND RESERVES");
  }
  if(!individual||!team||!reconnects)fail("Tournament rules headings did not load as separate lines");
  if(LUI_Name(a,"scroll")){
   uiInfo.uiDC.cursorx=item->window.rect.x+item->window.rect.w/2;
   uiInfo.uiDC.cursory=item->window.rect.y+item->window.rect.h/2;
   Menu_HandleMouseMove(m,uiInfo.uiDC.cursorx,uiInfo.uiDC.cursory);
   for(int j=0;j<6;++j)Menu_HandleKey(m,A_MWHEELDOWN,qtrue);
   if(scroll->startPos==0)fail("Tournament rules did not scroll");
  }
 }
 else if(LUI_Name(op,"click")||LUI_Name(op,"hover")){
  auto* item=m?Menu_FindItemByName(m,a):NULL;if(!item){fail(va("missing target %s",a));return qtrue;}
  uiInfo.uiDC.cursorx=item->window.rect.x+item->window.rect.w*.4f;uiInfo.uiDC.cursory=item->window.rect.y+item->window.rect.h*.5f;
  Menu_HandleMouseMove(m,uiInfo.uiDC.cursorx,uiInfo.uiDC.cursory);
  if(LUI_Name(op,"click")){Menu_HandleKey(m,A_MOUSE1,qtrue);Menu_HandleKey(m,A_MOUSE1,qfalse);}
 }else if(LUI_Name(op,"escape")){UI_KeyEvent(A_ESCAPE,qtrue);UI_KeyEvent(A_ESCAPE,qfalse);}
 else if(LUI_Name(op,"pause"))UI_SetActiveMenu(UIMENU_INGAME);
 else if(LUI_Name(op,"connected")){if(RUI_Connected()!=(atoi(a)!=0))fail("unexpected connection state");}
 else if(LUI_Name(op,"force-rank")){
  itemDef_t* item=NULL;if(m&&LUI_Name(m->window.name,"ingame_playerforce"))for(int j=0;j<m->itemCount;++j)if(m->items[j]->window.ownerDraw==UI_FORCE_RANK_SPEED){item=m->items[j];break;}
  if(!item){fail("missing Speed rank picker");return qtrue;}
  int rank=uiForcePowersRank[FP_SPEED],available=uiForceAvailable;auto r=item->window.rect;
  uiInfo.uiDC.cursorx=r.x+item->textalignx+8;uiInfo.uiDC.cursory=r.y+r.h/2;Menu_HandleMouseMove(m,uiInfo.uiDC.cursorx,uiInfo.uiDC.cursory);
  Menu_HandleKey(m,A_MOUSE1,qtrue);Menu_HandleKey(m,A_MOUSE1,qfalse);
  if(rank>=3||uiForcePowersRank[FP_SPEED]!=rank+1||uiForceAvailable!=available-bgForcePowerCost[FP_SPEED][rank+1])fail("native Force rank purchase changed");
 }
 else if(LUI_Name(op,"fixtures")){
  if(!m||!LUI_Name(m->window.name,"joinserver")||UI_SourceForLAN()!=AS_FAVORITES){fail("fixture requires private Favorites view");return qtrue;}
  for(int j=0;j<42;++j){char name[128],address[64];Com_sprintf(name,sizeof(name),j==0?"^3Saber Trials ^7Local Review":"^5Practice ^7Server %02d",j+1);Com_sprintf(address,sizeof(address),"127.0.0.1:%d",j==0&&atoi(a)>0?atoi(a):29100+j);trap->LAN_AddServer(AS_FAVORITES,name,address);}
  uiInfo.serverStatus.refreshActive=qfalse;uiInfo.serverStatus.numDisplayServers=std::min(42,trap->LAN_GetServerCount(AS_FAVORITES));uiInfo.serverStatus.currentServer=0;
  for(int j=0;j<uiInfo.serverStatus.numDisplayServers;++j)uiInfo.serverStatus.displayServers[j]=j;
  if(uiInfo.serverStatus.numDisplayServers<25)fail("not enough server fixtures");
 }else if(LUI_Name(op,"assertinfo")){
  char info[MAX_STRING_CHARS];trap->LAN_GetServerInfo(AS_FAVORITES,uiInfo.serverStatus.displayServers[0],info,sizeof(info));
  if(!LUI_Name(Info_ValueForKey(info,"mapname"),"mp/ffa3"))fail("local browser reply was not displayed");
 }else if(LUI_Name(op,"thumb")||LUI_Name(op,"drag")||LUI_Name(op,"release")||LUI_Name(op,"assertscrolled")){
  auto* item=m?Menu_FindItemByName(m,"serverlist"):NULL;if(!item||item->type!=ITEM_TYPE_LISTBOX){fail("missing server list");return qtrue;}
  auto r=item->window.rect;
  if(LUI_Name(op,"thumb")){
   uiInfo.uiDC.cursorx=r.x+r.w-SCROLLBAR_SIZE*.5f;uiInfo.uiDC.cursory=Item_ListBox_ThumbPosition(item)+SCROLLBAR_SIZE*.5f;
   Menu_HandleMouseMove(m,uiInfo.uiDC.cursorx,uiInfo.uiDC.cursory);Menu_HandleKey(m,A_MOUSE1,qtrue);
  }else if(LUI_Name(op,"drag")){uiInfo.uiDC.cursory=r.y+r.h-2*SCROLLBAR_SIZE;Menu_HandleMouseMove(m,uiInfo.uiDC.cursorx,uiInfo.uiDC.cursory);}
  else if(LUI_Name(op,"release"))Menu_HandleKey(m,A_MOUSE1,qfalse);
  else if(item->typeData.listbox->startPos<=0)fail("native scrollbar did not drag");
 }else fail("unknown QA operation");
 return qtrue;
}
#endif
