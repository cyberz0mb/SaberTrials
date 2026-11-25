"""Render the first JA+ player profile with the crash map and display dimensions."""
import re
import shutil
import struct
import tempfile
from pathlib import Path

from playback import ROOT, run, wheel_start


def main():
    home = Path(tempfile.mkdtemp(prefix="vulkan-profile-", dir=ROOT / "dist/compat/qa"))
    print(home, flush=True)
    game = home / "japlus"
    game.mkdir()
    shutil.copyfile(ROOT / "jampgamex86_64.dll", game / "jampgamex86_64.dll")
    start = wheel_start()
    start[start.index("map mp/duel1")] = "map mp/ffa3"
    first_profile = start.index("st_emoteuiqa resume")
    # Incoming chat rasterizes a new texture before the menu draws its two 3D previews.
    start[first_profile:first_profile] = [
        "wait 40", "say Profile loading", "wait 30", "say Welcome to the arena",
        "wait 30", "st_personalStatus", "screenshot_png first-profile", "wait 60"
    ]
    log = run(ROOT / "client/SaberTrials.x86_64.exe", home, "japlus", [
        "set r_mode -1", "set r_customwidth 2560", "set r_customheight 1440",
        "set st_personalHud 0", "set st_personalChat 1", "set cg_chatBox 30000",
        "set st_translate 1", "vid_restart", "wait 90",
        *start, "wait 50", "togglemenu", "wait 20", "ui_openmenu ingame_player",
        "wait 80", "st_activeRenderer", "st_personalStatus", "screenshot_png reopened-profile",
        "wait 90", "quit"
    ], renderer="rd-vulkan")
    assert "Connected to a pure server." in log and "Going from CS_PRIMED to CS_ACTIVE" in log
    assert 'st_activeRenderer = "rd-vulkan"' in re.sub(r"\^[0-9]", "", log)
    assert log.count("PERSONAL_UI frontend=ingame_player") >= 2
    assert re.search(r"PERSONAL_UI chat=2 translated=\d+ drawing=1", log)
    for name in ("first-profile", "reopened-profile"):
        shot = game / "screenshots" / (name + ".png")
        assert struct.unpack_from(">II", shot.read_bytes(), 16) == (2560, 1440)
    print("Rendered initial and reopened JA+ profiles at 2560x1440 on mp/ffa3.", flush=True)


if __name__ == "__main__":
    main()
