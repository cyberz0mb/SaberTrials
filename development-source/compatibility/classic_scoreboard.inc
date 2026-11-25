/* Renderer and painter callbacks are shared with the native Saber Trials board.
 * Only consume scoreboard fields defined by the classic multiplayer protocol. */
qboolean ST_UsePersonalScoreboard(void) {
    char preference[16];
    trap->Cvar_VariableStringBuffer("st_personalHud", preference, sizeof(preference));
    return atoi(preference) == 1 ? qtrue : qfalse;
}

static qboolean ST_DrawClassicConnectionBoard(float fade) {
    STPBoard board = {0};
    if (!cg.snap || !ST_UsePersonalScoreboard()) {
        stpVisible = 0;
        return qfalse;
    }
    if (!stpVisible || cg.time < stpOpened) stpOpened = cg.time;
    stpVisible = 1;
    board.page = (cg.time - stpOpened) / 10000;
    board.local = cg.clientNum;
    board.mode = cgs.gametype;
    board.teams = cgs.gametype >= GT_TEAM;
    board.classicStats = 1;
    board.red = cg.teamScores[0];
    board.blue = cg.teamScores[1];
    board.result = cg.predictedPlayerState.pm_type == PM_INTERMISSION;
    Q_strncpyz(board.title, board.result ? "MATCH RESULTS" : "SCOREBOARD", sizeof(board.title));
    Com_sprintf(board.subtitle, sizeof(board.subtitle), "%s  /  %s", STP_Mode(board.mode, 0, 0),
                board.result ? "Final server scores" : "Live server scores");
    for (int i = 0; i < cg.numScores && i < MAX_CLIENTS && board.count < STP_MAX_ROWS; ++i) {
        const score_t *score = &cg.scores[i];
        if (score->client < 0 || score->client >= cgs.maxclients || score->client >= MAX_CLIENTS) continue;
        const clientInfo_t *player = &cgs.clientinfo[score->client];
        if (!player->infoValid) continue;
        STPRow *row = &board.rows[board.count++];
        row->id = score->client;
        row->team = player->team;
        row->score = score->score;
        row->ping = score->ping;
        row->minutes = score->time;
        row->bot = player->botSkill != -1;
        row->icon = player->modelIcon;
        row->wins = player->wins;
        row->losses = player->losses;
        row->ready = board.result && score->client < 32 &&
            ((unsigned)cg.snap->ps.stats[STAT_CLIENTS_READY] & (1u << score->client));
        row->flag = (player->powerups & (1 << PW_REDFLAG)) ? 1 :
                    (player->powerups & (1 << PW_BLUEFLAG)) ? 2 :
                    (player->powerups & (1 << PW_NEUTRALFLAG)) ? 3 : 0;
        Q_strncpyz(row->name, player->name, sizeof(row->name));
    }
    if (board.result) {
        Q_strncpyz(board.outcome, "Match complete", sizeof(board.outcome));
        if (board.mode == GT_DUEL || board.mode == GT_POWERDUEL) {
            const int winner = cgs.duelWinner;
            if (winner >= 0 && winner < cgs.maxclients && winner < MAX_CLIENTS &&
                cgs.clientinfo[winner].infoValid)
                Com_sprintf(board.outcome, sizeof(board.outcome), "Winner: %s", cgs.clientinfo[winner].name);
        } else if (board.mode == GT_SIEGE && (cg_siegeWinTeam == 1 || cg_siegeWinTeam == 2)) {
            Q_strncpyz(board.outcome, cg_siegeWinTeam == 1 ? "Red team wins" : "Blue team wins", sizeof(board.outcome));
        } else if (board.teams && board.mode != GT_SIEGE && board.red != board.blue) {
            Q_strncpyz(board.outcome, board.red > board.blue ? "Red team wins" : "Blue team wins", sizeof(board.outcome));
        } else if (!board.teams) {
            const int winner = STP_Winner(&board);
            if (winner >= 0) Com_sprintf(board.outcome, sizeof(board.outcome), "Winner: %s", board.rows[winner].name);
        }
    }
    stpFade = fade;
    STP_DrawBoard(&stpPainter, &board);
    stpFade = 1;
    return qtrue;
}
