"""Build translation on the installed combined client; preserve gameplay and assets."""
from datetime import datetime
from importlib import import_module, util
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/translator-02'
SOURCE=ROOT/'development-source/translator'
RECEIPT=OUT/'source-receipt.json'
BASES={'engine':ROOT/'dist/chat-ui-01/engine','frontend':ROOT/'dist/weapon-dlc-01/frontend'}
ROLES={'engine':('engine','BuildMPEngine','openjk.x86_64','client/SaberTrials.x86_64.exe'),
       'cgame':('frontend','BuildMPCGame','cgamex86_64','cgamex86_64.dll'),
       'ui':('frontend','BuildMPUI','uix86_64','uix86_64.dll'),
       'qa':('frontend','BuildMPUI','uix86_64','uix86_64.dll'),
       'vanilla':('engine','BuildMPRdVanilla','rd-vanilla_x86_64','client/rd-vanilla_x86_64.dll'),
       'rend2':('engine','BuildMPRend2','rd-rend2_x86_64','client/rd-rend2_x86_64.dll')}


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf8'))
def write(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')
def tree(path):return {p.relative_to(path).as_posix():sha(p) for p in sorted(Path(path).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
def binary(role):return OUT/('build-'+role)/'Release'/(ROLES[role][2]+Path(ROLES[role][3]).suffix)
def load_overlay():
    spec=util.spec_from_file_location('translator_overlay',SOURCE/'overlay.py');m=util.module_from_spec(spec);spec.loader.exec_module(m);return m


def prepare(checkpoint=None):
    installed={}
    bases=BASES if checkpoint is None else {role:Path(checkpoint)/role for role in BASES}
    if checkpoint is None:
        prior=read(ROOT/'dist/translator-install.json');installed={**prior['protected'],**prior['after']}
        assert all(sha(ROOT/name)==digest for name,digest in installed.items()),'Current installation changed'
    OUT.mkdir(exist_ok=True)
    for role,path in bases.items():
        if checkpoint is None:
            assert tree(path)==read(path.parent/'source-receipt.json')['sources'][role],role+' source drift'
        else:
            expected=read(ROOT/'development-source/windows-checkpoint/manifest.json')['roles'][role]
            baseline=tree(path)
            assert len(baseline)==expected['file_count'] and hashlib.sha256(json.dumps(baseline,sort_keys=True,separators=(',',':')).encode('ascii')).hexdigest()==expected['tree_sha256']
        shutil.copytree(path,OUT/role,dirs_exist_ok=True)
        load_overlay().apply(OUT/role,engine=role=='engine')
    write(RECEIPT,dict(installed=installed,sources={role:tree(OUT/role) for role in BASES},authored=tree(SOURCE),
                       catalogue=sha(ROOT/'development-source/setup/st_setup_catalog.h')))
    print('Prepared translation sources on the verified November 12 baseline.',flush=True)


def build(role):
    source,target,library,_=ROLES[role]
    assert tree(OUT/source)==read(RECEIPT)['sources'][source]
    flags=('BuildMPEngine','BuildMPDed','BuildMPGame','BuildMPCGame','BuildMPUI','BuildMPRdVanilla','BuildMPRend2','BuildSPEngine','BuildSPGame','BuildSPRdVanilla')
    with (OUT/f'build-{role}.log').open('w') as log:
        subprocess.run(['cmake','-S',str(OUT/source),'-B',str(OUT/f'build-{role}'),'-G','Visual Studio 18 2026','-A','x64',
            '-DST_STAFF_QA=OFF','-DST_DEPS='+os.environ.get('ST_DEPS',str(ROOT/'dist/handedness-baseline-06/deps')),
            '-DCMAKE_CXX_FLAGS='+('/DST_CONTROLS_QA' if role in ('qa','engine-qa') else ''),
            *[f'-D{f}={"ON" if f==target else "OFF"}' for f in flags]],stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['cmake','--build',str(OUT/f'build-{role}'),'--config','Release','--parallel','5','--target',library],
                       stdout=log,stderr=subprocess.STDOUT,check=True)
    write(OUT/f'build-{role}.json',dict(source=sha(RECEIPT),sha256=sha(binary(role))))
    print('Built '+role,flush=True)


def files(qa=False):
    return {ROLES[role][3]:binary(role) for role in ('engine','cgame','qa' if qa else 'ui','vanilla','rend2')}


def validate():
    receipt=read(RECEIPT)
    assert tree(SOURCE)==receipt['authored'],'Authored translation source changed'
    assert sha(ROOT/'development-source/setup/st_setup_catalog.h')==receipt['catalogue']
    assert all(tree(OUT/role)==receipt['sources'][role] for role in BASES)
    for role in ROLES:
        assert read(OUT/f'build-{role}.json')==dict(source=sha(RECEIPT),sha256=sha(binary(role)))
    runtime=read(OUT/'runtime-receipt.json')
    assert tree(OUT/'runtime')==runtime['files']
    assert runtime['dependencies']==sha(SOURCE/'dependencies.json')
    assert sha(SOURCE/'worker.py')==runtime['files']['worker.py']
    assert tree(SOURCE/'terms')==tree(OUT/'runtime/terms')
    assert all(marker not in binary('ui').read_bytes() for marker in (b'st_setupqa',b'st_controlsqa',b'ST_PROFILE_FAIL'))
    evidence={}
    for mode in ('chat','settings','missing_pack','missing_helper','languages','network'):
        hashes={name:sha(path) for name,path in files(mode=='settings').items()}
        matching=[path for path in sorted(OUT.glob(mode+'-*/result.json'))
            if (read(path).get('proof_version')==2 or mode=='network') and read(path).get('source')==sha(RECEIPT) and read(path).get('files')==hashes and
            read(path).get('runtime')==runtime['files']['worker.py']]
        assert matching,'Run current '+mode+' live check first'
        selected=[matching[-1]]
        if mode=='languages':
            selected=[]
            for renderer in ('rd-vanilla','rd-rend2'):
                choices=[p for p in matching if read(p).get('renderer')==renderer]
                assert choices,'Run languages with '+renderer
                selected.append(choices[-1])
        for path in selected:
            record=read(path)
            if mode=='network':
                assert record['server']==sha(ROOT/'jampgamex86_64.dll')
                for name,player in record['results'].items():
                    assert sha(path.parent/name/'home/SaberTrials/qconsole.log')==player['log']
                    for binary_name,digest in hashes.items():
                        staged=path.parent/name/(binary_name if binary_name.startswith('client/') else 'home/SaberTrials/'+binary_name)
                        assert sha(staged)==digest,'Actual staged binary differs from the network receipt'
                    assert sha(path.parent/name/'client/translator/worker.py')==runtime['files']['worker.py']
            else:assert sha(path.parent/'home/SaberTrials/qconsole.log')==record['log']
            evidence[mode+('-'+record['renderer'] if mode=='languages' else '')]=dict(path=str(path),sha256=sha(path))
    benchmark=read(OUT/'benchmark.json')
    assert benchmark['worker']==runtime['files']['worker.py'] and benchmark['dependencies']==runtime['dependencies']
    assert benchmark['peak_commit_bytes']<4096*1024*1024
    languages=read(OUT/'language-results.json')
    assert languages['worker']==runtime['files']['worker.py'] and len(languages['results'])==39
    with (OUT/'validation-tests.log').open('w') as log:
        for command in ([str(OUT/'runtime/python.exe'),'-B','tests/test_translator.py','-v'],
                        ['cmake','--build',str(OUT/'tests'),'--config','Release'],
                        ['ctest','--test-dir',str(OUT/'tests'),'-C','Release','--output-on-failure']):
            subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    write(OUT/'validation.json',dict(source=sha(RECEIPT),files={name:sha(path) for name,path in files().items()},
        runtime=sha(OUT/'runtime-receipt.json'),benchmark=sha(OUT/'benchmark.json'),evidence=evidence,
        tests=sha(OUT/'validation-tests.log')))
    print('Validated all language pairs, Unicode, both renderers, channel audiences, settings and fallbacks.')


def install():
    helper=import_module('Install-Profile-Browser');helper.stopped()
    home,settings=helper.settings()
    current=read(RECEIPT)['installed']
    assert current,'Checkpoint builds are staged; installation needs a verified installed baseline'
    assert all(sha(ROOT/name)==digest for name,digest in current.items()),'Installed baseline changed'
    sources=files()
    assert not any((home/name).exists() for name in sources),'Home folder module override'
    evidence=read(OUT/'validation.json')
    assert evidence['source']==sha(RECEIPT) and evidence['runtime']==sha(OUT/'runtime-receipt.json')
    assert evidence['files']=={name:sha(path) for name,path in sources.items()}
    assert evidence['benchmark']==sha(OUT/'benchmark.json')
    assert tree(SOURCE)==read(RECEIPT)['authored']
    assert all(sha(record['path'])==record['sha256'] for record in evidence['evidence'].values())
    runtime=read(OUT/'runtime-receipt.json')['files'];assert tree(OUT/'runtime')==runtime
    assert (ROOT/'client/translator').is_dir(),'Previous translator runtime missing'
    sources.update({'client/translator/'+name:OUT/'runtime'/name for name in runtime})
    before={name:sha(ROOT/name) if (ROOT/name).is_file() else None for name in sources}
    after={name:sha(path) for name,path in sources.items()}
    protected={name:digest for name,digest in current.items() if name not in sources}
    backup=ROOT/'dist/backups'/f'translator-{datetime.now():%Y%m%d-%H%M%S}'
    payload=dict(before=before,after=after,protected=protected,backup=str(backup),preserved_settings=settings,
        source_sha256=sha(RECEIPT),evidence=sha(OUT/'validation.json'),gameplay_unchanged=True)
    for name in sources:(ROOT/name).parent.mkdir(parents=True,exist_ok=True)
    import_module('Install-Handedness').install_transaction(ROOT,sources,before,after,protected,
        backup,ROOT/'dist/translator-02-install.json',payload)
    assert all(sha(Path(name))==digest for name,digest in settings.items())
    # Keep the canonical receipt on the latest combined install; the accepted
    # first-version receipt is preserved under translator-02/accepted-install.json.
    shutil.copyfile(ROOT/'dist/translator-02-install.json',ROOT/'dist/translator-install.json')
    print('Installed multilingual public, team and private chat; gameplay and settings preserved.')


if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare(sys.argv[2] if len(sys.argv)>2 else None)
    elif sys.argv[1]=='validate':validate()
    elif sys.argv[1]=='install':install()
    else:build(sys.argv[1])
