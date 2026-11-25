"""Record a real OpenJK multiplayer session, then play it with the release client."""
import argparse
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT.parent


def test_profile(exe, home):
    mod = home / "SaberTrials"
    mod.mkdir()
    shutil.copyfile(ROOT / "dist/compat/ui-build/Release/uix86_64.dll",mod / "uix86_64.dll")
    actions = [(12,1),(9,8),(3,10),(4,0),(5,0),(4,1),(6,0),(1,4),(4,7),(9,8),(3,20),(5,0)]
    lines = ["wait 50", "st_emoteuiqa resume", "ui_openmenu playerMenu", "wait 35", "st_emoteuiqa open","wait 20"]
    for action, arg in actions:
        lines += [f"st_emoteuiqa action {action} {arg}", "wait 4"]
    run(exe,home,"SaberTrials",lines + ["wait 40","screenshot_png ja-profile","wait 10","quit"])
    header, *slots = (mod / "ja-emote-wheel.txt").read_text().splitlines()
    assert header == "JA-WHEEL-1" and len(slots) == 40
    assert slots[:3] == ["ambeg","-","amsurrender"] and slots[-1] == "amkiss", slots
    assert (mod / "screenshots/ja-profile.png").is_file()
    foreign = home / "japlus"
    foreign.mkdir()
    shutil.copyfile(ROOT / "jampgamex86_64.dll",foreign / "jampgamex86_64.dll")
    lines = wheel_start()
    for page,slot in [(0,1),(0,2),(4,8)]:
        lines += ["st_emoteinputqa F6 1"]
        for _ in range(page):
            lines += ["st_emoteinputqa RIGHTARROW 1","st_emoteinputqa RIGHTARROW 0"]
        lines += [f"st_emoteinputqa {slot} 1",f"st_emoteinputqa {slot} 0","st_emoteinputqa F6 0","wait 6"]
    log = run(exe,home,"japlus",lines+["wait 15","quit"])
    assert re.findall(r"Emote wheel selected (\w+)",log) == ["ambeg","amkiss"]
    assert re.findall(r"clientCommand:[^\n]* : (ambeg|amkiss)\s*$",log,re.M) == ["ambeg","amkiss"]
    print("Profile assignments and cleared slot persisted across client restart and JA+ mod switch.")


def wheel_start():
    return [
        "set sv_pure 1", 'set sv_master1 ""', "set g_hybridStyles 0",
        "set g_directionalFeints 0", "set g_manualBlocking 0", "set g_saberHandedness 0",
        "set g_stanceLibrary 0", "map mp/duel1", "wait 120", "st_emoteuiqa resume",
        "team free", "wait 30", "bind F6 +st_emotewheel"]


def test_ja_wheel(exe, home, mod):
    # Independent expectations from the JA+ emote list, including the base
    # gestures that travel as user commands. The fixture logs reliable commands.
    pages = [
        "amsit amdance amsurrender amatease amsit2 amtaunt amhug amkneel",
        "amsit3 amsit4 ambeg sleep amwait amhips amdie amdie2",
        "amhello amnod amshake amcomeon amkiss amnoisy amwon amvictory",
        "ambreakdance ambreakdance2 amneo amflip ampower amfinishinghim amhiltThrow1 amhiltThrow2",
        "amknockmedown amdropsaber taunt bow meditate flourish gloat",
    ]
    inputs = []

    def event(key, pressed):
        inputs.append(f"st_emoteinputqa {key} {int(pressed)}")

    def tap(key):
        event(key, True)
        event(key, False)

    for page, group in enumerate(pages):
        for slot, _ in enumerate(group.split(), start=1):
            event("F6", True)
            for _ in range(page):
                tap(("MWHEELDOWN", "RIGHTARROW", "JOY10")[slot % 3])
            tap(str(slot))
            if slot == 1 and page in (0, 4):
                inputs += ["wait 90", f"screenshot_png ja-wheel-{page+1}", "wait 10"]
            event("F6", False)
            inputs.append("wait 5")
    # Backward wrap to the partial fifth page. Its unused slot must clear
    # the prior selection so releasing cannot dispatch it.
    event("F6", True)
    tap("LEFTARROW")
    tap("1")
    tap("8")
    event("F6", False)
    log = run(exe, home, "japlus", wheel_start()+inputs+["wait 15", "quit"])
    expected = " ".join(pages).split()
    assert re.findall(r"Emote wheel selected (\w+)", log) == expected, mod
    wire = re.findall(r"clientCommand:[^\n]*? : (\w+)\s*$", log, re.M)
    expected_wire = expected[:-5]
    assert [c for c in wire if c in expected_wire] == expected_wire, mod
    assert all((mod / f"screenshots/ja-wheel-{n}.png").is_file() for n in (1, 5))
    assert "Connected to a pure server." in log and "Going from CS_PRIMED to CS_ACTIVE" in log
    print(f"Selected all {len(expected)} JA+ wheel entries across {len(pages)} pages; verified {len(expected_wire)} reliable commands.")


