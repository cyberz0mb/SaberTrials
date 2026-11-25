/* Server-side pursuit and local recovery for Berserkers. GPL-2.0.
 * The map's waypoint routes still handle doors, lifts and Force jumps. A
 * shortcut replaces them only after sweeping a player-sized safe corridor.
 */

int PassStandardEnemyChecks(bot_state_t *bs, gentity_t *enemy);
float TotalTrailDistance(int start, int end, bot_state_t *bs);

enum {
    ST_BNAV_ROUTE, ST_BNAV_PURSUIT, ST_BNAV_DROP,
    ST_BNAV_RECOVER, ST_BNAV_HOP, ST_BNAV_COMBAT
};

static qboolean ST_BerserkerActive(bot_state_t *bs) {
    gentity_t *self = &g_entities[bs->client];
    playerState_t *ps;
    if (!self->inuse || !self->client) return qfalse;
    ps = &self->client->ps;
    return self->inuse && self->health > 0 && ps->stats[STAT_HEALTH] > 0 &&
        self->client->pers.connected == CON_CONNECTED && ps->pm_type == PM_NORMAL &&
        self->client->sess.sessionTeam != TEAM_SPECTATOR &&
        ST_BotEffectiveRole(bs) == ST_BOT_ROLE_BERSERKER &&
        !ps->duelInProgress && !ps->m_iVehicleNum && !ps->emplacedIndex &&
        !level.intermissiontime && !level.intermissionQueued && !gDeactivated &&
        !bot_forgimmick.integer && !ST_MvpProofFrozen(bs->client) &&
        !bs->forceMove_Forward && !bs->forceMove_Right && !bs->forceMove_Up;
}

static qboolean ST_BerserkerEnemy(bot_state_t *bs, int number) {
    gentity_t *enemy;
    if (number < 0 || number >= level.maxclients || number == bs->client) return qfalse;
    enemy = &g_entities[number];
    return enemy->inuse && enemy->client &&
        enemy->client->pers.connected == CON_CONNECTED &&
        enemy->client->ps.stats[STAT_HEALTH] > 0 && !BotMindTricked(bs->client, number) &&
        PassStandardEnemyChecks(bs, enemy);
}

static qboolean ST_BerserkerVisible(bot_state_t *bs, gentity_t *enemy) {
    vec3_t eye;
    VectorCopy(enemy->client->ps.origin, eye);
    eye[2] += enemy->client->ps.viewheight * 0.75f;
    return OrgVisible(bs->eye, eye, bs->client) ? qtrue : qfalse;
}

static void ST_BerserkerReset(bot_state_t *bs) {
    stBerserkerNav_t *nav = &bs->stBerserker;
    memset(nav, 0, sizeof(*nav));
    nav->target = nav->targetWaypoint = nav->avoidWaypoint = -1;
}

/* A solid floor can still be a lava pool or sit inside a death trigger.
 * Check the actual player volume rather than assuming solid == survivable.
 */
static qboolean ST_BerserkerHazard(bot_state_t *bs, const vec3_t origin) {
    gentity_t *self = &g_entities[bs->client];
    vec3_t mins, maxs, feet;
    int list[MAX_GENTITIES], count, i;
    VectorAdd(origin, self->r.mins, mins);
    VectorAdd(origin, self->r.maxs, maxs);
    VectorCopy(origin, feet);
    feet[2] += self->r.mins[2] + 4;
    if (trap->PointContents(feet, bs->client) & (CONTENTS_LAVA|CONTENTS_SLIME|CONTENTS_NODROP))
        return qtrue;
    count = trap->EntitiesInBox(mins, maxs, list, MAX_GENTITIES);
    for (i = 0; i < count; i++) {
        gentity_t *hit = &g_entities[list[i]];
        if (hit->inuse && (hit->r.contents & CONTENTS_TRIGGER) && hit->classname &&
            !Q_stricmp(hit->classname, "trigger_hurt") && hit->damage > 0 &&
            trap->EntityContact(mins, maxs, (sharedEntity_t *)hit, qfalse)) return qtrue;
    }
    return qfalse;
}

