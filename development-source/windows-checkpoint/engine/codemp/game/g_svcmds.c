/*
===========================================================================
Copyright (C) 1999 - 2005, Id Software, Inc.
Copyright (C) 2000 - 2013, Raven Software, Inc.
Copyright (C) 2001 - 2013, Activision, Inc.
Copyright (C) 2005 - 2015, ioquake3 contributors
Copyright (C) 2013 - 2015, OpenJK contributors

This file is part of the OpenJK source code.

OpenJK is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License version 2 as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see <http://www.gnu.org/licenses/>.
===========================================================================
*/

// this file holds commands that can be executed by the server console, but not remote clients

#include "g_local.h"

/*
==============================================================================

PACKET FILTERING


You can add or remove addresses from the filter list with:

addip <ip>
removeip <ip>

The ip address is specified in dot format, and any unspecified digits will match any value, so you can specify an entire class C network with "addip 192.246.40".

Removeip will only remove an address specified exactly the same way.  You cannot addip a subnet, then removeip a single host.

listip
Prints the current list of filters.

g_filterban <0 or 1>

If 1 (the default), then ip addresses matching the current list will be prohibited from entering the game.  This is the default setting.

If 0, then only addresses matching the list will be allowed.  This lets you easily set up a private game, or a game that only allows players from your local network.


==============================================================================
*/

typedef struct ipFilter_s {
	uint32_t mask, compare;
} ipFilter_t;

#define	MAX_IPFILTERS (1024)

static ipFilter_t	ipFilters[MAX_IPFILTERS];
static int			numIPFilters;

/*
=================
StringToFilter
=================
*/
static qboolean StringToFilter( const char *s, ipFilter_t *f ) {
	char num[128];
	int i, j;
	byteAlias_t b, m;

	b.ui = m.ui = 0u;

	for ( i=0; i<4; i++ ) {
		if ( *s < '0' || *s > '9' ) {
			if ( *s == '*' ) {
				// 'match any'
				// b[i] and m[i] to 0
				s++;
				if ( !*s )
					break;
				s++;
				continue;
			}
			trap->Print( "Bad filter address: %s\n", s );
			return qfalse;
		}

		j = 0;
		while ( *s >= '0' && *s <= '9' )
			num[j++] = *s++;

		num[j] = 0;
		b.b[i] = (byte)atoi( num );
		m.b[i] = 0xFF;

		if ( !*s )
			break;

		s++;
	}

	f->mask = m.ui;
	f->compare = b.ui;

	return qtrue;
}

/*
=================
UpdateIPBans
=================
*/
static void UpdateIPBans( void ) {
	byteAlias_t b, m;
	int i, j;
	char ip[NET_ADDRSTRMAXLEN], iplist_final[MAX_CVAR_VALUE_STRING];

	*iplist_final = 0;
	for ( i=0; i<numIPFilters; i++ ) {
		if ( ipFilters[i].compare == 0xFFFFFFFFu )
			continue;

		b.ui = ipFilters[i].compare;
		m.ui = ipFilters[i].mask;
		*ip = 0;
		for ( j=0; j<4; j++ ) {
			if ( m.b[j] != 0xFF )
				Q_strcat( ip, sizeof( ip ), "*" );
			else
				Q_strcat( ip, sizeof( ip ), va( "%i", b.b[j] ) );
			Q_strcat( ip, sizeof( ip ), (j<3) ? "." : " " );
		}
		if ( strlen( iplist_final )+strlen( ip ) < MAX_CVAR_VALUE_STRING )
			Q_strcat( iplist_final, sizeof( iplist_final ), ip );
		else {
			Com_Printf( "g_banIPs overflowed at MAX_CVAR_VALUE_STRING\n" );
			break;
		}
	}

	trap->Cvar_Set( "g_banIPs", iplist_final );
}

/*
=================
G_FilterPacket
=================
*/
qboolean G_FilterPacket( char *from ) {
	int i;
	uint32_t in;
	byteAlias_t m;
	char *p;

	i = 0;
	p = from;
	while ( *p && i < 4 ) {
		m.b[i] = 0;
		while ( *p >= '0' && *p <= '9' ) {
			m.b[i] = m.b[i]*10 + (*p - '0');
			p++;
		}
		if ( !*p || *p == ':' )
			break;
		i++, p++;
	}

	in = m.ui;

	for ( i=0; i<numIPFilters; i++ ) {
		if ( (in & ipFilters[i].mask) == ipFilters[i].compare )
			return g_filterBan.integer != 0;
	}

	return g_filterBan.integer == 0;
}

