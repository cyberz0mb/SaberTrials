/*
===========================================================================
Saber Trials server rule and vote support.

This file is part of Saber Trials, based on OpenJK and distributed under the
GNU General Public License version 2.
===========================================================================
*/

#include "g_local.h"

#define ST_RESTRICTED_FORCE_DISABLE_MASK 163833
#define ST_SABER_ONLY_WEAPON_DISABLE_MASK 524278
#define ST_TOURNAMENT_STATE_VERSION 1
#define ST_TOURNAMENT_DISCONNECT_GRACE 60000
#define ST_TOURNAMENT_STATE_FILE "tournament_state.dat"

static void ST_TournamentSaveState( void );

static void ST_TournamentClearLevelState( void ) {
	int i;

	level.stTournamentPhase = ST_TOURNAMENT_OFF;
	level.stTournamentEntrantCount = 0;
	level.stTournamentRoundSize = 0;
	level.stTournamentRoundNumber = 0;
	level.stTournamentMatchCursor = 0;
	level.stTournamentArenaIndex = 0;
	level.stTournamentActiveA = -1;
	level.stTournamentActiveB = -1;
	level.stTournamentChampion = -1;
	level.stTournamentPendingArena = qfalse;
	level.stTournamentDisconnectDeadlineA = 0;
	level.stTournamentDisconnectDeadlineB = 0;
	level.stTournamentDisconnectNoticeA = qfalse;
	level.stTournamentDisconnectNoticeB = qfalse;
	level.stTournamentRegistrationDeadline = 0;
	for ( i = 0; i < ST_TOURNAMENT_MAX_PLAYERS; i++ ) {
		level.stTournamentEntrants[i] = -1;
		level.stTournamentRoundSlots[i] = -1;
		level.stTournamentNextSlots[i] = -1;
	}
}

static qboolean ST_TournamentReadStateInt( char **cursor, int *value ) {
	char *end;
	long parsed;

	parsed = strtol( *cursor, &end, 10 );
	if ( end == *cursor ) {
		return qfalse;
	}
	*value = (int)parsed;
	*cursor = end;
	return qtrue;
}

static void ST_TournamentLoadState( void ) {
	char state[MAX_STRING_CHARS];
	char *cursor;
	fileHandle_t stateFile = 0;
	int stateLength;
	int version;
	int i;
	qboolean valid = qtrue;

	ST_TournamentClearLevelState();
	stateLength = trap->FS_Open( ST_TOURNAMENT_STATE_FILE, &stateFile, FS_READ );
	if ( stateLength <= 0 || stateLength >= (int)sizeof( state ) ) {
		if ( stateFile ) {
			trap->FS_Close( stateFile );
		}
		return;
	}
	trap->FS_Read( state, stateLength, stateFile );
	state[stateLength] = '\0';
	trap->FS_Close( stateFile );
	cursor = state;

	valid = ST_TournamentReadStateInt( &cursor, &version ) &&
		ST_TournamentReadStateInt( &cursor, &level.stTournamentPhase ) &&
		ST_TournamentReadStateInt( &cursor, &level.stTournamentEntrantCount ) &&
		ST_TournamentReadStateInt( &cursor, &level.stTournamentRoundSize ) &&
		ST_TournamentReadStateInt( &cursor, &level.stTournamentRoundNumber ) &&
		ST_TournamentReadStateInt( &cursor, &level.stTournamentMatchCursor ) &&
		ST_TournamentReadStateInt( &cursor, &level.stTournamentArenaIndex ) &&
		ST_TournamentReadStateInt( &cursor, &level.stTournamentActiveA ) &&
		ST_TournamentReadStateInt( &cursor, &level.stTournamentActiveB ) &&
		ST_TournamentReadStateInt( &cursor, &level.stTournamentChampion );
	for ( i = 0; valid && i < ST_TOURNAMENT_MAX_PLAYERS; i++ ) {
		valid = ST_TournamentReadStateInt( &cursor, &level.stTournamentEntrants[i] );
	}
	for ( i = 0; valid && i < ST_TOURNAMENT_MAX_PLAYERS; i++ ) {
		valid = ST_TournamentReadStateInt( &cursor, &level.stTournamentRoundSlots[i] );
	}
	for ( i = 0; valid && i < ST_TOURNAMENT_MAX_PLAYERS; i++ ) {
		valid = ST_TournamentReadStateInt( &cursor, &level.stTournamentNextSlots[i] );
	}

	if ( !valid || version != ST_TOURNAMENT_STATE_VERSION ||
		level.stTournamentPhase < ST_TOURNAMENT_OFF ||
		level.stTournamentPhase > ST_TOURNAMENT_COMPLETE ||
		level.stTournamentEntrantCount < 0 ||
		level.stTournamentEntrantCount > ST_TOURNAMENT_MAX_PLAYERS ||
		level.stTournamentRoundSize < 0 ||
		level.stTournamentRoundSize > ST_TOURNAMENT_MAX_PLAYERS ) {
		trap->Print( "Saber Trials Tournament: discarded invalid saved state.\n" );
		ST_TournamentClearLevelState();
		return;
	}

	for ( i = 0; i < ST_TOURNAMENT_MAX_PLAYERS; i++ ) {
		if ( level.stTournamentEntrants[i] < -1 || level.stTournamentEntrants[i] >= MAX_CLIENTS ||
			level.stTournamentRoundSlots[i] < -1 || level.stTournamentRoundSlots[i] >= MAX_CLIENTS ||
			level.stTournamentNextSlots[i] < -1 || level.stTournamentNextSlots[i] >= MAX_CLIENTS ) {
			ST_TournamentClearLevelState();
			return;
		}
	}
	if ( level.stTournamentPhase == ST_TOURNAMENT_REGISTRATION ) {
		level.stTournamentRegistrationDeadline = level.time +
			Com_Clampi( 30, 3600, st_tournamentAutoStart.integer ) * 1000;
	}
}

static void ST_TournamentSaveState( void ) {
	char state[MAX_STRING_CHARS];
	fileHandle_t stateFile = 0;
	int i;

	if ( level.stTournamentPhase == ST_TOURNAMENT_OFF ) {
		trap->FS_Open( ST_TOURNAMENT_STATE_FILE, &stateFile, FS_WRITE );
		if ( stateFile ) {
			trap->FS_Close( stateFile );
		}
		return;
	}

	Com_sprintf( state, sizeof( state ), "%i %i %i %i %i %i %i %i %i %i",
		ST_TOURNAMENT_STATE_VERSION,
		level.stTournamentPhase,
		level.stTournamentEntrantCount,
		level.stTournamentRoundSize,
		level.stTournamentRoundNumber,
		level.stTournamentMatchCursor,
		level.stTournamentArenaIndex,
		level.stTournamentActiveA,
		level.stTournamentActiveB,
		level.stTournamentChampion );
	for ( i = 0; i < ST_TOURNAMENT_MAX_PLAYERS; i++ ) {
		Q_strcat( state, sizeof( state ), va( " %i", level.stTournamentEntrants[i] ) );
	}
	for ( i = 0; i < ST_TOURNAMENT_MAX_PLAYERS; i++ ) {
		Q_strcat( state, sizeof( state ), va( " %i", level.stTournamentRoundSlots[i] ) );
	}
	for ( i = 0; i < ST_TOURNAMENT_MAX_PLAYERS; i++ ) {
		Q_strcat( state, sizeof( state ), va( " %i", level.stTournamentNextSlots[i] ) );
	}
	trap->FS_Open( ST_TOURNAMENT_STATE_FILE, &stateFile, FS_WRITE );
	if ( stateFile ) {
		trap->FS_Write( state, strlen( state ), stateFile );
		trap->FS_Close( stateFile );
	}
}

static const char *ST_TournamentPhaseName( int phase ) {
	switch ( phase ) {
	case ST_TOURNAMENT_REGISTRATION: return "registration";
	case ST_TOURNAMENT_RUNNING: return "running";
	case ST_TOURNAMENT_PAUSED: return "paused";
	case ST_TOURNAMENT_COMPLETE: return "complete";
	default: return "off";
	}
}

static const char *ST_TournamentStageName( void ) {
	if ( level.stTournamentRoundSize == 2 ) {
		return "Final";
	}
	if ( level.stTournamentRoundSize == 4 ) {
		return "Semifinal";
	}
	return "Quarterfinal";
}

static int ST_TournamentFormatValue( int value ) {
	return value >= 5 ? 5 : 3;
}

static int ST_TournamentCurrentBestOf( void ) {
	if ( level.stTournamentRoundSize == 2 ) {
		return ST_TournamentFormatValue( st_tournamentFinalBestOf.integer );
	}
	return ST_TournamentFormatValue( st_tournamentBestOf.integer );
}

