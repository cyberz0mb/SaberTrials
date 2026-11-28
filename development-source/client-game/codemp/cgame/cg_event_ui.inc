#include "game/st_event_ui.h"

/* Reject partial parses, signs, whitespace, overflow and command punctuation. */
static int CG_STEventNumber(const char*text,int maximum) {
 int value=0;if(!text||!*text)return -1;
 for(;*text;text++){
  if(*text<'0'||*text>'9'||value>(maximum-(*text-'0'))/10)return -1;
  value=value*10+(*text-'0');if(value>maximum)return -1;
 }
 return value;
}
static int lobbyFormat, lobbyPractice;
static qboolean validTicket(const char *text) {
 int i;
 if(strlen(text)!=32)return qfalse;
 for(i=0;i<32;i++)if(!strchr("0123456789abcdef",text[i]))return qfalse;
 return qtrue;
}
static void lobbyWelcome(int format,int practice) {
 char address[128],previous[128],ticket[40];
 qboolean entering=lobbyFormat==0;
 lobbyFormat=format;lobbyPractice=practice;
 trap->Cvar_Set("ui_stLobbyActive","1");
 trap->Cvar_Set("ui_stLobbyPractice",practice?"1":"0");
 if(cg.demoPlayback)return;
 trap->SendClientCommand("st_lobby hello 1");
 if(!entering)return;
 if(practice){
  trap->Cvar_VariableStringBuffer("cl_currentServerIP",address,sizeof(address));
  trap->Cvar_VariableStringBuffer("st_lobbyLastServer",previous,sizeof(previous));
  trap->Cvar_VariableStringBuffer("st_lobbyResumeKey",ticket,sizeof(ticket));
  if(address[0]&&!strcmp(address,previous)&&validTicket(ticket))
   trap->SendClientCommand(va("st_lobby resume %s",ticket));
 }
 trap->SendConsoleCommand("ui_openmenu st_tournament_ready\n");
}
static void CG_STEventActions(const int*state) {
 int i,any=0;const char*names[]={"ui_stEventCanJoin","ui_stEventCanLeave","ui_stEventCanReady","ui_stEventVerified"};
 trap->Cvar_Set("ui_stLobbySoloJoin",state&&state[1]&&!(lobbyPractice&&lobbyFormat>1)?"1":"0");
 trap->Cvar_Set("ui_stLobbySquadJoin",state&&state[1]&&lobbyPractice&&lobbyFormat>1?"1":"0");
 for(i=0;i<4;i++)trap->Cvar_Set(names[i],state&&state[i+1]?"1":"0");
 for(i=0;i<STE_UI_SUB_CHOICES;i++){
  int target=state?state[i+5]:0;any|=target>0;
  trap->Cvar_Set(va("ui_stEventSub%d",i),va("%d",target));
  trap->Cvar_Set(va("ui_stEventSubAvailable%d",i),target?"1":"0");
 }
 trap->Cvar_Set("ui_stEventCanSubstitute",any?"1":"0");
 trap->Cvar_Set("ui_stEventHasBracket",state&&state[10]>0?"1":"0");
 for(i=0;i<4;i++)trap->Cvar_Set(va("ui_stEventBracketPage%d",i+1),state&&state[10]>i*8?"1":"0");
}
void CG_STEventResetUI(void) {
 int i;for(i=0;i<STE_UI_LINES;i++)trap->Cvar_Set(va("ui_ste%d",i),"");
 lobbyFormat=lobbyPractice=0;trap->Cvar_Set("ui_stLobbyActive","0");trap->Cvar_Set("ui_stLobbyPractice","0");
 for(i=0;i<32;i++)trap->Cvar_Set(va("ui_stLobbyEntry%d",i),"");
 CG_STEventActions(NULL);
 trap->Cvar_Set("ui_ste44","The host has no active tournament lobby.");
 trap->Cvar_Set("ui_ste45","Account sign-in and verification on this server are separate.");
}
static qboolean CG_STEventMessage(const char*cmd) {
 if(!strcmp(cmd,"stlobby")){
  int format=CG_STEventNumber(CG_Argv(1),5),practice=CG_STEventNumber(CG_Argv(2),1);
  if(trap->Cmd_Argc()==3&&format>=1&&practice>=0)lobbyWelcome(format,practice);
  return qtrue;
 }
 if(!strcmp(cmd,"stlobbyentry")){
  int row=CG_STEventNumber(CG_Argv(1),31);
  if(row>=0&&trap->Cmd_Argc()==3)trap->Cvar_Set(va("ui_stLobbyEntry%d",row),CG_Argv(2));
  return qtrue;
 }
 if(!strcmp(cmd,"stlobbyticket")){
  char address[128],key[40];
  Q_strncpyz(key,CG_Argv(1),sizeof(key));
  if(lobbyPractice&&!cg.demoPlayback&&trap->Cmd_Argc()==2&&validTicket(key)){
   trap->Cvar_VariableStringBuffer("cl_currentServerIP",address,sizeof(address));
   trap->Cvar_Set("st_lobbyLastServer",address);
   trap->Cvar_Set("st_lobbyResumeKey",key);
  }
  return qtrue;
 }
 if(!strcmp(cmd,"stereset")){if(trap->Cmd_Argc()==1)CG_STEventResetUI();return qtrue;}
 if(!strcmp(cmd,"steui")){
  int line=CG_STEventNumber(CG_Argv(1),STE_UI_LINES-1);char text[256];
  if(trap->Cmd_Argc()==3&&line>=0){Q_strncpyz(text,CG_Argv(2),sizeof(text));trap->Cvar_Set(va("ui_ste%d",line),text);}return qtrue;
 }
 if(!strcmp(cmd,"steactions")){
  int i,state[STE_UI_ACTION_FIELDS];
  if(trap->Cmd_Argc()!=STE_UI_ACTION_FIELDS+1){CG_STEventActions(NULL);return qtrue;}
  for(i=0;i<STE_UI_ACTION_FIELDS;i++){
   state[i]=CG_STEventNumber(CG_Argv(i+1),i<5?1:i==10?31:128);
   if(state[i]<0){CG_STEventActions(NULL);return qtrue;}
  }
  CG_STEventActions(state[0]==1?state:NULL);return qtrue;
 }
 if(!strcmp(cmd,"steaccount")){
  /* The server never sets the client's central Discord account name/session. */
  trap->Cvar_Set("ui_stEventVerified",trap->Cmd_Argc()==3&&CG_STEventNumber(CG_Argv(1),1)==1?"1":"0");return qtrue;
 }
 return qfalse;
}
void CG_STEventSubstitute_f(void) {
 int choice,target;char value[32];
 if(trap->Cmd_Argc()!=2)return;
 choice=CG_STEventNumber(CG_Argv(1),STE_UI_SUB_CHOICES-1);if(choice<0)return;
 trap->Cvar_VariableStringBuffer(va("ui_stEventSub%d",choice),value,sizeof(value));
 target=CG_STEventNumber(value,128);if(target<1)return;
 trap->SendClientCommand(va("st_lobby substitute %d",target));
}
