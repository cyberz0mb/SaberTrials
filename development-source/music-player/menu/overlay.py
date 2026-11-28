"""Add the Windows music panel onto the current frontend without overriding other menu files."""
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
PAUSE_ROW = '{"Pause menu","togglemenu","Camera / UI","Open or close the in-game menu",0}'
MUSIC_ROW = '{"Music player","st_music","Camera / UI","Open or close your music player",0}'


def _stage(path, edits):
    old = path.read_bytes()
    newline = "\r\n" if b"\r\n" in old else "\n"
    text = old.decode("utf-8").replace("\r\n", "\n")
    for anchor, replacement in edits:
        if replacement in text:
            continue
        if text.count(anchor) != 1:
            raise ValueError(f"{path.name}: missing or ambiguous music panel anchor {anchor!r}")
        text = text.replace(anchor, replacement, 1)
    result = text.replace("\n", newline).encode("utf-8")
    if result != old:
        path.write_bytes(result)


def stage_catalog(tree):
    actions = [
        '{"Next music track","playnext","Camera / UI","Skip to the next track",0}',
        '{"Previous music track","playprev","Camera / UI","Go to the previous track",0}',
        '{"Pause music","pausemusic","Camera / UI","Pause the selected music source",0}',
        '{"Search music","search","Camera / UI","Search by artist, song or album",0}',
        '{"Music volume down","musicvolume -5","Camera / UI","Lower music volume by 5%",0}',
        '{"Music volume up","musicvolume +5","Camera / UI","Raise music volume by 5%",0}',
    ]
    rows = [PAUSE_ROW, MUSIC_ROW, *actions]
    _stage(Path(tree) / "codemp/ui/st_controls_catalog.h",
           [(a, a + ",\n " + b) for a, b in zip(rows, rows[1:])])


def _write(path, data):
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)


def stage_resources(tree):
    """Embed the two namespaced player assets for disconnected, pure and personal UI use."""
    win = Path(tree) / "codemp/win32"
    client = Path(tree) / "codemp/client"
    entries = (("st_music/ui/player.menu", 8800), ("st_music/ui/record.png", 8801))
    table = client / "full_ui_resources.inc"
    existing = table.read_text().splitlines()
    names = {name for name, _ in entries}
    ids = {str(value) for _, value in entries}
    rows = []
    for line in existing:
        if not line.strip():
            continue
        match = re.fullmatch(r'\s*\{"([^"]+)",\s*(\d+)\},\s*', line)
        if not match:
            raise ValueError(f"Unexpected presentation resource entry {line!r}")
        if match[1] in names:
            continue
        if match[2] in ids:
            raise ValueError(f"Music resource ID collides with {match[1]}")
        rows.append(line)
    resource_file = win / "st_music_resources.rc"
    for rc in win.glob("*.rc"):
        if rc != resource_file and any(number in ids for number in re.findall(
                r"^\s*(\d+)\s+RCDATA\b", rc.read_text(errors="replace"), flags=re.MULTILINE|re.IGNORECASE)):
            raise ValueError(f"Music resource ID already used in {rc.name}")
    folder = win / "st-music"
    folder.mkdir(exist_ok=True)
    resources = []
    for name, value in entries:
        resource = folder / Path(name).name
        _write(resource, (HERE / "assets" / name).read_bytes())
        rows.append(f'{{"{name}",{value}}},')
        resources.append(f'{value} RCDATA "st-music/{resource.name}"')
    _write(table, ("\n".join(sorted(rows,key=str.upper)) + "\n").encode())
    _write(resource_file, ("\n".join(resources) + "\n").encode())
    rc = win / "openjk.rc"
    include = b'#include "st_music_resources.rc"'
    body = rc.read_bytes()
    if include not in body:
        newline = b"\r\n" if b"\r\n" in body else b"\n"
        rc.write_bytes(body.rstrip(b"\r\n") + newline + include + newline)
    _stage(client / "full_ui.inc", [
        ('if(Q_stricmp(path,"shaders/st_community_huds.shader")',
         'if(Q_stricmp(path,"st_music/ui/player.menu") && Q_stricmp(path,"st_music/ui/record.png") &&\n'
         '       Q_stricmp(path,"shaders/st_community_huds.shader")'),
    ])


