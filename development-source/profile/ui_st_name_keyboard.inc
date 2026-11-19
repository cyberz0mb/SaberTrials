/* Profile name entry using the same pointer as the native menus. */
struct SPNameKey {float x,y,w; int action; const char* label;};
static bool SPUI_Over(float x,float y,float w,float h);
enum {SPN_Shift=256,SPN_Symbols,SPN_Left,SPN_Right,SPN_Erase,SPN_Clear,SPN_Cancel,SPN_Done};
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
 spName={};
 spName.active=true;
 spName.focusNavigation=true;
 spName.focus=10;
 spName.text=spui.draft.value.name;
 spName.cursor=spName.text.size();
 spui.field=0;
 spui.scrollbar.dragging=false;
 trap->Cvar_Register(NULL,"st_uiNameKeyboard","0",CVAR_TEMP);
 trap->Cvar_Set("st_uiNameKeyboard","1");
}

static void SPN_Action(int action){
 if(action==SPN_Done){if(spName.text.find_first_not_of(' ')!=std::string::npos)SPN_Close(true);return;}
 if(action==SPN_Cancel){SPN_Close(false);return;}
 if(action==SPN_Clear){spName.text.clear();spName.cursor=0;return;}
 if(action==SPN_Shift){spName.shift=!spName.shift;return;}
 if(action==SPN_Symbols){spName.symbols=!spName.symbols;return;}
 if(action==SPN_Right){if(spName.cursor<spName.text.size())++spName.cursor;return;}
 if(action==SPN_Left){if(spName.cursor>0)--spName.cursor;return;}
 if(action==SPN_Erase){if(spName.cursor>0)spName.text.erase(--spName.cursor,1);return;}
 // These separators are rejected by the network user-info format.
 if(action<32||action>126||action=='\\'||action=='"'||action==';'||spName.text.size()>=MAX_NETNAME-1)return;
 spName.text.insert(spName.cursor++,1,char(action));
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
 UI_FillRect(76,101,488,296,panel);
 RUI_Control(74,99,492,300,"panel",false,false);
 SCUI_Text(93,112,.77f,"Player name",scuText);
 RUI_FieldArt("field_focus",93,139,454,31);
 SCUI_Fit(104,147,420,.74f,spName.text.empty()?"Enter your name":spName.text.c_str(),spName.text.empty()?scuMuted:scuText);
 if((uiInfo.uiDC.realTime/400)&1){
  const float caret=104+RUI_Width(spName.text.substr(0,spName.cursor).c_str(),.74f);
  if(caret<535)UI_FillRect(caret,145,1,17,scuCyan);
 }
 const char* rows[]= {"1234567890","qwertyuiop","asdfghjkl-","zxcvbnm_.!"};
 const char* symbols[]={"!@#$%^&*()","-_=+[]{}<>" ,"~`|:'?,./%","1234567890"};
 spName.keys.clear();
 for(int row=0;row<4;++row)for(int col=0;col<10;++col){
  int c=(spName.symbols?symbols[row]:rows[row])[col];
  if(spName.shift&&!spName.symbols&&c>='a'&&c<='z')c-='a'-'A';
  spName.keys.push_back({93+46.f*col,182+33.f*row,40,c,nullptr});
 }
 const SPNameKey utility[]={
  {93,315,50,SPN_Shift,"Shift"},{149,315,67,SPN_Symbols,spName.symbols?"Letters":"Symbols"},
  {222,315,36,SPN_Left,"<"},{264,315,84,' ',"Space"},{354,315,36,SPN_Right,">"},
  {396,315,81,SPN_Erase,"Backspace"},{483,315,64,SPN_Clear,"Clear"},
  {93,357,94,SPN_Cancel,"Cancel"},{453,357,94,SPN_Done,"Done"}
 };
 for(const auto& key:utility)spName.keys.push_back(key);
 const int focus=spName.focusNavigation?spName.focus:SPN_Hover();
 for(int i=0;i<int(spName.keys.size());++i){
  const auto& k=spName.keys[i];char letter[]={char(k.action),0};
  const bool selected=(k.action==SPN_Shift&&spName.shift)||(k.action==SPN_Symbols&&spName.symbols);
  const bool enabled=k.action!=SPN_Done||spName.text.find_first_not_of(' ')!=std::string::npos;
  vec4_t color;MSUI_Color(color,selected,i==focus,enabled);
  RUI_Control(k.x,k.y,k.w,25,k.action<256?"field":"action",selected,i==focus&&enabled);
  if(k.label)SCUI_Centered(k.x,k.y,k.w,25,.55f,k.label,color);
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
