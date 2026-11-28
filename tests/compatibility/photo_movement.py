"""Check the Photo Mode boundary through the installed menu, bindings and console."""
from pathlib import Path
import re
import shutil
import sys
import tempfile

from personal_ui import click, tap
from playback import ROOT, run, wheel_start


def main(game, renderer):
    home = Path(tempfile.mkdtemp(prefix="photo-access-", dir=ROOT / "dist/compat/qa"))
    mod = home / game
    mod.mkdir()
    steps = wheel_start()
    native = game == "SaberTrials"
    if native:
        steps[0] = "set sv_pure 0"
    else:
        shutil.copyfile(ROOT / "jampgamex86_64.dll", mod / "jampgamex86_64.dll")
    steps += ['bind F10 "exec photo-finish.cfg"', "togglemenu", "wait 15"]
    if native:
        steps += ["ui_openmenu st_photo", "wait 15"] + click(210,373)
        steps += ["wait 30", "st_photoMode", "st_photoCapture", "wait 90", "st_photo", "wait 15", "st_photoMode"]
        finish=["wait 10","quit"]
    else:
        steps += click(120,272) + ["st_personalStatus", "ui_openmenu st_photo", "wait 5", "st_personalStatus",
            "st_emoteuiqa resume", "wait 8", "bind F7 st_photo", "bind F8 st_photoCapture"]
        steps += tap("F7") + tap("F8")
        finish=["st_photoSpectate", "set st_photoMode 1",
            "set st_photoFreeze 1", "wait 30", "st_photoMode", "st_photoFreeze", "cl_paused", "cg_draw2D","quit"]
    (mod/"photo-finish.cfg").write_text("\n".join(finish)+"\n")
    log = run(ROOT / "client/SaberTrials.x86_64.exe", home, game, steps + tap("F10"), renderer=renderer)
    log = re.sub(r"\^[0-9]", "", log)
    print(game, renderer, home, flush=True)
    assert "Going from CS_PRIMED to CS_ACTIVE" in log
    modes = re.findall(r'Cvar st_photoMode = "(\d)"', log)
    shots = list((mod / "screenshots").glob("*.png"))
    if native:
        assert modes == ["1", "0"] and len(shots) == 1 and shots[0].stat().st_size > 4096, (modes, shots)
    else:
        assert modes == ["0"] and not shots, (modes, shots)
        assert log.count("Requires a Saber Trials server.") >= 2
        assert log.count("PERSONAL_UI frontend=ingame\n") == 2
        assert log.count("Photo Mode requires a Saber Trials server.") == 2
        assert 'Cvar st_photoFreeze = "0"' in log and 'Cvar cl_paused = "0"' in log
        assert 'Cvar cg_draw2D = "1"' in log
    assert not re.search(r"clientCommand:[^\n]* : (?:team spectator|st_photo\w*)$", log, re.I|re.M)


if __name__ == "__main__":
    main(*sys.argv[1:])
