#include "st_handedness.h"
#include <stdexcept>
#include <iostream>
static void check(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
int main(){try{
    check(ST_HandParse("1")==1,"left preference was not read");
    const char* invalid[]={nullptr,"","0","2","-1","1junk","true","01","1;quit"};
    for(auto value:invalid)check(ST_HandParse(value)==0,"invalid preference enabled left hand");
    check(ST_HandAtSpawn(1,1,1,1)==1,"supported left preference not applied at spawn");
    for(int mask=0;mask<7;mask++)check(ST_HandAtSpawn(1,mask&1,mask&2,mask&4)==0,"missing capability was ignored");
    check(ST_HandAtSpawn(0,1,1,1)==0 && ST_HandAtSpawn(7,1,1,1)==0,"invalid choice was activated");
    for(unsigned flags=0;flags<1024;flags++)for(int hand=0;hand<2;hand++) {
        unsigned encoded=ST_HandSetFlag(flags,hand);
        check((encoded&~ST_HAND_LEFT_FLAG)==(flags&~ST_HAND_LEFT_FLAG),"unrelated network flags changed");
        check(encoded<1024 && ST_HandFromFlags(encoded)==hand,"hand does not round trip in existing 10-bit flags");
    }
    check(ST_HandAttachment(0,0,0)==0 && ST_HandAttachment(0,1,0)==1,"primary hand attachment");
    check(ST_HandAttachment(1,0,0)==1 && ST_HandAttachment(1,1,0)==0,"secondary hand attachment");
    check(ST_HandAttachment(0,1,1)==4 && ST_HandAttachment(1,1,1)==3,"wrist attachment");
    check(ST_HandAttachment(-1,1,0)==-1 && ST_HandAttachment(2,1,0)==-1,"invalid slot attached to jetpack");
    check(ST_HandEffective(ST_HAND_LEFT_FLAG,0)==ST_HAND_LEFT,"dismount did not restore dominant hand");
    check(ST_HandEffective(ST_HAND_LEFT_FLAG,12)==ST_HAND_RIGHT,"rider did not retain stock hand");
    std::cout<<"PASS: preference validation, spawn gates, replicated flags and hand/wrist attachments\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<"\n";return 1;}}
