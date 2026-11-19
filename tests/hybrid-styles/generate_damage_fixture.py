"""Compile production damage snippets unchanged with a narrow deterministic entity fixture."""
from pathlib import Path
import sys

root,out=map(Path,sys.argv[1:])
source=(root/'game/codemp/game/w_saber.c').read_text()
panimate=(root/'game/codemp/game/bg_panimate.c').read_text()
adapter=(root/'game/codemp/game/g_st_hybrid.inc').read_text()
saber=(root/'game/codemp/game/bg_saber.c').read_text()

def function(text,marker):
    start=text.index(marker);brace=text.index('{',start);depth=1;at=brace+1
    while depth:
        depth+=(text[at]=='{')-(text[at]=='}');at+=1
    return text[start:at]

ramp=function(source,'static QINLINE int G_GetAttackDamage(')
speed=function(panimate,'void BG_SaberStartTransAnim(')
classification=function(panimate,'qboolean PM_InSaberAnim(')
capture=function(adapter,'int G_ST_HybridDamageStyle(')
start=source.index('            if(hybridDamageStyle==STH_GREEN)')
end=source.index('\n\t\t\tattackStr =',start)
mp=source[start:end]
sp=next(line for line in source.splitlines() if 'fDmg=STH_PowerFactor(hybridDamageStyle)' in line)

# Removing only the new guarded hooks must reproduce the complete old damage
# calculation branch. This catches accidental changes to original styles or
# common special/rage/armor/trace handling.
baseline=(root.parent/'feint-candidate-01/game/codemp/game/w_saber.c').read_text()
begin='\t{ //this animation is that of the last attack movement, and so it should do full damage'
finish='\telse if (self->client->ps.saberAttackWound < level.time &&\n\t\tself->client->ps.saberIdleWound < level.time)'
new_branch=source[source.index(begin):source.index(finish)]
new_branch=new_branch.replace('\n\t\tint hybridDamageStyle=G_ST_HybridDamageStyle(self,rSaberNum);','')
new_branch=new_branch.replace(sp+'\n','').replace(mp+'\n','')
old_branch=baseline[baseline.index(begin):baseline.index(finish)]
assert new_branch==old_branch,'Original active damage branch changed outside guarded hybrid hooks'

prefix=r'''
#include "st_hybrid.h"
#include "game/anims.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#define QINLINE inline
typedef int qboolean;
enum { qfalse=0,qtrue=1,WP_SABER=2,FORCE_LEVEL_1=1,FORCE_LEVEL_3=3,
       BROKENLIMB_RARM=0,BROKENLIMB_LARM=1,LS_A_TL2BR=10,LS_A_T2B=16 };
typedef struct {int firstFrame,numFrames,frameLerp,loopFrames;} animation_t;
#include "game/st_hybrid_anims.h"
typedef struct {STH_State stHybrid;int torsoAnim,torsoTimer,weapon,brokenLimbs,saberInFlight,saberMove;
 struct {int saberAnimLevel;} fd;} playerState_t;
typedef struct {playerState_t ps;} gclient_t;
typedef struct {gclient_t* client;int localAnimIndex;struct {int number;}s;} gentity_t;
typedef struct {float animSpeedScale;} saberInfo_t;
static saberInfo_t hilt={1.0f};
static saberInfo_t* BG_MySaber(int,int index){return index?nullptr:&hilt;}
static struct {animation_t anims[MAX_ANIMATIONS];} bgAllAnims[1];
static struct {int integer;} g_saberRealisticCombat;
'''
tests=r'''
static int checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"damage:%d %s\n",__LINE__,#x);exit(1);}}while(0)
int main(){
 gclient_t client={};gentity_t ent={};ent.client=&client;
 playerState_t* p=&client.ps;p->weapon=WP_SABER;p->fd.saberAnimLevel=1;
 p->torsoAnim=BOTH_ST_PURPLE_A1_T__B_;p->saberMove=LS_A_TL2BR;
 animation_t* a=&bgAllAnims[0].anims[p->torsoAnim];a->numFrames=20;a->frameLerp=20;
 p->torsoTimer=400;CHECK(hooked_mp(&ent,5,35)==2);
 p->torsoTimer=300;CHECK(hooked_mp(&ent,5,35)==60);
 p->torsoTimer=200;CHECK(hooked_mp(&ent,5,35)==120);
 p->torsoTimer=100;CHECK(hooked_mp(&ent,5,35)==60);
 p->torsoTimer=0;CHECK(hooked_mp(&ent,5,35)==2);
 for(int timer=0;timer<=400;timer+=50){p->torsoTimer=timer;CHECK(hooked_mp(&ent,4,60)==47);CHECK(hooked_mp(&ent,0,777)==777);}
 p->torsoTimer=200;CHECK(hooked_mp(&ent,6,120)==90);
 CHECK(hooked_sp(4,0,2.5f)==3.75f&&hooked_sp(5,0,2.5f)==7.5f&&hooked_sp(6,0,2.5f)==6.25f);
 CHECK(hooked_sp(0,0,7.5f)==7.5f&&hooked_sp(5,1,2.5f)==2.5f);
 p->stHybrid.enabled=p->stHybrid.committed=1;p->stHybrid.attackStyle=5;
 p->stHybrid.attackAnim=p->torsoAnim;p->stHybrid.attackMove=p->saberMove;
 CHECK(G_ST_HybridDamageStyle(&ent,0)==5);
 p->stHybrid.style=4;p->stHybrid.requestedStyle=6;CHECK(G_ST_HybridDamageStyle(&ent,0)==5);
 p->saberInFlight=1;CHECK(G_ST_HybridDamageStyle(&ent,0)==0);p->saberInFlight=0;
 CHECK(G_ST_HybridDamageStyle(&ent,1)==0);
 p->saberMove=30;CHECK(G_ST_HybridDamageStyle(&ent,0)==0);p->saberMove=10;
 p->stHybrid.attackStyle=4;CHECK(G_ST_HybridDamageStyle(&ent,0)==0);p->stHybrid.attackStyle=5;
 p->stHybrid.committed=0;CHECK(G_ST_HybridDamageStyle(&ent,0)==0);
 printf("production hybrid damage hooks: %d checks passed; original branch unchanged\n",checks);return 0;
}
'''
text=prefix+classification+'\n'+speed+'\n'+ramp+'\n'+capture+'\n'
text+='static int hooked_mp(gentity_t* self,int hybridDamageStyle,int original) { int dmg=original;\n'+mp+'\nreturn dmg;}\n'
text+='static float hooked_sp(int hybridDamageStyle,int realistic,float original) { float fDmg=original;g_saberRealisticCombat.integer=realistic;\n'+sp+'\nreturn fDmg;}\n'
out.write_text(text+tests,encoding='utf-8')
chain=function(saber,'qboolean PM_SaberKataDone(int curmove, int newmove)\n{')
assert 'if(PM_ST_HybridUsable() && pm->ps->stHybrid.style)' in chain
out.with_name('chain_fixture.inc').write_text(chain,encoding='utf-8')
print('Extracted production damage/capture/speed; original active damage branch unchanged.')
