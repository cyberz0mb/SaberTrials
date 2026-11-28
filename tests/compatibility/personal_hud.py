"""Switch HUDs in the actual personal UI and compare both renderings."""
from pathlib import Path
import re
import shutil
import sys
import tempfile

from playback import ROOT, run, wheel_start
from personal_camera import changed_pixels
from personal_ui import click, tap


def check(game,renderer):
    home=Path(tempfile.mkdtemp(prefix="hud-",dir=ROOT/"dist/compat/qa"))
    print(game,renderer,home,flush=True)
    mod=home/game
    mod.mkdir()
    (home/"SaberTrials").mkdir()
    shutil.copyfile(ROOT/"jampgamex86_64.dll",mod/"jampgamex86_64.dll")
    lines=wheel_start()+["wait 70","st_personalHud","screenshot_png mod-before","wait 50","togglemenu","wait 15",
        "ui_openmenu ingame_setup","wait 15"]
    lines+=click(181,128)+tap("MWHEELDOWN")*9+["wait 6","screenshot_png style-menu"]
    lines+=click(245,315)+click(558,451)+["wait 5","st_personalHud","st_emoteuiqa resume","wait 35",
        "screenshot_png trials","wait 50","set cg_draw2D 0","wait 30","screenshot_png clean","wait 50","set cg_draw2D 1",
        "set st_personalHud 0","wait 30","screenshot_png mod-after","wait 90","quit"]
    log=run(ROOT/"client/SaberTrials.x86_64.exe",home,game,lines,renderer=renderer)
    plain=re.sub(r"\^[0-9]","",log)
    assert re.findall(r'Cvar st_personalHud = "(\d)"',plain)==["0","1"],home
    assert 'seta st_personalHud "1"' in (home/"SaberTrials/openjk.cfg").read_text()
    shots=mod/"screenshots"
    for region in [(4,414,192,472),(486,410,634,472),(508,379,635,408)]:
        changed=changed_pixels(shots/"trials.png",shots/"mod-before.png",region)
        restored=changed_pixels(shots/"mod-before.png",shots/"mod-after.png",region)
        hidden=changed_pixels(shots/"trials.png",shots/"clean.png",region)
        assert changed>.16 and restored<changed*.7 and hidden>.14,(region,changed,restored,hidden)
    print("HUD changed through Setup, both panels rendered, Clean Capture hid them and the mod HUD returned.",flush=True)


if __name__=="__main__":
    check(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else "rd-vanilla")
