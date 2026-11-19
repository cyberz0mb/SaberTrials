"""Install the verified UI refinement, preserving gameplay and user settings."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parent.parent
BUILD=Path(tempfile.gettempdir())/'SaberTrials-interface-20261011/build/Release'
STAGE=ROOT/'dist/interface-staging'
BACKUP=ROOT/'dist/backups/interface-20261011'
MANIFEST=ROOT/'dist/interface-install-manifest.json'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def package(files):
    paths={ROOT/rel for rel in files}
    paths.update(ROOT/p for p in ['LICENSE.txt','CREDITS.txt','docs/Interface-Refinement.md',
        'docs/HUD.md','docs/Head-Portrait.md','tools/Refine-Interface.py','tools/Build-Interface.py',
        'tools/Install-Interface.py','tools/Test-Interface.py','tools/Build-Menu.py',
        'tools/Build-Overhaul.py','tools/Generate-Menu.py','tools/Theme-Menu-Details.py',
        'tools/Test-Menu.py','tools/Test-Portrait.py','tools/Test-Combat.py',
        'tests/menu_ui_qa.inc','tests/overhaul_ui_qa.inc','tests/overhaul_engine_qa.inc',
        'dist/interface-install-manifest.json'])
    for directory in ['development-source/bot-roles/codemp/ui',
        'development-source/bot-roles/patches','development-source/client-overhaul/patches',
        'development-source/menu/interface-original']:
        paths.update(p for p in (ROOT/directory).rglob('*') if p.is_file())
    archive=ROOT/'dist/SaberTrials-interface-20261011.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(paths):z.write(p,'SaberTrials/'+p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    archive.with_suffix('.zip.sha256').write_text(digest(archive)+'  '+archive.name+'\n')
    print('Packaged:',archive)

def install():
    build=json.loads((BUILD/'menu-build-manifest.json').read_text())
    assert build['kind']=='production'
    assert set(build['files'])=={'uix86_64.dll'}
    ui=BUILD/'uix86_64.dll';assert digest(ui)==build['files'][ui.name]
    assert not any(marker in ui.read_bytes() for marker in [b'st_clientqa',b'MENU_QA',b'st_hudqa',b'st_portraitqa'])
    for size in ['1280x1024','1280x720']:
        log=(ROOT/f'dist/interface-qa-{size}.log').read_text()
        assert 'PASS compact pause actions' in log and 'PASS main Setup category' in log
    assert 'PASS production menu rendering' in (ROOT/'dist/interface-production-1280x720.log').read_text()
    files={'uix86_64.dll':ui}
    files.update({p.relative_to(STAGE).as_posix():p for p in STAGE.rglob('*') if p.is_file()})
    assert len(files)==8
    # Detect external edits since the accepted HUD checkpoint before any writes.
    baseline=json.loads((ROOT/'dist/hud-install-manifest.json').read_text())
    expected={**baseline['files'],**baseline['unchanged']}
    if MANIFEST.exists():expected.update(json.loads(MANIFEST.read_text())['files'])
    for rel,sha in expected.items():assert digest(ROOT/rel)==sha,'Changed since checkpoint: '+rel
    unchanged={rel:digest(ROOT/rel) for rel in expected if rel not in files}
    for p in ROOT.glob('*.cfg'):unchanged[p.relative_to(ROOT).as_posix()]=digest(p)
    BACKUP.mkdir(parents=True,exist_ok=True)
    record=BACKUP/'manifest.json'
    originals=json.loads(record.read_text()) if record.exists() else {}
    for rel in files:
        target=ROOT/rel;assert target.resolve().is_relative_to(ROOT.resolve())
        if rel not in originals:
            originals[rel]={'existed':target.exists(),'sha256':digest(target) if target.exists() else None}
            if target.exists():
                saved=BACKUP/rel;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
    record.write_text(json.dumps(originals,indent=2)+'\n')
    with tempfile.TemporaryDirectory(prefix='st-interface-install-') as temp:
        previous=Path(temp);replaced=[]
        for rel in files:
            if (ROOT/rel).exists():
                saved=previous/rel;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,saved)
        try:
            for rel,source in files.items():
                target=ROOT/rel;target.parent.mkdir(parents=True,exist_ok=True)
                pending=target.with_name(target.name+'.interface-tmp');shutil.copy2(source,pending)
                pending.replace(target);replaced.append(rel)
                assert digest(target)==digest(source)
            assert unchanged=={rel:digest(ROOT/rel) for rel in unchanged}
        except Exception:
            for rel in reversed(replaced):
                if (previous/rel).exists():shutil.copy2(previous/rel,ROOT/rel)
                else:(ROOT/rel).unlink()
            raise
    MANIFEST.write_text(json.dumps({'build':build,'files':{rel:digest(ROOT/rel) for rel in files},
        'unchanged':unchanged,'backup':str(BACKUP)},indent=2)+'\n')
    print('Installed eight UI files with backup:',BACKUP)
    package(files)

if __name__=='__main__':
    if sys.argv[1:]==['--package-only']:
        files=json.loads(MANIFEST.read_text())['files']
        assert all(digest(ROOT/rel)==sha for rel,sha in files.items())
        package(files)
    else:install()
