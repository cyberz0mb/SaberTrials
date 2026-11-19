/* Freeze the actual Duel/controller result before rotation resets its score. */
static void ST_MvpWinnerResult(int winner,int loser,qboolean forfeit) {
    int i;
    qboolean series=ST_DuelBestOfEnabled();
    memset(&stMvpFinal,0,sizeof(stMvpFinal));
    stMvpFinalized=1; stMvpPlaybackDone=0;
    stMvpFinal.resultTime=level.time;
    stMvpFinal.winner=winner;
    stMvpFinal.presentation=level.stTournamentPhase==ST_TOURNAMENT_RUNNING ?
        (level.stTournamentRoundSize==2 ? ST_MVP_PRESENT_CHAMPION : ST_MVP_PRESENT_MATCH) : ST_MVP_PRESENT_DUEL;
    stMvpFinal.winnerScore=series ? level.clients[winner].sess.stDuelSeriesWins : level.clients[winner].ps.persistant[PERS_SCORE];
    stMvpFinal.loserScore=series ? level.clients[loser].sess.stDuelSeriesWins : level.clients[loser].ps.persistant[PERS_SCORE];
    stMvpFinal.forfeit=forfeit;
    Q_strncpyz(stMvpFinal.name,level.clients[winner].pers.netname,sizeof(stMvpFinal.name));
    // A timeout, suicide, environmental finish or forfeit must never replay an
    // earlier kill as though it decided this match.
    if (!forfeit && stMvpLastAttacker==winner &&
        stMvpLastVictim==loser && stMvpDecisionTime>=stMvpLastDeath &&
        stMvpDecisionTime-stMvpLastDeath<=100) {
        for (i=stMvpEventCount-1;i>=0;--i) {
            if (stMvpEvents[i].killTime==stMvpLastDeath && stMvpEvents[i].attacker==winner &&
                stMvpEvents[i].victim==loser) { ST_MvpAppendEvent(stMvpEvents[i]); break; }
        }
    }
    stMvpFinal.cardOnly=stMvpFinal.eventCount==0;
    stMvpFinal.retainedBytes=stMvpBytes;
    if (trap->Cvar_VariableIntegerValue("developer")) trap->Print("WINNER_FINAL kind=%d winner=%d loser=%d score=%d-%d card=%d forfeit=%d clips=%d\n",
        stMvpFinal.presentation,winner,loser,stMvpFinal.winnerScore,stMvpFinal.loserScore,
        stMvpFinal.cardOnly,forfeit,stMvpFinal.eventCount);
}

void ST_MvpDuelResult(void) {
    int winner,loser;
    char value[16];
    if (!ST_MvpLocalEnabled() || level.gametype!=GT_DUEL || stMvpFinalized) return;
    if (ST_DuelBestOfEnabled()) {
        if (!level.stDuelSeriesComplete) {
            if (trap->Cvar_VariableIntegerValue("developer")) trap->Print("WINNER_ROUND intermediate; no replay\n");
            return;
        }
        winner=level.stDuelSeriesWinner; loser=level.stDuelSeriesLoser;
    } else {
        if (level.numPlayingClients!=2 || ST_TournamentControlsDuel()) return;
        trap->GetConfigstring(CS_CLIENT_DUELWINNER,value,sizeof(value));
        winner=atoi(value);
        loser=level.sortedClients[0]==winner ? level.sortedClients[1] : level.sortedClients[0];
    }
    if (winner<0 || winner>=level.maxclients || loser<0 || loser>=level.maxclients || winner==loser) return;
    ST_MvpWinnerResult(winner,loser,qfalse);
}

qboolean ST_MvpPendingForfeit(void) { return stMvpForfeitPending!=0; }

static void ST_MvpBeginForfeit(int winner,int loser) {
    ST_MvpWinnerResult(winner,loser,qtrue);
    stMvpForfeitPending=1;
    level.stDuelSeriesComplete=qtrue;
    level.stDuelSeriesWinner=winner; level.stDuelSeriesLoser=loser;
    trap->SetConfigstring(CS_CLIENT_DUELWINNER,va("%d",winner));
    BeginIntermission();
}

qboolean ST_MvpTournamentForfeit(int winner,int loser) {
    if (!ST_MvpLocalEnabled() || level.gametype!=GT_DUEL || level.intermissiontime ||
        winner<0 || loser<0 || winner>=level.maxclients || loser>=level.maxclients) return qfalse;
    ST_MvpBeginForfeit(winner,loser);
    return qtrue;
}

qboolean ST_MvpDuelDisconnect(int leaving) {
    int a=level.sortedClients[0],b=level.sortedClients[1],winner;
    if (!ST_MvpLocalEnabled() || level.gametype!=GT_DUEL || ST_TournamentControlsDuel() ||
        level.intermissiontime || level.intermissionQueued || level.warmupTime ||
        level.numPlayingClients!=2 || (leaving!=a && leaving!=b)) return qfalse;
    winner=leaving==a ? b : a;
    ST_MvpBeginForfeit(winner,leaving);
    level.clients[winner].sess.wins++;
    ClientUserinfoChanged(winner);
    return qtrue;
}
