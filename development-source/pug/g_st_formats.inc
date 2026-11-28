// PUG rotation and adjacent-rank Duel scheduling.
#include "st_format_award.h"

static qboolean stAssigning, stAwardStarted;
static int stLastFrame, stLastInput[MAX_CLIENTS], stWarned[MAX_CLIENTS];
static int stNextTeam[MAX_CLIENTS], stNextTicket[MAX_CLIENTS], stPartner[MAX_CLIENTS];
static qboolean stFullMapLoad;
static int stAngles[MAX_CLIENTS][2];

int ST_FormatMode(void) {
    if (st_gameFormat.integer == 1 && level.gametype == GT_TEAM) return 1;
    if (st_gameFormat.integer == 2 && level.gametype == GT_DUEL && !ST_TournamentControlsDuel()) return 2;
    return 0;
}

static int ST_FormatNumber(const char *name) {
    return trap->Cvar_VariableIntegerValue(name);
}

static void ST_FormatNumberSet(const char *name, int value) {
    trap->Cvar_Set(name, va("%d", value));
}

static int ST_NextTicket(void) {
    int ticket = ST_FormatNumber("st_fmtTicket") + 1;
    ST_FormatNumberSet("st_fmtTicket", ticket);
    return ticket;
}

static qboolean ST_OnServer(int slot) {
    return level.clients[slot].pers.connected == CON_CONNECTED;
}

static void ST_Assign(int slot, int team) {
    stAssigning = qtrue;
    SetTeam(&g_entities[slot], (char *)(team == TEAM_FREE ? "free" :
            team == TEAM_SPECTATOR ? "s" : ST_TffaName(team)));
    stAssigning = qfalse;
    stLastInput[slot] = level.time;
    stWarned[slot] = 0;
}

qboolean ST_FormatBlockTeam(int slot, int team) {
    if (!ST_FormatMode() || stAssigning || team == TEAM_SPECTATOR) return qfalse;
    trap->SendServerCommand(slot, ST_FormatMode() == 1 ?
        "print \"Use pug join to enter the queue.\n\"" :
        "print \"Ladder assigns adjacent ranks to the arena.\n\"");
    return qtrue;
}

void ST_FormatLeaving(int slot) {
    if (ST_FormatMode() && level.clients[slot].sess.sessionTeam != TEAM_SPECTATOR) {
        ST_FormatAwardLeave(slot);
    }
}

static int ST_QueueHead(void) {
    int head = -1;
    for (int i=0; i<level.maxclients; ++i) {
        if (!ST_OnServer(i) || level.clients[i].sess.sessionTeam != TEAM_SPECTATOR ||
            !level.clients[i].sess.stQueueTicket) continue;
        if (head < 0 || level.clients[i].sess.stQueueTicket < level.clients[head].sess.stQueueTicket) head = i;
    }
    return head;
}

static void ST_CancelReservation(int slot) {
    if (!stNextTeam[slot]) return;
    stNextTeam[stPartner[slot]]=0;
    stNextTeam[slot]=0;
}

void ST_PugCommand(int slot) {
    char action[32];
    trap->Argv(1,action,sizeof(action));
    clientSession_t *session = &level.clients[slot].sess;
    if (ST_FormatMode() != 1) {
        trap->SendServerCommand(slot,"print \"PUG mode is inactive.\n\"");
        return;
    }
    if ((level.intermissionQueued || level.intermissiontime) && !Q_stricmp(action,"join")) {
        trap->SendServerCommand(slot,"print \"Round complete. Use pug join after the map loads.\n\"");
        return;
    }
    if (!Q_stricmp(action,"join") && session->sessionTeam == TEAM_SPECTATOR && !session->stQueueTicket)
        session->stQueueTicket = ST_NextTicket();
    else if (!Q_stricmp(action,"leave")) {
        ST_CancelReservation(slot);
        session->stQueueTicket = 0;
        if (session->sessionTeam != TEAM_SPECTATOR) ST_Assign(slot,TEAM_SPECTATOR);
    }
    int position = 0;
    if (session->stQueueTicket) {
        for (int i=0; i<level.maxclients; ++i)
            if (ST_OnServer(i) && level.clients[i].sess.stQueueTicket > 0 &&
                level.clients[i].sess.stQueueTicket <= session->stQueueTicket) ++position;
    }
    trap->SendServerCommand(slot, va("print \"PUG: %s. Use pug join, pug leave or pug status.\n\"",
        position ? va("queue position %d",position) : session->sessionTeam == TEAM_SPECTATOR ? "spectating" : "playing"));
}

