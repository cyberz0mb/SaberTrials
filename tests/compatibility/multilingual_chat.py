"""Run automatic incoming translation through both installed Windows chat paths."""
import re
import shutil
import tempfile
from pathlib import Path

from playback import ROOT, run, wheel_start


def check(game):
    home=Path(tempfile.mkdtemp(prefix="multilingual-",dir=ROOT/"dist/compat/qa"))
    mod=home/game
    mod.mkdir()
    native=game=="SaberTrials"
    if not native:
        shutil.copyfile(ROOT/"jampgamex86_64.dll",mod/"jampgamex86_64.dll")
    start=wheel_start()
    if native:
        start[0]="set sv_pure 0"
    status="st_translatorinfo" if native else "st_personalStatus"
    lines=["set cg_chatBox 30000","set st_translate 1","set st_translateSource 0"]
    for target,message in [(1,"hola amigos"),(1,"bonjour"),(9,"Привет друзья")]:
        lines += [f"set st_translateTarget {target}","wait 20",f'say "{message}"',"wait 780",status]
    (mod/"messages.cfg").write_text("\n".join(lines)+"\n",encoding="utf8")
    log=run(ROOT/"client/SaberTrials.x86_64.exe",home,game,start+["exec messages.cfg","wait 15","quit"])
    prefix=r"ST_TRANSLATOR enabled=1 source=0 target=\d+" if native else r"PERSONAL_UI chat=\d+"
    counts=[int(n) for n in re.findall(prefix+r" translated=(\d+)",log)]
    assert counts==[1,2,3],(home,counts)
    print(game,"passed Spanish and French to English, then Russian to French",flush=True)


if __name__=="__main__":
    for game in ("SaberTrials","japlus"):
        check(game)
