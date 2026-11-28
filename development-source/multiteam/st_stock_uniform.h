/* Shared outfit paths and garment dyes for the Profile preview and player models. */
#ifndef ST_STOCK_UNIFORM_H
#define ST_STOCK_UNIFORM_H
#include "st_tffa_teams.h"

static inline int ST_UniformSlot(const char *value)
{
    return value && value[0] >= '1' && value[0] <= '0' + ST_TFFA_MAX_TEAMS && !value[1]
        ? value[0] - '0' : 0;
}

static inline qboolean ST_StockModularJedi(const char *model)
{
    static const char *const names[] = {"jedi_hf","jedi_hm","jedi_kdm","jedi_rm","jedi_tf","jedi_zf"};
    for (size_t i = 0; i < ARRAY_LEN(names); ++i)
        if (!Q_stricmp(model, names[i])) return qtrue;
    return qfalse;
}

static inline const float *ST_UniformDye(int team)
{
    static const float cloth[ST_TFFA_TEAM_IDS][3] = {
        {1,1,1},{.81f,.25f,.23f},{.24f,.43f,.81f},{1,1,1},{.25f,.70f,.35f},
        {.83f,.72f,.27f},{.84f,.85f,.86f},{.35f,.36f,.38f},{.88f,.50f,.23f},{.64f,.34f,.77f}
    };
    return cloth[team];
}

static inline qboolean ST_StockUniformPath(const char *model, const char *outfit, int team, char *path)
{
    const char *color = ST_TffaName(team);
    path[0] = 0;
    if (!*color || !*model || strchr(outfit, '|')) return qfalse;
    if (!*outfit || !Q_stricmp(outfit, "red") || !Q_stricmp(outfit, "blue")) outfit = "default";
    if (strlen(model) + strlen(outfit) + strlen(color) + sizeof("models/st_team/skins//_.skin") > MAX_QPATH)
        return qfalse;
    Com_sprintf(path, MAX_QPATH, "models/st_team/skins/%s/%s_%s.skin", model, outfit, color);
    return qtrue;
}
#endif
