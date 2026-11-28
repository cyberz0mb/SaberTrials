"""Observe standard colors on an unmodified OpenJK peer on a loopback-only server."""
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time

from playback import ROOT, DATA, run


def check_messages(log):
    displayed = [line.split(" *", 1)[-1].lstrip("*") for line in log.splitlines()
                 if " *" in line or line.startswith("*")]
    for expected in ["^5PublicCyan","^5TeamCyan","^5PrivateCyan","^1ExplicitRed"]:
        assert any(expected in line for line in displayed), (expected, displayed[-20:])
    assert any(re.search(r"\^2DefaultBody",line) for line in displayed), displayed[-20:]


def replay(exe, home):
    # Record what the local server actually sent. Play the stream in a separate,
    # unmodified OpenJK client with its own configuration and stock renderer.
    game = home / "writer/base"
    game.mkdir(parents=True)
    shutil.copyfile(ROOT / "jampgamex86_64.dll", game / "jampgamex86_64.dll")
    lines = ['set sv_master1 ""', 'set name Sender', 'set sv_pure 1', 'set g_gametype 6',
             'set g_hybridStyles 0', 'set g_directionalFeints 0', 'set g_saberHandedness 0',
             'set g_stanceLibrary 0', 'set g_manualBlocking 0',
             'map mp/ctf1', 'wait 130', 'st_emoteuiqa resume', 'team red', 'wait 90',
             'record peer-colors', 'wait 90', 'set st_chatColor 5', 'say PublicCyan', 'wait 45',
             'say_team "TeamCyan"', 'wait 45', 'tell 0 "PrivateCyan"', 'wait 45',
             'say "^1ExplicitRed"', 'wait 45', 'set st_chatColor -1','say DefaultBody',
             'wait 360', 'stoprecord', 'quit']
    log = run(exe, home / "writer", "base", lines)
    assert "Saved recording:" in log or "Stopped demo" in log, log[-1800:]
    dest = home / "reader/base/demos/peer-colors.dm_26"
    dest.parent.mkdir(parents=True)
    shutil.copyfile(game / "demos/peer-colors.dm_26", dest)
    log = run(DATA / "openjk.x86_64.exe", home / "reader", "base",
              ["set cg_chatBox 90000", "demo peer-colors", "wait 340",
               "screenshot_png stock-peer-colors", "wait 340", "quit"])
    check_messages(log)
    assert (home / "reader/base/screenshots/stock-peer-colors.png").is_file()
    print("Stock OpenJK replayed the server's public, team and private colors.")


def port():
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1",0))
        return s.getsockname()[1]


def start(exe,home,settings,commands):
    base=home/"base"
    base.mkdir(parents=True)
    (base/"peer.cfg").write_text("\n".join(commands)+"\n")
    options=dict(fs_basepath=DATA,fs_homepath=home,fs_game="",developer=1,logfile=2,
                 net_ip="127.0.0.1",net_enabled=1,net_port=port(),cl_allowDownload=0,
                 com_introplayed=1,r_fullscreen=0,r_mode=3,com_maxfps=60, s_initsound=0)
    options.update(settings)
    args=[str(exe),"+safe"]
    for key,value in options.items(): args.extend(["+set",key,str(value)])
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW
    return subprocess.Popen(args+["+exec","peer.cfg"],cwd=exe.parent,startupinfo=startup,
        env={**os.environ,"LOCALAPPDATA":str(home/"local")},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


def wait(home,marker,process):
    log=home/"base/qconsole.log"
    until=time.monotonic()+65
    while time.monotonic()<until:
        data=log.read_text(errors="replace") if log.exists() else ""
        if marker in data:return data
        if process.poll() is not None:break
        time.sleep(.2)
    raise RuntimeError(f"Missing {marker} in {log}\n{data[-1200:]}")


def main():
    home=Path(tempfile.mkdtemp(dir=ROOT/"dist/compat/qa"))
    print(home,flush=True)
    if "--replay" in sys.argv:
        args = [a for a in sys.argv[1:] if a != "--replay"]
        return replay(Path(args[0]).resolve() if args else ROOT/"client/SaberTrials.x86_64.exe", home)
    processes=[]
    try:
        server_port=port()
        server=start(DATA/"openjkded.x86_64.exe",home/"server",dict(net_port=server_port,dedicated=1,sv_pure=1,
            sv_master1="",sv_allowDownload=0,sv_maxclients=4,g_gametype=6),
            ["map mp/ctf1","echo ST_LOCAL_SERVER"])
        processes.append(server);wait(home/"server","ST_LOCAL_SERVER",server)
        connect=f"connect 127.0.0.1:{server_port}"
        reader=start(DATA/"openjk.x86_64.exe",home/"reader",dict(name="Reader",cg_chatBox=90000),
            [connect,"wait 240","team red","wait 45","echo ST_READER_READY"])
        processes.append(reader);wait(home/"reader","Going from CS_PRIMED to CS_ACTIVE",reader)
        wait(home/"reader","ST_READER_READY",reader)
        sender=start(Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/"client/SaberTrials.x86_64.exe",home/"sender",dict(name="Sender",st_chatColor=5),
            [connect,"wait 240","team red","wait 45","say PublicCyan","wait 35","say_team TeamCyan",
             "wait 35",'tell 0 "PrivateCyan"',"wait 35",'say "^1ExplicitRed"',"wait 35",
             "set st_chatColor -1","say DefaultBody","wait 25","quit"])
        processes.append(sender)
        data=wait(home/"reader","DefaultBody",reader)
        check_messages(data)
        print("Stock OpenJK received cyan in public, team and private chat, explicit red and the server default.")
    finally:
        for p in reversed(processes):
            if p.poll() is None:p.terminate()
            p.wait(timeout=10)


if __name__=="__main__":
    main()
