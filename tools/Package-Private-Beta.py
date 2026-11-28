"""Package the installed client or compiled Linux pair for private beta testing."""
import argparse
import os
from pathlib import Path
import stat
import tempfile
import zipfile
import beta_release
import windows_launchers


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist/private-beta"
ASSETS = ("ext_data", "gfx", "maps", "menu", "models", "scripts", "shaders", "sound", "textures", "ui")
STANDALONE_PLAYER_MODELS = {"luffy", "luffy_g5", "luffy_newworld", "luffy_wano"}
WINDOWS_CLIENT_README = f"""Saber Trials | Windows x64 multiplayer client | {beta_release.VERSION}

1. Open the GameData folder inside your Jedi Academy installation.
   In Steam, right-click Jedi Academy and choose Manage > Browse local files.
2. Extract the ZIP into GameData. The SaberTrials folder should be next to base.
3. In GameData, double-click SaberTrials.x86_64.exe to play.

To host a dedicated server, double-click SaberTrialsDed.x86_64.exe in GameData.
It starts Free For All on mp/ffa3. Edit SaberTrials/server/sabertrials-host.cfg to customize it.

For tournament play, choose Play > Tournament and join the host. See
SaberTrials/docs/Tournament-Playtest.md for registration and ready checks.

Returning testers can close the game and extract the same edition over their
existing installation. Setup > Network > Auto uses the full packet range.
Existing Manual or Off selections are preserved.

Choose Setup > Interface > Menu Theme to switch between Saber Trials and Classic JKA.
Host a Match has a separate Gameplay selector for local matches.

Hats and capes come from TaystJK and its contributors. Saber Trials adds the
visual picker under Profile > Cosmetics. Preview an item on your model, then
choose Save outfit. Other compatible clients can see it when the server relays
your selection and they have the matching cosmetic.
TaystJK project: https://github.com/taysta/TaystJK

Choose a combat HUD in Setup > Interface > HUD style. Classic Jedi Academy,
Simple HUD and Jedi Outcast come from Raven Software's games. Elegance is by
DarthNormaN. The Quake-style layout builds on their menu and comes through
TaystJK. See CREDITS.txt for sources.

Settings and logs are saved under %LOCALAPPDATA%\\SaberTrials.
In-game screenshots are saved in the active game's screenshots folder under
GameData (base, japlus, or SaberTrials). The first capture creates the folder.
"""


