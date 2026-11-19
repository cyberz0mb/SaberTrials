#pragma once
#define MAX_CLIENTS 64
#define CS_ACTIVE 4
#define NA_BOT 0
struct netadr_t {int type=3;};
struct client_t {int state=0;struct{netadr_t remoteAddress;}netchan;};
struct TestServerStatic {client_t clients[MAX_CLIENTS];};
struct TestCvar {int integer;};
extern TestServerStatic svs;extern TestCvar*sv_maxclients;
int Cmd_Argc();const char*Cmd_Argv(int);
int Cvar_VariableIntegerValue(const char*);
void Com_Printf(const char*,...);
void SV_SendServerCommand(client_t*,const char*,...);