static qboolean ST_BerserkerFloor(bot_state_t *bs, const vec3_t start,
    float depth, vec3_t floor) {
    gentity_t *self = &g_entities[bs->client];
    trace_t tr;
    vec3_t end;
    VectorCopy(start, end);
    end[2] -= depth;
    trap->Trace(&tr, start, self->r.mins, self->r.maxs, end, bs->client,
        MASK_PLAYERSOLID, qfalse, 0, 0);
    if (tr.startsolid || tr.allsolid || tr.fraction == 1.0f || tr.plane.normal[2] < 0.7f)
        return qfalse;
    if (tr.entityNum < level.maxclients) return qfalse; // another player is not a landing
    VectorCopy(tr.endpos, floor);
    /* Check the descent, including hurt triggers suspended above a solid floor. */
    VectorCopy(start, end);
    while (end[2] > floor[2]) {
        if (ST_BerserkerHazard(bs, end)) return qfalse;
        end[2] -= 32;
    }
    return !ST_BerserkerHazard(bs, floor);
}

/* Follow the ground in <=32-unit increments with a full standing hull. This
 * rejects walls, head obstructions, steep slopes, gaps and excessive drops.
 * A lower floor is accepted only when the whole route reaches the goal's
 * floor, so a target under a roof does not lure the bot onto that roof.
 */
static qboolean ST_BerserkerPath(bot_state_t *bs, const vec3_t goal,
    qboolean allowDrop, vec3_t landing, qboolean *drops) {
    gentity_t *self = &g_entities[bs->client];
    trace_t tr;
    vec3_t direction, cursor, from, to, next;
    float distance, along, maxDrop;
    *drops = qfalse;
    VectorSubtract(goal, bs->origin, direction);
    direction[2] = 0;
    distance = VectorNormalize(direction);
    if (distance < 8 || distance > 768) return qfalse;
    maxDrop = allowDrop ? ((dmflags.integer & DF_NO_FALLING) ? 512.0f : 96.0f) : 48.0f;
    VectorCopy(bs->origin, cursor);
    for (along = 32; ; along += 32) {
        float step = along < distance ? along : distance;
        VectorCopy(cursor, from);
        from[2] += 18;
        /* Check the upward step too: never sweep out of a low ceiling. */
        trap->Trace(&tr, cursor, self->r.mins, self->r.maxs, from, bs->client,
            MASK_PLAYERSOLID, qfalse, 0, 0);
        if (tr.startsolid || tr.allsolid || tr.fraction < 1.0f) return qfalse;
        VectorMA(bs->origin, step, direction, to);
        to[2] = from[2];
        trap->Trace(&tr, from, self->r.mins, self->r.maxs, to, bs->client,
            MASK_PLAYERSOLID, qfalse, 0, 0);
        if (tr.startsolid || tr.allsolid || tr.fraction < 1.0f) return qfalse;
        if (!ST_BerserkerFloor(bs, to, maxDrop + 18, next)) return qfalse;
        if (bs->origin[2] - next[2] > maxDrop || ST_BerserkerHazard(bs, to)) return qfalse;
        if (cursor[2] - next[2] > 48) {
            /* Do not aim a long drop at an elevator which can move away. */
            trace_t support;
            vec3_t below;
            VectorCopy(next, below); below[2] -= 4;
            trap->Trace(&support, next, self->r.mins, self->r.maxs, below, bs->client,
                MASK_PLAYERSOLID, qfalse, 0, 0);
            if (support.entityNum < ENTITYNUM_WORLD &&
                g_entities[support.entityNum].s.eType == ET_MOVER) return qfalse;
            *drops = qtrue;
        }
        VectorCopy(next, cursor);
        if (along >= distance) break;
    }
    if (fabsf(cursor[2] - goal[2]) > 64) return qfalse;
    VectorCopy(cursor, landing);
    return qtrue;
}

