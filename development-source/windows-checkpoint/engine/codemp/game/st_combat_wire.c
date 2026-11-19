#include "st_combat_wire.h"
#include <string.h>
static int directionValid(STC_Direction d) {return d>=0 && d<STC_DIRECTION_COUNT;}
int STC_StateValid(const STC_State* s) {
 if(!s || !s->epoch || s->phase<STC_IDLE || s->phase>STC_FINISHED ||
    s->windupMs>10000 || s->elapsedMs>s->windupMs ||
    s->recoveryMs>2000 || s->cooldownMs>10000 || s->recoveryMs>s->cooldownMs ||
    s->feintsUsed>1 || s->contacted>1 || s->held>1 || s->inputSeen>1)return 0;
 if(!directionValid(s->redirect) && s->redirect!=STC_DIRECTION_NONE)return 0;
 if(s->attack) {
  if(!STC_StyleInfo(s->style) || !directionValid(s->direction) || !s->windupMs || s->phase==STC_IDLE)return 0;
 } else if(s->style!=STC_STYLE_NONE || s->direction!=STC_DIRECTION_NONE ||
           s->windupMs || s->elapsedMs || s->feintsUsed || s->contacted ||
           s->recoveryMs || s->cooldownMs ||
           (s->phase!=STC_IDLE && s->phase!=STC_CANCELLED && s->phase!=STC_FINISHED))return 0;
 if(s->phase==STC_WINDUP && s->elapsedMs>=s->windupMs)return 0;
 if(s->phase==STC_RECOVERY) {
  if(!s->recoveryMs || !s->feintsUsed)return 0;
 } else if(s->recoveryMs)return 0;
 if(s->phase==STC_REDIRECT_READY) {
  if(!directionValid(s->redirect) || !s->feintsUsed)return 0;
 } else if(s->phase!=STC_RECOVERY && s->redirect!=STC_DIRECTION_NONE)return 0;
 return 1;
}
static void put32(unsigned char* b,uint32_t n) {
 b[0]=(unsigned char)n;b[1]=(unsigned char)(n>>8);
 b[2]=(unsigned char)(n>>16);b[3]=(unsigned char)(n>>24);
}
static uint32_t get32(const unsigned char* b) {
 return (uint32_t)b[0]|((uint32_t)b[1]<<8)|((uint32_t)b[2]<<16)|((uint32_t)b[3]<<24);
}
int STC_Encode(const STC_State* s,unsigned char* bytes,size_t size) {
 uint32_t fields[16];unsigned i;
 if(!bytes || size!=STC_WIRE_SIZE || !STC_StateValid(s))return 0;
 fields[0]=s->epoch;fields[1]=s->attack;fields[2]=s->lastTime;fields[3]=s->lastInputTime;
 fields[4]=(uint32_t)s->style;fields[5]=(uint32_t)s->direction;
 fields[6]=(uint32_t)s->redirect;fields[7]=(uint32_t)s->phase;
 fields[8]=s->windupMs;fields[9]=s->elapsedMs;fields[10]=s->recoveryMs;fields[11]=s->cooldownMs;
 fields[12]=s->feintsUsed;fields[13]=s->contacted;fields[14]=s->held;fields[15]=s->inputSeen;
 bytes[0]='S';bytes[1]='T';bytes[2]='C';bytes[3]=1;
 bytes[4]=(unsigned char)STC_WIRE_SIZE;bytes[5]=bytes[6]=bytes[7]=0;
 for(i=0;i<16;i++)put32(bytes+8+i*4,fields[i]);return 1;
}
int STC_Decode(STC_State* s,const unsigned char* bytes,size_t size) {
 STC_State copy;uint32_t fields[16];unsigned i;
 if(!s || !bytes || size!=STC_WIRE_SIZE || bytes[0]!='S' || bytes[1]!='T' || bytes[2]!='C' ||
    bytes[3]!=1 || bytes[4]!=STC_WIRE_SIZE || bytes[5] || bytes[6] || bytes[7])return 0;
 for(i=0;i<16;i++)fields[i]=get32(bytes+8+i*4);
 /* Check enum ranges before converting unsigned untrusted integers to enums. */
 if(fields[4]>=STC_STYLE_COUNT || fields[5]>STC_DIRECTION_NONE ||
    fields[6]>STC_DIRECTION_NONE || fields[7]>STC_FINISHED)return 0;
 memset(&copy,0,sizeof(copy));
 copy.epoch=fields[0];copy.attack=fields[1];copy.lastTime=fields[2];copy.lastInputTime=fields[3];
 copy.style=(STC_Style)fields[4];copy.direction=(STC_Direction)fields[5];
 copy.redirect=(STC_Direction)fields[6];copy.phase=(STC_Phase)fields[7];
 copy.windupMs=fields[8];copy.elapsedMs=fields[9];copy.recoveryMs=fields[10];copy.cooldownMs=fields[11];
 copy.feintsUsed=fields[12];copy.contacted=fields[13];copy.held=fields[14];copy.inputSeen=fields[15];
 if(!STC_StateValid(&copy))return 0;
 *s=copy;return 1;
}
