"""Exercise the Windows client's own UI, worker and artwork against a local pure game."""
from pathlib import Path
import re
import shutil
import tempfile

from playback import ROOT, run, wheel_start


def tap(key):
    return [f"st_emoteinputqa {key} 1", f"st_emoteinputqa {key} 0"]

def click(x, y):
    return ["st_emoteinputqa motion -1000 -1000", f"st_emoteinputqa motion {x} {y}"] + tap("MOUSE1") + ["wait 4"]


def main():
    directory = ROOT / "dist/compat/qa"
    directory.mkdir(parents=True, exist_ok=True)
    home = Path(tempfile.mkdtemp(dir=directory))
    mod = home / "japlus"
    mod.mkdir()
    profile=home/"SaberTrials"
    profile.mkdir()
    primary=profile/"openjk.cfg"
    primary.write_bytes(b'// player profile\r\nseta sensitivity "7.5"\r\n')
    shutil.copyfile(ROOT / "jampgamex86_64.dll", mod / "jampgamex86_64.dll")
    # Use the installed client with its actual personal frontend and translator packs.
    exe = ROOT / "client/SaberTrials.x86_64.exe"
    lines = wheel_start()
    opening = lines.index("st_emoteuiqa resume")
    lines[opening:opening] = ["st_personalStatus","screenshot_png personal-first-profile"]
    lines += [
        "set st_translate 1", "set st_translateSource 1", "set st_translateTarget 2",
        "set cg_chatBox 30000", "set cg_teamChatsOnly 1", "say This message should stay filtered",
        "wait 15", "st_personalStatus", "set cg_teamChatsOnly 0", "say Hello my friend how are you today",
        "wait 480", "screenshot_png personal-chat", "st_personalStatus",
        "togglemenu", "wait 20", "screenshot_png personal-pause", "st_personalStatus",
        "ui_openmenu st_pause_account", "wait 10", "st_personalStatus", "screenshot_png personal-rules",
        "ui_openmenu ingame_player", "wait 15", "st_personalStatus","st_emoteuiqa open", "wait 15",
        "st_emoteuiqa action 3 1", "st_emoteuiqa action 4 0", "st_emoteuiqa action 5 0", "wait 5",
        "st_emoteuiqa resume", "togglemenu", "ui_openmenu ingame_setup", "wait 20","st_personalStatus",
    ]
    # Open Interface, scroll to Chat text color, select Red, then Apply changes.
    lines += click(180,129) + tap("MWHEELDOWN")*4 + ["wait 6"] + click(246,335)
    lines += click(561,451) + ["screenshot_png personal-settings","st_chatColor",
        "st_serverMenu","wait 8","st_personalStatus"]
    lines += tap("ESCAPE") + ["st_emoteinputqa F6 1"] + tap("1") + [
        "wait 10","screenshot_png personal-wheel","st_emoteinputqa F6 0","wait 6",
        "vid_restart","wait 150","st_emoteuiqa resume","togglemenu","wait 12",
        "st_personalStatus","disconnect","wait 30","quit"]
    log = run(exe, home, "japlus", lines)
    print(home,flush=True)
    for line in log.splitlines():
        if "PERSONAL_UI" in line: print(line)
    assert "Connected to a pure server." in log
    assert "chat=1 translated=1" in log
    assert "chat=0 translated=0" in log
    assert re.findall(r"PERSONAL_UI frontend=(\w+(?: or gameplay)?)",log) == [
        "ingame_player","server or gameplay","server or gameplay","ingame","ingame","ingame_player",
        "ingame_setup","server or gameplay","ingame"]
    assert "Requires a Saber Trials server." in log
    assert "Emote wheel selected amdance" in log
    assert (profile/"ja-emote-wheel.txt").read_text().splitlines()[1]=="amdance"
    assert b'seta sensitivity "7.5"\r\n' in primary.read_bytes()
    assert b'seta st_chatColor "1"' in primary.read_bytes()
    assert any('seta st_chatColor "1"' in cfg.read_text(errors="replace") for cfg in mod.glob("*.cfg"))
    for name in ("first-profile","chat","pause","settings","rules","wheel"):
        assert (mod / f"screenshots/personal-{name}.png").is_file()
    print("Full Profile, Pause, Setup, blocked action, saved color, translation, JA+ layout and mod menu passed.")


if __name__ == "__main__":
    main()
