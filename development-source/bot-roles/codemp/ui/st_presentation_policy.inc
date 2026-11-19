/* Saber Trials presentation-only data. GPL-2.0-only. No account authority. */
#ifndef ST_PRESENTATION_POLICY
#define ST_PRESENTATION_POLICY
#include <string.h>
#include <stdio.h>
#define STP_MAX_ROWS 64
#define STP_PAGE_ROWS 14
typedef struct {
 int id,team,score,ping,minutes,icon,ready,bot,kills,deaths,wins,losses,flag,assists,hasTffaKd;
 char name[96];
} STPRow;
typedef struct {
 STPRow rows[STP_MAX_ROWS];
 int count,local,teams,mode,page,red,blue,result;
 char title[128],subtitle[160],outcome[160],event[192];
} STPBoard;
typedef struct {char text[192];int kind,started,active;} STPNotice;
static void STP_FormatRatio(char *out,size_t size,int kills,int deaths) {
 if(deaths>0)snprintf(out,size,"%.2f",(double)kills/deaths);
 else snprintf(out,size,"--");
}
static int STP_Order(const STPBoard*b,int*out) {
 int n=0,team,i,limit=b->count;
 if(limit<0)limit=0;if(limit>STP_MAX_ROWS)limit=STP_MAX_ROWS;
 for(team=0;team<4;team++)for(i=0;i<limit;i++)if(b->rows[i].team==team)out[n++]=i;
 return n;
}
static int STP_PageCount(int count){return count>0?(count+STP_PAGE_ROWS-1)/STP_PAGE_ROWS:1;}
static int STP_NormalizePage(int page,int pages){return pages>0?((page%pages)+pages)%pages:0;}
/* -1 is tied; -2 means no active participant. Never treats a spectator as winner. */
static int STP_Winner(const STPBoard*b) {
 int i,winner=-2,best=0,tie=0;
 for(i=0;i<b->count&&i<STP_MAX_ROWS;i++)if(b->rows[i].team!=3){
  if(winner==-2||b->rows[i].score>best){best=b->rows[i].score;winner=i;tie=0;}
  else if(b->rows[i].score==best)tie=1;
 }
 return tie?-1:winner;
}
static const char*STP_Mode(int mode,int tournament,int verifiedRanked) {
 if(tournament)return "Tournament";
 if(verifiedRanked&&mode==3)return "Ranked Duel";
 if(verifiedRanked&&mode==6)return "Ranked TFFA";
 switch(mode){case 0:return "FFA";case 1:return "Holocron";case 2:return "Jedi Master";
 case 3:return "Duel";case 4:return "Power Duel";case 6:return "TFFA";case 7:return "Siege";
 case 8:return "CTF";case 9:return "CTY";default:return "Custom";}
}
static int STP_NoticePush(STPNotice*n,const char*text,int kind,int now) {
 if(!text||!*text)return 0;
 if(n->active&&!strcmp(n->text,text)&&n->kind==kind&&now>=n->started&&now-n->started<5000)return 0;
 strncpy(n->text,text,sizeof(n->text)-1);n->text[sizeof(n->text)-1]=0;
 n->kind=kind;n->started=now;n->active=1;return 1;
}
static float STP_NoticeAlpha(const STPNotice*n,int now) {
 int age=now-n->started;
 if(!n->active||age<0||age>=5000)return 0;
 return age<150?age/150.0f:age>4500?(5000-age)/500.0f:1.0f;
}
#endif
