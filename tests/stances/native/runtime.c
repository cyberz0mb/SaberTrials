/* Harness executes the actual candidate PM_GetSaberStance and classifiers. */
#include <stdio.h>
#include <string.h>
#include "anims.h"
typedef struct {int firstFrame,numFrames,frameLerp,loopFrames;} animation_t;
typedef struct {int readyAnim,type,numBlades;} saberInfo_t;
enum {SABER_NONE,SABER_SINGLE,SABER_STAFF,SABER_SWORD};
typedef struct {int saberAnimLevel;} force_t;
typedef struct {int clientNum,saberEntityNum,saberHolstered,stats[16];force_t fd;} playerState_t;
typedef struct {playerState_t* ps;animation_t* animations;} pmove_t;
typedef int qboolean;
#define qtrue 1
#define qfalse 0
#define STAT_ST_STANCES_A 9
#define STAT_ST_STANCES_ACTIVE 12
enum {SS_NONE,SS_FAST,SS_MEDIUM,SS_STRONG,SS_DESANN,SS_TAVION,SS_DUAL,SS_STAFF};
static pmove_t movement,*pm=&movement;
static playerState_t state;
static animation_t animations[MAX_ANIMATIONS];
static saberInfo_t first={-1,SABER_SINGLE,1},second={-1,SABER_SINGLE,1};
static int dual;
static saberInfo_t* BG_MySaber(int client,int saber) {(void)client;return saber?(dual?&second:NULL):&first;}
static int BG_SabersOff(playerState_t* ps) {return ps->saberHolstered==2;}
#include "st_stance_runtime.h"
#include "candidate_functions.inc"
#include "candidate_animation_fixture.inc"
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x);return 1;}}while(0)
int main(void) {
    int p[12],styles[]={SS_FAST,SS_MEDIUM,SS_STRONG,SS_DUAL,SS_STAFF};
    int slots[]={0,1,2,6,9},i,id;
    pm->ps=&state;pm->animations=animations;state.saberEntityNum=1;
    fill_animation_fixture(animations);
    CHECK(ST_StanceLibraryValid(animations));
    CHECK(ST_StanceParse("123456bccdee",p));ST_StancePack(p,&state.stats[9]);
    state.fd.saberAnimLevel=SS_FAST;
    CHECK(PM_GetSaberStance()==PM_GetStockSaberStance()); /* foreign server stats are not stance choices */
    state.stats[STAT_ST_STANCES_ACTIVE]=0x5311;
    for(i=0;i<5;i++) {
        state.fd.saberAnimLevel=styles[i];dual=styles[i]==SS_DUAL;
        first.type=styles[i]==SS_STAFF?SABER_STAFF:SABER_SINGLE;
        first.numBlades=styles[i]==SS_STAFF?2:1;
        CHECK(PM_GetSaberStance()==BOTH_ST_READY_01+p[slots[i]]-1);
        state.stats[STAT_ST_STANCES_ACTIVE]=0;CHECK(PM_GetSaberStance()==PM_GetStockSaberStance());state.stats[STAT_ST_STANCES_ACTIVE]=0x5311;
        state.saberEntityNum=0;CHECK(PM_GetSaberStance()==BOTH_STAND1);state.saberEntityNum=1;
        state.saberHolstered=2;CHECK(PM_GetSaberStance()==BOTH_STAND1);state.saberHolstered=0;
        first.readyAnim=BOTH_STAND2;CHECK(PM_GetSaberStance()==BOTH_STAND2);first.readyAnim=-1;
        animations[BOTH_ST_READY_01].numFrames++;
        CHECK(PM_GetSaberStance()==PM_GetStockSaberStance());
        animations[BOTH_ST_READY_01].numFrames--;
    }
    /* A staff's one-blade FAST mode must not consume the Single Blue choice. */
    dual=0;state.fd.saberAnimLevel=SS_FAST;state.saberHolstered=1;
    first.type=SABER_STAFF;first.numBlades=2;
    CHECK(PM_GetSaberStance()==PM_GetStockSaberStance());
    state.saberHolstered=0;state.fd.saberAnimLevel=SS_DUAL;dual=1;
    CHECK(PM_GetSaberStance()==PM_GetStockSaberStance()); /* mixed staff/single */
    first.type=SABER_SINGLE;first.numBlades=1;second.numBlades=3;
    CHECK(PM_GetSaberStance()==PM_GetStockSaberStance()); /* exotic dual geometry */
    second.numBlades=1;first.type=SABER_SWORD;
    CHECK(PM_GetSaberStance()==PM_GetStockSaberStance());
    first.type=SABER_SINGLE;
    dual=1;second.readyAnim=BOTH_STAND1;CHECK(PM_GetSaberStance()==BOTH_STAND1);second.readyAnim=-1;
    for(id=BOTH_ST_READY_01;id<=BOTH_ST_READY_15;id++) {
        CHECK(BG_SaberStanceAnim(id));CHECK(BG_InSaberStandAnim(id));
    }
    CHECK(!BG_InSaberStandAnim(BOTH_A1_T__B_));
    CHECK(BOTH_ST_READY_15<2048); /* retained animation encoding/toggle boundary */
    printf("PASS: actual shared selection; all families, overrides, off/lost saber, missing library, ready classifiers\n");
    return 0;
}
