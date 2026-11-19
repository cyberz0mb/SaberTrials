"""Back up and install the production menu UI, preserving accepted combat binaries."""
from pathlib import Path
import hashlib
import json
import shutil
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parent.parent
WORK=Path(tempfile.gettempdir())/'SaberTrials-menu-20261006'
STAGE=ROOT/'dist/menu-staging'
BACKUP=ROOT/'dist/backups/menu-20261006'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    built=WORK/'build/Release'
    manifest=json.loads((built/'menu-build-manifest.json').read_text())
    dll=built/'uix86_64.dll'
    if manifest['kind']!='production' or sha(dll)!=manifest['files']['uix86_64.dll']:
        raise RuntimeError('Refusing a QA or unverified UI build')
    data=dll.read_bytes()
    if any(marker in data for marker in [b'st_clientqa',b'MENU_QA',b'QA item missing']):
        raise RuntimeError('Test hooks found in production UI')
    combat={name:sha(ROOT/name) for name in ['jampgamex86_64.dll','cgamex86_64.dll','client/SaberTrials.x86_64.exe']}
    sources={'uix86_64.dll':dll}
    sources.update({p.relative_to(STAGE).as_posix():p for p in STAGE.rglob('*') if p.is_file()})
    BACKUP.mkdir(parents=True,exist_ok=True)
    index=BACKUP/'menu-backup-manifest.json'
    original=json.loads(index.read_text()) if index.exists() else {}
    for name,source in sources.items():
        target=ROOT/name;backup=BACKUP/name
        if name not in original:
            if target.exists():
                backup.parent.mkdir(parents=True,exist_ok=True)
                if not backup.exists():shutil.copy2(target,backup)
                original[name]={'existed':True,'sha256':sha(backup)}
            else:original[name]={'existed':False}
    index.write_text(json.dumps(original,indent=2)+'\n')
    for name,source in sources.items():
        target=ROOT/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        if sha(target)!=sha(source):raise RuntimeError('Install checksum mismatch: '+name)
    for name,checksum in combat.items():
        if sha(ROOT/name)!=checksum:raise RuntimeError('Accepted gameplay/client binary changed: '+name)
    installed={'kind':'production','source_revision':manifest['source_revision'],
               'files':{name:sha(ROOT/name) for name in sources},'preserved_binaries':combat}
    (ROOT/'dist/menu-install-manifest.json').write_text(json.dumps(installed,indent=2)+'\n')
    package=ROOT/'dist/SaberTrials-menu-20261006.zip'
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
        for name in sources:z.write(ROOT/name,'SaberTrials/'+name)
        z.write(ROOT/'docs/Menu-Redesign.md','SaberTrials/docs/Menu-Redesign.md')
        z.write(ROOT/'dist/menu-install-manifest.json','SaberTrials/menu-install-manifest.json')
        for folder in ['development-source/client-overhaul','development-source/bot-roles/patches','development-source/menu']:
            for p in (ROOT/folder).rglob('*'):
                if p.is_file():z.write(p,'source/'+p.relative_to(ROOT).as_posix())
        z.write(ROOT/'development-source/bot-roles/codemp/ui/ui_sabertrials_menu.inc','source/development-source/bot-roles/codemp/ui/ui_sabertrials_menu.inc')
        for name in ['Build-Menu.py','Build-Overhaul.py','Generate-Menu.py']:
            z.write(ROOT/'tools'/name,'source/tools/'+name)
        z.write(ROOT/'ui/jamp/ingame_callvote.menu','source/ui/jamp/ingame_callvote.menu')
        for name in ['menu_ui_qa.inc','overhaul_ui_qa.inc','overhaul_engine_qa.inc']:
            z.write(ROOT/'tests'/name,'source/tests/'+name)
    print('Installed verified production UI and menus. Combat/client binaries unchanged.')
    print('Backup:',BACKUP)
    print('Package:',package)

if __name__=='__main__':main()