static int ST_LowestPlayer(int team, qboolean botsOnly) {
    int lowest = -1;
    for (int i=0; i<level.maxclients; ++i) {
        if (!ST_OnServer(i) || level.clients[i].sess.sessionTeam != team ||
           (botsOnly && !(g_entities[i].r.svFlags & SVF_BOT))) continue;
        if (lowest < 0 || level.clients[i].ps.persistant[PERS_SCORE] < level.clients[lowest].ps.persistant[PERS_SCORE] ||
           (level.clients[i].ps.persistant[PERS_SCORE] == level.clients[lowest].ps.persistant[PERS_SCORE] &&
            level.clients[i].sess.stServiceTicket < level.clients[lowest].sess.stServiceTicket)) lowest = i;
    }
    return lowest;
}

static void ST_PugReplace(int team,int outgoing,int incoming) {
    if (outgoing >= 0) {
        ST_Assign(outgoing,TEAM_SPECTATOR);
        if (level.clients[outgoing].sess.sessionTeam != TEAM_SPECTATOR) return;
        if (!(g_entities[outgoing].r.svFlags & SVF_BOT))
            level.clients[outgoing].sess.stQueueTicket = ST_NextTicket();
    }
    ST_Assign(incoming,team);
    if (level.clients[incoming].sess.sessionTeam == team) {
        level.clients[incoming].sess.stQueueTicket = 0;
        level.clients[incoming].sess.stServiceTicket = ST_NextTicket();
    }
}

void ST_PugEnd(void) {
    if (ST_FormatMode()!=1) return;
    int teams=G_TffaTeams(), start=ST_FormatNumber("st_pugRotation") % teams;
    int queued[MAX_CLIENTS], size=0;
    for (int i=0;i<level.maxclients;++i) {
        int ticket=level.clients[i].sess.stQueueTicket;
        if (!ST_OnServer(i) || !ticket || level.clients[i].sess.sessionTeam!=TEAM_SPECTATOR) continue;
        int pos=size++;
        while (pos && level.clients[queued[pos-1]].sess.stQueueTicket>ticket) {
            queued[pos]=queued[pos-1]; --pos;
        }
        queued[pos]=i;
    }
    if (stAwardStarted) ST_FormatAward(1,ST_TffaLeader(level.teamScores,teams),-1);
    stAwardStarted=qfalse;
    int last=start, used=0;
    for (int n=0;n<teams;++n) {
        if (used>=size) break;
        int ordinal=(start+n)%teams, team=ST_TffaTeamAt(ordinal), head=queued[used];
        int low=ST_LowestPlayer(team,qfalse);
        if (low>=0) {
            ++used;
            stPartner[low]=head;
            stPartner[head]=low;
            stNextTeam[low]=TEAM_SPECTATOR;
            stNextTicket[low]=(g_entities[low].r.svFlags & SVF_BOT)?0:ST_NextTicket();
            stNextTeam[head]=team;
            stNextTicket[head]=ST_NextTicket();
            last=(ordinal+1)%teams;
        }
    }
    ST_FormatNumberSet("st_pugRotation",last);
}

// Apply only to the session being saved; keep the completed round scoreboard intact.
void ST_PugSaveRotation(void) {
    for (int i=0;i<level.maxclients;++i) {
        if (!stNextTeam[i] || !ST_OnServer(i)) continue;
        clientSession_t *s=&level.clients[i].sess;
        s->sessionTeam=(team_t)stNextTeam[i];
        s->spectatorState=s->sessionTeam==TEAM_SPECTATOR ? SPECTATOR_FREE : SPECTATOR_NOT;
        s->spectatorClient=0;
        s->stQueueTicket=s->sessionTeam==TEAM_SPECTATOR ? stNextTicket[i] : 0;
        s->stServiceTicket=s->sessionTeam==TEAM_SPECTATOR ? 0 : stNextTicket[i];
        stNextTeam[i]=0;
    }
}
qboolean ST_FormatAssigning(void) { return stAssigning; }

void ST_FormatInput(gclient_t *client) {
    int i=client->ps.clientNum;
    if (i<0 || i>=level.maxclients || &level.clients[i]!=client) return;
    usercmd_t *cmd=&client->pers.cmd;
    // Menu/chat commands suppress gameplay. Walking and ANY can remain set while stationary.
    if (cmd->buttons & BUTTON_TALK) return;
    const int actions=BUTTON_ATTACK|BUTTON_ALT_ATTACK|BUTTON_USE|BUTTON_USE_HOLDABLE|BUTTON_GESTURE|
        BUTTON_FORCEGRIP|BUTTON_FORCEPOWER|BUTTON_FORCE_LIGHTNING|BUTTON_FORCE_DRAIN|BUTTON_BLOCK|BUTTON_FEINT;
    if (cmd->forwardmove || cmd->rightmove || cmd->upmove || (cmd->buttons & actions) ||
        cmd->angles[0]!=stAngles[i][0] || cmd->angles[1]!=stAngles[i][1]) {
        stLastInput[i]=level.time;
        stWarned[i]=0;
    }
    stAngles[i][0]=cmd->angles[0];
    stAngles[i][1]=cmd->angles[1];
}

