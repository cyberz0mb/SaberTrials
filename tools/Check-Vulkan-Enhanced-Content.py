"""Exercise expanded worlds and high-detail GLMs together in a disposable Windows profile."""
import argparse
from datetime import datetime
from importlib import import_module
from pathlib import Path
import re
import shutil
import socket
import zipfile


vulkan = import_module("Check-Vulkan")
build = vulkan.b
ROOT = build.ROOT
DLL = "rd-vulkan_x86_64.dll"
OUT = ROOT / "dist/vulkan-content"


def crowd_fixture(home, fixture):
    # Reuse just the authored arena and NPC definitions. Keep the installed menus in use.
    with zipfile.ZipFile(home / "st_vulkan_crowd.pk3", "w", zipfile.ZIP_DEFLATED) as package:
        for archive, entries in (
                ("st_combined_map_fixtures.pk3", ("maps/st_t800bench.bsp", "shaders/st_t800bench.shader")),
                ("zz_t800_test_ui.pk3", ("ext_data/npcs/st_team_qa.npc",))):
            with zipfile.ZipFile(fixture / archive) as source:
                for entry in entries:
                    package.writestr(entry, source.read(entry))
    lines = ["devmap st_t800bench", "wait 220", "team free", "wait 120", "st_emoteuiqa resume",
             "god", "set cg_thirdPerson 0", "set d_npcfreeze 1", "set r_lodscale 20", "set r_lodbias 0"]
    variants = ["t800", "t800", "t800", "t800_endo", "t800", "t800", "t800", "t800_endo",
                "st_team_human_red", "st_team_endo_blue", "st_team_human_blue", "st_team_endo_red"]
    for i, variant in enumerate(variants):
        row, column = divmod(i, 4)
        x = -240 + 40 * (row % 2) + 160 * column
        lines += [f"setviewpos {x} {580 - row * 200} 32 270", "wait 40",
                  f"cmd npc spawn {variant} perf_{i}", "wait 40"]
    return lines + ["team spectator", "wait 80", "setviewpos 0 -620 48 90", "wait 180",
                    "viewpos", "entitylist", "st_activeRenderer", "screenshot_png crowd", "wait 10"]


