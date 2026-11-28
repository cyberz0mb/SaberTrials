"""Verify first capture in three game directories with separate install and profile roots."""
from pathlib import Path
import shutil
import tempfile

from playback import ROOT, run


def check():
    with tempfile.TemporaryDirectory(dir=ROOT / "dist/compat/qa") as work:
        fixture = Path(work)
        data = fixture / "GameData"
        base = data / "base"
        base.mkdir(parents=True)
        for source in (ROOT.parent / "base").glob("assets[0-3].pk3"):
            shutil.copyfile(source, base / source.name)
        for game in ("base", "japlus", "SaberTrials"):
            mod = data / game
            mod.mkdir(exist_ok=True)
            for source in ROOT.glob("*.pk3") if game == "SaberTrials" else ():
                shutil.copyfile(source, mod / source.name)
            modules = ROOT if game == "SaberTrials" else ROOT / "client/stock"
            for source in modules.glob("*.dll"):
                shutil.copyfile(source, mod / source.name)
        client = fixture / "client"
        shutil.copytree(ROOT / "client", client, copy_function=shutil.copyfile)
        exe = client / "candidate.exe"
        shutil.copyfile(ROOT / "dist/compat/build/Release/openjk.x86_64.exe", exe)
        home = fixture / "profile"
        for game in ("base", "japlus", "SaberTrials"):
            folder = data / game / "screenshots"
            assert not folder.exists()
            run(exe, home, game, ["wait 25", "screenshot_png first", "wait 15", "quit"], data=data)
            assert (folder / "first.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
            assert not (home / game / "screenshots").exists()
            assert (home / game / "qconsole.log").is_file()
            print(f"Verified GameData/{game}/screenshots", flush=True)


if __name__ == "__main__":
    check()
