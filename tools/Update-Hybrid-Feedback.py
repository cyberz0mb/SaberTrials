"""Install the matching player-feedback build with a verified reversible backup."""
from pathlib import Path
import argparse
import datetime
import importlib.util
import sys
import uuid

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT/'dist/hybrid-candidate-03'
STATE = ROOT/'dist/hybrid-feedback-install.json'
STAGING = ROOT/'dist/hybrid-feedback-install-staging'

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

PREVIOUS = load('feedback_previous_fix', ROOT/'tools/Fix-Hybrid-UI-Buffer.py')
LEGACY, TX = PREVIOUS.LEGACY, PREVIOUS.TX
sha, read, require = LEGACY.sha, LEGACY.read, LEGACY.require

def stage():
    sources = {
        'client/SaberTrials.x86_64.exe': CANDIDATE/'build-engine/Release/openjk.x86_64.exe',
        'client/openjkded.x86_64.exe': CANDIDATE/'build-engine/Release/openjkded.x86_64.exe',
        'client/rd-vanilla_x86_64.dll': CANDIDATE/'build-engine/Release/rd-vanilla_x86_64.dll',
        'client/rd-rend2_x86_64.dll': CANDIDATE/'build-engine/Release/rd-rend2_x86_64.dll',
        'jampgamex86_64.dll': CANDIDATE/'build-game/Release/jampgamex86_64.dll',
        'cgamex86_64.dll': CANDIDATE/'build-frontend/Release/cgamex86_64.dll',
        'uix86_64.dll': CANDIDATE/'build-frontend/Release/uix86_64.dll',
        'ui/jamp/saber.menu': CANDIDATE/'menus/ui/jamp/saber.menu',
        'ui/jamp/ingame_saber.menu': CANDIDATE/'menus/ui/jamp/ingame_saber.menu',
        'zz_sabertrials_styles_v1.pk3': CANDIDATE/'assets/zz_sabertrials_styles_v1.pk3',
    }
    require(sha(ROOT/'zz_sabertrials_stances_v1.pk3')==sha(CANDIDATE/'assets/zz_sabertrials_stances_v1.pk3'),
            'Matching installed stance library required')
    STAGING.mkdir(parents=True, exist_ok=True)
    restore = '@echo off\nsetlocal\n"'+str(Path(sys.executable).resolve())+'" "%~dp0tools\\Update-Hybrid-Feedback.py" --restore\nif errorlevel 1 pause\nendlocal\n'
    command = STAGING/'Restore-SaberTrials-Before-Style-Feedback.cmd'
    command.write_text(restore, encoding='ascii', newline='\r\n')
    sources[command.name] = command
    return sources

def verify_installed():
    state = read(STATE)
    require(state.get('installed') and not state.get('restored'), 'Feedback update has been restored')
    require(sha(PREVIOUS.STATE)==state['previous_receipt_sha256'], 'Previous UI correction receipt changed')
    PREVIOUS.verify_recorded_fix()
    LEGACY.verify_recorded_candidate(state)
    backup = Path(state['backup']).resolve()
    require(backup.is_relative_to((ROOT/'dist/backups').resolve()), 'Unexpected feedback backup path')
    for name, digest in state['before'].items():
        if digest is not None:
            require(sha(TX.child(backup, name))==digest, 'Feedback backup differs: '+name)
    for name, digest in {**state['protected'], **state['after']}.items():
        require(sha(TX.child(ROOT, name))==digest, 'Feedback/protected file differs: '+name)
    print('Feedback update, preserved files and all rollback layers verified.')
    return state

def install(commit=False):
    require(not STATE.exists(), 'Feedback receipt exists; use --verify or --restore.')
    LEGACY.stopped()
    previous = PREVIOUS.verify_installed(delegate=False)
    builder = load('feedback_builder', ROOT/'tools/Build-Hybrid-Feedback.py')
    require(builder.OUT.resolve()==CANDIDATE.resolve(), 'Wrong candidate path')
    manifest = builder.verify()
    require(set(manifest['builds'])=={'engine','game','frontend'}, 'Incomplete matching build')
    sources = stage()
    settings = LEGACY.settings_snapshot()
    protected = {**previous['protected'], **previous['after']}
    protected['dist/hybrid-ui-buffer-install.json'] = sha(PREVIOUS.STATE)
    protected.update({p.relative_to(ROOT).as_posix():sha(p) for p in ROOT.glob('*.cfg') if p.is_file()})
    before = {name:sha(TX.child(ROOT,name)) for name in sources}
    after = {name:sha(source) for name,source in sources.items()}
    require(all(after.values()), 'Missing build source')
    payload = dict(installed=True, restored=False, before=before, after=after,
        sources={k:str(v) for k,v in sources.items()},
        protected={k:v for k,v in protected.items() if k not in sources},
        preserved_settings=settings, source_manifest=str(CANDIDATE/'manifest.json'),
        source_manifest_sha256=sha(CANDIDATE/'manifest.json'),
        previous_receipt=str(PREVIOUS.STATE), previous_receipt_sha256=sha(PREVIOUS.STATE),
        game_launched=False, live_acceptance=False)
    LEGACY.verify_recorded_candidate(payload)
    if not commit:
        print('Ready:',len(sources),'matching feedback files. Installation and settings unchanged.'); return
    LEGACY.stopped()
    backup = ROOT/'dist/backups'/('hybrid-feedback-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
    payload['backup'] = str(backup)
    TX.install_transaction(ROOT,sources,before,after,protected,backup,STATE,payload)
    require(LEGACY.settings_snapshot()==settings, 'User settings changed; inspect before playing')
    verify_installed()
    print('Installed feedback update. Backup:',backup)

def restore():
    LEGACY.stopped()
    state = verify_installed()
    settings = LEGACY.settings_snapshot()
    LEGACY.restore_record(STATE,state)
    require(LEGACY.settings_snapshot()==settings, 'User settings changed during restore')
    PREVIOUS.verify_installed(delegate=False)
    print('Restored the previous three-style build and UI buffer fix.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--install',action='store_true')
    group.add_argument('--verify',action='store_true')
    group.add_argument('--restore',action='store_true')
    args=parser.parse_args()
    if args.verify: verify_installed()
    elif args.restore: restore()
    else: install(args.install)
