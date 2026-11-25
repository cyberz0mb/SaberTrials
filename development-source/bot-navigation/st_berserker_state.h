/* Saber Trials Berserker navigation state. GPL-2.0; see LICENSE.txt. */
#ifndef ST_BERSERKER_STATE_H
#define ST_BERSERKER_STATE_H

typedef struct {
    qboolean initialized;
    int spawnCount;
    int target;
    int targetWaypoint;
    int senseAt;
    int steerAt;
    int progressAt;
    int recoveryUntil;
    int jumpUntil;
    int jumpAgainAt;
    int avoidWaypoint;
    int avoidUntil;
    int mode;
    int recoveries;
    int reroutes;
    int drops;
    vec3_t progressOrigin;
    vec3_t moveGoal;
} stBerserkerNav_t;

#endif
