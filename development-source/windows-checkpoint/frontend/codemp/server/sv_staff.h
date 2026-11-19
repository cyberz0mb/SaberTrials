#pragma once
#include "../staff/st_staff_game_api.h"
void SV_StaffConsole_f(void);
bool SV_StaffPacket(const netadr_t* from);
void SV_StaffConnect(int slot,bool bot);
void SV_StaffDisconnect(int slot);
void SV_StaffReset(void);
void SV_StaffFrame(void);
int SV_StaffRole(int slot);
int SV_StaffGeneration(int slot,unsigned char generation[16]);
const STStaffImports* SV_StaffImports(void);
int GVM_StaffExecute(const STVerifiedAction*,STGameResult*);
int GVM_StaffResolve(const char*,STTargetRef*);
void GVM_StaffRevoke(const char*,int actorSlot);
void GVM_StaffReset(void);