def stage_ui(tree):
    ui = Path(tree) / "codemp/ui"
    _stage(ui / "ui_st_rich.inc", [
        ("const char* kind,bool selected,bool focus){", "const char* kind,bool selected,bool focus,bool mirror=false){"),
        ("else RUI_Image(art,x-1,y-1,w+2,h+2);",
         "else RUI_Image(art,x-1,y-1,mirror ? -(w+2) : w+2,h+2);"),
        ("  RUI_Light(p,stmain::phase(uiInfo.uiDC.realTime,true,2800),ruCyan,3.5f);",
         "  if (mirror) for (auto& point : p) point.x = 2*x+w-point.x;\n"
         "  RUI_Light(p,stmain::phase(uiInfo.uiDC.realTime,true,2800),ruCyan,3.5f);"),
    ])
    _stage(ui / "ui_st_legacy.inc", [
        ('{"server_menu","info"}', '{"server_menu","info"},{"st_music","play"}'),
        ("static bool LUI_Button(const itemDef_t* i){",
         "static bool LUI_RightRail(const itemDef_t* i){\n"
         " return LUI_Name(((const menuDef_t*)i->parent)->window.name,\"ingame\") && LUI_Name(i->window.name,\"st_music\");\n"
         "}\nstatic bool LUI_Button(const itemDef_t* i){"),
        ('"action",LUI_Primary(n),focus);', '"action",LUI_Primary(n),focus,LUI_RightRail(i));'),
        ("SMUI_Icon(path,r.x+18,", "SMUI_Icon(path,LUI_RightRail(i) ? r.x+r.w-18 : r.x+18,"),
        ("if (railIcon) { box.x += 33.f; box.w -= 33.f; }",
         "if (railIcon) {\n"
         "   box.w -= 33.f;\n"
         "   if (LUI_RightRail(i)) align = ITEM_ALIGN_RIGHT;\n"
         "   else box.x += 33.f;\n"
         "  }"),
    ])
    for name in ("ui_st_music.inc", "ui_st_music_edit.inc"):
        target = ui / name
        data = (HERE / name).read_bytes()
        if not target.exists() or target.read_bytes() != data:
            target.write_bytes(data)
    _stage(ui / "ui_main.c", [
        ("static void ST_AddPauseBrowserButton();",
         "static void ST_AddPauseBrowserButton();\nstatic void ST_MusicLoad();"),
        ("    ST_AddPauseBrowserButton();\n}",
         "    ST_AddPauseBrowserButton();\n    ST_MusicLoad();\n}"),
        ("if (!handle) handle = trap->PC_LoadSource(ThemeAsset(menuFile));",
         'if (!handle) handle = trap->PC_LoadSource(!Q_stricmp(menuFile,"st_music/ui/player.menu") ? menuFile : ThemeAsset(menuFile));'),
        ('#include "ui_st_legacy.inc"', '#include "ui_st_legacy.inc"\n#include "ui_st_music.inc"'),
        ("if ( ST_UIMenuScript( name ) ) { return; }",
         'if (!Q_stricmp(name,"stMusicClose")) { ST_MusicClose(); return; }\n'
         '        if (!Q_stricmp(name,"stMusicEnd")) { ST_MusicQueryEditing(true); return; }\n'
         '        if ( ST_UIMenuScript( name ) ) { return; }'),
        ("void UI_KeyEvent( int key, qboolean down ) {",
         "void UI_KeyEvent( int key, qboolean down ) {\n    if (ST_MusicKey(key,down)) return;"),
        ("if (ST_ClassicLayout()) { ST_UIStanceCapability();",
         "if (MusicIsMenu(focused)) ST_MusicPaint(Menu_GetFocused());\n"
         "        else if (ST_ClassicLayout()) { ST_UIStanceCapability();"),
        ("void UI_Shutdown( void ) {", 'void UI_Shutdown( void ) {\n    trap->Cvar_Set("st_musicVisible","0");'),
        ("        ST_ReleasePauseBrowser();\n\t\tMenu_Reset();",
         '        trap->Cvar_Set("st_musicVisible","0");\n        ST_ReleasePauseBrowser();\n\t\tMenu_Reset();'),
    ])
    _stage(ui / "ui_atoms.c", [
        ("static void UI_OpenMenu_f( void ) {",
         "extern void ST_MusicRememberOrigin();\nextern void ST_MusicClose();\n"
         'static void UI_OpenMenu_f( void ) {\n    if (!Q_stricmp(UI_Argv(1),"st_music_player")) {\n'
         '        if (!Menus_FindByName("st_music_player")) return;\n        ST_MusicRememberOrigin();\n    }'),
        ('{ "ui_load",\t\t\tUI_Load },', '{ "ui_load",\t\t\tUI_Load },\n\t{ "ui_musicclose", ST_MusicClose },'),
        ('typedef struct consoleCommand_s {', 'extern void ST_MusicFocusQuery();\n\ntypedef struct consoleCommand_s {'),
        ('{ "ui_musicclose", ST_MusicClose },', '{ "ui_musicclose", ST_MusicClose },\n\t{ "ui_musicsearch", ST_MusicFocusQuery },'),
    ])
    _stage(ui / "ui_shared.c", [
        ("void Menu_HandleKey(menuDef_t *menu, int key, qboolean down) {",
         '#ifdef UI_BUILD\n#include "ui_st_music_edit.inc"\n#endif\n\nvoid Menu_HandleKey(menuDef_t *menu, int key, qboolean down) {'),
        ('(!Q_stricmp(g_editItem->cvar, "ui_stServerSearch") ||',
         '(!Q_stricmp(g_editItem->cvar, "st_musicQuery") || !Q_stricmp(g_editItem->cvar, "ui_stServerSearch") ||'),
        ("\t\t\t\tbuff[item->cursorPos+1] = 0;",
         '\t\t\t\t// A music query retains the suffix when editing within the field.\n'
         '\t\t\t\tif (item->cursorPos >= len || Q_stricmp(item->cvar, "st_musicQuery"))\n'
         '\t\t\t\t\tbuff[item->cursorPos+1] = 0;'),
    ])
