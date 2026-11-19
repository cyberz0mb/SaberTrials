// The console keeps ownership of editing, command history and execution.
#include "cl_st_console_pad.h"
extern void Console_Key(int key);
extern void Message_Key(int key);
extern qboolean STCT_DrawInput(const char*,int,float,float);

namespace {
enum PadConsoleAction { Shift=256, Symbols, CaretLeft, CaretRight, Erase, Clear, Complete, Execute };
struct PadConsoleKey { int x,y,width,action; const char* label; };
constexpr int keyHeight=26;
constexpr int gridSize=40;
constexpr PadConsoleKey actions[]={
 {56,415,50,Shift,"Shift"}, {112,415,64,Symbols,"Symbols"}, {182,415,34,CaretLeft,"<"},
 {222,415,100,' ',"Space"}, {328,415,34,CaretRight,">"}, {368,415,77,Erase,"Backspace"},
 {451,415,50,Clear,"Clear"}, {507,415,71,Complete,"Complete"}, {446,450,132,Execute,"Run command"}
};
constexpr int keyCount=gridSize+ARRAY_LEN(actions);
struct PadConsoleState {
 int catcher=0;
 bool shift=false,symbols=false,pointer=false;
 int x=81,y=314,focus=0;
} padConsole;

PadConsoleKey Con_PadKey(int i) {
 if(i>=gridSize)return actions[i-gridSize];
 static constexpr const char* letters[]={"1234567890","qwertyuiop","asdfghjkl-","zxcvbnm_.,"};
 static constexpr const char* symbols[]={"!@#$%^&*()","-_=+[]{}<>","~`|:'?,./%","\\\";0123456"};
 const int row=i/10,col=i%10;
 int action=(padConsole.symbols?symbols[row]:letters[row])[col];
 if(padConsole.shift&&!padConsole.symbols&&action>='a'&&action<='z')action-='a'-'A';
 return {56+53*col,287+32*row,45,action,nullptr};
}

void Con_PadMoveFocus(int dx,int dy) {
 const auto from=Con_PadKey(padConsole.focus);
 int closest=10000;
 padConsole.pointer=false;
 for(int i=0;i<keyCount;++i){
  const auto to=Con_PadKey(i);
  const int x=to.x+to.width/2-from.x-from.width/2,y=to.y-from.y;
  if(dx?(x*dx<=0||y!=0):y*dy<=0)continue;
  const int distance=dx?abs(x):abs(y)*16+abs(x);
  if(distance<closest){padConsole.focus=i;closest=distance;}
 }
}

void Con_PadPress(int action) {
 const bool chat=padConsole.catcher==KEYCATCH_MESSAGE;
 field_t& field=chat?chatField:g_consoleField;
 switch(action){
  case Shift:padConsole.shift=!padConsole.shift;break;
  case Symbols:padConsole.symbols=!padConsole.symbols;break;
  case CaretLeft:Field_KeyDownEvent(&field,A_CURSOR_LEFT);break;
  case CaretRight:Field_KeyDownEvent(&field,A_CURSOR_RIGHT);break;
  case Erase:Field_CharEvent(&field,8);break;
  case Clear:{const int width=field.widthInChars;Field_Clear(&field);field.widthInChars=width;break;}
  case Complete:if(chat)Message_Key(A_ESCAPE);else Console_Key(A_TAB);break;
  case Execute:if(field.buffer[0]){if(chat)Message_Key(A_ENTER);else Console_Key(A_ENTER);}break;
  default:Field_CharEvent(&field,action);break;
 }
}
}

bool Con_AutoKeyboard(bool gamepad) {
 static cvar_t* mode=Cvar_Get("st_virtualKeyboard","0",CVAR_ARCHIVE);
 bool keyboard=Cvar_VariableIntegerValue("st_physicalKeyboard")!=0;
#ifdef ST_CONTROLS_QA
 static cvar_t* fixture=Cvar_Get("st_testKeyboardDevice","-1",CVAR_TEMP);
 if(fixture->integer>=0)keyboard=fixture->integer!=0;
#endif
 return mode->integer==1||(mode->integer==0&&gamepad&&!keyboard);
}
bool Con_PadKeyboardActive() {
 const int catcher=Key_GetCatcher();
 return Cvar_VariableIntegerValue("st_virtualKeyboard")!=2&&padConsole.catcher&&
  (catcher&(KEYCATCH_CONSOLE|KEYCATCH_MESSAGE))==padConsole.catcher&&
  (padConsole.catcher==KEYCATCH_CONSOLE||!(catcher&(KEYCATCH_UI|KEYCATCH_CGAME)));
}
void Con_SetPadKeyboard(int catcher) {padConsole={};padConsole.catcher=catcher;}
void Con_UpdatePadKeyboard(int catcher) {
 if(!(catcher&padConsole.catcher))Con_ClosePadKeyboard();
}
void Con_OpenPadKeyboard() {Con_SetPadKeyboard(KEYCATCH_CONSOLE);}
void Con_ClosePadKeyboard() {padConsole.catcher=0;}

