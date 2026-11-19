#pragma once
// Minimal engine boundary for exercising the actual client adapter off-screen.
#define CVAR_ROM 64
#define CA_ACTIVE 8
#define qfalse 0
struct AccountTestCls {int state=0;};
#define NA_LOOPBACK 2
struct netadr_t {int type=3;};
struct AccountTestClc {int demoplaying=0,clientNum=3;netadr_t serverAddress;};
extern AccountTestCls cls;
extern AccountTestClc clc;
void Cvar_Set(const char*,const char*);
void Cvar_Get(const char*,const char*,int);
void Com_Printf(const char*,...);
void Cmd_AddCommand(const char*,void(*)(),const char*);
void Cmd_RemoveCommand(const char*);
int Cmd_Argc();
const char* Cmd_Argv(int);
int Q_stricmp(const char*,const char*);
void CL_AddReliableCommand(const char*,int);
const char* NET_AdrToString(const netadr_t*);
int Cvar_VariableIntegerValue(const char*);
