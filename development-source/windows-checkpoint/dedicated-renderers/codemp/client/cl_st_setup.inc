// Setup draft and display recovery live in the engine, surviving UI restarts.
#include "../ui/st_setup_catalog.h"
#include "st_setup_core.h"
static stc::Draft ssDraft;
static ss::DisplayTest ssDisplayTest;
static stc::Snapshot ssPreviousDisplay;
static bool ssOpened=false,ssReturnIngame=false,ssResume=false,ssWaitingForVideo=false;
static bool ssRestoring=false,ssRestoreInitialized=false;
static int ssVideoWatchdog=0,ssRestoreNextAttempt=0;
static const char* ssRecoveryFile="_st_setup_display_recovery.cfg";
static cvar_t* SS_Cvar(const std::string& name){for(cvar_t* v=cvar_vars;v;v=v->next)if(!Q_stricmp(v->name,name.c_str()))return v;return nullptr;}
static int SS_Index(const std::string& name){for(int i=0;i<SS_COUNT;++i)if(!Q_stricmp(name.c_str(),ssSettings[i].name))return i;return -1;}
static std::string SS_Default(int i){auto v=SS_Cvar(ssSettings[i].name);return v&&v->resetString?v->resetString:ssSettings[i].fallback;}
static bool SS_Choice(const ssSetting_t& s,const std::string& value){
 std::string choices=s.choices;size_t p=0;while(p<choices.size()){size_t e=choices.find('|',p);std::string item=choices.substr(p,e==std::string::npos?e:e-p);size_t eq=item.find('=');if(item.substr(0,eq)==value)return true;if(e==std::string::npos)break;p=e+1;}return false;
}
static stc::Snapshot SS_Live(){
 stc::Snapshot s=STC_Live();
 for(int i=0;i<SS_COUNT;++i){auto v=SS_Cvar(ssSettings[i].name);s.vars[stc::lower(ssSettings[i].name)]=v?(v->latchedString?v->latchedString:v->string):ssSettings[i].fallback;}
 return s;
}
static void SS_Open(){
 // Register only missing non-renderer personal cvars with their owner flags.
 for(int i=0;i<SS_COUNT;++i){const auto& s=ssSettings[i];if(!SS_Cvar(s.name)&&s.tab!=0)Cvar_Get(s.name,s.fallback,s.flags);}
 ssDraft.open(SS_Live());ssOpened=true;
}
static std::string SS_Get(const char* name){return stc::get(ssDraft.value.vars,stc::lower(name));}
static std::string SS_Disabled(int i){
 auto& s=ssSettings[i];auto flags=Cvar_Flags(s.name);
 if(flags!=CVAR_NONEXISTENT&&(flags&(CVAR_ROM|CVAR_INIT|CVAR_PROTECTED|CVAR_CHEAT|CVAR_SYSTEMINFO|CVAR_SERVER_CREATED|CVAR_INTERNAL)))return "Unavailable in this client or server.";
 if(s.dependency==1&&SS_Get("cl_renderer")!="rd-rend2")return "Requires Rend2.";
 if(s.dependency==2&&SS_Get("cg_draw2D")=="0")return "Clean Capture is on.";
 if(s.dependency==3&&(SS_Get("cg_draw2D")=="0"||SS_Get("st_streamerMode")=="0"))return "Requires Streamer mode with Clean Capture off.";
 if(s.dependency==5&&SS_Get("r_mode")!="-1")return "Choose Custom resolution.";
 if(!Q_stricmp(s.name,"r_ext_texture_filter_anisotropic")&&Cvar_VariableValue("r_ext_texture_filter_anisotropic_avail")==0)return "Anisotropic filtering unavailable.";
 return "";
}
static bool SS_Valid(const std::string& name,const std::string& value,const std::string& base,std::string& error){
 int i=SS_Index(name);
 if(i>=0){auto& s=ssSettings[i];bool valid=s.kind==2||s.kind==1||s.kind==4?SS_Choice(s,value)||value==base:ss::number(value,s.low,s.high,s.kind==5,base);
  auto target=SS_Cvar(name);if(s.kind==2&&target&&target->validate&&ss::number(value,target->min,target->max,target->integral!=0,base))valid=true;
  // Resolution rows enumerate driver modes/custom dimensions, not just the stock list.
  if(!Q_stricmp(s.name,"r_mode"))valid=ss::number(value,-2,32,true,base);
  if(!Q_stricmp(s.name,"se_language")){valid=value==base;for(int language=0;language<SE_GetNumLanguages();++language)if(!Q_stricmp(value.c_str(),SE_GetLanguageName(language)))valid=true;}
  if(!valid){error=std::string(s.label)+": unsupported value.";return false;}
 }
 return STC_ValidSetting(name,value,error);
}
static bool SS_WriteRecovery(const stc::Snapshot& previous,std::string& error){
 if(!ss::recoveryValid(previous)){error="Cannot preserve the current custom renderer safely.";return false;}
 std::string text=stc::serialize(previous,[](int k){return std::to_string(k);}),check,temp="_st_setup_recovery.tmp";
 fileHandle_t f=FS_FOpenFileWrite(temp.c_str());if(!f){error="Could not save display recovery.";return false;}
 int written=FS_Write(text.data(),(int)text.size(),f);FS_FCloseFile(f);
 if(written!=(int)text.size()||!STC_ReadPersonal(temp,check)||check!=text||!STC_AtomicReplace(STC_Path(temp),STC_Path(ssRecoveryFile))){error="Display recovery could not be verified; settings were not changed.";return false;}
 return true;
}
static bool SS_RemoveRecovery(){FS_Remove(STC_Path(ssRecoveryFile).c_str());struct stat info;return stat(STC_Path(ssRecoveryFile).c_str(),&info)!=0;}
static void SS_RestoreDisplay(bool restart){
 for(auto& p:ssPreviousDisplay.vars)Cvar_Set(p.first.c_str(),p.second.c_str());
 ssDisplayTest.keep();ssRestoring=true;ssRestoreInitialized=false;ssOpened=false;ssWaitingForVideo=false;ssResume=restart;
 if(restart)Cbuf_ExecuteText(EXEC_INSERT,"vid_restart\n");
}
void STSetup_EarlyRecovery(){
 static bool checked=false;if(checked)return;checked=true;
 std::string text,error;if(!STC_ReadPersonal(ssRecoveryFile,text))return;
 stc::Snapshot previous;
 if(stc::parse(text,[](std::string){return -1;},previous,error)&&ss::recoveryValid(previous)){
  ssPreviousDisplay=previous;SS_RestoreDisplay(false);Com_Printf("Restored the last confirmed display settings.\n");
 }else Com_Printf("Setup display recovery file is invalid; no commands were executed.\n");
}
void STSetup_DisplayReady(){
 if(ssRestoring){ssRestoreInitialized=true;ssRestoreNextAttempt=0;}
 else if(ssWaitingForVideo){ssDisplayTest.begin(Sys_Milliseconds());ssWaitingForVideo=false;}
}
extern void Com_WriteConfiguration();
static bool SS_ConfirmedProfile(){
 std::string profile;if(!STC_ReadPersonal(Q3CONFIG_CFG,profile))return false;
 profile.erase(std::remove(profile.begin(),profile.end(),'\r'),profile.end());profile="\n"+profile+"\n";
 for(auto& p:ssPreviousDisplay.vars){auto v=SS_Cvar(p.first);if(!v||p.second!=v->string)return false;
  std::string expected="\nseta "+std::string(v->name)+" \""+p.second+"\"\n";
  if(profile.find(expected)==std::string::npos)return false;
 }return true;
}
void STSetup_Frame(){
 int now=Sys_Milliseconds();
 if((ssWaitingForVideo&&now>=ssVideoWatchdog)||(!ssWaitingForVideo&&ssDisplayTest.expired(now)))SS_RestoreDisplay(true);
 if(ssRestoring&&ssRestoreInitialized&&now>=ssRestoreNextAttempt){
  // Startup +set commands can be replayed after early recovery. Do not archive
  // those unconfirmed latched display values over the successfully restored mode.
  for(auto& p:ssPreviousDisplay.vars){auto v=SS_Cvar(p.first);if(v&&v->latchedString&&p.second==v->string)Cvar_Set(p.first.c_str(),p.second.c_str());}
  cvar_modifiedFlags|=CVAR_ARCHIVE;Com_WriteConfiguration();
  if(SS_ConfirmedProfile()&&SS_RemoveRecovery()){ssRestoring=false;ssRestoreInitialized=false;}
  else ssRestoreNextAttempt=now+1000;
 }
}
static bool SS_Apply(stc::Draft& draft,std::string& error){
 auto live=SS_Live();if(!draft.canApply(live)){error="Settings changed outside the editor. Cancel and reopen before applying.";return false;}
 bool video=false,sound=false,input=false,display=false;
 for(auto& p:draft.value.vars)if(stc::get(draft.base.vars,p.first)!=p.second){
  if(!SS_Valid(p.first,p.second,stc::get(draft.base.vars,p.first),error))return false;
  int i=SS_Index(p.first);int restart=i>=0?ssSettings[i].restart:ss::restartKind(p.first);
  auto target=SS_Cvar(p.first);if(target&&(target->flags&CVAR_LATCH)&&p.first.find("r_")==0)restart=1;
  video|=restart==1;sound|=restart==2;input|=p.first=="in_mouse"||p.first=="in_joystick";
  for(const char* n:ss::displayNames())if(p.first==n)display=true;
 }
 if(display){
  if(ssRestoring){error="The previous display recovery has not been saved yet.";return false;}
  stc::Snapshot previous;for(const char* n:ss::displayNames()){auto v=SS_Cvar(n);previous.vars[n]=v?v->string:"0";}
  if(!SS_WriteRecovery(previous,error))return false;ssPreviousDisplay=previous;ssDisplayTest.begin(Sys_Milliseconds());ssWaitingForVideo=true;ssVideoWatchdog=Sys_Milliseconds()+30000;
 }
 Key_ClearStates();
 for(int key:stc::keys(draft.base.binds,draft.value.binds))if(stc::get(draft.base.binds,key)!=stc::get(draft.value.binds,key))Key_SetBinding(key,stc::get(draft.value.binds,key).c_str());
 for(auto& p:draft.value.vars)if(stc::get(draft.base.vars,p.first)!=p.second){
  int i=SS_Index(p.first);if(!SS_Cvar(p.first))Cvar_Get(p.first.c_str(),i>=0?ssSettings[i].fallback:p.second.c_str(),i>=0?ssSettings[i].flags:CVAR_ARCHIVE);
  Cvar_SetSafe(p.first.c_str(),p.second.c_str());
 }
 if(input)Cbuf_ExecuteText(EXEC_APPEND,"in_restart\n");
 if(video)Cbuf_ExecuteText(EXEC_APPEND,"vid_restart\n");
 if(sound)Cbuf_ExecuteText(EXEC_APPEND,"snd_restart\n");
 ssResume=video||sound;ssOpened=false;return true;
}
static int STC_Controls(const stcRequest_t*,stcReply_t*);
static int STSetup_Controls(const stcRequest_t* q,stcReply_t* r){
 memset(r,0,sizeof(*r));r->status=1;std::string error;
 auto say=[&](const std::string& text,int status=1){r->status=status;Q_strncpyz(r->text,text.c_str(),sizeof(r->text));};
 if(q->op==100){SS_Open();ssResume=false;return 1;}if(!ssOpened)SS_Open();
 switch(q->op){
 case 101:{if(q->a<0||q->a>=SS_COUNT){say("Unknown setting",-1);break;}auto& s=ssSettings[q->a];r->a=q->a;r->b=s.kind;r->c=!SS_Disabled(q->a).empty();r->number=atof(SS_Get(s.name).c_str());Q_strncpyz(r->name,s.name,sizeof(r->name));Q_strncpyz(r->label,s.label,sizeof(r->label));Q_strncpyz(r->help,r->c?SS_Disabled(q->a).c_str():s.help,sizeof(r->help));say(SS_Get(s.name));break;}
 case 102:{int i=SS_Index(q->name);if(i<0){say("Unknown setting",-1);break;}if(!SS_Disabled(i).empty()){say(SS_Disabled(i),-1);break;}if(SS_Valid(q->name,q->text,stc::get(ssDraft.base.vars,stc::lower(q->name)),error))ssDraft.value.vars[stc::lower(q->name)]=q->text;else say(error,-1);break;}
 case 103:if(ssDisplayTest.deadline){say("Keep or revert the display change first.",-1);break;}ssReturnIngame=q->a!=0;if(!SS_Apply(ssDraft,error))say(error,-1);else{SS_Open();say("Settings applied.");}break;
 case 104:SS_Open();break;
 case 105:for(int i=0;i<SS_COUNT;++i)if(ssSettings[i].tab==q->a&&SS_Disabled(i).empty())ssDraft.value.vars[stc::lower(ssSettings[i].name)]=SS_Default(i);break;
 case 106:r->a=ssDisplayTest.remaining(Sys_Milliseconds());r->b=ssDisplayTest.deadline!=0;r->c=ssReturnIngame;r->number=ssResume?1:0;r->count=SS_COUNT;break;
 case 107:if(SS_RemoveRecovery())ssDisplayTest.keep();else say("Could not confirm the display settings; recovery file could not be removed.",-1);break;
 case 108:SS_RestoreDisplay(true);break;
 case 109:STC_Open();stcDraft.open(SS_Live());break;
 case 110:{stcRequest_t request=*q;request.op=STC_SAVE;return STC_Controls(&request,r);}
 case 111:{stcRequest_t request=*q;request.op=STC_LOAD;return STC_Controls(&request,r);}
 case 112:ssReturnIngame=q->a!=0;if(!SS_Apply(stcDraft,error))say(error,-1);else {STC_Open();SS_Open();stcDraft.open(SS_Live());say("Config applied.");}break;
 case 113:{ // Scoped quality choices stage only their listed video properties.
  const char* names[]={"r_lodbias","r_picmip","r_texturebits","r_colorbits","r_detailtextures"};
  static const char* values[3][5]={{"2","3","16","16","0"},{"1","1","0","0","1"},{"0","0","32","32","1"}};
  if(q->a<0||q->a>2){say("Unknown quality preset",-1);break;}
  for(int i=0;i<5;++i)ssDraft.value.vars[names[i]]=values[q->a][i];break;}
 default:say("Unknown Setup operation",-1);break;
 }
 r->dirty=ssDraft.dirty()?1:0;return r->status;
}
