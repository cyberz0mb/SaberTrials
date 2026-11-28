"""Use the same enhanced type on all native and bundled-compatibility HUDs."""
from pathlib import Path
import re

CHARSET = "fonts/st_game_chars"
DIGITS = "fonts/st_game_digits"


def edit(path, function):
    original = path.read_text()
    changed = function(original)
    if changed != original:
        path.write_text(changed)


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"Gameplay typography anchor changed: {old}")
    return source.replace(old, new, 1)


def stage_engine(tree):
    client = tree / "codemp/client"
    def screens(source):
        if "SCR_RegisterGameplayText" in source:
            return source
        anchor = "static void SCR_DrawChar("
        declarations = f'''static cvar_t *stGameplayFontSharpness;
static qhandle_t stGameplayCharset;

void SCR_RegisterGameplayText(void) {{
    stGameplayFontSharpness = Cvar_Get("r_fontSharpness", "1", CVAR_ARCHIVE_ND);
    stGameplayCharset = re->RegisterShaderNoMip("{CHARSET}");
}}

static qhandle_t SCR_GameplayCharset(int ch) {{
    if (ch >= 33 && stGameplayCharset && stGameplayFontSharpness &&
        stGameplayFontSharpness->value > 0.f)
        return stGameplayCharset;
    return cls.charSetShader;
}}

'''
        source = replace_once(source, anchor, declarations + anchor)
        if source.count("cls.charSetShader );") != 2:
            raise ValueError("Unexpected screen character draws")
        return source.replace("cls.charSetShader );", "SCR_GameplayCharset(ch) );")

    edit(client / "cl_scrn.cpp", screens)
    anchor = "void CL_InitRenderer( void ) {"
    register = 'cls.charSetShader = re->RegisterShaderNoMip("gfx/2d/charsgrid_med");'
    def renderer(source):
        if "SCR_RegisterGameplayText();" in source:
            return source
        source = replace_once(source, anchor, "void SCR_RegisterGameplayText(void);\n\n" + anchor)
        return replace_once(source, register, register + "\n\tSCR_RegisterGameplayText();")
    edit(client / "cl_main.cpp", renderer)