/*
=================
AddIP
=================
*/
static void AddIP( char *str ) {
	int i;

	for ( i=0; i<numIPFilters; i++ ) {
		if ( ipFilters[i].compare == 0xFFFFFFFFu )
			break; // free spot
	}
	if ( i == numIPFilters ) {
		if ( numIPFilters == MAX_IPFILTERS ) {
			trap->Print( "IP filter list is full\n" );
			return;
		}
		numIPFilters++;
	}

	if ( !StringToFilter( str, &ipFilters[i] ) )
		ipFilters[i].compare = 0xFFFFFFFFu;

	UpdateIPBans();
}

/*
=================
G_ProcessIPBans
=================
*/
void G_ProcessIPBans( void ) {
	char *s = NULL, *t = NULL, str[MAX_CVAR_VALUE_STRING] = {0};

	Q_strncpyz( str, g_banIPs.string, sizeof( str ) );

	for ( t=s=g_banIPs.string; *t; t=s ) {
		s = strchr( s, ' ' );
		if ( !s )
			break;

		while ( *s == ' ' )
			*s++ = 0;

		if ( *t )
			AddIP( t );
	}
}

/*
=================
Svcmd_AddIP_f
=================
*/
void Svcmd_AddIP_f (void)
{
	char		str[MAX_TOKEN_CHARS];

	if ( trap->Argc() < 2 ) {
		trap->Print("Usage: addip <ip-mask>\n");
		return;
	}

	trap->Argv( 1, str, sizeof( str ) );

	AddIP( str );
}

/*
=================
Svcmd_RemoveIP_f
=================
*/
void Svcmd_RemoveIP_f (void)
{
	ipFilter_t	f;
	int			i;
	char		str[MAX_TOKEN_CHARS];

	if ( trap->Argc() < 2 ) {
		trap->Print("Usage: removeip <ip-mask>\n");
		return;
	}

	trap->Argv( 1, str, sizeof( str ) );

	if (!StringToFilter (str, &f))
		return;

	for (i=0 ; i<numIPFilters ; i++) {
		if (ipFilters[i].mask == f.mask	&&
			ipFilters[i].compare == f.compare) {
			ipFilters[i].compare = 0xffffffffu;
			trap->Print ("Removed.\n");

			UpdateIPBans();
			return;
		}
	}

	trap->Print ( "Didn't find %s.\n", str );
}

void Svcmd_ListIP_f (void)
{
	int		i, count = 0;
	byteAlias_t b;

	for(i = 0; i < numIPFilters; i++) {
		if ( ipFilters[i].compare == 0xffffffffu )
			continue;

		b.ui = ipFilters[i].compare;
		trap->Print ("%i.%i.%i.%i\n", b.b[0], b.b[1], b.b[2], b.b[3]);
		count++;
	}
	trap->Print ("%i bans.\n", count);
}

/*
===================
Svcmd_EntityList_f
===================
*/
void	Svcmd_EntityList_f (void) {
	int			e;
	gentity_t		*check;

	check = g_entities;
	for (e = 0; e < level.num_entities ; e++, check++) {
		if ( !check->inuse ) {
			continue;
		}
		trap->Print("%3i:", e);
		switch ( check->s.eType ) {
		case ET_GENERAL:
			trap->Print("ET_GENERAL          ");
			break;
		case ET_PLAYER:
			trap->Print("ET_PLAYER           ");
			break;
		case ET_ITEM:
			trap->Print("ET_ITEM             ");
			break;
		case ET_MISSILE:
			trap->Print("ET_MISSILE          ");
			break;
		case ET_SPECIAL:
			trap->Print("ET_SPECIAL          ");
			break;
		case ET_HOLOCRON:
			trap->Print("ET_HOLOCRON         ");
			break;
		case ET_MOVER:
			trap->Print("ET_MOVER            ");
			break;
		case ET_BEAM:
			trap->Print("ET_BEAM             ");
			break;
		case ET_PORTAL:
			trap->Print("ET_PORTAL           ");
			break;
		case ET_SPEAKER:
			trap->Print("ET_SPEAKER          ");
			break;
		case ET_PUSH_TRIGGER:
			trap->Print("ET_PUSH_TRIGGER     ");
			break;
		case ET_TELEPORT_TRIGGER:
			trap->Print("ET_TELEPORT_TRIGGER ");
			break;
		case ET_INVISIBLE:
			trap->Print("ET_INVISIBLE        ");
			break;
		case ET_NPC:
			trap->Print("ET_NPC              ");
			break;
		case ET_BODY:
			trap->Print("ET_BODY             ");
			break;
		case ET_TERRAIN:
			trap->Print("ET_TERRAIN          ");
			break;
		case ET_FX:
			trap->Print("ET_FX               ");
			break;
		default:
			trap->Print("%-3i                ", check->s.eType);
			break;
		}

		if ( check->classname ) {
			trap->Print("%s", check->classname);
		}
		trap->Print("\n");
	}
}

