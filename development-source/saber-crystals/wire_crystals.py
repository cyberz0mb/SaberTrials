from pathlib import Path
import shutil


def wire(source, frontend, game, insert):
    ui = frontend / 'codemp/ui'
    cg = frontend / 'codemp/cgame'
    qagame = game / 'codemp/game'
    for folder in (ui, cg, qagame):
        shutil.copyfile(source/'st_crystal.h', folder/'st_crystal.h')
    for folder in (ui, cg):
        shutil.copyfile(source/'st_crystal_blade.inc', folder/'st_crystal_blade.inc')
    patch_game(qagame/'g_client.c', insert)
    patch_cgame(cg, insert)
    patch_ui(source, ui, insert)


def patch_game(path, insert):
    insert(path, '#include "g_local.h"', '#include "g_local.h"\n#include "st_crystal.h"')
    anchor = '\ttrap->GetConfigstring( CS_PLAYERS+clientNum, oldClientinfo, sizeof( oldClientinfo ) );'
    insert(path, anchor, '''	for (int saber = 0; saber < 2; ++saber) {
		int colors[MAX_BLADES];
		if (ST_CrystalParse(Info_ValueForKey(userinfo, stCrystalCvars[saber]), colors)) {
			char crystal[ST_CRYSTAL_TEXT_SIZE];
			ST_CrystalFormat(colors, crystal);
			// This configstring uses trailing separators. Append without
			// changing the native player info format.
			if (crystal[0] && strlen(buf) + strlen(stCrystalKeys[saber]) + strlen(crystal) + 2 < sizeof(buf))
				Q_strcat(buf, sizeof(buf), va("%s\\\\%s\\\\", stCrystalKeys[saber], crystal));
		}
	}

''' + anchor)


def patch_cgame(folder, insert):
    cvars = folder/'cg_xcvar.h'
    anchor = 'XCVAR_DEF( cg_saberTrail,'
    insert(cvars, anchor, 'XCVAR_DEF( cg_crystalWhiteCore, "0", NULL, CVAR_ARCHIVE )\n' + anchor)
    header = folder/'cg_local.h'
    insert(header, '\tint\t\t\t\ticolor2;', '\tint\t\t\t\ticolor2;\n\tint\t\t\t\tcrystals[2][MAX_BLADES];')
    players = folder/'cg_players.c'
    insert(players, '#include "game/bg_saga.h"',
           '#include "game/bg_saga.h"\n#include "st_crystal.h"\n#include "st_crystal_blade.inc"')
    insert(players, '\tnewInfo.icolor2 = atoi(v);', '''	newInfo.icolor2 = atoi(v);
	for (int saber = 0; saber < 2; ++saber)
		ST_CrystalParse(Info_ValueForKey(configstring, stCrystalKeys[saber]), newInfo.crystals[saber]);''')
    insert(players, 'static void CG_DoSaberLight( saberInfo_t *saber )', '''// Respect the same team and class rules used by the stock blade.
static const int *CG_CrystalColors(const centity_t *cent, const clientInfo_t *client, int saber)
{
	if (cent->currentState.eType == ET_NPC || cgs.gametype == GT_SIEGE)
		return NULL;
	if (cgs.gametype >= GT_TEAM && !cgs.jediVmerc &&
		(client->team == TEAM_RED || client->team == TEAM_BLUE))
		return NULL;
	return client->crystals[saber];
}

static void CG_DoSaberLight(saberInfo_t *saber, const int *crystals)''')
    insert(players, '\t\t\t//FIXME: make RGB sabers\n\t\t\tCG_RGBForSaberColor( saber->blade[i].color, rgbs[i] );',
           '''			if (crystals && crystals[i] >= 0) {
				for (int channel = 0; channel < 3; ++channel)
					rgbs[i][channel] = ST_CrystalChannel(crystals[i], channel) / 255.f;
			} else {
				CG_RGBForSaberColor(saber->blade[i].color, rgbs[i]);
			}''')
    insert(players, '\t\ttrap->R_AddLightToScene( mid, diameter + (Q_flrand(0.0f, 1.0f)*8.0f), rgb[0], rgb[1], rgb[2] );',
           '''		if (rgb[0] || rgb[1] || rgb[2])
			trap->R_AddLightToScene(mid, diameter + Q_flrand(0, 1) * 8, rgb[0], rgb[1], rgb[2]);''')
    anchor = '\tsaberEnt = &cg_entities[cent->currentState.saberEntityNum];\n\tsaberLen = client->saber[saberNum].blade[bladeNum].length;'
    insert(players, anchor, '''	const int *crystals = CG_CrystalColors(cent, client, saberNum);
	const int crystal = crystals ? crystals[bladeNum] : ST_CRYSTAL_DEFAULT;
''' + anchor)
    insert(players, '\t\t\t\t\t//Here we will use the happy process', '''					if (crystal >= 0)
						for (int channel = 0; channel < 3; ++channel)
							rgb1[channel] = ST_CrystalChannel(crystal, channel);

					//Here we will use the happy process''')
    insert(players, 'CG_DoSaberLight( &client->saber[saberNum] );', 'CG_DoSaberLight(&client->saber[saberNum], crystals);')
    data = players.read_bytes()
    assert data.count(b'CG_DoSaberLight( &ci->saber[l] );') == 2
    players.write_bytes(data.replace(b'CG_DoSaberLight( &ci->saber[l] );', b'CG_DoSaberLight(&ci->saber[l], CG_CrystalColors(cent, ci, l));'))
    anchor = '\tCG_DoSaber( org_, axis_[0], saberLen, client->saber[saberNum].blade[bladeNum].lengthMax, client->saber[saberNum].blade[bladeNum].radius,'
    insert(players, anchor, '''	if (crystal >= 0) {
		const saberInfo_t *hilt = &client->saber[saberNum];
		const bladeInfo_t *blade = &hilt->blade[bladeNum];
		if (cg_saberTrail.integer == 2 && cg_shadows.integer != 2 && cgs.glconfig.stencilBits >= 4)
			renderfx |= RF_FORCEPOST;
		if (ST_DrawCrystalBlade(org_, axis_[0], saberLen, blade->lengthMax, blade->radius, crystal, renderfx,
			(hilt->numBlades < 3 && !(hilt->saberFlags2 & SFL2_NO_DLIGHT)) ? qtrue : qfalse,
			cg_crystalWhiteCore.integer ? qtrue : qfalse))
			return;
	}
''' + anchor)

    draw = folder/'cg_draw.c'
    anchor = '\tif (atoi(review)) { CG_DrawInformation(); return; }'
    insert(draw, anchor, '''	char crystalReview[8];
	trap->Cvar_VariableStringBuffer("st_reviewCrystals", crystalReview, sizeof(crystalReview));
	if (atoi(crystalReview) && cg.snap) {
		trap->Cvar_Set("st_reviewCrystals", "0");
		for (int i = 0; i < MAX_CLIENTS; ++i) {
			const clientInfo_t *ci = &cgs.clientinfo[i];
			if (ci->infoValid)
				Com_Printf("ST_CRYSTALS %d %06X %06X %06X %06X\\n", i,
					(unsigned)ci->crystals[0][0], (unsigned)ci->crystals[0][1], (unsigned)ci->crystals[1][0], (unsigned)ci->crystals[1][1]);
		}
	}
''' + anchor)


