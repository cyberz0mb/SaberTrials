/* Included by g_event.c. Only changed presentation values use reliable commands. */
static void uiText(int recipient,int line,const char*value) {
 int slot;char text[256];Q_strncpyz(text,value,sizeof(text));
 for(slot=0;slot<level.maxclients;slot++)if((recipient<0||slot==recipient)&&level.clients[slot].pers.connected==CON_CONNECTED){
  if(strcmp(sentUI[slot][line],text)){
   Q_strncpyz(sentUI[slot][line],text,sizeof(sentUI[slot][line]));
   trap->SendServerCommand(slot,va("steui %d \"%s\"",line,text));
  }
 }
}

static void publish(int recipient) {
 int i,slot,side,line,connected[2]={0,0},ready[2]={0,0},required=event.teamSize?event.teamSize:1;
 char text[256];const char*hint;
 uiText(recipient,0,va("%s | %s",phaseName(),event.teamSize?va("%dv%d TFFA / %d kills",event.teamSize,event.teamSize,event.teamSize*10):"Individual / 10 rounds"));
 for(side=0;side<2;side++){
  line=1+side*5;
  for(i=0;i<event.memberCount;i++)if(STE_Side(&event,i)==side){
   STEMember*m=&event.members[i];connected[side]+=!!m->profile.connected;ready[side]+=!!m->ready;
   Com_sprintf(text,sizeof(text),"%.27s | %s",m->profile.name,!m->profile.connected?"Disconnected":event.phase==STE_LIVE?"Playing":m->ready?"READY":"Not ready");
   uiText(recipient,line++,text);
  }
  while(line<6+side*5)uiText(recipient,line++,"");
  uiText(recipient,47+side,event.active[side]>=0?va("%.30s",event.entries[event.active[side]].name):side?"Opponent":"Current match");
  uiText(recipient,49+side,event.active[side]>=0?va("%d/%d present | %d/%d ready",connected[side],required,ready[side],required):"Waiting for bracket");
  uiText(recipient,52+side,event.active[side]>=0&&connected[side]<required?
   va("Reconnect: %d:%02d",(int)((event.remaining[side]+999)/1000/60),(int)((event.remaining[side]+999)/1000%60)):"");
 }
 uiText(recipient,46,va("%d / %d %s registered",event.count,event.teamSize?8:32,event.teamSize?"teams":"players"));
 if(event.phase==STE_REGISTRATION)hint=event.teamSize?"2-8 full teams required. The operator locks the bracket.":"An even 8-32 players required. The operator locks the bracket.";
 else if(event.phase==STE_COMPLETE)hint="Tournament complete. View the bracket for results.";
 else if(event.staffPaused)hint="Paused by staff. Wait for staff to resume, then ready again.";
 else if(connected[0]<required||connected[1]<required)hint="Match paused: waiting for reconnect or a registered substitute.";
 else if(event.phase==STE_LIVE)hint="Match in progress. Waiting players can follow the bracket.";
 else hint="Both complete lineups must select Ready. Click again to unready.";
 uiText(recipient,44,hint);
 uiText(recipient,51,event.active[0]<0?"":event.teamSize?
  va("Time played %d:%02d / 10:00%s",(int)(event.playedMs/60000),(int)(event.playedMs/1000%60),event.playedMs>=600000?" | Sudden death":""):
  va("Rounds played %d / 10%s",event.score[0]+event.score[1],event.score[0]+event.score[1]>=10?" | Deciding round":""));
 if(event.active[0]>=0)Com_sprintf(text,sizeof(text),"%d  -  %d",event.score[0],event.score[1]);
 else Q_strncpyz(text,event.phase==STE_COMPLETE?(event.champion>=0?va("Champion: %.40s",event.entries[event.champion].name):"No champion"):
  (event.teamSize?"20 / 30 / 40 / 50 kills by team size":"All 10 rounds; deciding round at 5-5"),sizeof(text));
 uiText(recipient,12,text);
 for(slot=0;slot<level.maxclients;slot++)if((recipient<0||recipient==slot)&&level.clients[slot].pers.connected==CON_CONNECTED){
  STEvent preview;int m=slotMember(slot),join=0,leave=0,canReady=0,count=0,targets[5]={0,0,0,0,0};
  const char*personal;char command[128];
  if(profiles[slot].verified){
   preview=event;join=!ST_StaffBlocked(&g_entities[slot])&&STE_Join(&preview,&profiles[slot]);
   leave=m>=0&&event.phase==STE_REGISTRATION;
   canReady=m>=0&&STE_Side(&event,m)>=0&&event.members[m].profile.connected&&
    (event.phase==STE_READY||event.phase==STE_PAUSED)&&!event.staffPaused&&(event.members[m].ready||arenaReady());
  }
  if(!profiles[slot].verified)personal="Account not verified here. Open Account to sign in or check status.";
  else if(m<0)personal=join?"Verified account: select Join tournament.":event.teamSize&&!profiles[slot].team[0]?
   "A registered team is required for this tournament.":"Registration is unavailable for your account in this event.";
  else if(event.phase==STE_REGISTRATION)personal=event.members[m].starter?"Registered as a starter. Waiting for the bracket.":"Registered as a reserve. Your team has a full starting lineup.";
  else if(STE_Side(&event,m)>=0)personal=event.phase==STE_LIVE?"Your match is live.":canReady?
   "Your match: use Ready / Unready below.":"Your match: waiting for the full lineup or staff resume.";
  else personal=event.members[m].starter?"Registered. Check the bracket for your next match or result.":"Registered reserve. Open Substitutes to replace an absent teammate.";
  uiText(slot,45,personal);uiText(slot,11,m>=0&&event.members[m].ready?"Unready":"Ready");
  if(profiles[slot].verified&&m>=0&&!event.members[m].starter&&event.teamSize&&!ST_StaffBlocked(&g_entities[slot])&&
   (event.phase==STE_READY||event.phase==STE_PAUSED)){
   for(i=0;i<event.memberCount&&count<5;i++)if(STE_Side(&event,i)>=0&&!event.members[i].profile.connected&&event.members[i].entry==event.members[m].entry){
    targets[count]=i+1;uiText(slot,56+count,va("Replace %.36s",event.members[i].profile.name));count++;
   }
  }
  for(i=count;i<5;i++)uiText(slot,56+i,"");
  uiText(slot,54,count?"Choose an absent teammate. The full lineup must ready again.":"No replacement available. Only reserves can replace absent teammates.");
  Com_sprintf(command,sizeof(command),"steactions 1 %d %d %d %d %d %d %d %d %d %d",join,leave,canReady,!!profiles[slot].verified,targets[0],targets[1],targets[2],targets[3],targets[4],event.bracketSize?event.bracketSize-1:0);
  if(strcmp(command,sentActions[slot])){Q_strncpyz(sentActions[slot],command,sizeof(sentActions[slot]));trap->SendServerCommand(slot,command);}
 }
}

static void feedback(int slot,const char*text) {
 say(slot,text);uiText(slot,55,text);
}