static qboolean ST_TournamentGetArena( int index, char *arena, size_t arenaSize ) {
	char list[MAX_CVAR_VALUE_STRING];
	char *token;
	int count = 0;
	int wanted;

	Q_strncpyz( list, st_tournamentArenas.string, sizeof( list ) );
	token = strtok( list, " ,;" );
	while ( token ) {
		count++;
		token = strtok( NULL, " ,;" );
	}
	if ( !count ) {
		return qfalse;
	}

	wanted = index % count;
	Q_strncpyz( list, st_tournamentArenas.string, sizeof( list ) );
	token = strtok( list, " ,;" );
	while ( token && wanted-- > 0 ) {
		token = strtok( NULL, " ,;" );
	}
	if ( !token || strstr( token, ".." ) || strchr( token, '\\' ) ) {
		return qfalse;
	}
	Q_strncpyz( arena, token, arenaSize );
	return qtrue;
}

static void ST_TournamentLoadCurrentArena( void ) {
	char arena[MAX_QPATH];

	if ( !ST_TournamentGetArena( level.stTournamentArenaIndex, arena, sizeof( arena ) ) ) {
		trap->Print( "Saber Trials Tournament: no valid arena is configured.\n" );
		return;
	}
	level.stTournamentPendingArena = qfalse;
	ST_TournamentSaveState();
	trap->SendServerCommand( -1, va( "print \"Tournament: loading arena %s.\\n\"", arena ) );
	trap->SendConsoleCommand( EXEC_APPEND, va( "map %s\n", arena ) );
}

static int ST_ForceDisableMask( int mode ) {
	return mode == ST_FORCE_FULL ? 0 : ST_RESTRICTED_FORCE_DISABLE_MASK;
}

static int ST_WeaponDisableMask( int gametype, int mode ) {
	if ( (gametype == GT_TEAM || gametype == GT_CTF) && mode == ST_WEAPONS_OFF ) {
		return ST_SABER_ONLY_WEAPON_DISABLE_MASK;
	}
	return 0;
}

qboolean ST_IsSupportedGametype( int gametype ) {
	return gametype == GT_DUEL || gametype == GT_FFA ||
		gametype == GT_TEAM || gametype == GT_CTF;
}

int ST_ParseGametype( const char *value ) {
	int gametype;

	if ( !value || !value[0] ) {
		return -1;
	}

	if ( !Q_stricmp( value, "duel" ) ) {
		return GT_DUEL;
	}
	if ( !Q_stricmp( value, "ffa" ) || !Q_stricmp( value, "free" ) ) {
		return GT_FFA;
	}
	if ( !Q_stricmp( value, "tffa" ) || !Q_stricmp( value, "team" ) ||
		!Q_stricmp( value, "teamffa" ) ) {
		return GT_TEAM;
	}
	if ( !Q_stricmp( value, "ctf" ) || !Q_stricmp( value, "capturetheflag" ) ) {
		return GT_CTF;
	}

	gametype = atoi( value );
	return ST_IsSupportedGametype( gametype ) ? gametype : -1;
}

const char *ST_GametypeName( int gametype ) {
	switch ( gametype ) {
	case GT_DUEL:
		return "Duel";
	case GT_FFA:
		return "FFA";
	case GT_TEAM:
		return "TFFA";
	case GT_CTF:
		return "CTF";
	default:
		return "Unknown";
	}
}

int ST_ParseForceMode( const char *value ) {
	if ( !value || !value[0] ) {
		return -1;
	}
	if ( !Q_stricmp( value, "restricted" ) || !Q_stricmp( value, "restrictedforce" ) ||
		!Q_stricmp( value, "0" ) ) {
		return ST_FORCE_RESTRICTED;
	}
	if ( !Q_stricmp( value, "full" ) || !Q_stricmp( value, "fullforce" ) ||
		!Q_stricmp( value, "1" ) ) {
		return ST_FORCE_FULL;
	}
	return -1;
}

const char *ST_ForceModeName( int mode ) {
	return mode == ST_FORCE_FULL ? "Full Force" : "Restricted Force";
}

int ST_ParseWeaponsMode( const char *value ) {
	if ( !value || !value[0] ) {
		return -1;
	}
	if ( !Q_stricmp( value, "off" ) || !Q_stricmp( value, "saber" ) ||
		!Q_stricmp( value, "sabers" ) || !Q_stricmp( value, "saberonly" ) ||
		!Q_stricmp( value, "0" ) ) {
		return ST_WEAPONS_OFF;
	}
	if ( !Q_stricmp( value, "on" ) || !Q_stricmp( value, "all" ) ||
		!Q_stricmp( value, "allweapons" ) || !Q_stricmp( value, "1" ) ) {
		return ST_WEAPONS_ON;
	}
	return -1;
}

const char *ST_WeaponsModeName( int mode ) {
	return mode == ST_WEAPONS_ON ? "All Weapons" : "Sabers Only";
}

int ST_ParseMasterMode( const char *value ) {
	if ( !value || !value[0] ) {
		return -1;
	}
	if ( !Q_stricmp( value, "off" ) || !Q_stricmp( value, "standard" ) ||
		!Q_stricmp( value, "0" ) ) {
		return ST_MASTER_OFF;
	}
	if ( !Q_stricmp( value, "on" ) || !Q_stricmp( value, "master" ) ||
		!Q_stricmp( value, "1" ) ) {
		return ST_MASTER_ON;
	}
	return -1;
}

const char *ST_MasterModeName( int mode ) {
	return mode == ST_MASTER_ON ? "Master" : "Standard";
}

qboolean ST_TeamJoinAllowed( int clientNum, int team ) {
	if ( level.gametype != GT_TEAM || !level.stTeamsLocked || team == TEAM_SPECTATOR ) {
		return qtrue;
	}
	return clientNum >= 0 && clientNum < level.maxclients &&
		(team == TEAM_RED || team == TEAM_BLUE) && level.stLockedTeam[clientNum] == team;
}

void Svcmd_STLockTeams_f( void ) {
	char arg[16];
	qboolean lock;
	int i;
	if ( level.gametype != GT_TEAM ) {
		trap->Print( "Saber Trials: team locking is only available in TFFA.\n" );
		return;
	}
	trap->Argv( 1, arg, sizeof( arg ) );
	if ( trap->Argc() != 2 || (Q_stricmp( arg, "on" ) && Q_stricmp( arg, "off" )) ) {
		trap->Print( "Usage: st_lockteams <on|off>\n" );
		return;
	}
	lock = !Q_stricmp( arg, "on" );
	if ( lock == level.stTeamsLocked ) {
		trap->Print( "Saber Trials: teams are already %s.\n", lock ? "locked" : "unlocked" );
		return;
	}
	level.stTeamsLocked = lock;
	for ( i = 0; i < level.maxclients; i++ ) {
		level.stLockedTeam[i] = lock && level.clients[i].pers.connected == CON_CONNECTED ?
			level.clients[i].sess.sessionTeam : TEAM_SPECTATOR;
	}
	trap->SendServerCommand( -1, lock ?
		"print \"TFFA teams locked: current players keep playing; joining and switching teams are disabled until unlocked or the map restarts.\n\"" :
		"print \"TFFA teams unlocked: players may join and switch teams.\n\"" );
	G_LogPrintf( "Saber Trials: TFFA teams %s\n", lock ? "locked" : "unlocked" );
}

void ST_Init( void ) {
	int forceDisableMask;
	int weaponDisableMask;

	level.stPendingForceMode = -1;
	level.stPendingGametype = -1;
	level.stPendingWeaponsMode = -1;
	level.stPendingMasterMode = -1;
	level.stNextVoteCallTime = 0;
	level.stTeamsLocked = qfalse;
	memset( level.stLockedTeam, 0, sizeof( level.stLockedTeam ) );
	level.stDuelSeriesWinner = -1;
	level.stDuelSeriesLoser = -1;
	// Upgrade known shipped masks; preserve disabled voting and custom masks.
	if ( g_allowVote.integer == -1 || g_allowVote.integer == 1074 ||
		g_allowVote.integer == 3122 || g_allowVote.integer == 7218 ||
		g_allowVote.integer == 15410 ) {
		trap->Cvar_Set( "g_allowVote", "16383" );
		trap->Cvar_Update( &g_allowVote );
	}
	ST_TournamentLoadState();
	if ( level.gametype == GT_DUEL && level.stTournamentPhase != ST_TOURNAMENT_OFF ) {
		trap->Cvar_Set( "fraglimit", "1" );
		trap->Cvar_Update( &fraglimit );
	}

	if ( st_forceModeActive.integer != ST_FORCE_RESTRICTED && st_forceModeActive.integer != ST_FORCE_FULL ) {
		trap->Cvar_Set( "st_forceModeActive", "0" );
		trap->Cvar_Update( &st_forceModeActive );
	}

	forceDisableMask = ST_ForceDisableMask( st_forceModeActive.integer );
	if ( g_forcePowerDisable.integer != forceDisableMask ) {
		trap->Cvar_Set( "g_forcePowerDisable", va( "%i", forceDisableMask ) );
		trap->Cvar_Update( &g_forcePowerDisable );
	}

	if ( st_weaponsActive.integer != ST_WEAPONS_OFF && st_weaponsActive.integer != ST_WEAPONS_ON ) {
		trap->Cvar_Set( "st_weaponsActive", "0" );
		trap->Cvar_Update( &st_weaponsActive );
	}

	if ( st_masterModeActive.integer != ST_MASTER_OFF &&
		st_masterModeActive.integer != ST_MASTER_ON ) {
		trap->Cvar_Set( "st_masterModeActive", "0" );
		trap->Cvar_Update( &st_masterModeActive );
	}

	weaponDisableMask = ST_WeaponDisableMask( level.gametype, st_weaponsActive.integer );
	if ( g_weaponDisable.integer != weaponDisableMask &&
		(level.gametype == GT_TEAM || level.gametype == GT_CTF ||
		g_weaponDisable.integer == ST_SABER_ONLY_WEAPON_DISABLE_MASK) ) {
		trap->Cvar_Set( "g_weaponDisable", va( "%i", weaponDisableMask ) );
		trap->Cvar_Update( &g_weaponDisable );
	}

	ST_CombatInit();

}

