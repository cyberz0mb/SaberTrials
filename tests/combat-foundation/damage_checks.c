/* Execute the exact extracted accepted-source functions, not a rewritten
 * approximation. Engine-dependent animation speed is an explicit fixture. */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define QINLINE __inline
enum {STAT_ARMOR=5, CLASS_VEHICLE=7, DAMAGE_NO_ARMOR=1, DAMAGE_HALF_ABSORB=2,
 DAMAGE_HALF_ARMOR_REDUCTION=4};
typedef struct {int saberAnimLevel;} force_t;
typedef struct {int torsoAnim,torsoTimer,weapon,brokenLimbs,electrifyTime,stats[16];force_t fd;} ps_t;
typedef struct {ps_t ps;int NPC_class;} gclient_t;
typedef struct {int localAnimIndex;struct {int number;} s;gclient_t* client;void* m_pVehicle;} gentity_t;
typedef struct {int numFrames,frameLerp;} animation_t;
static struct {animation_t anims[1];} bgAllAnims[1];
static struct {int time;} level;
static float speed=1;
static void BG_SaberStartTransAnim(int client,int style,int weapon,int anim,float* factor,int broken) {
 (void)client;(void)style;(void)weapon;(void)anim;(void)broken;*factor=speed;
}
#include "accepted_damage_functions.inc"
#define CHECK(x) do {++checks;if(!(x)){fprintf(stderr,"line %d: %s\n",__LINE__,#x);exit(1);}} while(0)
int main(void) {
 int checks=0,t,i,damage,armor;gclient_t c;gentity_t e;
 int maxima[]={25,30,60,70,80,90,120,180};
 memset(&c,0,sizeof(c));memset(&e,0,sizeof(e));e.client=&c;
 bgAllAnims[0].anims[0].numFrames=20;bgAllAnims[0].anims[0].frameLerp=50;
 c.ps.torsoTimer=1000;CHECK(G_GetAttackDamage(&e,2,120,.5f)==2);
 c.ps.torsoTimer=750;CHECK(G_GetAttackDamage(&e,2,120,.5f)==60);
 c.ps.torsoTimer=500;CHECK(G_GetAttackDamage(&e,2,120,.5f)==120);
 c.ps.torsoTimer=250;CHECK(G_GetAttackDamage(&e,2,120,.5f)==60);
 c.ps.torsoTimer=0;CHECK(G_GetAttackDamage(&e,2,120,.5f)==2);
 c.ps.torsoTimer=350;CHECK(G_GetAttackDamage(&e,2,180,.65f)==180);
 c.ps.torsoTimer=1000;CHECK(G_GetAnimPoint(&e)==1.f);
 c.ps.torsoTimer=0;CHECK(G_GetAnimPoint(&e)==0.f);
 for(i=0;i<8;i++)for(t=0;t<=1000;t++) {
  c.ps.torsoTimer=t;damage=G_GetAttackDamage(&e,2,maxima[i],.5f);
  CHECK(damage>=2 && damage<=maxima[i]);
 }
 /* Negative frameLerp and the existing speed adjustment remain intact. */
 bgAllAnims[0].anims[0].frameLerp=-50;c.ps.torsoTimer=500;
 CHECK(G_GetAttackDamage(&e,2,120,.5f)==120);
 speed=.75f;c.ps.torsoTimer=625;CHECK(G_GetAttackDamage(&e,2,120,.5f)==120);
 speed=1.f;
 for(damage=0;damage<=200;damage++)for(armor=0;armor<=150;armor++) {
  int save;c.ps.stats[STAT_ARMOR]=armor;
  save=CheckArmor(&e,damage,0);CHECK(save==(damage<armor?damage:armor));
  CHECK(c.ps.stats[STAT_ARMOR]==armor-save);
  c.ps.stats[STAT_ARMOR]=armor;save=CheckArmor(&e,damage,DAMAGE_HALF_ABSORB);
  CHECK(save==((damage+1)/2<armor?(damage+1)/2:armor));
 }
 c.ps.stats[STAT_ARMOR]=100;CHECK(CheckArmor(&e,31,DAMAGE_NO_ARMOR)==0);
 CHECK(c.ps.stats[STAT_ARMOR]==100);
 CHECK(CheckArmor(&e,31,DAMAGE_HALF_ARMOR_REDUCTION)==31);
 CHECK(c.ps.stats[STAT_ARMOR]==85);
 c.NPC_class=CLASS_VEHICLE;e.m_pVehicle=&e;c.ps.electrifyTime=101;level.time=100;
 CHECK(CheckArmor(&e,31,0)==0);
 e.client=NULL;CHECK(CheckArmor(&e,31,0)==0);
 printf("Accepted-source ramp/armor: %d checks passed. Full trace/contact/Force runtime is not simulated.\n",checks);
 return 0;
}