void Con_PadKeyboardMove(int dx,int dy) {
 padConsole.pointer=true;
 padConsole.x=Com_Clampi(0,SCREEN_WIDTH,padConsole.x+dx);
 padConsole.y=Com_Clampi(0,SCREEN_HEIGHT,padConsole.y+dy);
 for(int i=0;i<keyCount;++i){
  const auto k=Con_PadKey(i);
  if(padConsole.x>=k.x&&padConsole.x<k.x+k.width&&padConsole.y>=k.y&&padConsole.y<k.y+keyHeight){padConsole.focus=i;return;}
 }
}

void Con_PadKeyboardButton(int button,int confirm) {
 const bool chat=padConsole.catcher==KEYCATCH_MESSAGE;
 if(button==confirm){
  const auto k=Con_PadKey(padConsole.focus);
  if(!padConsole.pointer||(padConsole.x>=k.x&&padConsole.x<k.x+k.width&&padConsole.y>=k.y&&padConsole.y<k.y+keyHeight))Con_PadPress(k.action);
 }else if(button==1-confirm||button==6){if(chat)Message_Key(A_ESCAPE);else Con_ToggleConsole_f();}
 else if(button==2)Con_PadPress(Erase);
 else if(button==3)Con_PadPress(Shift);
 else if(button==9||button==10){if(chat)Con_PadPress(button==9?CaretLeft:CaretRight);else Console_Key(button==9?A_CURSOR_UP:A_CURSOR_DOWN);}
 else if(!chat&&(button==16||button==17))Console_Key(button==16?A_PAGE_UP:A_PAGE_DOWN);
 else if(button>=11&&button<=14)Con_PadMoveFocus(button==13?-1:button==14?1:0,button==11?-1:button==12?1:0);
}

void Con_PadKeyboardMouseClick(){Con_PadKeyboardButton(0,0);}

void Con_DrawPadKeyboard() {
 if(!Con_PadKeyboardActive())return;
 const bool chat=padConsole.catcher==KEYCATCH_MESSAGE;
 const vec4_t panel={.014f,.042f,.064f,.98f},edge={.14f,.70f,.89f,1};
 const vec4_t idle={.032f,.095f,.133f,1},focus={.061f,.33f,.46f,1};
 vec4_t text={.87f,.95f,1,1},muted={.62f,.78f,.85f,1};
 SCR_FillRect(44,266,546,212,edge);
 SCR_FillRect(45,267,544,210,panel);
 const char* title=chat?(chat_playerNum>=0?"Private message":chat_team?"Team chat":"Chat"):"Console keyboard";
 re->Font_DrawString(56,272,title,text,cls.menuFont,-1,.66f);
 if(chat){
  SCR_FillRect(45,220,544,42,panel);
  SCR_FillRect(45,220,544,1,edge);
  if(!STCT_DrawInput(chatField.buffer,chatField.cursor,56,230))
   Field_BigDraw(&chatField,56,230,qtrue,qtrue);
 }
 for(int i=0;i<keyCount;++i){
  const auto k=Con_PadKey(i);
  const bool selected=(k.action==Shift&&padConsole.shift)||(k.action==Symbols&&padConsole.symbols);
  const bool highlighted=i==padConsole.focus;
  SCR_FillRect(k.x,k.y,k.width,keyHeight,highlighted||selected?edge:idle);
  SCR_FillRect(k.x+1,k.y+1,k.width-2,keyHeight-2,highlighted||selected?focus:panel);
  char glyph[]={static_cast<char>(k.action),0};
  const char* label=chat&&k.action==Execute?"Send message":chat&&k.action==Complete?"Cancel":
   k.action==Symbols&&padConsole.symbols?"Letters":k.label?k.label:glyph;
  const float scale=k.label?.65f:.85f;
  const int width=re->Font_StrLenPixels(label,cls.menuFont,scale),height=re->Font_HeightPixels(cls.menuFont,scale);
  re->Font_DrawString(k.x+(k.width-width)/2,k.y+(keyHeight-height)/2,label,text,cls.menuFont,-1,scale);
 }
 re->Font_DrawString(56,457,chat?"Bumpers move the caret":"Bumpers: command history   Triggers: scroll",muted,cls.menuFont,-1,.64f);
 if(padConsole.pointer){
  SCR_FillRect(padConsole.x-2,padConsole.y-2,5,5,edge);
  SCR_FillRect(padConsole.x-1,padConsole.y-1,3,3,text);
 }
}
