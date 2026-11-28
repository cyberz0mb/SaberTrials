"""Build the optional foreign-module client on the installed pickup/ladder release."""
import argparse
from datetime import datetime
import hashlib
from importlib import import_module
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import zipfile
from mod_compatibility import apply_compatibility, apply_profile
import player_ignore
from compat_art import stage_art
from full_client_ui import patch_engine, patch_frontend
import ja_client
import compat_renderers
import menu_theme
import compat_scoreboard
import cosmetic_outfits
import training_hud
import community_huds
import duel_privacy
import ingame_typography
import music_player

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BASE = DIST / "pug-01"
OUT = DIST / "compat"
CLIENT = "client/SaberTrials.x86_64.exe"
EXE = OUT / "build/Release/openjk.x86_64.exe"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


STOCK_DLLS = ("cgamex86_64.dll", "uix86_64.dll")
RENDERERS = {
    "rd-rend2_x86_64":"ab6f8904a7bb3479d59d28270637e9ad267a3cbd0549bbe8317a4f4db95e7eca",
    "rd-vulkan_x86_64":"9e5bece41f58ee6141a5b123d401f978c27785e2ebcc24eabb7bd1dacd1d3240",
}


def apply_window_branding(tree):
    windows = tree / "codemp/win32"
    shutil.copyfile(ROOT / "assets/branding/SaberTrials.ico", windows / "SaberTrials.ico")
    resource = windows / "openjk.rc"
    source = resource.read_text(encoding="utf-8")
    resource.write_text(source.replace('"../../shared/icons/OpenJK.ico"', '"SaberTrials.ico"')
                        .replace('"OpenJK Multiplayer"', '"Saber Trials Multiplayer"')
                        .replace('"OpenJK.exe"', '"SaberTrials.x86_64.exe"')
                        .replace('"ProductName", "OpenJK"', '"ProductName", "Saber Trials"'),
                        encoding="utf-8")

    sdl = tree / "shared/sdl"
    shutil.copyfile(ROOT / "development-source/compatibility/window_icon.inc", sdl / "window_icon.inc")
    window = sdl / "sdl_window.cpp"
    source = window.read_text(encoding="utf-8")
    anchor = '#include "sdl_icon.h"'
    call = "SDL_SetWindowIcon( screen, icon );"
    if source.count(anchor) != 1 or source.count(call) != 2:
        raise ValueError("Expected both SDL window creation paths")
    window.write_text(source.replace(anchor, anchor + '\n#include "window_icon.inc"')
                      .replace(call, "SetClientWindowIcon( screen, icon );"), encoding="utf-8")


def build_stock():
    archive = DIST / "staff-work/openjk.zip"
    if sha(archive) != "50dee49ccc3dc2b7a3333f6fb1cf50da976b40a38ba01d0971afe47d4ee5b52d":
        raise ValueError("Expected the pinned OpenJK source archive")
    with zipfile.ZipFile(archive) as z:
        source = OUT / "stock-src" / z.namelist()[0]
        if not (source / "codemp/ui/ui_public.h").exists():
            z.extractall(OUT / "stock-src")
    compat_scoreboard.stage_module(source, archive)
    cosmetic_outfits.stage_cgame(source)
    community_huds.stage_cgame(source)
    duel_privacy.stage_client(source)
    ingame_typography.stage_cgame(source)
    flags = import_module("Build-Adaptive-Network").FLAGS
    subprocess.run(["cmake", "-S", source, "-B", OUT / "stock-build", "-G", "Visual Studio 18 2026",
                    "-A", "x64", *[f"-D{f}={'ON' if f in ('BuildMPUI','BuildMPCGame') else 'OFF'}" for f in flags]], check=True)
    subprocess.run(["cmake", "--build", OUT / "stock-build", "--config", "Release", "--parallel", "1",
                    "--target", "uix86_64", "cgamex86_64"], check=True)
    ja_source=OUT/"ja-source"
    ja_client.patch_cgame(source,ja_source)
    compat_scoreboard.stage_module(ja_source, archive)
    cosmetic_outfits.stage_cgame(ja_source)
    community_huds.stage_cgame(ja_source)
    duel_privacy.stage_client(ja_source)
    ingame_typography.stage_cgame(ja_source)
    subprocess.run(["cmake","-S",ja_source,"-B",OUT/"ja-build","-G","Visual Studio 18 2026",
                    "-A","x64",*[f"-D{f}={'ON' if f=='BuildMPCGame' else 'OFF'}" for f in flags]],check=True)
    subprocess.run(["cmake","--build",OUT/"ja-build","--config","Release","--parallel","1",
                    "--target","cgamex86_64"],check=True)


def stage_video_presets(tree):
    # The compatibility checkpoint has newer Setup handlers around the video preset.
    # Refresh just this handler from the maintained Setup source.
    target = tree / "codemp/client/cl_st_setup.inc"
    canonical = (ROOT / "development-source/setup/cl_st_setup.inc").read_text()
    existing = target.read_text()

    def preset_handler(source):
        start = source.index(" case 113:{")
        end = source.index(" case 114:{", start)
        return source[start:end]

    updated = existing.replace(preset_handler(existing), preset_handler(canonical), 1)
    if updated != existing:
        target.write_text(updated)


