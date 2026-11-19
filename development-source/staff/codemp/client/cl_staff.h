#pragma once
void CL_StaffInit(void);
void CL_StaffReset(void);
void CL_StaffFrame(void);
bool CL_StaffPacket(const netadr_t* from);
void CL_StaffCommand_f(void);
void CL_ConnectAddress(const char* server);
