"""Stage only the missing pause-menu hand selector, preserving existing bytes."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/handedness-ingame-staging'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    source=ROOT/'ui/jamp/ingame_saber.menu'
    control=ROOT/'development-source/handedness/ui/ingame_hand_control.inc'
    raw=source.read_bytes()
    if b'name st_ingame_hand' in raw:raise RuntimeError('In-game hand control already installed')
    end=raw.rfind(b'}');menu_end=raw.rfind(b'}',0,end)
    assert menu_end>=0 and not raw[menu_end+1:end].strip()
    assert b'"getsabercvars"' in raw and b'"updatesabercvars"' in raw
    result=raw[:menu_end]+b'\n'+control.read_bytes()+b'\n'+raw[menu_end:]
    target=OUT/'ui/jamp/ingame_saber.menu';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(result)
    (OUT/'manifest.json').write_text(json.dumps({'installed':False,
        'inputs':{p.relative_to(ROOT).as_posix():sha(p) for p in (source,control)},
        'files':{'ui/jamp/ingame_saber.menu':sha(target)}},indent=2)+'\n')
    print('Staged pause-menu hand selector:',target)

if __name__=='__main__':main()
