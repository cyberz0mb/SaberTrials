#include <algorithm>
#include <array>
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <string>
#include <vector>
#include "st_tffa_teams.h"
#include "st_format_award.h"

enum { MAX_CLIENTS=32, CON_DISCONNECTED=0, CON_CONNECTING=1, CON_CONNECTED=2,
       GT_DUEL=3, GT_TEAM=6, SVF_BOT=1, TEAM_FREE=0, TEAM_SPECTATOR=3,
       SPECTATOR_NOT=0, SPECTATOR_FREE=1, PERS_SCORE=0, CS_INTERMISSION=4 };
enum { BUTTON_ATTACK=1,BUTTON_TALK=2,BUTTON_USE_HOLDABLE=4,BUTTON_GESTURE=8,BUTTON_WALKING=16,
       BUTTON_USE=32,BUTTON_FORCEGRIP=64,BUTTON_ALT_ATTACK=128,BUTTON_ANY=256,BUTTON_FORCEPOWER=512,
       BUTTON_FORCE_LIGHTNING=1024,BUTTON_FORCE_DRAIN=2048,BUTTON_FEINT=4096,BUTTON_BLOCK=8192 };
using qboolean=int;
using team_t=int;
constexpr int qtrue=1,qfalse=0;
struct usercmd_t {int forwardmove,rightmove,upmove,buttons,angles[3];};
struct clientSession_t {
    int sessionTeam,spectatorState,spectatorClient,stQueueTicket,stServiceTicket,stLadderRank,
        stLadderPlayed,stDuelSeriesOpponent,stDuelSeriesWins;
};
struct gclient_t {
    clientSession_t sess;
    struct { int connected; usercmd_t cmd; } pers;
    struct {int persistant[1],clientNum;} ps;
};
struct Entity {struct {int svFlags;} r;} g_entities[MAX_CLIENTS];
struct { int maxclients,gametype,intermissiontime,intermissionQueued,restarted,time,startTime,warmupTime,
        stDuelRoundAnnounced,teamScores[10]; gclient_t clients[MAX_CLIENTS]; } level;
struct {int integer;} st_gameFormat,st_pugAfkSeconds;
static int teamCount,cap,tournament,begins,awards,leaves,warnings;
static std::map<std::string,int> vars;
static std::string action;
static char *va(const char *fmt,...) {
    static char buffers[8][256]; static unsigned index;
    char *buf=buffers[index++%8]; va_list args; va_start(args,fmt);
    vsnprintf(buf,256,fmt,args); va_end(args); return buf;
}
struct Traps {
    int Cvar_VariableIntegerValue(const char *key){return vars[key];}
    void Cvar_Set(const char *key,const char *v){vars[key]=atoi(v);}
    void Argv(int,char *s,int n){snprintf(s,n,"%s",action.c_str());}
    void SendServerCommand(int,const char *s){assert(!strstr(s,"\\n"));if(strstr(s,"within 15 seconds")) ++warnings;}
    void SetConfigstring(int,const char*){}
} trapObject,*trap=&trapObject;
static int G_TffaTeams(){return teamCount;}
static int ST_TournamentControlsDuel(){return tournament;}
static int ST_MatchEffectiveTeamCap(){return cap;}
static int TeamCount(int ignore,int team){
    int n=0;
    for(int i=0;i<level.maxclients;++i)
        if(i!=ignore&&level.clients[i].pers.connected==CON_CONNECTED&&level.clients[i].sess.sessionTeam==team)++n;
    return n;
}
static int G_TffaHasRoom(int team,int ignore){return !cap||TeamCount(ignore,team)<cap;}
static int Com_Clampi(int min,int max,int v){return std::clamp(v,min,max);}
static int Q_stricmp(const char *a,const char *b){return strcmp(a,b);}
static void ClientUserinfoChanged(int){}
static void SetTeam(Entity *ent,char *name){
    int slot=int(ent-g_entities);
    int team=!strcmp(name,"s")?TEAM_SPECTATOR:TEAM_FREE;
    for(int t=0;t<teamCount;++t)
        if(!strcmp(name,ST_TffaName(ST_TffaTeamAt(t))))team=ST_TffaTeamAt(t);
    level.clients[slot].sess.sessionTeam=team;
}
void ST_FormatAwardBegin(int){++begins;}
void ST_FormatAwardLeave(int){++leaves;}
void ST_FormatAward(int,int,int){++awards;}

#include "../g_st_formats.inc"

