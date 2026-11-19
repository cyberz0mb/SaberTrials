/*
===========================================================================
Saber Trials monitor-only anti-cheat telemetry.

This module deliberately never modifies a user command, warns a player,
forces spectator, kicks, or bans. Its score is review evidence, not proof.

Copyright (C) 2026 Saber Trials contributors.

This file is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License version 2 as published by the
Free Software Foundation. See LICENSE.txt in the Saber Trials repository.
===========================================================================
*/

#include "g_local.h"

#define ST_AC_MODE_OFF 0
#define ST_AC_MODE_MONITOR 1
#define ST_AC_CATEGORY_COOLDOWN 500
#define ST_AC_LOG_COOLDOWN 2000

static const char *ST_ACCategoryName( stAntiCheatCategory_t category ) {
	static const char *names[ST_AC_CATEGORY_COUNT] = {
		"timing", "movement", "attack", "input", "command"
	};

	if ( category < 0 || category >= ST_AC_CATEGORY_COUNT ) {
		return "unknown";
	}
	return names[category];
}

static qboolean ST_ACCanMonitor( const gentity_t *ent ) {
	if ( st_anticheatMode.integer != ST_AC_MODE_MONITOR || !ent || !ent->client ) {
		return qfalse;
	}
	if ( ent->client->pers.connected != CON_CONNECTED ||
		(ent->r.svFlags & SVF_BOT) || ent->s.number >= MAX_CLIENTS ) {
		return qfalse;
	}
	return qtrue;
}

static void ST_ACDecay( stAntiCheatState_t *state ) {
	int interval = Com_Clampi( 5, 300, st_acScoreDecay.integer ) * 1000;
	int steps;

	if ( state->lastDecayTime <= 0 || state->lastDecayTime > level.time ) {
		state->lastDecayTime = level.time;
		return;
	}
	steps = (level.time - state->lastDecayTime) / interval;
	if ( steps <= 0 ) {
		return;
	}
	state->score = Q_max( 0, state->score - steps );
	state->lastDecayTime += steps * interval;
}

static void ST_ACRecord( gentity_t *ent, stAntiCheatCategory_t category,
	int weight, const char *reason ) {
	stAntiCheatState_t *state;
	char cleanName[MAX_NETNAME];
	int threshold;

	if ( !ST_ACCanMonitor( ent ) || category < 0 || category >= ST_AC_CATEGORY_COUNT ) {
		return;
	}
	state = &ent->client->pers.stAntiCheat;
	ST_ACDecay( state );
	if ( state->lastCategoryTime[category] > 0 &&
		level.time - state->lastCategoryTime[category] < ST_AC_CATEGORY_COOLDOWN ) {
		return;
	}

	weight = Com_Clampi( 1, 10, weight );
	state->score = Com_Clampi( 0, 1000, state->score + weight );
	state->totalEvents++;
	state->categoryEvents[category]++;
	state->lastCategoryTime[category] = level.time;
	state->lastEventTime = level.time;
	Q_strncpyz( state->lastReason, reason, sizeof( state->lastReason ) );

	threshold = Com_Clampi( 1, 100, st_acLogThreshold.integer );
	if ( (weight >= 3 || state->score >= threshold) &&
		(state->lastLogTime <= 0 || level.time - state->lastLogTime >= ST_AC_LOG_COOLDOWN) ) {
		Q_strncpyz( cleanName, ent->client->pers.netname, sizeof( cleanName ) );
		Q_CleanStr( cleanName );
		G_SecurityLogPrintf(
			"[ST-AC MONITOR] client=%d name=\"%s\" category=%s weight=%d score=%d ping=%d detail=\"%s\" action=none\n",
			ent->s.number, cleanName, ST_ACCategoryName( category ), weight,
			state->score, ent->client->ps.ping, state->lastReason );
		state->lastLogTime = level.time;
	}
}

