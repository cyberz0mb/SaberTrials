/* Read-only live roster publication; included in the C++ server adapter. */
static std::string ST_MatchDefinition(const char *userinfo) {
 std::string saved=Info_ValueForKey(userinfo,"st_matchDefinition");
 if(!saved.empty()&&G_GetBotInfoByName(saved.c_str()))return saved;
 std::string display=Info_ValueForKey(userinfo,"name");
 char *direct=G_GetBotInfoByName(display.c_str());
 if(direct)return Info_ValueForKey(direct,"name");
 std::string model=Info_ValueForKey(userinfo,"model"),personality=Info_ValueForKey(userinfo,"personality");
 std::string candidate;int matches=0;
 for(int i=0;i<level.bots.num;++i){char *info=G_GetBotInfoByNumber(i);if(!info)continue;
  std::string definitionModel=Info_ValueForKey(info,"model"),definitionPersonality=Info_ValueForKey(info,"personality");
  if(Q_stricmp(model.c_str(),definitionModel.c_str())||(!personality.empty()&&!definitionPersonality.empty()&&Q_stricmp(personality.c_str(),definitionPersonality.c_str())))continue;
  std::string name=Info_ValueForKey(info,"name"),fun=Info_ValueForKey(info,"funname");
  if(!Q_stricmp(display.c_str(),name.c_str())||(!fun.empty()&&!Q_stricmp(display.c_str(),fun.c_str())))return name;
  candidate=name;++matches;
 }
 return matches==1?candidate:"";
}
void ST_MatchLiveInit(void) {
 const char *fields[]={"present","model","skill","team","role","unresolved"};
 for(int client=0;client<MAX_CLIENTS;++client){
  for(int field=0;field<6;++field)trap->Cvar_Register(NULL,va("st_matchLive_bot%d_%s",client,fields[field]),"",CVAR_ROM);
  trap->Cvar_Register(NULL,va("st_matchLiveBot%d",client),"",CVAR_ROM);
 }
 trap->Cvar_Register(NULL,"st_matchLiveBotCount","0",CVAR_ROM);
 trap->Cvar_Register(NULL,"st_matchLiveBotUnresolved","0",CVAR_ROM);
 trap->Cvar_Register(NULL,"st_matchLiveReady","0",CVAR_ROM);
 trap->Cvar_Set("st_matchLiveReady","0");
}
void ST_MatchPublishLiveBots(void) {
 int count=0,unresolved=0;
 for(int client=0;client<MAX_CLIENTS;++client){
  bool present=client<level.maxclients&&level.clients[client].pers.connected!=CON_DISCONNECTED&&(g_entities[client].r.svFlags&SVF_BOT);
  std::string definition;int skill=4,team=0,role=0;
  if(present){char userinfo[MAX_INFO_STRING];trap->GetUserinfo(client,userinfo,sizeof(userinfo));definition=ST_MatchDefinition(userinfo);
   if(!stmatch::safeText(definition,64))definition.clear();
   skill=Com_Clampi(1,5,atoi(Info_ValueForKey(userinfo,"skill")));
   int actualTeam=level.clients[client].sess.sessionTeam;
   if((level.gametype==GT_TEAM||level.gametype==GT_CTF||level.gametype==GT_SIEGE)&&actualTeam!=TEAM_SPECTATOR)team=actualTeam;
   for(int value=1;value<8;++value)if(ST_BotParseRole(stmatch::roleTokens[value])==level.clients[client].pers.stBotRole){role=value;break;}
   if(!stmatch::roleAllowed(level.gametype,role))role=0;
   if(definition.empty())++unresolved;
   trap->Cvar_Set(va("st_matchLiveBot%d",count),va("%d %d %d %d %s",client,team,skill,role,stmatch::hex(definition).c_str()));++count;
  }
  trap->Cvar_Set(va("st_matchLive_bot%d_present",client),present?"1":"");
  trap->Cvar_Set(va("st_matchLive_bot%d_model",client),definition.c_str());
  trap->Cvar_Set(va("st_matchLive_bot%d_skill",client),present?va("%d",skill):"");
  trap->Cvar_Set(va("st_matchLive_bot%d_team",client),present?va("%d",team):"");
  trap->Cvar_Set(va("st_matchLive_bot%d_role",client),present?va("%d",role):"");
  trap->Cvar_Set(va("st_matchLive_bot%d_unresolved",client),present&&definition.empty()?"1":"");
 }
 for(int i=count;i<MAX_CLIENTS;++i)trap->Cvar_Set(va("st_matchLiveBot%d",i),"");
 trap->Cvar_Set("st_matchLiveBotCount",va("%d",count));trap->Cvar_Set("st_matchLiveBotUnresolved",va("%d",unresolved));trap->Cvar_Set("st_matchLiveReady","1");
}
