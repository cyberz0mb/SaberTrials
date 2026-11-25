#pragma once
#include <cstring>
#include <string>
constexpr int MAX_CLIENTS=4, MAX_NAME_LENGTH=32, CS_ACTIVE=4, NA_BOT=0, CVAR_SERVERINFO=4;
constexpr int PM_NORMAL=0, PMF_FOLLOW=8, TEAM_SPECTATOR=3, PERS_TEAM=1, STAT_HEALTH=0;
constexpr int BUTTON_ATTACK=1, BUTTON_ALT_ATTACK=128, BUTTON_TALK=2;
struct usercmd_s { int serverTime=0,buttons=0,forwardmove=0,rightmove=0,upmove=0; };
struct client_t { int state=0; struct {struct {int type=1;} remoteAddress;} netchan; char name[32]="Jawa"; };
struct AsServer {int time=0;};
struct AsStatic {client_t* clients;};
struct cvar_t {int integer; const char* string;};
struct playerState_t {int pm_type=0,stats[2]={100},persistant[2]={},m_iVehicleNum=0,pm_flags=0;};
extern AsServer sv; extern AsStatic svs; extern cvar_t* sv_maxclients;
cvar_t* Cvar_Get(const char*,const char*,int,const char*);
int Cvar_VariableIntegerValue(const char*);
void Cmd_AddCommand(const char*,void(*)(),const char*);
const char* Cmd_Argv(int); int Cmd_Argc();
void Com_Printf(const char*,...); void SV_SendServerCommand(client_t*,const char*,...);
void SV_DropClient(client_t*,const char*);
playerState_t* SV_GameClientNum(int);
int Q_stricmp(const char*,const char*); void Q_strncpyz(char*,const char*,int); void Q_CleanStr(char*);