void ST_UpdateParryInput( gentity_t *ent, const usercmd_t *ucmd ) {
	gclient_t *client;
	int parryWindow;
	int parryCooldown;

	if ( !ent || !ent->client || !ucmd ) {
		return;
	}

	client = ent->client;
	if ( !ST_CombatOption(ST_COMBAT_DEFENSE) ) {
		client->stParryWindowEnd = 0;
		client->stParryCooldownEnd = 0;
		client->stPerfectParrySuccessTime = 0;
		client->stCounterWindowEnd = 0;
		return;
	}
	if ( ent->health <= 0 || client->ps.stats[STAT_HEALTH] <= 0 ||
		client->sess.sessionTeam == TEAM_SPECTATOR ||
		(client->ps.pm_flags & PMF_FOLLOW) || client->ps.weapon != WP_SABER ||
		BG_SabersOff( &client->ps ) || client->ps.saberInFlight ) {
		// Temporary saber inactivity must not bypass the retry cooldown.
		client->stParryWindowEnd = 0;
		return;
	}

	// A perfect parry makes the defender immediately attack-ready during the
	// counter window, even if a block animation still has time remaining.
	if ( client->stCounterWindowEnd > level.time &&
		(ucmd->buttons & BUTTON_ATTACK) ) {
		client->ps.weaponTime = 0;
		client->stCounterWindowEnd = 0;
	}

	// Walk is the active-guard control. Only a fresh press opens the perfect
	// window, which prevents holding or rapid tapping from becoming invincible.
	if ( (ucmd->buttons & BUTTON_WALKING) && !(client->buttons & BUTTON_WALKING) &&
		client->stParryCooldownEnd <= level.time ) {
		parryWindow = Com_Clampi( 100, 450, st_parryWindow.integer );
		parryCooldown = Com_Clampi( parryWindow + 100, 1500, st_parryCooldown.integer );
		client->stParryWindowEnd = level.time + parryWindow;
		client->stParryCooldownEnd = level.time + parryCooldown;
	}
}

static int ST_DuelBestOf( void ) {
	int bestOf;

	if ( level.stTournamentPhase == ST_TOURNAMENT_RUNNING ||
		level.stTournamentPhase == ST_TOURNAMENT_PAUSED ) {
		return ST_TournamentCurrentBestOf();
	}

	bestOf = Com_Clampi( 1, 9, st_duelBestOf.integer );
	if ( !(bestOf & 1) ) {
		bestOf++;
	}
	return bestOf;
}

static int ST_DuelRoundsToWin( void ) {
	return ST_DuelBestOf() / 2 + 1;
}

qboolean ST_DuelBestOfEnabled( void ) {
	return level.gametype == GT_DUEL && ST_DuelBestOf() > 1;
}

static void ST_ResetDuelSeriesClient( int clientNum ) {
	if ( clientNum < 0 || clientNum >= level.maxclients ) {
		return;
	}
	level.clients[clientNum].sess.stDuelSeriesWins = 0;
	level.clients[clientNum].sess.stDuelSeriesOpponent = -1;
}

static void ST_ResetAllDuelSeries( void ) {
	int i;
	for ( i = 0; i < level.maxclients; i++ ) {
		ST_ResetDuelSeriesClient( i );
	}
}

static qboolean ST_TournamentClientConnected( int clientNum ) {
	return clientNum >= 0 && clientNum < level.maxclients &&
		level.clients[clientNum].pers.connected == CON_CONNECTED;
}

static int ST_TournamentFindEntrant( int clientNum ) {
	int i;
	for ( i = 0; i < level.stTournamentEntrantCount; i++ ) {
		if ( level.stTournamentEntrants[i] == clientNum ) {
			return i;
		}
	}
	return -1;
}

static void ST_TournamentResetClient( int clientNum ) {
	if ( clientNum < 0 || clientNum >= level.maxclients ) {
		return;
	}
	level.clients[clientNum].sess.stTournamentSeed = -1;
	level.clients[clientNum].sess.stTournamentStatus = ST_TOURNAMENT_PLAYER_NONE;
	level.clients[clientNum].sess.stTournamentMatchWins = 0;
	level.clients[clientNum].sess.stTournamentMatchLosses = 0;
	ST_ResetDuelSeriesClient( clientNum );
}

static void ST_TournamentResetAllClients( void ) {
	int i;
	for ( i = 0; i < level.maxclients; i++ ) {
		ST_TournamentResetClient( i );
	}
}

static qboolean ST_TournamentAddClient( int clientNum ) {
	gclient_t *client;

	if ( level.stTournamentPhase != ST_TOURNAMENT_REGISTRATION ) {
		return qfalse;
	}
	if ( !ST_TournamentClientConnected( clientNum ) ||
		ST_TournamentFindEntrant( clientNum ) >= 0 ||
		level.stTournamentEntrantCount >= ST_TOURNAMENT_MAX_PLAYERS ) {
		return qfalse;
	}

	client = &level.clients[clientNum];
	level.stTournamentEntrants[level.stTournamentEntrantCount++] = clientNum;
	client->sess.stTournamentSeed = -1;
	client->sess.stTournamentStatus = ST_TOURNAMENT_PLAYER_REGISTERED;
	client->sess.stTournamentMatchWins = 0;
	client->sess.stTournamentMatchLosses = 0;
	ST_TournamentSaveState();
	trap->SendServerCommand( -1, va( "print \"Tournament: %s joined (%i/%i).\\n\"",
		client->pers.netname, level.stTournamentEntrantCount, ST_TOURNAMENT_MAX_PLAYERS ) );
	return qtrue;
}

static qboolean ST_TournamentRemoveClient( int clientNum ) {
	int index;
	int i;

	if ( level.stTournamentPhase != ST_TOURNAMENT_REGISTRATION ) {
		return qfalse;
	}
	index = ST_TournamentFindEntrant( clientNum );
	if ( index < 0 ) {
		return qfalse;
	}
	for ( i = index; i + 1 < level.stTournamentEntrantCount; i++ ) {
		level.stTournamentEntrants[i] = level.stTournamentEntrants[i + 1];
	}
	level.stTournamentEntrants[--level.stTournamentEntrantCount] = -1;
	ST_TournamentResetClient( clientNum );
	ST_TournamentSaveState();
	trap->SendServerCommand( -1, va( "print \"Tournament: client %i left registration.\\n\"", clientNum ) );
	return qtrue;
}

static void ST_TournamentActivateMatch( int first, int second ) {
	int i;

	level.stTournamentActiveA = first;
	level.stTournamentActiveB = second;
	level.stTournamentDisconnectDeadlineA = 0;
	level.stTournamentDisconnectDeadlineB = 0;
	level.stTournamentDisconnectNoticeA = qfalse;
	level.stTournamentDisconnectNoticeB = qfalse;
	ST_ResetDuelSeriesClient( first );
	ST_ResetDuelSeriesClient( second );
	level.clients[first].sess.stTournamentStatus = ST_TOURNAMENT_PLAYER_ACTIVE;
	level.clients[second].sess.stTournamentStatus = ST_TOURNAMENT_PLAYER_ACTIVE;

	for ( i = 0; i < level.maxclients; i++ ) {
		if ( level.clients[i].pers.connected != CON_CONNECTED ) {
			continue;
		}
		if ( i == first || i == second ) {
			if ( level.clients[i].sess.sessionTeam != TEAM_FREE ) {
				SetTeam( &g_entities[i], "free" );
			}
		}
		else if ( level.clients[i].sess.sessionTeam != TEAM_SPECTATOR ) {
			SetTeam( &g_entities[i], "s" );
		}
	}

	level.stDuelRoundAnnounced = qtrue;
	ST_TournamentSaveState();
	trap->SendServerCommand( -1, va(
		"print \"Tournament %s: %s vs %s (best of %i).\\n\"",
		ST_TournamentStageName(), level.clients[first].pers.netname,
		level.clients[second].pers.netname, ST_TournamentCurrentBestOf() ) );
}

