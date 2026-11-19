/* Bounded local scrimmage capture. GPL-2.0-or-later. Included by g_main.c. */
#include "qcommon/st_mvp_api.h"
#include "qcommon/st_mvp_retention.h"
static stMvpSample_t stMvpFrames[ST_MVP_FRAMES];
static stMvpEvent_t stMvpEvents[ST_MVP_EVENTS];
static stMvpClip_t stMvpFinal;
static int stMvpEventCount, stMvpCount, stMvpBytes, stMvpKillTime;
static int stMvpSlots[ST_MVP_ACTORS], stMvpConnections[ST_MVP_ACTORS], stMvpActorCount;
static int stMvpKills[MAX_CLIENTS], stMvpDeaths[MAX_CLIENTS], stMvpReached[MAX_CLIENTS];
static int stMvpPartSpawn[MAX_GENTITIES], stMvpPartBorn[MAX_GENTITIES];
static int stMvpProofBot = -1, stMvpLimbPeak, stMvpFinalized;
static int stMvpPlaybackDone;
static int stMvpLastDeath, stMvpLastAttacker, stMvpLastVictim, stMvpLastMeans;
static int stMvpForfeitPending, stMvpDecisionTime;
static int stMvpLastSample;
static void ST_MvpNetworkReset(void);
static void ST_MvpNetworkFrame(void);

static qboolean ST_MvpLocalEnabled(void) {
    return trap->Cvar_VariableIntegerValue("st_mvpPrototype")!=0;
}

static void ST_MvpFreeFrame(stMvpSample_t *frame) {
    int i;
    if (!frame->count) return;
    for (i=0; i<frame->count; ++i)
        if (frame->actors[i].pose) trap->G2API_CleanGhoul2Models(&frame->actors[i].pose);
    for (i=0; i<frame->propCount; ++i)
        if (frame->props[i].pose) trap->G2API_CleanGhoul2Models(&frame->props[i].pose);
    stMvpBytes -= frame->bytes;
    --stMvpCount;
    memset(frame,0,sizeof(*frame));
}

void ST_MvpRendererReset(void) {
    int i;
    for (i=0; i<ST_MVP_FRAMES; ++i) ST_MvpFreeFrame(&stMvpFrames[i]);
    stMvpCount = stMvpBytes = stMvpEventCount = stMvpKillTime = stMvpLimbPeak = 0;
    memset(&stMvpFinal,0,sizeof(stMvpFinal));
    stMvpFinalized = 0;
    stMvpPlaybackDone = 0;
    /* Keep match kill totals across video restart; only renderer-owned footage
     * becomes unavailable. A new match uses ST_MvpReset below. */
}

void ST_MvpReset(void) {
    trap->Cvar_Register(NULL,"st_mvpPrototype","1",CVAR_SERVERINFO);
    ST_MvpRendererReset();
    ST_MvpNetworkReset();
    stMvpLastSample=0;
    stMvpActorCount = 0;
    stMvpProofBot = -1;
    stMvpLastDeath=stMvpForfeitPending=stMvpDecisionTime=0;
    memset(stMvpKills,0,sizeof(stMvpKills));
    memset(stMvpDeaths,0,sizeof(stMvpDeaths));
    memset(stMvpReached,0,sizeof(stMvpReached));
    memset(stMvpPartBorn,0,sizeof(stMvpPartBorn));
    for (int i=0;i<ST_MVP_ACTORS;++i) stMvpConnections[i]=-1;
}

static int ST_MvpSceneEligible(int *slots) {
    int i, count = 0;
    if (!ST_MvpLocalEnabled() || level.warmupTime) return 0;
    for (i=0; i<level.maxclients; ++i) {
        gentity_t *ent = &g_entities[i];
        if (!ent->inuse || !ent->client || ent->client->pers.connected != CON_CONNECTED ||
            ent->client->sess.sessionTeam == TEAM_SPECTATOR) continue;
        if (!ent->ghoul2 || count == ST_MVP_ACTORS) continue;
        slots[count++] = i;
    }
    return count >= 2 ? count : 0;
}

void ST_MvpTagPart(int entity, int owner, int spawn) {
    if (entity < 0 || entity >= MAX_GENTITIES || owner < 0 || owner >= MAX_CLIENTS) return;
    stMvpPartSpawn[entity] = spawn;
    stMvpPartBorn[entity] = level.time;
}

