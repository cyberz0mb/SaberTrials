"""Apply team appearance settings to the current client and server sources."""
import shutil


def wire(frontend, game, source, insert):
    cgame = frontend / 'codemp/cgame'
    shutil.copyfile(source / 'cg_st_team_appearance.inc', cgame / 'cg_st_team_appearance.inc')
    cvars = (source / 'cg_xcvar.h').read_text().splitlines()
    options = [line for line in cvars if line.startswith('XCVAR_DEF( cg_teamColor')]
    assert len(options) == 2
    anchor = 'XCVAR_DEF( cg_forceModel,'
    insert(cgame / 'cg_xcvar.h', anchor, '\n'.join(options) + '\n' + anchor)
    insert(cgame / 'cg_cvar.c', 'static void CG_TeamOverlayChange( void ) {', '''static void CG_TeamSkinChange( void ) {
	if (cgs.gametype < GT_TEAM || cgs.gametype == GT_SIEGE || cgs.jediVmerc)
		return;
	CG_ForceModelChange();
	CG_LoadDeferredPlayers();
}

static void CG_TeamOverlayChange( void ) {''')
    header = cgame / 'cg_local.h'
    insert(header, 'int\t\t\t\tcrystals[2][MAX_BLADES];',
           'int\t\t\t\tcrystals[2][MAX_BLADES];\n\tint\t\t\t\toutfitRGB;')
    patch_players(cgame / 'cg_players.c', insert)
    review = '\tchar crystalReview[8];'
    insert(cgame / 'cg_draw.c', review, '''	extern void CG_ReviewTeamAppearance(void);
	CG_ReviewTeamAppearance();
''' + review)
    patch_server(game / 'codemp/game/g_client.c', insert)