static void ST_BerserkerSense(bot_state_t *bs) {
    stBerserkerNav_t *nav = &bs->stBerserker;
    float scores[MAX_CLIENTS];
    int candidates[MAX_CLIENTS], count = 0, i, attempt;
    if (level.time < nav->senseAt && ST_BerserkerEnemy(bs, nav->target)) return;
    nav->senseAt = level.time + 800 + (bs->client % 5) * 35;
    for (i = 0; i < level.maxclients; i++) {
        vec3_t delta;
        float score;
        int place;
        if (!ST_BerserkerEnemy(bs, i)) continue;
        VectorSubtract(g_entities[i].client->ps.origin, bs->origin, delta);
        score = VectorLength(delta) + fabsf(delta[2]) * 1.5f;
        if (!ST_BerserkerVisible(bs, &g_entities[i])) score += 512;
        if (i == nav->target) score *= 0.72f; // retain a useful target instead of oscillating
        for (place = count; place > 0 && scores[place-1] > score; place--) {
            scores[place] = scores[place-1]; candidates[place] = candidates[place-1];
        }
        scores[place] = score; candidates[place] = i; count++;
    }
    nav->target = nav->targetWaypoint = -1;
    /* Bound route queries; visible nearby threats need no waypoint route. */
    for (attempt = 0; attempt < count && attempt < 4; attempt++) {
        gentity_t *enemy = &g_entities[candidates[attempt]];
        int wp = GetNearestVisibleWP(enemy->client->ps.origin, enemy->s.number);
        qboolean route = wp >= 0 && wp < gWPNum && gWPArray[wp] && gWPArray[wp]->inuse;
        if (route && bs->wpCurrent)
            route = TotalTrailDistance(bs->wpCurrent->index, wp, bs) >= 0;
        if (!route && !ST_BerserkerVisible(bs, enemy)) continue;
        nav->target = enemy->s.number;
        nav->targetWaypoint = route ? wp : -1;
        break;
    }
    if (ST_BerserkerEnemy(bs, nav->target)) {
        gentity_t *enemy = &g_entities[nav->target];
        if (ST_BerserkerVisible(bs, enemy)) {
            bs->currentEnemy = enemy;
            bs->enemySeenTime = level.time + ENEMY_FORGET_MS;
        }
    }
}

static void ST_BerserkerPrepare(bot_state_t *bs) {
    stBerserkerNav_t *nav = &bs->stBerserker;
    if (!ST_BerserkerActive(bs)) { ST_BerserkerReset(bs); return; }
    if (!nav->initialized || nav->spawnCount != bs->cur_ps.persistant[PERS_SPAWN_COUNT]) {
        ST_BerserkerReset(bs);
        nav->initialized = qtrue;
        nav->spawnCount = bs->cur_ps.persistant[PERS_SPAWN_COUNT];
        nav->progressAt = level.time;
        VectorCopy(bs->origin, nav->progressOrigin);
    }
    bs->wpCamping = bs->wpCampingTo = NULL;
    bs->isCamping = 0;
    ST_BerserkerSense(bs);
}

/* Called after the stock hazard/objective priorities in GetIdealDestination. */
static qboolean ST_BerserkerDestination(bot_state_t *bs) {
    stBerserkerNav_t *nav = &bs->stBerserker;
    int wp = nav->targetWaypoint;
    if (!ST_BerserkerActive(bs) || !ST_BerserkerEnemy(bs, nav->target) || !bs->wpCurrent ||
        wp < 0 || wp >= gWPNum || !gWPArray[wp] || !gWPArray[wp]->inuse ||
        TotalTrailDistance(bs->wpCurrent->index, wp, bs) < 0) return qfalse;
    bs->wpDestination = gWPArray[wp];
    bs->wpDestSwitchTime = level.time + 1000;
    bs->destinationGrabTime = level.time + 800;
    return qtrue;
}

