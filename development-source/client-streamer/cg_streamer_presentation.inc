/* Saber Trials client source overlay.
 * Insert this block in codemp/cgame/cg_draw.c immediately before CG_Draw2D.
 * It depends on the cvars and hooks in
 * development-source/bot-roles/patches/client-streamer-broadcast.patch.
 */
#define ST_STREAMER_KILLFEED_MAX 6
#define ST_STREAMER_KILLFEED_TIME 6000

typedef struct stStreamerKill_s {
	int time;
	char attacker[MAX_NETNAME];
	char target[MAX_NETNAME];
	char method[16];
} stStreamerKill_t;

static stStreamerKill_t stStreamerKills[ST_STREAMER_KILLFEED_MAX];
static int stStreamerKillCount;
static int stStreamerKillLastTime;

void ST_AddKillFeedEntry( int attacker, int target, int mod ) {
	stStreamerKill_t *entry;
	const char *method = "DEFEAT";

	if ( target < 0 || target >= MAX_CLIENTS ) {
		return;
	}
	if ( cg.time < stStreamerKillLastTime ) {
		memset( stStreamerKills, 0, sizeof( stStreamerKills ) );
		stStreamerKillCount = 0;
	}
	stStreamerKillLastTime = cg.time;

	if ( stStreamerKillCount == ST_STREAMER_KILLFEED_MAX ) {
		memmove( &stStreamerKills[0], &stStreamerKills[1],
			sizeof( stStreamerKills[0] ) * ( ST_STREAMER_KILLFEED_MAX - 1 ) );
		stStreamerKillCount--;
	}
	entry = &stStreamerKills[stStreamerKillCount++];
	memset( entry, 0, sizeof( *entry ) );
	entry->time = cg.time;

	if ( attacker >= 0 && attacker < MAX_CLIENTS ) {
		Q_strncpyz( entry->attacker, cgs.clientinfo[attacker].name,
			sizeof( entry->attacker ) );
	}
	else {
		Q_strncpyz( entry->attacker, "WORLD", sizeof( entry->attacker ) );
	}
	Q_strncpyz( entry->target, cgs.clientinfo[target].name,
		sizeof( entry->target ) );

	if ( attacker == target || mod == MOD_SUICIDE ) {
		method = "SELF";
	}
	else if ( mod == MOD_SABER ) {
		method = "SABER";
	}
	else if ( mod == MOD_FORCE_DARK ) {
		method = "FORCE";
	}
	else if ( mod == MOD_FALLING ) {
		method = "FALL";
	}
	else if ( mod == MOD_MELEE || mod == MOD_STUN_BATON ) {
		method = "MELEE";
	}
	Q_strncpyz( entry->method, method, sizeof( entry->method ) );
}

static void ST_DrawStreamerKillFeed( void ) {
	vec4_t panelColor = { 0.0f, 0.0f, 0.0f, 0.58f };
	vec4_t textColor = { 1.0f, 1.0f, 1.0f, 1.0f };
	int first = 0;
	int i;
	float y = 34.0f;

	if ( !st_streamerKillFeed.integer ) {
		return;
	}
	while ( first < stStreamerKillCount &&
		cg.time - stStreamerKills[first].time >= ST_STREAMER_KILLFEED_TIME ) {
		first++;
	}
	if ( first > 0 ) {
		memmove( &stStreamerKills[0], &stStreamerKills[first],
			sizeof( stStreamerKills[0] ) * ( stStreamerKillCount - first ) );
		stStreamerKillCount -= first;
	}

	for ( i = stStreamerKillCount - 1; i >= 0; i-- ) {
		char text[2 * MAX_NETNAME + 32];
		int age = cg.time - stStreamerKills[i].time;
		float width;

		textColor[3] = age > 4500 ? Com_Clamp( 0.0f, 1.0f,
			( ST_STREAMER_KILLFEED_TIME - age ) / 1500.0f ) : 1.0f;
		panelColor[3] = 0.58f * textColor[3];
		Com_sprintf( text, sizeof( text ), "%s  [%s]  %s",
			stStreamerKills[i].attacker, stStreamerKills[i].method,
			stStreamerKills[i].target );
		width = Q_min( 278.0f, CG_Text_Width( text, 0.42f, FONT_SMALL2 ) + 12.0f );
		CG_FillRect( 8, y - 12, width, 16, panelColor );
		CG_Text_Paint( 14, y, 0.42f, textColor, text, 0, 0,
			ITEM_TEXTSTYLE_SHADOWEDMORE, FONT_SMALL2 );
		y += 18.0f;
	}
}

