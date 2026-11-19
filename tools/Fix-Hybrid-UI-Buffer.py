"""Install only the verified UI animation-buffer correction. Never launch the game."""
from pathlib import Path
import argparse
import datetime
import importlib.util
import sys
import uuid

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
CANDIDATE=ROOT/'dist/hybrid-ui-buffer-fix'
STATE=ROOT/'dist/hybrid-ui-buffer-install.json'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

UPDATE=load('hybrid_loadout_base',ROOT/'tools/Update-Hybrid-Styles.py')
LEGACY=UPDATE.LEGACY
TX=UPDATE.TX
sha=LEGACY.sha
read=LEGACY.read
require=LEGACY.require


def verify_candidate(check_inputs=True,expected_manifest_sha=None):
    manifest=CANDIDATE/'manifest.json'
    if expected_manifest_sha is not None:
        require(sha(manifest)==expected_manifest_sha,'UI correction manifest changed')
    m=read(manifest)
    parent_manifest=UPDATE.CANDIDATE/'manifest.json'
    require(sha(parent_manifest)==m['parent_manifest_sha256'],'UI correction parent manifest changed')
    parent=read(parent_manifest)
    require(LEGACY.tree(CANDIDATE/'source')==m['sources'],'UI correction source drift')
    before=parent['sources']['frontend'];after=m['sources']
    changed={name for name in set(before)|set(after) if before.get(name)!=after.get(name)}
    require(changed=={'codemp/ui/ui_main.c'},'Correction may change only the UI animation buffer')
    original=(UPDATE.CANDIDATE/'frontend/codemp/ui/ui_main.c').read_bytes()
    require(original.count(b'UIPAFtext[60000]')==1,'Unexpected original UI animation buffer')
    require((CANDIDATE/'source/codemp/ui/ui_main.c').read_bytes()==original.replace(b'UIPAFtext[60000]',b'UIPAFtext[131072]',1),
            'Correction may change only the UI animation buffer')
    require(set(m['builds'])=={'uix86_64.dll'},'UI correction must contain only the matching UI build')
    require(sha(CANDIDATE/'build/Release/uix86_64.dll')==m['builds']['uix86_64.dll'],'UI correction binary drift')
    if check_inputs:
        require(bool(m['inputs']),'Missing UI correction build provenance')
        for name,digest in m['inputs'].items():
            require(sha(TX.child(ROOT,name))==digest,'UI correction build input changed: '+name)
    return m


def active_feedback():
    path=ROOT/'dist/hybrid-feedback-install.json'
    if not path.exists():return None
    state=read(path)
    if state.get('installed') and not state.get('restored'):
        return load('hybrid_feedback_update',ROOT/'tools/Update-Hybrid-Feedback.py')
    return None


def verify_recorded_fix():
    state=read(STATE)
    require(state.get('installed') and not state.get('restored'),'UI buffer correction has been restored')
    require(sha(UPDATE.STATE)==state['previous_receipt_sha256'],'Three-style receipt changed')
    UPDATE.verify_recorded_update()
    m=verify_candidate(False,state['source_manifest_sha256'])
    require(state['after']=={'uix86_64.dll':m['builds']['uix86_64.dll']},'Unexpected UI correction file set')
    backup=Path(state['backup']).resolve()
    require(backup.is_relative_to((ROOT/'dist/backups').resolve()),'Unexpected UI correction backup location')
    for name,digest in state['before'].items():
        require(digest is not None and sha(TX.child(backup,name))==digest,'UI correction backup differs: '+name)
    return state


def verify_installed(delegate=True):
    latest=active_feedback() if delegate else None
    if latest:return latest.verify_installed()
    state=verify_recorded_fix()
    for name,digest in {**state['protected'],**state['after']}.items():
        require(sha(TX.child(ROOT,name))==digest,'UI correction/protected file differs: '+name)
    print('UI buffer correction, preserved files and all rollback layers verified.')
    return state


def install(commit=False):
    require(not STATE.exists(),'UI correction receipt already exists; use --verify or --restore.')
    LEGACY.stopped()
    previous=UPDATE.verify_installed(delegate=False)
    m=verify_candidate()
    sources={'uix86_64.dll':CANDIDATE/'build/Release/uix86_64.dll'}
    before={'uix86_64.dll':sha(ROOT/'uix86_64.dll')}
    after={'uix86_64.dll':m['builds']['uix86_64.dll']}
    require(before['uix86_64.dll'] is not None,'Missing current matching UI')
    protected={**previous['protected'],**previous['after']}
    protected['dist/hybrid-loadout-install.json']=sha(UPDATE.STATE)
    settings=LEGACY.settings_snapshot()
    payload=dict(installed=True,restored=False,layer='ui-animation-buffer',before=before,after=after,
        sources={k:str(v) for k,v in sources.items()},
        protected={k:v for k,v in protected.items() if k not in sources},preserved_settings=settings,
        source_manifest=str(CANDIDATE/'manifest.json'),source_manifest_sha256=sha(CANDIDATE/'manifest.json'),
        previous_receipt=str(UPDATE.STATE),previous_receipt_sha256=sha(UPDATE.STATE),
        game_launched=False,live_acceptance=False)
    if not commit:
        print('Ready: one UI DLL correction. Installed files and settings unchanged.');return
    LEGACY.stopped()
    backup=ROOT/'dist/backups'/('hybrid-ui-buffer-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
    payload['backup']=str(backup)
    TX.install_transaction(ROOT,sources,before,after,protected,backup,STATE,payload)
    require(LEGACY.settings_snapshot()==settings,'User settings changed during UI correction; inspect before playing.')
    verify_installed()
    print('Installed UI animation-buffer correction. Backup:',backup)


def restore():
    LEGACY.stopped()
    latest=active_feedback()
    if latest:latest.restore()
    state=verify_installed(delegate=False)
    settings=LEGACY.settings_snapshot()
    LEGACY.restore_record(STATE,state)
    require(LEGACY.settings_snapshot()==settings,'User settings changed during UI restore; inspect before playing.')
    UPDATE.verify_installed(delegate=False)
    print('Restored the previous UI DLL. The three-style update remains installed.')


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