static int ST_BerserkerWaypoint(bot_state_t *bs, int waypoint) {
    stBerserkerNav_t *nav = &bs->stBerserker;
    if (ST_BerserkerActive(bs) && level.time < nav->avoidUntil && waypoint == nav->avoidWaypoint)
        return -1;
    return waypoint;
}

static qboolean ST_BerserkerLiftMoving(bot_state_t *bs) {
    int ground = bs->cur_ps.groundEntityNum;
    if (ground < 0 || ground >= ENTITYNUM_WORLD) return qfalse;
    return g_entities[ground].s.eType == ET_MOVER &&
        (g_entities[ground].moverState == MOVER_1TO2 || g_entities[ground].moverState == MOVER_2TO1);
}

static void ST_BerserkerRepath(bot_state_t *bs) {
    stBerserkerNav_t *nav = &bs->stBerserker;
    int i, best = -1;
    float bestScore = 99999999;
    vec3_t landing;
    qboolean drops;
    nav->avoidWaypoint = bs->wpCurrent ? bs->wpCurrent->index : -1;
    nav->avoidUntil = level.time + 6000;
    for (i = 0; i < gWPNum; i++) {
        vec3_t delta;
        float distance, route = 0, score;
        if (i == nav->avoidWaypoint || !gWPArray[i] || !gWPArray[i]->inuse) continue;
        VectorSubtract(gWPArray[i]->origin, bs->origin, delta);
        distance = VectorLength(delta);
        if (distance < 48 || distance > 256 || fabsf(delta[2]) > 48) continue;
        if (nav->targetWaypoint >= 0) {
            route = TotalTrailDistance(i, nav->targetWaypoint, bs);
            if (route < 0) continue;
        }
        score = distance + route * 0.15f;
        if (score >= bestScore || !ST_BerserkerPath(bs, gWPArray[i]->origin, qfalse, landing, &drops))
            continue;
        best = i; bestScore = score;
    }
    bs->wpCurrent = best >= 0 ? gWPArray[best] : NULL;
    bs->wpDestination = NULL;
    bs->wpDestIgnoreTime = bs->wpDestSwitchTime = bs->destinationGrabTime = 0;
    bs->wpSeenTime = level.time + 1500;
    bs->wpTravelTime = level.time + 8000;
    nav->senseAt = 0;
    nav->reroutes++;
    ST_BerserkerDestination(bs);
}

static qboolean ST_BerserkerHop(bot_state_t *bs, const vec3_t direction, vec3_t landing) {
    gentity_t *self = &g_entities[bs->client];
    trace_t tr;
    vec3_t top, end;
    /* Stay below an ordinary jump's apex; this recovery is not a charged jump. */
    VectorCopy(bs->origin, top); top[2] += 28;
    trap->Trace(&tr, bs->origin, self->r.mins, self->r.maxs, top, bs->client,
        MASK_PLAYERSOLID, qfalse, 0, 0);
    if (tr.startsolid || tr.allsolid || tr.fraction < 1.0f) return qfalse;
    VectorMA(top, 80, direction, end);
    trap->Trace(&tr, top, self->r.mins, self->r.maxs, end, bs->client,
        MASK_PLAYERSOLID, qfalse, 0, 0);
    if (tr.startsolid || tr.allsolid || tr.fraction < 1.0f ||
        ST_BerserkerHazard(bs, top) || ST_BerserkerHazard(bs, end) ||
        !ST_BerserkerFloor(bs, end, 76, landing)) return qfalse;
    return landing[2] - bs->origin[2] <= 20;
}