def stage_pause_browser(frontend):
    polish = ROOT / "development-source/menu-polish"
    sys.path.insert(0, str(polish))
    try:
        import_module("screenshot_layout").patch_ui(frontend)
        import_module("interface_audit").patch_ui(frontend)
    finally:
        sys.path.pop(0)
    runpy.run_path(str(ROOT / "development-source/compatibility/pause_servers.py"))["stage"](frontend)
    cosmetic_outfits.stage_ui(frontend)
    training_hud.stage_menu(frontend)
    community_huds.stage_menu(frontend)
    duel_privacy.stage_menu(frontend)
    music_player.stage_frontend(frontend)


def stage_screenshot_paths(tree):
    path = tree / "codemp/qcommon/files.cpp"
    source = path.read_text()
    marker = "qboolean FS_FileExists( const char *file )"
    helper = r'''static const char *FS_CaptureRoot(const char *path) {
#if defined(_WIN32) && !defined(DEDICATED)
    if (path && !Q_stricmpn(path, "screenshots/", 12)) {
        const char *name = path + 12;
        const char *ext = strrchr(name, '.');
        if (ext && ext != name && !strpbrk(name, "/\\:") &&
            (!Q_stricmp(ext, ".png") || !Q_stricmp(ext, ".jpg") || !Q_stricmp(ext, ".tga"))) {
            return fs_basepath->string;
        }
    }
#endif
    return fs_homepath->string;
}

'''
    if source.count(marker) != 1:
        raise ValueError("Missing screenshot filename lookup")
    source = source.replace(marker, helper + marker)
    for function, old, new in (
        (marker, "fs_homepath->string", "FS_CaptureRoot(file)"),
        ("fileHandle_t FS_FOpenFileWrite(", "fs_homepath->string", "FS_CaptureRoot(filename)"),
    ):
        start = source.index(function)
        end = source.index("\n}", start)
        body = source[start:end]
        if body.count(old) != 1:
            raise ValueError(f"Unexpected write root in {function}")
        source = source[:start] + body.replace(old, new) + source[end:]
    path.write_text(source)


def build():
    browser = runpy.run_path(str(ROOT / "development-source/server-browser/overlay.py"))
    tree = OUT / "engine"
    shutil.copytree(BASE / "engine", tree, dirs_exist_ok=True)
    browser["population_engine"](tree)
    apply_window_branding(tree)
    apply_compatibility(tree / "codemp/client", BASE / "engine/codemp/client")
    stage_art(ROOT, tree)
    patch_engine(ROOT, tree)
    compat_scoreboard.stage_engine(tree)
    ingame_typography.stage_engine(tree)
    runpy.run_path(str(ROOT / "development-source/compatibility/base_assets.py"))["stage"](tree)
    stage_video_presets(tree)
    ja_client.patch_engine(tree)
    compat_renderers.patch(tree)
    menu_theme.engine(tree)
    player_ignore.engine(tree / "codemp/client")
    runpy.run_path(str(ROOT / "development-source/network/live_settings.py"))["stage"](tree)
    cosmetic_outfits.stage_engine(tree)
    training_hud.stage_engine(tree)
    compat_renderers.stage_material_overrides(tree)
    community_huds.stage_engine(tree)
    duel_privacy.stage_menu(tree)
    music_player.stage_engine(tree)
    stage_screenshot_paths(tree)
    music_player.build_desktop()
    # After the mod's native library and the installed base library, try the
    # bundled OpenJK pair. Keep the original pure/unpacking checks above this.
    loader = tree / "shared/sys/sys_main.cpp"
    source = loader.read_text()
    start = source.index("void *Sys_LoadGameDll(")
    left, native = source[:start], source[start:]
    anchor = "libHandle = Sys_LoadDllFromPaths( filename, gamedir, searchPaths, numPaths, SEARCH_PATH_BASE | SEARCH_PATH_MOD, __FUNCTION__ );"
    if native.count(anchor) != 1:
        raise ValueError("Expected one native module loader")
    loader.write_text(left + native.replace(anchor, """#ifndef DEDICATED
                extern bool CL_JAConnection();
                if (!strcmp(name,"cgame") && CL_JAConnection()) {
                    // A real mod-specific native DLL takes priority. The JA+ client
                    // replaces only the generic base fallback after normal PK3 resolution.
                    if (*gamedir && Q_stricmp(gamedir,BASEGAME))
                        libHandle=Sys_LoadDllFromPaths(filename,gamedir,searchPaths,numPaths,SEARCH_PATH_MOD,__FUNCTION__);
                    if(!libHandle){
                        const char *binaryRoot[]={Sys_BinaryPath()};
                        libHandle=Sys_LoadDllFromPaths(filename,"ja-compat",binaryRoot,1,SEARCH_PATH_MOD,__FUNCTION__);
                        if(libHandle)Com_DPrintf("Saber Trials JA+ client renderer loaded.\\n");
                    }
                }
#endif
                if(!libHandle) """+anchor + """
                if (!libHandle && Q_stricmp(gamedir, "SaberTrials") &&
                    (!strcmp(name, "cgame") || !strcmp(name, "ui"))) {
                    const char *binaryRoot[] = {Sys_BinaryPath()};
                    libHandle = Sys_LoadDllFromPaths(filename, "stock", binaryRoot, 1, SEARCH_PATH_MOD, __FUNCTION__);
                }"""))
    loader.write_text(compat_scoreboard.prefer_bundled_base(loader.read_text()))
    flags = import_module("Build-Adaptive-Network").FLAGS
    subprocess.run(["cmake", "-S", tree, "-B", OUT / "build", "-G", "Visual Studio 18 2026",
                    "-A", "x64", "-DST_STAFF_QA=OFF", f"-DST_DEPS={DIST / 'handedness-baseline-06/deps'}",
                    *[f"-D{flag}={'ON' if flag in ('BuildMPEngine','BuildMPRend2','BuildMPRdVulkan') else 'OFF'}" for flag in flags]], check=True)
    subprocess.run(["cmake", "--build", OUT / "build", "--config", "Release", "--parallel", "1",
                    "--target", "openjk.x86_64", *RENDERERS], check=True)
    build_stock()
    frontend = OUT / "frontend"
    shutil.copytree(BASE / "frontend",frontend,dirs_exist_ok=True)
    browser["population_frontend"](frontend)
    apply_profile(frontend / "codemp/ui",BASE / "frontend/codemp/ui")
    player_ignore.catalog(frontend / "codemp/ui/st_controls_catalog.h")
    patch_frontend(frontend)
    ja_client.patch_frontend(frontend)
    menu_theme.frontend(frontend)
    stage_pause_browser(frontend)
    subprocess.run(["cmake", "-S", frontend, "-B", OUT / "ui-build", "-G", "Visual Studio 18 2026",
                    "-A", "x64", "-DST_STAFF_QA=OFF", f"-DST_DEPS={DIST / 'handedness-baseline-06/deps'}",
                    *[f"-D{flag}={'ON' if flag == 'BuildMPUI' else 'OFF'}" for flag in flags]], check=True)
    subprocess.run(["cmake","--build",OUT / "ui-build","--config","Release","--parallel","1","--target","uix86_64"],check=True)


