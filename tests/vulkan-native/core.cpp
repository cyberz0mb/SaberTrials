#undef NDEBUG
#include "st_setup_core.h"
#include "st_frame_stats.h"
#include <cassert>
#include <cmath>
#include <iostream>
int main() {
    stc::Snapshot state;
    for(const char *name:ss::displayNames()) state.vars[name]="0";
    for(const char *renderer:{"rd-vanilla","rd-rend2","rd-vulkan"}) {
        state.vars["cl_renderer"]=renderer;
        assert(ss::recoveryValid(state));
    }
    state.vars["cl_renderer"]="rd-vulkan;quit";
    assert(!ss::recoveryValid(state));
    state.vars["cl_renderer"]="rd-vulkan";state.vars["fs_game"]="other";
    assert(!ss::recoveryValid(state));
    STFrameStats times;
    assert(times.mean()==0 && times.percentile(.95)==0);
    for(int i=1;i<=100;++i)times.add(i);
    assert(std::abs(times.mean()-50.5)<.0001 && times.percentile(.95)==95 && times.percentile(.99)==99);
    times.clear();for(int i=0;i<10000;++i)times.add(8);
    assert(times.values.size()==6000 && times.mean()==8);
    std::cout<<"Vulkan display recovery and bounded profiling checks passed\n";
}