static qboolean ST_TournamentPrepareNextMatch( void ) {
	int first;
	int second;
	int winner;
	int destination;
	int i;

	while ( level.stTournamentPhase == ST_TOURNAMENT_RUNNING ) {
		while ( level.stTournamentMatchCursor < level.stTournamentRoundSize ) {
			first = level.stTournamentRoundSlots[level.stTournamentMatchCursor];
			second = level.stTournamentRoundSlots[level.stTournamentMatchCursor + 1];
			destination = level.stTournamentMatchCursor / 2;
			if ( first >= 0 && second >= 0 ) {
				ST_TournamentActivateMatch( first, second );
				return qtrue;
			}
			winner = first >= 0 ? first : second;
			level.stTournamentNextSlots[destination] = winner;
			level.stTournamentMatchCursor += 2;
		}

		if ( level.stTournamentRoundSize == 2 ) {
			level.stTournamentChampion = level.stTournamentNextSlots[0];
			level.stTournamentActiveA = -1;
			level.stTournamentActiveB = -1;
			level.stTournamentPhase = ST_TOURNAMENT_COMPLETE;
			if ( level.stTournamentChampion >= 0 ) {
				level.clients[level.stTournamentChampion].sess.stTournamentStatus = ST_TOURNAMENT_PLAYER_CHAMPION;
				trap->SendServerCommand( -1, va(
					"cp \"Tournament Champion: %s\"",
					level.clients[level.stTournamentChampion].pers.netname ) );
				trap->SendServerCommand( -1, va(
					"print \"Tournament Champion: %s!\\n\"",
					level.clients[level.stTournamentChampion].pers.netname ) );
			}
			ST_TournamentSaveState();
			return qfalse;
		}

		level.stTournamentRoundSize /= 2;
		level.stTournamentRoundNumber++;
		level.stTournamentMatchCursor = 0;
		for ( i = 0; i < ST_TOURNAMENT_MAX_PLAYERS; i++ ) {
			level.stTournamentRoundSlots[i] =
				i < level.stTournamentRoundSize ? level.stTournamentNextSlots[i] : -1;
			level.stTournamentNextSlots[i] = -1;
		}
	}
	return qfalse;
}

static void ST_TournamentCompleteMatch( int winner, int loser ) {
	if ( level.stTournamentPhase != ST_TOURNAMENT_RUNNING ||
		winner < 0 || loser < 0 ||
		!((winner == level.stTournamentActiveA && loser == level.stTournamentActiveB) ||
		(winner == level.stTournamentActiveB && loser == level.stTournamentActiveA)) ) {
		return;
	}

	if (ST_MvpTournamentForfeit(winner,loser)) return;
	level.clients[winner].sess.stTournamentMatchWins++;
	level.clients[loser].sess.stTournamentMatchLosses++;
	level.clients[winner].sess.stTournamentStatus = ST_TOURNAMENT_PLAYER_REGISTERED;
	level.clients[loser].sess.stTournamentStatus = ST_TOURNAMENT_PLAYER_ELIMINATED;
	level.stTournamentNextSlots[level.stTournamentMatchCursor / 2] = winner;
	level.stTournamentMatchCursor += 2;
	level.stTournamentActiveA = -1;
	level.stTournamentActiveB = -1;
	ST_ResetDuelSeriesClient( winner );
	ST_ResetDuelSeriesClient( loser );
	if ( ST_TournamentClientConnected( loser ) &&
		level.clients[loser].sess.sessionTeam != TEAM_SPECTATOR ) {
		SetTeam( &g_entities[loser], "s" );
	}

	trap->SendServerCommand( -1, va(
		"print \"Tournament: %s advances; %s is eliminated.\\n\"",
		level.clients[winner].pers.netname, level.clients[loser].pers.netname ) );

	if ( ST_TournamentPrepareNextMatch() ) {
		level.stTournamentArenaIndex++;
		level.stTournamentPendingArena = qtrue;
	}
	ST_TournamentSaveState();
}

static qboolean ST_TournamentStart( void ) {
	int shuffled[ST_TOURNAMENT_MAX_PLAYERS];
	int seedOrder[ST_TOURNAMENT_MAX_PLAYERS];
	int bracketSize;
	int i;
	int oldSize;
	int swapIndex;
	int temp;
	int seed;

	if ( level.stTournamentPhase != ST_TOURNAMENT_REGISTRATION ||
		level.stTournamentEntrantCount < 4 ) {
		return qfalse;
	}
	for ( i = 0; i < level.stTournamentEntrantCount; i++ ) {
		if ( !ST_TournamentClientConnected( level.stTournamentEntrants[i] ) ) {
			return qfalse;
		}
		shuffled[i] = level.stTournamentEntrants[i];
	}
	for ( i = level.stTournamentEntrantCount - 1; i > 0; i-- ) {
		swapIndex = Q_irand( 0, i );
		temp = shuffled[i];
		shuffled[i] = shuffled[swapIndex];
		shuffled[swapIndex] = temp;
	}
	for ( i = 0; i < level.stTournamentEntrantCount; i++ ) {
		level.stTournamentEntrants[i] = shuffled[i];
		level.clients[shuffled[i]].sess.stTournamentSeed = i + 1;
		level.clients[shuffled[i]].sess.stTournamentStatus = ST_TOURNAMENT_PLAYER_REGISTERED;
		level.clients[shuffled[i]].sess.stTournamentMatchWins = 0;
		level.clients[shuffled[i]].sess.stTournamentMatchLosses = 0;
	}

	bracketSize = 4;
	while ( bracketSize < level.stTournamentEntrantCount ) {
		bracketSize *= 2;
	}
	seedOrder[0] = 0;
	for ( oldSize = 1; oldSize < bracketSize; oldSize *= 2 ) {
		for ( i = oldSize - 1; i >= 0; i-- ) {
			seed = seedOrder[i];
			seedOrder[i * 2] = seed;
			seedOrder[i * 2 + 1] = oldSize * 2 - 1 - seed;
		}
	}

	level.stTournamentRoundSize = bracketSize;
	level.stTournamentRoundNumber = 1;
	level.stTournamentMatchCursor = 0;
	level.stTournamentArenaIndex = 0;
	level.stTournamentChampion = -1;
	for ( i = 0; i < ST_TOURNAMENT_MAX_PLAYERS; i++ ) {
		level.stTournamentNextSlots[i] = -1;
		if ( i >= level.stTournamentRoundSize ) {
			level.stTournamentRoundSlots[i] = -1;
			continue;
		}
		seed = seedOrder[i];
		level.stTournamentRoundSlots[i] =
			seed < level.stTournamentEntrantCount ? shuffled[seed] : -1;
	}
	level.stTournamentPhase = ST_TOURNAMENT_RUNNING;
	if ( !ST_TournamentPrepareNextMatch() ) {
		return qfalse;
	}
	ST_TournamentSaveState();
	ST_TournamentLoadCurrentArena();
	return qtrue;
}

qboolean ST_TournamentControlsDuel( void ) {
	return level.gametype == GT_DUEL &&
		(level.stTournamentPhase == ST_TOURNAMENT_REGISTRATION ||
		level.stTournamentPhase == ST_TOURNAMENT_RUNNING ||
		level.stTournamentPhase == ST_TOURNAMENT_PAUSED ||
		level.stTournamentPhase == ST_TOURNAMENT_COMPLETE);
}

qboolean ST_TournamentCanEnterArena( int clientNum ) {
	return level.stTournamentPhase == ST_TOURNAMENT_RUNNING &&
		(clientNum == level.stTournamentActiveA || clientNum == level.stTournamentActiveB);
}

qboolean ST_TournamentHandleExit( void ) {
	if ( !ST_TournamentControlsDuel() ) {
		return qfalse;
	}

	if ( level.stTournamentPendingArena && level.stTournamentPhase == ST_TOURNAMENT_RUNNING ) {
		ST_TournamentLoadCurrentArena();
	}
	else if ( !level.restarted ) {
		trap->SendConsoleCommand( EXEC_APPEND, "map_restart 0\n" );
		level.restarted = qtrue;
		level.changemap = NULL;
		level.intermissiontime = 0;
	}
	return qtrue;
}

static qboolean ST_GetDuelists( int *first, int *second ) {
	int a;
	int b;

	if ( level.numPlayingClients != 2 ) {
		return qfalse;
	}
	a = level.sortedClients[0];
	b = level.sortedClients[1];
	if ( a < 0 || a >= level.maxclients || b < 0 || b >= level.maxclients ) {
		return qfalse;
	}
	if ( level.clients[a].pers.connected != CON_CONNECTED ||
		level.clients[b].pers.connected != CON_CONNECTED ||
		level.clients[a].sess.sessionTeam != TEAM_FREE ||
		level.clients[b].sess.sessionTeam != TEAM_FREE ) {
		return qfalse;
	}
	*first = a;
	*second = b;
	return qtrue;
}