static qboolean ST_MvpNeeded(int time) {
    int i;
    if (time >= level.time-4500) return qtrue;
    for (i=0; i<stMvpEventCount; ++i)
        if (time >= stMvpEvents[i].killTime-4500 && time <= stMvpEvents[i].killTime+600) return qtrue;
    return qfalse;
}

static void ST_MvpCollect(void) {
    int i;
    for (i=0; i<ST_MVP_FRAMES; ++i)
        if (stMvpFrames[i].count && !ST_MvpNeeded(stMvpFrames[i].time)) ST_MvpFreeFrame(&stMvpFrames[i]);
}

static int ST_MvpLeader(void) {
    int i,winner=-1;
    for(i=0;i<stMvpActorCount;++i) {
        int slot=stMvpSlots[i];
        if(!stMvpKills[slot])continue;
        if(winner<0 || stMvpKills[slot]>stMvpKills[winner] ||
           (stMvpKills[slot]==stMvpKills[winner] && (stMvpDeaths[slot]<stMvpDeaths[winner] ||
           (stMvpDeaths[slot]==stMvpDeaths[winner] && stMvpReached[slot]<stMvpReached[winner]))))winner=slot;
    }
    return winner;
}

static void ST_MvpDropOldest(void) {
    if (stMvpEventCount) {
        int index=ST_MvpRetireIndex(stMvpEvents,stMvpEventCount,ST_MvpLeader());
        --stMvpEventCount;
        memmove(stMvpEvents+index,stMvpEvents+index+1,(stMvpEventCount-index)*sizeof(stMvpEvents[0]));
    }
    ST_MvpCollect();
}

