"""Back up and install only the verified Profile layout, UI module and focus texture."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess,tempfile,time

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'dist/profile-layout-staging'
EVIDENCE=ROOT/'dist/verification/profile-layout-20261023'
BUILD=Path(tempfile.gettempdir())/'SaberTrials-interface-20261011/build/Release'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())

def main():
    processes=subprocess.check_output(['tasklist','/FO','CSV'],text=True).lower()
    assert not any('"'+n+'"' in processes for n in ('sabertrials.x86_64.exe','openjk.x86_64.exe','jamp.exe','openjkded.x86_64.exe')),'Close Saber Trials first.'
    targets=read(STAGE/'manifest.json')
    sources={name:STAGE/name for name in targets};sources['uix86_64.dll']=BUILD/'uix86_64.dll'
    after={name:digest(p) for name,p in sources.items()}
    build=read(BUILD/'menu-build-manifest.json');assert build['kind']=='production'
    assert build['files']['uix86_64.dll']==after['uix86_64.dll']
    assert not any(marker in sources['uix86_64.dll'].read_bytes() for marker in (b'st_clientqa',b'PROFILE_QA',b'MENU_QA',b'PROFILE_LAYOUT'))
    spec=importlib.util.spec_from_file_location('layout_check',ROOT/'tools/Check-Profile-Layout.py')
    check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)
    reports=[read(EVIDENCE/name/'capture.json') for name in ('qa-1024-final','qa-720-final','production-1024')]
    assert reports[-1]['files']==after
    for report in reports:
        assert report['sources']==check.sources() and report['exit_code']==0 and not report['map_or_server_started']
        assert {n:h for n,h in report['files'].items() if n!='uix86_64.dll'}==targets
        for name,sha in report['screenshots'].items():assert digest(ROOT/name)==sha
    assert all(report['native_controls_checked'] for report in reports[:2])
    assert reports[0]['files']['uix86_64.dll']==reports[1]['files']['uix86_64.dll']==read(BUILD.parent.parent/'build-qa/Release/menu-build-manifest.json')['files']['uix86_64.dll']
    assert digest(ROOT/'ui/jamp/player.menu')==digest(ROOT/'development-source/menu/profile-layout-original/player.menu')
    paths=set(ROOT.glob('*.dll'))|set(ROOT.glob('*.cfg'))
    for pattern in ('ui/**/*.menu','ui/**/*.txt','ui/assets/**/*.tga','menu/**/*.tga','client/*.exe','server/*.cfg'):paths.update(ROOT.glob(pattern))
    protected={p.relative_to(ROOT).as_posix():digest(p) for p in paths if p.relative_to(ROOT).as_posix() not in sources}
    before={name:digest(ROOT/name) if (ROOT/name).exists() else None for name in sources}
    backup=ROOT/'dist/backups'/('profile-layout-'+time.strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True,exist_ok=False)
    for name,sha in before.items():
        if sha:
            saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,saved);assert digest(saved)==sha
    (backup/'manifest.json').write_text(json.dumps({'before':before,'after':after},indent=2)+'\n')
    changed=[]
    try:
        for name,source in sources.items():
            target=ROOT/name;assert target.resolve().is_relative_to(ROOT.resolve())
            assert (digest(target) if target.exists() else None)==before[name]
            pending=target.with_name(target.name+'.profile-pending');assert not pending.exists()
            try:
                shutil.copy2(source,pending);assert digest(pending)==after[name];os.replace(pending,target);changed.append(name)
            finally:
                if pending.exists():pending.unlink()
        assert after=={n:digest(ROOT/n) for n in sources}
        assert protected=={n:digest(ROOT/n) for n in protected}
    except Exception:
        for name in reversed(changed):
            if before[name]:shutil.copy2(backup/name,ROOT/name)
            else:(ROOT/name).unlink()
        raise
    (ROOT/'dist/profile-layout-install.json').write_text(json.dumps({'installed':True,'before':before,'after':after,'backup':str(backup.relative_to(ROOT)),
        'protected':protected,'sources':check.sources(),'build':build,'checks':['qa-1024-final','qa-720-final','production-1024']},indent=2)+'\n')
    print('Installed Profile layout; preserved',len(protected),'other installed files.')

if __name__=='__main__':main()
