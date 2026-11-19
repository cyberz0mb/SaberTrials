"""Back up and install only the verified menu/art refinement."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parent.parent
STAGE=ROOT/'dist/menu-soft-staging'
BACKUP=ROOT/'dist/backups/menu-soft-20261011'
MANIFEST=ROOT/'dist/menu-soft-install-manifest.json'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def package(files):
    paths={ROOT/rel for rel in files}
    paths.update(ROOT/p for p in ['LICENSE.txt','CREDITS.txt','docs/Soft-Menu-Style.md',
        'tools/Soften-Menus.py','tools/Install-Soft-Menus.py','tools/Test-Soft-Menus.py',
        'tools/Theme-Menu-Details.py','tools/Theme-Menu-Remainder.py','tools/Test-Menu-Details.py',
        'tools/Test-Menu-Remainder.py','tools/Test-Interface.py','tools/Test-Menu.py',
        'tools/Test-Portrait.py','tools/Test-Combat.py','dist/menu-soft-install-manifest.json'])
    paths.update(p for p in (ROOT/'development-source/menu/soft-original').rglob('*') if p.is_file())
    archive=ROOT/'dist/SaberTrials-menu-soft-20261011.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(paths):z.write(p,'SaberTrials/'+p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    archive.with_suffix('.zip.sha256').write_text(digest(archive)+'  '+archive.name+'\n')
    print('Packaged:',archive,flush=True)

def install():
    files={p.relative_to(STAGE).as_posix():p for p in STAGE.rglob('*') if p.is_file()}
    assert len(files)==47 and all(p.startswith('ui/') for p in files)
    for name,marker in [('detail','PASS: 41 native navigation/input checkpoints'),
                        ('wide','PASS all Rules pages'),('production','PASS production native rendering')]:
        log=(ROOT/f'dist/menu-soft-{name}.log').read_text()
        assert marker in log and 'Traceback' not in log,(name,log[-1500:])
    evidence=json.loads((ROOT/'dist/verification/menu-soft-20261011/structure.json').read_text())
    assert evidence['preserved_semantics_and_hitboxes'] and evidence['menus']==42
    # Confirm the accepted checkpoint and immutable menu snapshots before writes.
    checkpoint=json.loads((ROOT/'dist/interface-install-manifest.json').read_text())
    expected={**checkpoint['unchanged'],**checkpoint['files']}
    for p in (ROOT/'development-source/menu/soft-original').glob('*.menu'):
        expected['ui/jamp/'+p.name]=digest(p)
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
    with tempfile.TemporaryDirectory(prefix='st-soft-install-') as temp:
        previous=Path(temp);replaced=[]
        for rel in files:
            if (ROOT/rel).exists():
                p=previous/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
        try:
            for rel,source in files.items():
                target=ROOT/rel;target.parent.mkdir(parents=True,exist_ok=True)
                pending=target.with_name(target.name+'.soft-tmp');shutil.copy2(source,pending)
                pending.replace(target);replaced.append(rel)
                assert digest(target)==digest(source)
            assert unchanged=={rel:digest(ROOT/rel) for rel in unchanged}
        except Exception:
            for rel in reversed(replaced):
                if (previous/rel).exists():shutil.copy2(previous/rel,ROOT/rel)
                else:(ROOT/rel).unlink()
            raise
    MANIFEST.write_text(json.dumps({'files':{rel:digest(ROOT/rel) for rel in files},
        'unchanged':unchanged,'backup':str(BACKUP),'type':'menu and art only'},indent=2)+'\n')
    print('Installed',len(files),'files; protected',len(unchanged),'unchanged files. Backup:',BACKUP,flush=True)
    package(files)

if __name__=='__main__':
    raise SystemExit('Retired: the user rejected broad menu fading. Use Fade-Side-Menus.py for the side-menu-only update.')
    if sys.argv[1:]==['--package-only']:
        files=json.loads(MANIFEST.read_text())['files']
        assert all(digest(ROOT/rel)==sha for rel,sha in files.items());package(files)
    else:install()
