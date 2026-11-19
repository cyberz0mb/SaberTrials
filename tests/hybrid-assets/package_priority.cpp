// No game process: FS_AddGameDirectory sorts ascending then prepends each PK3.
// Therefore the expanded animation package must compare greater than the base.
#include <cstdio>
#include "fs_pathcmp_under_test.h"
int main(int argc, char** argv) {
    if(argc!=3) return 2;
    if(FS_PathCmp(argv[2],argv[1])<=0) {
        std::fprintf(stderr,"Expanded animations hidden by stance library: %s loses to %s\n",argv[2],argv[1]);
        return 1;
    }
    std::printf("Engine package priority: %s overrides %s\n",argv[2],argv[1]);
    return 0;
}
