"""Exercise the release client over IPv4 with a private loopback dedicated server."""
from contextlib import ExitStack
from importlib import import_module
from pathlib import Path
from tempfile import mkdtemp
import heapq
import re
import shutil
import socket
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "dist/net"
sys.path.insert(0, str(ROOT / "tools"))
runtime = import_module("Check-Emotes")


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def relay(sock, server, impaired, done):
    """Fixed 60 ms each way. During the trial, discard every fifth incoming message."""
    client = None
    queue = []
    count = serial = 0
    sock.settimeout(0.003)
    while not done.is_set():
        try:
            packet, sender = sock.recvfrom(65535)
            if sender == server:
                dest = client
                count += 1
                if impaired.is_set() and count % 5 == 0:
                    continue
            else:
                client = sender
                dest = server
            serial += 1
            if dest:
                heapq.heappush(queue, (time.monotonic() + .060, serial, dest, packet))
        except TimeoutError:
            pass
        while queue and queue[0][0] <= time.monotonic():
            _, _, dest, packet = heapq.heappop(queue)
            sock.sendto(packet, dest)


def stop(process):
    if process.poll() is None:
        process.terminate()
    process.wait(timeout=10)


def wait_for(process, mod, pattern, timeout):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        log = runtime.log(mod)
        match = re.search(pattern, log)
        if match:
            return match
        if process.poll() is not None:
            break
        time.sleep(.15)
    raise RuntimeError(f"Missing {pattern!r} in {mod / 'qconsole.log'}")


def main():
    directory = Path(mkdtemp(prefix="runtime-", dir=OUT))
    print(directory, flush=True)
    with ExitStack() as stack:
        sock = stack.enter_context(socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
        sock.bind(("127.0.0.1", 0))
        server_port = free_port()
        impaired, done = threading.Event(), threading.Event()
        thread = threading.Thread(target=relay, args=(sock, ("127.0.0.1", server_port), impaired, done))
        thread.start()
        stack.callback(thread.join)
        stack.callback(done.set)

        server, client = directory / "server", directory / "client"
        renderer = "rd-vanilla"
        ded, smod = runtime.stage(server, renderer, installed=True, server=True, use_pack=False)
        disable = [f'set sv_master{n} ""' for n in range(1, 6)]
        server_lines = disable + ["net_restart", "net_port", "set sv_fps 20", "set sv_maxRate 32000", "map mp/duel1"]
        dedicated = runtime.launch(server, ded, smod, server_lines, server_port, renderer, True)
        stack.callback(stop, dedicated)
        wait_for(dedicated, smod, r"(?i)InitGame:", 45)
        _, mod = runtime.stage(client, renderer, installed=True, use_pack=False)
        exe = client / "bin/SaberTrials.x86_64.exe"
        shutil.copyfile(OUT / "b-engine/Release/openjk.x86_64.exe", exe)
        shutil.copyfile(OUT / "b-frontend/Release/uix86_64.dll", mod / "uix86_64.dll")
        shutil.copyfile(OUT / "b-frontend/Release/cgamex86_64.dll", mod / "cgamex86_64.dll")
        poll = mod / "net-poll.cfg"
        def commands(lines):
            temp = poll.with_suffix(".tmp")
            temp.write_text("\n".join(lines) + "\n", encoding="ascii")
            temp.replace(poll)
        commands(["st_netStatus", "wait 18", "exec net-poll.cfg"])
        lines = disable + [
            "net_restart", "net_port", "set cl_motd 0", "set cl_lanForcePackets 0", "set com_maxfps 60", "set rate 29000", "set snaps 17",
            "set cl_maxpackets 42", "set cl_timeNudge -11", "set cl_packetdup 3",
            "set st_netStats 1", 'set activeAction "exec net-poll.cfg"',
            f"connect 127.0.0.1:{sock.getsockname()[1]}"]
        player = runtime.launch(client, exe, mod, lines, free_port(), renderer)
        stack.callback(stop, player)
        wait_for(player, mod, r"Auto \(trial\).*\n[^\n]*Nudge \d+  MaxPPS \d+  Snaps req 20  Rate req 32000", 90)
        commands(["st_netStatus", "writeconfig during-auto.cfg", "wait 18", "exec net-poll.cfg"])
        wait_for(player, mod, "Writing during-auto.cfg", 6)
        impaired.set()
        wait_for(player, mod, r"Auto \(restored\).*\n[^\n]*Nudge 0  MaxPPS \d+  Snaps req 20  Rate req 32000  Dup 3", 26)
        commands(["set st_netMode 1", "wait 3", "st_netStatus", "set cl_maxpackets 55",
                  "set st_netMode 0", "wait 3", "st_netStatus", "disconnect", "wait 3", "quit"])
        if player.wait(timeout=15):
            raise RuntimeError("Client exited with an error")
        log = runtime.log(mod)
        assert re.search(r"Manual .*\n[^\n]*Nudge -11  MaxPPS 42", log), "Manual failed to restore timing"
        assert re.search(r"Off .*\n[^\n]*Nudge -11  MaxPPS 55", log), "Off lost a manual edit"
        config = (mod / "during-auto.cfg").read_text()
        for name, value in (("rate", 29000), ("snaps", 17), ("cl_maxpackets", 42), ("cl_packetdup", 3)):
            assert f'seta {name} "{value}"' in config, name
        assert "Too many info changes" not in log
        print("Passed UDP join, advertised limits, rollback, Manual/Off and writeconfig.", flush=True)


if __name__ == "__main__":
    main()