def install():
    ui = "uix86_64.dll"
    files = {CLIENT: EXE, ui: OUT / "ui-build/Release" / ui,
             **{f"client/{name}.dll":EXE.parent/f"{name}.dll" for name in RENDERERS},
             "client/ja-compat/cgamex86_64.dll": OUT/"ja-build/Release/cgamex86_64.dll",
             "client/SaberTrialsUI.x86_64.dll": OUT / "ui-build/Release" / ui,
             **{"client/stock/" + n: OUT / "stock-build/Release" / n for n in STOCK_DLLS}}
    files[cosmetic_outfits.PACK.name] = cosmetic_outfits.PACK
    files["client/" + music_player.PLAYER.name] = music_player.PLAYER
    after = {n: sha(p) for n,p in files.items()}
    before = {n: sha(ROOT / n) for n in files}
    if before == after:
        return
    baseline = sha(BASE / "build-engine/Release/openjk.x86_64.exe")
    receipt = json.loads((DIST / "pug-ladder-final-install.json").read_text())
    previous = sorted(DIST.glob("compat-install-*.json"))
    known = json.loads(previous[-1].read_text()) if previous else {}
    if receipt["after"][CLIENT] != baseline or (before[CLIENT] != baseline and
            (before[CLIENT] != known.get("after", {}).get(CLIENT) or baseline != known.get("baseline"))):
        raise RuntimeError("Installed engine has changed since the compatibility build baseline")
    if before[ui] not in (known.get("after", {}).get(ui), receipt["after"][ui]):
        raise RuntimeError("Installed Saber Trials UI has changed since the build baseline")
    for n in files.keys() - {CLIENT,ui}:
        if n.startswith("client/") and RENDERERS.get(Path(n).stem)==before[n] and before[n] is not None:
            continue
        if before[n] is not None and before[n] not in (after[n], known.get("after", {}).get(n)):
            raise RuntimeError("Bundled stock module differs from the previous install: " + n)
    (ROOT / "client/stock").mkdir(exist_ok=True)
    (ROOT / "client/ja-compat").mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = DIST / "backups" / ("compat-" + stamp)
    import_module("Install-Handedness").install_transaction(
        ROOT, files, before, after, {}, backup, DIST / ("compat-install-" + stamp + ".json"),
        dict(before=before, after=after, baseline=baseline, backup=str(backup)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["build", "install"])
    {"build": build, "install": install}[parser.parse_args().action]()
