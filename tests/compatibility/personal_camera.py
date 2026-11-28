"""Verify camera changes in the rendered world while the editor is still open."""
import re
import shutil
import sys
import tempfile
from pathlib import Path

from personal_ui import click
from playback import ROOT, run, wheel_start
sys.path.insert(0,str(ROOT/"tools"))
from profile_png import read


def changed_pixels(first,second,region):
    w,h,a=read(first)
    ww,hh,b=read(second)
    assert (w,h)==(ww,hh)
    x1,y1,x2,y2=region
    points=[(x,y) for y in range(y1*h//480,y2*h//480,3) for x in range(x1*w//640,x2*w//640,3)]
    return sum(max(abs(u-v) for u,v in zip(a(x,y),b(x,y)))>20 for x,y in points)/len(points)


def check(game="japlus",exe=ROOT/"client/SaberTrials.x86_64.exe"):
    home=Path(tempfile.mkdtemp(prefix="camera-",dir=ROOT/"dist/compat/qa"))
    print(game,home,flush=True)
    mod=home/game
    mod.mkdir()
    shutil.copyfile(ROOT/"jampgamex86_64.dll",mod/"jampgamex86_64.dll")
    lines=wheel_start()+["set cg_thirdPerson 1","set cg_thirdPersonAngle 0","wait 90",
        "togglemenu","wait 12","ui_openmenu ingame_setup","wait 15"]
    lines+=click(551,129)+["wait 30","screenshot_png setup-before"]
    # Orbit slider on Camera, without pressing Apply.
    lines+=click(167,274)+["wait 45","screenshot_png setup-after","st_setupCameraPreview","cg_thirdPersonAngle",
        "st_emoteuiqa resume","wait 20","cg_draw2D","quit"]
    log=run(exe,home,game,lines)
    plain=re.sub(r"\^[0-9]","",log)
    assert re.search(r'Cvar st_setupCameraPreview = "[^"]*cg_thirdPersonAngle',plain),home
    assert 'Cvar cg_thirdPersonAngle = "0"' in plain
    assert 'Cvar cg_draw2D = "1"' in plain
    shots=mod/"screenshots"
    setup=changed_pixels(shots/"setup-before.png",shots/"setup-after.png",(300,185,620,400))
    assert setup>.10,setup
    print(f"Camera settings preview changed {setup:.0%} of world samples.",flush=True)


if __name__=="__main__":
    check(sys.argv[1] if len(sys.argv)>1 else "japlus")
