"""Exercise JA+ client input, saved saber colors and game switching on local fixtures."""
from pathlib import Path
import re
import shutil
import tempfile

from playback import ROOT, run, wheel_start
from personal_ui import click


def stage(directory):
    binary=directory/"bin"
    binary.mkdir()
    exe=binary/"SaberTrials.x86_64.exe"
    releases=ROOT/"dist/compat"
    shutil.copyfile(releases/"build/Release/openjk.x86_64.exe",exe)
    shutil.copyfile(releases/"ui-build/Release/uix86_64.dll",binary/"SaberTrialsUI.x86_64.dll")
    (binary/"ja-compat").mkdir()
    shutil.copyfile(releases/"ja-build/Release/cgamex86_64.dll",binary/"ja-compat/cgamex86_64.dll")
    for name in ("SDL2.dll","OpenAL32.dll","rd-vanilla_x86_64.dll"):
        shutil.copyfile(ROOT/"client"/name,binary/name)
    return exe


def test(exe,home,game):
    mod=home/game
    mod.mkdir(parents=True)
    shutil.copyfile(ROOT/"jampgamex86_64.dll",mod/"jampgamex86_64.dll")
    # Key events append commands to the normal engine queue. End each input
    # phase before observing it so the binding actually runs on its frame.
    bootstrap=wheel_start()+["bind F7 +st_jaGrapple",'bind F8 "exec ja-down.cfg"',
        'bind F9 "exec ja-up.cfg"',"st_emoteinputqa F7 1","st_emoteinputqa F8 1"]
    if game=="SaberTrials":
        # The installed development game includes loose assets. Use its normal
        # non-pure regression setup. The other fixtures exercise pure checks.
        bootstrap[bootstrap.index("set sv_pure 1")]="set sv_pure 0"
    (mod/"ja-down.cfg").write_text("wait 12\nst_jaStatus\nst_emoteinputqa F7 0\nst_emoteinputqa F9 1\n")
    lines=["wait 10","st_jaStatus",
        "st_jaJetpack","wait 10","st_jaFullForceDuel","wait 10"]
    if game=="japlus":
        lines+=["togglemenu","wait 10","ui_openmenu ingame_saber","wait 12"]
        lines+=click(144,92)+click(570,92)+click(520,199)+click(477,238)+click(568,279)
        lines+=click(513,403)+click(564,118)+click(466,199)+click(598,238)+click(494,279)
        lines+=["screenshot_png ja-dual-crystals"]+click(565,447)+["wait 35","st_jaStatus",
            "sets jp_allowRGBsaber 0","wait 45","st_jaStatus"]
    else:
        lines+=["set st_jaRGB1 16711935","set st_jaRGB2 255","set st_jaStyle1 7",
                "set name ScopeTest","wait 35","st_jaStatus"]
    lines+=["disconnect","wait 18","st_jaStatus","st_jaJetpack","quit"]
    (mod/"ja-up.cfg").write_text("\n".join(lines)+"\n")
    run(exe,home,game,bootstrap)
    log=(mod/"qconsole.log").read_text(errors="replace")
    assert "Going from CS_PRIMED to CS_ACTIVE" in log
    if game!="SaberTrials":
        assert "Connected to a pure server." in log
    states=re.findall(r"JA\+ client: active=(\d) rgb=(\d) hook button=(\d)",log)
    commands=re.findall(r"clientCommand:[^\n]*? : \d+ : ([^\r\n]+)",log)
    if game=="japlus":
        assert states==[("1","1","1"),("1","1","0"),("1","1","0"),("1","0","0"),("0","0","0")],states
        assert "Saber Trials JA+ client renderer loaded." in log
        assert commands.count("jetpack")==commands.count("engage_FullForceDuel")==1,commands
        selections=re.findall(r"JA\+ saber choices: (-?\d+)/(\d+) and (-?\d+)/(\d+)",log)
        rgb1,style1,rgb2,style2=map(int,selections[-1])
        assert rgb1>0 and rgb2>0 and rgb1!=rgb2 and (style1,style2)==(7,6),selections
        final=next(c for c in reversed(commands) if c.startswith("userinfo") and "cp_sbRGB1" in c)
        assert "cp_sbRGB" not in next(c for c in reversed(commands) if c.startswith("userinfo"))
        fields=final.split('"')[1].strip('\\').split('\\')
        info=dict(zip(fields[::2],fields[1::2]))
        for slot,rgb,style in [(1,rgb1,style1),(2,rgb2,style2)]:
            assert int(info[f"cp_sbRGB{slot}"])==int.from_bytes(rgb.to_bytes(3,"big"),"little"),info
            assert int(info[f"color{slot}"])==style
        assert (mod/"screenshots/ja-dual-crystals.png").is_file()
    else:
        assert states==[("0","0","0")]*4,states
        assert "Saber Trials JA+ client renderer loaded." not in log
        assert all(c not in ("jetpack","engage_FullForceDuel") and "cp_sbRGB" not in c for c in commands)


if __name__=="__main__":
    directory=Path(tempfile.mkdtemp(dir=ROOT/"dist/compat/qa"))
    print(directory,flush=True)
    exe=stage(directory)
    for game in ("japlus","base","SaberTrials"):
        test(exe,directory/"home",game)
    print("Passed dual saber UI and wire colors, held/released grapple, jetpack, duel and isolation on base JKA, Saber Trials and disconnect.")
