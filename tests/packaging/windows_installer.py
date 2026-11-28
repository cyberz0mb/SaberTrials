"""Exercise the release installer in a disposable copy of the retail game."""
import argparse
import binascii
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import winreg
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import beta_release


def crc(path):
    value = 0
    with path.open("rb") as data:
        for chunk in iter(lambda: data.read(1024 * 1024), b""):
            value = binascii.crc32(chunk, value)
    return value


def verify(game, archive, custom):
    with zipfile.ZipFile(archive) as source:
        for entry in source.infolist():
            if entry.is_dir():
                continue
            target = game / entry.filename
            if entry.filename == "README.txt":
                target = game / "SaberTrials/Windows-beta-README.txt"
            if target == custom:
                assert target.read_bytes() == b"// local host settings\n"
            else:
                assert target.stat().st_size == entry.file_size and crc(target) == entry.CRC, target


def run(installer, args):
    return subprocess.run([str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", *args],
                          timeout=900).returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("installer", type=Path)
    parser.add_argument("--retail-base", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    # Avoid an existing user's shortcuts or installer registration.
    key = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{845E0B40-4607-48ED-991A-08986C17826B}_is1"
    for view in (winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_READ | view):
                raise RuntimeError("Use a test account without a current-user Saber Trials installer registration.")
        except FileNotFoundError:
            pass
    args.work.mkdir(parents=True, exist_ok=True)
    programs = subprocess.check_output(["powershell", "-NoProfile", "-Command",
                                        "[Environment]::GetFolderPath('Programs')"], text=True).strip()
    group_dir = Path(programs) / "Saber Trials"
    shortcuts = {"Play Saber Trials": "SaberTrials.x86_64.exe",
                 "Saber Trials Dedicated Server": "SaberTrialsDed.x86_64.exe"}
    if any((group_dir / (name + ".lnk")).exists() for name in shortcuts):
        raise RuntimeError("Use a test account without existing Saber Trials Start Menu shortcuts.")
    release = ROOT / "dist/private-beta"
    with tempfile.TemporaryDirectory(dir=args.work, prefix="acceptance-") as tmp:
        stage = Path(tmp)
        game = stage / "Retail test/GameData"
        base = game / "base"
        base.mkdir(parents=True)
        options = ["/CURRENTUSER", "/SP-", "/TASKS="]
        assert run(args.installer, [*options, "/DIR=" + str(stage / "wrong")]) != 0
        assert not (stage / "wrong/SaberTrials.x86_64.exe").exists()
        print("Rejected a folder without retail assets", flush=True)
        for i in range(4):
            name = f"assets{i}.pk3"
            shutil.copyfile(args.retail_base / name, base / name)
        readme = game / "README.txt"
        readme.write_bytes(b"Existing game readme")
        extra = game / "SaberTrials/local-addon.pk3"
        extra.parent.mkdir()
        extra.write_bytes(b"Personal content")
        custom = game / "SaberTrials/server/sabertrials-host.cfg"
        custom.parent.mkdir()
        custom.write_bytes(b"// local host settings\n")
        uninstaller = game / "SaberTrials/uninstall/unins000.exe"
        try:
            # Pass the retail root first and GameData itself on the second run.
            assert run(args.installer, [*options, "/TYPE=lite", "/DIR=" + str(game.parent)]) == 0
            assert uninstaller.is_file()
            verify(game, release / beta_release.LITE, custom)
            with zipfile.ZipFile(release / beta_release.FULL) as full, zipfile.ZipFile(release / beta_release.LITE) as lite:
                assert not any((game / name).is_file() for name in set(full.namelist()) - set(lite.namelist()))
            for shortcut, target in shortcuts.items():
                link = group_dir / (shortcut + ".lnk")
                command = "(New-Object -ComObject WScript.Shell).CreateShortcut($env:ST_TEST_LINK).TargetPath"
                actual = subprocess.check_output(["powershell", "-NoProfile", "-Command", command],
                                                 env={**os.environ, "ST_TEST_LINK": str(link)}, text=True).strip()
                assert Path(actual) == game / target, (link, actual)
            print("Lite payload, both Start shortcuts and custom settings passed", flush=True)
            assert run(args.installer, [*options, "/TYPE=full", "/DIR=" + str(game)]) == 0
            verify(game, release / beta_release.FULL, custom)
            print("Full upgrade matched the distributed files", flush=True)
        finally:
            if uninstaller.is_file():
                assert run(uninstaller, []) == 0
        assert readme.read_bytes() == b"Existing game readme" and extra.is_file() and custom.is_file()
        assert not (game / "SaberTrials.x86_64.exe").exists() and not (game / "SaberTrialsDed.x86_64.exe").exists()
        assert not any((group_dir / (name + ".lnk")).exists() for name in shortcuts)
        for i in range(4):
            name = f"assets{i}.pk3"
            assert crc(base / name) == crc(args.retail_base / name)
        print("Uninstall preserved retail assets, personal content and host settings", flush=True)


if __name__ == "__main__":
    main()