static void ST_DrawStreamerPlayerNames( void ) {
	int i;

	if ( !st_streamerPlayerNames.integer || !cg.snap ||
		cg.snap->ps.persistant[PERS_TEAM] != TEAM_SPECTATOR ) {
		return;
	}

	for ( i = 0; i < cgs.maxclients; i++ ) {
		centity_t *cent = &cg_entities[i];
		clientInfo_t *ci = &cgs.clientinfo[i];
		trace_t tr;
		vec3_t labelOrigin;
		vec3_t delta;
		vec4_t labelColor = { 1.0f, 1.0f, 1.0f, 0.92f };
		char playerName[MAX_NETNAME];
		float x, y, width;

		if ( i == cg.snap->ps.clientNum || !ci->infoValid || !cent->currentValid ||
			cent->currentState.eType != ET_PLAYER ||
			( cent->currentState.eFlags & EF_DEAD ) ) {
			continue;
		}
		VectorSubtract( cent->lerpOrigin, cg.refdef.vieworg, delta );
		if ( VectorLengthSquared( delta ) > 4000000.0f ) {
			continue;
		}
		VectorCopy( cent->lerpOrigin, labelOrigin );
		labelOrigin[2] += 52.0f;
		CG_Trace( &tr, cg.refdef.vieworg, NULL, NULL, labelOrigin,
			cg.snap->ps.clientNum, CONTENTS_OPAQUE );
		if ( tr.fraction < 1.0f ) {
			continue;
		}
		if ( !CG_WorldCoordToScreenCoordFloat( labelOrigin, &x, &y ) ) {
			continue;
		}
		if ( ci->team == TEAM_RED ) {
			labelColor[0] = 1.0f;
			labelColor[1] = 0.38f;
			labelColor[2] = 0.32f;
		}
		else if ( ci->team == TEAM_BLUE ) {
			labelColor[0] = 0.35f;
			labelColor[1] = 0.68f;
			labelColor[2] = 1.0f;
		}
		Q_strncpyz( playerName, ci->name, sizeof( playerName ) );
		width = CG_Text_Width( playerName, 0.4f, FONT_SMALL2 );
		CG_Text_Paint( x - width * 0.5f, y, 0.4f, labelColor, playerName,
			0, 0, ITEM_TEXTSTYLE_SHADOWEDMORE, FONT_SMALL2 );
	}
}

static void ST_DrawStreamerMatchClock( void ) {
	vec4_t clockColor = { 1.0f, 0.86f, 0.35f, 1.0f };
	char text[32];
	int elapsed;
	int value;
	int minutes;
	int seconds;
	float width;

	if ( st_streamerMatchClock.integer <= 0 ) {
		return;
	}
	elapsed = Q_max( 0, cg.time - cgs.levelStartTime );
	if ( st_streamerMatchClock.integer == 2 && cgs.timelimit > 0 ) {
		value = Q_max( 0, cgs.timelimit * 60000 - elapsed );
		Com_sprintf( text, sizeof( text ), "REMAINING  %i:%02i",
			value / 60000, ( value / 1000 ) % 60 );
	}
	else {
		value = elapsed;
		minutes = value / 60000;
		seconds = ( value / 1000 ) % 60;
		Com_sprintf( text, sizeof( text ), "ELAPSED  %i:%02i", minutes, seconds );
	}
	width = CG_Text_Width( text, 0.48f, FONT_SMALL2 );
	CG_Text_Paint( 320.0f - width * 0.5f, 16, 0.48f, clockColor, text,
		0, 0, ITEM_TEXTSTYLE_SHADOWEDMORE, FONT_SMALL2 );
}