qboolean StringIsInteger( const char *s );
/*
===================
ClientForString
===================
*/
gclient_t	*ClientForString( const char *s ) {
	gclient_t	*cl;
	int			idnum;
	char		cleanInput[MAX_STRING_CHARS];

	// numeric values could be slot numbers
	if ( StringIsInteger( s ) ) {
		idnum = atoi( s );
		if ( idnum >= 0 && idnum < level.maxclients ) {
			cl = &level.clients[idnum];
			if ( cl->pers.connected == CON_CONNECTED ) {
				return cl;
			}
		}
	}

	Q_strncpyz( cleanInput, s, sizeof(cleanInput) );
	Q_StripColor( cleanInput );

	// check for a name match
	for ( idnum=0,cl=level.clients ; idnum < level.maxclients ; idnum++,cl++ ) {
		if ( cl->pers.connected != CON_CONNECTED ) {
			continue;
		}
		if ( !Q_stricmp( cl->pers.netname_nocolor, cleanInput ) ) {
			return cl;
		}
	}

	trap->Print( "User %s is not on the server\n", s );
	return NULL;
}

/*
===================
ST_NormalizeClientIPv4

The engine stores remote addresses as IPv4:port.  The legacy IP filter list
expects only the four IPv4 octets.
===================
*/
static qboolean ST_NormalizeClientIPv4( const char *address, char *out, size_t outSize ) {
	char copy[NET_ADDRSTRMAXLEN];
	char trailing;
	char *port;
	int octets[4];
	int i;

	if ( !address || !address[0] ) {
		return qfalse;
	}

	Q_strncpyz( copy, address, sizeof( copy ) );
	port = strchr( copy, ':' );
	if ( port ) {
		*port = '\0';
	}

	if ( sscanf( copy, "%d.%d.%d.%d%c",
		&octets[0], &octets[1], &octets[2], &octets[3], &trailing ) != 4 ) {
		return qfalse;
	}

	for ( i = 0; i < 4; i++ ) {
		if ( octets[i] < 0 || octets[i] > 255 ) {
			return qfalse;
		}
	}

	Com_sprintf( out, outSize, "%d.%d.%d.%d",
		octets[0], octets[1], octets[2], octets[3] );
	return qtrue;
}

static qboolean ST_IPFilterExists( const char *address ) {
	ipFilter_t filter;
	int i;

	if ( !StringToFilter( address, &filter ) ) {
		return qfalse;
	}

	for ( i = 0; i < numIPFilters; i++ ) {
		if ( ipFilters[i].compare == 0xFFFFFFFFu ) {
			continue;
		}
		if ( ipFilters[i].mask == filter.mask && ipFilters[i].compare == filter.compare ) {
			return qtrue;
		}
	}

	return qfalse;
}

