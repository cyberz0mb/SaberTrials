/* Test-build fixtures. This file is never compiled into production. */
static char stpFixture[32];
static int stpFixtureSelection;
void ST_UISetPresentationFixture(const char*name) {
 Q_strncpyz(stpFixture,name,sizeof(stpFixture));
 trap->Print("PRESENTATION_QA fixture=%s\n",stpFixture);
}
static int ST_UIFixtureBrowser(void){return !strcmp(stpFixture,"browser");}
static const char*ST_UIFixtureServerText(int index,int column) {
 static char text[128];
 switch(column){case 0:Com_sprintf(text,sizeof(text),"%s %d",index?"Community arena":"Saber Trials practice",index+1);break;
 case 1:Q_strncpyz(text,index%2?"mp/duel3":"mp/ffa3",sizeof(text));break;
 case 2:Com_sprintf(text,sizeof(text),"%d / 32",index+2);break;
 case 3:Q_strncpyz(text,index%2?"Duel":"FFA",sizeof(text));break;
 default:Com_sprintf(text,sizeof(text),"%d",32+index*15);}
 return text;
}
static int ST_UIPresentationQA(menuDef_t*menu) {
 STPBoard b;int i;char info[1024];
 if(!stpFixture[0]||!strcmp(stpFixture,"none"))return 0;
 if(ST_UIFixtureBrowser()){
  Com_sprintf(info,sizeof(info),"\\hostname\\Saber Trials practice\\mapname\\mp/ffa3\\clients\\%d\\sv_maxclients\\32\\gametype\\0\\ping\\%d\\game\\SaberTrials\\needpass\\0\\wdisable\\0\\fdisable\\0",stpFixtureSelection+2,32+stpFixtureSelection*15);
  ST_UIBrowserPanel(info);return 1;
 }
 if(!strcmp(stpFixture,"notice")){
  if(!stpNotice.active)STP_NoticePush(&stpNotice,"Settings saved.",0,uiInfo.uiDC.realTime);
  STP_DrawNoticeAt(&stpUIPainter,&stpNotice,uiInfo.uiDC.realTime,210,427,402);return 1;
 }
 memset(&b,0,sizeof(b));b.local=2;b.count=!strcmp(stpFixture,"crowded")?32:12;
 b.teams=!strcmp(stpFixture,"teams");b.mode=b.teams?6:0;b.red=35;b.blue=27;
 b.result=!strcmp(stpFixture,"results");b.page=!strcmp(stpFixture,"crowded")?2:0;
 Q_strncpyz(b.title,b.result?"MATCH RESULTS":"SABER TRIALS / SCOREBOARD",sizeof(b.title));
 Q_strncpyz(b.subtitle,b.teams?"TFFA / Visual fixture":"FFA / Visual fixture",sizeof(b.subtitle));
 Q_strncpyz(b.outcome,"Winner: Mira / 24 points",sizeof(b.outcome));
 for(i=0;i<b.count;i++){
  STPRow*r=&b.rows[i];r->id=i;r->team=b.teams?i<5?1:i<10?2:3:i<10||b.count>12?0:3;
  r->score=24-i;r->kills=24-i;r->deaths=i;r->wins=3;r->losses=1;r->ping=30+i*15;r->minutes=8;
  Com_sprintf(r->name,sizeof(r->name),"%s",i==0?"Mira":i==1?"A very long player name with colors":i==2?"You / SamplePlayer":va("Duelist %02d",i+1));
  r->icon=trap->R_RegisterShaderNoMip(i%2?"models/players/jan/icon_default":"models/players/kyle/icon_default");
 }
 STP_UIFill(0,0,640,480,stpInk);STP_DrawBoard(&stpUIPainter,&b);return 1;
}
