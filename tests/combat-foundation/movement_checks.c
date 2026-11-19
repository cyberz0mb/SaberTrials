/* Actual accepted/candidate movement functions, extracted without rewriting. */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
enum {PM_NORMAL,PM_NOCLIP,PM_FREEZE,PMF_JUMP_HELD=2,BUTTON_TALK=2};
#define ST_STAFF_STAT 15
#define ST_STAFF_FROZEN 1
#define ST_STAFF_GHOST 2
typedef struct {int forwardmove,rightmove,upmove,buttons,generic_cmd;} usercmd_t;
typedef struct {int pm_type,pm_flags,speed,stats[16];} playerState_t;
typedef struct {playerState_t* ps;usercmd_t cmd;} pmove_t;
static pmove_t *pm;
#include "movement_functions.inc"
#define CHECK(x) do {++checks;if(!(x)){fprintf(stderr,"line %d: %s\n",__LINE__,#x);exit(1);}} while(0)
int main(void) {
 int checks=0,mode,staff,axis;playerState_t ps;pmove_t client,server;
 memset(&ps,0,sizeof(ps));memset(&client,0,sizeof(client));client.ps=&ps;
 ps.speed=400;ps.pm_type=PM_NOCLIP;ps.stats[15]=ST_STAFF_GHOST;
 client.cmd.upmove=127;pm=&client;
 CHECK(ClientScale(&client.cmd)>0.f);
 CHECK(ClientScale(&client.cmd)==ServerScale(&client.cmd));
 for(mode=PM_NORMAL;mode<=PM_FREEZE;mode++)for(staff=0;staff<=2;staff++)
 for(axis=-127;axis<=127;axis+=127) {
  playerState_t serverPs;
  ps.pm_type=mode;ps.stats[15]=staff;ps.pm_flags=PMF_JUMP_HELD;
  client.cmd.forwardmove=axis;client.cmd.rightmove=127;client.cmd.upmove=-127;
  client.cmd.buttons=65535;client.cmd.generic_cmd=15;
  serverPs=ps;server=client;server.ps=&serverPs;
  ClientStaff(&client);ServerStaff(&server);
  CHECK(memcmp(&client.cmd,&server.cmd,sizeof(client.cmd))==0);
  CHECK(ps.pm_flags==serverPs.pm_flags);
  CHECK(ClientScale(&client.cmd)==ServerScale(&client.cmd));
  if(mode==PM_FREEZE && staff==ST_STAFF_FROZEN) {
   CHECK(client.cmd.forwardmove==0 && client.cmd.rightmove==0 && client.cmd.upmove==0);
   CHECK(client.cmd.buttons==BUTTON_TALK && !client.cmd.generic_cmd);
  } else if(mode==PM_NOCLIP && staff==ST_STAFF_GHOST) {
   CHECK(client.cmd.buttons==BUTTON_TALK && !client.cmd.generic_cmd);
   CHECK(client.cmd.upmove==-127 && !(ps.pm_flags&PMF_JUMP_HELD));
  } else CHECK(client.cmd.buttons==65535 && client.cmd.generic_cmd==15);
 }
 printf("Actual client/server staff movement: %d checks passed.\n",checks);return 0;
}