static qboolean ST_DrawStreamerTeamScores( void ) {
	vec4_t panelColor = { 0.015f, 0.025f, 0.08f, 0.72f };
	vec4_t redColor = { 1.0f, 0.38f, 0.32f, 1.0f };
	vec4_t blueColor = { 0.35f, 0.68f, 1.0f, 1.0f };
	int team;

	if ( !st_streamerTeamOverlay.integer || cgs.gametype < GT_TEAM ) {
		return qfalse;
	}

	for ( team = TEAM_RED; team <= TEAM_BLUE; team++ ) {
		float x = team == TEAM_RED ? 304.0f : 472.0f;
		float y = 61.0f;
		vec4_t *color = team == TEAM_RED ? &redColor : &blueColor;
		char header[32];
		int i;
		int rows = 0;

		for ( i = 0; i < cg.numScores && rows < 8; i++ ) {
			if ( cg.scores[i].team == team ) {
				rows++;
			}
		}
		CG_FillRect( x, 30, 160, 22 + rows * 17, panelColor );
		Com_sprintf( header, sizeof( header ), "%s  %i",
			team == TEAM_RED ? "RED" : "BLUE",
			team == TEAM_RED ? cgs.scores1 : cgs.scores2 );
		CG_Text_Paint( x + 8, 45, 0.45f, *color, header, 0, 0,
			ITEM_TEXTSTYLE_SHADOWEDMORE, FONT_SMALL2 );
		rows = 0;
		for ( i = 0; i < cg.numScores && rows < 8; i++ ) {
			score_t *score = &cg.scores[i];
			char name[MAX_NETNAME];
			char value[16];

			if ( score->team != team || score->client < 0 ||
				score->client >= MAX_CLIENTS ||
				!cgs.clientinfo[score->client].infoValid ) {
				continue;
			}
			Q_strncpyz( name, cgs.clientinfo[score->client].name, sizeof( name ) );
			{
				float nameScale = 0.4f;
				float nameWidth = CG_Text_Width( name, nameScale, FONT_SMALL2 );
				if ( nameWidth > 112.0f ) {
					nameScale *= 112.0f / nameWidth;
				}
				CG_Text_Paint( x + 8, y, nameScale, colorWhite, name, 0, 0,
					ITEM_TEXTSTYLE_SHADOWEDMORE, FONT_SMALL2 );
			}
			Com_sprintf( value, sizeof( value ), "%i", score->score );
			CG_Text_Paint( x + 152 - CG_Text_Width( value, 0.4f, FONT_SMALL2 ),
				y, 0.4f, colorWhite, value, 0, 0,
				ITEM_TEXTSTYLE_SHADOWEDMORE, FONT_SMALL2 );
			y += 17.0f;
			rows++;
		}
	}
	return qtrue;
}

