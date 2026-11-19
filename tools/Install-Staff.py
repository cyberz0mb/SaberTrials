"""Verify, package and install the staff update; never installs QA binaries or creates accounts."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,shutil,tempfile,time,zipfile

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'dist/verification/staff-20261012'
BUILD=ROOT/'dist/staff-build/Release'
QA=ROOT/'dist/staff-build-qa/Release'
FILES={'client/SaberTrials.x86_64.exe':'openjk.x86_64.exe','jampgamex86_64.dll':'jampgamex86_64.dll','cgamex86_64.dll':'cgamex86_64.dll'}
SUITES=('all','same-identity','network','gameplay','backup-media','listen','visuals')
TEMPLATES=('templates/staff-setup.cfg','templates/server.cfg','templates/README.md')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')

def verify():
    production=read(BUILD/'staff-build-manifest.json');qa=read(QA/'staff-build-manifest.json')
    assert production['kind']=='production' and qa['kind']=='qa'
    spec=importlib.util.spec_from_file_location('staff_build',ROOT/'tools/Build-Staff.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    assert production['inputs']==qa['inputs']==helper.input_hashes(),'Source changed since the tested builds'
    helper.verify_dependencies(ROOT/'dist/staff-deps')
    for folder,manifest in ((BUILD,production),(QA,qa)):
        assert manifest['files']=={name:digest(folder/name) for name in manifest['files']}
    forbidden=('stqacmd','STAFF_QA ','STAFF_CLIENT_QA','st_staffQAProbe','STAFF_VIEW','STAFF_PICKUP','STAFF_CLOCK')
    for name in production['files']:
        data=(BUILD/name).read_bytes()
        assert not any(text.encode(encoding) in data for text in forbidden for encoding in ('utf-8','utf-16le')),name
    reports={}
    for suite in SUITES:
        report=read(EVIDENCE/f'qa-{suite}-pass.json')
        assert report['passed'] and report['suite']==suite and report['kind']=='qa'
        assert report['files']==qa['files'] and report['inputs']==qa['inputs'],'Stale QA evidence: '+suite
        reports[suite]=report
    report=read(EVIDENCE/'production-production-pass.json')
    assert report['passed'] and report['kind']=='production' and report['files']==production['files']
    assert report['inputs']==production['inputs']
    reviewed=read(EVIDENCE/'visual-review.json')
    assert reviewed['passed'] and reviewed['files']==qa['files']
    assert reviewed['screenshots']=={name:digest(ROOT/name) for name in reports['visuals']['screenshots']}
    baseline={name.replace('\\','/'):sha for name,sha in read(EVIDENCE/'baseline.json').items() if not name.replace('\\','/').startswith('development-source/')}
    assert baseline=={name:digest(ROOT/name) for name in baseline},'Installed baseline has changed'
    evidence={'production':production,'qa':qa,'checks':{suite:r['checks'] for suite,r in reports.items()},'production_checks':report['checks'],'protected_files':len(baseline)}
    write(EVIDENCE/'release-verification.json',evidence)
    return production,baseline,evidence

def transaction(root,sources,backup,replace=os.replace):
    """Back up and replace only the supplied targets; roll back any partial write."""
    root=root.resolve();backup.mkdir(parents=True,exist_ok=False)
    old={};new={};changed=[];pending=[]
    for name,source in sources.items():
        target=(root/name).resolve();assert target.is_relative_to(root)
        old[name]=digest(target);new[name]=digest(source)
        saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
        assert digest(saved)==old[name]
    write(backup/'manifest.json',{'before':old,'after':new})
    try:
        for name,source in sources.items():
            target=root/name;temporary=target.with_name(target.name+'.staff-pending')
            assert not temporary.exists(),'Pending update exists: '+str(temporary)
            shutil.copy2(source,temporary);pending.append(temporary)
            assert digest(temporary)==new[name]
            assert digest(target)==old[name],'Target changed during installation'
            replace(temporary,target);changed.append(name)
            assert digest(target)==new[name]
    except Exception:
        for name in reversed(changed):
            target=root/name;temporary=target.with_name(target.name+'.staff-restore')
            shutil.copy2(backup/name,temporary);os.replace(temporary,target)
            assert digest(target)==old[name]
        raise
    finally:
        for path in pending:
            if path.exists():path.unlink()
    return {'before':old,'after':new,'backup':str(backup.relative_to(root))}

def package(production,evidence):
    archive=ROOT/'dist/SaberTrials-staff-20261022.zip'
    paths={}
    for target,source in FILES.items():paths['SaberTrials/'+target]=BUILD/source
    paths['SaberTrials/server/openjkded.x86_64.exe']=BUILD/'openjkded.x86_64.exe'
    for folder in ('development-source/bot-roles','development-source/client-game','development-source/client-overhaul','development-source/staff','tests/staff'):
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and p.suffix in ('.c','.cpp','.h','.inc','.patch','.txt','.json','.md','.py','.cmake'):
                paths['SaberTrials/'+p.relative_to(ROOT).as_posix()]=p
    for name in ('tools/Build-Staff.py','tools/Build-Overhaul.py','tools/Generate-Staff-Engine-Patch.py','tools/Install-Staff.py','tools/Test-Staff.py','docs/STAFF_ACCOUNTS.md','docs/STAFF_COMMAND_AUDIT.md','docs/ADMIN_GUIDE.md','docs/ADMIN_COMMANDS.md','docs/Staff-Verification.md','docs/Staff-Update-README.md','LICENSE.txt','CREDITS.txt'):
        paths['SaberTrials/'+name]=ROOT/name
    for name in TEMPLATES:paths['SaberTrials/'+name]=ROOT/name
    upstream=ROOT/'dist/staff-work/openjk.zip'
    assert digest(upstream)==production['source_archive_sha256']
    paths['SaberTrials/source/OpenJK-'+production['source_revision']+'.zip']=upstream
    for name in ('sodium.tar.gz','sqlite.zip'):paths['SaberTrials/dist/staff-deps/'+name]=ROOT/'dist/staff-deps'/name
    assert not any(Path(name).suffix.lower() in ('.key','.db','.log','.dm_26') for name in paths)
    assert all(name in {'SaberTrials/'+p for p in TEMPLATES} for name in paths if Path(name).suffix.lower()=='.cfg')
    assert not any('/private/' in name or '__pycache__' in name for name in paths)
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name,path in sorted(paths.items()):z.write(path,name)
        z.writestr('SaberTrials/staff-release-manifest.json',json.dumps({'build':production,'payload':{name:digest(path) for name,path in paths.items()},'checks':evidence['checks'],'production_checks':evidence['production_checks']},indent=2)+'\n')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,path in paths.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest(path)
    archive.with_suffix('.zip.sha256').write_text(digest(archive)+'  '+archive.name+'\n')
    return archive

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('verify','package','install','rollback'));p.add_argument('--backup');a=p.parse_args()
    if a.action=='rollback':
        assert a.backup,'Pass the exact backup folder from staff-install-manifest.json'
        backup=(ROOT/a.backup).resolve();assert backup.is_relative_to((ROOT/'dist/backups').resolve())
        manifest=read(backup/'manifest.json');assert set(manifest['after'])==set(FILES)
        for name,sha in manifest['after'].items():assert digest(ROOT/name)==sha,'Installed file changed; refusing automatic rollback'
        for name,sha in manifest['before'].items():assert digest(backup/name)==sha
        for name in FILES:
            target=ROOT/name;temporary=target.with_name(target.name+'.staff-restore');shutil.copy2(backup/name,temporary);os.replace(temporary,target)
            assert digest(target)==manifest['before'][name]
        print('Restored the three previous binaries. Staff private accounts were not modified.');return
    production,baseline,evidence=verify()
    if a.action=='verify':print('Verified exact build hashes, runtime evidence and installed baseline.');return
    archive=package(production,evidence)
    print('Packaged:',archive)
    if a.action=='install':
        backup=ROOT/'dist/backups'/('staff-'+time.strftime('%Y%m%d-%H%M%S'))
        record=transaction(ROOT,{name:BUILD/source for name,source in FILES.items()},backup)
        protected={name:sha for name,sha in baseline.items() if name not in FILES}
        assert protected=={name:digest(ROOT/name) for name in protected}
        record.update(unchanged=protected,build=production,archive=archive.name)
        write(ROOT/'dist/staff-install-manifest.json',record)
        print('Installed staff client/game/cgame. Menus, UI module, profile and private accounts unchanged.')
if __name__=='__main__':main()