static qboolean ST_BerserkerRecover(bot_state_t *bs, const vec3_t goal) {
    static const float offsets[] = {45, -45, 90, -90, 135, -135, 180};
    stBerserkerNav_t *nav = &bs->stBerserker;
    vec3_t toward, angles, direction, probe, landing, best;
    float bestScore = 99999999;
    qboolean found = qfalse, drops;
    int i;
    VectorSubtract(goal, bs->origin, toward); toward[2] = 0;
    if (VectorNormalize(toward) < 0.1f) {
        VectorSet(angles, 0, bs->viewangles[YAW], 0);
        AngleVectors(angles, toward, NULL, NULL);
    }
    vectoangles(toward, angles);
    for (i = 0; i < ARRAY_LEN(offsets); i++) {
        vec3_t difference;
        float score;
        vec3_t turn = {0, 0, 0};
        turn[YAW] = angles[YAW] + offsets[i] * ((bs->client & 1) ? 1 : -1);
        AngleVectors(turn, direction, NULL, NULL);
        VectorMA(bs->origin, 112, direction, probe);
        if (!ST_BerserkerPath(bs, probe, qfalse, landing, &drops)) continue;
        VectorSubtract(goal, landing, difference);
        score = VectorLength(difference) + fabsf(offsets[i]) * 0.25f;
        if (score < bestScore) { bestScore = score; VectorCopy(landing, best); found = qtrue; }
    }
    if (found) {
        VectorCopy(best, nav->moveGoal);
        nav->mode = ST_BNAV_RECOVER;
    } else if (level.time >= nav->jumpAgainAt && !(bs->cur_ps.pm_flags & PMF_JUMP_HELD) &&
        ST_BerserkerHop(bs, toward, landing)) {
        VectorCopy(landing, nav->moveGoal);
        nav->mode = ST_BNAV_HOP;
        nav->jumpUntil = level.time + 150;
        nav->jumpAgainAt = level.time + 1800;
    } else return qfalse;
    nav->recoveryUntil = level.time + 850;
    nav->recoveries++;
    return qtrue;
}

/* Runs after stock AI, before converting its movement to a user command. */
static void ST_BerserkerNavigate(bot_state_t *bs) {
    stBerserkerNav_t *nav = &bs->stBerserker;
    vec3_t delta, goal, landing;
    qboolean drops, hasTarget;
    int previousMode = nav->mode;
    if (!ST_BerserkerActive(bs)) { ST_BerserkerReset(bs); return; }
    if (bs->cur_ps.pm_flags & PMF_TIME_KNOCKBACK) { nav->mode = ST_BNAV_ROUTE; return; }
    if (bs->forceJumping > level.time || bs->jumpHoldTime > level.time) {
        nav->mode = ST_BNAV_ROUTE;
        return;
    }
#ifndef FORCEJUMP_INSTANTMETHOD
    if (bs->forceJumpChargeTime > level.time) { nav->mode = ST_BNAV_ROUTE; return; }
#endif
    /* Do not replace combat footwork or an authored airborne Force jump. */
    if (bs->currentEnemy && ST_BerserkerEnemy(bs, bs->currentEnemy->s.number) &&
        bs->frame_Enemy_Vis && bs->frame_Enemy_Len < 150 &&
        fabsf(bs->currentEnemy->client->ps.origin[2] - bs->origin[2]) < 64) {
        nav->mode = ST_BNAV_COMBAT;
        nav->recoveryUntil = 0;
        nav->progressAt = level.time; VectorCopy(bs->origin, nav->progressOrigin);
        return;
    }
    if (bs->cur_ps.groundEntityNum == ENTITYNUM_NONE) return;
    if (level.time < nav->steerAt) return;
    nav->steerAt = level.time + 200;
    VectorSubtract(bs->origin, nav->progressOrigin, delta);
    if (VectorLengthSquared(delta) >= 48*48 || ST_BerserkerLiftMoving(bs)) {
        nav->progressAt = level.time; VectorCopy(bs->origin, nav->progressOrigin);
    }
    if (nav->recoveryUntil > level.time) {
        VectorSubtract(nav->moveGoal, bs->origin, delta);
        if (VectorLengthSquared(delta) > 24*24 &&
            ST_BerserkerPath(bs, nav->moveGoal, qfalse, landing, &drops)) return;
        nav->recoveryUntil = 0;
    }
    nav->mode = ST_BNAV_ROUTE;
    hasTarget = ST_BerserkerEnemy(bs, nav->target);
    if (hasTarget) VectorCopy(g_entities[nav->target].client->ps.origin, goal);
    else VectorCopy(bs->goalPosition, goal);
    /* A direct pursuit can safely leave a ledge instead of waiting for a lift. */
    if (ST_BerserkerPath(bs, goal, goal[2] < bs->origin[2] - 48, landing, &drops)) {
        VectorCopy(landing, nav->moveGoal);
        nav->mode = drops ? ST_BNAV_DROP : ST_BNAV_PURSUIT;
        if (drops && previousMode != ST_BNAV_DROP) nav->drops++;
    }
    if (level.time - nav->progressAt >= 1800 && !ST_BerserkerLiftMoving(bs)) {
        ST_BerserkerRepath(bs);
        /* Use the route direction around walls, not the enemy behind the wall. */
        if (bs->wpCurrent) VectorCopy(bs->wpCurrent->origin, goal);
        ST_BerserkerRecover(bs, goal);
        nav->progressAt = level.time; VectorCopy(bs->origin, nav->progressOrigin);
    }
    if (nav->mode != ST_BNAV_ROUTE &&
        (!bs->currentEnemy || !bs->frame_Enemy_Vis)) {
        VectorSubtract(nav->moveGoal, bs->origin, delta);
        vectoangles(delta, bs->goalAngles);
        VectorCopy(bs->goalAngles, bs->ideal_viewangles);
    }
}

