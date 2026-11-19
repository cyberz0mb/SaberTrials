"""Install the authorized hybrid game-test build with verified backups. Never launch."""
from pathlib import Path
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import uuid

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
CANDIDATE=ROOT/'dist/hybrid-candidate-01'
STAGING=ROOT/'dist/hybrid-install-staging'
STATE=ROOT/'dist/hybrid-install.json'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def read(path):return json.loads(path.read_text())


def tree(path):
    return {p.relative_to(path).as_posix():sha(p) for p in sorted(path.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def require(value,message):
    if not value:raise RuntimeError(message)


def stopped():
    command="Get-Process -Name 'SaberTrials.x86_64','openjk.x86_64','openjkded.x86_64','taystjk.x86_64','taystjkded.x86_64','jamp','jampDed' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id; exit 0"
    ids=subprocess.check_output(['powershell','-NoProfile','-Command',command],text=True)
    require(not ids.strip(),'Close Jedi Academy/Saber Trials before replacing files.')


def candidate_only():
    builder=load('hybrid_builder',ROOT/'tools/Build-Hybrid-Styles.py')
    m=read(CANDIDATE/'manifest.json')
    require(builder.inputs()==m['inputs'],'Candidate overlay input drift')
    require(set(m['builds'])=={'engine','game','frontend'},'Incomplete matching build')
    for kind in ('engine','game','frontend'):
        require(builder.tree(CANDIDATE/kind)==m['sources'][kind],'Candidate source drift: '+kind)
        for name,digest in m['builds'][kind].items():
            require(sha(CANDIDATE/('build-'+kind)/'Release'/name)==digest,'Binary drift: '+name)
    for name in ('assets','menus'):
        require(builder.tree(CANDIDATE/name)==m[name],'Content drift: '+name)
    return m


def stage():
    sources={
        'client/SaberTrials.x86_64.exe':CANDIDATE/'build-engine/Release/openjk.x86_64.exe',
        'client/openjkded.x86_64.exe':CANDIDATE/'build-engine/Release/openjkded.x86_64.exe',
        'client/rd-vanilla_x86_64.dll':CANDIDATE/'build-engine/Release/rd-vanilla_x86_64.dll',
        'client/rd-rend2_x86_64.dll':CANDIDATE/'build-engine/Release/rd-rend2_x86_64.dll',
        'jampgamex86_64.dll':CANDIDATE/'build-game/Release/jampgamex86_64.dll',
        'cgamex86_64.dll':CANDIDATE/'build-frontend/Release/cgamex86_64.dll',
        'uix86_64.dll':CANDIDATE/'build-frontend/Release/uix86_64.dll',
    }
    for name in ('zz_sabertrials_stances_v1.pk3','zzz_sabertrials_hybrid_v1.pk3'):
        sources[name]=CANDIDATE/'assets'/name
    for path in (CANDIDATE/'menus').rglob('*'):
        if path.is_file():sources[path.relative_to(CANDIDATE/'menus').as_posix()]=path
    STAGING.mkdir(parents=True,exist_ok=True)
    # This older preview deliberately keeps its older matching native modules.
    # Pin its engine to the verified pre-install backup, never the new ABI.
    p=ROOT/'tools/Preview-Stances.py';text=p.read_text()
    old="        mapping['bin/'+name]=ROOT/'client'/name"
    require(text.count(old)==1,'Unexpected legacy preview launcher')
    new='''        source=ROOT/'client'/name
        installed=ROOT/'dist/hybrid-install.json'
        if installed.exists():
            state=json.loads(installed.read_text())
            key='client/'+name
            if state.get('installed') and state['before'].get(key):
                source=Path(state['backup'])/key
                if sha(source)!=state['before'][key]:raise RuntimeError('Legacy preview backup changed: '+name)
        mapping['bin/'+name]=source'''
    p=STAGING/'Preview-Stances.py'
    p.write_text(text.replace(old,new),encoding='utf-8',newline='\n')
    sources['tools/Preview-Stances.py']=p
    for name in ('Launch-SaberTrials-MP.cmd','Launch-SaberTrials-Local-Duel.cmd'):
        text=(ROOT/name).read_text()
        old='set "OPENJK=%GAMEDATA%\\openjk.x86_64.exe"'
        require(text.count(old)==1,'Unexpected original launcher: '+name)
        text=text.replace(old,'set "OPENJK=%~dp0client\\SaberTrials.x86_64.exe"')
        text=text.replace('OpenJK 64-bit','The matching Saber Trials client')
        text=text.replace('Install OpenJK in the Jedi Academy GameData folder, then try again.',
                          'Restore or reinstall the Saber Trials client, then try again.')
        p=STAGING/name;p.write_text(text,encoding='ascii',newline='\r\n');sources[name]=p
    launch='''@echo off
setlocal
rem Opens the menu only. Choose a local match yourself when ready.
call "%~dp0Launch-SaberTrials-Overhaul.cmd" +set g_hybridStyles 1 +set g_stanceLibrary 1 %*
endlocal
'''
    p=STAGING/'Test-SaberTrials-New-Styles.cmd'
    p.write_text(launch,encoding='ascii',newline='\r\n');sources[p.name]=p
    # The local interpreter was verified during the build; avoid PATH ambiguity.
    restore='''@echo off
setlocal
"'''+str(Path(sys.executable).resolve())+'''" "%~dp0tools\\Install-Hybrid-Styles.py" --restore
if errorlevel 1 pause
endlocal
'''
    p=STAGING/'Restore-SaberTrials-Before-Hybrids.cmd'
    p.write_text(restore,encoding='ascii',newline='\r\n');sources[p.name]=p
    return sources


def protected_files():
    files=dict(read(ROOT/'dist/stance-candidate-02/sources.json')['protected'])
    # Preserve current launch routing, runtime dependencies, server/staff config
    # and authored UI outside the two intentionally replaced menu files.
    for name in ('Launch-SaberTrials-Overhaul.cmd','client/SDL2.dll','client/OpenAL32.dll','staff-setup.cfg'):
        p=ROOT/name
        if p.is_file():files[name]=sha(p)
    for folder in ('server','templates','ui'):
        for p in (ROOT/folder).rglob('*'):
            if p.is_file():files[p.relative_to(ROOT).as_posix()]=sha(p)
    return files


def settings_snapshot():
    documents=subprocess.check_output(['powershell','-NoProfile','-Command',
        "[Environment]::GetFolderPath('MyDocuments')"],text=True).strip()
    home=Path(documents)/'My Games/OpenJK/SaberTrials'
    return {str(p):sha(p) for p in home.glob('*.cfg') if p.is_file()}


def verify_recorded_candidate(state):
    """Verify immutable installed provenance, independent of later worktree edits."""
    manifest=Path(state['source_manifest']).resolve()
    require(manifest.parent.parent==(ROOT/'dist').resolve() and manifest.name=='manifest.json',
            'Unexpected recorded candidate manifest')
    require(sha(manifest)==state['source_manifest_sha256'],'Recorded candidate manifest changed')
    candidate=manifest.parent;m=read(manifest)
    require(set(m['builds'])=={'engine','game','frontend'},'Incomplete recorded matching build')
    for kind in ('engine','game','frontend'):
        require(tree(candidate/kind)==m['sources'][kind],'Recorded candidate source drift: '+kind)
        for name,digest in m['builds'][kind].items():
            require(sha(candidate/('build-'+kind)/'Release'/name)==digest,'Recorded binary drift: '+name)
    for name in ('assets','menus'):
        require(tree(candidate/name)==m[name],'Recorded content drift: '+name)
    for name,source in state['sources'].items():
        path=Path(source).resolve()
        require(path.is_relative_to(ROOT.resolve()),'Recorded source outside workspace: '+name)
        require(sha(path)==state['after'][name],'Recorded install source drift: '+name)
    return m


def active_update():
    path=ROOT/'dist/hybrid-loadout-install.json'
    if not path.exists():return None
    state=read(path)
    if state.get('installed') and not state.get('restored'):
        return load('hybrid_loadout_update',ROOT/'tools/Update-Hybrid-Styles.py')
    return None


def verify_installed(delegate=True):
    update=active_update() if delegate else None
    if update:return update.verify_installed()
    state=read(STATE)
    require(state['installed'] and not state.get('restored'),'This installation has been restored')
    verify_recorded_candidate(state)
    for name,digest in {**state['protected'],**state['after']}.items():
        require(sha(ROOT/name)==digest,'Installed/protected file differs: '+name)
    backup=Path(state['backup']).resolve()
    require(backup.is_relative_to((ROOT/'dist/backups').resolve()),'Unexpected backup location')
    for name,digest in state['before'].items():
        if digest is not None:require(sha(backup/name)==digest,'Backup differs: '+name)
    print('Installed matching files, preserved content and rollback backups verified.')
    return state


def install(commit=False):
    require(not STATE.exists(),'Installation record already exists; use --verify or --restore.')
    stopped()
    builder=load('hybrid_preflight',ROOT/'tools/Build-Hybrid-Styles.py')
    builder.verify() # Includes the historical protected installation BEFORE changes.
    candidate_only()
    sources=stage();protected=protected_files();settings=settings_snapshot()
    helper=load('install_transaction',ROOT/'tools/Install-Handedness.py')
    for name,digest in protected.items():require(sha(ROOT/name)==digest,'Protected file changed: '+name)
    before={name:sha(ROOT/name) for name in sources}
    after={name:sha(path) for name,path in sources.items()}
    require(all(after.values()),'Missing installation source')
    if not commit:
        print('Ready:',len(sources),'matching files. No installed files changed.');return
    stopped()
    backup=ROOT/'dist/backups'/('hybrids-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
    payload=dict(installed=True,restored=False,before=before,after=after,backup=str(backup),
                 sources={k:str(v) for k,v in sources.items()},
                 protected={k:v for k,v in protected.items() if k not in sources},
                 preserved_settings=settings,source_manifest=str(CANDIDATE/'manifest.json'),
                 source_manifest_sha256=sha(CANDIDATE/'manifest.json'),
                 game_launched=False,live_acceptance=False)
    helper.install_transaction(ROOT,sources,before,after,protected,backup,STATE,payload)
    require(settings_snapshot()==settings,'User settings changed during installation; inspect before playing.')
    verify_installed()
    print('Installed. Backup:',backup)
    print('Launch when ready:',ROOT/'Test-SaberTrials-New-Styles.cmd')


def restore():
    stopped()
    update=active_update()
    if update:update.restore()
    state=verify_installed(delegate=False)
    restore_record(STATE,state)


def restore_record(state_path,state):
    """Restore one verified receipt. Callers check process and installation first."""
    backup=Path(state['backup']);helper=load('restore_transaction',ROOT/'tools/Install-Handedness.py')
    token=uuid.uuid4().hex;pending={};changed=[];introduced=[]
    # Stage every previous file before touching the installation.
    for name,digest in state['before'].items():
        if digest is not None:
            target=helper.child(ROOT,name)
            p=target.with_name(target.name+'.hybrid-restore-'+token+'.pending')
            require(not p.exists(),'Unexpected restore temporary')
            shutil.copy2(helper.child(backup,name),p)
            require(sha(p)==digest,'Restore staging failed: '+name);pending[name]=p
    try:
        for name,digest in state['before'].items():
            target=helper.child(ROOT,name)
            require(sha(target)==state['after'][name],'File changed during restore: '+name)
            if digest is None:
                quarantine=helper.child(backup,'introduced-files/'+name)
                quarantine.parent.mkdir(parents=True,exist_ok=True)
                require(not quarantine.exists(),'Restore quarantine exists')
                os.replace(target,quarantine);introduced.append((name,quarantine))
            else:
                os.replace(pending[name],target)
            changed.append(name)
        for name,digest in state['before'].items():require(sha(ROOT/name)==digest,'Restore mismatch: '+name)
        state['installed']=False;state['restored']=True
        helper.atomic_record(state_path,state)
    except BaseException:
        for name in reversed(changed):
            target=helper.child(ROOT,name)
            previous=next((p for n,p in introduced if n==name),None)
            source=previous if previous else Path(state['sources'][name])
            require(sha(source)==state['after'][name],'Cannot recover restored file: '+name)
            temp=target.with_name(target.name+'.hybrid-recover-'+token+'.pending')
            shutil.copy2(source,temp);os.replace(temp,target)
        raise
    finally:
        for p in pending.values():
            if p.exists():p.unlink() # Exact temporary file, never recursive.
    print('Previous installation restored. New files retained in the backup for inspection.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--install',action='store_true')
    group.add_argument('--verify',action='store_true')
    group.add_argument('--restore',action='store_true')
    args=parser.parse_args()
    if args.verify:verify_installed()
    elif args.restore:restore()
    else:install(args.install)
