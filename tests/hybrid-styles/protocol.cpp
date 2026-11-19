#include "qcommon/q_shared.h"
#include "qcommon/qcommon.h"
#include "server/server.h"
#include <cstdio>
#include <cstdlib>
#include <cstdarg>
#include <cstring>
void QDECL Com_Printf(const char*,...) {}
void QDECL Com_DPrintf(const char*,...) {}
NORETURN void QDECL Com_Error(int,const char* format,...) {
 va_list args;va_start(args,format);vfprintf(stderr,format,args);va_end(args);exit(2);
}
cvar_t* cl_shownet=nullptr;
server_t sv={};
long FS_FOpenFileRead(const char*,fileHandle_t* file,qboolean){*file=0;return -1;}
int FS_Read(void*,int,fileHandle_t){abort();}
void FS_FCloseFile(fileHandle_t){abort();}
void* Z_Malloc(int,memtag_t,qboolean,int){abort();}
sharedEntity_t* SV_GentityNum(int){abort();}
static int checks;
#define CHECK(x) do{++checks;if(!(x)){fprintf(stderr,"line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
int main() {
 byte bytes[16384];msg_t msg;playerState_t before={},after={},decoded={};
 cvar_t shownet={};cl_shownet=&shownet;
 for(int vehicle=0;vehicle<2;vehicle++)for(int pilot=0;pilot<2;pilot++) {
  after={};after.commandTime=1200;after.m_iVehicleNum=pilot?1:0;
  after.eFlags=pilot?EF_NODRAW:0;after.origin[0]=12.5f;after.stats[0]=100;
  MSG_Init(&msg,bytes,sizeof(bytes));MSG_WriteDeltaPlayerstate(&msg,&before,&after,(qboolean)vehicle);
  printf("LEGACY %d %d ",vehicle,pilot);
  for(int i=0;i<msg.cursize;i++)printf("%02x",bytes[i]);puts("");
 }
#ifndef STH_PROTOCOL_BASELINE
 static_assert(sizeof(STH_State)==84,"21 fixed 32-bit hybrid/loadout members");
 for(int vehicle=0;vehicle<2;vehicle++)for(int pilot=0;pilot<2;pilot++) {
  after={};after.commandTime=1200;after.m_iVehicleNum=pilot?1:0;after.eFlags=pilot?EF_NODRAW:0;
  after.stHybrid={5,6,5,1672,13,267,350,1,1,3,0xfedcba98u,1,112};
  after.stHybrid.loadout[0]=2;after.stHybrid.loadout[1]=5;after.stHybrid.loadout[2]=6;
  after.stHybrid.selectedStyle=5;after.stHybrid.requestedSelection=6;after.stHybrid.availableMask=126;
  after.stHybrid.comboCount=1;after.stHybrid.chainPending=2;
  after.stCombatFlags=STC_GUARD_PAUSED;
  MSG_Init(&msg,bytes,sizeof(bytes));MSG_WriteDeltaPlayerstate(&msg,&before,&after,(qboolean)vehicle);
  CHECK(!msg.overflowed);MSG_BeginReading(&msg);
  MSG_ReadDeltaPlayerstate(&msg,&before,&decoded,(qboolean)vehicle);
  CHECK(!memcmp(&after.stHybrid,&decoded.stHybrid,sizeof(STH_State)));
  CHECK(after.stCombatFlags==decoded.stCombatFlags);
  before=after;after.stHybrid={};after.stCombatFlags=0;
  MSG_Init(&msg,bytes,sizeof(bytes));MSG_WriteDeltaPlayerstate(&msg,&before,&after,(qboolean)vehicle);
  MSG_BeginReading(&msg);MSG_ReadDeltaPlayerstate(&msg,&before,&decoded,(qboolean)vehicle);
  CHECK(!memcmp(&after.stHybrid,&decoded.stHybrid,sizeof(STH_State)));
  CHECK(!decoded.stCombatFlags);before={};
 }
#endif
 printf("hybrid real snapshot: %d checks passed\n",checks);return 0;
}