static void ST_DrawStreamerPresentation( void ) {
	vec4_t barColor = { 0.0f, 0.0f, 0.0f, 0.72f };
	vec4_t panelColor = { 0.015f, 0.025f, 0.08f, 0.68f };
	vec4_t accentColor = { 0.35f, 0.78f, 1.0f, 1.0f };
	vec4_t healthColor = { 1.0f, 0.25f, 0.2f, 1.0f };
	vec4_t shieldColor = { 0.25f, 0.72f, 1.0f, 1.0f };
	static qhandle_t shieldIcon;
	char cameraText[128];
	char playerName[MAX_NETNAME];
	char scoreText[32];
	char vitalsText[32];
	int i;
	int rows = 0;
	int maxRows;
	float panelWidth = 164.0f;
	float panelX;
	float vitalsWidth;
	float vitalsX;
	float y;

	if ( st_streamerLetterbox.integer ) {
		CG_FillRect( 0, 0, SCREEN_WIDTH, 30, barColor );
		CG_FillRect( 0, SCREEN_HEIGHT - 30, SCREEN_WIDTH, 30, barColor );
	}

	/* Keep only a compact health/shield readout for an active player. */
	if ( st_streamerCleanHud.integer &&
		cg.snap->ps.persistant[PERS_TEAM] != TEAM_SPECTATOR ) {
		if ( !shieldIcon ) {
			shieldIcon = trap->R_RegisterShaderNoMip( "gfx/hud/i_icon_shieldwall" );
		}
		Com_sprintf( vitalsText, sizeof( vitalsText ), "%i/%i",
			Q_max( 0, cg.predictedPlayerState.stats[STAT_HEALTH] ),
			Q_max( 0, cg.predictedPlayerState.stats[STAT_ARMOR] ) );
		vitalsWidth = CG_Text_Width( vitalsText, 0.55f, FONT_SMALL2 );
		vitalsX = ( SCREEN_WIDTH - ( 16 + 4 + vitalsWidth + 4 + 16 ) ) * 0.5f;
		trap->R_SetColor( healthColor );
		CG_DrawPic( vitalsX, SCREEN_HEIGHT - 24, 16, 16, cgs.media.heartShader );
		trap->R_SetColor( NULL );
		CG_Text_Paint( vitalsX + 20, SCREEN_HEIGHT - 10, 0.55f, colorWhite,
			vitalsText, 0, 0, ITEM_TEXTSTYLE_SHADOWEDMORE, FONT_SMALL2 );
		trap->R_SetColor( shieldColor );
		CG_DrawPic( vitalsX + 24 + vitalsWidth, SCREEN_HEIGHT - 24, 16, 16,
			shieldIcon );
		trap->R_SetColor( NULL );
	}

	if ( cg.showScores ) {
		return;
	}

	if ( ( st_streamerOverlay.integer ||
		( st_streamerTeamOverlay.integer && cgs.gametype >= GT_TEAM ) ) &&
		cg.scoresRequestTime + 2000 < cg.time ) {
		cg.scoresRequestTime = cg.time;
		trap->SendClientCommand( "score" );
	}

	CG_FillRect( 0, 0, SCREEN_WIDTH, 22, barColor );
	if ( cg.snap->ps.persistant[PERS_TEAM] == TEAM_SPECTATOR ) {
		if ( cg.snap->ps.pm_flags & PMF_FOLLOW ) {
			Q_strncpyz( playerName,
				cgs.clientinfo[cg.snap->ps.clientNum].name, sizeof( playerName ) );
			Com_sprintf( cameraText, sizeof( cameraText ),
				"STREAMER  |  FOLLOW: %s  |  FOV %i",
				playerName, Com_Clampi( 60, 120, st_streamerFov.integer ) );
		}
		else {
			Com_sprintf( cameraText, sizeof( cameraText ),
				"STREAMER  |  FREE CAMERA  |  FOV %i  |  SPEED %i",
				Com_Clampi( 60, 120, st_streamerFov.integer ),
				Com_Clampi( 150, 800, st_streamerCameraSpeed.integer ) );
		}
	}
	else {
		Q_strncpyz( playerName,
			cgs.clientinfo[cg.snap->ps.clientNum].name, sizeof( playerName ) );
		Com_sprintf( cameraText, sizeof( cameraText ),
			"STREAMER  |  PLAYER: %s", playerName );
	}
	CG_Text_Paint( 12, 16, 0.48f, accentColor, cameraText, 0, 0,
		ITEM_TEXTSTYLE_SHADOWEDMORE, FONT_SMALL2 );
	ST_DrawStreamerMatchClock();
	ST_DrawStreamerKillFeed();
	ST_DrawStreamerPlayerNames();

	if ( ST_DrawStreamerTeamScores() ) {
		return;
	}
	if ( !st_streamerOverlay.integer ) {
		return;
	}

	maxRows = Q_min( cg.numScores, 10 );
	for ( i = 0; i < maxRows; i++ ) {
		if ( cg.scores[i].client >= 0 && cg.scores[i].client < MAX_CLIENTS &&
			cg.scores[i].team != TEAM_SPECTATOR &&
			cgs.clientinfo[cg.scores[i].client].infoValid ) {
			float desiredWidth = CG_Text_Width(
				cgs.clientinfo[cg.scores[i].client].name, 0.43f,
				FONT_SMALL2 ) + 64.0f;
			panelWidth = Q_max( panelWidth, Q_min( desiredWidth, 252.0f ) );
			rows++;
		}
	}
	if ( rows <= 0 ) {
		return;
	}

	panelX = 632.0f - panelWidth;
	CG_FillRect( panelX, 30, panelWidth, 24 + rows * 18, panelColor );
	CG_Text_Paint( panelX + 10, 46, 0.43f, accentColor, "PLAYERS", 0, 0,
		ITEM_TEXTSTYLE_SHADOWEDMORE, FONT_SMALL2 );
	CG_Text_Paint( panelX + panelWidth - 10 -
		CG_Text_Width( "SCORE", 0.43f, FONT_SMALL2 ), 46, 0.43f,
		accentColor, "SCORE", 0, 0,
		ITEM_TEXTSTYLE_SHADOWEDMORE, FONT_SMALL2 );
	y = 64;
	rows = 0;
	for ( i = 0; i < cg.numScores && rows < 10; i++ ) {
		score_t *score = &cg.scores[i];
		if ( score->client < 0 || score->client >= MAX_CLIENTS ||
			score->team == TEAM_SPECTATOR ||
			!cgs.clientinfo[score->client].infoValid ) {
			continue;
		}
		Q_strncpyz( playerName, cgs.clientinfo[score->client].name,
			sizeof( playerName ) );
		{
			float nameScale = 0.43f;
			float availableWidth = panelWidth - 64.0f;
			float nameWidth = CG_Text_Width( playerName, nameScale, FONT_SMALL2 );
			if ( nameWidth > availableWidth ) {
				nameScale *= availableWidth / nameWidth;
			}
			CG_Text_Paint( panelX + 10, y, nameScale, colorWhite, playerName,
				0, 0, ITEM_TEXTSTYLE_SHADOWEDMORE, FONT_SMALL2 );
		}
		Com_sprintf( scoreText, sizeof( scoreText ), "%i", score->score );
		CG_Text_Paint( panelX + panelWidth - 10 -
			CG_Text_Width( scoreText, 0.43f, FONT_SMALL2 ),
			y, 0.43f, colorWhite, scoreText, 0, 0,
			ITEM_TEXTSTYLE_SHADOWEDMORE, FONT_SMALL2 );
		y += 18;
		rows++;
	}
}

