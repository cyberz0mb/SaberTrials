/* Local privacy for private saber challenges in FFA and Team FFA. */
static vmCvar_t duelHideParticipants;
static vmCvar_t duelHideOutsiders;
static vmCvar_t duelMuteParticipants;
static vmCvar_t duelMuteOutsiders;
static cgameImport_t duelAudioImports;
static cgameImport_t *duelOriginalImports;
static int duelEventSource = -1;

void CG_DuelPrivacySettings( qboolean initial ) {
	static const struct {
		vmCvar_t *value;
		const char *name, *fallback;
	} settings[] = {
		{ &duelHideParticipants, "cg_hidePrivateDuels", "1" },
		{ &duelHideOutsiders, "cg_hideDuelOutsiders", "1" },
		{ &duelMuteParticipants, "cg_mutePrivateDuels", "1" },
		{ &duelMuteOutsiders, "cg_muteDuelOutsiders", "1" },
	};
	int i;
	for ( i = 0; i < ARRAY_LEN( settings ); ++i ) {
		if ( initial ) {
			trap->Cvar_Register( settings[i].value, settings[i].name, settings[i].fallback, CVAR_ARCHIVE );
		} else {
			trap->Cvar_Update( settings[i].value );
		}
	}
}

static qboolean CG_PrivateDuelView( void ) {
	return cg.snap && cg.snap->ps.pm_type != PM_INTERMISSION &&
		(cgs.gametype == GT_FFA || cgs.gametype == GT_TEAM);
}

/* Consult the snapshot because events can fire before every centity is updated. */
static const entityState_t *CG_DuelSnapshotPlayer( int client ) {
	int i;

	if ( client < 0 || client >= MAX_CLIENTS ) {
		return NULL;
	}

	for ( i = 0; i < cg.snap->numEntities; ++i ) {
		const entityState_t *state = &cg.snap->entities[i];
		if ( state->number == client && state->eType == ET_PLAYER ) {
			return state;
		}
	}

	return NULL;
}

static qboolean CG_DuelFilter( int client, const entityState_t *state, qboolean sound ) {
	const playerState_t *ps;

	if ( !CG_PrivateDuelView() || client < 0 || client >= MAX_CLIENTS ) {
		return qfalse;
	}
	ps = &cg.snap->ps;
	if ( client == ps->clientNum ) {
		return qfalse;
	}
	if ( ps->duelInProgress && ps->duelIndex < MAX_CLIENTS && ps->duelIndex >= 0 ) {
		return client != ps->duelIndex && (sound ? duelMuteOutsiders.integer : duelHideOutsiders.integer);
	}
	if ( !(sound ? duelMuteParticipants.integer : duelHideParticipants.integer) ) {
		return qfalse;
	}
	if ( !state ) {
		state = CG_DuelSnapshotPlayer( client );
	}
	return state && state->bolt1 && !(state->eFlags & EF_DEAD);
}

static int CG_DuelEntityOwner( const entityState_t *state ) {
	if ( state->eType == ET_PLAYER ) {
		return state->number;
	}
	if ( state->boltToPlayer ) {
		return state->boltToPlayer - 1;
	}
	if ( state->saberInFlight && (state->eType == ET_GENERAL || state->eType == ET_MISSILE) ) {
		return state->genericenemyindex - MAX_GENTITIES;
	}
	return -1;
}

qboolean CG_DuelHideEntity( const entityState_t *state ) {
	const int owner = CG_DuelEntityOwner( state );
	return CG_DuelFilter( owner, state->eType == ET_PLAYER ? state : NULL, qfalse );
}