void ST_AntiCheatMonitorUsercmd( gentity_t *ent, const usercmd_t *ucmd ) {
	stAntiCheatState_t *state;
	int validButtons;
	int invalidButtons;
	int future;
	int stale;
	int attackLimit;
	char reason[128];

	if ( !ST_ACCanMonitor( ent ) || !ucmd ) {
		return;
	}
	state = &ent->client->pers.stAntiCheat;
	future = ucmd->serverTime - level.time;
	stale = level.time - ucmd->serverTime;
	if ( future > 200 ) {
		Com_sprintf( reason, sizeof( reason ), "usercmd time %dms ahead of server clamp", future );
		ST_ACRecord( ent, ST_AC_TIMING, future > 1000 ? 4 : 2, reason );
	}
	else if ( stale > 1000 ) {
		Com_sprintf( reason, sizeof( reason ), "usercmd time %dms behind server clamp", stale );
		ST_ACRecord( ent, ST_AC_TIMING, stale > 5000 ? 3 : 1, reason );
	}

	validButtons = BUTTON_ATTACK | BUTTON_TALK | BUTTON_USE_HOLDABLE |
		BUTTON_GESTURE | BUTTON_WALKING | BUTTON_USE | BUTTON_FORCEGRIP |
		BUTTON_ALT_ATTACK | BUTTON_ANY | BUTTON_FORCEPOWER |
		BUTTON_FORCE_LIGHTNING | BUTTON_FORCE_DRAIN;
	invalidButtons = ucmd->buttons & ~validButtons;
	if ( invalidButtons ) {
		Com_sprintf( reason, sizeof( reason ), "unknown usercmd button bits 0x%X", invalidButtons );
		ST_ACRecord( ent, ST_AC_INPUT, 3, reason );
	}
	if ( ucmd->generic_cmd > GENCMD_GLOAT ) {
		Com_sprintf( reason, sizeof( reason ), "invalid generic command %d", ucmd->generic_cmd );
		ST_ACRecord( ent, ST_AC_INPUT, 3, reason );
	}

	if ( state->attackWindowStart <= 0 || level.time - state->attackWindowStart >= 1000 ) {
		state->attackWindowStart = level.time;
		state->attackPresses = 0;
	}
	if ( (ucmd->buttons & BUTTON_ATTACK) && !(state->lastButtons & BUTTON_ATTACK) ) {
		state->attackPresses++;
		attackLimit = Com_Clampi( 8, 30, st_acAttackLimit.integer );
		if ( state->attackPresses == attackLimit + 1 ) {
			Com_sprintf( reason, sizeof( reason ), "%d primary-attack presses within one second",
				state->attackPresses );
			ST_ACRecord( ent, ST_AC_ATTACK, 1, reason );
		}
	}
	state->lastButtons = ucmd->buttons;
}

void ST_AntiCheatMonitorMovement( gentity_t *ent, const vec3_t previousOrigin, int msec ) {
	float distance;
	float speed;
	float allowance;
	char reason[128];

	if ( !ST_ACCanMonitor( ent ) || msec <= 0 || msec > 200 ||
		ent->client->sess.sessionTeam == TEAM_SPECTATOR || ent->client->noclip ||
		ent->client->ps.pm_type != PM_NORMAL || ent->client->ps.m_iVehicleNum ||
		(ent->client->ps.pm_flags & PMF_TIME_KNOCKBACK) ||
		ent->client->ps.fallingToDeath ) {
		return;
	}

	distance = Distance( previousOrigin, ent->client->ps.origin );
	speed = Q_max( (float)abs( ent->client->ps.speed ),
		VectorLength( ent->client->ps.velocity ) );
	allowance = 256.0f + speed * ((float)msec / 1000.0f) * 3.0f;
	allowance = Q_max( allowance, 1024.0f );
	if ( distance > allowance ) {
		Com_sprintf( reason, sizeof( reason ),
			"server-simulated displacement %.0f exceeded %.0f units in %dms",
			distance, allowance, msec );
		ST_ACRecord( ent, ST_AC_MOVEMENT, 5, reason );
	}
}

void ST_AntiCheatMonitorClientCommand( gentity_t *ent, const char *command,
	qboolean recognized, qboolean blockedCheat ) {
	stAntiCheatState_t *state;
	int commandLimit;
	char cleanCommand[64];
	char reason[128];

	if ( !ST_ACCanMonitor( ent ) ) {
		return;
	}
	state = &ent->client->pers.stAntiCheat;
	if ( state->commandWindowStart <= 0 || level.time - state->commandWindowStart >= 1000 ) {
		state->commandWindowStart = level.time;
		state->commandCount = 0;
	}
	state->commandCount++;
	commandLimit = Com_Clampi( 10, 100, st_acCommandLimit.integer );
	if ( state->commandCount == commandLimit + 1 ) {
		Com_sprintf( reason, sizeof( reason ), "%d client commands within one second",
			state->commandCount );
		ST_ACRecord( ent, ST_AC_COMMAND, 2, reason );
	}

	Q_strncpyz( cleanCommand, command ? command : "", sizeof( cleanCommand ) );
	Q_strstrip( cleanCommand, "\n\r\"", "    " );
	if ( !recognized ) {
		if ( state->unknownWindowStart <= 0 || level.time - state->unknownWindowStart >= 5000 ) {
			state->unknownWindowStart = level.time;
			state->unknownCount = 0;
		}
		state->unknownCount++;
		if ( state->unknownCount == 9 ) {
			Com_sprintf( reason, sizeof( reason ),
				"9 unknown commands within five seconds; latest=%s", cleanCommand );
			ST_ACRecord( ent, ST_AC_COMMAND, 2, reason );
		}
	}
	if ( blockedCheat ) {
		Com_sprintf( reason, sizeof( reason ), "cheat-protected command attempted: %s", cleanCommand );
		ST_ACRecord( ent, ST_AC_COMMAND, 1, reason );
	}
}

