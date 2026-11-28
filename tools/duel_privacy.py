"""Stage the private-duel settings and local presentation filters."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = ROOT / "development-source/client-game/codemp/cgame/cg_duel_privacy.inc"
SETTINGS = (
    ("cg_hidePrivateDuels", "Hide private duelists", "Hide players in other private duels when you're outside a duel.", "1"),
    ("cg_hideDuelOutsiders", "Hide outside players", "During a private duel, show only you and your opponent.", "1"),
    ("cg_mutePrivateDuels", "Mute private duels", "Mute player and combat sounds from private duels you're outside of.", "1"),
    ("cg_muteDuelOutsiders", "Mute outside players", "During a private duel, mute sound from players outside your duel.", "1"),
)


def patch(path, edits, marker):
    source = path.read_text(encoding="utf-8")
    if marker in source:
        return
    for old, new in edits:
        if source.count(old) != 1:
            raise ValueError(f"Private duel staging anchor changed in {path}: {old!r}")
        source = source.replace(old, new, 1)
    path.write_text(source, encoding="utf-8")


def stage_menu(tree):
    path = tree / "codemp/ui/st_setup_catalog.h"
    end = "};\nstatic const int SS_COUNT="
    rows = [
        f' {{"{cvar}","{label}","Private duels","{description}","0=Off|1=On","{default}",2,1,0,0,CVAR_ARCHIVE,0,1}},'
        for cvar, label, description, default in SETTINGS
    ]
    patch(path, [(end, "\n".join(rows) + "\n" + end)], SETTINGS[0][0])


def stage_client(tree):
    cg = tree / "codemp/cgame"
    (cg / INCLUDE.name).write_bytes(INCLUDE.read_bytes())
    patch(cg / "cg_main.c", [
        ("cgameImport_t *trap = NULL;", 'cgameImport_t *trap = NULL;\n\n#include "cg_duel_privacy.inc"'),
        ("\tCG_RegisterCvars();", "\tCG_RegisterCvars();\n\tCG_DuelPrivacySettings( qtrue );"),
        ("\tcge.Init", "\ttrap = CG_DuelSoundImports( import );\n\n\tcge.Init"),
    ], '#include "cg_duel_privacy.inc"')
    patch(cg / "cg_view.c", [
        ("\tCG_UpdateCvars();", "\tCG_UpdateCvars();\n\tCG_DuelPrivacySettings( qfalse );"),
    ], "CG_DuelPrivacySettings( qfalse )")
    declarations = """
void CG_DuelPrivacySettings( qboolean initial );
qboolean CG_DuelHideEntity( const entityState_t *state );
void CG_DuelHiddenPlayerHum( const centity_t *cent );
void CG_DuelDispatchEvent( centity_t *cent, vec3_t origin );

"""
    patch(cg / "cg_local.h", [
        ("void CG_EntityEvent", declarations + "void CG_EntityEvent"),
    ], "void CG_DuelDispatchEvent")
    patch(cg / "cg_event.c", [
        ("CG_EntityEvent( cent, cent->lerpOrigin );", "CG_DuelDispatchEvent( cent, cent->lerpOrigin );"),
    ], "CG_DuelDispatchEvent(")
    ents = cg / "cg_ents.c"
    text = ents.read_text(encoding="utf-8")
    if "CG_DuelHiddenPlayerHum(" not in text:
        text = re.sub(
            r"static qboolean ST_HidePlayerForPrivateDuel\(.*?(?=static void CG_AddCEntity)",
            "", text, count=1, flags=re.S
        )
        text = text.replace("\tif ( ST_HidePlayerForPrivateDuel( cent ) ) {\n\t\treturn;\n\t}\n\n", "")
        anchor = "\tCG_EntityEffects( cent );"
        if text.count(anchor) != 1:
            raise ValueError(f"Private duel entity anchor changed in {ents}")
        text = text.replace(anchor, anchor + """
	if ( CG_DuelHideEntity( &cent->currentState ) ) {
		CG_DuelHiddenPlayerHum( cent );
		return;
	}""", 1)
        ents.write_text(text, encoding="utf-8")
    draw = cg / "cg_draw.c"
    marker = "static void CG_ScanForCrosshairEntity( void )"
    source = draw.read_text(encoding="utf-8")
    if "CG_DuelHideEntity(" not in source:
        prefix, scan = source.split(marker, 1)
        anchor = "\tif (trace.entityNum < MAX_CLIENTS)"
        position = scan.index(anchor)
        scan = scan[:position] + """
	if ( trace.entityNum >= 0 && trace.entityNum < MAX_CLIENTS &&
		CG_DuelHideEntity( &cg_entities[trace.entityNum].currentState ) ) {
		cg.crosshairClientNum = ENTITYNUM_NONE;
		cg.crosshairClientTime = 0;
		CG_DrawCrosshair( trace.endpos, 0 );
		return;
	}

""" + scan[position:]
        draw.write_text(prefix + marker + scan, encoding="utf-8")


def stage_server(tree):
    game = tree / "codemp/game"
    patch(game / "g_utils.c", [
        ("\tte->s.saberEntityNum = channel;\n\n\tif (ent && ent->client", """	te->s.saberEntityNum = channel;
	if ( ent->client && ent->s.number < MAX_CLIENTS ) {
		/* Tag positional player sounds without changing their position or delivery. */
		te->s.otherEntityNum = ENTITYNUM_NONE;
		te->s.clientNum = ent->s.number + 1;
	}

	if (ent && ent->client"""),
    ], "/* Tag positional player sounds")
    patch(game / "w_saber.c", [
        ("te = G_TempEntity( tr.endpos, EV_SABER_BLOCK );", "te = G_TempEntity( tr.endpos, EV_SABER_BLOCK );\n\t\t\t\t\tte->s.otherEntityNum2 = saberOwner->s.number;"),
        ("te = G_TempEntity( g_entities[saberNum].r.currentOrigin, EV_SABER_BLOCK );",
         "te = G_TempEntity( g_entities[saberNum].r.currentOrigin, EV_SABER_BLOCK );\n\t\t\t\tte->s.otherEntityNum2 = self->s.number;"),
    ], "te->s.otherEntityNum2 = saberOwner->s.number;\n\t\t\t\t\tVectorCopy")