static void ST_BerserkerCommand(bot_state_t *bs, usercmd_t *cmd) {
    stBerserkerNav_t *nav = &bs->stBerserker;
    vec3_t direction, angles, forward, right;
    float f, r, scale;
    cmd->buttons &= ~BUTTON_WALKING;
    if (!ST_BerserkerActive(bs) || nav->mode == ST_BNAV_ROUTE || nav->mode == ST_BNAV_COMBAT ||
        (bs->cur_ps.pm_flags & PMF_TIME_KNOCKBACK)) return;
    VectorSubtract(nav->moveGoal, g_entities[bs->client].client->ps.origin, direction);
    direction[2] = 0;
    if (VectorNormalize(direction) < 12) return;
    VectorSet(angles, 0, SHORT2ANGLE(cmd->angles[YAW] + bs->cur_ps.delta_angles[YAW]), 0);
    AngleVectors(angles, forward, right, NULL);
    f = DotProduct(direction, forward); r = DotProduct(direction, right);
    scale = fmaxf(fabsf(f), fabsf(r));
    if (scale < 0.01f) return;
    cmd->forwardmove = (signed char)(127 * f / scale);
    cmd->rightmove = (signed char)(127 * r / scale);
    /* One short hop; do not accidentally hold a Force jump over a drop. */
    cmd->upmove = nav->jumpUntil > level.time ? 127 : 0;
}

void Svcmd_STBotNav_f(void) {
    static const char *modes[] = {"waypoints", "pursuit", "safe-drop", "detour", "hop", "combat"};
    int i;
    trap->Print("Berserker pursuit/navigation (server):\n");
    for (i = 0; i < level.maxclients; i++) {
        bot_state_t *bs = botstates[i];
        stBerserkerNav_t *nav;
        if (!bs || !bs->inuse || !g_entities[i].client ||
            g_entities[i].client->pers.stBotRole != ST_BOT_ROLE_BERSERKER) continue;
        nav = &bs->stBerserker;
        trap->Print("  %2i %s^7 mode=%s target=%i wp=%i recoveries=%i reroutes=%i drops=%i\n",
            i, g_entities[i].client->pers.netname, modes[Com_Clampi(0, 5, nav->mode)],
            nav->target, bs->wpCurrent ? bs->wpCurrent->index : -1,
            nav->recoveries, nav->reroutes, nav->drops);
    }
}