def runtime_files(folder):
    for path in sorted(folder.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and not path.name.startswith("."):
            if path.suffix.lower() not in (".bak", ".log", ".tmp", ".pyc", ".pdb"):
                yield path


def package(platform, linux, vc_crt=None):
    files = {}
    client_only = platform == "windows-client"
    def add_mod(path):
        files["SaberTrials/" + path.relative_to(ROOT).as_posix()] = path
    for name in ("LICENSE.txt", "CREDITS.txt"):
        add_mod(ROOT/name)
    if not client_only:
        add_mod(ROOT/"description.txt")
        add_mod(ROOT/"docs/Anti-Script.md")
    for path in sorted(ROOT.glob("*sabertrials*.pk3")):
        add_mod(path)
    for folder in ASSETS:
        for path in runtime_files(ROOT/folder):
            parts = path.relative_to(ROOT).parts
            if (client_only and len(parts) >= 4 and parts[:2] == ("models", "players")
                    and parts[2].lower() in STANDALONE_PLAYER_MODELS):
                continue
            add_mod(path)
    if client_only:
        add_mod(ROOT/"docs/Tournament-Playtest.md")
        add_mod(ROOT/"docs/Player-Ignore.md")
        for config in ("tournament-test.cfg", "tournament-teams-test.cfg"):
            files["SaberTrials/"+config] = ROOT/"templates/linux"/config
        for path in sorted((ROOT/"server").glob("sabertrials-*.cfg")):
            add_mod(path)
        files["SaberTrials/SaberTrials-Cosmetics.pk3"] = ROOT/"assets/cosmetics/SaberTrials-Cosmetics.pk3"
        add_mod(ROOT/"z_st_match_formats.pk3")
        for path in sorted((ROOT/"dlc/emotes").glob("*.pk3")):
            add_mod(path)
    else:
        for path in sorted((ROOT/"server").glob("sabertrials-*.cfg")):
            add_mod(path)
    if platform in ("windows", "windows-client"):
        files.update(windows_launchers.build())
        add_mod(ROOT/"SaberTrialsDed.x86_64.exe")
        if client_only:
            files["SaberTrials/SaberTrials.cmd"] = ROOT/"templates/windows/SaberTrials.cmd"
        else:
            add_mod(ROOT/"docs/Client-Compatibility.md")
        add_mod(ROOT/"docs/Music-Player.md")
        for name in ("SaberTrials.x86_64.exe", "SaberTrials Music.exe", "SaberTrialsUI.x86_64.dll", "SDL2.dll", "OpenAL32.dll",
                     "rd-vanilla_x86_64.dll", "rd-rend2_x86_64.dll", "rd-vulkan_x86_64.dll"):
            add_mod(ROOT/"client"/name)
        for folder in ("translator", "licenses", "stock", "ja-compat"):
            for path in runtime_files(ROOT/"client"/folder):
                add_mod(path)
        for name in ("cgamex86_64.dll", "uix86_64.dll"):
            add_mod(ROOT/name)
        if not client_only:
            add_mod(ROOT/"tools/launchers/SaberTrials.cmd")
        # Local listen matches use the game module for the selected combat preset.
        add_mod(ROOT/"jampgamex86_64.dll")
        name = "SaberTrials-Windows-x64-private.zip"
        instructions = """Saber Trials private Windows beta candidate

Extract this archive into the GameData directory of your installed Jedi Academy.
Double-click SaberTrials.x86_64.exe in GameData to play, or SaberTrialsDed.x86_64.exe to host.
The offline text translation models are included. An existing Jedi Academy base game is required.
When testing opens, join the US or Europe server designated by the organizer.
For feedback, include the server, map, approximate time, what you did and what happened.
"""
        if client_only:
            beta_release.verify_engine((ROOT/"client/SaberTrials.x86_64.exe").read_bytes())
            name = beta_release.FULL
            instructions = WINDOWS_CLIENT_README
            if vc_crt:
                for dll in ("msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll"):
                    files["SaberTrials/client/"+dll] = vc_crt/dll
                    files["SaberTrials/"+dll] = vc_crt/dll
            else:
                instructions += "\nRequires the Microsoft Visual C++ v14 x64 runtime.\n"
    else:
        files["openjkded.x86_64"] = linux/"openjkded.x86_64"
        files["SaberTrials/jampgamex86_64.so"] = linux/"jampgamex86_64.so"
        files["SaberTrials/server.cfg.example"] = ROOT/"templates/linux/server.cfg.example"
        files["start-sabertrials.sh"] = ROOT/"templates/linux/start-sabertrials.sh"
        instructions = """Saber Trials private Linux x86_64 server candidate

Back up the server engine and mod directory. During the maintenance window, stop the server and
extract beside the existing licensed base/ directory. Install the dedicated engine and game module
together. Keep the host's assigned port, startup configuration, private account data and server.cfg.
The existing startup command must launch openjkded.x86_64 with fs_game set to SaberTrials.
Use chmod 755 openjkded.x86_64 if the upload tool discards execute permissions.
The anti-script setting defaults to Off. To record beta feedback without penalties, enter
set sv_stAntiScript 1 at the server console. See SaberTrials/docs/Anti-Script.md for the mode and account requirements.
"""
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=OUT, suffix=".partial", delete=False) as temp:
        pending = Path(temp.name)
    try:
        with zipfile.ZipFile(pending, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
            archive.writestr("README.txt", instructions)
            for dest, path in sorted(files.items()):
                if dest in ("start-sabertrials.sh", "openjkded.x86_64"):
                    info = zipfile.ZipInfo(dest)
                    info.create_system = 3
                    info.external_attr = (stat.S_IFREG | 0o755) << 16
                    data = path.read_bytes()
                    if dest.endswith(".sh"):
                        data = data.replace(b"\r\n", b"\n")
                    archive.writestr(info, data, zipfile.ZIP_DEFLATED, compresslevel=1)
                else:
                    archive.write(path, dest)
        with zipfile.ZipFile(pending) as archive:
            if set(archive.namelist()) != set(files) | {"README.txt"} or archive.testzip():
                raise ValueError("Archive verification failed")
        os.replace(pending, OUT/name)
    finally:
        pending.unlink(missing_ok=True)
    print(OUT/name, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", choices=("windows", "windows-client", "linux"))
    parser.add_argument("--linux", type=Path, default=ROOT/"dist/linux-server-release")
    parser.add_argument("--vc-crt", type=Path, help="Path to the app-local x64 Microsoft VC CRT redistributable directory")
    options = parser.parse_args()
    package(options.platform, options.linux, options.vc_crt)
