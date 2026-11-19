// Opt-in wall-clock measurements of client work and frame intervals, never simulation time.
#include "st_frame_stats.h"
#include <chrono>
using STProfileClock = std::chrono::steady_clock;
static STProfileClock::time_point stProfileStart, stProfileLast;
static STFrameStats stClientWork, stFrameIntervals;
static int stProfileTarget;
static bool stProfileSampling;
static void ST_FrameProfileBegin() {
    auto setting = Cvar_Get("st_profileFrames","0",CVAR_TEMP,"Record 1-6000 client frame-time samples");
    const int target = std::max(0,std::min(6000,setting->integer));
    stProfileSampling = target > 0;
    if (!stProfileSampling) { stProfileTarget=0; return; }
    stProfileStart = STProfileClock::now();
    if (target != stProfileTarget) {
        stProfileTarget=target; stClientWork.clear(); stFrameIntervals.clear();
    } else {
        stFrameIntervals.add(std::chrono::duration<double,std::milli>(stProfileStart-stProfileLast).count());
    }
    stProfileLast=stProfileStart;
}
static void ST_FrameProfileEnd() {
    if (!stProfileSampling) return;
    stClientWork.add(std::chrono::duration<double,std::milli>(STProfileClock::now()-stProfileStart).count());
    if ((int)stClientWork.values.size() < stProfileTarget) return;
    Com_Printf("ST_FRAME_PROFILE frames=%d work_mean_ms=%.4f work_p95_ms=%.4f interval_mean_ms=%.4f interval_p95_ms=%.4f interval_p99_ms=%.4f fps=%.2f\n",
        stProfileTarget,stClientWork.mean(),stClientWork.percentile(.95),stFrameIntervals.mean(),
        stFrameIntervals.percentile(.95),stFrameIntervals.percentile(.99),
        stFrameIntervals.mean()>0?1000.0/stFrameIntervals.mean():0);
    Cvar_Set("st_profileFrames","0"); stProfileTarget=0; stProfileSampling=false;
}
