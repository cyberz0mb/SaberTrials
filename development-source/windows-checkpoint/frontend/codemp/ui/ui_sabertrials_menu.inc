// Saber Trials menu actions. GPL-2.0-only; included by ui_main.c.
// Read live server values into proposal cvars; editing never changes the server.
static void ST_UIVoteInit( void ) {
	char info[MAX_INFO_STRING];
	int gt;
	trap->GetConfigString( CS_SERVERINFO, info, sizeof( info ) );
	gt = atoi( Info_ValueForKey( info, "g_gametype" ) );
	trap->Cvar_Set( "st_uiCurrentGametype", va( "%d", gt ) );
	trap->Cvar_Set( "st_uiVoteGametype", va( "%d", gt ) );
	trap->Cvar_Set( "st_uiVoteTime", Info_ValueForKey( info, "timelimit" ) );
	trap->Cvar_Set( "st_uiVoteFrags", Info_ValueForKey( info, "fraglimit" ) );
	trap->Cvar_Set( "st_uiVoteCaptures", Info_ValueForKey( info, "capturelimit" ) );
	trap->Cvar_Set( "st_uiVoteError", "" );
}

static void ST_UIVoteMaps( void ) {
	char info[MAX_INFO_STRING];
	int i, gt;
	trap->GetConfigString( CS_SERVERINFO, info, sizeof( info ) );
	gt = atoi( Info_ValueForKey( info, "g_gametype" ) );
	UI_LoadArenas();
	for ( i = 0; i < uiInfo.numGameTypes; i++ ) {
		if ( uiInfo.gameTypes[i].gtEnum == gt ) {
			trap->Cvar_Set( "ui_netGametype", va( "%d", i ) );
			trap->Cvar_Update( &ui_netGametype );
			break;
		}
	}
	trap->Cvar_Set( "ui_currentNetMap", "0" );
	trap->Cvar_Update( &ui_currentNetMap );
	if ( i < uiInfo.numGameTypes && UI_MapCountByGameType( qfalse ) > 0 ) {
		Menu_SetFeederSelection( NULL, FEEDER_ALLMAPS, 0, "ingame_callvote" );
	}
}

static qboolean ST_UIVoteNumber( const char *cvar, const char *command, int maximum, qboolean decimal ) {
	char value[64], *end;
	double number;
	trap->Cvar_VariableStringBuffer( cvar, value, sizeof( value ) );
	number = strtod( value, &end );
	if ( !value[0] || end == value || *end || number != number || number < 0 || number > maximum ||
		(!decimal && number != (int)number) ) {
		trap->Cvar_Set( "st_uiVoteError", va( "Enter %s0 to %d.", decimal ? "" : "a whole number from ", maximum ) );
		return qfalse;
	}
	trap->Cmd_ExecuteText( EXEC_APPEND, decimal ? va( "callvote %s %.3f\n", command, number ) :
		va( "callvote %s %d\n", command, (int)number ) );
	return qtrue;
}

static void ST_UICloseVote( void ) {
	trap->Key_SetCatcher( trap->Key_GetCatcher() & ~KEYCATCH_UI );
	trap->Key_ClearStates();
	trap->Cvar_Set( "cl_paused", "0" );
	Menus_CloseAll();
}

static void ST_UIInputFieldReset( const char *cvar ) {
	menuDef_t *menu = Menu_GetFocused();
	itemDef_t *item;
	if ( !menu ) return;
	item = Menu_FindItemByName( menu, !Q_stricmp( cvar, "st_uiHudScale" ) ? "size_value" :
		!Q_stricmp( cvar, "st_uiHudOpacity" ) ? "opacity_value" :
		!Q_stricmp( cvar, "st_uiPortraitSize" ) ? "size_value" :
		!Q_stricmp( cvar, "st_uiYawSpeed" ) ? "st_yaw_value" : "st_accel_value" );
	if ( item && item->type == ITEM_TYPE_EDITFIELD && item->typeData.edit ) {
		item->typeData.edit->paintOffset = 0;
		item->cursorPos = 0;
	}
}

