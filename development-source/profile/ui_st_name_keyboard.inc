/* Profile name entry using the same pointer as the native menus. */
#include "qcommon/st_keyboard_layout.h"
#include "qcommon/st_utf8.h"
struct SPNameKey {float x,y,w; int action; const char* label;};
static bool SPUI_Over(float x,float y,float w,float h);
enum {SPN_Shift=0x110000,SPN_Symbols,SPN_Left,SPN_Right,SPN_Erase,SPN_Clear,SPN_Cancel,SPN_Done,SPN_Language,SPN_Color};
static struct {
 bool active,shift,symbols,focusNavigation;
 size_t cursor;
 int focus;
 std::string text;
 std::vector<SPNameKey> keys;
} spName;

static void SPN_Close(bool keep){
 if(!spName.active)return;
 if(keep)spui.draft.value.name=spName.text;
 spName.active=false;
 spui.field=0;
 trap->Cvar_Set("st_uiNameKeyboard","0");
}

static void SPN_Open(){
 trap->Cvar_Register(NULL,"st_keyboardLanguage","0",CVAR_ARCHIVE);
 spName={};
 spName.active=true;
 spName.focusNavigation=true;
 spName.focus=stkeys::columns;
 spName.text=spui.draft.value.name;
 spName.cursor=spName.text.size();
 spui.field=0;
 spui.scrollbar.dragging=false;
 trap->Cvar_Register(NULL,"st_uiNameKeyboard","0",CVAR_TEMP);
 trap->Cvar_Set("st_uiNameKeyboard","1");
}

static bool SPN_ColorToken(size_t at){
 return at+1<spName.text.size()&&Q_IsColorString(spName.text.c_str()+at);
}
static int SPN_Layout(){
 return stkeys::index((int)trap->Cvar_VariableValue("st_keyboardLanguage"),(int)trap->Cvar_VariableValue("st_menuLanguage"));
}
static size_t SPN_Previous(){
 if(spName.cursor>=2&&SPN_ColorToken(spName.cursor-2))return spName.cursor-2;
 return ST_UTF8Previous(spName.text.c_str(),(int)spName.cursor);
}
static bool SPN_HasName(){
 for(size_t i=0;i<spName.text.size();++i){
  if(SPN_ColorToken(i)){++i;continue;}
  if(spName.text[i]!=' ')return true;
 }
 return false;
}
static int SPN_CurrentColor(){
 int color=7;
 for(size_t i=0;i+1<spName.cursor&&i+1<spName.text.size();++i)
  if(SPN_ColorToken(i)){color=spName.text[i+1]-'0';++i;}
 return color;
}

static void SPN_Action(int action){
 if(action>=SPN_Color&&action<SPN_Color+10){
  const char code=char('0'+action-SPN_Color);
  spName.cursor=std::min(spName.cursor,spName.text.size());
  if(spName.cursor>0&&SPN_ColorToken(spName.cursor-1))--spName.cursor;
  if(SPN_ColorToken(spName.cursor)){spName.text[spName.cursor+1]=code;spName.cursor+=2;}
  else if(spName.cursor>=2&&SPN_ColorToken(spName.cursor-2))spName.text[spName.cursor-1]=code;
  else if(spName.text.size()+2<=MAX_NETNAME-1){
   spName.text.insert(spName.cursor,std::string("^")+code);spName.cursor+=2;
  }
  return;
 }
 if(action==SPN_Done){if(SPN_HasName())SPN_Close(true);return;}
 if(action==SPN_Cancel){SPN_Close(false);return;}
 if(action==SPN_Clear){spName.text.clear();spName.cursor=0;return;}
 if(action==SPN_Shift){spName.shift=!spName.shift;return;}
 if(action==SPN_Language){trap->Cvar_Set("st_keyboardLanguage",va("%d",stkeys::next((int)trap->Cvar_VariableValue("st_keyboardLanguage"))));spName.symbols=false;return;}
 if(action==SPN_Symbols){spName.symbols=!spName.symbols;return;}
 if(action==SPN_Right){if(spName.cursor<spName.text.size()){int n;ST_UTF8Read(spName.text.c_str()+spName.cursor,&n);spName.cursor+=SPN_ColorToken(spName.cursor)?2:n;}return;}
 if(action==SPN_Left){spName.cursor=SPN_Previous();return;}
 if(action==SPN_Erase){const size_t prev=SPN_Previous();spName.text.erase(prev,spName.cursor-prev);spName.cursor=prev;return;}
 // These separators are rejected by the network user-info format.
 if(action<32||(action>=127&&action<160)||action=='\\'||action=='"'||action==';')return;
 char bytes[4];const int n=ST_UTF8Write(action,bytes);
 if(!n||spName.text.size()+n>MAX_NETNAME-1)return;
 spName.text.insert(spName.cursor,bytes,n);spName.cursor+=n;
}

static int SPN_Hover(){
 for(int i=0;i<int(spName.keys.size());++i){const auto& k=spName.keys[i];if(SPUI_Over(k.x,k.y,k.w,25))return i;}
 return -1;
}

static void SPN_MoveFocus(int dx,int dy){
 if(spName.keys.empty())return;
 spName.focusNavigation=true;
 const auto& from=spName.keys[spName.focus];
 int best=spName.focus;
 float distance=10000;
 for(int i=0;i<int(spName.keys.size());++i){
  const auto& to=spName.keys[i];
  const float x=to.x+to.w*.5f-from.x-from.w*.5f,y=to.y-from.y;
  if(dx?(x*dx<=0||y!=0):y*dy<=0)continue;
  const float score=dx?fabsf(x):fabsf(y)*12+fabsf(x);
  if(score<distance){distance=score;best=i;}
 }
 spName.focus=best;
}

