#pragma once
#include <cstdint>
bool CL_ASCollecting();
void CL_ASFrame();
void CL_ASReset();
void CL_ASAction(uint32_t origin,const char* command);
void CL_ASWait(uint32_t origin);
uint32_t Cbuf_ASOrigin();
void Cbuf_ASReset();
void Cbuf_ASBound(const char* text,uint32_t origin);