static void ST_ACPrintPlayer( int clientNum ) {
	gclient_t *client = &level.clients[clientNum];
	stAntiCheatState_t *state = &client->pers.stAntiCheat;
	char cleanName[MAX_NETNAME];
	int secondsAgo;

	ST_ACDecay( state );
	Q_strncpyz( cleanName, client->pers.netname, sizeof( cleanName ) );
	Q_CleanStr( cleanName );
	secondsAgo = state->lastEventTime > 0 ? Q_max( 0, (level.time - state->lastEventTime) / 1000 ) : -1;
	trap->Print( "%2d %-24s score=%3d events=%3d T/M/A/I/C=%d/%d/%d/%d/%d ping=%d\n",
		clientNum, cleanName, state->score, state->totalEvents,
		state->categoryEvents[ST_AC_TIMING], state->categoryEvents[ST_AC_MOVEMENT],
		state->categoryEvents[ST_AC_ATTACK], state->categoryEvents[ST_AC_INPUT],
		state->categoryEvents[ST_AC_COMMAND], client->ps.ping );
	if ( secondsAgo >= 0 ) {
		trap->Print( "   last=%ds ago: %s\n", secondsAgo, state->lastReason );
	}
}

void Svcmd_STAntiCheat_f( void ) {
	char mode[MAX_TOKEN_CHARS];

	trap->Argv( 1, mode, sizeof( mode ) );
	if ( !Q_stricmp( mode, "off" ) ) {
		trap->Cvar_Set( "st_anticheatMode", "0" );
		trap->Cvar_Update( &st_anticheatMode );
		trap->Print( "Saber Trials Guard is off. Existing observations remain available.\n" );
		return;
	}
	if ( !Q_stricmp( mode, "monitor" ) ) {
		trap->Cvar_Set( "st_anticheatMode", "1" );
		trap->Cvar_Update( &st_anticheatMode );
		trap->Print( "Saber Trials Guard is monitoring only. It will never take automatic action.\n" );
		return;
	}
	if ( !Q_stricmp( mode, "enforce" ) ) {
		trap->Print( "Enforcement is not implemented. Use: st_anticheat monitor\n" );
		return;
	}
	trap->Print( "Usage: st_anticheat <off|monitor>\n" );
}

void Svcmd_STACStatus_f( void ) {
	int i;
	int humans = 0;

	trap->Print( "Saber Trials Guard: %s; observation only, action=none\n",
		st_anticheatMode.integer == ST_AC_MODE_MONITOR ? "monitor" : "off" );
	trap->Print( "Categories: T=timing M=movement A=attack I=input C=command\n" );
	for ( i = 0; i < level.maxclients; i++ ) {
		if ( level.clients[i].pers.connected != CON_CONNECTED ||
			(g_entities[i].r.svFlags & SVF_BOT) ) {
			continue;
		}
		humans++;
		ST_ACPrintPlayer( i );
	}
	if ( !humans ) {
		trap->Print( "No connected human players.\n" );
	}
}

void Svcmd_STACPlayer_f( void ) {
	gclient_t *client;
	int clientNum;

	if ( trap->Argc() < 2 ) {
		trap->Print( "Usage: st_acplayer <player name|client number>\n" );
		return;
	}
	client = ClientForString( ConcatArgs( 1 ) );
	if ( !client ) {
		return;
	}
	clientNum = (int)(client - level.clients);
	if ( g_entities[clientNum].r.svFlags & SVF_BOT ) {
		trap->Print( "Saber Trials Guard does not monitor bots.\n" );
		return;
	}
	ST_ACPrintPlayer( clientNum );
	trap->Print( "This score is review evidence, not proof of cheating. No action was taken.\n" );
}
