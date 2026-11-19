// Native engine backing for Controls. GPL-2.0-only.
#include "../ui/st_controls_api.h"
#include "../ui/st_controls_catalog.h"
#include "st_controls_core.h"
#include <cmath>
#include <cerrno>
#include <cstdio>
#include <sys/stat.h>
#include "sys/sys_public.h"
#ifdef _WIN32
#include <windows.h>
#endif
extern cvar_t *cvar_vars;
static stc::Draft stcDraft;
static bool stcOpened=false;
static bool stcCapturing=false;
bool STC_IsCapturing(){return stcCapturing;}
static int stcPreferred[STC_ACTION_COUNT][2];
static bool STC_Match(const std::string& text,const char* filter){return !filter||!*filter||stc::lower(text).find(stc::lower(filter))!=std::string::npos;}
static bool STC_Catalog(const char* name){for(int i=0;i<STC_SETTING_COUNT;++i)if(!Q_stricmp(name,stcSettings[i].name))return true;return false;}
static stc::Snapshot STC_Live(){
 stc::Snapshot out;for(int k=0;k<MAX_KEYS;++k){const char* b=Key_GetBinding(k);if(b&&*b)out.binds[k]=b;}
 for(cvar_t* v=cvar_vars;v;v=v->next)if(((v->flags&CVAR_ARCHIVE)||STC_Catalog(v->name)||!Q_stricmp(v->name,"cl_timeNudge"))&&!(v->flags&(CVAR_ROM|CVAR_INIT|CVAR_PROTECTED|CVAR_CHEAT|CVAR_SYSTEMINFO|CVAR_SERVER_CREATED|CVAR_INTERNAL))&&stc::validVar(v->name))out.vars[stc::lower(v->name)]=v->latchedString?v->latchedString:v->string;
 return out;
}
static void STC_Preferences(){
 for(int i=0;i<STC_ACTION_COUNT;++i){auto command=stc::lower(stcActions[i].command);for(int slot=0;slot<2;++slot)if(stc::lower(stc::get(stcDraft.value.binds,stcPreferred[i][slot]))!=command)stcPreferred[i][slot]=-1;for(auto& p:stcDraft.value.binds)if(stc::lower(p.second)==command&&p.first!=stcPreferred[i][0]&&p.first!=stcPreferred[i][1]){if(stcPreferred[i][0]<0)stcPreferred[i][0]=p.first;else if(stcPreferred[i][1]<0)stcPreferred[i][1]=p.first;}}
}
static void STC_Open(){for(int i=0;i<STC_SETTING_COUNT;++i)if(Cvar_Flags(stcSettings[i].name)==CVAR_NONEXISTENT)Cvar_Get(stcSettings[i].name,stcSettings[i].value,CVAR_ARCHIVE);stcDraft.open(STC_Live());stcOpened=true;memset(stcPreferred,-1,sizeof(stcPreferred));STC_Preferences();}
static const char* STC_KeyName(int key){return key<0?"Unassigned":Key_KeynumToString(key);}
static bool STC_ValidSetting(const std::string& name,const std::string& value,std::string& error){
 if(!stc::validVar(name)){error="Not a personal setting: "+name;return false;}
 auto flags=Cvar_Flags(name.c_str());if(flags!=CVAR_NONEXISTENT&&(flags&(CVAR_ROM|CVAR_INIT|CVAR_PROTECTED|CVAR_CHEAT|CVAR_SYSTEMINFO|CVAR_SERVER_CREATED|CVAR_INTERNAL))){error="Setting is protected: "+name;return false;}
 for(cvar_t* v=cvar_vars;v;v=v->next)if(!Q_stricmp(v->name,name.c_str())){if(v->validate){char* end=nullptr;double n=strtod(value.c_str(),&end);if(value.empty()||!end||*end||!std::isfinite(n)||n<v->min||n>v->max||(v->integral&&n!=floor(n))){error="Unsupported value for "+name+"; engine range "+std::to_string(v->min)+" to "+std::to_string(v->max);return false;}}if((v->flags&CVAR_USERINFO)&&(value.find('\\')!=std::string::npos||value.find(';')!=std::string::npos||value.find('"')!=std::string::npos)){error="Unsupported user-info text for "+name;return false;}break;}
 for(int i=0;i<STC_SETTING_COUNT;++i)if(stc::lower(name)==stc::lower(stcSettings[i].name)){char* end=nullptr;double n=strtod(value.c_str(),&end);if(value.empty()||!end||*end||!std::isfinite(n)){error="Enter a finite number.";return false;}if((n<stcSettings[i].min||n>stcSettings[i].max)&&value!=stc::get(stcDraft.base.vars,name)){error="Value outside the supported edit range.";return false;}if((stcSettings[i].kind==1||stcSettings[i].kind==2)&&n!=floor(n)){error="Choose a whole-number option.";return false;}}
 return true;
}
static bool STC_Read(const std::string& name,std::string& text){fileHandle_t f=0;int len=FS_FOpenFileRead(name.c_str(),&f,qfalse);if(!f||len<0||len>4*1024*1024){if(f)FS_FCloseFile(f);return false;}text.resize(len);int read=len?FS_Read(&text[0],len,f):0;FS_FCloseFile(f);return read==len;}
static std::string STC_Path(const std::string& name){return FS_BuildOSPath(Cvar_VariableString("fs_homepath"),Cvar_VariableString("fs_game"),name.c_str());}
static bool STC_ReadPersonal(const std::string& name,std::string& text){FILE* f=fopen(STC_Path(name).c_str(),"rb");if(!f)return false;fseek(f,0,SEEK_END);long size=ftell(f);if(size<0||size>4*1024*1024){fclose(f);return false;}rewind(f);text.resize(size);size_t read=size?fread(&text[0],1,size,f):0;fclose(f);return read==(size_t)size;}
static bool STC_AtomicReplace(const std::string& from,const std::string& to){
#ifdef _WIN32
 auto wide=[](const std::string& s){int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.c_str(),-1,NULL,0);UINT cp=CP_UTF8;if(!n){cp=CP_ACP;n=MultiByteToWideChar(cp,0,s.c_str(),-1,NULL,0);}std::vector<wchar_t> w(n?n:1);if(n)MultiByteToWideChar(cp,0,s.c_str(),-1,w.data(),n);return w;};
 auto a=wide(from),b=wide(to);return MoveFileExW(a.data(),b.data(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)!=0;
#else
 return std::rename(from.c_str(),to.c_str())==0;
#endif
}
static int STC_Save(const char* input,bool overwrite,std::string& message){
 if(!stc::validName(input)){message="Use a new personal config name (letters, numbers, spaces, _ or -).";return -1;}
 std::string name=stc::profileName(input)+".cfg",current;
 struct stat info;bool exists=stat(STC_Path(name).c_str(),&info)==0;
 if(exists&&!overwrite){message="Replace "+name+"?";return 2;}
 auto snapshot=STC_Live();snapshot.binds=stcDraft.value.binds;for(auto& v:stcDraft.value.vars)snapshot.vars[v.first]=v.second;
 auto text=stc::serialize(snapshot,[](int k){return std::string(STC_KeyName(k));});std::string temporary="st-controls-save.tmp";
 fileHandle_t f=FS_FOpenFileWrite(temporary.c_str());if(!f){message="Could not open config for writing.";return -1;}
 int written=FS_Write(text.data(),(int)text.size(),f);FS_FCloseFile(f);
 if(written!=(int)text.size()||!STC_ReadPersonal(temporary,current)||current!=text){message="Config write verification failed; existing config retained.";return -1;}
 if(!STC_AtomicReplace(STC_Path(temporary),STC_Path(name))){message="Could not finish saving; existing config retained.";return -1;}
 if(!STC_ReadPersonal(name,current)||current!=text){message="Saved config could not be verified.";return -1;}
 message="Saved "+name;return 1;
}
static std::vector<std::string> STC_Configs(){int count=0;char** list=Sys_ListFiles(STC_Path("").c_str(),".cfg",NULL,&count,qfalse);std::vector<std::string> out;for(int i=0;i<count;++i)if(stc::validName(list[i]))out.push_back(list[i]);Sys_FreeFileList(list);std::sort(out.begin(),out.end());return out;}
static void STC_Reply(stcReply_t* r,const std::string& text){Q_strncpyz(r->text,text.c_str(),sizeof(r->text));}
#include "cl_st_setup.inc"
static int STC_Controls(const stcRequest_t* q,stcReply_t* r){
 if(q&&q->op>=100)return STSetup_Controls(q,r);
 if(!q||!r)return -1;memset(r,0,sizeof(*r));r->status=1;
 std::string error;auto say=[&](const std::string& t,int status=1){r->status=status;STC_Reply(r,t);};
 if(q->op==STC_OPEN){stcCapturing=false;STC_Open();return 1;}if(!stcOpened)STC_Open();r->dirty=stcDraft.dirty()?1:0;
 switch(q->op){
 case STC_CAPTURE:stcCapturing=q->a!=0;break;
 case STC_STATE: r->count=STC_Configs().size();say(STC_Path(""));break;
 case STC_ROWS:{
  std::vector<int> rows;std::vector<std::string> files;
  if(q->a==STC_ACTIONS||q->a==STC_SERVER){for(int i=0;i<STC_ACTION_COUNT;++i){auto& a=stcActions[i];if((q->a==STC_SERVER)!=(a.restricted!=0))continue;if(*q->name&&strcmp(q->name,"All")&&strcmp(q->name,a.group))continue;if(STC_Match(std::string(a.label)+" "+a.command+" "+a.help,q->text))rows.push_back(i);}}
  else if(q->a==STC_BINDLIST){for(auto& p:stcDraft.value.binds)if(STC_Match(std::string(STC_KeyName(p.first))+" "+p.second,q->text))rows.push_back(p.first);}
  else if(q->a==STC_SETTINGS){for(int i=0;i<STC_SETTING_COUNT;++i){auto& s=stcSettings[i];if(*q->name&&strcmp(q->name,s.group))continue;if(STC_Match(stc::lower(s.name)+" "+s.help,q->text))rows.push_back(i);}}
  else if(q->a==STC_CONFIGS){files=STC_Configs();for(int i=0;i<(int)files.size();++i)if(STC_Match(files[i],q->text))rows.push_back(i);}
  else if(q->a==STC_PAD){for(int i=0;i<18;++i)rows.push_back(i);}
  r->count=rows.size();if(q->b<0||q->b>=(int)rows.size())break;r->a=rows[q->b];
  if(q->a==STC_ACTIONS||q->a==STC_SERVER){auto& a=stcActions[r->a];Q_strncpyz(r->label,a.label,sizeof(r->label));Q_strncpyz(r->name,a.command,sizeof(r->name));Q_strncpyz(r->help,a.help,sizeof(r->help));r->b=stcPreferred[r->a][0];r->c=stcPreferred[r->a][1];say(std::string(STC_KeyName(r->b))+" | "+STC_KeyName(r->c));}
  else if(q->a==STC_BINDLIST){Q_strncpyz(r->label,STC_KeyName(r->a),sizeof(r->label));say(stcDraft.value.binds[r->a]);r->b=stcDraft.value.binds[r->a].size();}
  else if(q->a==STC_SETTINGS){auto& s=stcSettings[r->a];Q_strncpyz(r->name,s.name,sizeof(r->name));Q_strncpyz(r->label,s.help,sizeof(r->label));Com_sprintf(r->help,sizeof(r->help),"%s | default %s | edit range %.4g to %.4g",s.name,s.value,s.min,s.max);say(stc::get(stcDraft.value.vars,stc::lower(s.name)));r->number=(float)atof(r->text);r->b=s.kind;}
  else if(q->a==STC_CONFIGS){Q_strncpyz(r->label,files[r->a].c_str(),sizeof(r->label));say(files[r->a]);}
  else if(q->a==STC_PAD){int key=A_JOY0+r->a;int style=atoi(stc::get(stcDraft.value.vars,std::string("st_controllerlabels")).c_str());static const char* xbox[]={"A","B","X","Y","View","Guide","Menu","Left stick click","Right stick click","LB","RB","D-pad up","D-pad down","D-pad left","D-pad right","Extra button","LT","RT"};static const char* ps[]={"Cross","Circle","Square","Triangle","Share / Create","PS","Options","L3","R3","L1","R1","D-pad up","D-pad down","D-pad left","D-pad right","Extra button","L2","R2"};Q_strncpyz(r->label,style==1?ps[r->a]:style==2?STC_KeyName(key):xbox[r->a],sizeof(r->label));r->a=key;say(stc::get(stcDraft.value.binds,key));}
  break;}
 case STC_ACTIONINFO:if(q->a<0||q->a>=STC_ACTION_COUNT){say("Invalid action",-1);break;}r->b=stcPreferred[q->a][0];r->c=stcPreferred[q->a][1];break;
 case STC_RESETACTION:{if(q->a<0||q->a>=STC_ACTION_COUNT){say("Invalid action",-1);break;}std::string text;if(!STC_Read("mpdefault.cfg",text)){say("Stock defaults unavailable",-1);break;}stc::Snapshot defaults;if(!stc::parse(text,[](std::string key){return key.empty()?-1:Key_StringToKeynum(&key[0]);},defaults,error)){say(error,-1);break;}std::string command=stcActions[q->a].command;for(auto& p:defaults.binds)if(stc::lower(p.second)==stc::lower(command)&&!stc::get(stcDraft.value.binds,p.first).empty()&&stc::lower(stc::get(stcDraft.value.binds,p.first))!=stc::lower(command)&&!q->c){say("One or more default keys have another command. Confirm to replace them.",2);return 2;}for(auto it=stcDraft.value.binds.begin();it!=stcDraft.value.binds.end();)if(stc::lower(it->second)==stc::lower(command))it=stcDraft.value.binds.erase(it);else ++it;for(auto& p:defaults.binds)if(stc::lower(p.second)==stc::lower(command))stcDraft.value.binds[p.first]=p.second;STC_Preferences();say("Stock action defaults staged (unassigned when no stock default exists)");break;}
 case STC_BIND:{if(q->a<0||q->a>=STC_ACTION_COUNT||q->b<0||q->b>1||q->c<0||q->c>=MAX_KEYS){say("Invalid assignment",-1);break;}int old=stcPreferred[q->a][q->b];if(old<0&&!strcmp(q->text,"swap")){say("This slot has no key to swap. Choose Replace or Cancel.",-1);break;}auto occupied=stc::get(stcDraft.value.binds,q->c);if(!occupied.empty()&&occupied!=stcActions[q->a].command&&!*q->text){say(std::string(STC_KeyName(q->c))+" is assigned to: "+occupied,2);break;}if(old>=0&&old!=q->c){if(!occupied.empty()&&!strcmp(q->text,"swap"))stcDraft.value.binds[old]=occupied;else stcDraft.value.binds.erase(old);}stcDraft.value.binds[q->c]=stcActions[q->a].command;for(int slot=0;slot<2;++slot)if(stcPreferred[q->a][slot]==q->c)stcPreferred[q->a][slot]=-1;stcPreferred[q->a][q->b]=q->c;STC_Preferences();say("Assignment staged");break;}
 case STC_RAW:if(q->a<0||q->a>=MAX_KEYS){say("Invalid key",-1);break;}if(*q->text)stcDraft.value.binds[q->a]=q->text;else stcDraft.value.binds.erase(q->a);STC_Preferences();say("Binding staged; command was not executed");break;
 case STC_MOVE:if(q->a<0||q->a>=MAX_KEYS||q->b<0||q->b>=MAX_KEYS){say("Invalid key",-1);break;}if(!stcDraft.move(q->a,q->b,(stc::Conflict)q->c)){say(std::string(STC_KeyName(q->b))+" is assigned to: "+stc::get(stcDraft.value.binds,q->b),2);break;}STC_Preferences();say("Key change staged");break;
 case STC_VAR:if(STC_ValidSetting(q->name,q->text,error)){stcDraft.value.vars[stc::lower(q->name)]=q->text;say("Setting staged");}else say(error,-1);break;
 case STC_RESETVAR:if(q->a>=0&&q->a<STC_SETTING_COUNT){stcDraft.value.vars[stc::lower(stcSettings[q->a].name)]=stcSettings[q->a].value;say("Default staged");}else say("Invalid setting",-1);break;
 case STC_CANCEL:stcCapturing=false;stcDraft.cancel();STC_Preferences();say("Pending edits discarded");break;
 case STC_APPLY:{auto live=STC_Live();if(!stcDraft.canApply(live)){say("A setting or binding changed outside the editor. Cancel and reopen to refresh; nothing applied.",-1);break;}for(auto& p:stcDraft.value.vars)if(stc::get(stcDraft.base.vars,p.first)!=p.second&&!STC_ValidSetting(p.first,p.second,error))break;if(!error.empty()){say(error,-1);break;}bool restart=false;Key_ClearStates();for(int key:stc::keys(stcDraft.base.binds,stcDraft.value.binds))if(stc::get(stcDraft.base.binds,key)!=stc::get(stcDraft.value.binds,key))Key_SetBinding(key,stc::get(stcDraft.value.binds,key).c_str());for(auto& p:stcDraft.value.vars)if(stc::get(stcDraft.base.vars,p.first)!=p.second){if(p.first=="in_mouse"||p.first=="in_joystick")restart=true;cvar_t* target=cvar_vars;while(target&&Q_stricmp(target->name,p.first.c_str()))target=target->next;if(target)target->flags|=CVAR_ARCHIVE;else Cvar_Get(p.first.c_str(),p.second.c_str(),CVAR_ARCHIVE);Cvar_SetSafe(p.first.c_str(),p.second.c_str());}STC_Open();if(restart)Cbuf_ExecuteText(EXEC_APPEND,"in_restart\n");say("Settings applied. Video/sound changes may require a restart.");break;}
 case STC_SAVE:r->status=STC_Save(q->text,q->c!=0,error);STC_Reply(r,error);break;
 case STC_LOAD:{if(stcDraft.dirty()&&!q->c){say("Replace pending edits with this config?",2);break;}if(!stc::validName(q->text)){say("Invalid personal config filename",-1);break;}std::string name=stc::profileName(q->text)+".cfg",text;if(!STC_ReadPersonal(name,text)){say("Could not read config",-1);break;}stc::Snapshot parsed;bool replaces=false;if(!stc::parse(text,[](std::string key){return key.empty()?-1:Key_StringToKeynum(&key[0]);},parsed,error,&replaces)){say(error,-1);break;}for(auto& p:parsed.vars)if(!STC_ValidSetting(p.first,p.second,error))break;if(!error.empty()){say(error,-1);break;}auto next=stcDraft.base;if(replaces)next.binds=parsed.binds;else for(auto& p:parsed.binds){if(p.second.empty())next.binds.erase(p.first);else next.binds[p.first]=p.second;}for(auto& p:parsed.vars)next.vars[p.first]=p.second;stcDraft.value=next;STC_Preferences();say("Config loaded into editor. Review, then Apply.");break;}
 case STC_PADDEFAULTS:{static const char* defaults[]={"+moveup","+movedown","+use","saberAttackCycle","+scores","","togglemenu","+speed","cg_thirdPerson !","+useforce","+altattack","weapnext","weapprev","forceprev","forcenext","","","+attack"};for(int i=0;i<18;++i)if(*defaults[i])stcDraft.value.binds[A_JOY0+i]=defaults[i];STC_Preferences();say("Controller defaults staged; review before Apply");break;}
 default:say("Unsupported Controls operation",-1);break;
 }
 r->dirty=stcDraft.dirty()?1:0;return r->status;
}

#ifdef ST_CONTROLS_QA
static void STC_QAKey_f(){char name[64];Q_strncpyz(name,Cmd_Argv(1),sizeof(name));char continuation[128];Q_strncpyz(continuation,Cmd_Argv(2),sizeof(continuation));int key=Key_StringToKeynum(name);if(key<0||key>=MAX_KEYS)Com_Error(ERR_FATAL,"Invalid QA key");CL_KeyEvent(key,qtrue,Sys_Milliseconds());CL_KeyEvent(key,qfalse,Sys_Milliseconds());if(*continuation)Cbuf_ExecuteText(EXEC_APPEND,va("exec %s\n",continuation));}
#endif
