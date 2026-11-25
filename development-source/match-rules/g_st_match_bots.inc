/* Validated Match Rules bot adapter; included after G_AddBot. GPL-2.0. */
void ST_MatchSpawnBot(const char *name,int skill,int team,int role,int slot) {
 int actualRole;
 const char *teamName;
 if(!ST_MatchBotValid(name,skill,team,role,slot)){
  trap->Print("Match Rules: bot definition or mode-specific roster data is no longer valid.\n");return;}
 if(!trap->Cvar_VariableIntegerValue("bot_enable")){trap->Print("Match Rules: bots are disabled.\n");return;}
 if((level.gametype==GT_TEAM||level.gametype==GT_CTF)&&team==0)team=PickTeam(-1);
 if(team==TEAM_SPECTATOR||!ST_MatchHasRoom(team,-1)||
  (level.gametype==GT_TEAM&&level.stTeamsLocked)){
  trap->Print("Match Rules: team is full or locked; bot was not added.\n");return;}
 // The shared UI role order deliberately does not depend on the engine enum.
 actualRole=ST_BotParseRole(ST_MatchRoleToken(role));
 teamName=team==0?"":ST_TffaName(team);
 G_AddBot(name,(float)skill,teamName,0,(char *)"",actualRole,qtrue);
}
