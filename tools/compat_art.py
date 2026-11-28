"""Embed the shipped personal menu art in the Windows client at build time."""
from pathlib import Path
from zipfile import ZipFile


def stage_art(root, engine):
    resources = engine / "codemp/win32"
    folder = resources / "personal-art"
    folder.mkdir(exist_ok=True)
    assets = {}
    for name in ("pause_rail", "pause_line", "pause_focus", "pause_edge", "cursor",
                 "info", "join", "player", "controls", "settings", "play", "exit", "vote"):
        assets[name + ".tga"] = (root / "ui/assets/sabertrials" / (name + ".tga")).read_bytes()
    for pack, prefix, names in (
        ("emote_wheel", "ui/assets/sabertrials/rich", ["emote_" + s for s in
         ["face", "gesture", "empty", "taunt", "bow", "meditate", "flourish", "celebrate", "number",
          *["focus" + str(i) for i in range(8)]]]),
        ("main", "ui/assets/sabertrials/main", ["emblem"]),
        ("rich", "ui/assets/sabertrials/rich", ["wordmark", "action_focus", "action_idle"]),
        ("hud_theme", "gfx/sabertrials/hud_theme", ["chat_frame", "chat_frame_fill", "chat_header",
         *[p+s for p in ("health","armor","weapon","score","team") for s in ("_frame","_frame_fill")],
         "health_mark","armor_mark","saber_mark","dual_mark","staff_mark","ammo_mark","letters",
         "meter_track","meter_health","meter_armor","reticle"]),
    ):
        package, = root.glob("z*_sabertrials_" + pack + ".pk3")
        with ZipFile(package) as archive:
            for name in names:
                assets[name + ".png"] = archive.read(prefix + "/" + name + ".png")
    assets["movement_keycaps.png"] = (root / "assets/runtime-packages/training-hud/movement_keycaps.png").read_bytes()
    ids, rc = [], []
    for i, (filename, data) in enumerate(assets.items(), 4200):
        (folder / filename).write_bytes(data)
        ids.append(f'{{"{Path(filename).stem}", {i}}},')
        rc.append(f'{i} RCDATA "personal-art/{filename}"')
    (engine / "codemp/client/foreign_art_ids.inc").write_text("\n".join(ids))
    # The same compiled language catalogs and lookup rules used by the main menu.
    locale = (root / "dist/pug-01/frontend/codemp/ui/ui_st_menu_language.inc").read_text()
    locale = locale[:locale.index("static std::string STML_FormatNumbers")]
    locale = locale.replace("trap->Cvar_VariableValue", "Cvar_VariableIntegerValue")
    locale = locale.replace("trap->MenuCatalog ? trap->MenuCatalog(language, &size) : nullptr", "STML_MenuCatalog(language, &size)")
    (engine / "codemp/client/foreign_menu_language.inc").write_text(locale)
    with (resources / "openjk.rc").open("a") as out:
        out.write("\n" + "\n".join(rc) + "\n")
