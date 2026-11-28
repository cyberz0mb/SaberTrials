"""Run the actual client/listen server with isolated profiles and, optionally, a test transport."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import mkdtemp
from runtime import OUT, ROOT, runtime, stop, wait_for


def prepare_fixture():
    # Use a separate test executable. Change only the transport at the edges of
    # the optimizer, so the actual client, serializer, cvars and UI run together.
    tree = OUT / "fixture"
    if not tree.exists():
        shutil.copytree(OUT / "engine", tree)
    shutil.copyfile(OUT / "engine/codemp/qcommon/cvar.cpp", tree / "codemp/qcommon/cvar.cpp")
    for name in ("cl_main.cpp", "cl_input.cpp", "cl_st_setup.inc", "cl_st_network.inc", "st_network.h"):
        source = (OUT / "engine/codemp/client" / name).read_text()
        if name == "cl_st_network.inc":
            source = source.replace("clc.netchan.remoteAddress.type == NA_LOOPBACK", "false")
            source = source.replace("clc.netchan.remoteAddress.type != NA_LOOPBACK", "true")
        if name == "cl_input.cpp":
            source = source.replace("if ( clc.netchan.remoteAddress.type == NA_LOOPBACK )", "if (false)")
        if name == "cl_main.cpp":
            hook = "if (!CL_Netchan_Process( &clc.netchan, msg) )"
            assert source.count(hook) == 1
            source = source.replace(hook, """
    if (cls.state == CA_ACTIVE && from->type == NA_LOOPBACK &&
        Cvar_VariableIntegerValue("test_drop_incoming") &&
        LittleLong(*(int*)msg->data) % 5 == 0) return;
    """ + hook)
        (tree / "codemp/client" / name).write_text(source)
    return tree


def build_fixture():
    tree = prepare_fixture()
    folder = OUT / "b-fixture"
    # Copy the exact release build switches, ignoring cache paths/derived values.
    cache = (OUT / "b-engine/CMakeCache.txt").read_text()
    switches = re.findall(r"^(Build\w+):BOOL=(ON|OFF)$", cache, re.M)
    subprocess.run(["cmake", "-S", tree, "-B", folder, "-G", "Visual Studio 18 2026", "-A", "x64",
                    *[f"-D{k}={v}" for k, v in switches], "-DST_STAFF_QA=OFF",
                    f"-DST_DEPS={ROOT / 'dist/handedness-baseline-06/deps'}"], check=True)
    subprocess.run(["cmake", "--build", folder, "--config", "Release", "--parallel", "1",
                    "--target", "openjk.x86_64"], check=True)


def run(fixture):
    directory = Path(mkdtemp(prefix="fixture-" if fixture else "listen-", dir=OUT))
    _, mod = runtime.stage(directory, "rd-vanilla", installed=True, use_pack=False)
    exe = directory / "bin/SaberTrials.x86_64.exe"
    build = "b-fixture" if fixture else "b-engine"
    shutil.copyfile(OUT / build / "Release/openjk.x86_64.exe", exe)
    shutil.copyfile(OUT / "b-frontend/Release/uix86_64.dll", mod / "uix86_64.dll")
    shutil.copyfile(OUT / "b-frontend/Release/cgamex86_64.dll", mod / "cgamex86_64.dll")
    poll = mod / "net-poll.cfg"
    def commands(lines):
        temp = poll.with_suffix(".tmp")
        temp.write_text("\n".join(lines) + "\n", encoding="ascii")
        os.replace(temp, poll)
    repeat = ["st_netStatus", "wait 18", "exec net-poll.cfg"]
    commands(repeat)
    lines = [f'set sv_master{i} ""' for i in range(1, 6)] + [
        "set sv_fps 30", "set sv_maxRate 90000", "set sv_ratePolicy 2", "set sv_snapsPolicy 2",
        "set cl_lanForcePackets 0", "set sv_pure 0", "set com_maxfps 125", "set r_swapInterval 0",
        "set sv_stAntiScript 1", "set rate 25000", "set snaps 17", "set cl_packetdup 3",
        "set cl_timeNudge -11", "set cl_maxpackets 42", "set st_netStats 1",
        'set net_test_action "exec net-impair.cfg"', "map mp/duel1", "wait 60", "team free", "exec net-poll.cfg"]
    player = runtime.launch(directory, exe, mod, lines, 0, "rd-vanilla")
    print(directory, flush=True)
    try:
        wait_for(player, mod, r"Auto \(.*?\)  Ping \d+ ms  Jitter [\d.]+", 40)
        if fixture:
            wait_for(player, mod, r"Auto \(sampling\).*\n[^\n]*MaxPPS 1000  Snaps req 30  Rate req 90000", 6)
            wait_for(player, mod, r"Auto \(trial\).*\n[^\n]*MaxPPS 1000  Snaps req 30  Rate req 90000  Dup \d+  Sent/s [1-9]\d*", 60)
            (mod / "net-impair.cfg").write_text(
                'set net_test_action ""\ndumpuser 0\nset rate 90000\nset cl_maxpackets 1000'
                '\nwriteconfig during-auto.cfg\nset test_drop_incoming 1\n', encoding="ascii")
            commands(["vstr net_test_action", *repeat])
            wait_for(player, mod, r"Auto \(restored\).*\n[^\n]*MaxPPS (?!1000 )\d+  Snaps req 30  Rate req 90000", 40)
            commands(["set test_drop_incoming 0", *repeat])
            wait_for(player, mod, r"Auto \(restored\).*In loss 0.0%\n[^\n]*MaxPPS 1000  Snaps req 30  Rate req 90000", 45)
        else:
            wait_for(player, mod, r"Auto \(loopback\).*\n[^\n]*Nudge -11  MaxPPS 42", 5)
        commands(["set st_netMode 1", "wait 3", "st_netStatus", "set cl_maxpackets 55",
                  "set st_netMode 0", "wait 3", "st_netStatus", "screenshot_png network-hud",
                  "wait 3", "disconnect", "wait 3", "quit"])
        assert player.wait(timeout=15) == 0
        log = runtime.log(mod)
        assert re.search(r"Manual .*\n[^\n]*Nudge -11  MaxPPS 42  Snaps req 17  Rate req 25000", log)
        assert re.search(r"Off .*\n[^\n]*Nudge -11  MaxPPS 55", log)
        assert (mod / "screenshots/network-hud.png").is_file()
        if fixture:
            assert re.search(r"\brate\s+90000\b", log), "Server did not receive Auto's rate request"
            config = (mod / "during-auto.cfg").read_text()
            for name, value in (("rate", 25000), ("snaps", 17), ("cl_maxpackets", 42), ("cl_packetdup", 3)):
                assert f'seta {name} "{value}"' in config, name
        print("Passed", build, flush=True)
    finally:
        stop(player)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("release", "build-fixture", "fixture"))
    action = p.parse_args().action
    if action == "build-fixture":
        build_fixture()
    else:
        run(action == "fixture")
