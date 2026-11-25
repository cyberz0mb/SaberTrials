#pragma once
#include "qcommon/qcommon.h"
constexpr int CA_ACTIVE=8, CS_SERVERINFO=0, MAX_RELIABLE_COMMANDS=64;
struct TestCls {int state=CA_ACTIVE,realtime=10000;};
struct TestCl {int serverTime=1000;struct{char stringData[128]; int stringOffsets[1];}gameState{};};
struct TestClc {int demoplaying=0,reliableSequence=0,reliableAcknowledge=0;};
extern TestCls cls;extern TestCl cl;extern TestClc clc;
const char* Info_ValueForKey(const char*,const char*);
void CL_AddReliableCommand(const char*,int);