def scenario(renderer, cache, las_noches, crowd, device):
    run = OUT / ("check-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    binary = run / "bin"
    home = run / "home/SaberTrials"
    binary.mkdir(parents=True)
    home.mkdir(parents=True)
    for name in ("SaberTrials.x86_64.exe", "SDL2.dll", "OpenAL32.dll", "SaberTrialsUI.x86_64.dll"):
        shutil.copyfile(ROOT / "client" / name, binary / name)
    shutil.copyfile(renderer, binary / DLL)
    fixtures = ROOT / "dist/enhanced-maps/maps"
    for name in ("st_classic", "st_far", "st_dense"):
        shutil.copyfile(fixtures / (name + ".pk3"), home / (name + ".pk3"))
    if las_noches:
        shutil.copyfile(las_noches, home / "lasnoches.pk3")
    maps = ["mp/ffa3", "st_far", "st_dense", "st_classic"]
    if las_noches:
        maps.append("lasnoches")
    lines = [f'set sv_master{i} ""' for i in range(1, 6)]
    lines += ["set g_gametype 0", "set g_warmup 0", "set cg_forceModel 0",
             "set cg_deferPlayers 0", "set cg_thirdPerson 1", "set cg_thirdPersonRange 90",
             "set cg_thirdPersonAngle 180", "set cg_thirdPersonVertOffset -30", "set cg_draw2D 0",
             "set g_spawnInvulnerability 0", "set cg_shadows 1", "set r_lodscale 20",
             "set r_lodbias -2", "set r_enhancedModels 1", "model t800_human/default"]
    for level in maps:
        lines += ["echo ST_ENTER_" + level, "devmap " + level, "wait 230", "team free",
                  "wait 100", "st_emoteuiqa resume", "wait 40", "viewpos", "st_activeRenderer"]
        if level == "mp/ffa3":
            lines += ["model t800_human/default", "wait 80", "setviewpos 728 1200 -56 270", "wait 50"]
            for lod in range(3):
                lines += [f"set r_lodbias {lod}", "wait 50", f"screenshot_png human-lod{lod}"]
            lines += ["set r_lodbias -2", "model t800_endo/default", "wait 100",
                      "screenshot_png endo", "model t800_human/default", "wait 80"]
        if level == "st_far":
            for x in (130768, -130768):
                lines += [f"setviewpos {x} 32 {x + 72} 0", "wait 40", "viewpos"]
            lines += ["screenshot_png far"]
        if level == "st_dense":
            # Force one complete view so the backend counters detect the historical clamp.
            lines += ["set r_novis 1", "set r_nocull 1", "wait 12", "set r_speeds 1",
                      "wait 10", "set r_speeds 0", "set r_nocull 0", "set r_novis 0",
                      "wait 50", "screenshot_png dense"]
        lines += ["echo ST_LEAVE_" + level]
    lines += ["echo ST_RESTART", "vid_restart", "wait 220", "viewpos", "st_activeRenderer",
              "screenshot_png restart", "echo ST_AFTER_RESTART"]
    if crowd:
        lines += ["echo ST_CROWD", *crowd_fixture(home, crowd)]
    lines += ["echo ST_CONTENT_DONE", "wait 8", "quit"]
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    opts = dict(net_port=port, net_enabled=1, r_vbo=cache, r_vbo_models=cache,
                r_swapInterval=0, r_customwidth=960, r_customheight=540, in_mouse=0)
    if device is not None:
        opts["r_device"] = device
    print(run, flush=True)
    process = vulkan.launch(run, home, "rd-vulkan", lines, opts)
    try:
        code = process.wait(timeout=360)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    log = re.sub(r"\^[0-9]", "", (home / "qconsole.log").read_text(errors="replace"))
    assert code == 0 and "ST_CONTENT_DONE" in log, f"Client did not complete ({code}): {run}"
    assert 'ERROR:' not in log and 'Saved graphics settings retained.' not in log, run
    assert 'Draw surface capacity exceeded' not in log, run
    sections = {level: log.split("ST_ENTER_" + level, 1)[1].split("ST_LEAVE_" + level, 1)[0]
                for level in maps}
    for level, section in sections.items():
        assert f"maps/{level}.bsp (" in section and 'Cvar st_activeRenderer = "rd-vulkan"' in section, level
    far = sections["st_far"]
    coords = [tuple(map(int, row)) for row in re.findall(r"maps/st_far\.bsp \((-?\d+) (-?\d+) (-?\d+)\)", far)]
    assert any(x > 130500 and z > 130500 for x, _, z in coords), coords
    assert any(x < -130500 and z < -130500 for x, _, z in coords), coords
    dense = sections["st_dense"]
    surfaces = max(map(int, re.findall(r"\d+/(\d+) shdrs/srfs", dense)), default=0)
    assert surfaces >= 203137, f"Dense view truncated at {surfaces} surfaces"
    if cache:
        assert re.search(r"found [1-9]\d{5,} VBO surfaces", dense), "Static geometry cache was not exercised"
    for variant, lod in (("human", 0), ("human", 1), ("human", 2), ("endo", 0)):
        assert re.search(rf"ST_COSMETIC draw classic=.*? visual=models/cosmetics/t800_{variant}/model.glm surfaces=\d+ lod={lod}\b",
                         sections["mp/ffa3"]), (variant, lod)
    assert "ST_COSMETIC draw " in far, "Enhanced character missing from enhanced map"
    restart = log.split("ST_RESTART", 1)[1].split("ST_AFTER_RESTART", 1)[0]
    assert f"maps/{maps[-1]}.bsp (" in restart and 'Cvar st_activeRenderer = "rd-vulkan"' in restart
    captures = {p.stem: build.sha(p) for p in (home / "screenshots").glob("*.png")}
    assert {"human-lod0", "human-lod1", "human-lod2", "endo", "far", "dense", "restart"} <= captures.keys()
    if crowd:
        section = log.split("ST_CROWD", 1)[1]
        assert "maps/st_t800bench.bsp (" in section and "crowd" in captures
        assert len(re.findall(r"\b\d+:ET_NPC\s+NPC\s*$", section, re.M)) == 12
        assert "ST_MODEL_SURFACE_POOL passed legacy 2048" in section
        assert re.search(r"ST_COSMETIC draw .*visual=models/cosmetics/[^ ]*team[^ ]* .*lod=0", section)
        assert 'Cvar st_activeRenderer = "rd-vulkan"' in section
    result = dict(passed=True, renderer=build.sha(binary / DLL), client=build.sha(binary / "SaberTrials.x86_64.exe"),
                  vertex_buffers=bool(cache), maps=maps, dense_peak_surfaces=surfaces, far_positions=coords,
                  device=re.search(r"VK_RENDERER: ([^\n]+)", log)[1].strip(), crowd=bool(crowd),
                  screenshots=captures, log=build.sha(home / "qconsole.log"))
    build.write(run / "result.json", result)
    print(f"Passed with {surfaces} submitted surfaces, vertex buffers {cache}.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--renderer-dll", type=Path, default=ROOT / "client" / DLL)
    parser.add_argument("--cache", type=int, choices=(0, 1), nargs="+", default=[0, 1])
    parser.add_argument("--las-noches", type=Path)
    parser.add_argument("--crowd-fixture", type=Path, help="T800 test mod directory containing the crowd arena and NPC definitions")
    parser.add_argument("--device", type=int, help="Vulkan device selection, as accepted by r_device")
    args = parser.parse_args()
    for setting in args.cache:
        scenario(args.renderer_dll, setting, args.las_noches, args.crowd_fixture, args.device)
