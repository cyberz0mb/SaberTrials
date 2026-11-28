/* Shared by the game, cgame and scoreboard. Spectator keeps its network ID, 3. */
#ifndef ST_TFFA_TEAMS_H
#define ST_TFFA_TEAMS_H

#define ST_TFFA_MAX_TEAMS 8
#define ST_TFFA_TEAM_IDS 10

static inline int ST_TffaCount(int count)
{
    return count < 2 ? 2 : count > ST_TFFA_MAX_TEAMS ? ST_TFFA_MAX_TEAMS : count;
}

static inline int ST_TffaTeamAt(int slot)
{
    static const int teams[ST_TFFA_MAX_TEAMS] = {1, 2, 4, 5, 6, 7, 8, 9};
    return slot >= 0 && slot < ST_TFFA_MAX_TEAMS ? teams[slot] : 0;
}

static inline const char *ST_TffaName(int team)
{
    static const char *const names[ST_TFFA_TEAM_IDS] = {
        "", "Red", "Blue", "", "Green", "Yellow", "White", "Black", "Orange", "Purple"
    };
    return team >= 0 && team < ST_TFFA_TEAM_IDS ? names[team] : "";
}

static inline const float *ST_TffaColor(int team)
{
    /* Charcoal stays distinguishable on dark maps, with a lighter label on the board. */
    static const float colors[ST_TFFA_TEAM_IDS][4] = {
        {1,1,1,1}, {1,.32f,.32f,1}, {.24f,.66f,1,1}, {1,1,1,1},
        {.30f,.88f,.40f,1}, {1,.83f,.20f,1}, {1,1,1,1}, {.39f,.42f,.46f,1},
        {1,.49f,.13f,1}, {.72f,.40f,1,1}
    };
    return colors[team >= 0 && team < ST_TFFA_TEAM_IDS ? team : 0];
}

static inline int ST_TffaEnabled(int team, int count)
{
    return team > 0 && team != 3 && team <= ST_TffaTeamAt(ST_TffaCount(count) - 1);
}

/* Zero denotes a tie for first, regardless of ties among the trailing teams. */
static inline int ST_TffaLeader(const int *scores, int count)
{
    int best = ST_TffaTeamAt(0), tied = 0;
    for (int slot = 1; slot < ST_TffaCount(count); ++slot) {
        int team = ST_TffaTeamAt(slot);
        if (scores[team] > scores[best]) {
            best = team;
            tied = 0;
        } else if (scores[team] == scores[best]) {
            tied = 1;
        }
    }
    return tied ? 0 : best;
}

#endif
