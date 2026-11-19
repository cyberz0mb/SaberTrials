"""Package only verified Linux artifacts and public examples. Never deploys."""
from pathlib import Path
import hashlib,json,shutil,stat,zipfile
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'dist/verification/linux-server-20261023'
STAGE=ROOT/'dist/SaberTrials-linux-server-20261023'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    evidence=json.loads((EVIDENCE/'artifacts.json').read_text())
    if evidence['game_server_started'] or not evidence['source_matches']:raise RuntimeError('Invalid verification evidence')
    for name,v in evidence['artifacts'].items():
        if sha(ROOT/'dist/linux-server-release'/name)!=v['sha256']:raise RuntimeError('Linux binary changed: '+name)
    checks={}
    for name,count in [('linux',1),('accounts',5),('staff',7),('tournament',10)]:
        log=(EVIDENCE/(name+'-test.log')).read_text()
        if f'100% tests passed, 0 tests failed out of {count}' not in log:raise RuntimeError('Linux suite incomplete: '+name)
        checks['linux_'+name]=count
    for name,count in [('accounts',5),('staff',7),('tournament',10)]:
        log=ROOT/('dist/linux-tooling/windows-'+name+'-tests.log')
        if f'100% tests passed out of {count}' not in log.read_text() and f'100% tests passed, 0 tests failed out of {count}' not in log.read_text():raise RuntimeError('Windows suite incomplete: '+name)
        shutil.copy2(log,EVIDENCE/log.name);checks['windows_'+name]=count
    backend=ROOT/'dist/linux-tooling/backend-tests.log'
    if 'Ran 90 tests' not in backend.read_text() or not backend.read_text().rstrip().endswith('OK'):raise RuntimeError('Service tests incomplete')
    shutil.copy2(backend,EVIDENCE/backend.name);checks['python_service']=90
    previous=json.loads((ROOT/'dist/verification/account-bridge-20261023/verification.json').read_text())
    protected=previous['protected_installed_files']
    if any(sha(ROOT/n)!=h for n,h in protected.items()):raise RuntimeError('Installed game files changed')
    source=json.loads((ROOT/'dist/linux-tooling/source-manifest.json').read_text())
    if any(sha(ROOT/n)!=h for n,h in source['inputs'].items()):raise RuntimeError('Sources changed after compilation/verification')
    files={
      'upload/openjkded.x86_64':ROOT/'dist/linux-server-release/openjkded.x86_64',
      'upload/SaberTrials/jampgamex86_64.so':ROOT/'dist/linux-server-release/jampgamex86_64.so',
      'upload/start-sabertrials.sh':ROOT/'templates/linux/start-sabertrials.sh',
      'upload/SaberTrials/server.cfg.example':ROOT/'templates/linux/server.cfg.example',
      'upload/SaberTrials/staff-setup.cfg.example':ROOT/'templates/staff-setup.cfg',
      'READ-ME-FIRST.md':ROOT/'docs/Linux-Server-Upload.md',
      'VERIFICATION.md':ROOT/'docs/Linux-Build-Verification.md',
      'LICENSE.txt':ROOT/'LICENSE.txt','CREDITS.txt':ROOT/'CREDITS.txt',
      'source/SaberTrials-linux-source.tar.gz':ROOT/'dist/linux-tooling/source.tar.gz',
      'verification/artifacts.json':EVIDENCE/'artifacts.json',
      'verification/source-manifest.json':ROOT/'dist/linux-tooling/source-manifest.json',
    }
    for log in EVIDENCE.glob('*test*.log'):files['verification/'+log.name]=log
    STAGE.mkdir(parents=True,exist_ok=True)
    for name,path in files.items():
        dest=STAGE/name;dest.parent.mkdir(parents=True,exist_ok=True)
        if name.endswith(('.sh','.cfg.example')):
            dest.write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
        else:shutil.copy2(path,dest)
    contents={name:sha(STAGE/name) for name in sorted(files)}
    report={'format':1,'release':'SaberTrials Linux server development 2026-10-23','architecture':'x86_64',
            'source_revision':source['revision'],'game_server_started':False,'hosted_multiplayer_verified':False,
            'hosted_servers_changed':False,'central_server_enrolled':False,'checks':checks,
            'protected_installed_files_verified':len(protected),'files':contents}
    (STAGE/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    (STAGE/'SHA256SUMS.txt').write_text(''.join(h+'  '+n+'\n' for n,h in contents.items()))
    names=list(contents)+['manifest.json','SHA256SUMS.txt']
    archive=STAGE.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name in sorted(names):
            item=zipfile.ZipInfo(name);item.create_system=3;item.compress_type=zipfile.ZIP_DEFLATED
            item.external_attr=(stat.S_IFREG|(0o755 if name.endswith('.sh') or name=='upload/openjkded.x86_64' else 0o644))<<16
            z.writestr(item,(STAGE/name).read_bytes())
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None or set(z.namelist())!=set(names):raise RuntimeError('Archive integrity failure')
        for name,h in contents.items():
            if hashlib.sha256(z.read(name)).hexdigest()!=h:raise RuntimeError('Packaged content mismatch')
    digest=sha(archive);archive.with_suffix('.zip.sha256').write_text(digest+'  '+archive.name+'\n')
    report['archive_sha256']=digest;(EVIDENCE/'release.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Verified package:',archive)
    print('Files:',len(names),'Automated checks:',sum(checks.values()),'Bytes:',archive.stat().st_size)
if __name__=='__main__':main()
