/* Local MVP match capture and candidate-only fixture. GPL-2.0-or-later. */
#include "g_st_mvp_history.inc"
void LogExit(const char *string);

/* Directed bracket fixtures for native adapter checks, never used by launchers.
 * Scores are seeded before play; the deciding point uses real saber damage and
 * the production round controller. */
void ST_MvpWinnerProof(void) {
    int slots[ST_MVP_ACTORS],i,a,b;
    char kind[32],value[16];
    if (!ST_MvpLocalEnabled() || level.gametype!=GT_DUEL || level.intermissiontime ||
        ST_MvpSceneEligible(slots)!=2) return;
    trap->Argv(1,kind,sizeof(kind));
    if (Q_stricmp(kind,"match") && Q_stricmp(kind,"champion") && Q_stricmp(kind,"series")) return;
    a=slots[0]; b=slots[1];
    if (Q_stricmp(kind,"series")) {
        level.stTournamentPhase=ST_TOURNAMENT_RUNNING;
        level.stTournamentRoundSize=!Q_stricmp(kind,"champion") ? 2 : 4;
        level.stTournamentRoundNumber=1; level.stTournamentMatchCursor=0;
        level.stTournamentActiveA=a; level.stTournamentActiveB=b;
        level.stTournamentEntrantCount=4;
        for (i=0;i<ST_TOURNAMENT_MAX_PLAYERS;++i) {
            level.stTournamentRoundSlots[i]=i<4 ? i : -1;
            level.stTournamentEntrants[i]=i<4 ? i : -1;
            level.stTournamentNextSlots[i]=-1;
        }
    }
    level.clients[a].sess.stDuelSeriesOpponent=b;
    level.clients[b].sess.stDuelSeriesOpponent=a;
    trap->Argv(2,value,sizeof(value)); level.clients[a].sess.stDuelSeriesWins=Com_Clampi(0,1,atoi(value));
    trap->Argv(3,value,sizeof(value)); level.clients[b].sess.stDuelSeriesWins=Com_Clampi(0,1,atoi(value));
    trap->Print("WINNER_FIXTURE kind=%s a=%d b=%d score=%d-%d\n",kind,a,b,
        level.clients[a].sess.stDuelSeriesWins,level.clients[b].sess.stDuelSeriesWins);
}
qboolean ST_MvpProofFrozen(int client) {
    return stMvpProofBot >= 0 && client >= 0 && client < level.maxclients &&
        (g_entities[client].r.svFlags & SVF_BOT) && trap->Cvar_VariableIntegerValue("st_mvpPrototype") &&
        (!trap->Cvar_VariableIntegerValue("dedicated") || sv_cheats.integer);
}

