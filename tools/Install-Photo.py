"""Install verified native Photo Mode and preserve the accepted interface."""
from pathlib import Path
import hashlib, json, shutil, tempfile, zipfile, sys

ROOT=Path(__file__).resolve().parent.parent
WORK=Path.home()/'AppData/Local/Temp/SaberTrials-photo-20261012'
BUILD=WORK/'build/Release'
STAGE=ROOT/'dist/photo-staging'
EVIDENCE=ROOT/'dist/verification/photo-20261012'
BACKUP=ROOT/'dist/backups/photo-20261012'
MANIFEST=ROOT/'dist/photo-install-manifest.json'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def package(files):
    paths={ROOT/rel for rel in files}
    for folder in ['development-source/client-overhaul','development-source/client-game',
                   'development-source/bot-roles/codemp/ui','development-source/bot-roles/codemp/game','development-source/bot-roles/patches',
                   'development-source/menu/photo-original']:
        paths.update(p for p in (ROOT/folder).rglob('*') if p.is_file())
    for name in ['LICENSE.txt','CREDITS.txt','docs/Photo-Mode.md','dist/photo-install-manifest.json',
                 'tools/Build-Photo.py','tools/Stage-Photo.py','tools/Test-Photo.py','tools/Install-Photo.py',
                 'tools/Build-Overhaul.py','tools/Test-Menu.py','tools/Test-Combat.py',
                 'tests/photo_client_qa.inc','tests/photo_engine_qa.inc','tests/menu_ui_qa.inc',
                 'tests/overhaul_ui_qa.inc','tests/overhaul_engine_qa.inc']:
        paths.add(ROOT/name)
    archive=ROOT/'dist/SaberTrials-photo-20261012.zip'
    upstream=WORK/'openjk.zip'
    assert digest(upstream)=='50dee49ccc3dc2b7a3333f6fb1cf50da976b40a38ba01d0971afe47d4ee5b52d'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(paths):z.write(path,'SaberTrials/'+path.relative_to(ROOT).as_posix())
        z.write(upstream,'SaberTrials/source/OpenJK-1a6a643427aa347553e9073dac5570b33337c4d9.zip',compress_type=zipfile.ZIP_STORED)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    archive.with_suffix('.zip.sha256').write_text(digest(archive)+'  '+archive.name+'\n')
    print('Packaged:',archive)

def install():
    build=json.loads((BUILD/'photo-build-manifest.json').read_text())
    assert build['kind']=='production'
    for name,sha in build['files'].items():assert digest(BUILD/name)==sha,name
    for name in build['files']:
        data=(BUILD/name).read_bytes()
        assert not any(x in data for x in [b'st_photoqa',b'st_clientqa',b'st_engineqa',b'PHOTO_QA']),name
    qa=json.loads((WORK/'build-qa/Release/photo-build-manifest.json').read_text())
    for mode,height in [('qa',720),('qa',1024),('production',720)]:
        report=json.loads((EVIDENCE/f'{mode}-1280x{height}.json').read_text())
        assert report['passed'] and report['files']['menu']==digest(STAGE/'ui/jamp/ingame.menu')
        manifest=qa if mode=='qa' else build
        for name in ['cgamex86_64.dll','uix86_64.dll']:assert report['files'][name]==manifest['files'][name]
        assert report['files']['engine']==manifest['files']['openjk.x86_64.exe']
        if mode=='qa' and height==1024:assert report['online'] and report['replay']
    files={'client/SaberTrials.x86_64.exe':BUILD/'openjk.x86_64.exe',
           'cgamex86_64.dll':BUILD/'cgamex86_64.dll','uix86_64.dll':BUILD/'uix86_64.dll',
           'ui/jamp/ingame.menu':STAGE/'ui/jamp/ingame.menu'}
    baseline=json.loads((STAGE/'baseline.json').read_text())
    for rel,sha in baseline.items():assert digest(ROOT/rel)==sha,'Changed since photo staging: '+rel
    unchanged={rel:sha for rel,sha in baseline.items() if rel not in files}
    BACKUP.mkdir(parents=True,exist_ok=True)
    assert not (BACKUP/'manifest.json').exists(),'Existing backup: do not overwrite'
    for rel in files:
        assert (ROOT/rel).resolve().is_relative_to(ROOT.resolve())
        saved=BACKUP/rel;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,saved)
    (BACKUP/'manifest.json').write_text(json.dumps({rel:digest(ROOT/rel) for rel in files},indent=2)+'\n')
    replaced=[]
    try:
        for rel,source in files.items():
            target=ROOT/rel;pending=target.with_name(target.name+'.photo-tmp')
            shutil.copy2(source,pending);pending.replace(target);replaced.append(rel)
            assert digest(target)==digest(source)
        assert unchanged=={rel:digest(ROOT/rel) for rel in unchanged}
    except Exception:
        for rel in reversed(replaced):shutil.copy2(BACKUP/rel,ROOT/rel)
        raise
    MANIFEST.write_text(json.dumps({'build':build,'files':{rel:digest(ROOT/rel) for rel in files},
        'unchanged':unchanged,'backup':str(BACKUP)},indent=2)+'\n')
    print('Installed Photo Mode; protected files unchanged:',len(unchanged))
    package(files)

if __name__=='__main__':
    if sys.argv[1:]==['--package-only']:
        files=json.loads(MANIFEST.read_text())['files']
        assert all(digest(ROOT/rel)==sha for rel,sha in files.items())
        package(files)
    else:install()
