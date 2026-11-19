/* Bounded .jkb settings reader. Accept normal whitespace instead of assuming
 * that a group's brace is exactly two bytes after its name (CRLF only). */
#ifndef ST_BOT_PROFILE_H
#define ST_BOT_PROFILE_H

static const char *ST_ProfileSpace( const char *p ) {
	for ( ;; ) {
		while ( *p && (unsigned char)*p <= ' ' ) ++p;
		if ( p[0] != '/' || p[1] != '/' ) return p;
		while ( *p && *p != '\n' && *p != '\r' ) ++p;
	}
}

static int ST_ProfileGroup( const char *buf, const char *group, char *out, int size ) {
	const char *p = buf;
	out[0] = '\0';
	while ( *(p = ST_ProfileSpace( p )) ) {
		const char *name = p, *begin, *end;
		int length, depth;
		while ( *p && (unsigned char)*p > ' ' && *p != '{' && *p != '}' ) ++p;
		length = (int)(p - name);
		if ( !length ) return 0;
		p = ST_ProfileSpace( p );
		/* The chat marker is a standalone token, not a settings group. */
		if ( length == 17 && !strncmp( name, "BEGIN_CHAT_GROUPS", 17 ) ) continue;
		if ( *p != '{' ) return 0;
		begin = ++p;
		depth = 1;
		while ( *p && depth ) {
			if ( p[0] == '/' && p[1] == '/' ) {
				while ( *p && *p != '\n' && *p != '\r' ) ++p;
				continue;
			}
			if ( *p == '{' ) ++depth;
			else if ( *p == '}' ) --depth;
			if ( depth ) ++p;
		}
		if ( depth ) return 0;
		end = p++;
		if ( (int)strlen( group ) == length && !strncmp( name, group, length ) ) {
			length = (int)(end - begin);
			if ( length >= size ) return 0;
			memcpy( out, begin, length );
			out[length] = '\0';
			return 1;
		}
	}
	return 0;
}

static int ST_ProfileValue( const char *buf, const char *key, char *out, int size ) {
	const char *p = buf;
	out[0] = '\0';
	while ( *(p = ST_ProfileSpace( p )) ) {
		const char *name = p, *begin, *end;
		int length;
		while ( *p && (unsigned char)*p > ' ' ) ++p;
		length = (int)(p - name);
		while ( *p == ' ' || *p == '\t' ) ++p;
		begin = p;
		while ( *p && *p != '\n' && *p != '\r' && !(p[0] == '/' && p[1] == '/') ) ++p;
		end = p;
		while ( end > begin && (unsigned char)end[-1] <= ' ' ) --end;
		if ( (int)strlen( key ) == length && !strncmp( name, key, length ) ) {
			length = (int)(end - begin);
			if ( length <= 0 || length >= size ) return 0;
			memcpy( out, begin, length );
			out[length] = '\0';
			return 1;
		}
	}
	return 0;
}
#endif