/* Candidate-only repeatable setup. Damage still comes from ordinary saber combat. */
void ST_MvpProofSetup(void) {
    int slots[ST_MVP_ACTORS], i, direction, count;
    gentity_t *player, *bot;
    vec3_t angles = {0,0,0}, forward, target;
    trace_t trace;
    if (trap->Argc() > 1) {
        char action[16];trap->Argv(1,action,sizeof(action));
        if(!Q_stricmp(action,"style")) {
            if(!sv_cheats.integer || !trap->Cvar_VariableIntegerValue("developer"))return;
            for(i=0;i<level.maxclients;++i) {
                gentity_t *e=&g_entities[i];playerState_t *p;
                if(!e->inuse || !e->client || (e->r.svFlags&SVF_BOT))continue;
                p=&e->client->ps;
                trap->Print("STYLE_STATUS actor=%d enabled=%d selected=%d active=%d family=%d hand=%d stance=%d torso=%d animStyle=%d attackStyle=%d\n",
                    i,p->stHybrid.enabled,p->stHybrid.selectedStyle,p->stHybrid.style,p->fd.saberAnimLevel,
                    e->client->pers.stHand,(p->stats[STAT_ST_STANCES_B]>>4)&15,p->torsoAnim,STH_AnimStyle(p->torsoAnim),p->stHybrid.attackStyle);
            }
            return;
        }
        if(!Q_stricmp(action,"end") && sv_cheats.integer && stMvpKillTime && !level.intermissiontime) {
            LogExit("MVP boundary fixture");return;
        }
        if(!Q_stricmp(action,"finish") && sv_cheats.integer && stMvpProofBot>=0 && !level.intermissiontime) {
            count=ST_MvpSceneEligible(slots);
            if(count>=2)G_Damage(&g_entities[stMvpProofBot],&g_entities[slots[0]],&g_entities[slots[0]],NULL,NULL,1000,DAMAGE_NO_PROTECTION,MOD_SABER);
            return;
        }
        trap->Print("MVP_STATUS time=%d frames=%d budgetBytes=%d kill=%d\n",level.time,stMvpCount,stMvpBytes,stMvpKillTime);
        for (i=0; i<level.maxclients; ++i) {
            gentity_t *ent = &g_entities[i];
            if (!ent->inuse || !ent->client) continue;
            trap->Print("MVP_STATUS actor=%d health=%d armor=%d move=%d holstered=%d activeForce=%d buttons=%d\n",
                i,ent->health,ent->client->ps.stats[STAT_ARMOR],ent->client->ps.saberMove,
                ent->client->ps.saberHolstered,ent->client->ps.fd.forcePowersActive,ent->client->pers.cmd.buttons);
        }
        return;
    }
    count = ST_MvpSceneEligible(slots);
    if (level.intermissiontime || !count ||
        (g_entities[slots[0]].r.svFlags & SVF_BOT) ||
        !(g_entities[slots[1]].r.svFlags & SVF_BOT)) {
        char info[MAX_INFO_STRING], map[64];
        trap->Cvar_VariableStringBuffer("mapname",map,sizeof(map));
        trap->Print("MVP_FIXTURE unavailable: proto=%d dedicated=%d mode=%d frag=%d warmup=%d map=%s clients=%d intermission=%d\n",
            trap->Cvar_VariableIntegerValue("st_mvpPrototype"),trap->Cvar_VariableIntegerValue("dedicated"),
            level.gametype,fraglimit.integer,level.warmupTime,map,level.maxclients,level.intermissiontime);
        for (i=0; i<level.maxclients; ++i) {
            gentity_t *ent = &g_entities[i];
            if (!ent->inuse || !ent->client) continue;
            trap->GetUserinfo(i,info,sizeof(info));
            trap->Print("MVP_ACTOR slot=%d connected=%d team=%d model=%s ghoul2=%d blades=%d secondary=%s duel=%d thrown=%d\n",
                i,ent->client->pers.connected,ent->client->sess.sessionTeam,Info_ValueForKey(info,"model"),
                ent->ghoul2 ? trap->G2API_Ghoul2Size(ent->ghoul2) : 0,ent->client->saber[0].numBlades,
                ent->client->saber[1].model,ent->client->ps.duelInProgress,ent->client->ps.saberInFlight);
        }
        return;
    }
    player = &g_entities[slots[0]];
    bot = &g_entities[slots[1]];
    if (bot->client->ps.pm_type == PM_DEAD) ClientRespawn(bot);
    for (direction = 0; direction < 4; ++direction) {
        angles[YAW] = direction * 90;
        AngleVectors(angles,forward,NULL,NULL);
        VectorMA(player->client->ps.origin,52,forward,target);
        trap->Trace(&trace,player->client->ps.origin,bot->r.mins,bot->r.maxs,target,
            player->s.number,MASK_SOLID,qfalse,0,0);
        if (!trace.startsolid && trace.fraction == 1) break;
    }
    if (direction == 4) { trap->Print("MVP_FIXTURE unavailable: no clear setup space\n"); return; }
    stMvpProofBot = bot->s.number;
    trap->UnlinkEntity((sharedEntity_t *)bot);
    G_SetOrigin(bot,target);
    VectorCopy(target,bot->client->ps.origin);
    SetClientViewAngle(player,angles);
    angles[YAW] += 180;
    SetClientViewAngle(bot,angles);
    for (i = 0; i < count; ++i) {
        gentity_t *ent = &g_entities[slots[i]];
        VectorClear(ent->client->ps.velocity);
        ent->client->ps.weapon = WP_SABER;
        ent->client->ps.stats[STAT_WEAPONS] |= 1 << WP_SABER;
        ent->health = ent->client->ps.stats[STAT_HEALTH] = i == 0 ? 100 : (level.gametype==GT_DUEL ? 3 : 10);
        ent->client->ps.stats[STAT_ARMOR] = 0;
        ent->client->stShieldRegenDelayEnd = level.time + 60000;
        ent->client->ps.eFlags &= ~EF_INVULNERABLE;
        ent->client->invulnerableTimer = 0;
        ent->client->ps.saberHolstered = i == 0 ? 0 : 2;
    }
    trap->LinkEntity((sharedEntity_t *)bot);
    trap->Print("MVP_FIXTURE ready player=%d bot=%d at=%.1f %.1f %.1f; attack to finish\n",
        slots[0],slots[1],target[0],target[1],target[2]);
}
