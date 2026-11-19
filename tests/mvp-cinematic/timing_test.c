#include <math.h>
#include <stdio.h>
#include "st_mvp_timing.h"

/* Catch discontinuities, reverse time and a misplaced finishing contact. */
int main(void) {
    int t;
    double previous = ST_MvpSourceOffset(0);
    if (fabs(ST_MvpSourceOffset(3250)) > 0.001) return 1;
    if (fabs(previous + 3031.25) > 0.001) return 2;
    if (fabs(ST_MvpSourceOffset(4500) - 500.0) > 0.001) return 3;
    if (ST_MvpSourceOffset(-100) != previous) return 4;
    if (ST_MvpSourceOffset(20000) != ST_MvpSourceOffset(4500)) return 5;
    for (t = 1; t <= 4500; ++t) {
        double current = ST_MvpSourceOffset(t);
        if (current <= previous || current - previous > 1.501) return 6;
        previous = current;
    }
    if (fabs(ST_MvpSourceOffset(4000) - ST_MvpSourceOffset(2500) - 375.0) > .001) return 7;
    puts("MVP timing passed: continuous, monotone, 1.5-second slow interval, bounded playback.");
    return 0;
}
