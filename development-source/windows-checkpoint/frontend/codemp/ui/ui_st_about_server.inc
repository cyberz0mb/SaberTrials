/* Server-reported information for the in-game About menu. */
static void LUI_AboutRow(float x, float y, const char* label, const char* value){
 SCUI_Fit(x,y,94,.57f,label,scuMuted);
 SCUI_Fit(x+99,y,160,.64f,value&&*value?value:"Not reported",ruWhite);
}

static void LUI_AboutServer(const rectDef_t& r){
 char info[MAX_INFO_STRING]={0};
 uiClientState_t state;
 trap->GetClientState(&state);
 trap->GetConfigString(CS_SERVERINFO,info,sizeof(info));
 const auto serverValue=[&](const char* key){return Info_ValueForKey(info,key);};
 const float left=r.x+22,right=r.x+292,top=r.y+60,step=29;
 const char* mode=serverValue("g_gametype");
 const int gt=mode[0]?atoi(mode):-1;
 char value[128];

 SCUI_Fit(left,r.y+17,r.w-44,.88f,"SERVER INFORMATION",ruCyan);
 RUI_Divider(left,r.y+44,r.w-44);
 LUI_AboutRow(left,top,"Host name",serverValue("sv_hostname"));
 LUI_AboutRow(left,top+step,"Address",state.servername);
 LUI_AboutRow(left,top+step*2,"Map",serverValue("mapname"));
 LUI_AboutRow(left,top+step*3,"Game type",gt==GT_FFA?"Free For All":gt==GT_TEAM?"Team Free For All":gt>=0?STP_Mode(gt,0,0):"");
 LUI_AboutRow(left,top+step*4,"Max players",serverValue("sv_maxclients"));
 LUI_AboutRow(left,top+step*5,"Min players",serverValue("bot_minplayers"));

 const char* fps=serverValue("sv_fps");
 if(atoi(fps)>0)Com_sprintf(value,sizeof(value),"%d FPS",atoi(fps));else value[0]=0;
 LUI_AboutRow(right,top,"Server FPS",value);
 const char* rate=serverValue("sv_maxRate");
 if(atoi(rate)>0)Com_sprintf(value,sizeof(value),"%d B/s max",atoi(rate));
 else Q_strncpyz(value,!strcmp(rate,"0")?"Unlimited":"",sizeof(value));
 LUI_AboutRow(right,top+step,"Rate",value);
 const char* location=serverValue("sv_location");
 LUI_AboutRow(right,top+step*2,"Server location",*location?location:!Q_stricmp(state.servername,"localhost")?"Local server":"Not reported");
 LUI_AboutRow(right,top+step*3,"Time limit",serverValue("timelimit"));
 if(gt==GT_DUEL||gt==GT_POWERDUEL)LUI_AboutRow(right,top+step*4,"Duel limit",serverValue("duel_fraglimit"));
 else if(gt==GT_CTF||gt==GT_CTY)LUI_AboutRow(right,top+step*4,"Capture limit",serverValue("capturelimit"));
 else if(gt>=0&&gt!=GT_SIEGE)LUI_AboutRow(right,top+step*4,"Frag limit",serverValue("fraglimit"));

 SCUI_Fit(left,r.y+242,90,.53f,"Version",scuMuted);
 SCUI_Fit(left+99,r.y+242,r.w-143,.56f,serverValue("version"),ruWhite);
 RUI_Divider(left,r.y+267,r.w-44);
}