static void ST_PugFrame(void) {
    int teams=G_TffaTeams(), cap=ST_MatchEffectiveTeamCap();
    if (!cap) cap=4;
    for (int i=0;i<level.maxclients;++i) {
        if (!ST_OnServer(i) || level.clients[i].sess.sessionTeam==TEAM_SPECTATOR || (g_entities[i].r.svFlags & SVF_BOT)) continue;
        if (!stLastInput[i]) stLastInput[i]=level.time;
        int remaining=Com_Clampi(16,86400,st_pugAfkSeconds.integer)*1000-(level.time-stLastInput[i]);
        if (remaining<=0) ST_Assign(i,TEAM_SPECTATOR);
        else if (remaining<=15000 && !stWarned[i]) {
            stWarned[i]=1;
            trap->SendServerCommand(i,"cp \"Move within 15 seconds to keep your PUG place.\"");
        }
    }
    for (int n=0;n<level.maxclients;++n) {
        int head=ST_QueueHead(), team=-1, smallest=cap, bot=-1;
        if (head<0) break;
        for (int t=0;t<teams;++t) {
            int candidate=ST_TffaTeamAt(t), count=TeamCount(-1,(team_t)candidate);
            if (count<smallest && G_TffaHasRoom(candidate,head)) { team=candidate; smallest=count; }
        }
        if (team<0) {
            for (int t=0;t<teams && bot<0;++t) {
                team=ST_TffaTeamAt(t);
                bot=ST_LowestPlayer(team,qtrue);
            }
            if (bot<0) break;
        }
        ST_PugReplace(team,bot,head);
        if (head==ST_QueueHead()) break;
    }
    if (!stAwardStarted && !level.warmupTime) {
        int occupied=0;
        for (int t=0;t<teams;++t) if (TeamCount(-1,(team_t)ST_TffaTeamAt(t))) ++occupied;
        if (occupied>=2) { ST_FormatAwardBegin(1); stAwardStarted=qtrue; }
    }
}


void ST_FormatDisconnect(int slot) {
    ST_FormatLeaving(slot);
    ST_CancelReservation(slot);
    stLastInput[slot]=stWarned[slot]=0;
    int rank=level.clients[slot].sess.stLadderRank;
    if (ST_FormatMode()!=2 || !rank) return;
    int cursor=ST_FormatNumber("st_ladderCursor");
    if (rank<cursor) ST_FormatNumberSet("st_ladderCursor",cursor-1);
    for (int i=0;i<level.maxclients;++i) {
        if (i==slot || level.clients[i].pers.connected==CON_DISCONNECTED) continue;
        if (level.clients[i].sess.stDuelSeriesOpponent==slot) {
            level.stDuelRoundAnnounced=qfalse;
            level.clients[i].sess.stDuelSeriesOpponent=-1;
            level.clients[i].sess.stDuelSeriesWins=0;
            if (level.intermissionQueued && !level.intermissiontime) {
                level.intermissionQueued=0;
                trap->SetConfigstring(CS_INTERMISSION,"0");
            }
            level.clients[i].ps.persistant[PERS_SCORE]=0;
            ST_FormatNumberSet("st_ladderAwardOpen",0);
        }
        if (level.clients[i].sess.stLadderRank>rank) {
            --level.clients[i].sess.stLadderRank;
            if (ST_OnServer(i)) ClientUserinfoChanged(i);
        }
    }
    level.clients[slot].sess.stLadderRank=0;
}

