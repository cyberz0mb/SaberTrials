#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#undef assert
#define assert(test) do { if (!(test)) { fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#test); exit(1); } } while (0)
#include "st_presentation_policy.inc"
#include "st_presentation_notices.inc"
#include "st_presentation_draw.inc"
static int assistHeaders, assistValues, kdHeaders, ratioHeaders, scoreHeaders, timeHeaders;
static int kdValues, ratioValues;
static int ffaColumn, ffaRowColumn;
static int checkFfa;
static const char *ffaHeaders[]={"SCORE","K/D","W/L","RATIO","PING","TIME"};
static const char *ffaValues[]={"-2","5 / 2","7 / 1","2.50","42","3m"};
static float ffaHeaderX[6];
static void drawFill(float x,float y,float w,float h,const float *color) {
 (void)x;(void)y;(void)w;(void)h;(void)color;
}
static void drawText(float x,float y,float width,float scale,const char *text,const float *color,int right) {
 (void)x;(void)y;(void)width;(void)scale;(void)color;(void)right;
 if(!strcmp(text,"ASSISTS"))assistHeaders++;
 if(!strcmp(text,"K/D"))kdHeaders++;
 if(!strcmp(text,"RATIO"))ratioHeaders++;
 if(!strcmp(text,"SCORE"))scoreHeaders++;
 if(!strcmp(text,"TIME"))timeHeaders++;
 if(y>115 && !strcmp(text,"3"))assistValues++;
 if(y>115 && !strcmp(text,"5 / 2"))kdValues++;
 if(y>115 && !strcmp(text,"2.50"))ratioValues++;
 if(checkFfa&&x>300&&y==115){
  assert(ffaColumn<6&&!strcmp(text,ffaHeaders[ffaColumn]));
  assert(ffaColumn==0||x>ffaHeaderX[ffaColumn-1]);
  ffaHeaderX[ffaColumn++]=x;
 }
 if(checkFfa&&x>300&&y==132){
  assert(ffaRowColumn<6&&!strcmp(text,ffaValues[ffaRowColumn]));
  assert(x==ffaHeaderX[ffaRowColumn++]);
 }
}
static const char *accountStatus="",*signedIn="0";
static void readNoticeCvar(const char *key,char *out,int size) {
 const char *value="";
 if(!strcmp(key,"ui_stAccountStatus"))value=accountStatus;
 else if(!strcmp(key,"ui_stAccountSignedIn"))value=signedIn;
 else if(!strcmp(key,"ui_stAccountName"))value="Player One";
 snprintf(out,size,"%s",value);
}
int main(void) {
 STPBoard b={0}; STPNotice n={0}; int order[STP_MAX_ROWS],i;
 b.count=5;b.local=3;
 for(i=0;i<5;i++){b.rows[i].id=i;b.rows[i].team=i%2+1;b.rows[i].score=5-i;}
 b.rows[4].team=3;
 assert(STP_Order(&b,order)==5 && order[0]==0 && order[1]==2 && order[2]==1 && order[4]==4);
 assert(STP_PageCount(0)==1 && STP_PageCount(32)==3 && STP_PageCount(64)==5);
 assert(STP_NormalizePage(-1,3)==2 && STP_NormalizePage(99,3)==0);
 b.teams=0;assert(STP_Winner(&b)==0);
 b.rows[2].score=5;assert(STP_Winner(&b)==-1);
 b.rows[2].team=3;assert(STP_Winner(&b)==0); /* spectators cannot win */
 b.count=0;assert(STP_Winner(&b)==-2);
 assert(STP_NoticePush(&n,"Saved.",0,100));
 assert(!STP_NoticePush(&n,"Saved.",0,101)); /* duplicate doesn't extend lifetime */
 assert(n.started==100 && STP_NoticeAlpha(&n,200)>0 && STP_NoticeAlpha(&n,7000)==0);
 assert(STP_NoticePush(&n,"Try again.",2,400));
 assert(STP_NoticeAlpha(&n,399)==0); /* clock reset clears visibility */
 assert(!strcmp(STP_Mode(3,0,0),"Duel"));
 assert(!strcmp(STP_Mode(6,0,0),"TFFA"));
 assert(!strcmp(STP_Mode(7,0,0),"Siege")); /* legacy Siege is not a tournament */
 assert(!strcmp(STP_Mode(7,1,0),"Tournament"));
 assert(!strcmp(STP_Mode(3,0,1),"Ranked Duel")); /* only caller-verified eligibility */
 assert(!strcmp(STP_Mode(0,0,1),"FFA"));
 {
  const STPPainter painter={drawFill,drawText,NULL,NULL};
  char ratio[24];
  STP_FormatRatio(ratio,sizeof(ratio),5,0);assert(!strcmp(ratio,"--"));
  STP_FormatRatio(ratio,sizeof(ratio),0,2);assert(!strcmp(ratio,"0.00"));
  b.count=1;b.rows[0].assists=3;b.rows[0].kills=5;b.rows[0].deaths=2;b.rows[0].hasTffaKd=1;
  b.mode=6;STP_DrawBoard(&painter,&b);
  assert(kdHeaders==1 && ratioHeaders==1 && scoreHeaders==0 && timeHeaders==0);
  assert(assistHeaders==1 && assistValues==1 && kdValues==1 && ratioValues==1);
  b.rows[0].hasTffaKd=0;STP_DrawRow(&painter,&b,0,132);
  assert(kdValues==1 && ratioValues==1);
  b.mode=8;STP_DrawBoard(&painter,&b);
  assert(assistHeaders==1 && kdHeaders==1 && ratioHeaders==1 && scoreHeaders==1 && timeHeaders==1);
  b.mode=0;b.rows[0].team=0;b.rows[0].score=-2;b.rows[0].wins=7;
  b.rows[0].losses=1;b.rows[0].ping=42;b.rows[0].minutes=3;
  checkFfa=1;
  STP_DrawBoard(&painter,&b);
  b.result=1;
  assert(ffaColumn==6&&ffaRowColumn==6);
  ffaColumn=ffaRowColumn=0;
  STP_DrawBoard(&painter,&b);
  assert(ffaColumn==6&&ffaRowColumn==6);
  checkFfa=0;
 }
 STP_ObserveNotices(readNoticeCvar,0);
 signedIn="1";accountStatus="Signed in with Discord.";
 STP_ObserveNotices(readNoticeCvar,100);
 assert(!strcmp(stpNotice.text,"Logged in as Player One."));
 accountStatus="Saved sign-in unavailable. Keep open to finish sign-out.";
 STP_ObserveNotices(readNoticeCvar,200);
 assert(!strcmp(stpNotice.text,accountStatus)); /* signed in is not proof of a successful operation */
 accountStatus="Browser could not be opened. Try again.";
 STP_ObserveNotices(readNoticeCvar,300);
 assert(!strcmp(stpNotice.text,accountStatus));
 signedIn="0";accountStatus="Signed out.";
 STP_ObserveNotices(readNoticeCvar,400);
 assert(!strcmp(stpNotice.text,"Logged out."));
 puts("PASS presentation ordering, pagination, winner/tie, spectator, notification and mode policies");
 return 0;
}