def run(exe, home, game, lines, data=DATA, renderer="rd-vanilla", safe=True):
    mod = home / game
    mod.mkdir(parents=True, exist_ok=True)
    (mod / "compat-qa.cfg").write_text("\n".join(lines) + "\n", encoding="ascii")
    settings = dict(fs_basepath=data, fs_homepath=home, fs_game=game, logfile=2,
                    com_unpackLibraries=0, com_introplayed=1, developer=1, net_enabled=0,
                    s_initsound=0, r_fullscreen=0, r_mode=3, cl_renderer=renderer, com_maxfps=60)
    args = [exe, "+safe"] if safe else [exe]
    for key, value in settings.items():
        args.extend(["+set", key, str(value)])
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    subprocess.run(args + ["+exec", "compat-qa.cfg"], cwd=exe.parent, startupinfo=startup, timeout=75, check=True)
    return "\n".join(f.read_text(errors="replace") for f in home.rglob("qconsole.log"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["record", "play", "retail", "wheel", "trials", "profile"])
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    directory = args.directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    demo = directory / "stock.dm_26"
    if args.phase == "record":
        home = Path(tempfile.mkdtemp(dir=directory))
        log = run(DATA / "openjk.x86_64.exe", home, "base", [
            "set sv_pure 1", "set sv_master1 \"\"", "map mp/duel1", "wait 120",
            "record stock", "wait 8", "+forward", "wait 90", "-forward", "wait 90", "stoprecord", "quit"])
        source, = home.rglob("stock.dm_26")
        assert "Stopped demo" in log and source.stat().st_size > 1024, log[-2000:]
        shutil.copyfile(source, demo)
    else:
        binary = Path(tempfile.mkdtemp(dir=directory))
        exe = binary / "SaberTrials.x86_64.exe"
        shutil.copyfile(ROOT / "dist/compat/build/Release/openjk.x86_64.exe", exe)
        shutil.copyfile(ROOT / "dist/compat/ui-build/Release/uix86_64.dll", binary / "SaberTrialsUI.x86_64.dll")
        (binary/"ja-compat").mkdir()
        shutil.copyfile(ROOT/"dist/compat/ja-build/Release/cgamex86_64.dll",binary/"ja-compat/cgamex86_64.dll")
        for name in ["SDL2.dll", "OpenAL32.dll", "rd-vanilla_x86_64.dll"]:
            shutil.copyfile(ROOT / "client" / name, binary / name)
        data = DATA
        if args.phase == "profile":
            test_profile(exe,Path(tempfile.mkdtemp(dir=directory)))
            return
        if args.phase == "retail":
            asset_copy = tempfile.TemporaryDirectory(dir=directory)
            data = Path(asset_copy.name)
            (data / "base").mkdir()
            for i in range(4):
                name = f"assets{i}.pk3"
                try:
                    os.link(DATA / "base" / name, data / "base" / name)
                except OSError:
                    shutil.copyfile(DATA / "base" / name, data / "base" / name)
            (binary / "stock").mkdir()
            for name in ["uix86_64.dll", "cgamex86_64.dll"]:
                shutil.copyfile(ROOT / "dist/compat/stock-build/Release" / name, binary / "stock" / name)
        if args.phase == "trials":
            home = Path(tempfile.mkdtemp(dir=directory))
            log = run(exe, home, "SaberTrials", ["set sv_pure 0", "map mp/duel1",
                      "wait 120", "st_netStatus", "echo COMPAT_TRIALS_DONE", "quit"])
            assert "Going from CS_PRIMED to CS_ACTIVE" in log and "COMPAT_TRIALS_DONE" in log and "Auto (" in log
            print("Saber Trials pickup/ladder modules loaded and network optimizer active")
            return
        if args.phase == "wheel":
            # An instrumented-by-logging local receiver. It is not a JA+ server.
            home = Path(tempfile.mkdtemp(dir=directory))
            mod = home / "japlus"
            mod.mkdir()
            shutil.copyfile(ROOT / "jampgamex86_64.dll", mod / "jampgamex86_64.dll")
            test_ja_wheel(exe, home, mod)
            return
        for game in (["base"] if args.phase == "retail" else ["base", "japlus"]):
            home = Path(tempfile.mkdtemp(dir=directory))
            dest = home / game / "demos/compat-stock.dm_26"
            dest.parent.mkdir(parents=True)
            shutil.copyfile(demo, dest)
            log = run(exe, home, game, ["timedemo 1", "demo compat-stock", "wait 180", "echo COMPAT_PLAYBACK_DONE", "quit"], data)
            assert "COMPAT_PLAYBACK_DONE" in log and " frames," in log, log[-2500:]
            print(f"{game}: completed stock OpenJK snapshot playback")


if __name__ == "__main__":
    main()