void ST_MvpCapture(void) {
    int slots[ST_MVP_ACTORS], count, i, j, neededBytes=0,interval;
    stMvpSample_t *frame = NULL;
    if (level.intermissiontime) return;
    count = ST_MvpSceneEligible(slots);
    if (!count) return;
    stMvpActorCount = count;
    for (i=0; i<count; ++i) {
        int models = trap->G2API_Ghoul2Size(g_entities[slots[i]].ghoul2);
        stMvpSlots[i] = slots[i];
        if (stMvpConnections[slots[i]]!=level.clients[slots[i]].pers.connectTime) {
            int slot=slots[i];
            stMvpConnections[slot]=level.clients[slot].pers.connectTime;
            stMvpKills[slot]=stMvpDeaths[slot]=stMvpReached[slot]=0;
            for(j=stMvpEventCount-1;j>=0;--j) if(stMvpEvents[j].attacker==slot || stMvpEvents[j].victim==slot) {
                memmove(stMvpEvents+j,stMvpEvents+j+1,(stMvpEventCount-j-1)*sizeof(stMvpEvents[0])); --stMvpEventCount;
            }
        }
        if (models <= 0) return;
        neededBytes += models*65536;
    }
    /* Keep a full finishing window at every legal player count within the
     * same fixed memory budget. Interpolate sparse samples during playback. */
    interval=Q_max(50,(int)((double)neededBytes*10000/(ST_MVP_MEMORY_LIMIT*0.75)));
    interval=Q_min(interval,ST_MVP_MAX_GAP-50);
    if(stMvpLastSample && level.time-stMvpLastSample<interval) return;
    for (i=0; i<ST_MVP_FRAMES; ++i)
        if (stMvpFrames[i].count && stMvpFrames[i].time == level.time) return;
    ST_MvpCollect();
    while (stMvpEventCount && (stMvpCount == ST_MVP_FRAMES || stMvpBytes+neededBytes > ST_MVP_MEMORY_LIMIT))
        ST_MvpDropOldest();
    if (stMvpCount == ST_MVP_FRAMES || stMvpBytes+neededBytes > ST_MVP_MEMORY_LIMIT) return;
    for (i=0; i<ST_MVP_FRAMES; ++i) if (!stMvpFrames[i].count) { frame=&stMvpFrames[i]; break; }
    if (!frame) return;
    ++stMvpCount;
    frame->time = level.time;
    stMvpLastSample=level.time;
    for (i=0; i<count; ++i) {
        gentity_t *ent = &g_entities[slots[i]];
        stMvpActor_t *actor = &frame->actors[i];
        bladeInfo_t *blade = &ent->client->saber[0].blade[0];
        char info[MAX_INFO_STRING];
        int bytes = trap->G2API_Ghoul2Size(ent->ghoul2)*65536;
        trap->G2API_DuplicateGhoul2Instance(ent->ghoul2,&actor->pose);
        frame->count = i+1;
        if (!actor->pose) { ST_MvpFreeFrame(frame); return; }
        frame->bytes += bytes; stMvpBytes += bytes;
        actor->clientNum = slots[i];
        actor->weapon=ent->client->ps.weapon;
        actor->spawnId = ent->client->ps.persistant[PERS_SPAWN_COUNT];
        VectorCopy(ent->client->ps.origin,actor->origin);
        actor->angles[YAW] = ent->client->ps.viewangles[YAW];
        VectorCopy(ent->modelScale,actor->scale);
        VectorCopy(blade->muzzlePoint,actor->bladeBase);
        VectorCopy(blade->muzzleDir,actor->bladeDir);
        actor->alive = ent->client->ps.pm_type != PM_DEAD;
        actor->bladeLength = !actor->alive || ent->client->ps.saberHolstered ? 0 : blade->lengthMax;
        trap->GetUserinfo(slots[i],info,sizeof(info));
        actor->bladeColor = Com_Clampi(SABER_RED,SABER_PURPLE,atoi(Info_ValueForKey(info,"color1")));
        actor->trailStyle = ent->client->saber[0].trailStyle;
        if (ent->client->ps.saberMove >= LS_NONE && ent->client->ps.saberMove < LS_MOVE_MAX)
            actor->trailDuration = saberMoveData[ent->client->ps.saberMove].trailLength/5.0f;
        actor->strongTrail = BG_SaberInAttack(ent->client->ps.saberMove) || BG_SuperBreakWinAnim(ent->client->ps.torsoAnim);
        if (BG_SuperBreakWinAnim(ent->client->ps.torsoAnim) && actor->trailDuration <= 0) actor->trailDuration=150;
        for(int saber=0;saber<MAX_SABERS;++saber) {
            saberInfo_t *si=&ent->client->saber[saber];
            if(!si->model[0] || ent->client->ps.weapon!=WP_SABER) continue;
            for(int b=0;b<si->numBlades && actor->bladeCount<ST_MVP_BLADES;++b) {
                bladeInfo_t *bi=&si->blade[b];
                stMvpBlade_t *out=&actor->blades[actor->bladeCount++];
                mdxaBone_t bolt; void *pose=actor->pose;
                vec3_t origin,angles,scale; int model=saber+1;
                VectorCopy(actor->origin,origin);VectorCopy(actor->angles,angles);VectorCopy(actor->scale,scale);
                if(saber==0 && ent->client->ps.saberInFlight && ent->client->ps.saberEntityNum>0 &&
                   ent->client->ps.saberEntityNum<level.num_entities) {
                    gentity_t *thrown=&g_entities[ent->client->ps.saberEntityNum];
                    pose=thrown->ghoul2;model=0;VectorCopy(thrown->r.currentOrigin,origin);VectorCopy(thrown->r.currentAngles,angles);
                }
                VectorCopy(bi->muzzlePoint,out->base);VectorCopy(bi->muzzleDir,out->dir);
                if(pose && trap->G2API_GetBoltMatrix(pose,model,b,&bolt,angles,origin,level.time,NULL,scale)) {
                    BG_GiveMeVectorFromMatrix(&bolt,ORIGIN,out->base);BG_GiveMeVectorFromMatrix(&bolt,NEGATIVE_Y,out->dir);
                }
                out->length=actor->alive && ent->client->ps.saberHolstered<2 &&
                    !(ent->client->ps.saberHolstered==1 && (saber || b)) ? bi->lengthMax : 0;
                out->radius=bi->radius;
                out->color=Com_Clampi(SABER_RED,SABER_PURPLE,atoi(Info_ValueForKey(info,saber ? "color2":"color1")));
                if(level.gametype>=GT_TEAM && level.gametype!=GT_SIEGE && !trap->Cvar_VariableIntegerValue("g_jediVmerc"))
                    out->color=ent->client->sess.sessionTeam==TEAM_RED ? SABER_RED:SABER_BLUE;
                out->flags=(si->saberFlags2&SFL2_NO_BLADE ? 1:0)|(si->saberFlags2&SFL2_NO_DLIGHT ? 2:0);
                out->duration=actor->trailDuration;
                out->style=si->trailStyle;out->strong=actor->strongTrail;
            }
        }
    }
    for (i=level.maxclients; i<level.num_entities; ++i) {
        gentity_t *ent = &g_entities[i];
        stMvpLimb_t *part;
        if (!ent->inuse || ent->s.eType != ET_GENERAL || ent->s.weapon != G2_MODEL_PART ||
            ent->s.modelGhoul2 < G2_MODELPART_HEAD || ent->s.modelGhoul2 > G2_MODELPART_RLEG || !stMvpPartBorn[i]) continue;
        for (j=0; j<count; ++j)
            if (slots[j] == ent->s.modelindex && !frame->actors[j].alive &&
                frame->actors[j].spawnId == stMvpPartSpawn[i]) break;
        if (j==count) continue;
        if (frame->limbCount==ST_MVP_LIMBS) continue;
        part=&frame->limbs[frame->limbCount++];
        part->entityNum=i; part->owner=ent->s.modelindex; part->part=ent->s.modelGhoul2;
        VectorCopy(ent->r.currentOrigin,part->origin); VectorCopy(ent->r.currentAngles,part->angles);
    }
    for(i=level.maxclients;i<level.num_entities && frame->propCount<ST_MVP_PROPS;++i) {
        gentity_t *ent=&g_entities[i];stMvpProp_t *p;
        if(!ent->inuse || ent->s.weapon==G2_MODEL_PART || (ent->s.eFlags&EF_NODRAW) ||
           (!ent->s.modelindex && !ent->ghoul2 && ent->s.eType!=ET_MISSILE) ||
           (ent->s.eType!=ET_MOVER && ent->s.eType!=ET_MISSILE && ent->s.eType!=ET_NPC &&
            !(ent->s.eType==ET_GENERAL && ent->ghoul2))) continue;
        p=&frame->props[frame->propCount];
        p->entityNum=i;p->modelIndex=ent->s.modelindex;p->brush=ent->r.bmodel;
        p->type=ent->s.eType;p->weapon=ent->s.weapon;p->flags=ent->s.eFlags;
        VectorCopy(ent->s.pos.trDelta,p->velocity);
        VectorCopy(ent->r.currentOrigin,p->origin);VectorCopy(ent->r.currentAngles,p->angles);VectorCopy(ent->modelScale,p->scale);
        if(ent->ghoul2) {
            int bytes=trap->G2API_Ghoul2Size(ent->ghoul2)*65536;
            if(stMvpBytes+bytes>ST_MVP_MEMORY_LIMIT) continue;
            trap->G2API_DuplicateGhoul2Instance(ent->ghoul2,&p->pose);
            if(p->pose) { frame->bytes+=bytes;stMvpBytes+=bytes; }
        }
        ++frame->propCount;
    }
    if (frame->limbCount > stMvpLimbPeak) {
        stMvpLimbPeak=frame->limbCount;
        if (trap->Cvar_VariableIntegerValue("developer")) trap->Print("MVP_LIMBS captured=%d time=%d\n",stMvpLimbPeak,level.time);
    }
}

