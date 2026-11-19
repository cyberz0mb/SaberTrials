"""Verify and install one complete native handedness build, with rollback.

Requires exact production-engine evidence and the accepted component baseline.
Does not change configuration, account data, game archives or other menus.
"""
from pathlib import Path
import argparse, datetime, hashlib, importlib.util, json, os, re, shutil, subprocess, sys, uuid

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'dist/handedness-install.json'
sys.dont_write_bytecode=True


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def read(p):return json.loads(p.read_text())


def require(condition,message):
    if not condition:raise RuntimeError(message)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def child(root,name):
    root=Path(root).resolve();relative=Path(name)
    require(not relative.is_absolute() and '..' not in relative.parts,'Unsafe relative path: '+str(name))
    target=(root/relative).resolve()
    require(target!=root and target.is_relative_to(root),'Path escapes root: '+str(target))
    return target


def checked_evidence(folder,files):
    folder=folder.resolve()
    require(folder.is_relative_to((ROOT/'dist/verification/handedness-20261024').resolve()),'Evidence path outside verification root')
    for relative,digest in files.items():
        p=child(folder,relative)
        require(sha(p)==digest,'Evidence artifact changed: '+str(p))
    return folder


def checked_renderer(log,folder,renderer):
    wanted='rd-'+renderer+'_x86_64.dll'
    loads=re.findall(r'Trying to load "(rd-[^"]+)" from "([^"]+)"',log)
    require(bool(loads) and all(name==wanted and Path(path).resolve()==(folder/'bin').resolve()
                               for name,path in loads),'Unexpected native renderer load: '+repr(loads))


def verify_lock_evidence(folder,renderer,scale,engine,qa,checker):
    folder=checked_evidence(folder,{})
    result=read(folder/'result.json');manifest=read(folder/'manifest.json');plan=read(folder/'plan.json')
    checked_evidence(folder,manifest['files'])
    require(result['renderer']==manifest['renderer']==renderer,'Wrong lock renderer')
    require(not manifest['map_or_server_requested'],'Lock run requested a server')
    require(Path(manifest['build']).resolve()==Path(qa['baseline'])/'qa/Release','Lock run used another QA bundle')
    probe_sources={Path(name).as_posix():digest for name,digest in manifest['sources'].items()}
    require(len(probe_sources)==len(manifest['sources']),'Ambiguous lock source paths')
    for name,digest in probe_sources.items():
        require(sha(child(ROOT,name))==digest,'Lock probe/checker changed: '+name)
    for name in ('tests/handedness/lock_qa.inc','tools/Check-Handedness-Locks.py'):
        require(probe_sources.get(name)==sha(ROOT/name),'Missing current lock source provenance: '+name)
    analysis=read(folder/'analysis_manifest.json')
    require(analysis['checker_sha256']==sha(ROOT/'tools/Check-Handedness-Locks.py'),'Lock analyzer changed')
    require(analysis['qconsole_sha256']==sha(folder/'home/SaberTrials/qconsole.log'),'Lock log changed after analysis')
    require(read(folder/'process.json')['returncode']==0,'Native lock process failed')
    wanted_files={'bin/openjk.x86_64.exe':engine['openjk.x86_64.exe'],
                  'bin/rd-'+renderer+'_x86_64.dll':engine['rd-'+renderer+'_x86_64.dll'],
                  'home/SaberTrials/uix86_64.dll':qa['files']['uix86_64.dll']}
    actual_files={Path(n).as_posix():digest for n,digest in manifest['files'].items()}
    require(actual_files==wanted_files,'Lock run binary identity differs from production/QA UI')
    _,scenarios,shots=checker.make_plan(None,scale)
    _,pairs,pair_shots=checker.make_pair_plan(scale)
    shots+=pair_shots
    require(plan==dict(scenarios=scenarios,screenshots=shots,pair_scenes=pairs,finger_probe=True),
            'Lock evidence must contain the complete matrix and paired scenes at scale '+str(scale))
    log=(folder/'home/SaberTrials/qconsole.log').read_text(errors='replace')
    checked_renderer(log,folder,renderer)
    fresh=checker.validate(log,checker.parse_records(log),scenarios,shots,folder/'home/SaberTrials')
    pair_result=checker.validate_pairs(log,pairs)
    pair_result={key:value for key,value in pair_result.items() if key!='records'}
    fingers=checker.validate_fingers(log,scenarios,pairs)
    require(fresh['passed'] and pair_result['passed'] and fingers['passed'],'Fresh lock evidence analysis failed')
    require(not fresh['map_or_server_started'],'Native lock run started a server/map')
    for key,value in fresh.items():require(result.get(key)==value,'Lock result differs from fresh analysis: '+key)
    require(result['pair_scenes']==pair_result and result['finger_grips']==fingers,'Stale pair/finger results')
    require(fresh['scenarios']==144 and fresh['records']==2496 and fingers['records']==2088,'Incomplete native matrix')
    require(pair_result['scenes']==18 and pair_result['blade_records']==60,'Incomplete paired visual scenes')
    require(set(result['screenshots'])==set(shots),'Incomplete screenshot evidence')
    checked_evidence(folder/'home/SaberTrials/screenshots',result['screenshots'])
    return {'path':str(folder),'result_sha256':sha(folder/'result.json'),
            'manifest_sha256':sha(folder/'manifest.json'),'plan_sha256':sha(folder/'plan.json'),
            'analysis_manifest_sha256':sha(folder/'analysis_manifest.json'),
            'qconsole_sha256':analysis['qconsole_sha256'],'checker_sha256':analysis['checker_sha256']}