static void SPN_Draw(){
 const vec4_t shade={.008f,.021f,.029f,.74f};
 UI_FillRect(8,45,624,419,shade);
 const vec4_t panel={.015f,.043f,.061f,.98f};
 UI_FillRect(76,101,488,332,panel);
 RUI_Control(74,99,492,336,"panel",false,false);
 SCUI_Text(93,112,.77f,"Player name",scuText);
 RUI_FieldArt("field_focus",93,139,454,31);
 SCUI_Fit(104,147,420,.74f,spName.text.empty()?"Enter your name":spName.text.c_str(),spName.text.empty()?scuMuted:scuText);
 if((uiInfo.uiDC.realTime/400)&1){
  const float caret=104+RUI_Width(spName.text.substr(0,spName.cursor).c_str(),.74f);
  if(caret<535)UI_FillRect(caret,145,1,17,scuCyan);
 }
 spName.keys.clear();
 const int layout=SPN_Layout();
 for(int i=0;i<stkeys::count;++i){
  const int c=stkeys::character(layout,i,spName.shift,spName.symbols);
  spName.keys.push_back({93+41.5f*(i%stkeys::columns),182+33.f*(i/stkeys::columns),38,c,nullptr});
 }
 static char languageLabel[40];
 Com_sprintf(languageLabel,sizeof(languageLabel),trap->Cvar_VariableValue("st_keyboardLanguage")?"%s":"Auto (%s)",stkeys::layouts[layout].name);
 const SPNameKey utility[]={
  {93,315,50,SPN_Shift,"Shift"},{149,315,67,SPN_Symbols,spName.symbols?"ABC":"123 / #"},
  {222,315,36,SPN_Left,"<"},{264,315,84,' ',"Space"},{354,315,36,SPN_Right,">"},
  {396,315,81,SPN_Erase,"Backspace"},{483,315,64,SPN_Clear,"Clear"},
  {93,393,94,SPN_Cancel,"Cancel"},{235,393,150,SPN_Language,languageLabel},{453,393,94,SPN_Done,"Done"}
 };
 for(const auto& key:utility)spName.keys.push_back(key);
 for(int col=0;col<10;++col)spName.keys.push_back({93+46.f*col,352,40,SPN_Color+(col+1)%10,nullptr});
 SCUI_Text(93,342,.45f,"Text color",scuMuted);
 const int focus=spName.focusNavigation?spName.focus:SPN_Hover();
 for(int i=0;i<int(spName.keys.size());++i){
  const auto& k=spName.keys[i];char letter[5]={};
  if(!k.label&&k.action<SPN_Shift)ST_UTF8Write(k.action,letter);
  const bool isColor=k.action>=SPN_Color&&k.action<SPN_Color+10;
  const bool selected=(k.action==SPN_Shift&&spName.shift)||(k.action==SPN_Symbols&&spName.symbols)||
   (isColor&&k.action-SPN_Color==SPN_CurrentColor());
  const bool enabled=k.action!=SPN_Done||SPN_HasName();
  vec4_t color;MSUI_Color(color,selected,i==focus,enabled);
  RUI_Control(k.x,k.y,k.w,25,k.action<SPN_Shift||isColor?"field":"action",selected,i==focus&&enabled);
  if(isColor){
   const int n=k.action-SPN_Color;
   const vec4_t rim={.65f,.78f,.84f,1};
   UI_FillRect(k.x+6,k.y+4,k.w-12,6,rim);
   UI_FillRect(k.x+7,k.y+5,k.w-14,4,g_color_table[n]);
   const float x=k.x+(k.w-RUI_Width("^",.52f)-RUI_Width(std::to_string(n).c_str(),.52f))*.5f;
   const char digit[]={char('0'+n),0};
   RUI_Text(x,k.y+12,.52f,"^",color);
   RUI_Text(x+RUI_Width("^",.52f),k.y+12,.52f,digit,color);
  }
  else if(k.label)SCUI_Centered(k.x,k.y,k.w,25,.55f,k.label,color);
  else if(k.action>=128)SCUI_Centered(k.x,k.y,k.w,25,.75f,letter,color);
  else{
   constexpr float scale=.83f;
   const int width=Text_Width(letter,scale,FONT_SMALL2),height=Text_Height(letter,scale,FONT_SMALL2);
   Text_Paint(k.x+(k.w-width)*.5f,k.y+(25-height)*.5f,scale,color,letter,0,0,ITEM_TEXTSTYLE_NORMAL,FONT_SMALL2);
  }
 }
}

static void SPN_Key(int key,qboolean down){
 if(!down)return;
 if(key&K_CHAR_FLAG){SPN_Action(key&~K_CHAR_FLAG);return;}
 switch(key){
 case A_MOUSE1:{
  const int hit=spName.focusNavigation&&trap->Cvar_VariableValue("st_uiPadClick")?spName.focus:SPN_Hover();
  if(hit>=0&&hit<int(spName.keys.size()))SPN_Action(spName.keys[hit].action);
  break;}
 case A_JOY2: SPN_Action(SPN_Erase);break;
 case A_JOY3: SPN_Action(SPN_Shift);break;
 case A_ESCAPE: SPN_Action(SPN_Cancel);break;
 case A_ENTER: SPN_Action(SPN_Done);break;
 case A_BACKSPACE: SPN_Action(SPN_Erase);break;
 case A_JOY13:case A_CURSOR_LEFT:SPN_MoveFocus(-1,0);break;
 case A_JOY14:case A_CURSOR_RIGHT:SPN_MoveFocus(1,0);break;
 case A_JOY11:case A_CURSOR_UP:SPN_MoveFocus(0,-1);break;
 case A_JOY12:case A_CURSOR_DOWN:SPN_MoveFocus(0,1);break;
 default:break;
 }
}