/*
===================
Svcmd_STBan_f

st_ban <player name|client number>
Adds the connected player's exact IPv4 address to the persistent OpenJK ban
list and disconnects them.  This command is server-console/RCON only.
===================
*/
void Svcmd_STBan_f( void ) {
	char target[MAX_TOKEN_CHARS];
	char address[NET_ADDRSTRMAXLEN];
	char displayName[MAX_NETNAME];
	gclient_t *client;
	int clientNum;
	qboolean alreadyBanned;

	if ( trap->Argc() != 2 ) {
		trap->Print( "Usage: st_ban <player name|client number>\n" );
		return;
	}

	trap->Argv( 1, target, sizeof( target ) );
	client = ClientForString( target );
	if ( !client ) {
		return;
	}

	clientNum = (int)(client - level.clients);
	if ( g_entities[clientNum].r.svFlags & SVF_BOT ) {
		trap->Print( "Saber Trials: bots cannot be IP-banned.\n" );
		return;
	}
	if ( client->pers.localClient ) {
		trap->Print( "Saber Trials: the local host cannot be IP-banned.\n" );
		return;
	}
	if ( !g_filterBan.integer ) {
		trap->Print( "Saber Trials: st_ban is unavailable while g_filterBan is 0 (allow-list mode). Set g_filterBan 1 first.\n" );
		return;
	}
	if ( !ST_NormalizeClientIPv4( client->sess.IP, address, sizeof( address ) ) ) {
		trap->Print( "Saber Trials: this player's address is not a supported IPv4 address.\n" );
		return;
	}

	alreadyBanned = ST_IPFilterExists( address );
	if ( !alreadyBanned ) {
		AddIP( address );
		if ( !ST_IPFilterExists( address ) ) {
			trap->Print( "Saber Trials: failed to add the address to the IP-ban list; the player was not disconnected.\n" );
			return;
		}
	}

	Q_strncpyz( displayName, client->pers.netname_nocolor, sizeof( displayName ) );
	G_SecurityLogPrintf( "Saber Trials st_ban: client %d (%s) IP %s%s\n",
		clientNum, displayName, address, alreadyBanned ? " was already listed" : "" );
	trap->Print( "Saber Trials: banned %s (client %d, IP %s)%s.\n",
		displayName, clientNum, address, alreadyBanned ? "; address was already listed" : "" );
	trap->DropClient( clientNum, "Banned by a Saber Trials administrator." );
}

static void Svcmd_STCmdList_f( void ) {
	trap->Print( "Saber Trials server commands:\n" );
	trap->Print("  st_combat <original|trials>                       Queue combat preset\n");
	trap->Print("  st_combatoption <option> <on|off>                  Queue individual combat option\n");
	trap->Print( "  st_cmdlist                                      Show this list\n" );
	trap->Print( "  st_lockteams <on|off>                           Lock/unlock TFFA team entry now\n" );
	trap->Print( "  st_status                                       Show active and queued rules\n" );
	trap->Print( "  st_setforcemode <restricted|full>               Queue Force mode\n" );
	trap->Print( "  st_gametype <duel|ffa|tffa|ctf>                 Queue game type\n" );
	trap->Print( "  st_weapons <on|off>                             Queue TFFA/CTF weapons\n" );
	trap->Print( "  st_master <on|off>                              Queue Master Mode\n" );
	trap->Print( "  st_applyrules                                    Apply queued rules now\n" );
	trap->Print( "  st_cancelrules                                   Cancel queued rules\n" );
	trap->Print( "  st_ban <player name|client number>               Ban a human by IP\n" );
	trap->Print( "  st_addbot <role> [red|blue] [skill 1-5]          Add a role bot\n" );
	trap->Print( "  st_kickbot <bot name|client number>              Remove a bot\n" );
	trap->Print( "  st_botstatus                                     List bots, roles, and teams\n" );
	trap->Print( "  st_anticheat <off|monitor>                       Set Guard mode\n" );
	trap->Print( "  st_acstatus                                      Show Guard summary\n" );
	trap->Print( "  st_acplayer <player name|client number>           Show player Guard details\n" );
	trap->Print( "  st_tournament <action>                           Manage Tournament\n" );
	trap->Print( "Saber Trials settings: cvarlist st_*\n" );
}

/*
===================
Svcmd_ForceTeam_f

forceteam <player> <team>
===================
*/
void	Svcmd_ForceTeam_f( void ) {
	gclient_t	*cl;
	char		str[MAX_TOKEN_CHARS];

	if ( trap->Argc() < 3 ) {
		trap->Print("Usage: forceteam <player> <team>\n");
		return;
	}

	// find the player
	trap->Argv( 1, str, sizeof( str ) );
	cl = ClientForString( str );
	if ( !cl ) {
		return;
	}

	// set the team
	trap->Argv( 2, str, sizeof( str ) );
	SetTeam( &g_entities[cl - level.clients], str );
}

