/* Display preferences for team games that use red and blue uniforms. */
static qboolean CG_UsesTeamAppearance(int team)
{
	return (cgs.gametype >= GT_TEAM && cgs.gametype != GT_SIEGE && !cgs.jediVmerc &&
		(team == TEAM_RED || team == TEAM_BLUE)) ? qtrue : qfalse;
}

static qboolean CG_UsesModularTeamTint(const char *model)
{
	return (strlen(model) > 5 && !Q_stricmpn(model, "jedi_", 5)) ? qtrue : qfalse;
}

static void CG_ApplyTeamSkin(const char *model, char *skin, int team, vec3_t tint)
{
	if (!cg_teamColorSkins.integer || !CG_UsesTeamAppearance(team))
		return;

	if (CG_UsesModularTeamTint(model)) {
		BG_ValidateSkinForTeam(model, skin, team, tint);
		return;
	}

	const char *teamSkin = team == TEAM_RED ? "red" : "blue";
	char outfit[MAX_QPATH];
	Q_strncpyz(outfit, skin, sizeof(outfit));
	const size_t length = strlen(outfit);
	if (length > 5 && !Q_stricmp(outfit + length - 5, "_blue"))
		outfit[length - 5] = '\0';
	else if (length > 4 && !Q_stricmp(outfit + length - 4, "_red"))
		outfit[length - 4] = '\0';

	char variant[MAX_QPATH];
	if (outfit[0] && Q_stricmp(outfit, "default") && Q_stricmp(outfit, "red") &&
		Q_stricmp(outfit, "blue") && !strchr(outfit, '|') &&
		strlen(outfit) + 1 + strlen(teamSkin) < sizeof(variant)) {
		Com_sprintf(variant, sizeof(variant), "%s_%s", outfit, teamSkin);
		if (BG_FileExists(va("models/players/%s/model_%s.skin", model, variant))) {
			Q_strncpyz(skin, variant, MAX_QPATH);
			return;
		}
	}

	if (BG_FileExists(va("models/players/%s/model_%s.skin", model, teamSkin)))
		Q_strncpyz(skin, teamSkin, MAX_QPATH);
}

static int CG_TeamSaberColor(const centity_t *cent, const clientInfo_t *client)
{
	if (!cg_teamColorSabers.integer || cent->currentState.eType == ET_NPC ||
		!CG_UsesTeamAppearance(client->team))
		return -1;
	return client->team == TEAM_RED ? SABER_RED : SABER_BLUE;
}

static int CG_PlayerSaberColor(const centity_t *cent, const clientInfo_t *client, int slot)
{
	const int teamColor = CG_TeamSaberColor(cent, client);
	return teamColor >= 0 ? teamColor : slot == 0 ? client->icolor1 : client->icolor2;
}