static void setup(int mode,int players) {
    level={};vars.clear();memset(g_entities,0,sizeof(g_entities));
    teamCount=2;cap=1;tournament=0;begins=awards=leaves=warnings=0;
    level.maxclients=MAX_CLIENTS;level.gametype=mode==1?GT_TEAM:GT_DUEL;
    st_gameFormat.integer=mode;st_pugAfkSeconds.integer=90;level.time=1000;
    for(int i=0;i<players;++i) {
        level.clients[i].pers.connected=CON_CONNECTED;
        level.clients[i].sess.sessionTeam=TEAM_SPECTATOR;
        level.clients[i].sess.stDuelSeriesOpponent=-1;
    }
    ST_FormatInit(qfalse);
}
static void join(int slot) {action="join";ST_PugCommand(slot);}
static void expectPair(int first,int second) {
    ST_LadderFrame();
    assert(TeamCount(-1,TEAM_FREE)==2);
    assert(level.clients[first].sess.sessionTeam==TEAM_FREE);
    assert(level.clients[second].sess.sessionTeam==TEAM_FREE);
}
static void finish(int winner,int loser){
    ST_LadderResult(winner,loser);
    for(int i:{winner,loser}){
        level.clients[i].sess.stDuelSeriesOpponent=-1;
        ST_Assign(i,TEAM_SPECTATOR);
    }
}
int main(){
    setup(1,5);join(4);join(1);join(2);join(0);
    ST_PugFrame();
    assert(level.clients[4].sess.sessionTeam==1 && level.clients[1].sess.sessionTeam==2);
    assert(ST_QueueHead()==2 && begins==1);
    ST_PugEnd(); assert(level.clients[4].sess.sessionTeam==1 && awards==1);
    ST_PugSaveRotation();
    assert(level.clients[2].sess.sessionTeam==1 && level.clients[0].sess.sessionTeam==2);
    assert(ST_QueueHead()==4);
    setup(1,3);join(0);join(1);join(2);ST_PugFrame();ST_PugEnd();
    ST_FormatDisconnect(2);level.clients[2].pers.connected=CON_DISCONNECTED;
    ST_PugSaveRotation();assert(level.clients[0].sess.sessionTeam==1);
    setup(1,3);join(0);join(1);join(2);ST_PugFrame();level.intermissiontime=100;ST_PugEnd();
    action="leave";ST_PugCommand(2);ST_PugSaveRotation();
    assert(level.clients[0].sess.sessionTeam==1 && level.clients[2].sess.sessionTeam==TEAM_SPECTATOR);
    gclient_t npc={}; npc.ps.clientNum=0; npc.pers.cmd.buttons=1;
    int last=stLastInput[0];++level.time;ST_FormatInput(&npc);assert(stLastInput[0]==last);
    setup(1,12);teamCount=8;
    for(int i=0;i<8;++i)join(i);
    ST_PugFrame();join(8);ST_PugEnd();ST_PugSaveRotation();
    assert(level.clients[8].sess.sessionTeam==1 && ST_QueueHead()==0);
    ST_PugEnd();ST_PugSaveRotation();assert(level.clients[0].sess.sessionTeam==2);
    setup(1,5);cap=2;
    for(int i=0;i<5;++i)join(i);
    ST_PugFrame();level.clients[0].ps.persistant[0]=3;
    assert(ST_LowestPlayer(1,0)==2);
    level.clients[0].ps.persistant[0]=0;assert(ST_LowestPlayer(1,0)==0);
    setup(1,3);g_entities[0].r.svFlags=g_entities[1].r.svFlags=SVF_BOT;
    level.clients[0].sess.sessionTeam=1;level.clients[1].sess.sessionTeam=2;
    join(2);ST_PugFrame();assert(level.clients[2].sess.sessionTeam==1);
    auto &human=level.clients[2];human.ps.clientNum=2;
    human.pers.cmd.buttons=BUTTON_ATTACK;++level.time;ST_FormatInput(&human);assert(stLastInput[2]==level.time);
    human.pers.cmd.buttons=BUTTON_WALKING|BUTTON_ANY;++level.time;ST_FormatInput(&human);assert(stLastInput[2]!=level.time);
    human.pers.cmd.buttons=BUTTON_TALK|BUTTON_WALKING|BUTTON_ANY|BUTTON_ATTACK;
    level.time+=75000;ST_FormatInput(&human);ST_PugFrame();ST_PugFrame();assert(warnings==1);
    level.time+=15000;ST_PugFrame();assert(level.clients[2].sess.sessionTeam==TEAM_SPECTATOR);
    setup(2,5);expectPair(0,1);assert(begins==1);
    finish(1,0);assert(level.clients[1].sess.stLadderRank==1 && level.clients[0].sess.stLadderRank==2);
    expectPair(2,3); finish(2,3);
    expectPair(0,2); finish(0,2);
    expectPair(3,4); finish(3,4);
    expectPair(1,0);assert(awards==4);
    setup(2,5);expectPair(0,1);finish(0,1);expectPair(2,3);
    level.clients[2].sess.stDuelSeriesOpponent=3;level.clients[3].sess.stDuelSeriesOpponent=2;
    level.clients[2].sess.stDuelSeriesWins=7;
    ST_FormatDisconnect(0);level.clients[0].pers.connected=CON_DISCONNECTED;expectPair(2,3);
    assert(level.clients[2].sess.stDuelSeriesWins==7);
    level.clients[5].pers.connected=CON_CONNECTING;
    expectPair(2,3);ST_FormatDisconnect(3);level.clients[3].pers.connected=CON_DISCONNECTED;
    assert(level.clients[2].sess.stDuelSeriesWins==0 && awards==1);
    setup(2,2); expectPair(0,1); finish(0,1);
    level.clients[2].pers.connected=CON_CONNECTED;level.clients[2].sess.sessionTeam=TEAM_SPECTATOR;
    expectPair(1,2);
    level.clients[1].sess.stDuelSeriesWins=5;level.clients[1].sess.stDuelSeriesOpponent=2;
    ST_FormatInit(qtrue);ST_FormatConnect(1);
    assert(vars["st_ladderAwardOpen"]==1 && level.clients[1].sess.stDuelSeriesWins==5);
    ST_FormatInit(qfalse);ST_FormatConnect(1);
    assert(!vars["st_ladderAwardOpen"] && !level.clients[1].sess.stDuelSeriesWins &&
           level.clients[1].sess.stDuelSeriesOpponent==-1 && level.clients[1].sess.stLadderRank==2);
    tournament=1;assert(!ST_FormatMode());
    puts("Gameplay format checks passed.");
}