static void ST_EnsureDuelSeriesPair( int first, int second ) {
	if ( level.clients[first].sess.stDuelSeriesOpponent == second &&
		level.clients[second].sess.stDuelSeriesOpponent == first ) {
		return;
	}

	level.clients[first].sess.stDuelSeriesWins = 0;
	level.clients[second].sess.stDuelSeriesWins = 0;
	level.clients[first].sess.stDuelSeriesOpponent = second;
	level.clients[second].sess.stDuelSeriesOpponent = first;
}

void ST_AnnounceDuelRound( void ) {
	int first;
	int second;
	char message[512];

	if ( !ST_DuelBestOfEnabled() || level.stDuelRoundAnnounced ||
		!ST_GetDuelists( &first, &second ) ) {
		return;
	}

	ST_EnsureDuelSeriesPair( first, second );
	if ( level.stTournamentPhase == ST_TOURNAMENT_RUNNING ) {
		Com_sprintf( message, sizeof( message ),
			"Tournament %s - Best of %i: %s ^7vs %s",
			ST_TournamentStageName(), ST_DuelBestOf(),
			level.clients[first].pers.netname,
			level.clients[second].pers.netname );
	}
	else {
		Com_sprintf( message, sizeof( message ),
			"Best of %i: %s ^7vs %s",
			ST_DuelBestOf(),
			level.clients[first].pers.netname,
			level.clients[second].pers.netname );
	}
	trap->SendServerCommand( -1, va( "cp \"%s\"", message ) );
	trap->SendServerCommand( -1, va( "print \"%s\\n\"", message ) );
	level.stDuelRoundAnnounced = qtrue;
}

void ST_RecordDuelRound( void ) {
	int first;
	int second;
	int winner = -1;
	int loser = -1;
	int firstScore;
	int secondScore;
	int firstCondition;
	int secondCondition;
	int winsNeeded = ST_DuelRoundsToWin();

	if ( !ST_DuelBestOfEnabled() || !ST_GetDuelists( &first, &second ) ) {
		return;
	}

	ST_EnsureDuelSeriesPair( first, second );
	firstScore = level.clients[first].ps.persistant[PERS_SCORE];
	secondScore = level.clients[second].ps.persistant[PERS_SCORE];
	if ( firstScore > secondScore ) {
		winner = first;
		loser = second;
	}
	else if ( secondScore > firstScore ) {
		winner = second;
		loser = first;
	}
	else {
		firstCondition = level.clients[first].ps.stats[STAT_HEALTH] + level.clients[first].ps.stats[STAT_ARMOR];
		secondCondition = level.clients[second].ps.stats[STAT_HEALTH] + level.clients[second].ps.stats[STAT_ARMOR];
		if ( firstCondition > secondCondition ) {
			winner = first;
			loser = second;
		}
		else if ( secondCondition > firstCondition ) {
			winner = second;
			loser = first;
		}
	}

	if ( winner == -1 ) {
		trap->SetConfigstring( CS_CLIENT_DUELWINNER, "-1" );
		trap->SendServerCommand( -1, "cp \"Round draw - the round will be replayed\"" );
		trap->SendServerCommand( -1, "print \"Saber Trials: round draw; no series point awarded.\\n\"" );
		return;
	}

	level.clients[winner].sess.stDuelSeriesWins++;
	trap->SetConfigstring( CS_CLIENT_DUELWINNER, va( "%i", winner ) );

	if ( level.clients[winner].sess.stDuelSeriesWins >= winsNeeded ) {
		level.stDuelSeriesComplete = qtrue;
		level.stDuelSeriesWinner = winner;
		level.stDuelSeriesLoser = loser;
		level.clients[winner].sess.wins++;
		level.clients[loser].sess.losses++;
		ClientUserinfoChanged( winner );
		ClientUserinfoChanged( loser );
		trap->SendServerCommand( -1, va(
			"cp \"%s wins the series! Final: %i - %i\"",
			level.clients[winner].pers.netname,
			level.clients[winner].sess.stDuelSeriesWins,
			level.clients[loser].sess.stDuelSeriesWins ) );
		trap->SendServerCommand( -1, va(
			"print \"Saber Trials: %s wins the best-of-%i series %i-%i.\\n\"",
			level.clients[winner].pers.netname, ST_DuelBestOf(),
			level.clients[winner].sess.stDuelSeriesWins,
			level.clients[loser].sess.stDuelSeriesWins ) );
	}
	else {
		trap->SendServerCommand( -1, va(
			"cp \"Round won by %s - Series: %i - %i\"",
			level.clients[winner].pers.netname,
			level.clients[winner].sess.stDuelSeriesWins,
			level.clients[loser].sess.stDuelSeriesWins ) );
		trap->SendServerCommand( -1, va(
			"print \"Saber Trials: %s wins the round; series score is %i-%i.\\n\"",
			level.clients[winner].pers.netname,
			level.clients[winner].sess.stDuelSeriesWins,
			level.clients[loser].sess.stDuelSeriesWins ) );
	}
}

void ST_RotateCompletedDuelSeries( void ) {
	int winner = level.stDuelSeriesWinner;
	int loser = level.stDuelSeriesLoser;

	if ( !level.stDuelSeriesComplete ) {
		return;
	}
	if ( level.stTournamentPhase == ST_TOURNAMENT_RUNNING ) {
		ST_TournamentCompleteMatch( winner, loser );
		level.stDuelSeriesComplete = qfalse;
		level.stDuelSeriesWinner = -1;
		level.stDuelSeriesLoser = -1;
		return;
	}

	ST_ResetDuelSeriesClient( winner );
	ST_ResetDuelSeriesClient( loser );
	if ( loser >= 0 && loser < level.maxclients &&
		level.clients[loser].pers.connected == CON_CONNECTED ) {
		SetTeam( &g_entities[loser], "s" );
	}
	level.stDuelSeriesComplete = qfalse;
	level.stDuelSeriesWinner = -1;
	level.stDuelSeriesLoser = -1;
}

void ST_QueueForceMode( int mode ) {
	if ( mode != ST_FORCE_RESTRICTED && mode != ST_FORCE_FULL ) {
		return;
	}

	level.stPendingForceMode = mode;
	trap->SendServerCommand( -1, va( "print \"Saber Trials: %s is queued for the next round.\n\"", ST_ForceModeName( mode ) ) );
}

void ST_QueueGametype( int gametype ) {
	if ( !ST_IsSupportedGametype( gametype ) ) {
		return;
	}

	// Close a legacy tournament only when the accepted change executes.
	// Ordinary gametype changes must not run or announce a tournament reset.
	if ( level.stTournamentPhase != ST_TOURNAMENT_OFF ) {
		ST_TournamentResetAllClients();
		ST_TournamentClearLevelState();
		ST_TournamentSaveState();
	}

	level.stPendingGametype = gametype;
	trap->SendServerCommand( -1, va( "print \"Saber Trials: %s is queued for the next round.\n\"", ST_GametypeName( gametype ) ) );
}

void ST_QueueWeaponsMode( int mode ) {
	if ( mode != ST_WEAPONS_OFF && mode != ST_WEAPONS_ON ) {
		return;
	}

	level.stPendingWeaponsMode = mode;
	trap->SendServerCommand( -1, va(
		"print \"Saber Trials: TFFA/CTF weapon mode %s is queued for the next round.\n\"",
		ST_WeaponsModeName( mode ) ) );
}

void ST_QueueMasterMode( int mode ) {
	if ( mode != ST_MASTER_OFF && mode != ST_MASTER_ON ) {
		return;
	}

	level.stPendingMasterMode = mode;
	trap->SendServerCommand( -1, va(
		"print \"Saber Trials: %s combat is queued for the next round.\n\"",
		ST_MasterModeName( mode ) ) );
}

