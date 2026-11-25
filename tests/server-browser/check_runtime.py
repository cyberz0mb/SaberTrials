"""Run the staged Windows build against two local masters and a real server."""
import argparse
from contextlib import ExitStack
from importlib import import_module
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess
import sys
from tempfile import mkdtemp
from threading import Thread
import time
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
runtime = import_module("Check-Emotes")
BUILD = ROOT / "dist/server-browser-01"
PACKAGE = BUILD / "zzzzzzzzzzzzzzz_sabertrials_browser.pk3"
PREFIX = b"\xff" * 4


def wait_for(predicate, description, timeout=35):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.1)
    raise RuntimeError(f"Timed out waiting for {description}")


def udp(stack):
    sock = stack.enter_context(socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
    sock.bind(("127.0.0.1", 0))
    sock.settimeout(0.2)
    return sock


def port(sock):
    return sock.getsockname()[1]


def responder(sock, reply):
    def run():
        while True:
            try:
                packet, sender = sock.recvfrom(4096)
                data = reply(packet)
                if data:
                    sock.sendto(data, sender)
            except TimeoutError:
                continue
            except OSError:
                return
    Thread(target=run, daemon=True).start()


def master(*ports, movie=False):
    lead = PREFIX + b"getserversResponse" + (b"\n" if movie else b"")
    packet = lead + b"".join(b"\\\x7f\x00\x00\x01" + struct.pack(">H", n) for n in ports) + b"\\EOT"
    return lambda query: packet if query == PREFIX + b"getservers 26 full empty" else None


def info(name, delay=0, protocol=26, clients=3, humans=None, bots=None, capacity=6):
    def reply(query):
        if not query.startswith(PREFIX + b"getinfo "):
            return None
        time.sleep(delay)
        challenge = query.split()[1].decode("ascii")
        data = dict(challenge=challenge, protocol=protocol, hostname=name, mapname="mp/ffa3",
                    clients=clients, sv_maxclients=capacity, gametype=0, needpass=0, game="SaberTrials")
        if humans is not None:
            data["g_humanplayers"] = humans
        if bots is not None:
            data["bots"] = bots
        return PREFIX + b"infoResponse\n" + "".join(f"\\{key}\\{value}" for key, value in data.items()).encode("ascii")
    return reply


def native_has_bot(server_port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(0.3)
            sock.connect(("127.0.0.1", server_port))
            sock.send(PREFIX + b"getinfo browser-smoke")
            reply = sock.recv(4096)
        return all(field in reply for field in (b"\\clients\\1\\", b"\\g_humanplayers\\0\\",
                                                 b"\\st_combatMode\\1\\", b"\\sv_maxclients\\6\\"))
    except OSError:
        return False


def stage(run, renderer, server=False, compatibility=False):
    exe, mod = runtime.stage(run, renderer, server=server, use_pack=False)
    if compatibility and not server:
        compat = ROOT / "dist/compat"
        ui = compat / "ui-build/Release/uix86_64.dll"
        shutil.copyfile(compat / "build/Release/openjk.x86_64.exe", exe)
        shutil.copyfile(ui, mod / "uix86_64.dll")
        shutil.copyfile(ui, exe.parent / "SaberTrialsUI.x86_64.dll")
        return exe, mod
    role, binary = ("dedicated", "openjkded.x86_64.exe") if server else ("engine", "openjk.x86_64.exe")
    shutil.copyfile(BUILD / f"build-{role}/Release" / binary, exe)
    if not server:
        shutil.copyfile(BUILD / "build-ui/Release/uix86_64.dll", mod / "uix86_64.dll")
    return exe, mod


def fixture_menu(mod):
    """Expose stock menu actions to the scripted client, in the isolated test home."""
    with ZipFile(PACKAGE) as original, ZipFile(mod / PACKAGE.name, "w") as overlay:
        name = "ui/jamp/joinserver.menu"
        for entry in original.namelist():
            if entry != name:
                overlay.writestr(entry, original.read(entry))
        menu = original.read(name).decode("utf-8").replace("onOpen { uiScript QuickOpen }", "")
        end = menu.rfind("}")
        fixtures = '''
            menuDef { name "st_test_find" rect 0 0 0 0 visible 0
                onOpen { close st_test_find ; open joinserver ; open st_quickmatch ;
                    uiScript QuickOpen ; uiScript QuickFind ; } }
            menuDef { name "st_test_join" rect 0 0 0 0 visible 0
                onOpen { close st_test_join ; open joinserver ; open st_quickmatch ;
                    uiScript QuickJoin ; exec "exec browser-confirm.cfg" ; } }
            menuDef { name "st_test_enter_password" rect 0 0 0 0 visible 0
                onOpen { close st_test_enter_password ; uiScript JoinServer ;
                    exec "exec browser-finish.cfg" ; } }
            menuDef { name "st_test_clear" rect 0 0 0 0 visible 0
                onOpen { close st_test_clear ; open joinserver ; open st_quickmatch ; uiScript QuickClear ; } }
            menuDef { name "st_test_population_refresh" rect 0 0 0 0 visible 0
                onOpen { close st_test_population_refresh ; uiScript RefreshServers ; } }
        '''
        overlay.writestr(name, menu[:end] + fixtures + menu[end:])


def main(renderer, protected, compatibility):
    evidence = Path(mkdtemp(prefix="runtime-", dir=BUILD))
    print(evidence, flush=True)
    with ExitStack() as stack:
        first, second, missing, slow, full, wrong = [udp(stack) for _ in range(6)]
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserved:
            reserved.bind(("127.0.0.1", 0))
            server_port = port(reserved)
        responder(first, master(server_port, server_port, port(full)))
        responder(second, master(port(slow), server_port, port(wrong), movie=True))
        responder(slow, info("Slow Legacy Fixture", delay=0.78))
        responder(full, info("Full Bot Fixture", clients=6, humans=0))
        responder(wrong, info("Wrong Protocol Fixture", protocol=25))
        server, client = evidence / "server", evidence / "client"
        server_exe, server_mod = stage(server, renderer, server=True)
        client_exe, client_mod = stage(client, renderer, compatibility=compatibility)
        fixture_menu(client_mod)
        (server_mod / "scripts").mkdir()
        (server_mod / "scripts/st_browser_fixture.bot").write_text(
            '{\nname "BrowserBot"\nmodel "kyle/default"\npersonality "botfiles/kyle.jkb"\n}\n', encoding="ascii")
        finish = "wait 950\nset ui_stMatchMaxPing 450\nwait 5\necho SERVER_BROWSER_COMPLETE\nquit\n"
        confirm = ("wait 45\nscreenshot_png password-request\npassword private-browser-fixture\n"
                   "ui_openmenu st_test_enter_password\n") if protected else finish
        (client_mod / "browser-confirm.cfg").write_text(confirm, encoding="ascii")
        (client_mod / "browser-finish.cfg").write_text(finish, encoding="ascii")
        disable = [f'set sv_master{i} ""' for i in range(1, 6)] + ['set cl_browserBackupMaster ""']
        server_lines = disable + (["set g_password private-browser-fixture"] if protected else []) + [
            'set sv_hostname "Fast Saber Trials Fixture"', 'set g_gametype 0',
            'set bot_enable 1', 'set st_combatMode 1', 'map mp/ffa3', 'wait 45', 'addbot BrowserBot 1',
        ]
        dedicated = runtime.launch(server, server_exe, server_mod, server_lines, server_port, renderer, True)
        stack.callback(stop, dedicated)
        wait_for(lambda: native_has_bot(server_port), "real bot excluded from advertised human count")
        client_lines = disable + [
            f'set sv_master1 127.0.0.1:{port(first)}', f'set sv_master2 127.0.0.1:{port(second)}',
            f'set sv_master3 127.0.0.1:{port(missing)}', 'set cl_maxPing 100',
            'set ui_netSource 1', 'set ui_stMatchMaxPing 1', 'set ui_stMatchHumans 1',
            'set name "ST Browser Smoke"', 'wait 60', 'ui_openmenu joinserver', 'wait 850',
            'screenshot_png worldwide', 'set ui_stServerSearch legacy', 'wait 20', 'screenshot_png search',
            'set ui_stServerSearch ""', 'wait 40', 'ui_openmenu st_test_find', 'wait 35', 'ui_stMatchMessage',
            'screenshot_png no-match', 'ui_openmenu st_test_clear', 'wait 20', 'ui_stMatchMessage',
            'screenshot_png quick-match', 'ui_openmenu st_test_join',
        ]
        game = runtime.launch(client, client_exe, client_mod, client_lines, server_port + 1, renderer)
        stack.callback(stop, game)
        if game.wait(timeout=55) != 0:
            raise RuntimeError("Candidate client exited with an error")
        output = runtime.log(client_mod)
        for expected in ("3 servers listed", "No joinable server matches these filters.",
                         "Recommended: Fast Saber Trials Fixture", "SERVER_BROWSER_COMPLETE"):
            if expected not in output:
                raise AssertionError((expected, client_mod / "qconsole.log"))
        if not re.search(r"ping time (?:7[5-9]\d|8\d\d)ms from", output):
            raise AssertionError("High-latency server did not produce a measured ping")
        server_log = runtime.log(server_mod)
        accepted = re.search(r'ClientConnect: (\d+) .*"ST Browser Smoke', server_log)
        if not accepted or f"ClientBegin: {accepted[1]}" not in server_log:
            raise AssertionError("The client did not enter the recommended dedicated server")
        if 'seta ui_stMatchMaxPing "450"' not in (client_mod / "openjk.cfg").read_text():
            raise AssertionError("The ping filter was not saved")
        screenshots = ["worldwide", "search", "no-match", "quick-match"]
        if protected:
            screenshots.append("password-request")
        for screenshot in screenshots:
            assert (client_mod / "screenshots" / f"{screenshot}.png").is_file(), screenshot
    access = "password-protected join" if protected else "open join"
    print(f"{renderer}: browser, missing master, overlapping lists, high ping, filters and {access} passed")


def players(bots, humans):
    return (b'0 0 "Bot"\n' * bots) + (b'1 150 "Human"\n' * humans)


def legacy_info(name, clients, statuses, requests, *, echo=True, ping_delay=0,
                status_delay=0, human_count=None, bot_count=None):
    short_reply = info(name, delay=ping_delay, clients=clients, humans=human_count,
                       bots=bot_count, capacity=32)

    def reply(query):
        if not query.startswith(PREFIX + b"getstatus "):
            return short_reply(query)
        requests.append(query)
        if not statuses:
            return None
        roster = statuses[min(len(requests) - 1, len(statuses) - 1)]
        challenge = query.split()[1]
        header = b"\\protocol\\26\\sv_maxclients\\32"
        if echo:
            header += b"\\challenge\\" + (challenge if echo is True else echo)
        time.sleep(status_delay)
        return PREFIX + b"statusResponse\n" + header + b"\n" + roster
    return reply


def population(renderer, compatibility):
    evidence = Path(mkdtemp(prefix="population-", dir=BUILD))
    print(evidence, flush=True)
    with ExitStack() as stack:
        listing, missing = udp(stack), udp(stack)
        cases = [
            ("Legacy bots only", 10, [players(10, 0)], {"echo": False}),
            ("Legacy mixed", 13, [players(10, 3), players(9, 4)], {"ping_delay": 0.8, "status_delay": 0.7}),
            ("Legacy humans only", 9, [players(0, 9)], {}),
            ("Empty", 0, [], {}),
            ("Advertised humans", 3, [], {"human_count": 2, "bot_count": 3}),
            ("Advertised bots", 13, [], {"human_count": "invalid", "bot_count": 12}),
            ("Status refused", 2, [], {}),
            ("Malformed roster", 2, [b'0 0 "Bot"\n0 invalid "Player"\n'], {}),
            ("Roster mismatch", 2, [players(0, 1)], {}),
            ("Wrong challenge", 2, [players(0, 2)], {"echo": b"stp-stale"}),
        ]
        requests = [[] for _ in cases]
        ports = [port(missing)]
        for (name, clients, statuses, options), queried in zip(cases, requests):
            sock = udp(stack)
            ports.append(port(sock))
            responder(sock, legacy_info(name, clients, statuses, queried, **options))
        responder(listing, master(*ports))

        exe, mod = stage(evidence, renderer, compatibility=compatibility)
        fixture_menu(mod)
        lines = [f'set sv_master{i} ""' for i in range(1, 6)] + [
            'set cl_browserBackupMaster ""', f'set sv_master1 127.0.0.1:{port(listing)}',
            'set ui_netSource 1', 'set ui_browserShowEmpty 1', 'wait 60',
            'ui_openmenu joinserver', 'wait 550', 'set ui_browserShowEmpty 0',
            'ui_openmenu st_test_population_refresh', 'wait 550', 'echo POPULATION_COMPLETE', 'quit',
        ]
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserved:
            reserved.bind(("127.0.0.1", 0))
            client_port = port(reserved)
        game = runtime.launch(evidence, exe, mod, lines, client_port, renderer)
        stack.callback(stop, game)
        if game.wait(timeout=55) != 0:
            raise RuntimeError("Candidate client exited with an error")
        output = runtime.log(mod)
        for expected in ("10 servers listed with 15 known human players.",
                         "8 servers listed with 16 known human players.", "POPULATION_COMPLETE"):
            if expected not in output:
                raise AssertionError((expected, mod / "qconsole.log"))
        for i, queries in enumerate(requests):
            refreshes = 0 if i in (3, 4, 5) else 2
            assert len(set(queries)) == refreshes, (cases[i][0], queries)
            # Each unresolved roster gets one retry with the original challenge.
            assert len(queries) == refreshes * (2 if i >= 6 else 1), (cases[i][0], queries)
    print(f"{renderer}: human-only, bot-only, mixed, empty, delayed, and unknown populations passed")


def stop(process):
    if process.poll() is None:
        process.terminate()
        process.wait(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("renderer", nargs="?", default="rd-vanilla", choices=("rd-vanilla", "rd-rend2"))
    parser.add_argument("--protected", action="store_true")
    parser.add_argument("--compat", action="store_true", help="Use the current Windows compatibility build")
    parser.add_argument("--population", action="store_true", help="Run legacy population and refresh fixtures")
    args = parser.parse_args()
    if args.population:
        population(args.renderer, args.compat)
    else:
        main(args.renderer, args.protected, args.compat)