// Keep saved values compact so reopening a field leaves room for typing.
static void ST_UIInputValue( const char *destination, const char *source ) {
	char value[64], *end;
	double number;
	trap->Cvar_VariableStringBuffer( source, value, sizeof( value ) );
	number = strtod( value, &end );
	if ( end != value && !*end && number == number && number >= 0 && number <= 10000 ) {
		trap->Cvar_Set( destination, va( "%.9g", number ) );
	} else {
		trap->Cvar_Set( destination, value );
	}
	ST_UIInputFieldReset( destination );
}

// The title animation is optional and local. Missing footage always keeps the still.
static void ST_UIMenuBackground( void ) {
	fileHandle_t file = 0;
	int length, i;
	const char *roots[] = { "main", "mainMenu" };
	trap->Cvar_Register( NULL, "st_menuMotion", "1", CVAR_ARCHIVE );
	length = trap->FS_Open( "video/sabertrials_menu.roq", &file, FS_READ );
	if ( file ) trap->FS_Close( file );
	trap->Cvar_Set( "st_uiMenuMovie", length > 0 && trap->Cvar_VariableValue( "st_menuMotion" ) != 0 ? "1" : "0" );
	trap->Cvar_Set( "st_uiMenuMotionLabel", trap->Cvar_VariableValue( "st_menuMotion" ) != 0 ? "Menu motion: On" : "Menu motion: Off" );
	// The native UI stretches its 640x480 canvas. Keep the hologram circular.
	for ( i = 0; i < 2; i++ ) {
		menuDef_t *menu = Menus_FindByName( roots[i] );
		itemDef_t *item = menu ? Menu_FindItemByName( menu, "hologram" ) : NULL;
		if ( item && uiInfo.uiDC.xscale > 0 ) {
			float width = 272.0f * uiInfo.uiDC.yscale / uiInfo.uiDC.xscale;
			item->window.rectClient.w = item->window.rect.w = width;
			item->window.rectClient.x = item->window.rect.x = 426.0f - width * 0.5f;
		}
	}
}

#include "ui_sabertrials_profile.inc"
#include "ui_st_handedness.inc"
#include "ui_st_stances.inc"
#include "ui_st_hybrid.inc"
#include "ui_sabertrials_presentation.inc"

static void ST_UIRefreshShell( void ) {
	menuDef_t *menu = Menu_GetFocused();
	qboolean show = menu && (!Q_stricmp( menu->window.name, "ingame" ) ||
		!Q_stricmpn( menu->window.name, "st_pause_", 9 ));
	if ( (trap->Cvar_VariableValue( "st_uiPauseShell" ) != 0) != show )
		trap->Cvar_Set( "st_uiPauseShell", show ? "1" : "0" );
	ST_UIProfilePreview( menu );
 ST_UIHandPreview(menu);
 ST_UIStanceRefresh(menu);
 ST_UIHybridRefresh(menu);
}

extern void Item_RunScript( itemDef_t *item, const char *script );

#include "ui_sabertrials_hud.inc"
#include "ui_sabertrials_photo.inc"