qboolean ST_ApplyQueuedRuleChanges( void ) {
	char nextMap[MAX_QPATH] = { 0 };
	qboolean hasForceChange = level.stPendingForceMode != -1;
	qboolean hasGametypeChange = level.stPendingGametype != -1;
	qboolean hasWeaponsChange = level.stPendingWeaponsMode != -1;
	qboolean hasMasterChange = level.stPendingMasterMode != -1;
	int targetGametype = hasGametypeChange ? level.stPendingGametype : level.gametype;
	int targetWeaponsMode = hasWeaponsChange ? level.stPendingWeaponsMode : st_weaponsActive.integer;

	if ( !hasForceChange && !hasGametypeChange && !hasWeaponsChange && !hasMasterChange && !ST_CombatPending() ) {
		return qfalse;
	}

	if ( hasForceChange ) {
		trap->Cvar_Set( "st_forceModeActive", va( "%i", level.stPendingForceMode ) );
		trap->Cvar_Set( "g_forcePowerDisable", va( "%i", ST_ForceDisableMask( level.stPendingForceMode ) ) );
		trap->SendServerCommand( -1, va( "print \"Saber Trials: %s is now active.\n\"", ST_ForceModeName( level.stPendingForceMode ) ) );
	}

	if ( hasGametypeChange ) {
		const char *selectedMap = G_RefreshNextMap( targetGametype, qtrue );
		ST_ResetAllDuelSeries();
		trap->Cvar_Set( "g_gametype", va( "%i", targetGametype ) );
		if ( selectedMap && selectedMap[0] ) {
			Q_strncpyz( nextMap, selectedMap, sizeof( nextMap ) );
		}
		trap->SendServerCommand( -1, va( "print \"Saber Trials: %s is now active.\n\"", ST_GametypeName( targetGametype ) ) );
	}

	if ( hasWeaponsChange ) {
		trap->Cvar_Set( "st_weaponsActive", va( "%i", targetWeaponsMode ) );
		trap->SendServerCommand( -1, va(
			"print \"Saber Trials: TFFA/CTF weapon mode %s is now active.\n\"",
			ST_WeaponsModeName( targetWeaponsMode ) ) );
	}

	if ( hasWeaponsChange || hasGametypeChange ) {
		trap->Cvar_Set( "g_weaponDisable", va( "%i",
			ST_WeaponDisableMask( targetGametype, targetWeaponsMode ) ) );
	}

	if ( hasMasterChange ) {
		trap->Cvar_Set( "st_masterModeActive", va( "%i", level.stPendingMasterMode ) );
		trap->SendServerCommand( -1, va(
			"print \"Saber Trials: Master preference set to %s; applies in Saber Trials Combat.\n\"",
			ST_MasterModeName( level.stPendingMasterMode ) ) );
	}

	ST_CombatApply();

	level.stPendingForceMode = -1;
	level.stPendingGametype = -1;
	level.stPendingWeaponsMode = -1;
	level.stPendingMasterMode = -1;
	level.restarted = qtrue;
	level.changemap = NULL;
	level.intermissiontime = 0;

	if ( nextMap[0] ) {
		trap->SendConsoleCommand( EXEC_APPEND, va( "map %s\n", nextMap ) );
	}
	else {
		trap->SendConsoleCommand( EXEC_APPEND, "map_restart 0\n" );
	}

	return qtrue;
}

static qboolean ST_ListContainsGuid( const char *list, const char *guid ) {
	char copy[MAX_CVAR_VALUE_STRING];
	char *token;

	if ( !list || !list[0] || !guid || !guid[0] ) {
		return qfalse;
	}

	Q_strncpyz( copy, list, sizeof( copy ) );
	token = strtok( copy, " ,;" );
	while ( token ) {
		if ( !Q_stricmp( token, guid ) ) {
			return qtrue;
		}
		token = strtok( NULL, " ,;" );
	}
	return qfalse;
}

qboolean ST_IsKickProtected( const gentity_t *target ) {
	if ( !target || !target->client ) {
		return qfalse;
	}
	if ( target->client->pers.localClient ) {
		return qtrue;
	}
	return ST_StaffRoleForClient(target->s.number)>0 || ST_ListContainsGuid( st_staffGuids.string, target->client->pers.guid );
}

void Svcmd_STForceMode_f( void ) {
	char value[MAX_TOKEN_CHARS] = { 0 };
	int mode;

	trap->Argv( 1, value, sizeof( value ) );
	mode = ST_ParseForceMode( value );
	if ( mode == -1 ) {
		trap->Print( "Usage: st_setforcemode <restricted|full>\n" );
		return;
	}
	ST_QueueForceMode( mode );
}

void Svcmd_STGametype_f( void ) {
	char value[MAX_TOKEN_CHARS] = { 0 };
	int gametype;

	trap->Argv( 1, value, sizeof( value ) );
	gametype = ST_ParseGametype( value );
	if ( gametype == -1 ) {
		trap->Print( "Usage: st_gametype <duel|ffa|tffa|ctf>\n" );
		return;
	}
	ST_QueueGametype( gametype );
}

void Svcmd_STWeapons_f( void ) {
	char value[MAX_TOKEN_CHARS] = { 0 };
	int mode;

	trap->Argv( 1, value, sizeof( value ) );
	mode = ST_ParseWeaponsMode( value );
	if ( mode == -1 ) {
		trap->Print( "Usage: st_weapons <on|off>\n" );
		return;
	}
	ST_QueueWeaponsMode( mode );
}

void Svcmd_STMaster_f( void ) {
	char value[MAX_TOKEN_CHARS] = { 0 };
	int mode;

	trap->Argv( 1, value, sizeof( value ) );
	mode = ST_ParseMasterMode( value );
	if ( mode == -1 ) {
		trap->Print( "Usage: st_master <on|off>\n" );
		return;
	}
	ST_QueueMasterMode( mode );
}

void Svcmd_STCancelRules_f( void ) {
	ST_CombatCancel();
	level.stPendingForceMode = -1;
	level.stPendingGametype = -1;
	level.stPendingWeaponsMode = -1;
	level.stPendingMasterMode = -1;
	trap->SendServerCommand( -1, "print \"Saber Trials: queued rule changes were cancelled by an administrator.\n\"" );
}

void Svcmd_STApplyRules_f( void ) {
	if ( !ST_ApplyQueuedRuleChanges() ) {
		trap->Print( "Saber Trials: no rule changes are queued.\n" );
	}
}

void Svcmd_STStatus_f( void ) {
	int i;
	ST_CombatStatus();
	trap->Print( "TFFA team entry: %s\n", level.gametype != GT_TEAM ? "not applicable" :
		(level.stTeamsLocked ? "locked" : "unlocked") );

	trap->Print( "Saber Trials force mode: %s\n", ST_ForceModeName( st_forceModeActive.integer ) );
	trap->Print( "Saber Trials gametype: %s\n", ST_GametypeName( level.gametype ) );
	trap->Print( "Queued force mode: %s\n", level.stPendingForceMode == -1 ? "none" : ST_ForceModeName( level.stPendingForceMode ) );
	trap->Print( "Queued gametype: %s\n", level.stPendingGametype == -1 ? "none" : ST_GametypeName( level.stPendingGametype ) );
	trap->Print( "TFFA/CTF weapons: %s\n", ST_WeaponsModeName( st_weaponsActive.integer ) );
	trap->Print( "Queued TFFA/CTF weapons: %s\n", level.stPendingWeaponsMode == -1 ? "none" : ST_WeaponsModeName( level.stPendingWeaponsMode ) );
	trap->Print( "Master mode (effective): %s\n", ST_MasterModeName( ST_MasterEnabled() ) );
	trap->Print( "Queued Master mode: %s\n", level.stPendingMasterMode == -1 ? "none" : ST_MasterModeName( level.stPendingMasterMode ) );
	trap->Print( "Master tuning: %i saber damage, %ims parry stagger\n",
		Com_Clampi( 10, 150, st_masterSaberDamage.integer ),
		Com_Clampi( 400, 1200, st_masterParryStagger.integer ) );
	if (ST_CombatOption(ST_COMBAT_SHIELDS)) trap->Print( "Shield: %i starting/max, %i points/sec after %ims without damage\n",
		Com_Clampi( 1, 200, st_shieldMax.integer ),
		Com_Clampi( 1, 10, st_shieldRegenAmount.integer ),
		Com_Clampi( 0, 30000, st_shieldRegenDelay.integer ) );
	else trap->Print("Shield: stock spawn armor; no regeneration\n");
	trap->Print("Force Speed: %s\n", ST_CombatOption(ST_COMBAT_SPEED) ? "free level 3" : "player loadout");
	trap->Print( "Duel series: best of %i\n", ST_DuelBestOf() );
	trap->Print( "Saber dismemberment chance: %i%%\n", Com_Clampi( 0, 100, st_dismemberChance.integer ) );
	trap->Print( "Fall damage: %s\n", (dmflags.integer & DF_NO_FALLING) ? "disabled" : "enabled" );
	trap->Print( "Saber damage: SP-style model %i, scale %.2f\n",
		d_saberSPStyleDamage.integer, g_saberDamageScale.value );
	trap->Print( "Perfect parry tuning (requires defense): %ims window, %ims retry, %ims counter\n",
		Com_Clampi( 100, 450, st_parryWindow.integer ),
		Com_Clampi( Com_Clampi( 100, 450, st_parryWindow.integer ) + 100, 1500, st_parryCooldown.integer ),
		Com_Clampi( 250, 1000, st_counterWindow.integer ) );
	trap->Print( "Anti-cheat: %s (observation only; no automatic action)\n",
		st_anticheatMode.integer ? "monitor" : "off" );

	if ( level.gametype == GT_FFA ) {
		trap->Print( "FFA scoreboard statistics:\n" );
		for ( i = 0; i < level.maxclients; i++ ) {
			gclient_t *client = &level.clients[i];

			if ( client->pers.connected != CON_CONNECTED ) {
				continue;
			}
			trap->Print( "  %2i %-24s Shield %i  Speed %i  FFA %i/%i  Duels %i/%i  Perfect parries %i\n",
				i, client->pers.netname,
				client->ps.stats[STAT_ARMOR],
				client->ps.fd.forcePowerLevel[FP_SPEED],
				client->pers.stFfaKills, client->pers.stFfaDeaths,
				client->pers.stPrivateDuelWins, client->pers.stPrivateDuelLosses,
				client->pers.stPerfectParries );
		}
	}
}