void ST_MvpDeath(gentity_t *victim, gentity_t *attacker, int meansOfDeath) {
    int slots[ST_MVP_ACTORS], count,i;
    stMvpEvent_t *event;
    if (!victim || !victim->client || victim->s.number<0 || victim->s.number>=MAX_CLIENTS ||
        level.intermissiontime) return;
    if (ST_MvpLocalEnabled() && level.gametype==GT_DUEL && !level.warmupTime &&
        victim->client->sess.sessionTeam!=TEAM_SPECTATOR) {
        stMvpLastDeath=level.time; stMvpLastVictim=victim->s.number;
        stMvpLastAttacker=attacker && attacker->client ? attacker->s.number : -1;
        stMvpLastMeans=meansOfDeath;
    }
    count = ST_MvpSceneEligible(slots);
    if (!count) return;
    for (i=0; i<count && slots[i]!=victim->s.number; ++i) {}
    if (i==count) return;
    ST_MvpCapture();
    ++stMvpDeaths[victim->s.number];
    if (!attacker || !attacker->client || attacker==victim || attacker->s.number<0 || attacker->s.number>=MAX_CLIENTS) return;
    for (i=0; i<count && slots[i]!=attacker->s.number; ++i) {}
    if (i==count) return;
    if (OnSameTeam(victim,attacker)) return;
    ++stMvpKills[attacker->s.number];
    stMvpReached[attacker->s.number]=level.time;
    if (!stMvpCount) return;
    if (stMvpEventCount==ST_MVP_EVENTS) ST_MvpDropOldest();
    event=&stMvpEvents[stMvpEventCount++];
    memset(event,0,sizeof(*event));
    event->killTime=stMvpKillTime=level.time;
    event->attacker=attacker->s.number; event->victim=victim->s.number;
    if (trap->Cvar_VariableIntegerValue("developer")) trap->Print("MVP_CAPTURE kill=%d winner=%d frames=%d budgetBytes=%d total=%d\n",
        level.time,attacker->s.number,stMvpCount,stMvpBytes,stMvpKills[attacker->s.number]);
}

