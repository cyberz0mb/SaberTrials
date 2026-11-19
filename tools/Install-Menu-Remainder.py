"""Install the remaining menus with a separate backup of the accepted release."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import zipfile

ROOT=Path(__file__).resolve().parent.parent
STAGE=ROOT/'dist/menu-remainder-staging'
BACKUP=ROOT/'dist/backups/menu-remainder-20261006'
MANIFEST=ROOT/'dist/menu-remainder-install-manifest.json'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def install():
    spec=importlib.util.spec_from_file_location('verify',ROOT/'tools/Test-Menu-Remainder.py')
    verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify);verify.structure()
    unchanged=['uix86_64.dll','jampgamex86_64.dll','cgamex86_64.dll','client/SaberTrials.x86_64.exe',
               'ui/jamp/main.menu','ui/jamp/ingame.menu','ui/jamp/multiplayer.menu']
    prior=json.loads((ROOT/'dist/menu-details-install-manifest.json').read_text())['files']
    unchanged+=list(prior)
    before={name:digest(ROOT/name) for name in unchanged}
    files=sorted(STAGE.rglob('*.menu'))
    assert {p.stem for p in files}==set(verify.skin.NAMES)
    BACKUP.mkdir(parents=True,exist_ok=True)
    record=BACKUP/'manifest.json'
    originals=json.loads(record.read_text()) if record.exists() else {}
    for p in files:
        rel=p.relative_to(STAGE).as_posix();target=ROOT/rel
        assert target.resolve().is_relative_to(ROOT.resolve())
        if rel not in originals:
            originals[rel]={'existed':target.exists(),'sha256':digest(target) if target.exists() else None}
            if target.exists():
                dest=BACKUP/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,dest)
    record.write_text(json.dumps(originals,indent=2)+'\n')
    installed={}
    for p in files:
        rel=p.relative_to(STAGE).as_posix();target=ROOT/rel
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        assert digest(p)==digest(target)
        installed[rel]=digest(target)
    assert before=={name:digest(ROOT/name) for name in unchanged}
    MANIFEST.write_text(json.dumps({'files':installed,'unchanged':before,'backup':str(BACKUP)},indent=2)+'\n')
    archive=ROOT/'dist/SaberTrials-remaining-menus-20261006.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for rel in installed:z.write(ROOT/rel,rel)
        for p in (ROOT/'ui/assets/sabertrials').glob('*.tga'):
            z.write(p,p.relative_to(ROOT).as_posix())
        for name in ['Theme-Menu-Remainder.py','Test-Menu-Remainder.py','Install-Menu-Remainder.py',
                     'Theme-Menu-Details.py','Test-Menu-Details.py','Test-Menu.py','Test-Combat.py']:
            p=ROOT/'tools'/name;z.write(p,p.relative_to(ROOT).as_posix())
        for p in verify.skin.SOURCE.glob('*'):z.write(p,p.relative_to(ROOT).as_posix())
        z.write(ROOT/'docs/Remaining-Menus.md','docs/Remaining-Menus.md')
        z.write(MANIFEST,MANIFEST.name)
    print(f'Installed {len(installed)} menus; accepted main/pause, earlier editors and binaries unchanged.')
    print('Backup:',BACKUP);print('Package:',archive)

if __name__=='__main__':install()
