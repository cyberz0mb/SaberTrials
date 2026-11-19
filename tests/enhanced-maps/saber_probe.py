"""Check for a server-confirmed saber kill near the enhanced world boundary."""

from contextlib import ExitStack
import re
import time
import zipfile

from runtime import ADDRESS, DIST, archive, free_port, launch, read_log, udp, wait_for


def add_input_menu(packages):
    # The temporary menu provides a way to clear the UI key catcher so scripted
    # movement and attack commands reach the game. Reuse the actual menu lists.
    sources = sorted(packages.glob("*.pk3"), reverse=True) + [DIST / "stock/base/assets1.pk3"]
    with zipfile.ZipFile(packages / "zzzzzzzzzzz_st_map_qa.pk3", "w", zipfile.ZIP_DEFLATED) as patch:
        for name in ("ui/jampmenus.txt", "ui/jampingame.txt"):
            for source in sources:
                with zipfile.ZipFile(source) as original:
                    if name in original.namelist():
                        menu = original.read(name).decode("cp1252")
                        break
            else:
                raise ValueError(f"Missing original menu list {name}")
            end = menu.rindex("}")
            menu = menu[:end] + 'loadMenu { "ui/st_map_qa.menu" }\n' + menu[end:]
            patch.writestr(name, menu.encode("cp1252"))
        patch.writestr("ui/st_map_qa.menu", "menuDef { name st_map_qa rect 0 0 640 480 "
                       "visible 0 fullscreen 0 onESC { uiScript closeingame; } }")


def probe():
    run = DIST / "runtime" / f"saber-{time.time_ns()}"
    packages = run / "packages"
    packages.mkdir(parents=True)
    archive(packages, None, False)
    add_input_menu(packages)
    port = free_port()
    common = (f"connect {ADDRESS}:{port}", "wait 470", "team free", "wait 120",
              "ui_openmenu st_map_qa", "wait 1", "togglemenu", "wait 60")
    print(run, flush=True)
    with ExitStack() as stack:
        server, log = stack.enter_context(launch(
            run, "server", server=True, candidate=True, net_port=str(port),
            commands=("devmap st_far",), g_debugDamage="1", g_spawnInvulnerability="0", g_logSync="1"))
        wait_for("Boundary map started", lambda: "st_far" in udp(port, "getstatus"), server)
        target, target_log = stack.enter_context(launch(
            run, "target", candidate=True, cl_renderer="rd-vanilla", name="SaberTarget",
            commands=(*common, "setviewpos 130760 -33 130832 90", "wait 200", "viewpos",
                      "echo QA_TARGET_READY")))
        wait_for("Saber target ready", lambda: "QA_TARGET_READY" in read_log(target_log), target)
        attacker, attacker_log = stack.enter_context(launch(
            run, "attacker", candidate=True, cl_renderer="rd-vanilla", name="SaberProbe",
            commands=(*common, "weapon 3", "setviewpos 130760 -86 130832 90", "wait 170",
                      "viewpos", "+forward", "wait 9", "-forward", "wait 30", "viewpos",
                      "+attack", "wait 2000", "-attack", "echo QA_SABER_DONE")))
        wait_for("Saber attack sequence completed", lambda: "QA_SABER_DONE" in read_log(attacker_log), attacker)
        def positions(path):
            return [tuple(map(int, p)) for p in re.findall(
                r"maps/st_far\.bsp \((-?\d+) (-?\d+) (-?\d+)\)", read_log(path))]
        observed = positions(attacker_log) + positions(target_log)
        if len(observed) < 3 or any(pos[0] < 130500 or pos[2] < 130500 for pos in observed):
            raise AssertionError(f"Unexpected saber probe positions: {observed}")
        result = re.search(r"Kill: \d+ \d+ \d+: SaberProbe.*killed SaberTarget.*MOD_SABER", read_log(log))
        if not result:
            raise AssertionError(f"No server-confirmed saber kill at {observed}")
        print(f"{result[0]} at {observed}")


if __name__ == "__main__":
    probe()
