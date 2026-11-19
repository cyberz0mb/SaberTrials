"""Install only verified production hud files, with backup and rollback."""
from pathlib import Path
import hashlib, json, shutil, tempfile, zipfile
ROOT=Path(__file__).resolve().parent.parent
BUILD=Path(tempfile.gettempdir())/'SaberTrials-hud-20261006/build/Release'
STAGE=ROOT/'dist/hud-staging'
BACKUP=ROOT/'dist/backups/hud-20261006'
MANIFEST=ROOT/'dist/hud-install-manifest.json'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    build=json.loads((BUILD/'hud-build-manifest.json').read_text())
    assert build['kind']=='production','QA build cannot be installed'
    files={}
    for name,sha in build['files'].items():
        assert name in ['cgamex86_64.dll','uix86_64.dll']
        p=BUILD/name;assert digest(p)==sha
        assert not any(marker in p.read_bytes() for marker in [b'st_hudqa',b'HUD_QA',b'st_portraitqa',b'PORTRAIT_QA',b'st_clientqa',b'MENU_QA',b'st_predictionqa'])
        files[name]=p
    assert len(files)==2
    files.update({p.relative_to(STAGE).as_posix():p for p in STAGE.rglob('*') if p.is_file()})
    unchanged={name:digest(ROOT/name) for name in ['jampgamex86_64.dll','client/SaberTrials.x86_64.exe',
        'ui/jamp/main.menu','ui/jamp/ingame.menu','ui/jamp/multiplayer.menu',
        'models/players/jawa/st_portrait.cfg','models/players/luffy/st_portrait.cfg']}
    BACKUP.mkdir(parents=True,exist_ok=True)
    record=BACKUP/'manifest.json';originals=json.loads(record.read_text()) if record.exists() else {}
    for rel in files:
        target=ROOT/rel;assert target.resolve().is_relative_to(ROOT.resolve())
        if rel not in originals:
            originals[rel]={'existed':target.exists(),'sha256':digest(target) if target.exists() else None}
            if target.exists():
                p=BACKUP/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,p)
    record.write_text(json.dumps(originals,indent=2)+'\n')
    with tempfile.TemporaryDirectory(prefix='hud-install-') as temp:
        previous=Path(temp);replaced=[]
        for rel in files:
            target=ROOT/rel
            if target.exists():
                p=previous/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,p)
        try:
            for rel,source in files.items():
                target=ROOT/rel;target.parent.mkdir(parents=True,exist_ok=True)
                staged=target.with_name(target.name+'.hud-tmp');shutil.copy2(source,staged)
                staged.replace(target);replaced.append(rel);assert digest(source)==digest(target)
        except Exception:
            for rel in reversed(replaced):
                p=previous/rel
                if p.exists():shutil.copy2(p,ROOT/rel)
                else:(ROOT/rel).unlink()
            raise
    assert unchanged=={name:digest(ROOT/name) for name in unchanged}
    MANIFEST.write_text(json.dumps({'build':build,'files':{rel:digest(ROOT/rel) for rel in files},
        'unchanged':unchanged,'backup':str(BACKUP)},indent=2)+'\n')
    print('Installed production HUD; backup:',BACKUP)
    package(files)

def package(files):
    paths=set(ROOT/rel for rel in files)
    paths.update(ROOT/p for p in ['LICENSE.txt','CREDITS.txt','docs/HUD.md','docs/Head-Portrait.md',
        'tools/Build-Hud.py','tools/Build-Overhaul.py','tools/Generate-Hud.py',
        'tools/Install-Hud.py','tools/Test-Hud.py','tools/Test-Portrait.py','tools/Test-Menu.py','tools/Test-Combat.py',
        'tools/Theme-Menu-Details.py','tests/hud_client_qa.inc','tests/portrait_client_qa.inc','tests/menu_ui_qa.inc',
        'tests/overhaul_ui_qa.inc','tests/overhaul_engine_qa.inc','dist/hud-install-manifest.json'])
    for directory in ['development-source/client-game','development-source/bot-roles/codemp',
        'development-source/bot-roles/patches','development-source/client-overhaul/patches',
        'development-source/menu/hud-original','development-source/menu/portrait-profiles']:
        paths.update(p for p in (ROOT/directory).rglob('*') if p.is_file())
    package=ROOT/'dist/SaberTrials-hud-20261006.zip'
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(paths):z.write(p,'SaberTrials/'+p.relative_to(ROOT).as_posix())
    package.with_suffix('.zip.sha256').write_text(digest(package)+'  '+package.name+'\n')
    print('Package:',package)

if __name__=='__main__':
    import sys
    if sys.argv[1:] == ['--package-only']:
        files=json.loads(MANIFEST.read_text())['files']
        assert all(digest(ROOT/rel)==sha for rel,sha in files.items())
        package(files)
    else:main()
