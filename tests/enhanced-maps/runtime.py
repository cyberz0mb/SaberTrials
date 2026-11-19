"""Run an isolated Windows multiplayer map smoke test and retain console evidence."""

import argparse
from contextlib import ExitStack, contextmanager
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import statistics
import subprocess
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist/enhanced-maps"
BASE = ROOT / "dist/mvp-cinematic-candidate-03"
ENGINE = DIST / "build-engine/Release"
MOD = "stmaptest"
ADDRESS = "127.0.0.1"


class MemoryCounters(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("faults", wintypes.DWORD),
                *((key, ctypes.c_size_t) for key in
                  ("peak", "working", "quota_peak_paged", "quota_paged",
                   "quota_peak_nonpaged", "quota_nonpaged", "pagefile", "peak_pagefile"))]


def memory(process):
    counters = MemoryCounters()
    counters.size = ctypes.sizeof(counters)
    read = ctypes.WinDLL("psapi").GetProcessMemoryInfo
    read.argtypes = (wintypes.HANDLE, ctypes.POINTER(MemoryCounters), wintypes.DWORD)
    if not read(int(process._handle), ctypes.byref(counters), counters.size):
        raise ctypes.WinError()
    return {key + "_mib": round(getattr(counters, key) / (1 << 20), 1)
            for key in ("working", "peak", "pagefile")}


def udp(port, command):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
        connection.settimeout(0.4)
        connection.sendto(b"\xff" * 4 + command.encode("ascii"), (ADDRESS, port))
        try:
            return connection.recv(65535).decode("ascii", "replace")
        except (TimeoutError, ConnectionResetError):
            return ""


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
        connection.bind((ADDRESS, 0))
        return connection.getsockname()[1]


def read_log(path):
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def wait_for(description, predicate, process, seconds=80):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        if process.poll() is not None:
            raise RuntimeError(f"{description}: process exited with {process.returncode}")
        time.sleep(0.15)
    raise TimeoutError(description)


def archive(stage, las_noches, dense):
    for package in ROOT.glob("*.pk3"):
        shutil.copyfile(package, stage / package.name)
    for filename in ("st_classic", "st_far", "st_dense"):
        if filename == "st_dense" and not dense:
            continue
        source = DIST / "compiled" / (filename + ".bsp")
        with zipfile.ZipFile(stage / (filename + ".pk3"), "w", zipfile.ZIP_DEFLATED, compresslevel=1) as pkg:
            pkg.write(source, f"maps/{source.name}")
            for asset in ("shaders/st_maptest.shader", "textures/st_maptest/grid.tga"):
                pkg.write(DIST / "fixtures" / asset, asset)
    if las_noches:
        shutil.copyfile(las_noches, stage / "lasnoches.pk3")
    with zipfile.ZipFile(stage / "st_bad.pk3", "w") as pkg:
        pkg.writestr("maps/st_bad.bsp", b"RBSP\x02\x00\x00\x00")


@contextmanager
def launch(run, label, *, candidate, server=False, commands=(), **overrides):
    folder = run / label
    folder.mkdir()
    mod = folder / MOD
    mod.mkdir()
    module_sources = {
        "jampgamex86_64.dll": (DIST if candidate else BASE) / "build-game/Release",
        "cgamex86_64.dll": BASE / "build-frontend/Release",
        "uix86_64.dll": BASE / "build-frontend/Release",
    }
    for module, source in module_sources.items():
        if not server or module.startswith("jampgame"):
            shutil.copyfile(source / module, mod / module)
    for pkg in (run / "packages").glob("*.pk3"):
        os.link(pkg, mod / pkg.name)

    role = "build-server" if server else "build-engine"
    source = ENGINE if candidate else BASE / role / "Release"
    binary = "openjkded.x86_64.exe" if server else "openjk.x86_64.exe"
    shutil.copyfile(source / binary, folder / binary)
    if not server:
        for name in ("rd-vanilla_x86_64.dll", "rd-rend2_x86_64.dll"):
            shutil.copyfile(source / name, folder / name)
        for name in ("SDL2.dll", "OpenAL32.dll"):
            shutil.copyfile(ROOT / "client" / name, folder / name)
    settings = {
        "fs_basepath": str(DIST / "stock"), "fs_homepath": str(folder), "fs_game": MOD,
        "net_ip": ADDRESS, "net_port": str(free_port()), "net_enabled": "1",
        "logfile": "2", "developer": "0", "com_introplayed": "1", "sv_pure": "0",
        "sv_allowDownload": "0", "cl_allowDownload": "0", "bot_enable": "0",
        **{f"sv_master{i}": "" for i in range(1, 6)}, **overrides,
    }
    if server:
        settings["dedicated"] = "1"
        settings.update(sv_floodProtect="0", sv_floodProtectSlow="0")
    else:
        settings.update(r_fullscreen="0", r_mode="-1", r_customwidth="960", r_customheight="540",
                        s_initsound="0", com_maxfps="125", r_swapInterval="0", cg_thirdPersonRange="0")
    argv = [str(folder / binary)]
    for key, value in settings.items():
        argv.extend(("+set", key, value))
    (mod / "stmap-qa.cfg").write_text("\n".join(commands) + "\n", encoding="ascii")
    argv.extend(("+exec", "stmap-qa.cfg"))
    log = mod / "qconsole.log"
    with (folder / "stdout.log").open("wb") as stdout:
        process = subprocess.Popen(argv, cwd=folder, stdout=stdout, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW if server else 0)
        try:
            yield process, log
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=15)


