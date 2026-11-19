#include "st_event.h"
#include <string.h>

static int active(const STEvent* e) {return e->phase>=STE_READY&&e->phase<=STE_PAUSED;}
static void clearReady(STEvent*e) {int i;for(i=0;i<e->memberCount;i++)e->members[i].ready=0;}
static int starters(const STEvent*e,int entry,int connected) {
 int i,n=0;for(i=0;i<e->memberCount;i++)if(e->members[i].entry==entry&&e->members[i].starter&&
 (!connected||e->members[i].profile.connected))n++;return n;
}
static int missing(const STEvent*e,int side) {return starters(e,e->active[side],1)!=(e->teamSize?e->teamSize:1);}
static void waiting(STEvent*e) {
 if(!active(e))return;
 e->phase=e->staffPaused||missing(e,0)||missing(e,1)?STE_PAUSED:STE_READY;
}
static void result(STEvent*e,int a,int b,int winner,int kind) {
 STEResult*r=&e->history[e->historyCount++];r->a=a;r->b=b;r->winner=winner;r->kind=kind;
 r->score[0]=e->score[0];r->score[1]=e->score[1];
 if(kind==STE_PLAYED&&winner>=0)e->entries[winner].playedWins++;
 e->next[e->cursor/2]=winner;e->cursor+=2;
}
static void nextMatch(STEvent*e) {
 int i,a,b;
 for(;;) {
  if(e->cursor>=e->roundSize) {
   if(e->roundSize==2) {e->champion=e->next[0];e->active[0]=e->active[1]=-1;e->phase=STE_COMPLETE;return;}
   e->roundSize/=2;e->cursor=0;
   for(i=0;i<STE_ENTRIES;i++){e->slots[i]=e->next[i];e->next[i]=-1;}
  }
  a=e->slots[e->cursor];b=e->slots[e->cursor+1];
  if(a>=0&&e->entries[a].disqualified)a=-1;
  if(b>=0&&e->entries[b].disqualified)b=-1;
  e->score[0]=e->score[1]=0;
  if(a<0||b<0) {result(e,a,b,a>=0?a:b,a<0&&b<0?STE_VOID:STE_BYE);continue;}
  e->active[0]=a;e->active[1]=b;e->playedMs=0;e->remaining[0]=e->remaining[1]=e->teamSize?600000:300000;
  e->staffPaused=0;e->serial++;e->resetSerial++;e->phase=STE_READY;clearReady(e);waiting(e);return;
 }
}
static void finish(STEvent*e,int side,int kind) {
 result(e,e->active[0],e->active[1],side<0?-1:e->active[side],kind);nextMatch(e);
}
void STE_Open(STEvent*e,int size,uint64_t now) {
 int i;memset(e,0,sizeof(*e));e->active[0]=e->active[1]=e->champion=-1;
 for(i=0;i<STE_ENTRIES;i++)e->seeds[i]=e->slots[i]=e->next[i]=-1;
 if(size!=0&&(size<2||size>5))return;
 e->teamSize=size;e->phase=STE_REGISTRATION;e->lastTick=now;
}
int STE_Member(const STEvent*e,const char*account) {
 int i;if(!account||!account[0])return -1;
 for(i=0;i<e->memberCount;i++)if(!strcmp(e->members[i].profile.account,account))return i;return -1;
}
int STE_Side(const STEvent*e,int m) {
 int side;if(m<0||m>=e->memberCount||!e->members[m].starter)return -1;
 for(side=0;side<2;side++)if(e->active[side]>=0&&e->members[m].entry==e->active[side])return side;return -1;
}
int STE_Join(STEvent*e,const STEProfile*p) {
 int i,entry=-1;const char*id;STEMember*m;
 if((e->phase!=STE_REGISTRATION&&!(e->teamSize&&active(e)))||!p||!p->verified||!p->account[0]||!p->name[0]||
 !memchr(p->account,0,sizeof(p->account))||!memchr(p->name,0,sizeof(p->name))||
 !memchr(p->team,0,sizeof(p->team))||!memchr(p->teamName,0,sizeof(p->teamName))||
 (e->teamSize&&!p->teamName[0])||e->memberCount>=STE_MEMBERS||STE_Member(e,p->account)>=0)return 0;
 id=e->teamSize?p->team:p->account;if(!id[0])return 0;
 for(i=0;i<e->count;i++)if(!strcmp(e->entries[i].id,id)){entry=i;break;}
 if(entry>=0&&e->entries[entry].disqualified)return 0;
 if(entry<0) {
  if(e->phase!=STE_REGISTRATION)return 0;
  if(e->count>=(e->teamSize?8:32))return 0;
  entry=e->count++;memcpy(e->entries[entry].id,id,strlen(id)+1);
  if(e->teamSize)memcpy(e->entries[entry].name,p->teamName,sizeof(p->teamName));
  else memcpy(e->entries[entry].name,p->name,sizeof(p->name));
 }
 m=&e->members[e->memberCount++];memset(m,0,sizeof(*m));m->profile=*p;m->entry=entry;
 m->starter=e->phase==STE_REGISTRATION&&starters(e,entry,0)<(e->teamSize?e->teamSize:1);return 1;
}
int STE_Leave(STEvent*e,const char*account) {
 int i,entry,remaining=0,m=STE_Member(e,account);
 if(e->phase!=STE_REGISTRATION||m<0)return 0;
 entry=e->members[m].entry;
 for(i=m;i+1<e->memberCount;i++)e->members[i]=e->members[i+1];e->memberCount--;
 for(i=0;i<e->memberCount;i++)if(e->members[i].entry==entry){remaining++;if(starters(e,entry,0)<e->teamSize)e->members[i].starter=1;}
 if(!remaining) {
  for(i=entry;i+1<e->count;i++)e->entries[i]=e->entries[i+1];e->count--;
  for(i=0;i<e->memberCount;i++)if(e->members[i].entry>entry)e->members[i].entry--;
 }
 return 1;
}
int STE_Start(STEvent*e,uint32_t seed,uint64_t now) {
 int i,n,order[STE_ENTRIES],shuffle[STE_ENTRIES];
 if(e->phase!=STE_REGISTRATION)return 0;
 if(e->teamSize) {if(e->count<2||e->count>8)return 0;}
 else if(e->count<8||e->count>32||(e->count&1))return 0;
 for(i=0;i<e->count;i++) {if(starters(e,i,0)!=(e->teamSize?e->teamSize:1))return 0;shuffle[i]=i;}
 if(!seed)seed=1;
 for(i=e->count-1;i>0;i--) {int pick,tmp;seed^=seed<<13;seed^=seed>>17;seed^=seed<<5;pick=(int)(seed%(uint32_t)(i+1));tmp=shuffle[i];shuffle[i]=shuffle[pick];shuffle[pick]=tmp;}
 for(n=2;n<e->count;n*=2){} e->bracketSize=e->roundSize=n;e->lastTick=now;
 order[0]=0;for(n=1;n<e->bracketSize;n*=2)for(i=n-1;i>=0;i--){int old=order[i];order[i*2]=old;order[i*2+1]=n*2-1-old;}
 for(i=0;i<e->bracketSize;i++)e->seeds[i]=e->slots[i]=order[i]<e->count?shuffle[order[i]]:-1;
 nextMatch(e);return 1;
}
void STE_Tick(STEvent*e,uint64_t now) {
 uint64_t dt;int m0,m1,expired0,expired1;
 if(now<e->lastTick)return;dt=now-e->lastTick;e->lastTick=now;if(!active(e))return;
 m0=missing(e,0);m1=missing(e,1);
 if(m0)e->remaining[0]=dt>=e->remaining[0]?0:e->remaining[0]-dt;
 if(m1)e->remaining[1]=dt>=e->remaining[1]?0:e->remaining[1]-dt;
 expired0=m0&&!e->remaining[0];expired1=m1&&!e->remaining[1];
 if(expired0||expired1) {finish(e,expired0&&expired1?-1:(expired0?1:0),expired0&&expired1?STE_VOID:STE_FORFEIT);return;}
 if(e->phase==STE_LIVE&&!e->staffPaused&&!m0&&!m1) {
  e->playedMs+=dt;
  /* Team winner evaluation belongs to STE_Score, with that frame's scores. */
 }
}
void STE_Connected(STEvent*e,const char*account,int connected,uint64_t now) {
 int m=STE_Member(e,account);STE_Tick(e,now);if(m<0)return;connected=!!connected;
 if(e->members[m].profile.connected==connected)return;e->members[m].profile.connected=connected;
 if(active(e)&&STE_Side(e,m)>=0){clearReady(e);waiting(e);}
}
int STE_Ready(STEvent*e,const char*account,uint64_t now) {
 int m,i,all=1,serial=e->serial;STE_Tick(e,now);if(serial!=e->serial)return 0;m=STE_Member(e,account);
 if(!active(e)||e->phase==STE_LIVE||m<0||STE_Side(e,m)<0||!e->members[m].profile.connected)return 0;
 e->members[m].ready=!e->members[m].ready;
 for(i=0;i<e->memberCount;i++)if(STE_Side(e,i)>=0&&(!e->members[i].ready||!e->members[i].profile.connected))all=0;
 if(all&&!e->staffPaused&&!missing(e,0)&&!missing(e,1))e->phase=STE_LIVE;return 1;
}
int STE_Round(STEvent*e,int side,uint64_t now) {
 int serial=e->serial;STE_Tick(e,now);
 if(e->serial!=serial||e->teamSize||e->phase!=STE_LIVE||side<0||side>1)return 0;
 e->score[side]++;
 if(e->score[0]+e->score[1]>=10&&e->score[0]!=e->score[1])finish(e,e->score[0]>e->score[1]?0:1,STE_PLAYED);
 return 1;
}
int STE_Score(STEvent*e,int red,int blue,uint64_t now) {
 int serial=e->serial;
 /* Scores and time form one observation; never decide from the prior frame. */
 if(e->teamSize&&e->phase==STE_LIVE){e->score[0]=red;e->score[1]=blue;}
 STE_Tick(e,now);
 if(e->serial!=serial||!e->teamSize||e->phase!=STE_LIVE)return 0;
 e->score[0]=red;e->score[1]=blue;
 if((red>=e->teamSize*10||blue>=e->teamSize*10||e->playedMs>=600000)&&red!=blue)finish(e,red>blue?0:1,STE_PLAYED);
 return 1;
}
int STE_Substitute(STEvent*e,const char*absent,const char*replacement,uint64_t now) {
 int a,b,serial=e->serial;STE_Tick(e,now);if(serial!=e->serial)return 0;a=STE_Member(e,absent);b=STE_Member(e,replacement);
 if(!active(e)||!e->teamSize||a<0||b<0||STE_Side(e,a)<0||e->members[a].profile.connected||
 !e->members[b].profile.connected||e->members[b].starter||e->members[a].entry!=e->members[b].entry)return 0;
 e->members[a].starter=0;e->members[b].starter=1;clearReady(e);waiting(e);return 1;
}
int STE_Pause(STEvent*e,int pause,uint64_t now) {
 int serial=e->serial;STE_Tick(e,now);if(serial!=e->serial||!active(e))return 0;e->staffPaused=!!pause;clearReady(e);waiting(e);return 1;
}
int STE_Restart(STEvent*e,uint64_t now) {
 int serial=e->serial;STE_Tick(e,now);if(serial!=e->serial||!active(e))return 0;e->score[0]=e->score[1]=0;e->playedMs=0;e->resetSerial++;clearReady(e);waiting(e);return 1;
}
int STE_Disqualify(STEvent*e,int entry,uint64_t now) {
 int side,serial=e->serial;STE_Tick(e,now);if(serial!=e->serial||!active(e)||entry<0||entry>=e->count||e->entries[entry].disqualified)return 0;
 e->entries[entry].disqualified=1;
 for(side=0;side<2;side++)if(e->active[side]==entry){finish(e,1-side,STE_FORFEIT);break;}return 1;
}
