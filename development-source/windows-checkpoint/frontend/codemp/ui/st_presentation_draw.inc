/* Shared production renderer; UI fixtures exercise these exact drawing paths. */
#include "st_presentation_policy.inc"
typedef struct {
 void (*fill)(float,float,float,float,const float*);
 void (*text)(float,float,float,float,const char*,const float*,int);
 void (*icon)(float,float,float,int,const float*);
 void (*art)(float,float,float,float,const char*,const float*);
} STPPainter;
static const float stpInk[4]={.035f,.065f,.085f,.96f};
static const float stpText[4]={.81f,.9f,.95f,1};
static const float stpMuted[4]={.55f,.68f,.76f,1};
static const float stpCyan[4]={.25f,.79f,1,1};
static const float stpRed[4]={1,.43f,.43f,1};
static const float stpGold[4]={1,.77f,.39f,1};
static void STP_Box(const STPPainter*p,float x,float y,float w,float h,const float*c) {
 p->fill(x,y,w,h,c);
 p->fill(x,y,w,.5f,stpMuted);
}
static void STP_DrawRow(const STPPainter*p,const STPBoard*b,int index,float y) {
 const STPRow*r=&b->rows[index];char value[80];float own[4]={.035f,.23f,.34f,.90f};
 const float*accent=r->team==1?stpRed:r->team==2?stpCyan:stpMuted;
 int you=r->id==b->local;
 if(you){p->fill(40,y-2,560,19,own);p->fill(43,y-2,554,.45f,stpCyan);}
 else if(index%2==0){float stripe[4]={.15f,.22f,.26f,.19f};p->fill(40,y-2,560,20,stripe);}
 p->fill(42,y,2,16,you&&r->team==0?stpCyan:accent);
 if(r->icon)p->icon(50,y,16,r->icon,stpText);
 else p->text(50,y,16,.55f,"?",stpMuted,0);
 p->text(74,y,200,.69f,r->name,stpText,0);
 /* Local position and readiness are independent of global rank. */
 p->text(278,y,55,.58f,r->ready?"READY":r->flag==1?"RED FLAG":r->flag==2?"BLUE FLAG":r->flag==3?"FLAG":you?"YOU":r->team==3?"SPEC":r->team==1?"RED":r->team==2?"BLUE":"",accent,0);
 if(b->mode==6){
  int hasKd=r->hasTffaKd && r->team!=3 && r->ping>=0;
  snprintf(value,sizeof(value),"%d / %d",r->kills,r->deaths);
  p->text(334,y,56,.66f,hasKd?value:"--",stpText,1);
  STP_FormatRatio(value,sizeof(value),r->kills,r->deaths);
  p->text(400,y,56,.63f,hasKd?value:"--",stpText,1);
  snprintf(value,sizeof(value),"%d",r->assists);
  p->text(466,y,56,.63f,r->team==3?"--":value,stpText,1);
 }else if(b->mode==0){
  snprintf(value,sizeof(value),"%d / %d",r->kills,r->deaths);
  p->text(334,y,38,.63f,r->team==3?"--":value,stpText,1);
  snprintf(value,sizeof(value),"%d / %d",r->wins,r->losses);
  p->text(380,y,56,.63f,r->team==3?"--":value,stpMuted,1);
  STP_FormatRatio(value,sizeof(value),r->kills,r->deaths);
  p->text(444,y,56,.63f,r->team==3?"--":value,stpText,1);
 }else{
  snprintf(value,sizeof(value),"%d",r->score);
  p->text(334,y,38,.66f,r->team==3?"--":value,stpText,1);
  snprintf(value,sizeof(value),"%d / %d",r->kills,r->deaths);
  p->text(380,y,56,.63f,r->team==3||b->mode!=0?"--":value,stpMuted,1);
  snprintf(value,sizeof(value),"%d / %d",r->wins,r->losses);
  p->text(444,y,56,.63f,r->team==3?"--":value,stpMuted,1);
 }
 snprintf(value,sizeof(value),"%d",r->ping);
 p->text(b->mode==6?535:510,y,b->mode==6?55:43,.63f,r->bot?"BOT":r->ping<0?"JOIN":value,r->ping>150?stpGold:stpText,1);
 if(b->mode!=6){
  snprintf(value,sizeof(value),"%dm",r->minutes);
  p->text(560,y,30,.60f,value,stpMuted,1);
 }
}
static void STP_DrawBoard(const STPPainter*p,const STPBoard*b) {
 int order[STP_MAX_ROWS],n=STP_Order(b,order),pages=STP_PageCount(n);
 int page=STP_NormalizePage(b->page,pages),i,start=page*STP_PAGE_ROWS,end=start+STP_PAGE_ROWS,local=-1,shown=0;
 float y=132;char text[192];
 if(end>n)end=n;
 if(p->art){
  const float panel[4]={.022f,.052f,.073f,.96f};
  p->fill(35,31,570,418,panel);
  p->art(32,28,576,424,"ui/assets/sabertrials/rollout/frame",stpText);
  p->art(48,43,136,14,"ui/assets/sabertrials/rich/wordmark",stpText);
  p->fill(195,42,.6f,16,stpGold);
  p->text(206,41,170,.83f,b->title,stpText,0);
  p->fill(48,82,544,.45f,stpGold);
 }else{
  STP_Box(p,32,28,576,424,stpInk);
  p->text(48,40,380,.94f,b->title,stpCyan,0);
 }
 p->text(48,65,544,.62f,b->subtitle,stpMuted,0);
 if(b->teams){snprintf(text,sizeof(text),"RED %d     /     BLUE %d",b->red,b->blue);p->text(388,43,204,.65f,text,stpText,1);}
 p->text(48,88,544,.76f,b->result?b->outcome:"GLOBAL RANK: unavailable",b->result?stpGold:stpMuted,0);
 p->fill(48,112,544,.5f,stpCyan);
 p->text(74,115,200,.53f,"PLAYER",stpMuted,0);
 if(b->mode==6){
  p->text(334,115,56,.53f,"K/D",stpMuted,1);
  p->text(400,115,56,.53f,"RATIO",stpMuted,1);
  p->text(466,115,56,.53f,"ASSISTS",stpMuted,1);
  p->text(535,115,55,.53f,"PING",stpMuted,1);
 }else{
  p->text(334,115,38,.53f,b->mode==0?"K/D":"SCORE",stpMuted,1);
  p->text(380,115,56,.53f,b->mode==0?"DUEL W/L":"FFA K/D",stpMuted,1);
  p->text(444,115,56,.53f,b->mode==0?"RATIO":"DUEL W/L",stpMuted,1);
  p->text(510,115,43,.53f,"PING",stpMuted,1);
  p->text(560,115,30,.53f,"TIME",stpMuted,1);
 }
 for(i=0;i<n;i++)if(b->rows[order[i]].id==b->local)local=order[i];
 for(i=start;i<end;i++,y+=19){
  if(i>start&&b->rows[order[i-1]].team!=b->rows[order[i]].team)p->fill(48,y-3,544,.5f,stpMuted);
  STP_DrawRow(p,b,order[i],y);if(order[i]==local)shown=1;
 }
 if(!n)p->text(48,160,544,.75f,"Waiting for the server's player list...",stpMuted,0);
 if(!shown&&local>=0){p->fill(48,402,544,.5f,stpMuted);STP_DrawRow(p,b,local,405);}
 if(p->art)p->fill(48,425,544,.45f,stpGold);
 if(b->event[0])p->text(48,429,420,.57f,b->event,stpCyan,0);
 else p->text(48,429,420,.57f,b->result?"Rating change: unavailable. No verified ranked result received.":pages>1?"Pages rotate every 10s. Your row stays visible.":"Match scores are separate from global rank.",stpMuted,0);
 snprintf(text,sizeof(text),"%d / %d",page+1,pages);p->text(535,429,57,.6f,text,stpCyan,1);
}
static void STP_DrawNoticeAt(const STPPainter*p,const STPNotice*n,int now,float x,float y,float width) {
 float a=STP_NoticeAlpha(n,now),bg[4]={.025f,.055f,.075f,.96f},fg[4];
 const float*c=n->kind==2?stpRed:n->kind==1?stpGold:stpCyan;
 if(a<=0)return;
 memcpy(fg,c,sizeof(fg));fg[3]=a;bg[3]*=a;
 p->fill(x,y,width,30,bg);p->fill(x,y,2,30,fg);
 p->text(x+11,y+6,20,.73f,n->kind==2?"!":n->kind==1?"i":"+",fg,0);
 p->text(x+35,y+7,width-48,.65f,n->text,fg,0);
}