def frame_stats(log):
    samples = list(map(int, re.findall(r"frame:\d+ all:\s*(\d+)", log)))
    if not samples:
        raise AssertionError("No frame timings were emitted")
    return {"samples": len(samples), "median_ms": statistics.median(samples),
            "p95_ms": sorted(samples)[int(0.95 * (len(samples) - 1))]}


def benchmark(run, renderer, port, password, map_name):
    udp(port, f"rcon {password} devmap {map_name}")
    commands = (f"connect {ADDRESS}:{port}", "wait 400", "viewpos", "com_speeds 1",
                "r_speeds 1", "wait 130", "com_speeds 0", "r_speeds 0", "echo QA_BENCH_DONE")
    label = renderer + "-bench-" + map_name.replace("/", "-")
    with launch(run, label, candidate=True, cl_renderer=renderer, commands=commands) as (client, log):
        wait_for(f"{map_name} benchmark sample", lambda: "QA_BENCH_DONE" in read_log(log), client, seconds=100)
        content = read_log(log)
        if not re.search(rf"maps/{re.escape(map_name)}\.bsp \(-?\d+ -?\d+ -?\d+\)", content):
            raise AssertionError(f"Client did not enter {map_name} during the benchmark")
        render = re.findall(r"\d+/(?:\d+/)?\d+ (?:shdrs/srfs|shaders/batches/surfs).*?tris", content)
        if not render or "Draw surface capacity exceeded" in content:
            raise AssertionError(f"Missing render counters or queue overflow on {map_name}")
        return {"memory": memory(client), "frames": frame_stats(content), "render_sample": render[-1]}


def run_client_suite(run, renderer, port, password, report, dense, las_noches):
    first_map = "mp/duel1"
    with launch(run, renderer + "-classic-baseline", candidate=False,
                cl_renderer=renderer, name="ClassicProbe",
                commands=(f"connect {ADDRESS}:{port}", "wait 420", "viewpos",
                          "com_speeds 1", "wait 100", "com_speeds 0", "echo QA_BASE_DONE")) as (old, old_log):
        wait_for("Classic client timing sample", lambda: "QA_BASE_DONE" in read_log(old_log), old)
        old_text = read_log(old_log)
        if not re.search(r"maps/mp/duel1\.bsp \(-?\d+ -?\d+ -?\d+\)", old_text):
            raise AssertionError("Classic client never entered the stock map")
        report["classic_client"] = {"memory": memory(old), "frames": frame_stats(old_text)}
        udp(port, f"rcon {password} devmap st_far")
        wait_for("Classic client rejected during map rotation",
                 lambda: "requires a Saber Trials client with Enhanced Map Support" in read_log(old_log), old)
        report["classic_rotation_rejected"] = True

    with launch(run, renderer + "-classic-rejected", candidate=False, cl_renderer=renderer,
                commands=(f"connect {ADDRESS}:{port}",)) as (old, old_log):
        wait_for("Classic client rejected on direct connect",
                 lambda: "requires a Saber Trials client with Enhanced Map Support" in read_log(old_log), old)
        report["classic_direct_rejected"] = True

    probe = [
        f"connect {ADDRESS}:{port}", "wait 470", "echo QA_FAR_BEGIN",
        "setviewpos 130650 120 130836 0", "wait 150", "viewpos",
        "setviewpos 130852 0 130880 0", "wait 150", "viewpos",
        "setviewpos 131010 128 130836 0", "wait 150", "viewpos",
        "setviewpos 130768 -112 130836 270", "wait 100", "+forward", "wait 100",
        "-forward", "wait 80", "viewpos", "com_speeds 1", "r_speeds 1", "wait 100",
        "com_speeds 0", "r_speeds 0", "echo QA_FAR_DONE",
    ]
    with ExitStack() as stack:
        client, log = stack.enter_context(launch(run, renderer + "-far", candidate=True,
                                                 cl_renderer=renderer, name="MapProbe", commands=probe))
        second, second_log = stack.enter_context(launch(
            run, renderer + "-peer", candidate=True, cl_renderer=renderer, name="PeerProbe",
            commands=(f"connect {ADDRESS}:{port}", "wait 700", "viewpos", "echo QA_PEER_DONE")))
        wait_for("Enhanced boundary movement", lambda: "QA_FAR_DONE" in read_log(log), client, seconds=105)
        wait_for("Second enhanced client snapshot", lambda: "QA_PEER_DONE" in read_log(second_log), second)
        far_log = read_log(log)
        locations = [tuple(map(int, p)) for p in re.findall(r"maps/st_far\.bsp \((-?\d+) (-?\d+) (-?\d+)\)", far_log)]
        if len(locations) < 4:
            raise AssertionError(f"Missing enhanced-map client positions: {locations}")
        start, patch, wall, teleport = locations[-4:]
        if not (130700 < start[0] < 130735 and 130800 < start[2] < 130900):
            raise AssertionError(f"Unexpected start position {start}")
        if not (130900 < patch[0] < 130945 and patch[2] > start[2] + 12):
            raise AssertionError(f"Player did not land above the floor on the patch: {patch}")
        if not (131035 < wall[0] < 131048):
            raise AssertionError(f"Player did not stop at the outer wall: {wall}")
        if not (teleport[0] < -130500 and teleport[2] < -130500):
            raise AssertionError(f"Player did not reach the far negative sector: {teleport}")
        status = udp(port, "getstatus")
        if not ("MapProbe" in status and "PeerProbe" in status and "\\sv_stMap\\2" in status and
                re.search(r"maps/st_far\.bsp \(-?\d+ -?\d+ -?\d+\)", read_log(second_log))):
            raise AssertionError("Expected two enhanced players and the advertised map capability")
        report["far"] = {"positions": locations, "memory": memory(client), "peer_memory": memory(second),
                         "frames": frame_stats(far_log)}

        for map_name in (["st_dense"] if dense else []) + (["lasnoches"] if las_noches else []) + [
            "st_classic", first_map, "st_far",
        ]:
            previous = len(read_log(log))
            previous_peer = len(read_log(second_log))
            started = time.monotonic()
            udp(port, f"rcon {password} map {map_name}")
            wait_for(f"Client reload on {map_name}", lambda: "CL_InitCGame:" in read_log(log)[previous:]
                     and "CL_InitCGame:" in read_log(second_log)[previous_peer:]
                     and f"\\mapname\\{map_name}\\" in udp(port, "getstatus"), client, seconds=100)
            report.setdefault("rotations", {})[map_name] = {
                "seconds": round(time.monotonic() - started, 2), "client_memory": memory(client)}
            if "Draw surface capacity exceeded" in read_log(log)[previous:]:
                raise AssertionError(f"Draw surface queue overflowed on {map_name}")
    report["benchmarks"] = {}
    for map_name in [first_map] + (["st_dense"] if dense else []):
        report["benchmarks"][map_name] = benchmark(run, renderer, port, password, map_name)


