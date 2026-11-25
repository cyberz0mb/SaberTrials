"""Apply the Match Rules game/cgame adapter to a disposable OpenJK source clone.

No installed files or baseline trees are changed by importing this module.
"""
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent


def replace(path: Path, old: str, new: str, count: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    found = text.count(old)
    if found != count:
        raise RuntimeError(f"Match Rules overlay: {path.name}: expected {count} anchors, got {found}: {old[:80]!r}")
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")


def apply(root: Path) -> None:
    root = Path(root)
    game = root / "codemp/game"
    for name in ("st_match_rules.h", "st_match_server_policy.h", "g_st_match_rules.cpp", "g_st_match_rules.inc", "g_st_match_bots.inc", "g_st_match_live.inc"):
        shutil.copy2(HERE / name, game / name)
    local = game / "g_local.h"
    with local.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write("""
// Server-only Match Rules interfaces. Never dispatched from ClientCommand.
qboolean ST_MatchConsoleCommand(const char *cmd);
void ST_MatchInit(void);
void ST_MatchFrame(void);
void ST_MatchShutdown(void);
void ST_MatchApplyTeamLock(void);
void ST_MatchPublishControls(void);
void ST_MatchPublishLiveBots(void);
void ST_MatchLiveInit(void);
int ST_MatchInt(const char *name);
qboolean ST_MatchWeaponsManaged(void);
qboolean ST_MatchTeamsManaged(void);
qboolean ST_MatchPopulationManaged(void);
qboolean ST_MatchVotesManaged(void);
int ST_MatchEffectiveTeamCap(void);
int ST_MatchEffectiveWeaponMask(void);
qboolean ST_MatchReady(void);
qboolean ST_MatchCommit(char *map,size_t size);
qboolean ST_MatchHasRoom(int team,int ignoreClient);
qboolean ST_MatchJoinAllowed(int clientNum,int team);
int ST_MatchForceCap(int power);
int ST_MatchForceMask(int mode);
int ST_MatchWeaponMask(int mode);
void ST_MatchApplyForce(gentity_t *ent);
void ST_MatchSpawn(gentity_t *ent);
int ST_MatchRespawnAt(int normal);
qboolean ST_MatchRotationConfigured(void);
void ST_MatchSpawnBot(const char *name,int skill,int team,int role,int slot);
qboolean ST_MatchBotValid(const char *name,int skill,int team,int role,int slot);
const char *ST_MatchRoleToken(int role);
""")
    replace(game / "CMakeLists.txt", '"${MPDir}/game/g_sabertrials.c"', '"${MPDir}/game/g_sabertrials.c"\n    "${MPDir}/game/g_st_match_rules.cpp"')
    trials = game / "g_sabertrials.c"
    replace(trials, 'return mode == ST_FORCE_FULL ? 0 : ST_RESTRICTED_FORCE_DISABLE_MASK;', 'return ST_MatchForceMask(mode);')
    replace(trials, '''\tif ( (gametype == GT_TEAM || gametype == GT_CTF) && mode == ST_WEAPONS_OFF ) {
\t\treturn ST_SABER_ONLY_WEAPON_DISABLE_MASK;
\t}
\treturn 0;''', '''    if (ST_MatchWeaponsManaged()) return ST_MatchWeaponMask(mode);
    return (gametype == GT_TEAM || gametype == GT_CTF) && mode == ST_WEAPONS_OFF ? ST_SABER_ONLY_WEAPON_DISABLE_MASK : 0;''')
    replace(trials, '''\tlevel.stPendingForceMode = -1;
\tlevel.stPendingGametype = -1;
\tlevel.stPendingWeaponsMode = -1;
\tlevel.stPendingMasterMode = -1;
\tlevel.stNextVoteCallTime''', '''\tST_MatchInit();
\tlevel.stPendingForceMode = -1;
\tlevel.stPendingGametype = -1;
\tlevel.stPendingWeaponsMode = -1;
\tlevel.stPendingMasterMode = -1;
\tlevel.stNextVoteCallTime''')
    replace(trials, 'if ( g_allowVote.integer == -1 || g_allowVote.integer == 1074 ||', 'if ( !ST_MatchVotesManaged() && (g_allowVote.integer == -1 || g_allowVote.integer == 1074 ||')
    replace(trials, 'g_allowVote.integer == 15410 ) {', 'g_allowVote.integer == 15410) ) {')
    replace(trials, 'st_forceModeActive.integer != ST_FORCE_RESTRICTED && st_forceModeActive.integer != ST_FORCE_FULL', 'st_forceModeActive.integer < 0 || st_forceModeActive.integer > 2')
    replace(trials, 'st_weaponsActive.integer != ST_WEAPONS_OFF && st_weaponsActive.integer != ST_WEAPONS_ON', 'st_weaponsActive.integer < 0 || st_weaponsActive.integer > 2')
    replace(trials, '''if ( g_weaponDisable.integer != weaponDisableMask &&
\t\t(level.gametype == GT_TEAM || level.gametype == GT_CTF ||
\t\tg_weaponDisable.integer == ST_SABER_ONLY_WEAPON_DISABLE_MASK) )''', '''if ( g_weaponDisable.integer != weaponDisableMask &&
        (ST_MatchWeaponsManaged() || level.gametype == GT_TEAM || level.gametype == GT_CTF || g_weaponDisable.integer == ST_SABER_ONLY_WEAPON_DISABLE_MASK) )''')
    replace(trials, '\tST_CombatInit();', '\tST_CombatInit();\n\tST_MatchPublishControls();')
    replace(trials, 'qboolean ST_ApplyQueuedRuleChanges( void ) {\n\tchar nextMap[MAX_QPATH] = { 0 };', '''qboolean ST_ApplyQueuedRuleChanges( void ) {
\tchar nextMap[MAX_QPATH] = { 0 };
\tqboolean matchRestart = ST_MatchCommit(nextMap, sizeof(nextMap));''')
    replace(trials, '!hasMasterChange && !ST_CombatPending() )', '!hasMasterChange && !ST_CombatPending() && !matchRestart )')
    replace(trials, 'if ( selectedMap && selectedMap[0] ) {', 'if ( !nextMap[0] && selectedMap && selectedMap[0] ) {')
    replace(trials, '(team == TEAM_RED || team == TEAM_BLUE) && level.stLockedTeam[clientNum] == team;', 'ST_TffaEnabled(team,G_TffaTeams()) && level.stLockedTeam[clientNum] == team;')
    replace(trials, '''qboolean ST_TeamJoinAllowed( int clientNum, int team ) {
\tif''', '''qboolean ST_TeamJoinAllowed( int clientNum, int team ) {
\tif (!ST_MatchJoinAllowed(clientNum,team)) return qfalse;
\tif''')
    replace(trials, 'return mode == ST_FORCE_FULL ? "Full Force" : "Restricted Force";', 'return mode == 2 ? "Custom Force" : mode == ST_FORCE_FULL ? "Full Force" : "Restricted Force";')
    replace(trials, 'return mode == ST_WEAPONS_ON ? "All Weapons" : "Sabers Only";', 'return mode == 2 ? "Custom Weapons" : mode == ST_WEAPONS_ON ? "All Weapons" : "Sabers Only";')
    svc = game / "g_svcmds.c"
    replace(svc, '\tcommand = (svcmd_t *)Q_LinearSearch(', '\tif (ST_MatchConsoleCommand(cmd)) return qtrue;\n\tcommand = (svcmd_t *)Q_LinearSearch(')
    main = game / "g_main.c"
    replace(main, 'void G_ShutdownGame( int restart ) {', 'void G_ShutdownGame( int restart ) {\n    ST_MatchShutdown();')
    replace(main, 'void G_RunFrame( int levelTime ) {', 'void G_RunFrame( int levelTime ) {\n    ST_MatchFrame();')
    bot = game / "g_bot.c"
    replace(bot, 'int delay, char *altname, int stRole) {', 'int delay, char *altname, int stRole, qboolean keepSkill) {')
    replace(bot, 'G_AddBot( name, skill, team, delay, altname, stRole );', 'G_AddBot( name, skill, team, delay, altname, stRole, qfalse );')
    replace(bot, 'G_AddBot( botName, skill, team, 0, "", role );', 'G_AddBot( botName, skill, team, 0, "", role, qfalse );')
    replace(bot, 'if ( stRole == ST_BOT_ROLE_SABER_MASTER )\n\t\tskill = 5.0f;', 'if ( stRole == ST_BOT_ROLE_SABER_MASTER && !keepSkill )\n\t\tskill = 5.0f;')
    replace(bot, 'Info_SetValueForKey( userinfo, "skill", va("%.2f", skill) );', 'Info_SetValueForKey( userinfo, "skill", va("%.2f", skill) );\n    Info_SetValueForKey(userinfo,"st_matchDefinition",name);')
    replace(bot, 'const char *G_RefreshNextMap(int gametype, qboolean forced)\n{', '''const char *G_RefreshNextMap(int gametype, qboolean forced)
{
    if (!forced && ST_MatchRotationConfigured()) {
        trap->Cvar_Set("nextmap", "st_match_nextmap");
        return NULL;
    }''')
    replace(bot, '/*\n===============\nSvcmd_AddBot_f', '#include "g_st_match_bots.inc"\n\n/*\n===============\nSvcmd_AddBot_f')
    # Admission applies to ordinary addbot and automatic population too.
    replace(bot, 'if (level.gametype == GT_TEAM && (G_TffaTeams() > 2 || g_tffaTeamSize.integer)) {', 'if (level.gametype == GT_TEAM || level.gametype == GT_CTF) {')
    replace(bot, '\tminplayers = bot_minplayers.integer;', '''\tminplayers = bot_minplayers.integer;
    if (ST_MatchPopulationManaged()) {
        minplayers = Com_Clampi(0,sv_maxclients.integer-1,minplayers);
        int cap = ST_MatchEffectiveTeamCap();
        if (cap > 0 && (level.gametype == GT_TEAM || level.gametype == GT_CTF))
            minplayers = Com_Clampi(0,cap*G_TffaTeams(),minplayers);
    }''')
    client = game / "g_client.c"
    replace(client, 'if (G_TffaTeams() > 2 || (level.gametype == GT_TEAM && g_tffaTeamSize.integer)) {', 'if (level.gametype == GT_TEAM || level.gametype == GT_CTF) {', count=2)
    replace(client, 'if (level.gametype == GT_TEAM && client->sess.sessionTeam != TEAM_SPECTATOR &&', 'if ((level.gametype == GT_TEAM || level.gametype == GT_CTF) && client->sess.sessionTeam != TEAM_SPECTATOR &&')
    replace(client, '\tclient->stShieldRegenDelayEnd = level.time;', '\tST_MatchSpawn(ent);\n\tclient->stShieldRegenDelayEnd = level.time;')
    for item_source in (client, game / "g_items.c", game / "w_saber.c"):
        replace(item_source, 'wDisable = g_duelWeaponDisable.integer;', 'wDisable = ST_MatchEffectiveWeaponMask();')
        replace(item_source, 'wDisable = g_weaponDisable.integer;', 'wDisable = ST_MatchEffectiveWeaponMask();')
    replace(game / "g_st_dlc.inc", '''    disabled=(level.gametype==GT_DUEL || level.gametype==GT_POWERDUEL) ?
        g_duelWeaponDisable.integer : g_weaponDisable.integer;''', '    disabled=ST_MatchEffectiveWeaponMask();')
    replace(game / "w_saber.c", 'i != WP_SABER && i != WP_NONE)', 'i != WP_SABER && i != WP_NONE && (i != WP_MELEE || !ST_MatchWeaponsManaged()))')
    replace(client, '\tclient->ps.stats[STAT_MAX_HEALTH] = client->pers.maxHealth;', '''\tclient->ps.stats[STAT_MAX_HEALTH] = client->pers.maxHealth;
    if (level.gametype != GT_SIEGE && trap->Cvar_VariableIntegerValue("st_spawnHealth") > 0)
        client->ps.stats[STAT_MAX_HEALTH] = client->pers.maxHealth = Com_Clampi(1,500,trap->Cvar_VariableIntegerValue("st_spawnHealth"));''', count=2)
    team = game / "g_team.c"
    replace(team, '''    if (level.gametype != GT_TEAM || !g_tffaTeamSize.integer) return qtrue;
    return TeamCount(ignoreClient, (team_t)team) < Com_Clampi(2, 4, g_tffaTeamSize.integer);''', '    return ST_MatchHasRoom(team,ignoreClient);')
    cmds = game / "g_cmds.c"
    replace(cmds, 'if (level.gametype == GT_TEAM && (team == TEAM_SPECTATOR || !G_TffaHasRoom(team, clientNum))) {', 'if ((level.gametype == GT_TEAM || level.gametype == GT_CTF) && (team == TEAM_SPECTATOR || !G_TffaHasRoom(team, clientNum))) {')
    replace(cmds, '\toldTeam = client->sess.sessionTeam;', '''\toldTeam = client->sess.sessionTeam;
    if (!ST_MatchJoinAllowed(clientNum,team)) {
        trap->SendServerCommand(clientNum,"print \\"Team entry is locked, switching is disabled, or this team is full.\\n\\"");
        return;
    }''')
    # Both stock death-animation paths must respect the same minimum.
    combat = game / "g_combat.c"
    replace(combat, 'self->client->respawnTime = level.time + 1700;', 'self->client->respawnTime = ST_MatchRespawnAt(level.time + 1700);')
    replace(combat, 'self->client->respawnTime = level.time + 1000;', 'self->client->respawnTime = ST_MatchRespawnAt(level.time + 1000);')
    force = game / "w_force.c"
    replace(force, 'qboolean WP_ForcePowerUsable( gentity_t *self, forcePowers_t forcePower )\n{', '''qboolean WP_ForcePowerUsable( gentity_t *self, forcePowers_t forcePower )
{
    ST_MatchApplyForce(self);''')
    replace(force, '\tif (!(self->client->ps.fd.forcePowersActive & (1 << FP_TELEPATHY)))', '\tST_MatchApplyForce(self);\n\tif (!(self->client->ps.fd.forcePowersActive & (1 << FP_TELEPATHY)))')


def apply_frontend(root: Path) -> None:
    """Keep custom caps authoritative during native client prediction."""
    cg = Path(root) / "codemp/cgame/cg_predict.c"
    replace(cg, '\tif ( pmove_msec.integer < 8 ) {', '''    // Optional trailing Match Rules fields preserve the existing controls protocol.
    {
        int version=0,block=0,active=0,forceMode=0;
        char caps[19]={0};
        if (sscanf(CG_ConfigString(CS_ST_COMBAT_CONTROLS),"%d %d %d %d %18s",&version,&block,&active,&forceMode,caps)==5 &&
            version==1 && forceMode==2 && strlen(caps)==18) {
            for(int power=0;power<NUM_FORCE_POWERS;++power) {
                int cap=caps[power]-'0';
                if(cap<0||cap>3)continue;
                if(cg.predictedPlayerState.fd.forcePowerLevel[power]>cap)cg.predictedPlayerState.fd.forcePowerLevel[power]=cap;
                if(!cap)cg.predictedPlayerState.fd.forcePowersKnown&=~(1<<power);
            }
        }
    }
\tif ( pmove_msec.integer < 8 ) {''')
