#pragma once
#include "st_event_account_api.h"
#include <string>
std::string SV_VerifiedPlayerAccount(int slot);
void SV_AccountFrame(bool (*allowGamePublish)(int) = nullptr);
void SV_AccountReset();
bool SV_AccountCommand(int slot);
void SV_AccountConsole_f();
bool GVM_AccountAvailable();
int GVM_AccountSet(int,const unsigned char generation[16],const STEProfile*);
void GVM_AccountClear(int);