def patch_players(path, insert):
    anchor = 'qboolean BG_ValidateSkinForTeam( const char *modelName, char *skinName, int team, float *colors );'
    insert(path, anchor, anchor + '''
qboolean BG_FileExists(const char *fileName);
#include "cg_st_team_appearance.inc"''')
    insert(path, 'char\t*useSkinName;\n\nretryModel:', 'char\t*useSkinName;\n\tchar fallbackSkin[MAX_QPATH];\n\nretryModel:')
    insert(path, '''	if ( cgs.gametype >= GT_TEAM && !cgs.jediVmerc && cgs.gametype != GT_SIEGE )
	{ //We won't force colors for siege.
		BG_ValidateSkinForTeam( ci->modelName, ci->skinName, ci->team, ci->colorOverride );
		skinName = ci->skinName;
	}
	else
	{
		ci->colorOverride[0] = ci->colorOverride[1] = ci->colorOverride[2] = 0.0f;
	}''', '''	if (Q_stricmp(modelName, ci->modelName)) {
		Q_strncpyz(fallbackSkin, skinName, sizeof(fallbackSkin));
		CG_ApplyTeamSkin(modelName, fallbackSkin, ci->team, ci->colorOverride);
		skinName = fallbackSkin;
	}''')
    insert(path, 'newInfo.icolor2 = atoi(v);', '''newInfo.icolor2 = atoi(v);
	v = Info_ValueForKey(configstring, "outfitrgb");
	newInfo.outfitRGB = strlen(v) == 6 ? ST_CrystalParseHex(v) : -1;''')
    insert(path, '''	if (cgs.gametype >= GT_TEAM	&& !cgs.jediVmerc && cgs.gametype != GT_SIEGE )
	{ //We won't force colors for siege.
		BG_ValidateSkinForTeam( newInfo.modelName, newInfo.skinName, newInfo.team, newInfo.colorOverride );
	}
	else
	{
		newInfo.colorOverride[0] = newInfo.colorOverride[1] = newInfo.colorOverride[2] = 0.0f;
	}''', '	CG_ApplyTeamSkin(newInfo.modelName, newInfo.skinName, newInfo.team, newInfo.colorOverride);')
    insert(path, '''	if (cgs.gametype >= GT_TEAM && !cgs.jediVmerc &&
		(client->team == TEAM_RED || client->team == TEAM_BLUE))
		return NULL;''', '''	if (CG_TeamSaberColor(cent, client) >= 0)
		return NULL;''')
    insert(path, '''static void CG_DoSaberLight(saberInfo_t *saber, const int *crystals)
{''', '''static void CG_DoSaberLight(const centity_t *cent, clientInfo_t *client, int slot)
{
	saberInfo_t *saber = &client->saber[slot];
	const int *crystals = CG_CrystalColors(cent, client, slot);
	const int preset = cent->currentState.eType != ET_NPC && CG_UsesTeamAppearance(client->team)
		? CG_PlayerSaberColor(cent, client, slot) : -1;''')
    insert(path, 'CG_RGBForSaberColor(saber->blade[i].color, rgbs[i]);',
           'CG_RGBForSaberColor(preset >= 0 ? (saber_colors_t)preset : saber->blade[i].color, rgbs[i]);')
    insert(path, '''	else
	{
		if (saberNum == 0)
		{
			scolor = client->icolor1;
		}
		else
		{
			scolor = client->icolor2;
		}
	}

	if (cgs.gametype >= GT_TEAM &&
		cgs.gametype != GT_SIEGE &&
		!cgs.jediVmerc &&
		cent->currentState.eType != ET_NPC)
	{
		if (client->team == TEAM_RED)
		{
			scolor = SABER_RED;
		}
		else if (client->team == TEAM_BLUE)
		{
			scolor = SABER_BLUE;
		}
	}''', '''	else
		scolor = CG_PlayerSaberColor(cent, client, saberNum);''')
    insert(path, 'CG_DoSaberLight(&client->saber[saberNum], crystals);',
           'CG_DoSaberLight(cent, client, saberNum);')
    data = path.read_bytes()
    before = b'CG_DoSaberLight(&ci->saber[l], CG_CrystalColors(cent, ci, l));'
    assert data.count(before) == 2
    path.write_bytes(data.replace(before, b'CG_DoSaberLight(cent, ci, l);'))
    insert(path, '''	else
	{
		legs.shaderRGBA[0] = cent->currentState.customRGBA[0];''', '''	else if (!cg_teamColorSkins.integer && cent->currentState.eType != ET_NPC &&
		CG_UsesTeamAppearance(ci->team) && CG_UsesModularTeamTint(ci->modelName))
	{
		// Older servers only send the forced tint. Use neutral for those clients.
		const int rgb = ci->outfitRGB < 0 ? 0xFFFFFF : ci->outfitRGB;
		for (int channel = 0; channel < 3; ++channel)
			legs.shaderRGBA[channel] = ST_CrystalChannel(rgb, channel);
		legs.shaderRGBA[3] = cent->currentState.customRGBA[3];
	}
	else
	{
		legs.shaderRGBA[0] = cent->currentState.customRGBA[0];''')
    anchor = 'static void CG_DoSaberLight('
    insert(path, anchor, '''#ifdef ST_WORKBENCH_QA
void CG_ReviewTeamAppearance(void)
{
	char phase[32];
	trap->Cvar_VariableStringBuffer("st_reviewTeamAppearance", phase, sizeof(phase));
	if (!phase[0] || !cg.snap)
		return;
	trap->Cvar_Set("st_reviewTeamAppearance", "");
	for (int slot = 0; slot < cgs.maxclients; ++slot) {
		const clientInfo_t *client = &cgs.clientinfo[slot];
		const centity_t *cent = &cg_entities[slot];
		if (!client->infoValid)
			continue;
		const int *crystals = CG_CrystalColors(cent, client, 0);
		Com_Printf("TEAM_APPEARANCE %s %d %s/%s preset=%d rgb=%06X,%06X outfit=%06X defer=%d\\n",
			phase, client->team, client->modelName, client->skinName, CG_PlayerSaberColor(cent, client, 0),
			(unsigned)(crystals ? crystals[0] : -1), (unsigned)(crystals ? crystals[1] : -1),
			(unsigned)client->outfitRGB, client->deferred);
	}
}
#endif

''' + anchor)


def patch_server(path, insert):
    anchor = '\t// update our customRGBA for team colors.'
    insert(path, anchor, '''	const unsigned outfitRGB = (client->ps.customRGBA[0] << 16) |
		(client->ps.customRGBA[1] << 8) | client->ps.customRGBA[2];
	qboolean teamTint = qfalse;
''' + anchor)
    insert(path, '''		if ( colorOverride[0] != 0.0f || colorOverride[1] != 0.0f || colorOverride[2] != 0.0f )
			VectorScaleM( colorOverride, 255.0f, client->ps.customRGBA );
	}

	// bots set their team a few frames later''', '''		if ( colorOverride[0] != 0.0f || colorOverride[1] != 0.0f || colorOverride[2] != 0.0f ) {
			VectorScaleM( colorOverride, 255.0f, client->ps.customRGBA );
			teamTint = qtrue;
		}
	}

	// bots set their team a few frames later''')
    anchor = '\ttrap->GetConfigstring( CS_PLAYERS+clientNum, oldClientinfo, sizeof( oldClientinfo ) );'
    insert(path, anchor, r'''	// Older clients still receive the native team tint through entity state.
	if (teamTint && strlen(buf) + sizeof("outfitrgb\\000000\\") <= sizeof(buf))
		Q_strcat(buf, sizeof(buf), va("outfitrgb\\%06X\\", outfitRGB));

''' + anchor)