def patch_ui(source, ui, insert):
    main = ui/'ui_main.c'
    insert(main, '\tUI_RegisterCvars();', '''	UI_RegisterCvars();
	trap->Cvar_Create(ST_WHITE_CORE_CVAR, "0", CVAR_ARCHIVE);
	for (int saber = 0; saber < 2; ++saber)
		trap->Cvar_Create(stCrystalCvars[saber], "", CVAR_ARCHIVE | CVAR_USERINFO);''')
    insert(main, '\ttrap->Cvar_Set ( "saber2", UI_Cvar_VariableString ( "ui_saber2" ) );', '''	const char *secondSaber = UI_Cvar_VariableString("ui_saber2");
	trap->Cvar_Set("saber2", secondSaber[0] ? secondSaber : "none");''')
    workbench = ui/'ui_st_workbench.inc'
    insert(workbench, '/* Saber workbench. Native saber definitions, models and saved equipment. */',
           '/* Saber workbench. Native saber definitions, models and saved equipment. */\n#include "st_crystal.h"')
    saber = ui/'ui_saber.c'
    insert(saber, '#include "ui_shared.h"',
           '#include "ui_shared.h"\n#include "st_crystal.h"\n#include "st_crystal_blade.inc"')
    anchor = '\tUI_DoSaber( bladeOrigin, axis[0], bladeLength, bladeLength, bladeRadius, bladeColor );'
    insert(saber, anchor, '''	const int slot = (item->flags & ITF_ISSABER) && saberModel < 2 ? 0 : 1;
	const menuDef_t *menu = (const menuDef_t *)item->parent;
	const bool workbench = menu && menu->window.name &&
		(!Q_stricmp(menu->window.name, "saberMenu") || !Q_stricmp(menu->window.name, "ingame_saber"));
	char crystal[ST_CRYSTAL_TEXT_SIZE + 1];
	trap->Cvar_VariableStringBuffer(workbench ? stCrystalDrafts[slot] : stCrystalCvars[slot], crystal, sizeof(crystal));
	int colors[MAX_BLADES];
	if (bladeNum < MAX_BLADES && ST_CrystalParse(crystal, colors) && colors[bladeNum] >= 0 &&
		ST_DrawCrystalBlade(bladeOrigin, axis[0], bladeLength, bladeLength, bladeRadius, colors[bladeNum], 0, qfalse,
			trap->Cvar_VariableValue(workbench ? ST_WHITE_CORE_DRAFT : ST_WHITE_CORE_CVAR) != 0 ? qtrue : qfalse))
		return;
''' + anchor)
    from crystal_workbench import patch
    patch(source, workbench, insert)
