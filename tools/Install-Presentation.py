"""Install verified presentation files only, with source/hash guards and rollback."""
from pathlib import Path
import argparse,datetime,hashlib,importlib.util,json,shutil,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'dist/presentation-staging'
INPUT=ROOT/'dist/presentation-input'
BUILD=Path(tempfile.gettempdir())/'SaberTrials-presentation-20261023/build/Release'
STATE=ROOT/'dist/presentation-install.json'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def processes():
    output=subprocess.check_output(['powershell','-NoProfile','-Command',"Get-Process -Name 'SaberTrials.x86_64','openjk.x86_64','jamp' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id; exit 0"],text=True)
    return output.strip()
def main():
    p=argparse.ArgumentParser();p.add_argument('--install',action='store_true');a=p.parse_args()
    assert not (STATE.exists() and json.loads(STATE.read_text()).get('installed')), 'Already installed; inspect current manifest before updating'
    baseline=json.loads((INPUT/'manifest.json').read_text());menus=json.loads((STAGE/'manifest.json').read_text());build=json.loads((BUILD/'presentation-build.json').read_text())
    assert build['kind']=='production'
    for name,sha in build['sources'].items():assert digest(ROOT/name)==sha,'Source changed since build: '+name
    sources={n:STAGE/n for n in menus};sources.update({n:BUILD/n for n in ['uix86_64.dll','cgamex86_64.dll']})
    expected={**menus,**build['files']}
    for name,path in sources.items():
        assert digest(path)==expected[name],'Staged file changed: '+name
        assert name in baseline and digest(ROOT/name)==baseline[name],'Installed file drift: '+name
        if name.endswith('.dll'):
            data=path.read_bytes()
            for token in [b'PRESENTATION_QA',b'ST_ClientQA',b'st_clientqa',b'PROFILE_QA',b'st_hudqa',b'st_portraitqa']:
                assert token not in data,'Test hook in production '+name
    protected={n:sha for n,sha in baseline.items() if n not in sources and not n.startswith('development-source/')}
    for n,sha in protected.items():assert digest(ROOT/n)==sha,'Protected file drift: '+n
    evidence=ROOT/'dist/verification/presentation-20261023'
    # Explicitly selected successful runs, with exact final menu/build input hashes.
    for folder in ['qa-720-reviewed','qa-1024-reviewed','production-1024-reviewed']:
        record=json.loads((evidence/folder/'capture.json').read_text())
        assert record['exit_code']==0 and not record['map_loaded'] and not record['server_started']
        assert record['menu_files']==menus,'QA used different menus: '+folder
        assert record['build']['sources']==build['sources'],'QA used different sources: '+folder
    if not a.install:print('READY: verified',len(sources),'files;',len(protected),'protected files unchanged');return
    assert not processes(),'Close the game before installation'
    backup=ROOT/'dist/backups'/('presentation-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    for name in sources:
        dest=backup/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
    changed=[]
    try:
        for name,path in sources.items():
            assert digest(ROOT/name)==baseline[name],name
            shutil.copy2(path,ROOT/name);changed.append(name)
            assert digest(ROOT/name)==expected[name],name
        for n,sha in protected.items():assert digest(ROOT/n)==sha,n
    except Exception:
        for name in changed:shutil.copy2(backup/name,ROOT/name)
        raise
    STATE.write_text(json.dumps({'installed':True,'before':{n:baseline[n] for n in sources},'after':expected,'backup':str(backup.relative_to(ROOT)),'protected':protected,'build':build},indent=2)+'\n')
    print('Installed',len(sources),'presentation files; protected files unchanged. Backup:',backup)
if __name__=='__main__':main()
