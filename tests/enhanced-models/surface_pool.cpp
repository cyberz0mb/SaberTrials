#include "st_surface_pool.h"
#include <vector>
#include <iostream>
struct Surface { int value=0; };
int main() {
    st_models::SurfacePool<Surface,256,32> pool;
    std::vector<Surface*> saved;
    for(int i=0;i<8192;++i) {
        Surface* p=pool.allocate(); if(!p) return 1;
        p->value=i; saved.push_back(p);
    }
    if(pool.allocate()) return 2;
    // More than the old 2048-entry capacity must preserve every pointer/value.
    for(int i=0;i<8192;++i) if(saved[i]->value!=i) return 3;
    pool.reset();
    for(int i=0;i<8192;++i) if(pool.allocate()!=saved[i]) return 4;
    if(pool.allocate()) return 5;
    std::cout<<"8192 stable surfaces, bounded exhaustion, frame reuse passed\n";
}
