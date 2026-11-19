"""Install the verified Profile viewport and UI DLL, preserving all other installed files."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,tempfile,time

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'dist/verification/profile-preview-20261023'
BUILD=Path(tempfile.gettempdir())/'SaberTrials-interface-20261011/build/Release'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text())

def main():
    processes=subprocess.check_output(['tasklist','/FO','CSV'],text=True).lower()
    assert not any('"'+name+'"' in processes for name in ('sabertrials.x86_64.exe','openjk.x86_64.exe','jamp.exe','openjkded.x86_64.exe')),'Close Saber Trials before installing.'
    sources={'uix86_64.dll':BUILD/'uix86_64.dll','ui/jamp/player.menu':ROOT/'dist/profile-preview-staging/ui/jamp/player.menu'}
    expected={name:digest(path) for name,path in sources.items()}
    build=read(BUILD/'menu-build-manifest.json')
    assert build['kind']=='production' and build['files']['uix86_64.dll']==expected['uix86_64.dll']
    data=sources['uix86_64.dll'].read_bytes()
    assert not any(marker in data for marker in (b'st_clientqa',b'PROFILE_QA',b'MENU_QA')),'QA build must never be installed'
    checks=load('profile_checks','tools/Check-Profile-Preview.py')
    qa=read(EVIDENCE/'qa-1024-lit/capture.json')
    production=read(EVIDENCE/'production-720/capture.json')
    assert qa['native_animation_checked'] and qa['exit_code']==production['exit_code']==0
    assert qa['sources']==production['sources']==checks.source_hashes(),'Changed source since verification'
    assert production['files']==expected and qa['files']['ui/jamp/player.menu']==expected['ui/jamp/player.menu']
    qa_build=read(BUILD.parent.parent/'build-qa/Release/menu-build-manifest.json')
    assert qa_build['files']['uix86_64.dll']==qa['files']['uix86_64.dll']
    for report in (qa,production):
        assert not report['map_or_server_started']
        for name,sha in report['screenshots'].items():assert digest(ROOT/name)==sha

    # Hash only installed program/menu/configuration files, never account databases or keys.
    paths=set(ROOT.glob('*.dll'))|set(ROOT.glob('*.cfg'))
    for pattern in ('ui/**/*.menu','ui/**/*.txt','menu/**/*.tga','client/*.exe','server/*.cfg'):
        paths.update(ROOT.glob(pattern))
    protected={path.relative_to(ROOT).as_posix():digest(path) for path in paths if path.relative_to(ROOT).as_posix() not in sources}
    original=ROOT/'development-source/menu/profile-preview-original/player.menu'
    assert digest(ROOT/'ui/jamp/player.menu')==digest(original),'Profile menu changed since staging'
    helper=load('staff_install','tools/Install-Staff.py')
    backup=ROOT/'dist/backups'/('profile-preview-'+time.strftime('%Y%m%d-%H%M%S'))
    record=helper.transaction(ROOT,sources,backup)
    assert protected=={name:digest(ROOT/name) for name in protected}
    record.update(installed=True,protected=protected,build=build,sources=checks.source_hashes(),checks=['qa-1024-lit','production-720'])
    (ROOT/'dist/profile-preview-install.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Installed walking Profile preview. Preserved',len(protected),'other installed files.')

if __name__=='__main__':main()