static qboolean ST_UIMenuScript( const char *name ) {
	qboolean sent = qfalse;
	if (ST_UIHybridScript(name)) return qtrue;
	if (ST_UIStanceScript(name)) return qtrue;
	if (ST_UIHudScript(name)) return qtrue;
    if (ST_UIPhotoScript(name)) return qtrue;
	if (!Q_stricmp(name, "stPortraitInit") || !Q_stricmp(name, "stPortraitReset")) {
		trap->Cvar_Register(NULL, "st_portraitMode", "1", CVAR_ARCHIVE);
		trap->Cvar_Register(NULL, "st_portraitTarget", "0", CVAR_ARCHIVE);
		trap->Cvar_Register(NULL, "st_portraitSize", "80", CVAR_ARCHIVE);
		trap->Cvar_Register(NULL, "st_portraitDamage", "1", CVAR_ARCHIVE);
		if (!Q_stricmp(name, "stPortraitReset")) {
			trap->Cvar_Set("st_portraitMode", "1");
			trap->Cvar_Set("st_portraitTarget", "0");
			trap->Cvar_Set("st_portraitSize", "80");
			trap->Cvar_Set("st_portraitDamage", "1");
			trap->Cvar_Set("cg_drawEnemyInfo", "1");
		}
		ST_UIInputValue("st_uiPortraitSize", "st_portraitSize");
		trap->Cvar_Set("st_uiPortraitStatus", "Size: 48-144. Drag or type a number, then Apply size.");
		return qtrue;
	} else if (!Q_stricmp(name, "stPortraitSize")) {
		char value[64], *end;
		double number;
		trap->Cvar_VariableStringBuffer("st_uiPortraitSize", value, sizeof(value));
		number = strtod(value, &end);
		if (end == value || *end || number != number || number < 48 || number > 144) {
			trap->Cvar_Set("st_uiPortraitStatus", "Enter a size from 48 to 144.");
		} else {
			trap->Cvar_Set("st_portraitSize", va("%.6g", number));
			ST_UIInputValue("st_uiPortraitSize", "st_portraitSize");
			trap->Cvar_Set("st_uiPortraitStatus", "Portrait size applied.");
		}
		return qtrue;
	}
	if ( !Q_stricmp( name, "stMenuInit" ) ) {
		ST_UIMenuBackground();
		return qtrue;
	} else if ( !Q_stricmp( name, "stMenuMotion" ) ) {
		menuDef_t *menu = Menu_GetFocused();
		// Reopening also stops any already-running cinematic.
		const char *root = menu && !Q_stricmp( menu->window.name, "mainMenu" ) ? "mainMenu" : "main";
		trap->Cvar_Set( "st_menuMotion", trap->Cvar_VariableValue( "st_menuMotion" ) == 0 ? "1" : "0" );
		Menus_CloseAll();
		Menus_ActivateByName( root );
		return qtrue;
	} else if ( !Q_stricmp( name, "stPauseInit" ) ) {
		trap->Cvar_Set( "cl_paused", "0" );
		return qtrue;
	} else if ( !Q_stricmp( name, "stStreamerSettings" ) || !Q_stricmp( name, "stInputSettings" ) ) {
		menuDef_t *menu = Menus_ActivateByName( "ingame_setup" );
		itemDef_t *item = menu ? Menu_FindItemByName( menu,
			!Q_stricmp( name, "stStreamerSettings" ) ? "streamermenubutton" : "inputmenubutton" ) : NULL;
		if ( item && item->action ) Item_RunScript( item, item->action );
		return qtrue;
	} else if ( !Q_stricmp( name, "stInputInit" ) ) {
		ST_UIInputValue( "st_uiYawSpeed", "cl_yawspeed" );
		ST_UIInputValue( "st_uiMouseAccel", "cl_mouseAccel" );
		trap->Cvar_Set( "st_uiInputStatus", "" );
		return qtrue;
	} else if ( !Q_stricmp( name, "stResetYaw" ) || !Q_stricmp( name, "stResetAccel" ) ||
		!Q_stricmp( name, "stResetInput" ) ) {
		if ( Q_stricmp( name, "stResetAccel" ) ) {
			trap->Cvar_Set( "st_uiYawSpeed", "140" );
			ST_UIInputFieldReset( "st_uiYawSpeed" );
		}
		if ( Q_stricmp( name, "stResetYaw" ) ) {
			trap->Cvar_Set( "st_uiMouseAccel", "0" );
			ST_UIInputFieldReset( "st_uiMouseAccel" );
		}
		trap->Cvar_Set( "st_uiInputStatus", "Defaults selected. Click Apply Input to save." );
		return qtrue;
	} else if ( !Q_stricmp( name, "stApplyInput" ) ) {
		char yawText[64], accelText[64], *yawEnd, *accelEnd;
		double yaw, accel;
		trap->Cvar_VariableStringBuffer( "st_uiYawSpeed", yawText, sizeof( yawText ) );
		trap->Cvar_VariableStringBuffer( "st_uiMouseAccel", accelText, sizeof( accelText ) );
		yaw = strtod( yawText, &yawEnd );
		accel = strtod( accelText, &accelEnd );
		if ( yawEnd == yawText || *yawEnd || yaw != yaw || yaw < 0 || yaw > 10000 ||
			accelEnd == accelText || *accelEnd || accel != accel || accel < 0 || accel > 100 ) {
			trap->Cvar_Set( "st_uiInputStatus", "Use turn speed 0-10000 and accel 0-100." );
		} else {
			trap->Cvar_Set( "cl_yawspeed", va( "%.9g", yaw ) );
			trap->Cvar_Set( "cl_mouseAccel", va( "%.9g", accel ) );
			ST_UIInputValue( "st_uiYawSpeed", "cl_yawspeed" );
			ST_UIInputValue( "st_uiMouseAccel", "cl_mouseAccel" );
			trap->Cvar_Set( "st_uiInputStatus", "Input settings applied." );
		}
		return qtrue;
	} else if ( !Q_stricmp( name, "stVoteInit" ) ) {
		ST_UIVoteInit();
		return qtrue;
	} else if ( !Q_stricmp( name, "stVoteMaps" ) ) {
		ST_UIVoteMaps();
		return qtrue;
	} else if ( !Q_stricmp( name, "stVoteTime" ) ) {
		sent = ST_UIVoteNumber( "st_uiVoteTime", "timelimit", 1440, qtrue );
	} else if ( !Q_stricmp( name, "stVoteFrags" ) ) {
		sent = ST_UIVoteNumber( "st_uiVoteFrags", "fraglimit", 999, qfalse );
	} else if ( !Q_stricmp( name, "stVoteCaptures" ) ) {
		sent = ST_UIVoteNumber( "st_uiVoteCaptures", "capturelimit", 999, qfalse );
	} else if ( !Q_stricmp( name, "stVoteGametype" ) ) {
		int gt = (int)trap->Cvar_VariableValue( "st_uiVoteGametype" );
		if ( gt == GT_FFA || gt == GT_DUEL || gt == GT_TEAM || gt == GT_CTF ) {
			trap->Cmd_ExecuteText( EXEC_APPEND, va( "callvote g_gametype %d\n", gt ) );
			sent = qtrue;
		} else if ( gt == -1 ) {
			trap->Cmd_ExecuteText( EXEC_APPEND, "callvote tournament open\n" );
			sent = qtrue;
		}
	} else if ( !Q_stricmp( name, "stVoteMap" ) ) {
		int index = ui_currentNetMap.integer;
		if ( index >= 0 && index < uiInfo.mapCount && uiInfo.mapList[index].active ) {
			const char *map = uiInfo.mapList[index].mapLoadName, *p;
			for ( p = map; *p; p++ ) {
				if ( !((*p >= 'a' && *p <= 'z') || (*p >= 'A' && *p <= 'Z') ||
					(*p >= '0' && *p <= '9') || *p == '_' || *p == '-' || *p == '/' || *p == '.') ) {
					break;
				}
			}
			if ( map[0] && !*p && !strstr( map, ".." ) ) {
				trap->Cmd_ExecuteText( EXEC_APPEND, va( "callvote map %s\n", map ) );
				sent = qtrue;
			}
		}
		if ( !sent ) trap->Cvar_Set( "st_uiVoteError", "Select an available map for the current game type." );
	} else {
		return qfalse;
	}
	if ( sent ) ST_UICloseVote();
	return qtrue;
}
