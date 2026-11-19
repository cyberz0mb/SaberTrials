// Real engine allocation/free and staff bookkeeping with minimal engine services.
// No game process, server, network socket, private account or key is created.
#include "st_staff_types.h"
#include "check.h"
#include <cstring>

enum {MAX_CLIENTS=32,CS_FREE=0,CS_ACTIVE=4,NA_BOT=0,SVF_BOT=8,ERR_DROP=1};
struct entity_t {struct {int number=0;} s;struct {int svFlags=SVF_BOT;} r;};
struct client_t {
 int state=CS_FREE,lastPacketTime=0,rate=0;char name[64]={};entity_t* gentity=nullptr;
 struct {struct {int type=0;} remoteAddress;} netchan;
 struct {bool demorecording=false;} demo;
};
static entity_t entities[MAX_CLIENTS];
static struct {client_t clients[MAX_CLIENTS];int time=123;} svs;
static struct Cvar {int integer=2;} maxclients;
static Cvar* sv_maxclients=&maxclients;
static st::Generation generations[MAX_CLIENTS]={};
static bool connected[MAX_CLIENTS]={},targetConnected[MAX_CLIENTS]={};
static std::string activeAccounts[MAX_CLIENTS];
static struct Authority {void Disconnect(int) {}} *authority=nullptr;
static void GVM_StaffRevoke(const char*,int) {}
static entity_t* SV_GentityNum(int slot) {return &entities[slot];}
static void SV_StopRecordDemo(client_t* client) {client->demo.demorecording=false;}
static void Com_Error(int,const char*,int) {throw std::runtime_error("Invalid client slot");}
void SV_StaffDisconnect(int slot);
#include "bot_lifecycle_functions.inc"

RUN_TEST(
 int bot=SV_BotAllocateClient();CHECK(bot==0);
 unsigned char first[16]={};CHECK(SV_StaffGeneration(bot,first));
 CHECK(targetConnected[bot]&&!connected[bot]); // targetable, never allowed to log in
 CHECK(svs.clients[bot].state==CS_ACTIVE&&svs.clients[bot].rate==16384);
 svs.clients[bot].demo.demorecording=true;strcpy(svs.clients[bot].name,"Bot");
 SV_BotFreeClient(bot);CHECK(!SV_StaffGeneration(bot,first));
 CHECK(!targetConnected[bot]&&!connected[bot]);CHECK(svs.clients[bot].state==CS_FREE);
 CHECK(!svs.clients[bot].demo.demorecording&&!svs.clients[bot].name[0]);
 bot=SV_BotAllocateClient();CHECK(bot==0);
 unsigned char second[16]={};CHECK(SV_StaffGeneration(bot,second));
 CHECK(memcmp(first,second,16)); // delayed requests cannot affect a replacement bot
 int other=SV_BotAllocateClient();CHECK(other==1);
 auto preserved=generations[0];CHECK(SV_BotAllocateClient()==-1);CHECK(generations[0]==preserved);
 SV_BotFreeClient(other);CHECK(SV_StaffGeneration(0,second));
 // Reconnecting as a human still gets a fresh generation and login eligibility.
 SV_StaffConnect(0,false);CHECK(connected[0]&&targetConnected[0]);
 CHECK(generations[0]!=preserved);SV_StaffDisconnect(0);CHECK(!SV_StaffGeneration(0,second));
)
