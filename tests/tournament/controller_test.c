#include "st_event.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do { if(!(x)) { fprintf(stderr,"line %d: %s\n",__LINE__,#x); exit(1); } } while(0)
static STEvent event;
static uint64_t now;
static STEProfile profile(int n,int team) {
 STEProfile p; memset(&p,0,sizeof(p));
 snprintf(p.account,sizeof(p.account),"account%d",n);
 snprintf(p.name,sizeof(p.name),"Player %d",n);
 if(team>=0)snprintf(p.team,sizeof(p.team),"team%d",team);
 if(team>=0)snprintf(p.teamName,sizeof(p.teamName),"[Team %d]",team);
 p.verified=p.connected=1; return p;
}
static void setup(int size,int entries) {
 int i,j; now=1000; STE_Open(&event,size,now);
 for(i=0;i<entries;i++)for(j=0;j<(size?size:1);j++) {
  STEProfile p=profile(i*5+j,size?i:-1); CHECK(STE_Join(&event,&p));
 }
}
static int member(int side,int index) {
 int i;for(i=0;i<event.memberCount;i++)if(STE_Side(&event,i)==side&&event.members[i].starter&&index--==0)return i;
 CHECK(0);return -1;
}
static void ready(void) {
 int i;for(i=0;i<event.memberCount;i++)if(STE_Side(&event,i)>=0&&event.members[i].starter&&!event.members[i].ready)
 CHECK(STE_Ready(&event,event.members[i].profile.account,now));
 CHECK(event.phase==STE_LIVE);
}
static void limits(void) {
 int n,size;for(n=0;n<=32;n++) { setup(0,n); CHECK(STE_Start(&event,17,now)==(n>=8&&n%2==0)); }
 for(size=2;size<=5;size++) { setup(size,8);CHECK(STE_Start(&event,3,now)); }
 STE_Open(&event,1,now);CHECK(event.phase==STE_OFF); /* invalid format */
 setup(0,32); {STEProfile p=profile(999,-1);CHECK(!STE_Join(&event,&p));}
 setup(2,8); {STEProfile p=profile(999,9);CHECK(!STE_Join(&event,&p));}
}
static void readiness(void) {
 int a; setup(5,2);CHECK(STE_Start(&event,1,now));a=member(0,0);
 CHECK(STE_Ready(&event,event.members[a].profile.account,now));
 CHECK(STE_Ready(&event,event.members[a].profile.account,now));CHECK(!event.members[a].ready);
 STE_Connected(&event,event.members[a].profile.account,0,now);
 for(int i=0;i<event.memberCount;i++)if(i!=a)CHECK(STE_Ready(&event,event.members[i].profile.account,now));
 CHECK(event.phase!=STE_LIVE);
 STE_Connected(&event,event.members[a].profile.account,1,now);ready();
 CHECK(!STE_Ready(&event,event.members[a].profile.account,now));
}
static void individual(void) {
 int serial;setup(0,8);CHECK(STE_Start(&event,2,now));ready();serial=event.serial;
 for(int i=0;i<9;i++){CHECK(STE_Round(&event,0,now));CHECK(event.serial==serial);}
 CHECK(STE_Round(&event,0,now));CHECK(event.serial>serial);CHECK(event.history[0].score[0]==10);
 ready();serial=event.serial;
 for(int i=0;i<10;i++)CHECK(STE_Round(&event,i%2,now));
 CHECK(event.serial==serial&&event.score[0]==5&&event.score[1]==5);
 CHECK(!STE_Round(&event,-1,now));CHECK(event.serial==serial);
 CHECK(STE_Round(&event,1,now));CHECK(event.serial>serial);
}
static void teams(void) {
 for(int size=2;size<=5;size++) {
  setup(size,2);CHECK(STE_Start(&event,3,now));ready();
  CHECK(STE_Score(&event,size*10-1,2,now));CHECK(event.phase==STE_LIVE);
  CHECK(STE_Score(&event,size*10,2,now));CHECK(event.phase==STE_COMPLETE);
 }
 setup(2,2);CHECK(STE_Start(&event,3,now));ready();CHECK(STE_Score(&event,3,3,now));
 now+=600000;STE_Tick(&event,now);CHECK(event.phase==STE_LIVE);
 CHECK(STE_Score(&event,4,3,now));CHECK(event.phase==STE_COMPLETE);
 /* A score in the time-limit frame belongs to that match, including an equalizer. */
 setup(2,2);CHECK(STE_Start(&event,3,now));ready();CHECK(STE_Score(&event,4,3,now));
 now+=600000;CHECK(STE_Score(&event,4,4,now));CHECK(event.phase==STE_LIVE);
 CHECK(STE_Score(&event,4,5,now));CHECK(event.phase==STE_COMPLETE);
}
static void disconnects(void) {
 int a;char account[65];setup(0,8);CHECK(STE_Start(&event,3,now));ready();a=member(0,0);memcpy(account,event.members[a].profile.account,sizeof(account));
 now+=5000;STE_Tick(&event,now);CHECK(event.playedMs==5000);
 STE_Connected(&event,account,0,now);now+=120000;STE_Tick(&event,now);CHECK(event.playedMs==5000&&event.remaining[0]==180000);
 STE_Connected(&event,account,1,now);CHECK(event.phase==STE_READY);ready();
 STE_Connected(&event,account,0,now);now+=179999;STE_Tick(&event,now);CHECK(event.historyCount==0);
 now++;STE_Tick(&event,now);CHECK(event.history[0].kind==STE_FORFEIT);
 setup(5,2);CHECK(STE_Start(&event,3,now));ready();a=member(0,0);
 STE_Connected(&event,event.members[a].profile.account,0,now);now+=599999;STE_Tick(&event,now);CHECK(event.phase!=STE_COMPLETE);
 now++;STE_Tick(&event,now);CHECK(event.phase==STE_COMPLETE);
}
static void substitution(void) {
 STEProfile bench,wrong;int a,b;setup(2,2);bench=profile(100,0);wrong=profile(101,1);
 CHECK(STE_Join(&event,&bench));CHECK(STE_Join(&event,&wrong));CHECK(STE_Start(&event,5,now));ready();
 a=STE_Member(&event,"account0");b=STE_Member(&event,"account100");
 CHECK(!STE_Substitute(&event,"account0","account100",now));
 STE_Connected(&event,"account0",0,now);CHECK(!STE_Substitute(&event,"account0","account101",now));
 CHECK(STE_Substitute(&event,"account0","account100",now));CHECK(!event.members[a].starter&&event.members[b].starter);
 CHECK(event.phase==STE_READY);ready();
 STE_Connected(&event,"account0",1,now);CHECK(!event.members[a].starter);
 bench=profile(102,0);CHECK(STE_Join(&event,&bench));CHECK(!event.members[STE_Member(&event,"account102")].starter);
 wrong=profile(103,9);CHECK(!STE_Join(&event,&wrong));
}
static void brackets(void) {
 int n;for(n=8;n<=32;n+=2) {
  setup(0,n);CHECK(STE_Start(&event,101,now));
  while(event.phase!=STE_COMPLETE) {ready();for(int i=0;i<10;i++)CHECK(STE_Round(&event,0,now));}
  CHECK(event.champion>=0);int played=0;for(int i=0;i<event.historyCount;i++)played+=event.history[i].kind==STE_PLAYED;
  CHECK(played==n-1);
 }
}
static void staff(void) {
 setup(2,2);CHECK(STE_Start(&event,7,now));ready();CHECK(STE_Score(&event,8,4,now));
 CHECK(STE_Pause(&event,1,now));now+=50000;STE_Tick(&event,now);CHECK(event.playedMs==0);
 CHECK(!STE_Score(&event,20,4,now));CHECK(STE_Restart(&event,now));CHECK(event.score[0]==0&&event.score[1]==0);
 CHECK(STE_Pause(&event,0,now));ready();CHECK(STE_Disqualify(&event,event.active[0],now));CHECK(event.phase==STE_COMPLETE);
 /* A request issued for an expired match cannot mutate the next match. */
 setup(0,8);CHECK(STE_Start(&event,7,now));ready();
 STE_Connected(&event,event.members[member(0,0)].profile.account,0,now);now+=300000;
 CHECK(!STE_Pause(&event,1,now));CHECK(!event.staffPaused);
}
static void identity(void) {
 STEProfile p;setup(0,0);p=profile(1,-1);p.verified=0;CHECK(!STE_Join(&event,&p));p.verified=1;CHECK(STE_Join(&event,&p));CHECK(!STE_Join(&event,&p));
 CHECK(STE_Leave(&event,p.account));CHECK(STE_Join(&event,&p));
 setup(2,0);p=profile(1,-1);CHECK(!STE_Join(&event,&p));
}
int main(int argc,char**argv) {
 CHECK(argc==2);
 if(!strcmp(argv[1],"limits"))limits();else if(!strcmp(argv[1],"ready"))readiness();
 else if(!strcmp(argv[1],"individual"))individual();else if(!strcmp(argv[1],"teams"))teams();
 else if(!strcmp(argv[1],"disconnect"))disconnects();else if(!strcmp(argv[1],"substitution"))substitution();
 else if(!strcmp(argv[1],"bracket"))brackets();else if(!strcmp(argv[1],"staff"))staff();else identity();
 puts("pass");return 0;
}