static int CG_DuelEventOwner( const entityState_t *state ) {
	const int event = state->event & ~EV_EVENT_BITS;
	switch ( event ) {
	case EV_SABER_HIT:
	case EV_SABER_BLOCK:
		return state->otherEntityNum2;
	case EV_ENTITY_SOUND:
		return state->clientNum;
	case EV_GENERAL_SOUND:
		if ( state->eFlags & EF_SOUNDTRACKER ) {
			return state->trickedentindex;
		}
		/* New Saber Trials servers tag positional sounds with the speaker plus one. */
		return state->otherEntityNum == ENTITYNUM_NONE ? state->clientNum - 1 : state->number;
	default:
		return state->number;
	}
}

void CG_DuelDispatchEvent( centity_t *cent, vec3_t origin ) {
	const int previous = duelEventSource;
	duelEventSource = CG_DuelEventOwner( &cent->currentState );
	CG_EntityEvent( cent, origin );
	duelEventSource = previous;
}

static int CG_DuelSoundOwner( int entity ) {
	if ( entity >= 0 && entity < MAX_CLIENTS ) {
		return entity;
	}
	if ( entity >= MAX_CLIENTS && entity < ENTITYNUM_WORLD ) {
		const entityState_t *state = &cg_entities[entity].currentState;
		const int owner = CG_DuelEntityOwner( state );
		if ( state->eFlags & EF_SOUNDTRACKER ) {
			return state->trickedentindex;
		}
		if ( owner >= 0 ) {
			return owner;
		}
	}
	return duelEventSource;
}

static void CG_DuelStartSound( const vec3_t origin, int entity, int channel, sfxHandle_t sound ) {
	if ( !CG_DuelFilter( CG_DuelSoundOwner( entity ), NULL, qtrue ) ) {
		duelOriginalImports->S_StartSound( origin, entity, channel, sound );
	}
}

static void CG_DuelLoopSound( int entity, const vec3_t origin, const vec3_t velocity, sfxHandle_t sound ) {
	if ( !CG_DuelFilter( CG_DuelSoundOwner( entity ), NULL, qtrue ) ) {
		duelOriginalImports->S_AddLoopingSound( entity, origin, velocity, sound );
	}
}

static void CG_DuelPlayEffect( int id, vec3_t origin, vec3_t direction, int volume, int radius, qboolean portal ) {
	if ( !CG_DuelFilter( duelEventSource, NULL, qfalse ) ) {
		duelOriginalImports->FX_PlayEffectID( id, origin, direction, volume, radius, portal );
	}
}

static cgameImport_t *CG_DuelSoundImports( cgameImport_t *imports ) {
	duelOriginalImports = imports;
	duelAudioImports = *imports;
	duelAudioImports.S_StartSound = CG_DuelStartSound;
	duelAudioImports.S_AddLoopingSound = CG_DuelLoopSound;
	duelAudioImports.FX_PlayEffectID = CG_DuelPlayEffect;
	return &duelAudioImports;
}

/* The usual hum is added by CG_Player. Keep it audible when only visuals are hidden. */
void CG_DuelHiddenPlayerHum( const centity_t *cent ) {
	const entityState_t *state = &cent->currentState;
	const clientInfo_t *info;
	sfxHandle_t primary = 0;

	if ( state->eType != ET_PLAYER || state->number < 0 || state->number >= MAX_CLIENTS || state->weapon != WP_SABER ||
		state->saberHolstered >= 2 || state->eFlags & EF_DEAD ) {
		return;
	}
	info = &cgs.clientinfo[state->number];
	if ( !info->infoValid ) {
		return;
	}
	if ( info->saber[0].model[0] && !state->saberInFlight ) {
		primary = info->saber[0].soundLoop;
		if ( primary ) {
			trap->S_AddLoopingSound( state->number, cent->lerpOrigin, vec3_origin, primary );
		}
	}
	if ( state->saberHolstered == 0 && info->saber[1].model[0] && info->saber[1].soundLoop &&
		info->saber[1].soundLoop != primary ) {
		trap->S_AddLoopingSound( state->number, cent->lerpOrigin, vec3_origin, info->saber[1].soundLoop );
	}
}
