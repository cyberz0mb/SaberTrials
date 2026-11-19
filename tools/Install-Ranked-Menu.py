"""Install only the verified Ranked menu page family and package its source."""
from pathlib import Path
import hashlib,json,shutil,zipfile,sys
ROOT=Path(__file__).resolve().parent.parent
STAGE=ROOT/'dist/ranked-menu-staging'
BACKUP=ROOT/'dist/backups/ranked-menu-20261012'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    rel='ui/jamp/main.menu';source=STAGE/rel;target=ROOT/rel
    baseline=json.loads((STAGE/'baseline.json').read_text())
    for name,sha in baseline.items():assert digest(ROOT/name)==sha,'Changed since Ranked staging: '+name
    for height in [720,1024]:
        report=json.loads((ROOT/f'dist/verification/ranked-menu-20261012/qa-1280x{height}.json').read_text())
        assert report['passed'] and report['menu']==digest(source)
    assert '\nOK\n' in (ROOT/'dist/ranking-tests.log').read_text()
    saved=BACKUP/rel
    assert not saved.exists(),'Do not overwrite the original backup'
    saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
    protected={name:sha for name,sha in baseline.items() if name!=rel}
    pending=target.with_name('main.menu.ranked-tmp');shutil.copy2(source,pending)
    try:
        pending.replace(target)
        assert digest(target)==digest(source)
        assert protected=={name:digest(ROOT/name) for name in protected}
    except Exception:
        shutil.copy2(saved,target);raise
    manifest=ROOT/'dist/ranked-menu-install-manifest.json'
    manifest.write_text(json.dumps({'files':{rel:digest(target)},'unchanged':protected,
                                    'backup':str(BACKUP)},indent=2)+'\n')
    print('Installed Ranked pages; protected files unchanged:',len(protected))
    package(manifest,target)

def package(manifest,target):
    paths=[target,manifest,ROOT/'LICENSE.txt',ROOT/'docs/Ranked-Foundation.md',ROOT/'docs/RANKED_PLAY_DESIGN.md',
           ROOT/'tools/Stage-Ranked-Menu.py',ROOT/'tools/Test-Ranked-Menu.py',ROOT/'tools/Install-Ranked-Menu.py',
           ROOT/'tests/test_rating.py',ROOT/'tests/test_ranking_store.py',ROOT/'dist/ranking-tests.log',
           ROOT/'services/__init__.py',ROOT/'development-source/menu/ranked-original/main.menu']
    paths += sorted((ROOT/'services/ranking').glob('*.py'))
    archive=ROOT/'dist/SaberTrials-ranked-foundation-20261012.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in paths:z.write(path,'SaberTrials/'+path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    archive.with_suffix('.zip.sha256').write_text(digest(archive)+'  '+archive.name+'\n')
    print('Packaged:',archive)
if __name__=='__main__':
    if sys.argv[1:]==['--package-only']:
        manifest=ROOT/'dist/ranked-menu-install-manifest.json'
        assert all(digest(ROOT/rel)==sha for rel,sha in json.loads(manifest.read_text())['files'].items())
        package(manifest,ROOT/'ui/jamp/main.menu')
    else:main()