static const char *ST_TournamentPlayerStatusName( int status ) {
	switch ( status ) {
	case ST_TOURNAMENT_PLAYER_REGISTERED: return "waiting";
	case ST_TOURNAMENT_PLAYER_ACTIVE: return "fighting";
	case ST_TOURNAMENT_PLAYER_ELIMINATED: return "eliminated";
	case ST_TOURNAMENT_PLAYER_CHAMPION: return "champion";
	default: return "not entered";
	}
}

static void ST_TournamentOutput( int clientNum, const char *message ) {
	if ( clientNum < 0 ) {
		char consoleMessage[512];
		int source = 0;
		int destination = 0;
		while ( message[source] && destination + 1 < (int)sizeof( consoleMessage ) ) {
			if ( message[source] == '\\' && message[source + 1] == 'n' ) {
				consoleMessage[destination++] = '\n';
				source += 2;
			}
			else {
				consoleMessage[destination++] = message[source++];
			}
		}
		consoleMessage[destination] = '\0';
		trap->Print( "%s", consoleMessage );
	}
	else {
		trap->SendServerCommand( clientNum, va( "print \"%s\"", message ) );
	}
}

static void ST_TournamentPrintStatus( int clientNum ) {
	char line[512];
	char arena[MAX_QPATH];
	int i;
	int entrant;
	int secondsRemaining;
	gclient_t *client;

	Com_sprintf( line, sizeof( line ),
		"Saber Trials Tournament: %s, %i/%i players.\\n",
		ST_TournamentPhaseName( level.stTournamentPhase ),
		level.stTournamentEntrantCount, ST_TOURNAMENT_MAX_PLAYERS );
	ST_TournamentOutput( clientNum, line );
	if ( level.stTournamentPhase == ST_TOURNAMENT_REGISTRATION ) {
		secondsRemaining = level.stTournamentRegistrationDeadline > level.time ?
			(level.stTournamentRegistrationDeadline - level.time + 999) / 1000 : 0;
		Com_sprintf( line, sizeof( line ),
			"Automatic start: %i:%02i remaining; at least 4 players required.\\n",
			secondsRemaining / 60, secondsRemaining % 60 );
		ST_TournamentOutput( clientNum, line );
	}
	Com_sprintf( line, sizeof( line ),
		"Format: best of %i; final best of %i.\\n",
		ST_TournamentFormatValue( st_tournamentBestOf.integer ),
		ST_TournamentFormatValue( st_tournamentFinalBestOf.integer ) );
	ST_TournamentOutput( clientNum, line );
	if ( ST_TournamentGetArena( level.stTournamentArenaIndex, arena, sizeof( arena ) ) ) {
		Com_sprintf( line, sizeof( line ), "Arena: %s (rotation %i).\\n",
			arena, level.stTournamentArenaIndex + 1 );
		ST_TournamentOutput( clientNum, line );
	}
	if ( level.stTournamentActiveA >= 0 && level.stTournamentActiveB >= 0 ) {
		Com_sprintf( line, sizeof( line ), "%s: %s vs %s.\\n",
			ST_TournamentStageName(),
			level.clients[level.stTournamentActiveA].pers.netname,
			level.clients[level.stTournamentActiveB].pers.netname );
		ST_TournamentOutput( clientNum, line );
	}
	if ( level.stTournamentChampion >= 0 ) {
		Com_sprintf( line, sizeof( line ), "Champion: %s.\\n",
			level.clients[level.stTournamentChampion].pers.netname );
		ST_TournamentOutput( clientNum, line );
	}
	for ( i = 0; i < level.stTournamentEntrantCount; i++ ) {
		entrant = level.stTournamentEntrants[i];
		if ( entrant < 0 || entrant >= level.maxclients ) {
			continue;
		}
		client = &level.clients[entrant];
		Com_sprintf( line, sizeof( line ),
			"  Seed %i: %s - matches %i/%i - %s.\\n",
			client->sess.stTournamentSeed > 0 ? client->sess.stTournamentSeed : i + 1,
			client->pers.netname[0] ? client->pers.netname : va( "client %i", entrant ),
			client->sess.stTournamentMatchWins,
			client->sess.stTournamentMatchLosses,
			ST_TournamentPlayerStatusName( client->sess.stTournamentStatus ) );
		ST_TournamentOutput( clientNum, line );
	}
}

static void ST_TournamentPrintBracket( int clientNum ) {
	char line[512];
	int i;
	int first;
	int second;
	const char *firstName;
	const char *secondName;

	if ( level.stTournamentPhase == ST_TOURNAMENT_OFF ||
		level.stTournamentPhase == ST_TOURNAMENT_REGISTRATION ) {
		ST_TournamentOutput( clientNum,
			"Tournament bracket is created when registration starts.\\n" );
		return;
	}

	Com_sprintf( line, sizeof( line ), "%s bracket (round %i):\\n",
		ST_TournamentStageName(), level.stTournamentRoundNumber );
	ST_TournamentOutput( clientNum, line );
	for ( i = 0; i < level.stTournamentRoundSize; i += 2 ) {
		first = level.stTournamentRoundSlots[i];
		second = level.stTournamentRoundSlots[i + 1];
		firstName = first >= 0 ? level.clients[first].pers.netname : "BYE";
		secondName = second >= 0 ? level.clients[second].pers.netname : "BYE";
		Com_sprintf( line, sizeof( line ), "  Match %i: %s vs %s%s.\\n",
			i / 2 + 1, firstName, secondName,
			i == level.stTournamentMatchCursor ? " [current]" :
			(i < level.stTournamentMatchCursor ? " [complete]" : "") );
		ST_TournamentOutput( clientNum, line );
	}
}

static qboolean ST_TournamentValidArenaList( const char *list ) {
	const char *p;
	qboolean hasMap = qfalse;

	if ( !list || !list[0] ) {
		return qfalse;
	}
	for ( p = list; *p; p++ ) {
		if ( isalnum( (unsigned char)*p ) || *p == '_' || *p == '-' || *p == '/' ||
			*p == ' ' || *p == ',' ) {
			if ( isalnum( (unsigned char)*p ) ) {
				hasMap = qtrue;
			}
			continue;
		}
		return qfalse;
	}
	return hasMap;
}

void ST_TournamentFrame( void ) {
	qboolean firstConnected;
	qboolean secondConnected;
	int i;

	if ( !ST_TournamentControlsDuel() ) {
		return;
	}
	if ( level.stTournamentPhase == ST_TOURNAMENT_REGISTRATION ) {
		if ( !level.stTournamentRegistrationDeadline ) {
			level.stTournamentRegistrationDeadline = level.time +
				Com_Clampi( 30, 3600, st_tournamentAutoStart.integer ) * 1000;
		}
		if ( level.stTournamentEntrantCount >= 4 &&
			(level.time >= level.stTournamentRegistrationDeadline ||
			level.stTournamentEntrantCount >= ST_TOURNAMENT_MAX_PLAYERS) ) {
			trap->SendServerCommand( -1,
				"print \"Tournament registration closed; the bracket is starting.\\n\"" );
			ST_TournamentStart();
			return;
		}
	}

	if ( !level.intermissiontime && !level.intermissionQueued ) {
		for ( i = 0; i < level.maxclients; i++ ) {
			if ( level.clients[i].pers.connected != CON_CONNECTED ) {
				continue;
			}
			if ( ST_TournamentCanEnterArena( i ) ) {
				level.clients[i].sess.stTournamentStatus = ST_TOURNAMENT_PLAYER_ACTIVE;
				if ( level.clients[i].sess.sessionTeam != TEAM_FREE ) {
					SetTeam( &g_entities[i], "free" );
				}
			}
			else if ( level.clients[i].sess.sessionTeam != TEAM_SPECTATOR ) {
				SetTeam( &g_entities[i], "s" );
			}
		}
	}

	if ( level.stTournamentPhase != ST_TOURNAMENT_RUNNING ||
		level.stTournamentActiveA < 0 || level.stTournamentActiveB < 0 ||
		level.intermissiontime || level.intermissionQueued ||
		level.time - level.startTime < 3000 ) {
		return;
	}

	firstConnected = ST_TournamentClientConnected( level.stTournamentActiveA );
	secondConnected = ST_TournamentClientConnected( level.stTournamentActiveB );
	if ( firstConnected ) {
		level.stTournamentDisconnectDeadlineA = 0;
		level.stTournamentDisconnectNoticeA = qfalse;
	}
	else if ( !level.stTournamentDisconnectDeadlineA ) {
		level.stTournamentDisconnectDeadlineA = level.time + ST_TOURNAMENT_DISCONNECT_GRACE;
		level.stTournamentDisconnectNoticeA = qtrue;
		trap->SendServerCommand( -1,
			"print \"Tournament: a competitor disconnected; 60-second grace period started.\\n\"" );
	}
	if ( secondConnected ) {
		level.stTournamentDisconnectDeadlineB = 0;
		level.stTournamentDisconnectNoticeB = qfalse;
	}
	else if ( !level.stTournamentDisconnectDeadlineB ) {
		level.stTournamentDisconnectDeadlineB = level.time + ST_TOURNAMENT_DISCONNECT_GRACE;
		level.stTournamentDisconnectNoticeB = qtrue;
		trap->SendServerCommand( -1,
			"print \"Tournament: a competitor disconnected; 60-second grace period started.\\n\"" );
	}

	if ( !firstConnected && secondConnected &&
		level.time >= level.stTournamentDisconnectDeadlineA ) {
		ST_TournamentCompleteMatch( level.stTournamentActiveB, level.stTournamentActiveA );
		if ( level.stTournamentPendingArena ) {
			ST_TournamentLoadCurrentArena();
		}
	}
	else if ( firstConnected && !secondConnected &&
		level.time >= level.stTournamentDisconnectDeadlineB ) {
		ST_TournamentCompleteMatch( level.stTournamentActiveA, level.stTournamentActiveB );
		if ( level.stTournamentPendingArena ) {
			ST_TournamentLoadCurrentArena();
		}
	}
	else if ( !firstConnected && !secondConnected &&
		level.time >= level.stTournamentDisconnectDeadlineA &&
		level.time >= level.stTournamentDisconnectDeadlineB ) {
		level.stTournamentPhase = ST_TOURNAMENT_PAUSED;
		ST_TournamentSaveState();
		trap->SendServerCommand( -1,
			"print \"Tournament paused: both competitors disconnected. Administrator action is required.\\n\"" );
	}
}

