#include "st_cosmetic_spec.h"
#include <iostream>
#include <string>
static int failures=0;
static void check(bool value,const char* name) { if(!value) {++failures;std::cerr<<name<<'\n';} }
int main() {
    st_cosmetic::Spec spec={};
    std::string valid="STCOS1 models/players/t800/model.glm models/cosmetics/t800/model.glm models/cosmetics/t800/model.skin\n";
    check(st_cosmetic::parse(valid.data(),valid.size(),spec),"valid");
    for(const auto& bad:{"", "STCOS2", "STCOS1 models/players/../x.glm models/cosmetics/x.glm models/cosmetics/x.skin",
        "STCOS1 models/players/x.glm models/players/x.glm models/cosmetics/x.skin",
        "STCOS1 models/players/x.glm models/cosmetics/x.glm models/cosmetics/x.skin extra"})
        check(!st_cosmetic::parse(bad,strlen(bad),spec),"malformed accepted");
    auto nul=valid;nul[12]=0;check(!st_cosmetic::parse(nul.data(),nul.size(),spec),"embedded null");
    auto huge=valid+std::string(256,' ');check(!st_cosmetic::parse(huge.data(),huge.size(),spec),"byte cap");
    check(!st_cosmetic::reject(true,true,0,false,1,0,false),"eligible");
    check(st_cosmetic::reject(false,true,0,false,1,0,false)==st_cosmetic::enabled,"opt out");
    check(st_cosmetic::reject(true,false,0,false,1,0,false)==st_cosmetic::identity,"identity");
    check(st_cosmetic::reject(true,true,2,false,1,0,false)==st_cosmetic::root,"limb");
    check(st_cosmetic::reject(true,true,0,true,1,0,false)==st_cosmetic::gore,"gore");
    check(st_cosmetic::reject(true,true,0,false,2,0,false)==st_cosmetic::shadows,"stencil");
    check(st_cosmetic::reject(true,true,0,false,1,1,false)==st_cosmetic::lod,"distance");
    check(!st_cosmetic::reject(true,true,0,false,1,1,false,3),"authored LOD chain");
    check(!st_cosmetic::reject(true,true,0,false,1,7,false,3),"visual chain selects independently of canonical count");
    check(st_cosmetic::reject(true,true,0,false,1,-1,false,3)==st_cosmetic::lod,"invalid canonical LOD");
    check(st_cosmetic::reject(true,true,0,true,1,1,false,3)==st_cosmetic::gore,"LOD must not bypass gore");
    check(st_cosmetic::reject(true,true,2,false,1,1,false,3)==st_cosmetic::root,"LOD must not bypass detached root");
    check(st_cosmetic::reject(true,true,0,false,2,1,false,3)==st_cosmetic::shadows,"LOD must not bypass stencil");
    check(st_cosmetic::reject(true,true,0,false,1,0,true)==st_cosmetic::shader,"effect");
    return failures?1:0;
}
