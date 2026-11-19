#include "st_setup_core.h"
#include <cassert>
#include <iostream>
int main(){
 assert(ss::number("0.125",0,1,false,"0"));
 assert(!ss::number("nan",0,1,false,"0"));
 assert(!ss::number("1;quit",0,1,false,"0"));
 assert(!ss::number("1.5",0,10,true,"0"));
 assert(ss::number("999",0,100,true,"999")); // Existing custom value survives untouched.
 assert(!ss::number("998",0,100,true,"999"));
 stc::Draft d;stc::Snapshot live;live.vars["rate"]="25000";live.vars["s_volume"]="0.5";
 d.open(live);d.value.vars["s_volume"]="0.8";live.vars["s_volume"]="0.2";assert(!d.canApply(live));
 ss::DisplayTest test;test.begin(100);assert(test.remaining(101)==15);assert(!test.expired(15099));assert(test.expired(15100));
 test.keep();assert(!test.expired(20000));
 stc::Snapshot display;for(const char* n:ss::displayNames())display.vars[n]=!strcmp(n,"cl_renderer")?"rd-vanilla":"0";
 assert(ss::recoveryValid(display));display.vars["fs_game"]="other";assert(!ss::recoveryValid(display));
 display.vars.erase("fs_game");display.vars["cl_renderer"]="bad;quit";assert(!ss::recoveryValid(display));
 assert(ss::restartKind("r_picmip")==1);assert(ss::restartKind("s_khz")==2);assert(ss::restartKind("rate")==0);
 std::cout<<"Setup validation, conflict and recovery contracts passed\n";
}
