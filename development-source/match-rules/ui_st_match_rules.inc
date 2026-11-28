/* Transactional, native local-host Match Rules UI. GPL-2.0-only.
 * No gameplay cvar changes occur until the concrete review is accepted.
 * Presets are structured data read through the VFS, never executable configs.
 */
#include "st_match_rules.h"
enum MRAction {
 MR_TAB=1,MR_RULE,MR_SLIDER,MR_NUMBER,MR_FORCE,MR_WEAPON,MR_VOTE,
 MR_HOSTNAME,MR_PASSWORD,MR_MAP,MR_ROTATION,MR_BOT,MR_ROLE,MR_SKILL,MR_TEAM,MR_REPLACE,
 MR_PREV,MR_NEXT,MR_BACK,MR_CANCEL,MR_PRESETS,MR_REVIEW,MR_NOW,MR_LATER,MR_YES,MR_NO,
 MR_FILENAME,MR_SAVE,MR_LOAD,MR_DELETE,MR_FILE,MR_BOTCHOICE,MR_MAPCHOICE,MR_MAPEDIT,
 MR_ROTADD,MR_ROTUP,MR_ROTDOWN,MR_ROTDELETE,MR_ROTEDIT,MR_KEY,MR_QUEUECANCEL,MR_HOSTCHOOSER
};
enum {MR_MAIN=0,MR_SUMMARY,MR_FILES,MR_EDIT,MR_CONFIRM,MR_BOTS,MR_MAPS,MR_ROTATIONS};
struct MRHit {float x,y,w,h;int action,a,b;};
struct MRRow {int action,index;std::string label,help;};
static struct {
 bool active=false,cached=false,local=false,pointer=true,rosterEdited=false,replaceBots=false,passwordEdited=false,shift=false,editReplace=false,routing=false;
 int tab=0,scroll=0,focus=0,modal=0,page=0,slot=0,confirm=0,editTarget=0,editIndex=0,editReturn=0,drag=-1,editLimit=100,reviewScroll=0;
 int hostMode=-1,hostMap=-1,hostTeams=-1,hostSize=-1,hostOpenSlots=-1,hostMaxPlayers=-1;
 size_t caret=0;
 std::string menu,status,help,filename,edit,editTitle,password,originalPassword,previousKeyboardRoute;
 stmatch::Preset draft,original,presetToLoad,presetToSave;
 std::vector<MRHit> hits;
 std::vector<MRRow> rows;
 std::vector<std::string> files,review;
} mrui;
static const char* const mrTabs[]={"Combat","Force / Weapons","Health / Movement","Teams / Bots","Match","Server"};
// Bit order is the server's validVoteStrings[] order in g_cmds.c.
static const char* const mrVotes[]={"Capture limit","Kick by client number","Score limit","Warm-up","Game type","Kick by name","Map","Restart map","Next map","Time limit","Force rules","Tournament","Add bot","Lock teams"};
static const int mrTeamIds[]={0,1,2,4,5,6,7,8,9};
static const char* const mrTeamNames[]={"Auto","Red","Blue","Green","Yellow","White","Black","Orange","Purple"};
static std::string MRUI_Cvar(const char* name){char value[2048];trap->Cvar_VariableStringBuffer(name,value,sizeof(value));return value;}
static bool MRUI_Owned(const char* domain){return trap->Cvar_VariableValue("st_matchManaged")!=0||trap->Cvar_VariableValue(domain)!=0;}
static int MRUI_LegacyWeaponMask(){int type=int(trap->Cvar_VariableValue("g_gametype"));int mask=int(trap->Cvar_VariableValue(type==3||type==4?"g_duelWeaponDisable":"g_weaponDisable"));return std::max(0,std::min((1<<stmatch::WeaponCount)-1,mask));}
static bool MRUI_ActiveNumber(const char* name,int& value){
 if(mrui.local&&!MRUI_Owned("st_matchWeaponsManaged")){
  if(!Q_stricmp(name,"st_weaponsActive")){int mask=MRUI_LegacyWeaponMask();value=mask==0?1:mask==524278?0:2;return true;}
  if(!Q_stricmp(name,"st_matchWeaponDisable")){value=MRUI_LegacyWeaponMask()&~((1<<2)|(1<<3));return true;}
 }
 if(mrui.local&&!Q_stricmp(name,"st_matchTeamCap")&&!MRUI_Owned("st_matchTeamsManaged")){int size=int(trap->Cvar_VariableValue("g_tffaTeamSize"));value=trap->Cvar_VariableValue("g_gametype")==6?(size?std::max(2,std::min(4,size)):0):0;return true;}
 return stmatch::integer(MRUI_Cvar(name),value);
}
static bool MRUI_Server(){return trap->Cvar_VariableValue("sv_running")!=0;}
static bool MRUI_Remote(){uiClientState_t state;trap->GetClientState(&state);return state.connState>=CA_CONNECTED&&!MRUI_Server();}
static bool MRUI_Over(float x,float y,float w,float h){return uiInfo.uiDC.cursorx>=x&&uiInfo.uiDC.cursorx<x+w&&uiInfo.uiDC.cursory>=y&&uiInfo.uiDC.cursory<y+h;}
static void MRUI_Hit(float x,float y,float w,float h,int action,int a=0,int b=0){mrui.hits.push_back({x,y,w,h,action,a,b});}
static int MRUI_Hover(){for(int i=int(mrui.hits.size())-1;i>=0;--i){const auto& h=mrui.hits[i];if(MRUI_Over(h.x,h.y,h.w,h.h))return i;}return -1;}
static bool MRUI_Focus(){return mrui.pointer?false:mrui.focus==int(mrui.hits.size());}
static void MRUI_Button(float x,float y,float w,float h,const std::string& text,int action,int a=0,int b=0,bool selected=false,bool enabled=true){
 bool focus=MRUI_Focus()||(mrui.pointer&&MRUI_Over(x,y,w,h));vec4_t ink;MSUI_Color(ink,selected,focus,enabled);
 RUI_Control(x,y,w,h,action==MR_TAB?"tab":"field",selected,focus&&enabled);
 SCUI_Centered(x,y,w,h,.57f,text.c_str(),ink);MRUI_Hit(x,y,w,h,action,a,b);
}
static void MRUI_Wrap(float x,float y,float width,float scale,const std::string& text,const float* color,int lines=3){
 std::istringstream in(text);std::string word,line;int n=0;
 while(in>>word){std::string next=line.empty()?word:line+" "+word;if(RUI_Width(next.c_str(),scale)>width&&!line.empty()){SCUI_Text(x,y+15*n++,scale,line.c_str(),color);line=word;if(n>=lines)return;}else line=next;}
 if(n<lines&&!line.empty())SCUI_Text(x,y+15*n,scale,line.c_str(),color);
}
static void MRUI_BuildRows(){
 mrui.rows.clear();auto add=[](int a,int i,const std::string& label,const std::string& help){mrui.rows.push_back({a,i,label,help});};
 if(mrui.tab==stmatch::Server){add(MR_HOSTNAME,0,"Server name","Public server name. Presets include this name.");add(MR_PASSWORD,0,"Host password","Optional join password, held only for this draft; never saved in a preset.");}
 for(int i=0;i<stmatch::RuleCount;++i){const auto& r=stmatch::rules[i];int type=mrui.draft.get("g_gametype");if(r.tab!=mrui.tab||!stmatch::visible(r,mrui.draft)||!Q_stricmp(r.cvar,"g_allowVote")||((type==3||type==4)&&!Q_stricmp(r.cvar,"fraglimit")))continue;add(MR_RULE,i,r.label,r.help);}
 if(mrui.tab==stmatch::Force){
  for(int i=0;i<stmatch::ForceCount;++i)add(MR_FORCE,i,std::string("Force cap: ")+stmatch::forceNames[i],"Custom Force: maximum level 0 disables this power; 1 through 3 caps allocation and grants. Restricted keeps Jump, Speed, Saber Attack and Saber Defense.");
  for(int i=1;i<stmatch::WeaponCount;++i)add(MR_WEAPON,i,stmatch::weaponNames[i],"Custom weapons: checked means available. Melee and Lightsaber always remain available. Preferences are retained while another weapon preset is active.");
 }
 if(mrui.tab==stmatch::Teams){
  if(mrui.local)add(MR_REPLACE,0,"Replace existing bots on apply","Explicitly removes existing bots before spawning this draft's roster. Human players are never removed. With this off, roster entries are additions only.");
  for(int i=0;i<stmatch::MaxBots;++i)add(MR_BOT,i,std::string(mrui.local&&!mrui.replaceBots?"Add slot ":"Slot ")+std::to_string(i+1),"Choose a loaded bot definition, role, skill and team. During a match these are additions unless Replace existing bots is selected. Presets also include the current live bots. Always reserve a connection beyond your bots.");
 }
 if(mrui.tab==stmatch::Match){add(MR_MAP,0,"Selected map","Choose an installed map compatible with this game type, or enter an installed map name. The Host screen's existing map chooser remains available.");add(MR_ROTATION,0,"Ordered map rotation","Edit up to 32 maps in order. The server uses this order when automatic map rotation is enabled.");}
 if(mrui.tab==stmatch::Server)for(int i=0;i<14;++i)add(MR_VOTE,i,std::string("Allow vote: ")+mrVotes[i],"Controls this individual vote permission. Other vote permissions remain unchanged.");
 mrui.scroll=std::max(0,std::min(mrui.scroll,std::max(0,int(mrui.rows.size())-9)));
}
static stmatch::Bot* MRUI_Bot(int slot){for(auto& b:mrui.draft.bots)if(b.slot==slot)return &b;return nullptr;}
static bool MRUI_TeamAllowed(int team){int type=mrui.draft.get("g_gametype");if(team==0)return true;if(type==8||type==7)return team==1||team==2;if(type!=6)return false;int count=mrui.draft.get("g_tffaTeams");for(int i=1;i<=count;++i)if(mrTeamIds[i]==team)return true;return false;}
static void MRUI_NormalizeBots(){for(auto& b:mrui.draft.bots){if(!stmatch::roleAllowed(mrui.draft.get("g_gametype"),b.role))b.role=0;if(!MRUI_TeamAllowed(b.team))b.team=0;}}
static void MRUI_ImportHostRoster(){
 mrui.draft.bots.clear();int type=mrui.draft.get("g_gametype"),limit=type==6?UI_TffaPlayableSlots():PLAYERS_PER_TEAM*2;
 for(int slot=0;slot<limit;++slot){int bot=int(trap->Cvar_VariableValue(UI_TffaSlotCvar(slot)))-2;if(bot<0||bot>=UI_GetNumBots())continue;
  stmatch::Bot b;b.slot=slot;b.model=UI_GetBotNameByNumber(bot);b.skill=std::max(1,std::min(5,int(trap->Cvar_VariableValue("g_spSkill"))));b.team=type==6?UI_TffaSlotTeam(slot):(type==8||type==7)?(slot%2?1:2):0;mrui.draft.bots.push_back(b);}
 MRUI_NormalizeBots();
}
static void MRUI_RememberHost(){
 mrui.hostMode=int(trap->Cvar_VariableValue("ui_netGametype"));mrui.hostMap=int(trap->Cvar_VariableValue("ui_currentNetMap"));
 mrui.hostTeams=int(trap->Cvar_VariableValue("ui_stHostTeams"));mrui.hostSize=int(trap->Cvar_VariableValue("ui_stHostTeamSize"));mrui.hostOpenSlots=int(trap->Cvar_VariableValue("ui_stTffaOpenSlots"));mrui.hostMaxPlayers=int(trap->Cvar_VariableValue("sv_maxclients"));
}
static void MRUI_HostSelection(bool first){
 int index=int(trap->Cvar_VariableValue("ui_netGametype"));int type=index>=0&&index<uiInfo.numGameTypes?uiInfo.gameTypes[index].gtEnum:0;
 int teams=int(trap->Cvar_VariableValue("ui_stHostTeams")),size=int(trap->Cvar_VariableValue("ui_stHostTeamSize")),openSlots=int(trap->Cvar_VariableValue("ui_stTffaOpenSlots")),maxPlayers=int(trap->Cvar_VariableValue("sv_maxclients"));
 bool modeChanged=first||index!=mrui.hostMode,teamsChanged=first||teams!=mrui.hostTeams,sizeChanged=first||size!=mrui.hostSize,openChanged=first||openSlots!=mrui.hostOpenSlots,maxChanged=first||maxPlayers!=mrui.hostMaxPlayers;
 if(modeChanged&&stmatch::valid(stmatch::find("g_gametype"),type))mrui.draft.set("g_gametype",type);
 if(type==6){
  if(modeChanged||teamsChanged)mrui.draft.set("g_tffaTeams",ST_TffaCount(teams));
  if((modeChanged||sizeChanged)&&size>=0&&size<=16)mrui.draft.set("st_matchTeamCap",size);
  // Open TFFA has its own active player-limit field. Its lower value must not
  // be replaced by the hidden legacy sv_maxclients field from another mode.
  if(modeChanged||sizeChanged||(size?(teamsChanged||maxChanged):openChanged)){int clients=size?UI_HostMaxClients():UI_TffaPlayableSlots();if(clients>=2&&clients<=32)mrui.draft.set("sv_maxclients",clients);}
 }else if((modeChanged||maxChanged)&&maxPlayers>=2&&maxPlayers<=32)mrui.draft.set("sv_maxclients",maxPlayers);
 MRUI_NormalizeBots();
 int map=int(trap->Cvar_VariableValue("ui_currentNetMap"));if((first||map!=mrui.hostMap)&&map>=0&&map<uiInfo.mapCount&&stmatch::mapName(uiInfo.mapList[map].mapLoadName))mrui.draft.map=uiInfo.mapList[map].mapLoadName;
 if(!mrui.rosterEdited)MRUI_ImportHostRoster();MRUI_RememberHost();
}
static void MRUI_Snapshot(bool includePending=true){
 mrui.draft=stmatch::Preset();
 for(int i=0;i<stmatch::RuleCount;++i){int number;if(MRUI_ActiveNumber(stmatch::rules[i].cvar,number)&&stmatch::valid(i,number))mrui.draft.values[i]=number;}
 for(int i=0;i<stmatch::ForceCount;++i){int number;if(stmatch::integer(MRUI_Cvar(va("st_matchForceCap%d",i)),number)&&number>=0&&number<=3)mrui.draft.force[i]=number;}
 int weapon;if(MRUI_ActiveNumber("st_matchWeaponDisable",weapon)&&weapon>=0&&weapon<(1<<stmatch::WeaponCount))mrui.draft.weaponDisable=weapon&~((1<<2)|(1<<3));
 mrui.draft.hostname=MRUI_Cvar("sv_hostname");if(!stmatch::safeText(mrui.draft.hostname,100))mrui.draft.hostname="Saber Trials Server";
 mrui.draft.rotation=MRUI_Cvar("st_matchRotation");mrui.password=MRUI_Cvar("g_password");mrui.originalPassword=mrui.password;
 if(mrui.local){std::string map=MRUI_Cvar("mapname");if(stmatch::mapName(map))mrui.draft.map=map;}
 else MRUI_HostSelection(true);
 mrui.original=mrui.draft;
 if(mrui.local&&includePending){
  for(int i=0;i<stmatch::RuleCount;++i){int value;if(stmatch::integer(MRUI_Cvar(va("st_matchPending_%s",stmatch::rules[i].cvar)),value)&&stmatch::valid(i,value))mrui.draft.values[i]=value;}
  for(int i=0;i<stmatch::ForceCount;++i){int value;if(stmatch::integer(MRUI_Cvar(va("st_matchPending_force%d",i)),value)&&value>=0&&value<=3)mrui.draft.force[i]=value;}
  int value;if(stmatch::integer(MRUI_Cvar("st_matchPending_weapons"),value)&&value>=0&&value<(1<<stmatch::WeaponCount))mrui.draft.weaponDisable=value&~((1<<2)|(1<<3));
  std::string text=MRUI_Cvar("st_matchPending_hostname");if(!text.empty()||MRUI_Cvar("st_matchPending_hashostname")=="1")mrui.draft.hostname=text;
  text=MRUI_Cvar("st_matchPending_map");if(!text.empty())mrui.draft.map=text;
  text=MRUI_Cvar("st_matchPending_rotation");if(!text.empty()||MRUI_Cvar("st_matchPending_hasrotation")=="1")mrui.draft.rotation=text;
  mrui.replaceBots=MRUI_Cvar("st_matchPending_clearbots")=="1";
  for(int slot=0;slot<stmatch::MaxBots;++slot){std::string model=MRUI_Cvar(va("st_matchPending_bot%d_model",slot));if(model.empty())continue;stmatch::Bot bot;bot.slot=slot;bot.model=model;int value;
   if(stmatch::integer(MRUI_Cvar(va("st_matchPending_bot%d_skill",slot)),value))bot.skill=value;
   if(stmatch::integer(MRUI_Cvar(va("st_matchPending_bot%d_team",slot)),value))bot.team=value;
   if(stmatch::integer(MRUI_Cvar(va("st_matchPending_bot%d_role",slot)),value))bot.role=value;
   mrui.draft.bots.push_back(bot);}
 }
 mrui.cached=true;
}
static void MRUI_Open(bool start=false){
 if(MRUI_Remote()){Menus_CloseByName("advancedcreateserver");return;}
 if(!mrui.routing){mrui.previousKeyboardRoute=MRUI_Cvar("st_uiNameKeyboard");trap->Cvar_Register(NULL,"st_uiNameKeyboard","0",CVAR_TEMP);trap->Cvar_Set("st_uiNameKeyboard","1");mrui.routing=true;}
 bool local=MRUI_Server();if(local!=mrui.local){mrui.cached=false;mrui.rosterEdited=false;mrui.passwordEdited=false;mrui.replaceBots=false;}
 mrui.local=local;mrui.active=true;mrui.menu=Menu_GetFocused()?Menu_GetFocused()->window.name:"createserver";mrui.status.clear();mrui.help.clear();mrui.focus=0;mrui.pointer=true;mrui.drag=-1;mrui.modal=MR_MAIN;
 if(!mrui.cached)MRUI_Snapshot();else if(!local)MRUI_HostSelection(false);
 if(start)mrui.modal=MR_SUMMARY;
}
static void MRUI_Close(bool keep){
 if(mrui.routing){trap->Cvar_Set("st_uiNameKeyboard",mrui.previousKeyboardRoute.empty()?"0":mrui.previousKeyboardRoute.c_str());mrui.routing=false;}
 if(keep&&!mrui.local){
  int type=mrui.draft.get("g_gametype");for(int i=0;i<uiInfo.numGameTypes;++i)if(uiInfo.gameTypes[i].gtEnum==type){trap->Cvar_SetValue("ui_netGametype",i);trap->Cvar_Update(&ui_netGametype);mrui.hostMode=i;break;}
  trap->Cvar_SetValue("ui_actualNetGametype",type);trap->Cvar_Update(&ui_actualNetGametype);trap->Cvar_SetValue("ui_stHostTeams",mrui.draft.get("g_tffaTeams"));UI_MapCountByGameType(qfalse);
  for(int i=0,selection=0;i<uiInfo.mapCount;++i){if(mrui.draft.map==uiInfo.mapList[i].mapLoadName){trap->Cvar_SetValue("ui_currentNetMap",i);trap->Cvar_Update(&ui_currentNetMap);mrui.hostMap=i;Menu_SetFeederSelection(NULL,FEEDER_ALLMAPS,selection,"createserver");break;}if(uiInfo.mapList[i].active)++selection;}
  MRUI_RememberHost();
 }
 mrui.active=false;mrui.drag=-1;mrui.modal=0;if(!keep){mrui.cached=false;mrui.password.clear();mrui.originalPassword.clear();mrui.passwordEdited=false;mrui.rosterEdited=false;mrui.replaceBots=false;}
 if(mrui.menu=="advancedcreateserver")Menus_CloseByName("advancedcreateserver");
}
static void MRUI_ListFiles(){
 mrui.files.clear();char list[16384]={0};int count=trap->FS_GetFileList("match-presets","fcf",list,sizeof(list));const char* p=list;
 for(int i=0;i<count&&p<list+sizeof(list)&&*p;++i){size_t len=strlen(p);std::string name(p);p+=len+1;if(name.size()<=12||name.substr(name.size()-12)!=".stmatch.fcf")continue;name.resize(name.size()-12);if(!stmatch::filename(name))continue;
  fileHandle_t f=0;int bytes=trap->FS_Open(("match-presets/"+name+".stmatch.fcf").c_str(),&f,FS_READ);if(f)trap->FS_Close(f);if(bytes>0&&bytes<=32768)mrui.files.push_back(name);}
 std::sort(mrui.files.begin(),mrui.files.end());mrui.files.erase(std::unique(mrui.files.begin(),mrui.files.end()),mrui.files.end());
}
static bool MRUI_Assets(const stmatch::Preset& p,std::string& error){
 auto installed=[](const std::string& map){fileHandle_t file=0;int length=trap->FS_Open(("maps/"+map+".bsp").c_str(),&file,FS_READ);if(file)trap->FS_Close(file);return length>0;};
 if(!installed(p.map)){error="Selected map is not installed: "+p.map;return false;}
 std::istringstream rotation(p.rotation);std::string map;while(rotation>>map)if(!installed(map)){error="Rotation map is not installed: "+map;return false;}
 for(const auto& b:p.bots){bool found=false;for(int i=0;i<UI_GetNumBots();++i)if(!Q_stricmp(b.model.c_str(),UI_GetBotNameByNumber(i))){found=true;break;}if(!found){error="Bot definition is not installed: "+b.model;return false;}}
 return true;
}
static bool MRUI_Valid(){if(!stmatch::validate(mrui.draft,mrui.status)||!MRUI_Assets(mrui.draft,mrui.status))return false;if(!stmatch::safeText(mrui.password,64)){mrui.status="Password must be at most 64 characters and cannot contain quotes, backslashes, semicolons or control characters.";return false;}return true;}
static void MRUI_Edit(int target,int index,const std::string& value,int limit,const std::string& title){mrui.editTarget=target;mrui.editIndex=index;mrui.edit=value;mrui.editLimit=limit;mrui.editTitle=title;mrui.caret=value.size();mrui.editReturn=mrui.modal;mrui.modal=MR_EDIT;mrui.focus=0;mrui.shift=false;mrui.editReplace=true;mrui.status.clear();}
static bool MRUI_CommitEdit(){
 int n;const std::string& text=mrui.edit;
 if(mrui.editTarget==MR_NUMBER){if(!stmatch::integer(text,n)||!stmatch::valid(mrui.editIndex,n)){mrui.status="Enter a whole number in the displayed range.";return false;}mrui.draft.values[mrui.editIndex]=n;}
 else if(mrui.editTarget==MR_FILENAME){if(!stmatch::filename(text)){mrui.status="Use 1 to 40 letters, numbers, underscores or hyphens.";return false;}mrui.filename=text;}
 else if(mrui.editTarget==MR_HOSTNAME||mrui.editTarget==MR_PASSWORD){if(!stmatch::safeText(text,mrui.editTarget==MR_PASSWORD?64:100)){mrui.status="Use text without quotes, backslashes, semicolons or control characters.";return false;}if(mrui.editTarget==MR_HOSTNAME)mrui.draft.hostname=text;else{mrui.password=text;mrui.passwordEdited=true;}}
 else if(mrui.editTarget==MR_MAP||mrui.editTarget==MR_ROTEDIT||mrui.editTarget==MR_ROTADD){if(!stmatch::mapName(text)){mrui.status="Enter a map name such as mp/ffa3 using letters, numbers, /, _ or -.";return false;}
  if(mrui.editTarget==MR_MAP)mrui.draft.map=text;else{std::istringstream in(mrui.draft.rotation);std::vector<std::string> maps;std::string map;while(in>>map)maps.push_back(map);if(mrui.editTarget==MR_ROTADD){if(maps.size()>=32){mrui.status="Rotation already has 32 maps.";return false;}maps.push_back(text);}else if(mrui.editIndex>=0&&mrui.editIndex<int(maps.size()))maps[mrui.editIndex]=text;std::string candidate;for(const auto& m:maps){if(!candidate.empty())candidate+=' ';candidate+=m;}if(candidate.size()>stmatch::RotationLimit){mrui.status="Rotation exceeds the safe command length. Shorten or remove a map name.";return false;}mrui.draft.rotation=candidate;}}
 MRUI_NormalizeBots();mrui.modal=mrui.editReturn;mrui.status.clear();mrui.focus=0;return true;
}
static void MRUI_ChangeRule(int id,int delta){
 const auto& r=stmatch::rules[id];std::string inactive=stmatch::inactive(r,mrui.draft);if(!inactive.empty())mrui.status=inactive;if(mrui.local&&!Q_stricmp(r.cvar,"ui_dedicated")){mrui.status="Hosting process can only be selected before starting a new server.";return;}
 int value=mrui.draft.values[id];if(*r.choices){for(int n=0;n<=r.high-r.low;++n){value+=delta;if(value>r.high)value=r.low;if(value<r.low)value=r.high;if(stmatch::valid(id,value))break;}}else value=std::max(r.low,std::min(r.high,value+delta*r.step));mrui.draft.values[id]=value;MRUI_NormalizeBots();
}
static void MRUI_Review(){
 mrui.review.clear();mrui.review.push_back(std::string(mrui.local?"Apply to local server: ":"Start match: ")+mrui.draft.map);mrui.review.push_back("Server: "+mrui.draft.hostname);mrui.review.push_back(std::string("Join password: ")+(mrui.password.empty()?"open server":"configured (never included in presets)"));
 bool duel=mrui.draft.get("g_gametype")==3||mrui.draft.get("g_gametype")==4;
 if(duel)mrui.review.push_back("Duel round: one kill");
 for(int i=0;i<stmatch::RuleCount;++i){const auto& r=stmatch::rules[i];if((mrui.local&&!Q_stricmp(r.cvar,"ui_dedicated"))||(duel&&!Q_stricmp(r.cvar,"fraglimit")))continue;if(!mrui.local||mrui.draft.values[i]!=mrui.original.values[i])mrui.review.push_back(std::string(r.label)+": "+stmatch::label(i,mrui.draft.values[i])+(mrui.local&&r.restart?" [restart / next boundary]":""));}
 for(int i=0;i<stmatch::ForceCount;++i)if(mrui.draft.get("st_forceModeActive")==2||mrui.draft.force[i]!=mrui.original.force[i])mrui.review.push_back(std::string(stmatch::forceNames[i])+" maximum: "+std::to_string(mrui.draft.force[i])+(mrui.draft.get("st_forceModeActive")!=2?" (stored preference)":""));
 for(int i=1;i<stmatch::WeaponCount;++i)if(mrui.draft.get("st_weaponsActive")==2||((mrui.draft.weaponDisable^mrui.original.weaponDisable)&(1<<i)))mrui.review.push_back(std::string(stmatch::weaponNames[i])+": "+((mrui.draft.weaponDisable&(1<<i))?"disabled":"enabled")+(mrui.draft.get("st_weaponsActive")!=2?" (stored preference)":""));
 if(!mrui.local||mrui.draft.get("g_allowVote")!=mrui.original.get("g_allowVote"))for(int i=0;i<14;++i)mrui.review.push_back(std::string("Vote ")+mrVotes[i]+": "+((mrui.draft.get("g_allowVote")&(1<<i))?"allowed":"disabled"));
 mrui.review.push_back("Rotation: "+(mrui.draft.rotation.empty()?std::string("none"):mrui.draft.rotation));
 mrui.review.push_back(std::string(mrui.local?(mrui.replaceBots?"Replace existing bots; new roster: ":"Add roster without removing existing players: "):"Bot roster: ")+std::to_string(mrui.draft.bots.size()));
 for(const auto& b:mrui.draft.bots)mrui.review.push_back("Slot "+std::to_string(b.slot+1)+": "+b.model+" / "+stmatch::roleNames[b.role]+" / skill "+std::to_string(b.skill)+" / team "+std::to_string(b.team));
 mrui.review.push_back("Connection capacity: "+std::to_string(mrui.draft.get("sv_maxclients"))+" (includes humans, bots and spectators)");
}
static void MRUI_Send(const std::string& command){trap->Cmd_ExecuteText(EXEC_APPEND,(command+"\n").c_str());}
static bool MRUI_NumberChanged(const char* live,int target,const char* pending){int value;return !MRUI_Cvar(pending).empty()||!MRUI_ActiveNumber(live,value)||value!=target;}
static bool MRUI_Apply(bool later){
 if(MRUI_Remote()||MRUI_Server()!=mrui.local){mrui.status="Server state changed. Close and reopen Match Rules.";return false;}if(!MRUI_Valid())return false;
 if(mrui.local){
  for(int i=0;i<stmatch::RuleCount;++i)if(Q_stricmp(stmatch::rules[i].cvar,"ui_dedicated")&&Q_stricmp(stmatch::rules[i].cvar,"st_weaponsActive")&&(!(mrui.draft.get("g_gametype")==3||mrui.draft.get("g_gametype")==4)||Q_stricmp(stmatch::rules[i].cvar,"fraglimit"))&&MRUI_NumberChanged(stmatch::rules[i].cvar,mrui.draft.values[i],va("st_matchPending_%s",stmatch::rules[i].cvar)))MRUI_Send(std::string("st_match_set ")+stmatch::rules[i].cvar+" "+std::to_string(mrui.draft.values[i]));
  for(int i=0;i<stmatch::ForceCount;++i)if(MRUI_NumberChanged(va("st_matchForceCap%d",i),mrui.draft.force[i],va("st_matchPending_force%d",i)))MRUI_Send("st_match_force "+std::to_string(i)+" "+std::to_string(mrui.draft.force[i]));
  // Explicit adoption supplies the complete weapon domain. An inactive custom
  // preference edit must retain legacy Full mode even when its raw cvar is 0.
  if(MRUI_NumberChanged("st_weaponsActive",mrui.draft.get("st_weaponsActive"),"st_matchPending_st_weaponsActive")||MRUI_NumberChanged("st_matchWeaponDisable",mrui.draft.weaponDisable,"st_matchPending_weapons")){
   MRUI_Send("st_match_set st_weaponsActive "+std::to_string(mrui.draft.get("st_weaponsActive")));MRUI_Send("st_match_weapons "+std::to_string(mrui.draft.weaponDisable));}
  if(mrui.draft.map!=MRUI_Cvar("mapname")||!MRUI_Cvar("st_matchPending_map").empty())MRUI_Send("st_match_text map \""+mrui.draft.map+"\"");
  if(mrui.draft.rotation!=MRUI_Cvar("st_matchRotation")||!MRUI_Cvar("st_matchPending_rotation").empty()||MRUI_Cvar("st_matchPending_hasrotation")=="1")MRUI_Send("st_match_text rotation \""+mrui.draft.rotation+"\"");
  if(mrui.draft.hostname!=MRUI_Cvar("sv_hostname")||!MRUI_Cvar("st_matchPending_hostname").empty()||MRUI_Cvar("st_matchPending_hashostname")=="1")MRUI_Send("st_match_text hostname \""+mrui.draft.hostname+"\"");
  if(mrui.passwordEdited)MRUI_Send("st_match_text password \""+mrui.password+"\"");
  // Roster edits are explicit server commands, held until this review is accepted.
  if(mrui.rosterEdited||mrui.replaceBots||!mrui.draft.bots.empty()||!MRUI_Cvar("st_matchPending_bots").empty()||!MRUI_Cvar("st_matchPending_clearbots").empty()){
   MRUI_Send("st_match_rosterreset");if(mrui.replaceBots)MRUI_Send("st_match_clearbots");
   for(const auto& b:mrui.draft.bots)MRUI_Send("st_match_addbot \""+b.model+"\" "+std::to_string(b.skill)+" "+std::to_string(b.team)+" "+std::to_string(b.role)+" "+std::to_string(b.slot));}
  MRUI_Send(later?"st_match_apply later":"st_match_apply now");
  MRUI_Close(false);
 }else{
  // This replaces legacy StartServer: it cannot stomp custom Force, weapons, teams or limits.
  for(int i=0;i<stmatch::RuleCount;++i)trap->Cvar_Set(stmatch::rules[i].cvar,std::to_string(mrui.draft.values[i]).c_str());
  for(int i=0;i<stmatch::ForceCount;++i)trap->Cvar_Set(va("st_matchForceCap%d",i),std::to_string(mrui.draft.force[i]).c_str());
  trap->Cvar_Set("st_matchWeaponDisable",std::to_string(mrui.draft.weaponDisable).c_str());trap->Cvar_Set("st_matchRotation",mrui.draft.rotation.c_str());trap->Cvar_Set("sv_hostname",mrui.draft.hostname.c_str());trap->Cvar_Set("g_password",mrui.password.c_str());
  // A prior server may have stopped between staging a roster and its frame.
  // An accepted new match owns a fresh roster transaction, including no bots.
  trap->Cvar_Set("st_matchRosterExecute","0");trap->Cvar_Set("st_matchRosterCount","0");trap->Cvar_Set("st_matchRosterClear","0");
  for(int i=0;i<stmatch::MaxBots;++i)trap->Cvar_Set(va("st_matchRoster_%d",i),"");
  trap->Cvar_Set("st_matchManaged","1");trap->Cvar_Set("st_matchInitialRosterPending",mrui.draft.bots.empty()?"0":"1");trap->Cvar_Set("dedicated",std::to_string(mrui.draft.get("ui_dedicated")).c_str());trap->Cvar_Set("g_tffaTeamSize","0");trap->Cvar_Set("cg_cameraOrbit","0");
  if(mrui.draft.get("g_gametype")==3||mrui.draft.get("g_gametype")==4)trap->Cvar_Set("fraglimit","1");
  MRUI_Send("wait; wait; map "+mrui.draft.map);MRUI_Send("wait; wait");
  for(const auto& b:mrui.draft.bots)MRUI_Send("st_match_addbot \""+b.model+"\" "+std::to_string(b.skill)+" "+std::to_string(b.team)+" "+std::to_string(b.role)+" "+std::to_string(b.slot));
  if(!mrui.draft.bots.empty())MRUI_Send("st_match_apply roster");
  MRUI_Close(false);Menus_CloseAll();trap->Key_SetCatcher(trap->Key_GetCatcher()&~KEYCATCH_UI);
 }
 return true;
}
static bool MRUI_SaveSnapshot(){
 mrui.presetToSave=mrui.draft;
 if(mrui.local&&!mrui.replaceBots){
  if(MRUI_Cvar("st_matchLiveReady")!="1"){mrui.status="Live bot roster is still updating. Wait a moment and save again.";return false;}
  if(trap->Cvar_VariableValue("st_matchLiveBotUnresolved")!=0){mrui.status="A live bot's original definition cannot be recovered. Choose Replace existing bots with a complete roster before saving.";return false;}
  mrui.presetToSave.bots.clear();std::array<bool,stmatch::MaxBots> used={};
  for(int slot=0;slot<stmatch::MaxBots;++slot)if(MRUI_Cvar(va("st_matchLive_bot%d_present",slot))=="1"){
   stmatch::Bot bot;bot.slot=slot;bot.model=MRUI_Cvar(va("st_matchLive_bot%d_model",slot));
   if(MRUI_Cvar(va("st_matchLive_bot%d_unresolved",slot))=="1"||bot.model.empty()||!stmatch::integer(MRUI_Cvar(va("st_matchLive_bot%d_skill",slot)),bot.skill)||!stmatch::integer(MRUI_Cvar(va("st_matchLive_bot%d_team",slot)),bot.team)||!stmatch::integer(MRUI_Cvar(va("st_matchLive_bot%d_role",slot)),bot.role)){mrui.status="A live bot cannot be represented safely. Your preset and draft are unchanged.";return false;}
   used[slot]=true;mrui.presetToSave.bots.push_back(bot);
  }
  for(const auto& addition:mrui.draft.bots){stmatch::Bot bot=addition;if(used[bot.slot]){int slot=0;while(slot<stmatch::MaxBots&&used[slot])++slot;if(slot==stmatch::MaxBots){mrui.status="Current bots plus additions leave no connection for players.";return false;}bot.slot=slot;}used[bot.slot]=true;mrui.presetToSave.bots.push_back(bot);}
 }
 return stmatch::validate(mrui.presetToSave,mrui.status)&&MRUI_Assets(mrui.presetToSave,mrui.status);
}
static void MRUI_FileAction(int action){
 if(!stmatch::filename(mrui.filename)){mrui.status="Choose or enter a preset name (1 to 40 letters, numbers, _ or -).";return;}
 if(action==MR_SAVE&&!MRUI_SaveSnapshot())return;
 if(action==MR_LOAD){fileHandle_t f=0;int size=trap->FS_Open(("match-presets/"+mrui.filename+".stmatch.fcf").c_str(),&f,FS_READ);if(size<=0||size>32768||!f){if(f)trap->FS_Close(f);mrui.status="Preset is missing, deleted or too large. Your draft is unchanged.";return;}
  std::string text(size,'\0');int read=trap->FS_Read(&text[0],size,f);trap->FS_Close(f);if(read!=size||!stmatch::decode(text,mrui.presetToLoad,mrui.status)||!MRUI_Assets(mrui.presetToLoad,mrui.status)){if(read!=size)mrui.status="Preset read was incomplete. Your draft is unchanged.";return;}}
 mrui.confirm=action;mrui.modal=MR_CONFIRM;mrui.focus=0;
}
static void MRUI_Confirm(){
 if(mrui.confirm==MR_CANCEL){MRUI_Close(false);return;}
 if(mrui.confirm==MR_QUEUECANCEL){if(MRUI_Server()&&!MRUI_Remote())MRUI_Send("st_match_cancel");mrui.cached=false;mrui.replaceBots=false;mrui.rosterEdited=false;mrui.passwordEdited=false;MRUI_Snapshot(false);mrui.modal=MR_MAIN;mrui.status="Requested cancellation of the server's queued changes.";return;}
 if(mrui.confirm==MR_LOAD){mrui.draft=mrui.presetToLoad;if(mrui.local){mrui.draft.set("ui_dedicated",mrui.original.get("ui_dedicated"));mrui.replaceBots=true;}mrui.rosterEdited=true;mrui.modal=MR_FILES;mrui.status="Preset loaded into draft. Password unchanged; review before applying.";return;}
 fileHandle_t f=0;trap->FS_Open(("match-presets/"+mrui.filename+".stmatch.fcf").c_str(),&f,FS_WRITE);if(!f){mrui.status="Could not write this preset.";mrui.modal=MR_FILES;return;}
 // The native UI VFS has no remove import. A zero-byte tombstone hides the name
 // and overrides any lower-priority package file; reusing this name is supported.
 std::string data=mrui.confirm==MR_SAVE?stmatch::encode(mrui.presetToSave):std::string();int written=trap->FS_Write(data.data(),int(data.size()),f);trap->FS_Close(f);
 mrui.status=written==int(data.size())?(mrui.confirm==MR_SAVE?"Preset saved. Password excluded.":"Preset deleted."):"Preset write was incomplete.";mrui.modal=MR_FILES;MRUI_ListFiles();
}
static void MRUI_KeyAction(int code){
 if(code==256){mrui.shift=!mrui.shift;return;}if(code==257){mrui.editReplace=false;if(mrui.caret){mrui.edit.erase(--mrui.caret,1);}return;}if(code==258){mrui.edit.clear();mrui.caret=0;mrui.editReplace=false;return;}if(code==259){mrui.editReplace=false;if(mrui.caret)--mrui.caret;return;}if(code==260){mrui.editReplace=false;if(mrui.caret<mrui.edit.size())++mrui.caret;return;}if(code==261){mrui.modal=mrui.editReturn;mrui.status.clear();return;}if(code==262){MRUI_CommitEdit();return;}
 if(code<32||code>126||code=='"'||code=='\\'||code==';')return;if(mrui.editReplace){mrui.edit.clear();mrui.caret=0;mrui.editReplace=false;}if(int(mrui.edit.size())>=mrui.editLimit)return;mrui.edit.insert(mrui.caret++,1,char(code));
}
static void MRUI_Action(const MRHit& h,int direction=1){
 mrui.status.clear();int a=h.action;
 if(a==MR_TAB){mrui.tab=h.a;mrui.scroll=0;mrui.focus=h.a;mrui.help.clear();}
 else if(a==MR_RULE)MRUI_ChangeRule(h.a,direction);
 else if(a==MR_NUMBER){const auto& r=stmatch::rules[h.a];if(mrui.local&&!Q_stricmp(r.cvar,"ui_dedicated")){mrui.status="Hosting process is start-only.";return;}MRUI_Edit(MR_NUMBER,h.a,std::to_string(mrui.draft.values[h.a]),11,std::string(r.label)+" ("+std::to_string(r.low)+" to "+std::to_string(r.high)+")");}
 else if(a==MR_SLIDER){std::string reason=stmatch::inactive(stmatch::rules[h.a],mrui.draft);if(!reason.empty())mrui.status=reason;mrui.drag=h.a;const auto& r=stmatch::rules[h.a];float fraction=Com_Clamp(0,1,(uiInfo.uiDC.cursorx-h.x)/h.w);int n=r.low+int((r.high-r.low)*fraction+.5f);mrui.draft.values[h.a]=std::max(r.low,std::min(r.high,n));}
 else if(a==MR_FORCE){if(mrui.draft.get("st_forceModeActive")!=2)mrui.status="Custom cap preference saved; becomes active with Custom Force rules.";mrui.draft.force[h.a]=(mrui.draft.force[h.a]+direction+4)%4;}
 else if(a==MR_WEAPON){if(h.a==2||h.a==3){mrui.status="Melee and Lightsaber always remain available.";return;}if(mrui.draft.get("st_weaponsActive")!=2)mrui.status="Weapon preference saved; becomes active with Custom weapon rules.";mrui.draft.weaponDisable^=1<<h.a;}
 else if(a==MR_VOTE)mrui.draft.set("g_allowVote",mrui.draft.get("g_allowVote")^(1<<h.a));
 else if(a==MR_HOSTNAME)MRUI_Edit(a,0,mrui.draft.hostname,100,"Server name");
 else if(a==MR_PASSWORD)MRUI_Edit(a,0,mrui.password,64,"Host password (never saved in presets)");
 else if(a==MR_MAP){mrui.modal=MR_MAPS;mrui.page=0;mrui.focus=0;}
 else if(a==MR_MAPEDIT)MRUI_Edit(MR_MAP,0,mrui.draft.map,60,"Installed map name");
 else if(a==MR_MAPCHOICE){mrui.draft.map=uiInfo.mapList[h.a].mapLoadName;mrui.modal=MR_MAIN;mrui.focus=0;}
 else if(a==MR_ROTATION){mrui.modal=MR_ROTATIONS;mrui.page=0;mrui.focus=0;}
 else if(a==MR_ROTADD)MRUI_Edit(a,0,mrui.draft.map,60,"Append map to rotation");
 else if(a==MR_ROTUP||a==MR_ROTDOWN||a==MR_ROTDELETE||a==MR_ROTEDIT){std::istringstream in(mrui.draft.rotation);std::vector<std::string> maps;std::string map;while(in>>map)maps.push_back(map);if(h.a<0||h.a>=int(maps.size()))return;if(a==MR_ROTEDIT){MRUI_Edit(a,h.a,maps[h.a],60,"Rotation map "+std::to_string(h.a+1));return;}if(a==MR_ROTDELETE)maps.erase(maps.begin()+h.a);else{int other=h.a+(a==MR_ROTUP?-1:1);if(other>=0&&other<int(maps.size()))std::swap(maps[h.a],maps[other]);}mrui.draft.rotation.clear();for(const auto& m:maps){if(!mrui.draft.rotation.empty())mrui.draft.rotation+=' ';mrui.draft.rotation+=m;}}
 else if(a==MR_BOT){mrui.slot=h.a;mrui.modal=MR_BOTS;mrui.page=0;mrui.focus=0;}
 else if(a==MR_BOTCHOICE){auto* bot=MRUI_Bot(mrui.slot);if(h.a<0){if(bot)mrui.draft.bots.erase(std::remove_if(mrui.draft.bots.begin(),mrui.draft.bots.end(),[](const stmatch::Bot& b){return b.slot==mrui.slot;}),mrui.draft.bots.end());}
  else if(h.a<UI_GetNumBots()){if(!bot){stmatch::Bot added;added.slot=mrui.slot;added.skill=mrui.draft.get("st_botSkill");mrui.draft.bots.push_back(added);bot=&mrui.draft.bots.back();}bot->model=UI_GetBotNameByNumber(h.a);}mrui.rosterEdited=true;mrui.modal=MR_MAIN;mrui.focus=0;}
 else if(a==MR_ROLE||a==MR_SKILL||a==MR_TEAM){auto* bot=MRUI_Bot(h.a);if(!bot)return;mrui.rosterEdited=true;if(a==MR_SKILL)bot->skill=(bot->skill-1+direction+5)%5+1;else if(a==MR_ROLE){int next=bot->role;for(int i=0;i<8;++i){next=(next+direction+8)%8;if(stmatch::roleAllowed(mrui.draft.get("g_gametype"),next))break;}bot->role=next;}else{int index=0;for(int i=0;i<9;++i)if(mrTeamIds[i]==bot->team)index=i;for(int i=0;i<9;++i){index=(index+direction+9)%9;if(MRUI_TeamAllowed(mrTeamIds[index]))break;}bot->team=mrTeamIds[index];}}
 else if(a==MR_REPLACE)mrui.replaceBots=!mrui.replaceBots;
 else if(a==MR_PRESETS){MRUI_ListFiles();mrui.modal=MR_FILES;mrui.page=0;mrui.focus=0;}
 else if(a==MR_FILENAME)MRUI_Edit(a,0,mrui.filename,40,"Preset name (letters, numbers, _ and -)");
 else if(a==MR_FILE&&h.a>=0&&h.a<int(mrui.files.size()))mrui.filename=mrui.files[h.a];
 else if(a==MR_SAVE||a==MR_LOAD||a==MR_DELETE)MRUI_FileAction(a);
 else if(a==MR_REVIEW){if(MRUI_Valid()){mrui.modal=MR_SUMMARY;mrui.reviewScroll=0;mrui.focus=0;}}
 else if(a==MR_NOW||a==MR_LATER)MRUI_Apply(a==MR_LATER);
 else if(a==MR_CANCEL){mrui.confirm=MR_CANCEL;mrui.modal=MR_CONFIRM;mrui.focus=0;}
 else if(a==MR_QUEUECANCEL){mrui.confirm=a;mrui.modal=MR_CONFIRM;mrui.focus=0;}
 else if(a==MR_YES)MRUI_Confirm();
 else if(a==MR_NO){mrui.modal=(mrui.confirm==MR_CANCEL||mrui.confirm==MR_QUEUECANCEL)?MR_MAIN:MR_FILES;mrui.focus=0;}
 else if(a==MR_BACK){mrui.modal=MR_MAIN;mrui.focus=0;}
 else if(a==MR_HOSTCHOOSER)MRUI_Close(true);
 else if(a==MR_PREV||a==MR_NEXT){int delta=a==MR_PREV?-1:1;if(mrui.modal==MR_MAIN)mrui.scroll=std::max(0,mrui.scroll+delta);else if(mrui.modal==MR_SUMMARY)mrui.reviewScroll=std::max(0,std::min(std::max(0,int(mrui.review.size())-13),mrui.reviewScroll+delta*8));else mrui.page=std::max(0,mrui.page+delta);}
 else if(a==MR_KEY)MRUI_KeyAction(h.a);
}
static void MRUI_DrawRow(const MRRow& row,float y){
 const float* ink=scuText;bool enabled=true;std::string value;
 if(row.action==MR_RULE){const auto& r=stmatch::rules[row.index];enabled=stmatch::inactive(r,mrui.draft).empty()&&!(mrui.local&&!Q_stricmp(r.cvar,"ui_dedicated"));value=stmatch::label(row.index,mrui.draft.values[row.index]);if(!enabled)ink=scuMuted;
  SCUI_Fit(29,y+6,267,.63f,row.label.c_str(),ink);
  if(*r.choices)MRUI_Button(308,y,289,24,value,MR_RULE,row.index,0,false,enabled);
  else{float fraction=float(mrui.draft.values[row.index]-r.low)/std::max(1,r.high-r.low);UI_FillRect(315,y+11,175,3,scuLine);UI_FillRect(315,y+11,175*fraction,3,enabled?scuCyan:scuMuted);RUI_Control(311+175*fraction,y+6,9,14,"field",false,false);MRUI_Hit(308,y,189,24,MR_SLIDER,row.index);MRUI_Button(505,y,92,24,value,MR_NUMBER,row.index,0,false,enabled);}
 }else if(row.action==MR_BOT){auto* bot=MRUI_Bot(row.index);SCUI_Text(29,y+7,.56f,row.label.c_str(),scuMuted);MRUI_Button(81,y,194,24,bot?bot->model:mrui.local&&!mrui.replaceBots?"No addition / choose bot":"Open / choose bot",MR_BOT,row.index);
  if(bot){MRUI_Button(279,y,132,24,stmatch::roleNames[bot->role],MR_ROLE,row.index);MRUI_Button(415,y,65,24,"Skill "+std::to_string(bot->skill),MR_SKILL,row.index);int t=0;for(int i=0;i<9;++i)if(mrTeamIds[i]==bot->team)t=i;MRUI_Button(484,y,113,24,mrTeamNames[t],MR_TEAM,row.index);}
 }else{
  SCUI_Fit(29,y+6,267,.63f,row.label.c_str(),scuText);
  if(row.action==MR_FORCE){enabled=mrui.draft.get("st_forceModeActive")==2;value=mrui.draft.force[row.index]?"Maximum level "+std::to_string(mrui.draft.force[row.index]):"0 - Disabled";}
  else if(row.action==MR_WEAPON){enabled=mrui.draft.get("st_weaponsActive")==2&&row.index!=2&&row.index!=3;value=(mrui.draft.weaponDisable&(1<<row.index))?"[ ] Disabled":"[X] Available";}
  else if(row.action==MR_VOTE)value=(mrui.draft.get("g_allowVote")&(1<<row.index))?"[X] Allowed":"[ ] Disabled";
  else if(row.action==MR_HOSTNAME)value=mrui.draft.hostname;
  else if(row.action==MR_PASSWORD)value=mrui.password.empty()?"Open server":"********";
  else if(row.action==MR_MAP)value=mrui.draft.map;
  else if(row.action==MR_ROTATION)value=mrui.draft.rotation.empty()?"No rotation / Edit order":"Edit rotation order";
  else if(row.action==MR_REPLACE)value=mrui.replaceBots?"[X] Replace bots only":"[ ] Keep existing bots";
  MRUI_Button(308,y,289,24,value,row.action,row.index,0,false,enabled);
 }
 int hover=mrui.pointer?MRUI_Hover():mrui.focus;if(hover>=0&&hover<int(mrui.hits.size())){const auto& h=mrui.hits[hover];if(h.y==y){mrui.help=row.help;if(row.action==MR_RULE){std::string reason=stmatch::inactive(stmatch::rules[row.index],mrui.draft);if(!reason.empty())mrui.help=reason+" "+mrui.help;}else if(row.action==MR_FORCE&&!enabled)mrui.help="Requires Custom Force rules. "+mrui.help;else if(row.action==MR_WEAPON&&!enabled)mrui.help="Requires Custom weapon rules; Melee and Lightsaber stay available. "+mrui.help;}}
}
static void MRUI_DrawMain(){
 for(int i=0;i<6;++i)MRUI_Button(20+i*100.f,55,98,29,mrTabs[i],MR_TAB,i,0,mrui.tab==i);
 MRUI_BuildRows();mrui.help.clear();for(int i=0;i<9&&mrui.scroll+i<int(mrui.rows.size());++i)MRUI_DrawRow(mrui.rows[mrui.scroll+i],96+i*26.f);
 float n=float(std::max(1,int(mrui.rows.size()))),thumb=234*std::min(1.f,9/n);UI_FillRect(609,96,3,234,scuLine);UI_FillRect(609,96+(234-thumb)*mrui.scroll/std::max(1,int(mrui.rows.size())-9),3,thumb,scuCyan);
 MRUI_Button(559,343,27,21,"^",MR_PREV);MRUI_Button(590,343,27,21,"v",MR_NEXT);
 if(mrui.help.empty())mrui.help="Select a rule for its description. Mouse wheel scrolls; arrows / controller move focus. Left / right adjusts a focused value; Enter edits numbers.";
 MRUI_Wrap(28,348,518,.52f,mrui.help,scuMuted,3);
 if(!mrui.local)MRUI_Button(24,404,126,27,"Map chooser / Back",MR_HOSTCHOOSER);
 else MRUI_Button(24,404,126,27,"Back / discard draft",MR_CANCEL);
 MRUI_Button(156,404,104,27,"Cancel edits",MR_CANCEL);MRUI_Button(266,404,104,27,"Presets",MR_PRESETS);MRUI_Button(376,404,129,27,mrui.local?"Review changes":"Review / Start",MR_REVIEW);
 if(mrui.local)MRUI_Button(511,404,106,27,"Discard queue",MR_QUEUECANCEL);
 else SCUI_Fit(511,410,106,.49f,(std::to_string(mrui.scroll+1)+" / "+std::to_string(mrui.rows.size())).c_str(),scuMuted);
}
static void MRUI_DrawSummary(){
 MRUI_Review();SCUI_Text(27,62,.77f,mrui.local?"Review changes to this local server":"Review before starting the match",scuText);
 MRUI_Wrap(27,88,578,.54f,mrui.local?"Apply now applies live changes and restarts only if needed, or loads a changed selected map. Apply next round/map leaves the current match running and queues changes. Roster commands are held for that apply.":"These are the complete match rules. Starting applies this draft, loads the selected map and adds the chosen bots.",scuGold,3);
 mrui.reviewScroll=std::min(mrui.reviewScroll,std::max(0,int(mrui.review.size())-13));for(int i=0;i<13&&mrui.reviewScroll+i<int(mrui.review.size());++i)SCUI_Fit(29,143+i*17.f,574,.56f,mrui.review[mrui.reviewScroll+i].c_str(),scuText);
 MRUI_Button(24,404,106,27,"Back to draft",MR_BACK);MRUI_Button(139,404,37,27,"^",MR_PREV);MRUI_Button(181,404,37,27,"v",MR_NEXT);
 if(mrui.local){MRUI_Button(226,404,182,27,"Apply next round / map",MR_LATER);MRUI_Button(416,404,201,27,"Apply now (restarts if needed)",MR_NOW);}else MRUI_Button(416,404,201,27,"Start this match",MR_NOW);
}
static void MRUI_DrawFiles(){
 SCUI_Text(27,62,.77f,"Saved match presets",scuText);MRUI_Wrap(27,89,580,.54f,"Complete rules, map, rotation, server name and roster. Passwords are excluded. Loading replaces only this draft; gameplay changes after review.",scuMuted,2);
 MRUI_Button(27,127,402,27,mrui.filename.empty()?"Enter a preset name":mrui.filename,MR_FILENAME);MRUI_Button(438,127,179,27,"Save current draft",MR_SAVE);
 int pages=std::max(1,(int(mrui.files.size())+7)/8);mrui.page=std::min(mrui.page,pages-1);
 for(int i=0;i<8&&mrui.page*8+i<int(mrui.files.size());++i){int id=mrui.page*8+i;MRUI_Button(27,164+i*27.f,590,24,mrui.files[id],MR_FILE,id,0,mrui.filename==mrui.files[id]);}
 if(mrui.files.empty())SCUI_Text(31,179,.64f,"No saved presets.",scuMuted);
 MRUI_Button(24,404,100,27,"Back",MR_BACK);MRUI_Button(132,404,38,27,"<",MR_PREV);MRUI_Button(176,404,38,27,">",MR_NEXT);MRUI_Button(348,404,129,27,"Load selected",MR_LOAD);MRUI_Button(485,404,132,27,"Delete selected",MR_DELETE);
}
static void MRUI_DrawEdit(){
 SCUI_Fit(27,62,586,.76f,mrui.editTitle.c_str(),scuText);RUI_Control(27,94,590,34,"field",false,true);
 std::string visible=mrui.editTarget==MR_PASSWORD?std::string(mrui.edit.size(),'*'):mrui.edit;SCUI_Fit(37,104,570,.69f,visible.c_str(),scuText);
 if((uiInfo.uiDC.realTime/400)&1){float caret=37+RUI_Width(visible.substr(0,mrui.caret).c_str(),.69f);if(caret<607)UI_FillRect(caret,101,1,20,scuCyan);}
 SCUI_Text(28,140,.54f,"Type directly or use the controller keyboard. Enter confirms; Esc cancels this field.",scuMuted);
 const char* rows[]={"1234567890","qwertyuiop","asdfghjkl-","zxcvbnm_./"};
 for(int r=0;r<4;++r)for(int c=0;c<10;++c){char letter=rows[r][c];if(mrui.shift&&letter>='a'&&letter<='z')letter-=32;MRUI_Button(40+c*56.f,171+r*36.f,49,29,std::string(1,letter),MR_KEY,letter);}
 MRUI_Button(40,322,82,28,"Shift",MR_KEY,256,0,mrui.shift);MRUI_Button(129,322,42,28,"<",MR_KEY,259);MRUI_Button(178,322,153,28,"Space",MR_KEY,' ');MRUI_Button(338,322,42,28,">",MR_KEY,260);MRUI_Button(387,322,112,28,"Backspace",MR_KEY,257);MRUI_Button(506,322,94,28,"Clear",MR_KEY,258);
 const char* symbols="!@#$%^&*():?=+,";for(int i=0;symbols[i];++i)MRUI_Button(40+i*40.f,357,34,26,std::string(1,symbols[i]),MR_KEY,symbols[i]);
 MRUI_Button(24,404,126,27,"Cancel field",MR_KEY,261);MRUI_Button(491,404,126,27,"Use this value",MR_KEY,262);
}
static void MRUI_DrawConfirm(){
 std::string title,body;if(mrui.confirm==MR_CANCEL){title="Discard this Match Rules draft?";body="All edits in this draft will be discarded. Existing server settings and any already queued server changes remain as they were.";}
 else if(mrui.confirm==MR_QUEUECANCEL){title="Discard the server's queued changes?";body="Cancel all Match Rules changes waiting for the next round/map. Current active match rules remain in effect.";}
 else if(mrui.confirm==MR_SAVE){title="Save preset: "+mrui.filename+"?";body="Save this complete match configuration and bot roster. An existing preset with this name will be replaced. The host password is excluded.";}
 else if(mrui.confirm==MR_LOAD){title="Load preset: "+mrui.filename+"?";body=mrui.local?"Load the complete rules and roster as a bots-only replacement draft. Applying after review replaces existing bots; human players are never removed. Current gameplay and password remain unchanged until Apply.":"Replace all non-secret rules, map, rotation, name and bot roster in this draft. Current gameplay and password remain unchanged until you review and apply.";}
 else{title="Delete preset: "+mrui.filename+"?";body="Remove this preset from the saved list. This cannot be undone; you can save a new preset under the same name later.";}
 SCUI_Fit(36,130,568,.88f,title.c_str(),scuText);MRUI_Wrap(36,180,568,.67f,body,scuMuted,7);MRUI_Button(36,330,259,35,"Keep / Back",MR_NO);MRUI_Button(315,330,289,35,mrui.confirm==MR_LOAD&&mrui.local?"Load replacement draft":"Confirm",MR_YES);
}
static void MRUI_DrawBots(){
 SCUI_Text(27,62,.77f,("Bot model for slot "+std::to_string(mrui.slot+1)).c_str(),scuText);SCUI_Text(27,91,.54f,"Loaded bot definitions; custom player models appear when they include a bot definition.",scuMuted);
 MRUI_Button(27,120,590,26,"Open connection slot / Remove this bot",MR_BOTCHOICE,-1);
 int pages=std::max(1,(UI_GetNumBots()+15)/16);mrui.page=std::min(mrui.page,pages-1);
 for(int i=0;i<16&&mrui.page*16+i<UI_GetNumBots();++i){int id=mrui.page*16+i;MRUI_Button(27+(i%2)*299.f,159+(i/2)*27.f,291,24,UI_GetBotNameByNumber(id),MR_BOTCHOICE,id);}
 MRUI_Button(24,404,112,27,"Back",MR_BACK);MRUI_Button(438,404,84,27,"Previous",MR_PREV);MRUI_Button(531,404,86,27,"Next",MR_NEXT);
}
static void MRUI_DrawMaps(){
 SCUI_Text(27,62,.77f,"Select installed map",scuText);SCUI_Text(27,91,.54f,"Maps listed for the draft's game type. A custom installed map can be entered directly.",scuMuted);
 std::vector<int> maps;int type=mrui.draft.get("g_gametype");if(type==6)type=0;for(int i=0;i<uiInfo.mapCount;++i)if(uiInfo.mapList[i].mapLoadName&&(uiInfo.mapList[i].typeBits&(1<<type)))maps.push_back(i);
 int pages=std::max(1,(int(maps.size())+15)/16);mrui.page=std::min(mrui.page,pages-1);
 for(int i=0;i<16&&mrui.page*16+i<int(maps.size());++i){int id=maps[mrui.page*16+i];MRUI_Button(27+(i%2)*299.f,124+(i/2)*31.f,291,27,uiInfo.mapList[id].mapName?uiInfo.mapList[id].mapName:uiInfo.mapList[id].mapLoadName,MR_MAPCHOICE,id,0,mrui.draft.map==uiInfo.mapList[id].mapLoadName);}
 MRUI_Button(24,404,100,27,"Back",MR_BACK);MRUI_Button(133,404,212,27,"Enter map name",MR_MAPEDIT);MRUI_Button(438,404,84,27,"Previous",MR_PREV);MRUI_Button(531,404,86,27,"Next",MR_NEXT);
}
static void MRUI_DrawRotation(){
 SCUI_Text(27,62,.77f,"Ordered map rotation",scuText);SCUI_Text(27,91,.54f,"Order is preserved in presets. Enable automatic rotation in Match to use this list.",scuMuted);
 std::istringstream in(mrui.draft.rotation);std::vector<std::string> maps;std::string map;while(in>>map)maps.push_back(map);int pages=std::max(1,(int(maps.size())+8)/9);mrui.page=std::min(mrui.page,pages-1);
 for(int i=0;i<9&&mrui.page*9+i<int(maps.size());++i){int id=mrui.page*9+i;float y=121+i*28.f;MRUI_Button(27,y,369,25,std::to_string(id+1)+". "+maps[id],MR_ROTEDIT,id);MRUI_Button(404,y,43,25,"Up",MR_ROTUP,id);MRUI_Button(453,y,60,25,"Down",MR_ROTDOWN,id);MRUI_Button(519,y,98,25,"Remove",MR_ROTDELETE,id);}
 if(maps.empty())SCUI_Text(31,138,.65f,"Rotation is empty.",scuMuted);
 MRUI_Button(24,404,100,27,"Back",MR_BACK);MRUI_Button(133,404,212,27,"Append a map",MR_ROTADD);MRUI_Button(438,404,84,27,"Previous",MR_PREV);MRUI_Button(531,404,86,27,"Next",MR_NEXT);
}
static void MRUI_Draw(){
 if(!mrui.active)return;if(MRUI_Remote()||!Menu_GetFocused()||mrui.menu!=Menu_GetFocused()->window.name){MRUI_Close(false);return;}
 const vec4_t background={.006f,.021f,.033f,.99f};UI_FillRect(0,0,640,480,background);SMUI_Image("ui/assets/sabertrials/arena.tga",0,0,640,480);const vec4_t shade={.004f,.017f,.027f,.96f};UI_FillRect(0,0,640,480,shade);
 RUI_Image("wordmark",24,18,150,15);SCUI_Text(194,16,.91f,"MATCH RULES",scuText);
 std::string subtitle=mrui.local?"Local host draft":"New match draft";if(mrui.local){int pending=int(trap->Cvar_VariableValue("st_matchPendingCount"));if(pending)subtitle+=" | "+std::to_string(pending)+(trap->Cvar_VariableValue("st_matchPendingApply")?" queued for next round/map":" pending, not armed");if(MRUI_Cvar("st_matchPending_password")=="1")subtitle+=" | password change queued";}
 SCUI_Fit(194,37,419,.47f,subtitle.c_str(),scuMuted);mrui.hits.clear();
 switch(mrui.modal){case MR_SUMMARY:MRUI_DrawSummary();break;case MR_FILES:MRUI_DrawFiles();break;case MR_EDIT:MRUI_DrawEdit();break;case MR_CONFIRM:MRUI_DrawConfirm();break;case MR_BOTS:MRUI_DrawBots();break;case MR_MAPS:MRUI_DrawMaps();break;case MR_ROTATIONS:MRUI_DrawRotation();break;default:MRUI_DrawMain();break;}
 if(!mrui.status.empty())MRUI_Wrap(27,444,586,.51f,mrui.status,scuGold,2);mrui.focus=std::max(0,std::min(mrui.focus,std::max(0,int(mrui.hits.size())-1)));LUI_Frame();
}
static void MRUI_Move(int dx,int dy){
 if(mrui.hits.empty())return;mrui.pointer=false;mrui.focus=std::max(0,std::min(mrui.focus,int(mrui.hits.size())-1));const auto& from=mrui.hits[mrui.focus];int best=-1;float distance=100000;
 for(int i=0;i<int(mrui.hits.size());++i){const auto& to=mrui.hits[i];float x=to.x+to.w*.5f-from.x-from.w*.5f,y=to.y+to.h*.5f-from.y-from.h*.5f;if(dx?(x*dx<=0||fabsf(y)>16):y*dy<=0)continue;float score=dx?fabsf(x)+fabsf(y)*12:fabsf(y)*12+fabsf(x);if(score<distance){distance=score;best=i;}}
 if(best>=0)mrui.focus=best;
}
static bool MRUI_Key(int key,qboolean down){
 if(!mrui.active)return false;
 if(!down){if(key==A_MOUSE1)mrui.drag=-1;return true;}
 if(key>=A_JOY0&&key<=A_JOY31)mrui.pointer=false;
 if(MRUI_Remote()){MRUI_Close(false);return true;}
 if(key&K_CHAR_FLAG){if(mrui.modal==MR_EDIT)MRUI_KeyAction(key&~K_CHAR_FLAG);return true;}
 if(key==A_ESCAPE||key==A_JOY1||key==A_MOUSE2){if(mrui.modal==MR_EDIT){mrui.modal=mrui.editReturn;mrui.status.clear();}else if(mrui.modal!=MR_MAIN){mrui.modal=MR_MAIN;mrui.focus=0;}else{mrui.confirm=MR_CANCEL;mrui.modal=MR_CONFIRM;mrui.focus=0;}return true;}
 if(mrui.modal==MR_EDIT){if(key==A_BACKSPACE||key==A_JOY2){MRUI_KeyAction(257);return true;}else if(key==A_DELETE){mrui.editReplace=false;if(mrui.caret<mrui.edit.size())mrui.edit.erase(mrui.caret,1);return true;}else if(key==A_ENTER){MRUI_CommitEdit();return true;}else if(key==A_HOME){mrui.caret=0;mrui.editReplace=false;return true;}else if(key==A_END){mrui.caret=mrui.edit.size();mrui.editReplace=false;return true;}else if(key==A_CURSOR_LEFT){MRUI_KeyAction(259);return true;}else if(key==A_CURSOR_RIGHT){MRUI_KeyAction(260);return true;}}
 if(key==A_MWHEELUP||key==A_MWHEELDOWN||key==A_JOY9||key==A_JOY10){MRHit h={0,0,0,0,(key==A_MWHEELUP||key==A_JOY9)?MR_PREV:MR_NEXT,0,0};MRUI_Action(h);return true;}
 if(key==A_MOUSE1||key==A_ENTER||key==A_JOY0){int hit=key==A_MOUSE1&&mrui.pointer?MRUI_Hover():mrui.focus;if(hit>=0&&hit<int(mrui.hits.size())){MRHit h=mrui.hits[hit];mrui.focus=hit;if(h.action==MR_SLIDER&&(key!=A_MOUSE1||!mrui.pointer)){h.action=MR_NUMBER;MRUI_Action(h);}else MRUI_Action(h);}return true;}
 if(key==A_TAB){mrui.pointer=false;if(!mrui.hits.empty())mrui.focus=(mrui.focus+1)%int(mrui.hits.size());return true;}
 int dx=(key==A_CURSOR_LEFT||key==A_JOY13)?-1:(key==A_CURSOR_RIGHT||key==A_JOY14)?1:0;int dy=(key==A_CURSOR_UP||key==A_JOY11)?-1:(key==A_CURSOR_DOWN||key==A_JOY12)?1:0;
 if(dx&&mrui.modal!=MR_EDIT&&!mrui.hits.empty()&&mrui.focus<int(mrui.hits.size())){const auto h=mrui.hits[mrui.focus];if(h.action==MR_RULE||h.action==MR_FORCE){mrui.pointer=false;MRUI_Action(h,dx);return true;}if(h.action==MR_SLIDER||h.action==MR_NUMBER){mrui.pointer=false;MRUI_ChangeRule(h.a,dx);return true;}}
 if(dx||dy)MRUI_Move(dx,dy);return true;
}
static bool MRUI_Mouse(){
 if(!mrui.active)return false;mrui.pointer=true;
 if(mrui.drag>=0){const auto& r=stmatch::rules[mrui.drag];float fraction=Com_Clamp(0,1,(uiInfo.uiDC.cursorx-308)/189.f);mrui.draft.values[mrui.drag]=std::max(r.low,std::min(r.high,r.low+int((r.high-r.low)*fraction+.5f)));}
 return true;
}
static bool MRUI_Script(const char* name){
 if(!Q_stricmp(name,"matchRulesHostReset")){if(!MRUI_Server()){mrui.cached=false;mrui.rosterEdited=false;mrui.replaceBots=false;mrui.passwordEdited=false;mrui.password.clear();}return true;}
 if(!Q_stricmp(name,"matchRules")){MRUI_Open();return true;}
 if(!Q_stricmp(name,"matchRulesCancel")){if(mrui.active)MRUI_Close(false);return true;}
 if(!Q_stricmp(name,"StartServer")&&!trap->Cvar_VariableValue("ui_singlePlayerActive")){MRUI_Open(true);return true;}
 return false;
}
