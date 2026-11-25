"""Apply the shared FPS and lagometer layout to the three Windows client games."""


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError("Unexpected client HUD source at " + old.splitlines()[0])
    return source.replace(old, new)


def stage(tree):
    folder = tree / "codemp/cgame"
    draw = folder / "cg_draw.c"
    source = draw.read_text()
    if "CG_Text_Width(s, fpsScale, FONT_MEDIUM)" in source:
        return
    native = "ST_DrawCombatHud();" in source
    start = source.index("static float CG_DrawFPS(")
    end = source.index("\n}", start)
    fps = source[start:end]
    fps = replace_once(fps, "const int\t\txOffset = 0;", "const float fpsScale = 0.64f;")
    fps = replace_once(fps, '''s = va( "%ifps", fps );
	w = CG_DrawStrlen( s ) * BIGCHAR_WIDTH;

	CG_DrawBigString( 635 - w + xOffset, y + 2, s, 1.0F);

	return y + BIGCHAR_HEIGHT + 4;''', '''s = va("%d FPS", fps);
	w = CG_Text_Width(s, fpsScale, FONT_MEDIUM);
	CG_Text_Paint(SCREEN_WIDTH - 5 - w, y + 2, fpsScale, colorWhite, s, 0, 0, ITEM_TEXTSTYLE_SHADOWED, FONT_MEDIUM);
	return y + CG_Text_Height(s, fpsScale, FONT_MEDIUM) + 4;''')
    source = source[:start] + fps + source[end:]

    start = source.index("static void CG_DrawLagometer(")
    end = source.index("\n}", start)
    graph = source[start:end]
    graph = replace_once(graph, "int\t\ta, x, y, i;", "int\t\ta, i;")
    style = "st_hudStyle" if native else "stCommunityHudStyle"
    scale = "ST_HudScale()" if native else "Com_Clamp(.75f, 1.25f, atof(scaleText) * .01f)"
    query = "" if native else '''
        char scaleText[16];
        trap->Cvar_VariableStringBuffer("st_hudScale", scaleText, sizeof(scaleText));'''
    graph = replace_once(graph, '''x = 640 - 48;
	y = 480 - 144;

	trap->R_SetColor( NULL );
	CG_DrawPic( x, y, 48, 48, cgs.media.lagometerShader );

	ax = x;
	ay = y;
	aw = 48;
	ah = 48;''', f'''const vec4_t graphBg = {{.025f, .05f, .065f, .77f}};
    const float pixelWidth = cgs.screenXScale > 0 ? cgs.screenYScale / cgs.screenXScale : 1;
    float bottom = 358;  // Above the classic circular health meter.
    if ({style}.integer == 1) {{{query}
        bottom = 467 - 53 * {scale} - 6;
    }}
    aw = 48;  // One column per sample on every aspect ratio.
    ah = 24;
    ax = 5 * pixelWidth;
    ay = bottom - ah;
    CG_FillRect(ax, ay, aw * pixelWidth, ah, graphBg);''')
    # Stock and the native HUD differ by one column in the original graph.
    for old in ("ax + aw - 1 - a,", "ax + aw - a,"):
        graph = graph.replace(old, "ax + (aw - 1 - a) * pixelWidth,")
    if graph.count("(aw - 1 - a) * pixelWidth") != 4:
        raise ValueError("Unexpected lagometer sample drawing")
    graph = graph.replace(", 1, v, 0, 0, 0, 0,", ", pixelWidth, v, 0, 0, 0, 0,")
    graph = graph.replace(", 1, range, 0, 0, 0, 0,", ", pixelWidth, range, 0, 0, 0, 0,")
    graph = replace_once(graph, 'CG_DrawBigString( ax, ay, "snc", 1.0 );',
                         'CG_Text_Paint(ax, ay, .52f, colorWhite, "snc", 0, 0, ITEM_TEXTSTYLE_SHADOWED, FONT_MEDIUM);')
    source = source[:start] + graph + source[end:]

    if native:
        original = "if (st_hudStyle.integer == 1) y = ST_DrawHudScore(y);"
        source = replace_once(source, original, '''if (st_hudStyle.integer == 1) {
        if (cg.snap->ps.persistant[PERS_TEAM] == TEAM_SPECTATOR) {
            y = ST_DrawHudScore(y);
        } else {
            float teamHeight = 0;
            if (cgs.tffaCount > 2) teamHeight = 16 + 12 * ((cgs.tffaCount + 1) / 2);
            else if (cgs.gametype >= GT_TEAM && cgs.gametype != GT_SIEGE) teamHeight = 33;
            ST_DrawHudScore(467 - (55 + 33 + teamHeight) * ST_HudScale() - 8);
        }
    }''')
        hud = folder / "cg_sabertrials_hud.inc"
        layout = hud.read_text()
        old = "right = 640 / ST_HudAspect() - 4;"
        if old in layout:
            hud.write_text(replace_once(layout, old, "right = 640 / ST_HudAspect() - 5;"))
    draw.write_text(source)