static void ST_LadderFrame(void) {
    int count=0;
    for (int i=0;i<level.maxclients;++i) {
        if (ST_OnServer(i)) ++count;
    }
    int maxRank=0;
    for (int i=0;i<level.maxclients;++i)
        if (level.clients[i].pers.connected!=CON_DISCONNECTED && level.clients[i].sess.stLadderRank>maxRank) maxRank=level.clients[i].sess.stLadderRank;
    for (int i=0;i<level.maxclients;++i) {
        if (ST_OnServer(i) && !level.clients[i].sess.stLadderRank) {
            level.clients[i].sess.stLadderRank=++maxRank;
            ClientUserinfoChanged(i);
        }
    }
    // Skip slow connections while keeping their rank reserved across map loads.
    int order[MAX_CLIENTS], size=0;
    for (int i=0;i<level.maxclients;++i) {
        if (!ST_OnServer(i)) continue;
        int pos=size++;
        while (pos && level.clients[order[pos-1]].sess.stLadderRank>level.clients[i].sess.stLadderRank) {
            order[pos]=order[pos-1]; --pos;
        }
        order[pos]=i;
    }
    if (count<2) {
        if (count && level.clients[order[0]].sess.sessionTeam!=TEAM_SPECTATOR) ST_Assign(order[0],TEAM_SPECTATOR);
        return;
    }
    int cursor=ST_FormatNumber("st_ladderCursor");
    int pos=0;
    while (pos<size && level.clients[order[pos]].sess.stLadderRank<cursor) ++pos;
    if (cursor<1 || pos+1>=size) {
        int nextEven=cursor>0 && !ST_FormatNumber("st_ladderEvenPass") && size>=3;
        ST_FormatNumberSet("st_ladderEvenPass",nextEven);
        pos=nextEven?1:0;
        cursor=level.clients[order[pos]].sess.stLadderRank;
        ST_FormatNumberSet("st_ladderCursor",cursor);
    }
    int a=order[pos], b=order[pos+1];
    // A newly connected spectator cannot displace an active pair midway through its series.
    for (int i=0;i<level.maxclients;++i) {
        if (!ST_OnServer(i) || level.clients[i].sess.sessionTeam!=TEAM_FREE) continue;
        int other=level.clients[i].sess.stDuelSeriesOpponent;
        if (other>=0 && other<level.maxclients && ST_OnServer(other) &&
            level.clients[other].sess.sessionTeam==TEAM_FREE && level.clients[other].sess.stDuelSeriesOpponent==i) {
            a=i; b=other; break;
        }
    }
    for (int i=0;i<level.maxclients;++i)
        if (ST_OnServer(i) && level.clients[i].sess.sessionTeam!=TEAM_SPECTATOR &&
            (b<0 || (i!=a && i!=b))) ST_Assign(i,TEAM_SPECTATOR);
    if (a<0 || b<0) return;
    if (level.clients[a].sess.sessionTeam!=TEAM_FREE) ST_Assign(a,TEAM_FREE);
    if (level.clients[b].sess.sessionTeam!=TEAM_FREE) ST_Assign(b,TEAM_FREE);
    if (!level.warmupTime && !ST_FormatNumber("st_ladderAwardOpen") &&
        level.clients[a].sess.sessionTeam==TEAM_FREE && level.clients[b].sess.sessionTeam==TEAM_FREE) {
        ST_FormatAwardBegin(2);
        ST_FormatNumberSet("st_ladderAwardOpen",1);
    }
}

void ST_LadderResult(int winner,int loser) {
    ST_FormatAward(2,winner,loser);
    ST_FormatNumberSet("st_ladderAwardOpen",0);
    level.clients[winner].sess.stLadderPlayed=level.clients[loser].sess.stLadderPlayed=1;
    int a=level.clients[winner].sess.stLadderRank, b=level.clients[loser].sess.stLadderRank;
    if (a>b) {
        level.clients[winner].sess.stLadderRank=b;
        level.clients[loser].sess.stLadderRank=a;
    }
    ST_FormatNumberSet("st_ladderCursor",(a>b?a:b)+1);
}

void ST_FormatFrame(void) {
    if (!ST_FormatMode() || level.intermissiontime || level.intermissionQueued || level.restarted ||
        level.time<level.startTime+1000 || level.time-stLastFrame<250) return;
    stLastFrame=level.time;
    if (ST_FormatMode()==1) ST_PugFrame();
    else ST_LadderFrame();
}

void ST_FormatConnect(int slot) {
    if (ST_FormatMode()==2 && stFullMapLoad) {
        level.clients[slot].sess.stDuelSeriesOpponent=-1;
        level.clients[slot].sess.stDuelSeriesWins=0;
    }
}

void ST_FormatInit(qboolean restart) {
    stFullMapLoad=!restart;
    if (!restart) ST_FormatNumberSet("st_ladderAwardOpen",0);
    stAwardStarted=qfalse;
    stAssigning=qfalse;
    stLastFrame=0;
    memset(stLastInput,0,sizeof(stLastInput));
    memset(stWarned,0,sizeof(stWarned));
    memset(stNextTeam,0,sizeof(stNextTeam));
    if (ST_FormatMode()!=2) {
        ST_FormatNumberSet("st_ladderEvenPass",0);
        ST_FormatNumberSet("st_ladderCursor",1);
        ST_FormatNumberSet("st_ladderAwardOpen",0);
    }
}
