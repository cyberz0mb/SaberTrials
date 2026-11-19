/* Presentation adapter: consumes snapshots; never changes match or rank data. */
#include "ui/st_presentation_draw.inc"
#include "ui/st_presentation_notices.inc"
static float stpFade=1;
static int stpPageOffset,stpOpened,stpVisible;
static void STP_CGFill(float x,float y,float w,float h,const float*c) {
 vec4_t color;memcpy(color,c,sizeof(color));color[3]*=stpFade;CG_FillRect(x,y,w,h,color);
}
static void STP_CGText(float x,float y,float width,float scale,const char*text,const float*c,int right) {
 vec4_t color;float w;memcpy(color,c,sizeof(color));color[3]*=stpFade;
 w=CG_Text_Width(text,scale,FONT_SMALL2);
 if(w>width&&w>0){scale*=width/w;w=width;}
 CG_Text_Paint(right?x+width-w:x,y,scale,color,text,0,0,ITEM_TEXTSTYLE_NORMAL,FONT_SMALL2);
}
static void STP_CGIcon(float x,float y,float size,int icon,const float*c) {
 vec4_t color;float w=size*cgs.screenYScale/cgs.screenXScale;
 memcpy(color,c,sizeof(color));color[3]*=stpFade;trap->R_SetColor(color);
 CG_DrawPic(x+(size-w)/2,y,w,size,icon);trap->R_SetColor(NULL);
}
static void STP_CGArt(float x,float y,float w,float h,const char*path,const float*c) {
 qhandle_t shader=trap->R_RegisterShaderNoMip(path);
 if(!shader)return;
 vec4_t color;memcpy(color,c,sizeof(color));color[3]*=stpFade;
 trap->R_SetColor(color);CG_DrawPic(x,y,w,h,shader);trap->R_SetColor(NULL);
}
static const STPPainter stpPainter={STP_CGFill,STP_CGText,STP_CGIcon,STP_CGArt};
void ST_ScorePage_f(void) {
 const char*arg=CG_Argv(1);
 if(!strcmp(arg,"prev"))stpPageOffset--;
 else stpPageOffset++;
 stpOpened=cg.time;
}
static void STP_CGBoard(STPBoard*b) {
 int i,winner;char event[256];memset(b,0,sizeof(*b));
 b->local=cg.clientNum;b->mode=cgs.gametype;b->teams=cgs.gametype>=GT_TEAM;
 b->red=cg.teamScores[0];b->blue=cg.teamScores[1];
 b->result=cg.predictedPlayerState.pm_type==PM_INTERMISSION;
 trap->Cvar_VariableStringBuffer("ui_ste0",event,sizeof(event));
 Q_strncpyz(b->title,b->result?"MATCH RESULTS":"SCOREBOARD",sizeof(b->title));
 Com_sprintf(b->subtitle,sizeof(b->subtitle),"%s  /  %s",STP_Mode(b->mode,event[0]!=0,0),b->result?"Final server scores":"Live server scores");
 for(i=0;i<cg.numScores&&i<MAX_CLIENTS&&b->count<STP_MAX_ROWS;i++){
  score_t*s=&cg.scores[i];clientInfo_t*ci;STPRow*r;
  if(s->client<0||s->client>=cgs.maxclients||s->client>=MAX_CLIENTS)continue;
  ci=&cgs.clientinfo[s->client];if(!ci->infoValid)continue;
  r=&b->rows[b->count++];r->id=s->client;r->team=ci->team;r->score=s->score;
  r->ping=s->ping;r->minutes=s->time;r->icon=ci->modelIcon;r->bot=ci->botSkill!=-1;
  r->kills=s->stMatchKills;r->deaths=s->stMatchDeaths;
  r->hasTffaKd=(s->scoreFlags&ST_SCORE_TFFA_KD)!=0;
  r->assists=s->assistCount;
  r->wins=b->mode==GT_DUEL||b->mode==GT_POWERDUEL?ci->wins:s->stPrivateDuelWins;
  r->losses=b->mode==GT_DUEL||b->mode==GT_POWERDUEL?ci->losses:s->stPrivateDuelLosses;
  r->ready=b->result&&s->client<32&&((unsigned int)cg.snap->ps.stats[STAT_CLIENTS_READY]&(1u<<s->client));
  r->flag=(ci->powerups&(1<<PW_REDFLAG))?1:(ci->powerups&(1<<PW_BLUEFLAG))?2:(ci->powerups&(1<<PW_NEUTRALFLAG))?3:0;
  Q_strncpyz(r->name,st_streamerMode.integer&&!st_streamerPlayerNames.integer?va("Player %d",s->client+1):ci->name,sizeof(r->name));
 }
 if(b->result){
  if((b->mode==GT_DUEL||b->mode==GT_POWERDUEL)&&cgs.duelWinner>=0&&cgs.duelWinner<cgs.maxclients&&cgs.duelWinner<MAX_CLIENTS){
   Com_sprintf(b->outcome,sizeof(b->outcome),"Winner: %s",st_streamerMode.integer&&!st_streamerPlayerNames.integer?va("Player %d",cgs.duelWinner+1):cgs.clientinfo[cgs.duelWinner].name);
  }else if(b->mode==GT_POWERDUEL||b->mode==GT_DUEL){Q_strncpyz(b->outcome,"Round complete / awaiting winner",sizeof(b->outcome));}
  else if(b->mode==GT_SIEGE){Q_strncpyz(b->outcome,cg_siegeWinTeam==1?"Red team wins":cg_siegeWinTeam==2?"Blue team wins":"Match complete",sizeof(b->outcome));}
  else if(b->teams){Com_sprintf(b->outcome,sizeof(b->outcome),"%s  /  %d - %d",b->red==b->blue?"Draw":b->red>b->blue?"Red team wins":"Blue team wins",b->red,b->blue);}
  else{winner=STP_Winner(b);if(winner>=0)Com_sprintf(b->outcome,sizeof(b->outcome),"Winner: %s  /  %d points",b->rows[winner].name,b->rows[winner].score);
   else Q_strncpyz(b->outcome,winner==-1?"Draw / tied final scores":"Match complete / no active scores",sizeof(b->outcome));}
 }
 if(event[0]){
  char progress[256];trap->Cvar_VariableStringBuffer("ui_ste44",progress,sizeof(progress));
  Q_strncpyz(b->event,progress[0]?progress:event,sizeof(b->event));
 }
 b->page=stpPageOffset+(cg.time-stpOpened)/10000;
}
static void ST_DrawPresentationBoard(float fade) {
 STPBoard b;if(!stpVisible){stpOpened=cg.time;stpPageOffset=0;}stpVisible=1;
 stpFade=fade;STP_CGBoard(&b);STP_DrawBoard(&stpPainter,&b);stpFade=1;
}
void ST_CGNotifications(void) {
 STP_ObserveNotices(trap->Cvar_VariableStringBuffer,cg.time);
 if(st_notifications.integer&&!(trap->Key_GetCatcher()&KEYCATCH_UI))STP_DrawNoticeAt(&stpPainter,&stpNotice,cg.time,166,22,308);
}
