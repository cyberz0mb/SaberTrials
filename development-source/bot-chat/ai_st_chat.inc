/* Model personality dialogue takes precedence over role flavour text.
 * Included by ai_util.c; the combat role remains independent of this policy. */

static const char *ST_ChatSkipSpace( const char *p ) {
	for ( ;; ) {
		while ( *p && (unsigned char)*p <= ' ' ) ++p;
		if ( p[0] != '/' || p[1] != '/' ) return p;
		while ( *p && *p != '\n' && *p != '\r' ) ++p;
	}
}

/* Count/select complete, nonempty lines from complete groups. A NULL section
 * checks whether a personality has any usable dialogue at all. No temp arena,
 * newline convention, or fixed leading-byte offset is required. */
static int ST_ChatLines( const char *text, const char *section, int selected,
	char *out, int outSize ) {
	const char *p = text;
	int count = 0;
	if ( out && outSize > 0 ) out[0] = '\0';
	while ( *(p = ST_ChatSkipSpace( p )) ) {
		const char *name = p, *end;
		int nameLen, matches;
		while ( *p && (unsigned char)*p > ' ' && *p != '{' && *p != '}' ) ++p;
		nameLen = (int)(p - name);
		p = ST_ChatSkipSpace( p );
		if ( !nameLen || *p != '{' ) return count;
		end = ++p;
		while ( *end && *end != '}' ) {
			if ( end[0] == '/' && end[1] == '/' ) {
				while ( *end && *end != '\n' && *end != '\r' ) ++end;
			} else ++end;
		}
		if ( !*end ) return count;
		matches = !section || ((int)strlen( section ) == nameLen && !strncmp( name, section, nameLen ));
		while ( p < end ) {
			const char *line = p, *last;
			int length;
			while ( p < end && *p != '\n' && *p != '\r' ) ++p;
			last = p;
			while ( line < last && (unsigned char)*line <= ' ' ) ++line;
			while ( last > line && (unsigned char)last[-1] <= ' ' ) --last;
			length = (int)(last - line);
			if ( matches && length > 0 && length < MAX_CHAT_LINE_SIZE &&
				!(length >= 2 && line[0] == '/' && line[1] == '/') ) {
				if ( count == selected && out && length < outSize ) {
					memcpy( out, line, length );
					out[length] = '\0';
				}
				++count;
			}
			while ( p < end && (*p == '\n' || *p == '\r') ) ++p;
		}
		p = end + 1;
	}
	return count;
}

/* Reject an oversized expansion instead of overrunning currentChat or cutting
 * a UTF-8 character/name in half. Literal percent signs remain literal. */
static int ST_ChatExpand( const char *line, const gentity_t *object,
	const gentity_t *altObject, char *out, int size ) {
	int used = 0;
	while ( *line ) {
		const char *value = line;
		int length = 1;
		if ( line[0] == '%' && (line[1] == 's' || line[1] == 'a') ) {
			const gentity_t *who = line[1] == 's' ? object : altObject;
			value = who && who->client ? who->client->pers.netname : "opponent";
			length = (int)strlen( value );
			line += 2;
		} else {
			if ( line[0] == '%' && line[1] == '%' ) ++line;
			++line;
		}
		if ( used + length >= size ) { out[0] = '\0'; return 0; }
		memcpy( out + used, value, length );
		used += length;
	}
	out[used] = '\0';
	return used != 0;
}

static int ST_ChatSelect( bot_state_t *bs, const char *section,
	const gentity_t *object, const gentity_t *altObject, char *out, int size ) {
	char line[MAX_CHAT_LINE_SIZE];
	int count = ST_ChatLines( gBotChatBuffer[bs->client], section, -1, NULL, 0 );
	if ( !count ) return 0;
	ST_ChatLines( gBotChatBuffer[bs->client], section, Q_irand( 0, count - 1 ), line, sizeof( line ) );
	return ST_ChatExpand( line, object, altObject, out, size );
}

int BotDoChat( bot_state_t *bs, char *section, int always ) {
	if ( !bs->canChat || bs->doChat ) return 0;
	if ( !always && Q_irand( 1, 10 ) > bs->chatFrequency ) return 0;
	if ( !ST_ChatSelect( bs, section, bs->chatObject, bs->chatAltObject,
		bs->currentChat, sizeof( bs->currentChat ) ) ) return 0;
	bs->chatTeam = 0;
	bs->doChat = !strcmp( section, "GeneralGreetings" ) ? 2 : 1;
	bs->chatTime_stored = (int)strlen( bs->currentChat ) * 45 + Q_irand( 1300, 1500 );
	bs->chatTime = level.time + bs->chatTime_stored;
	return 1;
}

void ST_BotTricksterChat( bot_state_t *bs ) {
	static const char *fallback[] = {
		"Relax. I am only passing through.",
		"Your saber looks safer switched off.",
		"I am definitely not behind you.",
		"Was that supposed to be a challenge?"
	};
	char line[MAX_CHAT_LINE_SIZE];
	if ( level.time < bs->stNextChat || bs->doChat ) return;
	bs->stNextChat = level.time + Com_Clampi( 5000, 60000, st_botTricksterChat.integer );
	if ( ST_ChatLines( gBotChatBuffer[bs->client], NULL, -1, NULL, 0 ) ) {
		/* Missing a combat group is not permission to overwrite the character's
		 * voice with a role line. Other groups still play at their own events. */
		const char *section = ST_ChatLines( gBotChatBuffer[bs->client], "CombatChat", -1, NULL, 0 )
			? "CombatChat" : "Hatred";
		if ( !bs->canChat || Q_irand( 1, 10 ) > bs->chatFrequency ) return;
		if ( !ST_ChatSelect( bs, section, bs->currentEnemy, NULL, line, sizeof( line ) ) ) return;
		G_Say( &g_entities[bs->client], NULL, SAY_ALL, line );
		return;
	}
	G_Say( &g_entities[bs->client], NULL, SAY_ALL, fallback[Q_irand( 0, ARRAY_LEN( fallback ) - 1 )] );
}
