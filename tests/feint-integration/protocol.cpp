#include "qcommon/q_shared.h"
#include "qcommon/qcommon.h"
#include "server/server.h"
#include <cstdio>
#include <cstdlib>
#include <cstdarg>
#include <cstring>
/* Real production MSG delta and Huffman code, linked without an engine loop. */
void QDECL Com_Printf(const char*,...) {}
void QDECL Com_DPrintf(const char*,...) {}
NORETURN void QDECL Com_Error(int,const char* format,...) {
 va_list args;va_start(args,format);vfprintf(stderr,format,args);va_end(args);exit(2);
}
cvar_t* cl_shownet=nullptr;
server_t sv={};
/* Exercise the default field tables (no optional net-field override files). */
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
 /* Byte-for-byte default-off fixtures, also compiled against the baseline. */
 for(int vehicle=0;vehicle<2;vehicle++)for(int pilot=0;pilot<2;pilot++) {
  after={};after.commandTime=1200;after.m_iVehicleNum=pilot?1:0;
  after.eFlags=pilot?EF_NODRAW:0;after.origin[0]=12.5f;after.stats[0]=100;
  MSG_Init(&msg,bytes,sizeof(bytes));MSG_WriteDeltaPlayerstate(&msg,&before,&after,(qboolean)vehicle);
  printf("LEGACY %d %d ",vehicle,pilot);
  for(int i=0;i<msg.cursize;i++)printf("%02x",bytes[i]);puts("");
 }
#ifndef ST_PROTOCOL_BASELINE
 static_assert(sizeof(STC_State)==64,"Combat state must have 16 32-bit members");
 /* The existing 16-bit user-command transport must preserve the feint input. */
 {
  usercmd_t from={},to={},out={};to.serverTime=1234;to.buttons=BUTTON_FEINT|BUTTON_ATTACK;
  MSG_Init(&msg,bytes,sizeof(bytes));MSG_WriteDeltaUsercmdKey(&msg,77,&from,&to);
  MSG_BeginReading(&msg);MSG_ReadDeltaUsercmdKey(&msg,77,&from,&out);
  CHECK(out.buttons==to.buttons && out.serverTime==to.serverTime);
 }
 for(int vehicle=0;vehicle<2;vehicle++)for(int pilot=0;pilot<2;pilot++) {
  after={};after.commandTime=1200;after.m_iVehicleNum=pilot?1:0;
  after.eFlags=pilot?EF_NODRAW:0;
  after.stCombat.epoch=0xfedcba98u;after.stCombat.attack=0x81234567u;
  after.stCombat.lastTime=0xfffffff0u;after.stCombat.lastInputTime=1199;
  after.stCombat.style=STC_SINGLE_RED;after.stCombat.direction=STC_T_B;
  after.stCombat.redirect=STC_TR_BL;after.stCombat.phase=STC_RECOVERY;
  after.stCombat.windupMs=750;after.stCombat.elapsedMs=123;
  after.stCombat.recoveryMs=200;after.stCombat.cooldownMs=600;
  after.stCombat.feintsUsed=after.stCombat.contacted=after.stCombat.held=after.stCombat.inputSeen=1;
  after.stCombatFlags=STC_GUARD_PAUSED;
  MSG_Init(&msg,bytes,sizeof(bytes));
  MSG_WriteDeltaPlayerstate(&msg,&before,&after,(qboolean)vehicle);
  CHECK(!msg.overflowed);
  MSG_BeginReading(&msg);MSG_ReadDeltaPlayerstate(&msg,&before,&decoded,(qboolean)vehicle);
  CHECK(!memcmp(&after.stCombat,&decoded.stCombat,sizeof(after.stCombat)));
  CHECK(after.stCombatFlags==decoded.stCombatFlags);
  /* Reset/deactivation must remove every previous extended state field. */
  before=after;after.stCombat={};after.stCombatFlags=0;
  MSG_Init(&msg,bytes,sizeof(bytes));MSG_WriteDeltaPlayerstate(&msg,&before,&after,(qboolean)vehicle);
  MSG_BeginReading(&msg);MSG_ReadDeltaPlayerstate(&msg,&before,&decoded,(qboolean)vehicle);
  CHECK(!memcmp(&after.stCombat,&decoded.stCombat,sizeof(after.stCombat)));
  CHECK(!decoded.stCombatFlags);before={};
 }
#endif
 printf("Production playerstate delta/Huffman: %d checks passed.\n",checks);return 0;
}
