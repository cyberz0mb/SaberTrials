#include <stdio.h>
#include <stdlib.h>
enum {qfalse=0,qtrue=1,CS_ST_COMBAT_CONTROLS=1};
static const char *wire;
static int mode,active;
static const char *CG_ConfigString(int n){(void)n;return wire;}
static void BG_ST_SetManualGuard(int m,int a){mode=m;active=a;}
#include "combat_sync.inc"
int main(void){
 int m,a,i;char message[32];
 const char *invalid[]={"","1","1 1","2 1 1","1 -1 1","1 3 1","1 1 -1","1 1 2","garbage"};
 for(m=0;m<3;m++)for(a=0;a<2;a++){
  sprintf(message,"1 %d %d",m,a);wire=message;CG_ParseCombatControls();
  if(mode!=m||active!=a)return 1;
 }
 for(i=0;i<sizeof(invalid)/sizeof(invalid[0]);i++){
  wire=invalid[i];mode=active=1;CG_ParseCombatControls();if(mode||active)return 2;
 }
 puts("Compact combat configuration: all modes and missing/malformed/old-server states passed.");return 0;
}