def run(args):
    stock = DIST / "stock/base"
    stock.mkdir(parents=True, exist_ok=True)
    for archive_path in (ROOT.parent / "base").glob("assets*.pk3"):
        target = stock / archive_path.name
        if not target.exists():
            os.link(archive_path, target)
    run_dir = DIST / "runtime" / (time.strftime("%Y%m%d-%H%M%S") + f"-{time.time_ns() % 10**9:09d}")
    packages = run_dir / "packages"
    packages.mkdir(parents=True)
    archive(packages, args.las_noches, args.dense)
    report = {"run": str(run_dir), "renderer": args.renderer, "dense": args.dense}
    try:
        with launch(run_dir, "server-baseline", server=True, candidate=False,
                    commands=("map mp/duel1", "wait 60", "map st_far")) as (old, log):
            started = time.monotonic()
            wait_for("Stock map initialized in baseline server",
                     lambda: "Server Initialization" in read_log(log) and "InitGame" in read_log(log), old)
            report["baseline_server"] = {"seconds": round(time.monotonic() - started, 2), "memory": memory(old)}
            wait_for("Baseline dedicated server rejects RBSP 2",
                     lambda: "wrong version number (2 should be 1)" in
                     read_log(log.parent.parent / "stdout.log"), old)
            report["baseline_rejects_enhanced_bsp"] = True
        port, password = free_port(), secrets.token_hex(16)
        started = time.monotonic()
        with launch(run_dir, "server-enhanced", server=True, candidate=True, net_port=str(port),
                    rconPassword=password, commands=("map mp/duel1",)) as (server, log):
            wait_for("Stock map initialized in enhanced server", lambda: "duel1" in udp(port, "getstatus"), server)
            report["enhanced_server"] = {"seconds": round(time.monotonic() - started, 2), "memory": memory(server)}
            run_client_suite(run_dir, args.renderer, port, password, report, args.dense, args.las_noches)
            report["enhanced_server_end"] = memory(server)
        with launch(run_dir, "server-malformed", server=True, candidate=True,
                    commands=("map st_bad", "wait 20", "map mp/duel1")) as (server, log):
            wait_for("Malformed BSP rejected and classic map loaded afterward",
                     lambda: "st_bad.bsp: invalid BSP file length" in read_log(log) and
                     "InitGame:" in read_log(log), server)
            report["malformed_recovery"] = True
        report["passed"] = True
    finally:
        (run_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(run_dir, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--renderer", choices=("rd-vanilla", "rd-rend2"), default="rd-vanilla")
    parser.add_argument("--las-noches", type=Path)
    parser.add_argument("--dense", action="store_true")
    run(parser.parse_args())
