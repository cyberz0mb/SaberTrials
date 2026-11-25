"""Stage the native scoreboard artwork, layout and painter for bundled classic cgames."""
from pathlib import Path
from shutil import copyfile
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]


def stage_engine(tree):
    win = tree / "codemp/win32"
    folder = win / "hud-fonts"
    folder.mkdir(exist_ok=True)
    font_names = sorted(f"{family}_sharp{level}.{ext}" for family in ("arialnb", "ergoec")
                        for level in (1, 2) for ext in ("fontdat", "png"))
    resources, table = [], []
    for index, name in enumerate(font_names, 6200):
        copyfile(ROOT / "assets/hud-fonts" / name, folder / name)
        resources.append(f'{index} RCDATA "hud-fonts/{name}"')
        table.append(f'{{"fonts/{name}",{index}}},')
    (tree / "codemp/client/hud_font_resources.inc").write_text("\n".join(table))
    rc = win / "openjk.rc"
    if resources[0] not in rc.read_text():
        with rc.open("a") as f:
            f.write("\n" + "\n".join(resources) + "\n")

    files = tree / "codemp/qcommon/files.cpp"
    source = files.read_text()
    anchor = '\tCom_DPrintf ("Can\'t find %s\\n", filename);'
    if source.count(anchor) != 1:
        raise ValueError("Expected the normal filesystem search to complete before HUD fallback")
    files.write_text(source.replace(anchor, """#ifndef DEDICATED
    // Only built-in glyphs and scoreboard art can be returned here. Preserve
    // the normal mod, user and pure-pack lookup order above.
    extern const byte *CL_HudPresentationFile(const char *, int *);
    int hudLength = 0;
    if (const byte *data = CL_HudPresentationFile(filename, &hudLength)) {
        auto &handle = fsh[*file];
        handle.presentation = data;
        handle.cursor = 0;
        handle.fileSize = hudLength;
        Q_strncpyz(handle.name, filename, sizeof(handle.name));
        return hudLength;
    }
#endif
""" + anchor))


def stage_module(tree, archive):
    cg = tree / "codemp/cgame"
    ui = tree / "codemp/ui"
    for name in ("st_presentation_draw.inc", "st_presentation_policy.inc"):
        copyfile(ROOT / "development-source/bot-roles/codemp/ui" / name, ui / name)
    native = (ROOT / "development-source/client-game/codemp/cgame/cg_sabertrials_presentation.inc").read_text()
    painter = native[native.index("static void STP_CGFill"):native.index("void ST_ScorePage_f")]
    (cg / "st_classic_scoreboard.inc").write_text(
        '#include "ui/st_presentation_draw.inc"\nstatic float stpFade = 1;\nstatic int stpOpened, stpVisible;\n'
        + painter + (ROOT / "development-source/compatibility/classic_scoreboard.inc").read_text())

    with ZipFile(archive) as z:
        name, = (n for n in z.namelist() if n.endswith("/codemp/cgame/cg_scoreboard.c"))
        source = z.read(name).decode().replace("\r\n", "\n")
        draw_source = z.read(name.replace("cg_scoreboard.c", "cg_draw.c")).decode().replace("\r\n", "\n")
    for old, new in [
        ("static void CG_DrawSpectator(void)", "extern qboolean ST_UsePersonalScoreboard(void);\nstatic void CG_DrawSpectator(void)"),
        ("\t\tCG_DrawSpectator();", "\t\tif (!cg.showScores || !ST_UsePersonalScoreboard()) CG_DrawSpectator();"),
        ("if ( !CG_DrawFollow() )", "if ((!cg.showScores || !ST_UsePersonalScoreboard()) && !CG_DrawFollow())"),
    ]:
        if draw_source.count(old) != 1:
            raise ValueError("Unexpected classic spectator HUD entry point")
        draw_source = draw_source.replace(old, new)
    (cg / "cg_draw.c").write_text(draw_source)
    entry = "qboolean CG_DrawOldScoreboard( void ) {"
    draw = "\t// fragged by ... line"
    if source.count(entry) != 1 or source.count(draw) != 1:
        raise ValueError("Classic scoreboard entry points changed")
    before, body = source.split(entry)
    body = body.replace("return qfalse;", "stpVisible = 0;\n\t\treturn qfalse;")
    body = body.replace(draw, """    if (ST_DrawClassicConnectionBoard(fadeColor[3])) {
        if (++cg.deferredPlayerLoading > 10) CG_LoadDeferredPlayers();
        return qtrue;
    }

""" + draw)
    (cg / "cg_scoreboard.c").write_text(before + '#include "st_classic_scoreboard.inc"\n' + entry + body)


def prefer_bundled_base(source):
    marker = 'if (!strcmp(name,"cgame") && CL_JAConnection())'
    if source.count(marker) != 1:
        raise ValueError("Expected the compatibility loader after PK3 selection")
    return source.replace(marker, """if (!strcmp(name,"cgame") && (!*gamedir || !Q_stricmp(gamedir,BASEGAME)) &&
                    !CL_JAConnection()) {
                    const char *binaryRoot[] = {Sys_BinaryPath()};
                    libHandle = Sys_LoadDllFromPaths(filename,"stock",binaryRoot,1,SEARCH_PATH_MOD,__FUNCTION__);
                }
                """ + marker)
