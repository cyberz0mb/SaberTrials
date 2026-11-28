#pragma once
struct usercmd_s;
void SV_ASInit();
void SV_ASFrame();
void SV_ASAccountChanged(int slot);
void SV_ASReset(int slot);
bool SV_ASDeferBegin(int slot);
bool SV_ASAllowed(int slot);
bool SV_ASCommand(int slot);
void SV_ASSample(int slot,const usercmd_s& cmd);