void Cmd_STTournament_f( gentity_t *ent ) {
	char action[MAX_TOKEN_CHARS];
	int clientNum = ent - g_entities;

	trap->Argv( 1, action, sizeof( action ) );
	if ( !action[0] || !Q_stricmp( action, "status" ) ) {
		ST_TournamentPrintStatus( clientNum );
		return;
	}
	if ( !Q_stricmp( action, "bracket" ) ) {
		ST_TournamentPrintBracket( clientNum );
		return;
	}
	if ( !Q_stricmp( action, "join" ) ) {
		if ( !ST_TournamentAddClient( clientNum ) ) {
			trap->SendServerCommand( clientNum,
				"print \"Unable to join: registration must be open, space must remain, and you cannot already be entered.\\n\"" );
		}
		return;
	}
	if ( !Q_stricmp( action, "leave" ) ) {
		if ( !ST_TournamentRemoveClient( clientNum ) ) {
			trap->SendServerCommand( clientNum,
				"print \"You can only leave during registration.\\n\"" );
		}
		return;
	}
	trap->SendServerCommand( clientNum,
		"print \"Usage: tournament <join|leave|status|bracket>\\n\"" );
}

void Svcmd_STTournament_f( void ) {
	char action[MAX_TOKEN_CHARS];
	char value[MAX_CVAR_VALUE_STRING];
	gclient_t *client;
	int clientNum;
	int format;

	trap->Argv( 1, action, sizeof( action ) );
	if ( !action[0] || !Q_stricmp( action, "status" ) ) {
		ST_TournamentPrintStatus( -1 );
		return;
	}
	if ( !Q_stricmp( action, "bracket" ) ) {
		ST_TournamentPrintBracket( -1 );
		return;
	}
	if ( !Q_stricmp( action, "open" ) ) {
		ST_TournamentResetAllClients();
		ST_TournamentClearLevelState();
		level.stTournamentPhase = ST_TOURNAMENT_REGISTRATION;
		level.stTournamentRegistrationDeadline = level.time +
			Com_Clampi( 30, 3600, st_tournamentAutoStart.integer ) * 1000;
		trap->Cvar_Set( "fraglimit", "1" );
		trap->Cvar_Update( &fraglimit );
		ST_TournamentSaveState();
		trap->SendServerCommand( -1,
			"print \"Tournament registration is open for 5 minutes. Use the Player menu or /tournament join.\\n\"" );
		if ( level.gametype != GT_DUEL ) {
			trap->Cvar_Set( "g_gametype", va( "%i", GT_DUEL ) );
			ST_TournamentLoadCurrentArena();
		}
		return;
	}
	if ( !Q_stricmp( action, "reset" ) ) {
		ST_TournamentResetAllClients();
		ST_TournamentClearLevelState();
		ST_TournamentSaveState();
		trap->SendServerCommand( -1, "print \"Tournament reset. Normal Duel queue restored.\\n\"" );
		return;
	}
	if ( !Q_stricmp( action, "add" ) || !Q_stricmp( action, "remove" ) ) {
		if ( trap->Argc() < 3 ) {
			trap->Print( "Usage: st_tournament %s <player name|client number>\n", action );
			return;
		}
		client = ClientForString( ConcatArgs( 2 ) );
		if ( !client ) {
			return;
		}
		clientNum = client - level.clients;
		if ( !Q_stricmp( action, "add" ) ) {
			if ( !ST_TournamentAddClient( clientNum ) ) {
				trap->Print( "Could not add that player; check registration and capacity.\n" );
			}
		}
		else if ( !ST_TournamentRemoveClient( clientNum ) ) {
			trap->Print( "Could not remove that player; removals are registration-only.\n" );
		}
		return;
	}
	if ( !Q_stricmp( action, "start" ) ) {
		if ( level.gametype != GT_DUEL ) {
			trap->Print( "Tournament must be on a Duel map. Use st_tournament open first.\n" );
		}
		else if ( !ST_TournamentStart() ) {
			trap->Print( "Unable to start: register 4-32 connected players first.\n" );
		}
		return;
	}
	if ( !Q_stricmp( action, "pause" ) ) {
		if ( level.stTournamentPhase != ST_TOURNAMENT_RUNNING ) {
			trap->Print( "Tournament is not running.\n" );
			return;
		}
		level.stTournamentPhase = ST_TOURNAMENT_PAUSED;
		ST_TournamentSaveState();
		trap->SendServerCommand( -1, "print \"Tournament paused by administrator.\\n\"" );
		return;
	}
	if ( !Q_stricmp( action, "resume" ) ) {
		if ( level.stTournamentPhase != ST_TOURNAMENT_PAUSED ||
			!ST_TournamentClientConnected( level.stTournamentActiveA ) ||
			!ST_TournamentClientConnected( level.stTournamentActiveB ) ) {
			trap->Print( "Unable to resume: both active competitors must be connected.\n" );
			return;
		}
		level.stTournamentPhase = ST_TOURNAMENT_RUNNING;
		ST_TournamentActivateMatch( level.stTournamentActiveA, level.stTournamentActiveB );
		trap->SendServerCommand( -1, "print \"Tournament resumed.\\n\"" );
		return;
	}
	if ( !Q_stricmp( action, "forfeit" ) ) {
		if ( trap->Argc() < 3 || level.stTournamentPhase != ST_TOURNAMENT_RUNNING ) {
			trap->Print( "Usage: st_tournament forfeit <active player>\n" );
			return;
		}
		client = ClientForString( ConcatArgs( 2 ) );
		if ( !client ) {
			return;
		}
		clientNum = client - level.clients;
		if ( clientNum != level.stTournamentActiveA && clientNum != level.stTournamentActiveB ) {
			trap->Print( "That player is not in the active match.\n" );
			return;
		}
		ST_TournamentCompleteMatch(
			clientNum == level.stTournamentActiveA ? level.stTournamentActiveB : level.stTournamentActiveA,
			clientNum );
		if ( level.stTournamentPendingArena ) {
			ST_TournamentLoadCurrentArena();
		}
		return;
	}
	if ( !Q_stricmp( action, "format" ) || !Q_stricmp( action, "finalformat" ) ) {
		trap->Argv( 2, value, sizeof( value ) );
		format = atoi( value );
		if ( format != 3 && format != 5 ) {
			trap->Print( "Tournament formats must be 3 or 5.\n" );
			return;
		}
		trap->Cvar_Set( !Q_stricmp( action, "format" ) ?
			"st_tournamentBestOf" : "st_tournamentFinalBestOf", va( "%i", format ) );
		trap->Print( "Tournament %s set to best of %i.\n",
			!Q_stricmp( action, "format" ) ? "matches" : "final", format );
		return;
	}
	if ( !Q_stricmp( action, "arenas" ) ) {
		Q_strncpyz( value, ConcatArgs( 2 ), sizeof( value ) );
		if ( !ST_TournamentValidArenaList( value ) ) {
			trap->Print( "Usage: st_tournament arenas <map1 map2 ...>\n" );
			return;
		}
		trap->Cvar_Set( "st_tournamentArenas", value );
		trap->Print( "Tournament arena rotation: %s\n", value );
		return;
	}

	trap->Print(
		"Usage: st_tournament <open|add|remove|start|status|bracket|format|finalformat|arenas|pause|resume|forfeit|reset>\n" );
}
