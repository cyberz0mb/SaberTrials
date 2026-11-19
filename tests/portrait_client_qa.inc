/* Isolated QA build only. Never ship this command. */
static void ST_PortraitSelectionQA(void) {
    snapshot_t *snap = cg.snap;
    int self = cg.clientNum, gt = cgs.gametype, winner = cgs.duelWinner;
    int d1 = cgs.duelist1, d2 = cgs.duelist2, pref = st_portraitTarget.integer;
    int sclient, duel, opponent, scores = cg.numScores, failures = 0;
    qboolean valid1 = cgs.clientinfo[1].infoValid, valid2 = cgs.clientinfo[2].infoValid;
    team_t t0 = cgs.clientinfo[0].team, t1 = cgs.clientinfo[1].team, t2 = cgs.clientinfo[2].team;
    score_t score0 = cg.scores[0], score1 = cg.scores[1];
    const char *label;
    if (!snap) return;
    sclient = snap->ps.clientNum; duel = snap->ps.duelInProgress; opponent = snap->ps.duelIndex;
    cg.clientNum = snap->ps.clientNum = 0; cgs.gametype = GT_FFA;
    cgs.clientinfo[0].team = cgs.clientinfo[1].team = cgs.clientinfo[2].team = TEAM_FREE;
    cgs.clientinfo[1].infoValid = cgs.clientinfo[2].infoValid = qtrue;
    st_portraitTarget.integer = 0; snap->ps.duelInProgress = qfalse;
    cgs.duelWinner = 1;
#define ST_EXPECT(n) do { if (ST_PortraitTarget(&label) != (n)) failures++; } while (0)
    ST_EXPECT(1); // FFA leader.
    cgs.duelWinner = 2; ST_EXPECT(2); // Leader changes.
    snap->ps.duelInProgress = qtrue; snap->ps.duelIndex = 1; ST_EXPECT(1);
    st_portraitTarget.integer = 1; ST_EXPECT(0); // Self remains self in a duel.
    st_portraitTarget.integer = 2; ST_EXPECT(1);
    snap->ps.duelInProgress = qfalse; ST_EXPECT(0); // No opponent fallback.
    cgs.gametype = GT_DUEL; cgs.duelist1 = 0; cgs.duelist2 = 2; ST_EXPECT(2);
    cgs.duelist2 = 0; cgs.duelist1 = 1; ST_EXPECT(1);
    cgs.clientinfo[0].team = TEAM_SPECTATOR; ST_EXPECT(0); // No invented spectator opponent.
    cgs.clientinfo[0].team = TEAM_FREE;
    cgs.gametype = GT_POWERDUEL; ST_EXPECT(0); // Ambiguous multi-opponent match.
    cgs.gametype = GT_FFA; st_portraitTarget.integer = 0;
    snap->ps.duelInProgress = qtrue; snap->ps.duelIndex = MAX_CLIENTS; ST_EXPECT(2);
    cgs.clientinfo[2].infoValid = qfalse; ST_EXPECT(0); // Disconnected leader.
    cgs.clientinfo[2].infoValid = qtrue; snap->ps.duelInProgress = qfalse;
    cgs.gametype = GT_TEAM; cg.numScores = 2;
    cg.scores[0].client = 1; cg.scores[0].score = 5;
    cg.scores[1].client = 2; cg.scores[1].score = 12; ST_EXPECT(2);
    cgs.clientinfo[2].team = TEAM_SPECTATOR; ST_EXPECT(1);
#undef ST_EXPECT
    snap->ps.clientNum = sclient; snap->ps.duelInProgress = duel; snap->ps.duelIndex = opponent;
    cg.clientNum = self; cgs.gametype = gt; cgs.duelWinner = winner;
    cgs.duelist1 = d1; cgs.duelist2 = d2; st_portraitTarget.integer = pref;
    cgs.clientinfo[1].infoValid = valid1; cgs.clientinfo[2].infoValid = valid2;
    cgs.clientinfo[0].team = t0; cgs.clientinfo[1].team = t1; cgs.clientinfo[2].team = t2;
    cg.numScores = scores; cg.scores[0] = score0; cg.scores[1] = score1;
    Com_Printf("PORTRAIT_SELECTION cases=14 failures=%d\n", failures);
}

void ST_PortraitQA_f(void) {
    const char *label;
    const char *op = CG_Argv(1);
    int n = ST_PortraitTarget(&label);
    if (!Q_stricmp(op, "selection")) { ST_PortraitSelectionQA(); return; }
    if (!Q_stricmp(op, "damage")) { cg.damageTime = cg.time; return; }
    if (!Q_stricmp(op, "face")) {
        const animation_t *a = &bgHumanoidAnimations[FACE_TALK1];
        if (n >= 0 && n < MAX_CLIENTS && cg_entities[n].ghoul2)
            trap->G2API_SetBoneAnim(cg_entities[n].ghoul2, 0, "face", a->firstFrame, a->firstFrame + a->numFrames,
                BONE_ANIM_OVERRIDE_LOOP, 1, cg.time, -1, 0);
        return;
    }
    Com_Printf("PORTRAIT_QA target=%d label=%s mode=%d ready=%d cache=%d yaw=%.3f pitch=%.3f size=%.1f kick=%.3f\n",
        n, label, st_portraitMode.integer, st_portrait.ready, st_portrait.client,
        st_portrait.yaw, st_portrait.pitch, st_portraitSize.value, st_portrait.kick);
    if (st_portrait.ready && n >= 0 && n < MAX_CLIENTS) {
        float a = -1, b = -1, speed;
        int first, last, flags;
        centity_t *cent = &cg_entities[n];
        Com_Printf("PORTRAIT_MODEL model=%s skin=%s noface=%d talkframe=%d talkcount=%d\n", cgs.clientinfo[n].modelName,
            cgs.clientinfo[n].skinName, cent->noFace, bgHumanoidAnimations[FACE_TALK1].firstFrame, bgHumanoidAnimations[FACE_TALK1].numFrames);
        qboolean fa = trap->G2API_GetBoneAnim(cent->ghoul2, "face", cg.time, &a, &first, &last, &flags, &speed, NULL, 0);
        qboolean fb = trap->G2API_GetBoneAnim(st_portrait.model, "face", cg.time, &b, &first, &last, &flags, &speed, NULL, 0);
        Com_Printf("PORTRAIT_FACE world=%d/%.3f portrait=%d/%.3f valid=%d type=%d blink=%.0f\n", fa, a, fb, b,
            cent->currentValid, cent->currentState.eType, cgs.clientinfo[n].facial_blink);
    }
}