def atomic_record(path,payload,replace=os.replace):
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.pending')
    try:
        with temporary.open('x',encoding='utf-8',newline='\n') as stream:
            json.dump(payload,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()


def install_transaction(root,sources,before,after,protected,backup,state,payload,replace=os.replace,copy=shutil.copy2):
    """Stage all bytes before replacing targets; restore every changed target on error."""
    root=Path(root).resolve()
    targets={name:child(root,name) for name in sources}
    backup=Path(backup).resolve();state=Path(state).resolve()
    require(backup.is_relative_to(child(root,'dist/backups')),'Backup outside intended backup root')
    require(state.parent==child(root,'dist'),'Installation record outside dist')
    require(not state.exists() and not state.is_symlink(),'Installation record already exists')
    require(set(sources)==set(before)==set(after),'Transaction file set mismatch')
    for name,source in sources.items():
        require(Path(source).resolve().is_relative_to(root),'Source outside workspace: '+str(source))
        require(sha(source)==after[name] and after[name] is not None,'Source changed: '+name)
        require(sha(targets[name])==before[name],'Destination changed: '+name)
    backup.mkdir(parents=True,exist_ok=False)
    for name,digest in before.items():
        if digest is not None:
            saved=child(backup,name);saved.parent.mkdir(parents=True,exist_ok=True)
            copy(targets[name],saved);require(sha(saved)==digest,'Backup verification failed: '+name)
    atomic_record(backup/'manifest.json',{'before':before,'after':after,'state':str(state)})
    token=uuid.uuid4().hex;pending=[];staged={};changed=[];rollback_errors=[]
    try:
        for name,source in sources.items():
            target=targets[name];temporary=target.with_name(target.name+'.handedness-'+token+'.pending')
            require(not temporary.exists() and not temporary.is_symlink(),'Pending file exists: '+str(temporary))
            pending.append(temporary);copy(source,temporary)
            require(sha(temporary)==after[name],'Staged file verification failed: '+name)
            staged[name]=temporary
        for name,target in targets.items():
            require(child(root,name)==target and sha(target)==before[name],'Destination drift: '+name)
            replace(staged[name],target);changed.append(name)
            require(sha(target)==after[name],'Installed hash mismatch: '+name)
        for name,digest in protected.items():
            if name not in sources:require(sha(child(root,name))==digest,'Protected file changed: '+name)
        require(not state.exists() and not state.is_symlink(),'Installation record appeared during transaction')
        atomic_record(state,payload,replace=replace)
    except BaseException as failure:
        for name in reversed(changed):
            try:
                target=targets[name]
                require(child(root,name)==target and sha(target)==after[name],'Refusing to overwrite external changes: '+name)
                if before[name] is None:
                    target.unlink()
                else:
                    saved=child(backup,name);require(sha(saved)==before[name],'Backup changed: '+name)
                    temporary=target.with_name(target.name+'.handedness-'+token+'.restore')
                    require(not temporary.exists() and not temporary.is_symlink(),'Restore file exists: '+str(temporary))
                    pending.append(temporary);copy(saved,temporary)
                    require(sha(temporary)==before[name],'Restore staging failed: '+name)
                    replace(temporary,target)
                require(sha(target)==before[name],'Restored hash mismatch: '+name)
            except BaseException as restore_failure:
                rollback_errors.append(name+': '+str(restore_failure))
        if rollback_errors:
            raise RuntimeError('Install failed: '+str(failure)+'; rollback errors: '+'; '.join(rollback_errors)+
                               '; verified backup: '+str(backup)) from failure
        raise
    finally:
        for temporary in pending:
            if temporary.exists():
                require(temporary.resolve().is_relative_to(root),'Temporary path escaped workspace')
                try:temporary.unlink()
                except OSError as cleanup_failure:
                    print('Retained transaction temporary file:',temporary,cleanup_failure,file=sys.stderr)


def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True)
    for name in ('locks','scaled','rend2','menu','preview'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--install',action='store_true');a=p.parse_args()
    require(not STATE.exists() and not STATE.is_symlink(),'Inspect existing installation record before updating')
    base=a.baseline.resolve()
    require(base.parent==(ROOT/'dist').resolve() and base.name.startswith('handedness-baseline-'),'Invalid baseline path')
    record=read(base/'provenance.json');qa=read(base/'qa/qa-manifest.json')
    require(qa['production_engine_renderers'] and qa['baseline']==str(base),'QA bundle belongs to another baseline')
    require(qa['baseline_provenance_sha256']==sha(base/'provenance.json'),'Baseline changed since QA build')
    builder=load('baseline_verify',ROOT/'tools/Prepare-Handedness-Baseline.py')
    qa_builder=load('qa_verify',ROOT/'tools/Build-Handedness-QA.py')
    require(qa_builder.input_hashes()==qa['inputs'],'QA probe/build inputs changed')
    expected_qa=dict(record['components']['frontend'])
    edits=qa_builder.qa_texts(base/'frontend')
    expected_qa.update({name:hashlib.sha256(text.encode('utf-8')).hexdigest() for name,text in edits.items()})
    require(qa['qa_source_changes']==sorted(edits),'Unexpected QA source edit set')
    require(builder.tree(base/'qa/source')==qa['source']==expected_qa,'QA source differs from accepted frontend plus probes')
    require(builder.tree(base/'qa/Release')==qa['files'],'QA release files changed')
    require(builder.tree(ROOT/'development-source/handedness')==record['feature_inputs'],'Feature changed since build')
    for component in ('engine','game','frontend'):
        require(builder.tree(base/component)==record['components'][component],'Prepared source changed')
        for name,digest in record['builds'][component].items():
            require(sha(child(base/('build-'+component)/'Release',name))==digest,'Build output changed')
    engine=record['builds']['engine'];front=record['builds']['frontend'];game=record['builds']['game']
    for name in ('openjk.x86_64.exe','rd-vanilla_x86_64.dll','rd-rend2_x86_64.dll'):
        require(qa['files'][name]==engine[name],'QA engine/renderer differs from production')
    require('"1", NULL, CVAR_SERVERINFO|CVAR_LATCH' in (ROOT/'development-source/handedness/state_hooks.py').read_text(),
            'Handedness default is not enabled in accepted source')
    evidence={}
    checker=load('lock_verify',ROOT/'tools/Check-Handedness-Locks.py')
    for label,folder,renderer,scale in (('locks',a.locks,'vanilla',1.),('scaled',a.scaled,'vanilla',1.25),('rend2',a.rend2,'rend2',1.)):
        evidence[label]=verify_lock_evidence(folder,renderer,scale,engine,qa,checker)
    for label,folder in (('menu',a.menu),('preview',a.preview)):
        folder=checked_evidence(folder,{})
        result=read(folder/'evidence.json');checked_evidence(folder,result['files'])
        require(not result['map_or_server_started'],'Menu/preview started a map/server')
        script=ROOT/('tools/Check-Handedness-'+label.capitalize()+'.py')
        require(result['checker_sha256']==sha(script),'Menu/preview checker changed after run')
        wanted_logs={'hand-menu.log','hand-reopen.log'} if label=='menu' else {'home/SaberTrials/qconsole.log'}
        require(set(result['logs'])==wanted_logs,'Missing menu/preview logs')
        require(result['returncodes']==([0,0] if label=='menu' else [0]),'Native menu/preview process failed')
        checked_evidence(folder,result['logs'])
        for name in wanted_logs:
            log=child(folder,name).read_text(errors='replace')
            checked_renderer(log,folder,'vanilla')
            require(not re.search(r'Server Initialization|SpawnServer|Loading map',log,re.I),'Menu/preview log contains a map/server')
            require(('ST_HAND_MENU_COMPLETE' if label=='menu' else 'ST_HANDEDNESS_PREVIEW_COMPLETE') in log,
                    'Menu/preview completion missing')
        files={Path(n).as_posix():d for n,d in result['files'].items()}
        require(files['bin/SaberTrials.x86_64.exe']==engine['openjk.x86_64.exe'],'Menu/preview engine differs from production')
        require(files['home/SaberTrials/uix86_64.dll']==qa['files']['uix86_64.dll'],'Menu/preview UI differs from QA bundle')
        require(files['bin/rd-vanilla_x86_64.dll']==engine['rd-vanilla_x86_64.dll'],'Menu/preview renderer differs from production')
        require(sum(n.endswith('.png') for n in files)==(5 if label=='menu' else 16),'Incomplete menu/preview screenshots')
        if label=='menu':
            require(set(result['checks'])=={'initial','opened','edited','cancelled','applied','escaped','persisted'},
                    'Incomplete menu state checks')
        evidence[label]={'path':str(folder),'result_sha256':sha(folder/'evidence.json'),
                         'checker_sha256':result['checker_sha256'],'logs':result['logs']}
    menu_record=read(ROOT/'dist/handedness-staging/menus.json')
    for name,digest in menu_record['inputs'].items():require(sha(child(ROOT,name))==digest,'Menu source changed')
    menu_path=ROOT/'dist/handedness-staging/ui/jamp/saber.menu'
    require(sha(menu_path)==menu_record['files']['ui/jamp/saber.menu'],'Staged menu changed')
    require(sha(a.menu/'home/SaberTrials/ui/jamp/saber.menu')==sha(menu_path),'Menu evidence differs')
    sources={
        'client/SaberTrials.x86_64.exe':base/'build-engine/Release/openjk.x86_64.exe',
        'client/rd-vanilla_x86_64.dll':base/'build-engine/Release/rd-vanilla_x86_64.dll',
        'client/rd-rend2_x86_64.dll':base/'build-engine/Release/rd-rend2_x86_64.dll',
        'jampgamex86_64.dll':base/'build-game/Release/jampgamex86_64.dll',
        'cgamex86_64.dll':base/'build-frontend/Release/cgamex86_64.dll',
        'uix86_64.dll':base/'build-frontend/Release/uix86_64.dll',
        'ui/jamp/saber.menu':menu_path,
    }
    accepted=read(ROOT/'dist/presentation-install.json')
    protected={**accepted['protected'],**accepted['after'],**record['installed']}
    protected['client/rd-vanilla_x86_64.dll']=read(ROOT/'client/manifest.json')['installed_files']['client/rd-vanilla_x86_64.dll']
    for name,digest in protected.items():require(sha(child(ROOT,name))==digest,'Installed file drift: '+name)
    require(not child(ROOT,'client/rd-rend2_x86_64.dll').exists(),'Unexpected existing Rend2 renderer; inspect first')
    for name,path in sources.items():
        if path.suffix in ('.dll','.exe'):
            data=path.read_bytes()
            for marker in (b'st_handqa',b'st_lockqa',b'HAND_QA ready',b'ST_LOCK_QA_COMPLETE'):
                require(marker not in data,'QA code in production: '+name)
    before={n:sha(child(ROOT,n)) for n in sources};after={n:sha(p) for n,p in sources.items()}
    if not a.install:
        print('READY: seven files verified against production evidence; installed files unchanged.');return
    running=subprocess.check_output(['powershell','-NoProfile','-Command',
        "Get-Process -Name 'SaberTrials.x86_64','openjk.x86_64','openjkded.x86_64','taystjk.x86_64','taystjkded.x86_64','jamp','jampDed' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id; exit 0"],text=True)
    require(not running.strip(),'Close the game before installation')
    backup=child(ROOT,'dist/backups/handedness-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
    payload={'installed':True,'baseline':str(base),'before':before,'after':after,
             'backup':str(backup),'evidence':evidence,'protected':{n:d for n,d in protected.items() if n not in sources}}
    install_transaction(ROOT,sources,before,after,protected,backup,STATE,payload)
    print('Installed handedness engine, modules, renderers and saber menu. Backup:',backup)


if __name__=='__main__':main()
