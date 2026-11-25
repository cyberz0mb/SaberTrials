// Exercises the production native UI adapter with an in-memory engine boundary.
#include <algorithm>
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <cmath>
#include <map>
#include <string>
#include <vector>
#include "keycodes.h"
using std::string;
typedef int qboolean;typedef int fileHandle_t;typedef float vec4_t[4];
enum {qfalse=0,qtrue=1,FS_READ,FS_WRITE,CA_CONNECTED=4,EXEC_APPEND=2,KEYCATCH_UI=2,FEEDER_ALLMAPS=1,CVAR_TEMP=1,PLAYERS_PER_TEAM=8};
struct menuDef_t {struct {const char* name;} window;};
static menuDef_t testMenu={{"advancedcreateserver"}};
struct uiClientState_t {int connState;};
struct vmCvar_t{};static vmCvar_t ui_netGametype,ui_actualNetGametype,ui_currentNetMap;
struct TestUI {
 struct {float cursorx=0,cursory=0;int realTime=0;} uiDC;
 struct {int gtEnum;} gameTypes[6];int numGameTypes=5;
 struct {const char *mapLoadName,*mapName;int typeBits;bool active;} mapList[4];int mapCount=2;
} uiInfo;
static std::map<string,string> cvars,files;static std::map<int,string> handles;static std::vector<string> commands,drawTexts;static int changes=0,connection=0,nextHandle=1;static bool shortRead=false,checkCleanRosterBeforeMap=false;
struct MockTrap {
 void Cvar_VariableStringBuffer(const char* n,char* out,int size){std::snprintf(out,size,"%s",cvars[n].c_str());}
 float Cvar_VariableValue(const char* n){return float(std::atof(cvars[n].c_str()));}
 void Cvar_Set(const char* n,const char* v){cvars[n]=v;if(string(n)!="st_uiNameKeyboard")++changes;}
 void Cvar_Register(void*,const char* n,const char* v,int){if(!cvars.count(n))cvars[n]=v;}
 void Cvar_SetValue(const char* n,float v){cvars[n]=std::to_string(int(v));++changes;}
 void Cvar_Update(vmCvar_t*){}
 void GetClientState(uiClientState_t* s){s->connState=connection;}
 int FS_GetFileList(const char*,const char*,char* output,int size){string list;for(const auto& f:files)if(f.first.find("match-presets/")==0){list+=f.first.substr(14);list+='\0';}list+='\0';assert(int(list.size())<=size);std::memcpy(output,list.data(),list.size());return int(std::count(list.begin(),list.end(),'\0'))-1;}
 int FS_Open(const char* path,int* h,int mode){*h=0;if(mode==FS_READ&&!files.count(path))return -1;*h=nextHandle++;handles[*h]=path;if(mode==FS_WRITE)files[path].clear();return int(files[path].size());}
 void FS_Close(int h){handles.erase(h);}
 int FS_Read(void* out,int size,int h){string s=files[handles[h]];int n=std::min(size,int(s.size()))-(shortRead?1:0);std::memcpy(out,s.data(),n);return n;}
 int FS_Write(const void* input,int size,int h){files[handles[h]]=string(static_cast<const char*>(input),size);return size;}
 void Cmd_ExecuteText(int,const char* value){if(checkCleanRosterBeforeMap&&string(value).find("map mp/")!=string::npos){assert(cvars["st_matchRosterExecute"]=="0"&&cvars["st_matchRosterCount"]=="0"&&cvars["st_matchRosterClear"]=="0");for(int i=0;i<32;++i)assert(cvars["st_matchRoster_"+std::to_string(i)].empty());}commands.push_back(value);}
 int Key_GetCatcher(){return 2;}void Key_SetCatcher(int){}
} mockTrap;static MockTrap* trap=&mockTrap;
static const char* va(const char* fmt,...){static char buffers[16][2048];static int at=0;char* s=buffers[(at++)%16];va_list a;va_start(a,fmt);std::vsnprintf(s,2048,fmt,a);va_end(a);return s;}
static int Q_stricmp(const char* a,const char* b){return _stricmp(a,b);}
static float Com_Clamp(float a,float b,float v){return std::max(a,std::min(b,v));}
static int UI_GetNumBots(){return 2;}static const char* UI_GetBotNameByNumber(int i){return i==0?"Luke":"Desann";}
static int ST_TffaCount(int n){return std::max(2,std::min(8,n));}static int UI_TffaPlayableSlots(){int size=std::atoi(cvars["ui_stHostTeamSize"].c_str());int value=size?ST_TffaCount(std::atoi(cvars["ui_stHostTeams"].c_str()))*std::max(2,std::min(4,size)):std::atoi(cvars["ui_stTffaOpenSlots"].c_str());return std::max(1,std::min(32,value));}static int UI_TffaSlotTeam(int s){return s%2?1:2;}
static int UI_HostMaxClients(){int size=std::atoi(cvars["ui_stHostTeamSize"].c_str());return std::max(std::atoi(cvars["sv_maxclients"].c_str()),size?ST_TffaCount(std::atoi(cvars["ui_stHostTeams"].c_str()))*std::max(2,std::min(4,size)):0);}
static const char* UI_TffaSlotCvar(int s){return va(s%2?"ui_redteam%d":"ui_blueteam%d",1+s/2);}
static menuDef_t* Menu_GetFocused(){return &testMenu;}static void Menus_CloseByName(const char*){}static void Menus_CloseAll(){}
static int UI_MapCountByGameType(int){return 2;}static void Menu_SetFeederSelection(void*,int,int,const char*){}
static float RUI_Width(const char* text,float scale){return std::strlen(text)*7*scale;}
static void RUI_Control(float,float,float,float,const char*,bool,bool){}static void RUI_Image(const char*,float,float,float,float){}
static vec4_t scuText={1,1,1,1},scuMuted={.5f,.5f,.5f,1},scuCyan={0,1,1,1},scuLine={0,0,0,1},scuGold={1,1,0,1};
static void MSUI_Color(float* ink,bool,bool,bool){std::memcpy(ink,scuText,sizeof(vec4_t));}
static void SCUI_Centered(float,float,float,float,float,const char* text,const float*){drawTexts.push_back(text);}static void SCUI_Text(float,float,float,const char* text,const float*){drawTexts.push_back(text);}
static void SCUI_Fit(float,float,float,float,const char*,const float*){}static void SMUI_Image(const char*,float,float,float,float){}
static void UI_FillRect(float,float,float,float,const float*){}static void LUI_Frame(){}
#include "ui_st_match_rules.inc"
static void reset(bool local=false){
 mrui={};cvars.clear();files.clear();handles.clear();commands.clear();drawTexts.clear();changes=connection=0;shortRead=checkCleanRosterBeforeMap=false;
 for(int i=0;i<stmatch::RuleCount;++i)cvars[stmatch::rules[i].cvar]=std::to_string(stmatch::rules[i].initial);
 for(int i=0;i<stmatch::ForceCount;++i)cvars[va("st_matchForceCap%d",i)]="3";cvars["st_matchWeaponDisable"]="0";
 cvars["sv_running"]=local?"1":"0";cvars["sv_hostname"]="Test host";cvars["mapname"]="mp/ffa3";cvars["ui_netGametype"]="0";cvars["ui_currentNetMap"]="0";cvars["sv_maxclients"]="16";
 cvars["ui_stHostTeams"]="2";cvars["ui_stHostTeamSize"]="0";cvars["ui_stTffaOpenSlots"]="16";
 files["maps/mp/ffa3.bsp"]="BSP";files["maps/mp/duel1.bsp"]="BSP";
 const int types[]={0,3,4,6,8};for(int i=0;i<5;++i)uiInfo.gameTypes[i].gtEnum=types[i];uiInfo.mapList[0]={"mp/ffa3","FFA",1,true};uiInfo.mapList[1]={"mp/duel1","Duel",1<<3,false};
}
int main(){
 reset();MRUI_Open();MRUI_ChangeRule(stmatch::find("st_spawnHealth"),1);assert(changes==0&&commands.empty());MRUI_Close(false);assert(changes==0&&commands.empty());
 assert(cvars["st_uiNameKeyboard"]=="0");
 reset();MRUI_Open();mrui.draft.set("st_combatMode",0);MRUI_ChangeRule(stmatch::find("st_activeDefense"),1);assert(mrui.draft.get("st_activeDefense")==0);assert(!mrui.status.empty());
 reset();MRUI_Open();MRUI_Edit(MR_PASSWORD,0,"secret",64,"Password");MRUI_Key(A_ESCAPE,qtrue);assert(mrui.password.empty());MRUI_Edit(MR_PASSWORD,0,"secret",64,"Password");MRUI_Key('x'|K_CHAR_FLAG,qtrue);assert(mrui.edit=="x");MRUI_CommitEdit();assert(mrui.password=="x");assert(stmatch::encode(mrui.draft).find("secret")==string::npos);
 reset(true);cvars["st_matchPending_bot5_model"]="Desann";cvars["st_matchPending_bot5_role"]="3";cvars["st_matchPending_bot5_skill"]="5";cvars["st_matchPending_bot5_team"]="0";MRUI_Open();assert(mrui.draft.bots.size()==1&&mrui.draft.bots[0].slot==5);assert(changes==0&&commands.empty());assert(MRUI_Apply(true));assert(changes==0);string all;for(const auto& c:commands)all+=c;assert(all.find("st_match_rosterreset")<all.find("st_match_addbot"));assert(all.find("st_match_addbot")<all.find("st_match_apply later"));assert(all.find("st_match_set ui_dedicated")==string::npos);
 reset(true);cvars["st_matchPending_st_spawnHealth"]="125";MRUI_Open();assert(mrui.draft.get("st_spawnHealth")==125);mrui.confirm=MR_QUEUECANCEL;MRUI_Confirm();assert(cvars["st_matchPending_st_spawnHealth"]=="125");assert(mrui.draft.get("st_spawnHealth")==0);assert(commands.back()=="st_match_cancel\n");
 reset(true);MRUI_Open();mrui.draft.set("st_voteCooldown",65);assert(MRUI_Apply(true));assert(commands.size()==2&&commands[0]=="st_match_set st_voteCooldown 65\n"&&commands[1]=="st_match_apply later\n");
 reset(true);cvars["g_gametype"]="6";cvars["g_tffaTeamSize"]="4";cvars["g_weaponDisable"]="0";MRUI_Open();assert(mrui.draft.get("st_matchTeamCap")==4&&mrui.draft.get("st_weaponsActive")==1);mrui.draft.set("st_voteCooldown",65);assert(MRUI_Apply(true));assert(commands.size()==2&&commands[0]=="st_match_set st_voteCooldown 65\n");
 reset(true);cvars["g_weaponDisable"]="0";MRUI_Open();assert(mrui.draft.get("st_weaponsActive")==1);mrui.draft.set("st_weaponsActive",0);assert(MRUI_Apply(true));assert(std::find(commands.begin(),commands.end(),"st_match_set st_weaponsActive 0\n")!=commands.end());
 reset(true);cvars["g_weaponDisable"]="0";MRUI_Open();mrui.draft.weaponDisable=16;assert(MRUI_Apply(true));assert(std::find(commands.begin(),commands.end(),"st_match_set st_weaponsActive 1\n")!=commands.end()&&std::find(commands.begin(),commands.end(),"st_match_weapons 16\n")!=commands.end());
 reset(true);cvars["g_weaponDisable"]="524278";MRUI_Open();assert(mrui.draft.get("st_weaponsActive")==0&&mrui.draft.weaponDisable==524274);assert(MRUI_Apply(true));assert(commands.size()==1&&commands[0]=="st_match_apply later\n");
 reset(true);cvars["g_gametype"]="3";cvars["g_weaponDisable"]="0";cvars["g_duelWeaponDisable"]="524278";MRUI_Open();assert(mrui.draft.get("st_weaponsActive")==0);MRUI_Review();assert(std::find(mrui.review.begin(),mrui.review.end(),"Duel round: one kill")!=mrui.review.end());for(const auto& row:mrui.review)assert(row.find("Score limit:")==string::npos);
 reset(true);cvars["g_gametype"]="6";cvars["g_tffaTeamSize"]="4";cvars["st_matchTeamsManaged"]="1";cvars["st_matchWeaponsManaged"]="1";cvars["g_weaponDisable"]="0";MRUI_Open();assert(mrui.draft.get("st_matchTeamCap")==0&&mrui.draft.get("st_weaponsActive")==0);
 reset();cvars["ui_netGametype"]="3";cvars["ui_stTffaOpenSlots"]="4";cvars["sv_maxclients"]="16";MRUI_Open();assert(mrui.draft.get("sv_maxclients")==4);mrui.draft.set("sv_maxclients",11);mrui.draft.set("st_spawnHealth",125);MRUI_Close(true);MRUI_Open();assert(mrui.draft.get("sv_maxclients")==11&&mrui.draft.get("st_spawnHealth")==125);MRUI_Close(true);cvars["ui_stTffaOpenSlots"]="6";cvars["ui_stHostTeams"]="3";MRUI_Open();assert(mrui.draft.get("sv_maxclients")==6&&mrui.draft.get("g_tffaTeams")==3&&mrui.draft.get("st_spawnHealth")==125);MRUI_Close(true);cvars["ui_stHostTeamSize"]="4";MRUI_Open();assert(mrui.draft.get("st_matchTeamCap")==4&&mrui.draft.get("sv_maxclients")==16);
 reset();cvars["ui_netGametype"]="3";cvars["ui_stHostTeamSize"]="4";cvars["sv_maxclients"]="8";MRUI_Open();assert(mrui.draft.get("sv_maxclients")==8);MRUI_Close(true);cvars["ui_stHostTeams"]="8";MRUI_Open();assert(mrui.draft.get("sv_maxclients")==32);
 reset();MRUI_Open();MRUI_Close(true);cvars["sv_maxclients"]="9";MRUI_Open();assert(mrui.draft.get("sv_maxclients")==9);
 reset(true);cvars["st_matchRotation"]="mp/ffa3";cvars["st_matchPending_hasrotation"]="1";MRUI_Open();assert(mrui.draft.rotation.empty());
 reset(true);cvars["st_matchLiveReady"]="1";cvars["st_matchLive_bot2_present"]="1";cvars["st_matchLive_bot2_model"]="Desann";cvars["st_matchLive_bot2_skill"]="5";cvars["st_matchLive_bot2_team"]="0";cvars["st_matchLive_bot2_role"]="3";MRUI_Open();assert(mrui.draft.bots.empty());assert(MRUI_SaveSnapshot());assert(mrui.presetToSave.bots.size()==1&&mrui.presetToSave.bots[0].model=="Desann");assert(mrui.draft.bots.empty()&&commands.empty());cvars["st_matchLiveBotUnresolved"]="1";assert(!MRUI_SaveSnapshot()&&mrui.draft.bots.empty());
 reset();MRUI_Open();mrui.filename="valid";files["match-presets/valid.stmatch.fcf"]=stmatch::encode(mrui.draft);mrui.draft.set("st_spawnHealth",125);shortRead=true;MRUI_FileAction(MR_LOAD);assert(mrui.draft.get("st_spawnHealth")==125&&mrui.modal!=MR_CONFIRM);shortRead=false;files["maps/mp/ffa3.bsp"].clear();MRUI_FileAction(MR_LOAD);assert(mrui.draft.get("st_spawnHealth")==125&&mrui.modal!=MR_CONFIRM);
 reset();MRUI_Open();mrui.filename="test";MRUI_FileAction(MR_SAVE);MRUI_Confirm();assert(files["match-presets/test.stmatch.fcf"].find("ST_MATCH_PRESET 1")==0);MRUI_FileAction(MR_DELETE);MRUI_Confirm();assert(files["match-presets/test.stmatch.fcf"].empty());assert(mrui.files.empty());
 reset();connection=CA_CONNECTED;MRUI_Open();assert(!mrui.active&&commands.empty()&&changes==0);
 reset();MRUI_Open();stmatch::Bot b;b.model="Luke";b.slot=2;mrui.draft.bots.push_back(b);mrui.draft.set("g_allowVote",5);assert(MRUI_Apply(false));assert(cvars["st_matchManaged"]=="1"&&cvars["g_allowVote"]=="5");all.clear();for(const auto& c:commands)all+=c;assert(all.find("map mp/ffa3")<all.find("st_match_addbot"));assert(all.find("st_match_addbot")<all.find("st_match_apply roster"));
 reset();cvars["st_matchRosterExecute"]="1";cvars["st_matchRosterCount"]="31";cvars["st_matchRosterClear"]="1";cvars["st_matchInitialRosterPending"]="1";for(int i=0;i<32;++i)cvars["st_matchRoster_"+std::to_string(i)]="stale";checkCleanRosterBeforeMap=true;MRUI_Open();MRUI_Close(false);assert(cvars["st_matchRosterExecute"]=="1");MRUI_Open();assert(MRUI_Apply(false));assert(cvars["st_matchInitialRosterPending"]=="0");
 reset(true);MRUI_Open();mrui.modal=MR_SUMMARY;MRUI_DrawSummary();assert(std::find(drawTexts.begin(),drawTexts.end(),"Apply now (restarts if needed)")!=drawTexts.end());
 reset();MRUI_Open();assert(cvars["st_uiNameKeyboard"]=="1");MRUI_Draw();assert(!mrui.hits.empty());MRUI_Key(A_JOY11,qtrue);assert(!mrui.pointer);MRUI_Key(A_JOY1,qtrue);assert(mrui.modal==MR_CONFIRM);
 reset();MRUI_Open();MRUI_Draw();MRUI_Key(A_JOY12,qtrue);assert(!mrui.pointer);uiInfo.uiDC.cursorx=125;uiInfo.uiDC.cursory=64;MRUI_Mouse();assert(mrui.pointer);cvars["st_uiPadClick"]="1";MRUI_Key(A_MOUSE1,qtrue);assert(mrui.tab==1);
 reset();MRUI_Open();mrui.tab=stmatch::Teams;stmatch::Bot roster;roster.model="Luke";mrui.draft.bots.push_back(roster);MRUI_BuildRows();for(int i=0;i<int(mrui.rows.size());++i)if(mrui.rows[i].action==MR_BOT){mrui.scroll=i;break;}MRUI_Draw();for(int i=0;i<int(mrui.hits.size());++i)if(mrui.hits[i].action==MR_BOT&&mrui.hits[i].a==0){mrui.focus=i;break;}MRUI_Key(A_JOY14,qtrue);assert(mrui.hits[mrui.focus].action==MR_ROLE);MRUI_Key(A_JOY14,qtrue);assert(mrui.hits[mrui.focus].action==MR_SKILL);MRUI_Key(A_JOY14,qtrue);assert(mrui.hits[mrui.focus].action==MR_TEAM);
 std::puts("Native UI transaction, security, preset, roster, authority, input and host command checks passed.");
}