def stage_cgame(tree):
    cg = tree / "codemp/cgame"
    def tools(source):
        if "CG_InitGameplayText" in source:
            return source
        anchor = "void CG_DrawChar("
        declarations = f'''static vmCvar_t stGameplayFontSharpness;
static qhandle_t stGameplayCharset;
static qhandle_t stGameplayDigits;

void CG_InitGameplayText(void) {{
    trap->Cvar_Register(&stGameplayFontSharpness, "r_fontSharpness", "1", CVAR_ARCHIVE_ND);
    stGameplayCharset = trap->R_RegisterShaderNoMip("{CHARSET}");
    stGameplayDigits = trap->R_RegisterShaderNoMip("{DIGITS}");
}}

void CG_UpdateGameplayText(void) {{
    trap->Cvar_Update(&stGameplayFontSharpness);
}}

static void CG_DrawGameplayDigit(int x, int y, int width, int height, int frame, qhandle_t fallback) {{
    if (!stGameplayDigits || stGameplayFontSharpness.value <= 0.f) {{
        CG_DrawPic(x, y, width, height, fallback);
        return;
    }}
    const float u = frame / 16.f;
    trap->R_DrawStretchPic(x, y, width, height, u, 0.f, u + 1.f / 16.f, 1.f, stGameplayDigits);
}}

'''
        source = replace_once(source, anchor, declarations + anchor)
        source = replace_once(source, "size2, cgs.media.charsetShader );", """size2,
        ch >= 33 && stGameplayCharset && stGameplayFontSharpness.value > 0.f
            ? stGameplayCharset : cgs.media.charsetShader );""")
        start = source.index("void CG_DrawNumField")
        end = source.index("void CG_DrawProportionalString", start)
        numbers, count = re.subn(
            r"CG_DrawPic\(\s*x,y, charWidth, charHeight, (cgs\.media\.\w+\[(frame|0)\]) \);",
            r"CG_DrawGameplayDigit(x, y, charWidth, charHeight, \2, \1);",
            source[start:end],
        )
        if count != 6:
            raise ValueError("Unexpected HUD number shader draws")
        return source[:start] + numbers + source[end:]

    edit(cg / "cg_drawtools.c", tools)

    def init(source):
        if "CG_InitGameplayText();" in source:
            return source
        anchor = 'cgs.media.charsetShader\t\t= trap->R_RegisterShaderNoMip( "gfx/2d/charsgrid_med" );'
        return replace_once(source, anchor, anchor + "\n\textern void CG_InitGameplayText(void);\n\tCG_InitGameplayText();")
    edit(cg / "cg_main.c", init)

    def frame(source):
        if "CG_UpdateGameplayText();" in source:
            return source
        anchor = "\tCG_UpdateCvars();"
        return replace_once(source, anchor,
                            "\textern void CG_UpdateGameplayText(void);\n" + anchor + "\n\tCG_UpdateGameplayText();")
    edit(cg / "cg_view.c", frame)

    def enhanced_fonts(source):
        if "CG_ResolveGameplayFont" in source:
            return source
        anchor = "int CG_Text_Width("
        helper = """static int CG_ResolveGameplayFont(int menuFont, float *scale) {
    const int baseFont = MenuFontToHandle(menuFont);
    if (!CG_GameplayTypographyEnabled() || trap->R_Language_IsAsian()) {
        return baseFont;
    }
    for (size_t i = 0; i < ARRAY_LEN(stGameplayFonts); ++i) {
        if (baseFont && baseFont == stGameplayFonts[i].standard && stGameplayFonts[i].sharp) {
            *scale /= 6.f; // The atlas preserves all metrics at six times the resolution.
            return stGameplayFonts[i].sharp;
        }
    }
    return baseFont;
}

"""
        table = """static struct {
    const char *name;
    qhandle_t standard;
    qhandle_t sharp;
} stGameplayFonts[] = {
    { "ocr_a", 0, 0 },
    { "ergoec", 0, 0 },
    { "arialnb", 0, 0 },
};

extern qboolean CG_GameplayTypographyEnabled(void);

void CG_RegisterGameplayFonts(void) {
    for (size_t i = 0; i < ARRAY_LEN(stGameplayFonts); ++i) {
        stGameplayFonts[i].standard = trap->R_RegisterFont(stGameplayFonts[i].name);
        stGameplayFonts[i].sharp = trap->R_RegisterFont(va("%s_sharp2", stGameplayFonts[i].name));
    }
}

"""
        source = replace_once(source, anchor, table + helper + anchor)
        old = "int iFontIndex = MenuFontToHandle(iMenuFont);"
        if source.count(old) != 3:
            raise ValueError("Unexpected gameplay font measurements")
        return source.replace(old, "int iFontIndex = CG_ResolveGameplayFont(iMenuFont, &scale);")

    edit(cg / "cg_draw.c", enhanced_fonts)

    def activate_fonts(source):
        if "CG_RegisterGameplayFonts();" in source:
            return source
        return replace_once(source, "CG_InitGameplayText();", "CG_InitGameplayText();"
                            "\n\textern void CG_RegisterGameplayFonts(void);\n\tCG_RegisterGameplayFonts();")

    edit(cg / "cg_main.c", activate_fonts)

    def enable_fonts(source):
        if "CG_GameplayTypographyEnabled(void)" in source:
            return source
        return replace_once(source, "void CG_UpdateGameplayText(void)",
                            "qboolean CG_GameplayTypographyEnabled(void) {\n"
                            "    return stGameplayFontSharpness.value > 0.f;\n}\n\n"
                            "void CG_UpdateGameplayText(void)")

    edit(cg / "cg_drawtools.c", enable_fonts)

    def scoreboard(source):
        if "CG_ScoreboardForeground(void)" in source:
            return source
        anchor = "qboolean CG_DrawOldScoreboard( void ) {"
        predicate = '''qboolean CG_ScoreboardForeground(void) {
    if (cl_paused.integer || (cg.warmup && !cg.showScores)) {
        return qfalse;
    }
    return cg.showScores || cg.predictedPlayerState.pm_type == PM_DEAD ||
        cg.predictedPlayerState.pm_type == PM_INTERMISSION ||
        CG_FadeColor(cg.scoreFadeTime, FADE_TIME) != NULL;
}

'''
        return replace_once(source, anchor, predicate + anchor)
    edit(cg / "cg_scoreboard.c", scoreboard)

    def overlays(source):
        if "CG_ScoreboardForeground()" in source:
            return source
        anchor = "static void CG_DrawSpectator(void)"
        source = replace_once(source, anchor, "extern qboolean CG_ScoreboardForeground(void);\n" + anchor)
        spectator = "\t\tCG_DrawSpectator();"
        if spectator not in source:
            spectator = "\t\tif (!cg.showScores || !ST_UsePersonalScoreboard()) CG_DrawSpectator();"
        follow = "\tif ( !CG_DrawFollow() ) {"
        if follow not in source:
            follow = "\tif ((!cg.showScores || !ST_UsePersonalScoreboard()) && !CG_DrawFollow()) {"
        source = replace_once(source, spectator, "\t\tif (!CG_ScoreboardForeground()) CG_DrawSpectator();")
        return replace_once(source, follow, "\tif (!CG_ScoreboardForeground() && !CG_DrawFollow()) {")
    edit(cg / "cg_draw.c", overlays)
