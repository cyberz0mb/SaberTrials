/* Saber Trials tournament state machine. No engine or network dependencies. */
#ifndef ST_EVENT_H
#define ST_EVENT_H
#include <stdint.h>
#define STE_ENTRIES 32
#define STE_MEMBERS 128
#define STE_TEAM_SIZE 5
#define STE_HISTORY 63
enum { STE_OFF, STE_REGISTRATION, STE_READY, STE_LIVE, STE_PAUSED, STE_COMPLETE };
enum { STE_PLAYED, STE_FORFEIT, STE_BYE, STE_VOID };
typedef struct {
 char account[65], name[64], team[65], teamName[64];
 int verified, connected;
} STEProfile;
typedef struct { STEProfile profile; int entry, ready, starter; } STEMember;
typedef struct { char id[65], name[64]; int disqualified, playedWins; } STEEntry;
typedef struct { int a,b,winner,kind,score[2]; } STEResult;
typedef struct {
 int phase, teamSize, count, memberCount, bracketSize, roundSize, cursor;
 int seeds[STE_ENTRIES], slots[STE_ENTRIES], next[STE_ENTRIES];
 int active[2], score[2], champion, staffPaused, serial, resetSerial;
 int historyCount;
 uint64_t lastTick, playedMs, remaining[2];
 STEEntry entries[STE_ENTRIES]; STEMember members[STE_MEMBERS];
 STEResult history[STE_HISTORY];
} STEvent;
void STE_Open(STEvent*,int teamSize,uint64_t now);
int STE_Join(STEvent*,const STEProfile*);
int STE_Leave(STEvent*,const char* account);
int STE_Start(STEvent*,uint32_t randomSeed,uint64_t now);
int STE_Member(const STEvent*,const char* account);
int STE_Side(const STEvent*,int member);
int STE_StartPractice(STEvent*,uint32_t randomSeed,uint64_t now);
int STE_Ready(STEvent*,const char* account,uint64_t now);
void STE_Connected(STEvent*,const char* account,int connected,uint64_t now);
void STE_Tick(STEvent*,uint64_t now);
int STE_Round(STEvent*,int winnerSide,uint64_t now);
int STE_Score(STEvent*,int red,int blue,uint64_t now);
int STE_Substitute(STEvent*,const char* absent,const char* replacement,uint64_t now);
int STE_Pause(STEvent*,int pause,uint64_t now);
int STE_Restart(STEvent*,uint64_t now);
int STE_Disqualify(STEvent*,int entry,uint64_t now);
#endif
