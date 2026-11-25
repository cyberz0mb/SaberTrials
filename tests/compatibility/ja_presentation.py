"""Exercise the JA+ frontend, real renderer and Controls binding on a local map."""
import re
import shutil
import sys
import tempfile
from pathlib import Path

from ja_features import stage
from personal_ui import click, tap
from playback import ROOT, run, wheel_start
sys.path.insert(0,str(ROOT/"tools"))
from profile_png import read


def main(renderer):
    directory=Path(tempfile.mkdtemp(prefix="ja-presentation-",dir=ROOT/"dist/compat/qa"))
    print(renderer,directory,flush=True)
    exe=stage(directory)
    dll=renderer+"_x86_64.dll"
    shutil.copyfile(ROOT/"dist/compat/build/Release"/dll,exe.parent/dll)
    home=directory/"profile"
    mod=home/"japlus"
    mod.mkdir(parents=True)
    shutil.copyfile(ROOT/"jampgamex86_64.dll",mod/"jampgamex86_64.dll")
    lines=wheel_start()
    lines[lines.index("map mp/duel1")]="devmap t2_rancor"
    lines+=["noclip","setviewpos 64 -192 2048 90","wait 28","st_jaLight",
            "setviewpos -896 1348 1740 90","wait 30","st_jaLight",
            "set model bespin_cop/default","set cg_thirdperson 1","set cg_thirdpersonangle 180",
            "wait 90","screenshot_png character","wait 20","togglemenu","wait 12",
            "ui_openmenu ingame_saber","wait 12"]+click(570,92)
    lines+=["wait 15","screenshot_png crystals","wait 20","ui_openmenu ingame_player",
            "wait 14","st_emoteuiqa open","wait 20"]
    for index in range(39):
        lines += [f"st_emoteuiqa preview {index}","wait 2","st_emoteuiqa loop"]
    lines+=["st_emoteuiqa preview 1","wait 5","st_emoteuiqa loop","screenshot_png dance-a",
            "wait 17","st_emoteuiqa loop","screenshot_png dance-b","wait 15",
            "st_emoteuiqa close","ui_openmenu ingame_controls","wait 18"]
    # Movement, second page, fourth row, primary key.
    lines+=click(57,221)+click(577,412)+["screenshot_png movement","wait 5"]
    lines+=click(508,258)+tap("F7")+["wait 6"]+click(499,390)
    lines+=click(45,452)+["screenshot_png pending-controls","wait 5"]+click(472,392)
    lines+=["wait 6","bind F7","st_emoteuiqa resume","wait 15"]
    # Real keys append their bindings to the command buffer. Dispatch each
    # observation from a subsequent binding, just like separate OS key events.
    for key,name in [("F8","held"),("F9","released"),("F10","blocked")]:
        lines.append(f'bind {key} "exec qa-{name}.cfg"')
    lines+=["st_emoteinputqa F7 1","st_emoteinputqa F8 1"]
    (mod/"qa-held.cfg").write_text("wait 15\nst_jaStatus\nst_emoteinputqa F7 0\nst_emoteinputqa F9 1\n")
    (mod/"qa-released.cfg").write_text("wait 15\nst_jaStatus\nsets jp_allowHook 0\nwait 25\nst_emoteinputqa F7 1\nst_emoteinputqa F10 1\n")
    (mod/"qa-blocked.cfg").write_text("wait 15\nst_jaStatus\nst_emoteinputqa F7 0\nst_activeRenderer\nwait 5\nquit\n")
    log=run(exe,home,"japlus",lines,renderer=renderer)
    clean=re.sub(r"\^[0-9]","",log)
    assert f'Cvar st_activeRenderer = "{renderer}"' in clean and "Connected to a pure server." in clean
    reports=re.findall(r"JA\+ lighting .*? at ([\d .-]+): ambient ([\d .-]+), direct ([\d .-]+)",clean)
    assert len(reports)==2 and all(min(map(float,ambient.split()))>0 for _,ambient,_ in reports),reports
    for (position,_,_),expected in zip(reports,[(64,-192,2048),(-896,1348,1740)]):
        assert all(abs(float(v)-target)<40 for v,target in zip(position.split(),expected)),reports
    width,height,pixel=read(mod/"screenshots/crystals.png")
    blue,green,red=(pixel(x*width//640,y*height//480) for x,y in [(456,338),(501,338),(501,367)])
    assert blue[2]>blue[0]*1.5 and green[1]>green[0]*1.5 and red[0]>red[2]*1.5,(blue,green,red)
    assert len(re.findall(r"ST_EMOTE_UI_PREVIEW \d+ 1",clean))==40
    frames=re.findall(r"ST_EMOTE_UI_LOOP amdance 1 ([\d.]+)",clean)
    assert len(frames)>=2 and frames[-2]!=frames[-1],frames
    assert re.search(r'bind "F7" "\+st_jaGrapple"',(mod/"openjk.cfg").read_text(),re.I)
    assert re.findall(r"JA\+ client: active=1 rgb=1 hook button=(\d)",clean)==["1","0","0"]
    assert "Grapple input included in an outgoing packet this session: yes" in clean
    assert "Grapple is disabled on this JA+ server" in clean
    saved=run(exe,home,"japlus",["wait 20","bind F7","wait 5","quit"],renderer=renderer,safe=False)
    assert 'Bind F7 = "+st_jaGrapple"' in re.sub(r"\^[0-9]","",saved)
    print("Passed map lighting, crystal colors, 39 previews, Controls binding and outgoing grapple.",flush=True)


if __name__=="__main__":
    main(sys.argv[1])
