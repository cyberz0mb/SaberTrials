"""Install the authorized three-style update with verified backups. Never launch."""
from pathlib import Path
import argparse
import datetime
import importlib.util
import json
import sys
import uuid

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
CANDIDATE=ROOT/'dist/hybrid-candidate-02'
STATE=ROOT/'dist/hybrid-loadout-install.json'
STAGING=ROOT/'dist/hybrid-loadout-install-staging'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

LEGACY=load('hybrid_install_base',ROOT/'tools/Install-Hybrid-Styles.py')
TX=load('hybrid_update_transaction',ROOT/'tools/Install-Handedness.py')
sha=LEGACY.sha
read=LEGACY.read
require=LEGACY.require


def stage():
    sources={
        'client/SaberTrials.x86_64.exe':CANDIDATE/'build-engine/Release/openjk.x86_64.exe',
        'client/openjkded.x86_64.exe':CANDIDATE/'build-engine/Release/openjkded.x86_64.exe',
        'client/rd-vanilla_x86_64.dll':CANDIDATE/'build-engine/Release/rd-vanilla_x86_64.dll',
        'client/rd-rend2_x86_64.dll':CANDIDATE/'build-engine/Release/rd-rend2_x86_64.dll',
        'jampgamex86_64.dll':CANDIDATE/'build-game/Release/jampgamex86_64.dll',
        'cgamex86_64.dll':CANDIDATE/'build-frontend/Release/cgamex86_64.dll',
        'uix86_64.dll':CANDIDATE/'build-frontend/Release/uix86_64.dll',
        'ui/jamp/saber.menu':CANDIDATE/'menus/ui/jamp/saber.menu',
        'ui/jamp/ingame_saber.menu':CANDIDATE/'menus/ui/jamp/ingame_saber.menu',
        'zz_sabertrials_styles_v1.pk3':CANDIDATE/'assets/zz_sabertrials_styles_v1.pk3',
    }
    # The existing stance package is unchanged; the former hybrid package is
    # retained below the corrected package in the engine's tested sort order.
    require(sha(ROOT/'zz_sabertrials_stances_v1.pk3')==sha(CANDIDATE/'assets/zz_sabertrials_stances_v1.pk3'),
            'Update requires the matching installed stance library')
    STAGING.mkdir(parents=True,exist_ok=True)
    restore='''@echo off
setlocal
"'''+str(Path(sys.executable).resolve())+'''" "%~dp0tools\\Update-Hybrid-Styles.py" --restore
if errorlevel 1 pause
endlocal
'''
    command=STAGING/'Restore-SaberTrials-Before-Loadouts.cmd'
    command.write_text(restore,encoding='ascii',newline='\r\n')
    sources[command.name]=command
    return sources


def active_ui_fix():
    path=ROOT/'dist/hybrid-ui-buffer-install.json'
    if not path.exists():return None
    state=read(path)
    if state.get('installed') and not state.get('restored'):
        return load('hybrid_ui_buffer_fix',ROOT/'tools/Fix-Hybrid-UI-Buffer.py')
    return None


def verify_recorded_update():
    """Validate this layer's immutable sources and backups beneath a later fix."""
    state=read(STATE)
    require(state.get('installed') and not state.get('restored'),'The three-style update has been restored')
    require(sha(LEGACY.STATE)==state['previous_receipt_sha256'],'Previous installation receipt changed')
    previous=read(LEGACY.STATE)
    require(previous.get('installed') and not previous.get('restored'),'Previous installation is inactive')
    LEGACY.verify_recorded_candidate(previous)
    LEGACY.verify_recorded_candidate(state)
    backup=Path(state['backup']).resolve()
    require(backup.is_relative_to((ROOT/'dist/backups').resolve()),'Unexpected update backup location')
    for name,digest in state['before'].items():
        if digest is not None:require(sha(TX.child(backup,name))==digest,'Update backup differs: '+name)
    # Keep the first installation's rollback evidence valid as well.
    old_backup=Path(previous['backup']).resolve()
    require(old_backup.is_relative_to((ROOT/'dist/backups').resolve()),'Unexpected original backup location')
    for name,digest in previous['before'].items():
        if digest is not None:require(sha(TX.child(old_backup,name))==digest,'Original backup differs: '+name)
    return state


def verify_installed(delegate=True):
    fix=active_ui_fix() if delegate else None
    if fix:return fix.verify_installed()
    state=verify_recorded_update()
    for name,digest in {**state['protected'],**state['after']}.items():
        require(sha(TX.child(ROOT,name))==digest,'Updated/protected file differs: '+name)
    print('Three-style installation, preserved content and both rollback backups verified.')
    return state


def install(commit=False):
    require(not STATE.exists(),'Update receipt already exists; use --verify or --restore.')
    LEGACY.stopped()
    previous=LEGACY.verify_installed(delegate=False)
    builder=load('hybrid_update_builder',ROOT/'tools/Build-Hybrid-Styles.py')
    require(builder.OUT.resolve()==CANDIDATE.resolve(),'Builder targets a different candidate')
    manifest=builder.verify()
    require(set(manifest['builds'])=={'engine','game','frontend'},'Incomplete three-style build')
    sources=stage()
    settings=LEGACY.settings_snapshot()
    protected={**previous['protected'],**previous['after']}
    protected['dist/hybrid-install.json']=sha(LEGACY.STATE)
    # Hash current root configuration too, without reading or changing values.
    protected.update({p.relative_to(ROOT).as_posix():sha(p) for p in ROOT.glob('*.cfg') if p.is_file()})
    before={name:sha(TX.child(ROOT,name)) for name in sources}
    after={name:sha(source) for name,source in sources.items()}
    require(all(after.values()),'Missing update source')
    payload=dict(installed=True,restored=False,before=before,after=after,
        sources={k:str(v) for k,v in sources.items()},
        protected={k:v for k,v in protected.items() if k not in sources},
        preserved_settings=settings,source_manifest=str(CANDIDATE/'manifest.json'),
        source_manifest_sha256=sha(CANDIDATE/'manifest.json'),
        previous_receipt=str(LEGACY.STATE),previous_receipt_sha256=sha(LEGACY.STATE),
        game_launched=False,live_acceptance=False)
    # Independent sealed-file verification catches bad staging without trusting
    # an updated builder's interpretation of previously installed provenance.
    LEGACY.verify_recorded_candidate(payload)
    if not commit:
        print('Ready:',len(sources),'matching update files. Installed files and settings unchanged.');return
    LEGACY.stopped()
    backup=ROOT/'dist/backups'/('hybrid-loadouts-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
    payload['backup']=str(backup)
    TX.install_transaction(ROOT,sources,before,after,protected,backup,STATE,payload)
    require(LEGACY.settings_snapshot()==settings,'User settings changed during update; inspect before playing.')
    verify_installed()
    print('Installed three-style update. Backup:',backup)
    print('Launch when ready:',ROOT/'Test-SaberTrials-New-Styles.cmd')


def restore():
    LEGACY.stopped()
    fix=active_ui_fix()
    if fix:fix.restore()
    state=verify_installed(delegate=False)
    settings=LEGACY.settings_snapshot()
    LEGACY.restore_record(STATE,state)
    require(LEGACY.settings_snapshot()==settings,'User settings changed during restore; inspect before playing.')
    LEGACY.verify_installed(delegate=False)
    print('Restored the previous hybrid installation. The original rollback remains available.')


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
