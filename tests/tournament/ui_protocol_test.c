/* Real cgame presentation adapter with only engine imports substituted. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#define CHECK(x) do{if(!(x)){fprintf(stderr,"line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef int qboolean;
#define qtrue 1
#define qfalse 0
static char keys[100][64],values[100][256],sent[256];static int used,argc;static const char*argv[16];
static const char*CG_Argv(int n){return n>=0&&n<argc?argv[n]:"";}
static int Argc(void){return argc;}
static void Q_strncpyz(char*out,const char*in,size_t n){snprintf(out,n,"%s",in);}
static char*va(const char*fmt,...){static char buf[8][512];static int cursor;va_list args;char*out=buf[cursor++%8];va_start(args,fmt);vsnprintf(out,512,fmt,args);va_end(args);return out;}
static void Set(const char*k,const char*v){int i;for(i=0;i<used&&strcmp(keys[i],k);i++){}CHECK(i<100);if(i==used){Q_strncpyz(keys[used++],k,64);}Q_strncpyz(values[i],v,256);}
static const char*Get(const char*k){int i;for(i=0;i<used;i++)if(!strcmp(keys[i],k))return values[i];return "";}
static void Read(const char*k,char*out,int n){Q_strncpyz(out,Get(k),(size_t)n);}
static void Send(const char*s){Q_strncpyz(sent,s,sizeof(sent));}
static struct {void(*Cvar_Set)(const char*,const char*);void(*Cvar_VariableStringBuffer)(const char*,char*,int);int(*Cmd_Argc)(void);void(*SendClientCommand)(const char*);} imports={Set,Read,Argc,Send},*trap=&imports;
#include "cg_event_ui.inc"
int main(void){
 const char*valid[]={"steactions","1","1","0","1","1","7","0","0","0","0","31"};int i;
 Set("ui_stAccountName","SamplePlayer");CG_STEventResetUI();
 CHECK(!strcmp(Get("ui_stEventCanJoin"),"0"));CHECK(!strcmp(Get("ui_stAccountName"),"SamplePlayer"));
 CHECK(!Get("ui_ste0")[0]); /* No tournament banner on ordinary servers. */
 argc=12;for(i=0;i<12;i++)argv[i]=valid[i];CHECK(CG_STEventMessage("steactions"));
 CHECK(!strcmp(Get("ui_stEventCanJoin"),"1"));CHECK(!strcmp(Get("ui_stEventCanReady"),"1"));
 argc=2;argv[1]="0";CG_STEventSubstitute_f();CHECK(!strcmp(sent,"tournament substitute 7"));
 sent[0]=0;Set("ui_stEventSub0","7;quit");CG_STEventSubstitute_f();CHECK(!sent[0]);
 Set("ui_stEventSub0","129");CG_STEventSubstitute_f();CHECK(!sent[0]);
 CHECK(!strcmp(Get("ui_stEventBracketPage4"),"1"));
 argc=12;for(i=0;i<12;i++)argv[i]=valid[i];argv[6]="999999999999999999";CHECK(CG_STEventMessage("steactions"));CHECK(!strcmp(Get("ui_stEventCanJoin"),"0"));
 argc=3;argv[1]="44bad";argv[2]="poison";CHECK(CG_STEventMessage("steui"));CHECK(strcmp(Get("ui_ste44"),"poison"));
 argv[1]="44";argv[2]="Ready check";CG_STEventMessage("steui");CHECK(!strcmp(Get("ui_ste44"),"Ready check"));
 argv[1]="1";argv[2]="Someone else";CG_STEventMessage("steaccount");CHECK(!strcmp(Get("ui_stAccountName"),"SamplePlayer"));
 argc=1;CG_STEventMessage("stereset");CHECK(!strcmp(Get("ui_stEventCanReady"),"0"));CHECK(!strcmp(Get("ui_stEventSub0"),"0"));
 puts("client UI protocol pass");return 0;
}
