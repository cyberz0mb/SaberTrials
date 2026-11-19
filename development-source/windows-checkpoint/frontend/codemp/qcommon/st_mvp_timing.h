/* Saber Trials MVP playback timing. GPL-2.0-or-later. */
#ifndef ST_MVP_TIMING_H
#define ST_MVP_TIMING_H
#define ST_MVP_PLAYBACK_MS 4500
#define ST_MVP_CONTACT_MS 3250
#define ST_MVP_APPROACH_SPEED 1.5

/* Integral of a smoothstep speed ramp, in source milliseconds. */
static double ST_MvpRamp(double t, double duration, double from, double to) {
    double u = t / duration;
    return from * t + (to - from) * duration * (u*u*u - 0.5*u*u*u*u);
}

static double ST_MvpSourceOffset(int elapsedMs) {
    double t = elapsedMs;
    double source;
    double fast = ST_MVP_APPROACH_SPEED;
    double accelDistance = 500 * (1 + fast) * .5;
    double rampStart = accelDistance + 750 * fast;
    double slowStart = rampStart + 1250 * (fast + .25) * .5;
    if (t < 0) t = 0;
    if (t > ST_MVP_PLAYBACK_MS) t = ST_MVP_PLAYBACK_MS;
    if (t <= 500) source = ST_MvpRamp(t, 500, 1, fast);
    // Begin easing 250 ms earlier, keeping contact and the slow interval fixed.
    else if (t <= 1250) source = accelDistance + (t - 500) * fast;
    else if (t <= 2500) source = rampStart + ST_MvpRamp(t - 1250, 1250, fast, 0.25);
    else if (t <= 4000) source = slowStart + (t - 2500) * 0.25;
    else source = slowStart + 375 + ST_MvpRamp(t - 4000, 500, 0.25, 1);
    return source - slowStart - 187.5;
}
#endif
