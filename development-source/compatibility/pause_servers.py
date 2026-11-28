"""Add the in-match server browser to the Windows release and personal frontend."""
from pathlib import Path
from shutil import copyfile


def stage(tree):
    ui = tree / "codemp/ui"
    copyfile(Path(__file__).with_name("pause_servers.inc"), ui / "st_pause_servers.inc")
    rail = ui / "ui_st_legacy.inc"
    layout = rail.read_text()
    if '{"find_server","stream"}' not in layout:
        marker = '{"join","join"}'
        if layout.count(marker) != 1:
            raise ValueError("Expected the pause rail icon table")
        rail.write_text(layout.replace(marker, marker + ',{"find_server","stream"}'))
    main = ui / "ui_main.c"
    source = main.read_text()
    if '#include "st_pause_servers.inc"' in source:
        return
    edits = {
        "static void UI_LoadPage(const char *requested);": "static void ST_ReleasePauseBrowser();\nstatic void ST_AddPauseBrowserButton();\nstatic void UI_LoadPage(const char *requested);",
        '#include "ui_sabertrials_menu.inc"': '#include "st_pause_servers.inc"\n#include "ui_sabertrials_menu.inc"',
        "ST_AddClassicInterface();\n}": "ST_AddClassicInterface();\n    ST_AddPauseBrowserButton();\n}",
        "if (reset) {\n\t\tMenu_Reset();": "if (reset) {\n        ST_ReleasePauseBrowser();\n\t\tMenu_Reset();",
        "void UI_SetActiveMenu( uiMenuCommand_t menu ) {": "void UI_SetActiveMenu( uiMenuCommand_t menu ) {\n    ST_ReleasePauseBrowser();",
        'else if (Q_stricmp(name, "closeJoin") == 0)': '''else if (!Q_stricmp(name, "stBrowseFromPause")) {
        ST_OpenPauseBrowser();
    } else if (!Q_stricmp(name, "stBackToPause")) {
        ST_BackToPause();
    } else if (Q_stricmp(name, "closeJoin") == 0)''',
    }
    for old, new in edits.items():
        if source.count(old) != 1:
            raise ValueError(f"Unexpected UI source around {old}")
        source = source.replace(old, new)
    main.write_text(source)
