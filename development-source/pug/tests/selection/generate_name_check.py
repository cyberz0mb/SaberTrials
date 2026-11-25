from pathlib import Path
import sys
cg=Path(sys.argv[2])
src=(cg/'cg_players.c').read_text()
names=src[src.index('v = Info_ValueForKey(configstring, "n");'):src.index('// colors',src.index('v = Info_ValueForKey(configstring, "n");'))]
draw=(cg/'cg_draw.c').read_text()
mark='name = cgs.clientinfo[ cg.crosshairClientNum ].cleanname;'
cross=draw[draw.index(mark):draw.index('if (cgs.gametype >= GT_TEAM)',draw.index(mark))]
out=Path(sys.argv[1])
out.write_text(r"""
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdarg>
#include <string>
struct Client {char name[36],cleanname[36];};
struct {int gametype;Client clientinfo[1];}cgs;
struct {int crosshairClientNum;}cg;
struct Cvar{int integer;} st_streamerMode,st_streamerPlayerNames;
enum{GT_DUEL=3,MAX_CLIENTS=32,CS_SERVERINFO,CS_PLAYERS};
static int format;
static const char* nick="^1Kyle^7";
const char*CG_ConfigString(int index){return index==CS_SERVERINFO?"server":"player";}
const char*Info_ValueForKey(const char*,const char*key){
 static char value[2][64];static size_t index;char* dest=value[(index++)%2];
 if(!strcmp(key,"n"))snprintf(dest,64,"%s",nick);
 else snprintf(dest,64,"%d",!strcmp(key,"lr")?1:format);
 return dest;
}
void Q_strncpyz(char*d,const char*s,size_t n){snprintf(d,n,"%s",s);}
void Q_strcat(char*d,size_t n,const char*s){snprintf(d+strlen(d),n-strlen(d),"%s",s);}
#define Com_sprintf snprintf
void Q_StripColor(char*s){char*d=s;for(char*p=s;*p;++p){if(*p=='^'&&p[1]){++p;continue;}*d++=*p;}*d=0;}
char* va(const char*fmt,...){static char scratch[128];va_list args;va_start(args,fmt);vsnprintf(scratch,sizeof(scratch),fmt,args);va_end(args);return scratch;}
void load(){const char*configstring="player",*v;Client&newInfo=cgs.clientinfo[0];
"""+names+"}\n"+'std::string crosshair(){char*name;\n'+cross+"return name;}\n"+r"""
int main(){
 cgs.gametype=3;format=2;load();
 if(strcmp(cgs.clientinfo[0].name,"^1Kyle^7 (1)")||crosshair()!="Kyle (1)")return 1;
 st_streamerMode.integer=1;if(crosshair()!="Player 1 (1)")return 2;
 format=0;load();if(crosshair()!="Player 1")return 3;
 st_streamerMode.integer=0;if(crosshair()!="Kyle")return 4;
 puts("Colored Ladder name, plain crosshair name and anonymous crosshair rank passed. Ordinary Duel clears rank.");
}
""")