char *ConcatArgs( int start );
void Svcmd_Say_f( void ) {
	char *p = NULL;
	// don't let text be too long for malicious reasons
	char text[MAX_SAY_TEXT] = {0};

	if ( trap->Argc () < 2 )
		return;

	p = ConcatArgs( 1 );

	if ( strlen( p ) >= MAX_SAY_TEXT ) {
		p[MAX_SAY_TEXT-1] = '\0';
		G_SecurityLogPrintf( "Cmd_Say_f from -1 (server) has been truncated: %s\n", p );
	}

	Q_strncpyz( text, p, sizeof(text) );
	Q_strstrip( text, "\n\r", "  " );

	//G_LogPrintf( "say: server: %s\n", text );
	trap->SendServerCommand( -1, va("print \"server: %s\n\"", text ) );
}

typedef struct svcmd_s {
	const char	*name;
	void		(*func)(void);
	qboolean	dedicated;
} svcmd_t;

int svcmdcmp( const void *a, const void *b ) {
	return Q_stricmp( (const char *)a, ((svcmd_t*)b)->name );
}

svcmd_t svcmds[] = {
	{ "addbot",						Svcmd_AddBot_f,						qfalse },
	{ "addip",						Svcmd_AddIP_f,						qfalse },
	{ "botlist",					Svcmd_BotList_f,					qfalse },
	{ "entitylist",					Svcmd_EntityList_f,					qfalse },
	{ "forceteam",					Svcmd_ForceTeam_f,					qfalse },
	{ "game_memory",				Svcmd_GameMem_f,					qfalse },
	{ "listip",						Svcmd_ListIP_f,						qfalse },
	{ "removeip",					Svcmd_RemoveIP_f,					qfalse },
	{ "say",						Svcmd_Say_f,						qtrue },
	{ "st_acplayer",				Svcmd_STACPlayer_f,				qfalse },
	{ "st_acstatus",				Svcmd_STACStatus_f,				qfalse },
	{ "st_anticheat",				Svcmd_STAntiCheat_f,			qfalse },
	{ "st_addbot",					Svcmd_STAddBot_f,				qfalse },
	{ "st_applyrules",				Svcmd_STApplyRules_f,				qfalse },
	{ "st_ban",						Svcmd_STBan_f,						qfalse },
	{ "st_botstatus",				Svcmd_STBotStatus_f,			qfalse },
	{ "st_cancelrules",			Svcmd_STCancelRules_f,			qfalse },
	{ "st_combat", Svcmd_STCombat_f, qfalse },
	{ "st_combatoption", Svcmd_STCombatOption_f, qfalse },
	{ "st_cmdlist",				Svcmd_STCmdList_f,				qfalse },
	{ "st_lockteams", Svcmd_STLockTeams_f, qfalse },
	{ "st_setforcemode",			Svcmd_STForceMode_f,				qfalse },
	{ "st_gametype",				Svcmd_STGametype_f,				qfalse },
	{ "st_kickbot",					Svcmd_STKickBot_f,				qfalse },
	{ "st_queue_forcemode",		Svcmd_STForceMode_f,				qfalse },
	{ "st_queue_gametype",		Svcmd_STGametype_f,				qfalse },
	{ "st_master",					Svcmd_STMaster_f,					qfalse },
	{ "st_status",					Svcmd_STStatus_f,					qfalse },
	{ "st_tournament",				Svcmd_STTournament_f,				qfalse },
	{ "st_weapons",					Svcmd_STWeapons_f,					qfalse },
	{ "toggleallowvote",			Svcmd_ToggleAllowVote_f,			qfalse },
	{ "toggleuserinfovalidation",	Svcmd_ToggleUserinfoValidation_f,	qfalse },
};
static const size_t numsvcmds = ARRAY_LEN( svcmds );

/*
=================
ConsoleCommand

=================
*/
qboolean	ConsoleCommand( void ) {
	char	cmd[MAX_TOKEN_CHARS] = {0};
	svcmd_t	*command = NULL;

	trap->Argv( 0, cmd, sizeof( cmd ) );

	command = (svcmd_t *)Q_LinearSearch( cmd, svcmds, numsvcmds, sizeof( svcmds[0] ), svcmdcmp );
	if ( !command )
		return qfalse;

	if ( command->dedicated && !dedicated.integer )
		return qfalse;

	command->func();
	return qtrue;
}