static void ST_MvpAppendEvent(stMvpEvent_t event) {
    int first=0,last=0,previous=0,j;
    /* Require continuous footage across the finishing interval. */
    for (;;) {
        int next=0;
        for (j=0; j<ST_MVP_FRAMES; ++j) {
            int t=stMvpFrames[j].time;
            if (stMvpFrames[j].count && t>=event.killTime-4500 && t<=event.killTime+600 &&
                t>previous && (!next || t<next)) next=t;
        }
        if (!next) break;
        if (previous && next-previous>ST_MVP_MAX_GAP) first=0;
        if (!first) first=next;
        previous=last=next;
    }
    if (!first || first>event.killTime-188 || last<event.killTime+188) return;
    event.firstTime=first; event.lastTime=last;
    stMvpFinal.events[stMvpFinal.eventCount++]=event;
    if (!stMvpFinal.firstTime || first<stMvpFinal.firstTime) stMvpFinal.firstTime=first;
    if (last>stMvpFinal.lastTime) stMvpFinal.lastTime=last;
    stMvpFinal.killTime=event.killTime;
}

#include "g_st_mvp_duel.inc"

static void ST_MvpFinalize(void) {
    int i,winner=ST_MvpLeader();
    memset(&stMvpFinal,0,sizeof(stMvpFinal));
    stMvpFinalized=1;
    if (winner<0) return;
    stMvpFinal.winner=winner; stMvpFinal.totalKills=stMvpKills[winner];
    stMvpFinal.resultTime=level.intermissiontime;
    stMvpFinal.retainedBytes=stMvpBytes;
    Q_strncpyz(stMvpFinal.name,level.clients[winner].pers.netname,sizeof(stMvpFinal.name));
    for (i=0; i<stMvpEventCount; ++i) {
        stMvpEvent_t event=stMvpEvents[i];
        if (event.attacker!=winner) continue;
        ST_MvpAppendEvent(event);
    }
    stMvpFinal.cardOnly=stMvpFinal.eventCount==0;
    if (trap->Cvar_VariableIntegerValue("developer")) trap->Print("MVP_FINAL winner=%d total=%d clips=%d budgetBytes=%d\n",winner,
        stMvpFinal.totalKills,stMvpFinal.eventCount,stMvpBytes);
}

qboolean ST_MvpRead(int sourceTime, stMvpClip_t *out) {
    int slots[ST_MVP_ACTORS], count,i;
    if (!out || !level.intermissiontime || !ST_MvpLocalEnabled()) return qfalse;
    if (level.gametype==GT_DUEL) {
        if (!stMvpFinalized || !stMvpFinal.resultTime) return qfalse;
    } else {
        if (!stMvpCount) return qfalse;
        if (!stMvpFinalized) ST_MvpFinalize();
    }
    *out=stMvpFinal;
    if (out->cardOnly) return qtrue;
    if (!out->eventCount) return qfalse;
    if (!sourceTime) sourceTime=out->firstTime;
    for (i=0; i<ST_MVP_FRAMES; ++i) {
        const stMvpSample_t *sample=&stMvpFrames[i];
        if (!sample->count) continue;
        if (sample->time<=sourceTime && (!out->before || sample->time>out->before->time)) out->before=sample;
        if (sample->time>=sourceTime && (!out->after || sample->time<out->after->time)) out->after=sample;
    }
    if (!out->before) out->before=out->after;
    if (!out->after) out->after=out->before;
    return out->before && out->after && out->after->time-out->before->time<=ST_MVP_MAX_GAP;
}

#include "g_st_mvp_network.inc"
qboolean ST_MvpHoldIntermission(void) {
    return ST_MvpLocalEnabled() && level.intermissiontime && ST_MvpNetworkHold();
}
