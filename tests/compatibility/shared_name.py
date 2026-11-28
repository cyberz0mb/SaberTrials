"""Exercise name migration, mod config reloads, userinfo and client restarts."""
from pathlib import Path
import re
import shutil
import tempfile

from personal_ui import click
from playback import DATA, ROOT, run, wheel_start


def check_mod_switch(home,exe):
    # Use the real Setup > Mods action, which changes fs_game and restarts the filesystem.
    native=home/"SaberTrials"
    native.mkdir(parents=True)
    (native/"openjk.cfg").write_text('seta name "Starting name"\n')
    for mod in (p for p in DATA.iterdir() if p.is_dir() and p!=ROOT and any(p.glob("*.pk3"))):
        target=home/mod.name
        target.mkdir()
        (target/"openjk.cfg").write_text(
            'seta name "Old mod alias"\necho SHARED_NAME_MOD_LOADED\nname\nfs_game\nquit\n')
    steps=['name "^6Server Traveler"',"wait 45","ui_openmenu setup_menu","wait 30"]
    steps+=click(204,453)+["wait 12"]+click(280,220)+["wait 10"]+click(495,387)
    log=run(exe,home,"SaberTrials",steps,safe=False)
    assert "SHARED_NAME_MOD_LOADED" in log and 'Cvar ^7name = ^9"^7^6Server Traveler^9"' in log
    assert (native/"player-name.txt").read_text()=="^6Server Traveler"


def main():
    home=Path(tempfile.mkdtemp(prefix="shared-name-",dir=ROOT/"dist/compat/qa"))
    print(home,flush=True)
    exe=ROOT/"client/SaberTrials.x86_64.exe"
    names={"SaberTrials":"^2Trial Pilot","japlus":"Old JA Alias","base":"Old Base Alias"}
    for game in names:
        mod=home/game
        mod.mkdir()
        if game!="SaberTrials":
            shutil.copyfile(ROOT/"jampgamex86_64.dll",mod/"jampgamex86_64.dll")

    shared=home/"SaberTrials/player-name.txt"
    current=names["SaberTrials"]
    for game in ("SaberTrials","japlus","base","SaberTrials"):
        mod=home/game
        (mod/"openjk.cfg").write_text(f'seta name "{names[game]}"\nseta st_nameCfgProbe "{game}"\n')
        if shared.exists():
            (mod/"autoexec.cfg").write_text('exec old-auto-name.cfg\n')
            (mod/"old-auto-name.cfg").write_text(f'set name "Old autoexec alias"\nset st_autoNameProbe "{game}"\n')
        next_name="^5Orbit Pilot" if game=="japlus" else current
        steps=["name", "st_nameCfgProbe", "st_autoNameProbe"]
        if game=="japlus":
            steps+=wheel_start()+[f'name "{next_name}"',"wait 25","userinfo","wait 8"]
            # Replay a stale archived value, then issue a real rename from a bind.
            steps+=['exec openjk.cfg','wait 8','name','bind F8 "name ^3Pilot"',
                'bind F10 "exec name-finish.cfg"','st_emoteinputqa F8 1','st_emoteinputqa F8 0',
                'st_emoteinputqa F10 1','st_emoteinputqa F10 0']
            (mod/"name-finish.cfg").write_text("wait 8\nname\nquit\n")
        else:
            steps+=["name","quit"]
        run(exe,home,game,steps,safe=False)
        log=(mod/"qconsole.log").read_text(errors="replace")
        seen=re.findall(r'Cvar \^7name = \^9"\^7(.*?)\^9"',log)
        if game=="japlus":
            assert seen==[current,next_name,"^3Pilot"],seen
            assert any("clientCommand:" in line and "userinfo" in line and "\\name\\"+next_name in line
                       for line in log.splitlines()),home
            current="^3Pilot"
        else:
            assert seen==[current,current],seen
        assert f'Cvar st_nameCfgProbe = "{game}"' in re.sub(r'\^[0-9]','',log)
        if (mod/"autoexec.cfg").exists():
            assert f'Cvar st_autoNameProbe = "{game}"' in re.sub(r'\^[0-9]','',log)
        assert shared.read_text()==current
    print("Shared colored name survived the JA+ rename, archive reload and bind, then base and Saber Trials restarts.")
    check_mod_switch(home/'switch',exe)
    print("Switching mods through Setup loaded the destination config and kept the current player name.")


if __name__=="__main__":
    main()
