"""Exercise installed-base PK3 reads and player directory listing on local MP servers."""
import argparse
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time
from zipfile import ZipFile, ZIP_DEFLATED

from beta_release import BUILD_LABEL


ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "dist/base-assets-qa"
GAME = QA / "GameData"
MOD = GAME / "SaberTrials"
SERVER_GAME = QA / "server-game"


def fixture(base, name, explicit):
    prefix = f"models/players/{name}/"
    with ZipFile(base / f"{name}.pk3", "w", ZIP_DEFLATED) as pack, ZipFile(base / "assets1.pk3") as retail:
        if explicit:
            pack.writestr(prefix, b"")
        for leaf in ("model.glm", "model_default.skin", "icon_default.jpg"):
            data = retail.read("models/players/kyle/" + leaf)
            if leaf.endswith(".skin"):
                # JKA identifies pure packs by content CRCs, independent of their names.
                data += ("\n// " + name + "\n").encode("ascii")
            pack.writestr(prefix + leaf, data)
        pack.writestr(f"textures/{name}/probe.jpg", retail.read("models/players/kyle/icon_default.jpg"))


def stage(archive, engine, ui=None):
    for base in (GAME / "base", SERVER_GAME / "base"):
        base.mkdir(parents=True, exist_ok=True)
        for f in [*(ROOT.parent / "base").glob("assets[0-3].pk3"), *(ROOT.parent / "base").glob("*x86_64.dll")]:
            dst = base / f.name
            if not dst.exists():
                try:
                    os.link(f, dst)
                except OSError:
                    shutil.copyfile(f, dst)
    with ZipFile(archive) as package:
        for item in package.infolist():
            if item.filename.startswith("SaberTrials/") and "/client/translator/" not in item.filename:
                package.extract(item, GAME)
    shutil.copy2(engine, MOD / "client/SaberTrials.x86_64.exe")
    if ui:
        for filename in ("uix86_64.dll", "client/SaberTrialsUI.x86_64.dll"):
            shutil.copy2(ui, MOD / filename)
    for name, explicit in (("st_test_personal", False), ("st_test_approved", True)):
        fixture(GAME / "base", name, explicit)
    shutil.copyfile(GAME / "base/st_test_approved.pk3", SERVER_GAME / "base/st_test_approved.pk3")


def options(settings):
    return [word for key, value in settings.items() for word in ("+set", key, str(value))]


def local_port():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def run(mode, pure, launcher, baseline=False):
    tag = f"{mode}-{pure}-" + str(time.time_ns())
    run_dir = QA / tag
    appdata = run_dir / "user"
    home = appdata / "SaberTrials"
    player = home / "SaberTrials"
    player.mkdir(parents=True)
    server_home = run_dir / "server"
    (server_home / mode).mkdir(parents=True)
    hidden = subprocess.STARTUPINFO()
    hidden.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    hidden.wShowWindow = 0
    args = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=hidden)
    port = local_port()
    server = subprocess.Popen([str(ROOT.parent / "openjkded.x86_64.exe"), *options(dict(
        fs_basepath=SERVER_GAME, fs_homepath=server_home, fs_game=mode, dedicated=1,
        logfile=2, net_ip="127.0.0.1", net_port=port, sv_pure=pure, g_gametype=0)), "+map", "mp/ffa3"],
        cwd=SERVER_GAME, **args)
    client = None
    try:
        serverlog = server_home / mode / "qconsole.log"
        for _ in range(160):
            if serverlog.exists() and "InitGame:" in serverlog.read_text(errors="replace"):
                break
            if server.poll() is not None:
                raise RuntimeError("Loopback server exited")
            time.sleep(.15)
        else:
            raise RuntimeError("Loopback server did not start")
        lines = ["wait 30", "echo ST_LOCAL_BEGIN", "fs_game", "fs_basepath", "fs_homepath",
                 "dir models/players /", "echo ST_LOCAL_END", f"connect 127.0.0.1:{port}",
                 "wait 410", "viewpos", "echo ST_ONLINE_BEGIN", "fs_game", "sv_pure",
                 "dir models/players /", "set fs_debug 1"]
        for name in ("st_test_personal", "st_test_approved"):
            for path in (f"models/players/{name}/model.glm", f"textures/{name}/probe.jpg"):
                lines.append("touchFile " + path)
        lines += ["set fs_debug 0", "echo ST_ONLINE_END", "quit"]
        (player / "asset-check.cfg").write_text("\n".join(lines) + "\n")
        cvars = dict(net_ip="127.0.0.1", net_port=local_port(), com_unpackLibraries=0, logfile=2,
                     r_fullscreen=0, r_mode=3, cl_renderer="rd-vanilla", com_maxfps=85,
                     s_initsound=0, com_introplayed=1, st_translate=0, st_personalHud=1)
        command = options(cvars) + ["+exec", "asset-check.cfg"]
        binary = MOD / "client/SaberTrials.x86_64.exe"
        if launcher:
            # Exercise the exact .cmd shipped to testers. START detaches its child.
            command = [os.environ["COMSPEC"], "/d", "/c", "call", str(MOD / "SaberTrials.cmd"), *command]
        else:
            command = [str(binary), *command]
        client = subprocess.Popen(command, cwd=run_dir, env={**os.environ,"LOCALAPPDATA":str(appdata)}, **args)
        for _ in range(480):
            logs = list(home.glob("*/qconsole.log"))
            text = "\n".join(log.read_text(errors="replace") for log in logs)
            if "ST_ONLINE_END" in text:
                break
            time.sleep(.25)
        else:
            raise RuntimeError(f"Client did not complete, see {run_dir}")
        assert client.wait(timeout=15) == 0
        local = text.split("ST_LOCAL_BEGIN",1)[1].split("ST_LOCAL_END",1)[0]
        online = text.split("ST_ONLINE_BEGIN",1)[1].split("ST_ONLINE_END",1)[0]
        assert str(GAME) in local and str(home) in local and "SaberTrials" in local
        assert "ClientBegin:" in serverlog.read_text(errors="replace")
        clean = re.sub(r"\^[0-9]", "", online)
        assert f'sv_pure = "{pure}"' in clean
        assert f'fs_game = "{"" if mode == "base" else mode}"' in clean
        assert "st_test_approved/" in local and "st_test_approved/" in online
        if not baseline:
            assert BUILD_LABEL in text and "st_test_personal/" in local
        for name in ("st_test_personal","st_test_approved"):
            allowed = name=="st_test_approved" or not pure
            # Match the directory listing independently of later debug file paths.
            listed = any(line.split()[-1:] == [name+"/"] for line in online.splitlines())
            assert listed == (allowed and (not baseline or name=="st_test_approved")), (tag, name, listed)
            for path in (f"models/players/{name}/model.glm", f"textures/{name}/probe.jpg"):
                assert (f"FS_FOpenFileRead: {path} (found in '" in online) == allowed, (tag, path)
        print(f"{tag} passed using {'the beta launcher' if launcher else 'the EXE directly'}", flush=True)
    finally:
        for process in (client, server):
            if process and process.poll() is None:
                process.terminate()
                process.wait(timeout=10)


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("archive", type=Path)
    cli.add_argument("engine", type=Path)
    cli.add_argument("--baseline", action="store_true")
    cli.add_argument("--ui", type=Path)
    args = cli.parse_args()
    stage(args.archive, args.engine, args.ui)
    if args.baseline:
        run("base", 0, True, True)
    else:
        for mode in ("base","japlus"):
            for pure in (0,1):
                run(mode, pure, bool(pure))
