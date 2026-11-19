#include "st_glm_validate.h"
#include <fstream>
#include <iostream>
#include <iterator>
int main(int argc,char** argv) {
    if(argc!=2 && argc!=3) return 2;
    std::ifstream stream(argv[1],std::ios::binary);
    if(!stream) return 2;
    std::vector<char> data((std::istreambuf_iterator<char>(stream)),{});
    const size_t maxBones=argc==3?72:1024;
    const char* error=st_glm::validate(data.data(),data.size(),maxBones);
    std::cout<<(error?error:"valid classic GLM")<<'\n';
    return error?1:0;
}
