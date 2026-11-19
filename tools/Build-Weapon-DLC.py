"""Build additive weapons on the verified combined Windows game/client."""
from datetime import datetime
from importlib import import_module, util
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'dist/weapon-dlc-01'
SOURCE = ROOT/'development-source/weapon-dlc'
RECEIPT = OUT/'source-receipt.json'
BASES = {'game': ROOT/'dist/ui-hud-polish-01/game', 'frontend': ROOT/'dist/chat-ui-01/frontend'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    Path(path).write_text(json.dumps(data,indent=2)+'\n')


def tree(path):
    return {p.relative_to(path).as_posix():sha(p) for p in sorted(Path(path).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def overlay():
    spec=util.spec_from_file_location('weapon_dlc_overlay',SOURCE/'overlay.py')
    module=util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare():
    prior=read(ROOT/'dist/chat-panel-install.json')
    installed={**prior['protected'],**prior['after']}
    assert all(sha(ROOT/name)==digest for name,digest in installed.items()),'Installation changed'
    assert sha(ROOT/'dist/chat-ui-01/build-cgame/Release/cgamex86_64.dll')==installed['cgamex86_64.dll']
    assert sha(ROOT/'dist/ui-hud-polish-01/build-game/Release/jampgamex86_64.dll')==installed['jampgamex86_64.dll']
    OUT.mkdir(exist_ok=True)
    baseline={role:tree(path) for role,path in BASES.items()}
    for role,path in BASES.items():
        expected=read(path.parent/'source-receipt.json')['sources'][role]
        assert baseline[role]==expected,role+' baseline changed'
        shutil.copytree(path,OUT/role,dirs_exist_ok=True)
        overlay().apply(OUT/role,client=role=='frontend',server=role=='game')
    sources={role:tree(OUT/role) for role in BASES}
    write(RECEIPT,dict(installed=installed,baseline=baseline,sources=sources,authored=tree(SOURCE)))
    print('Prepared additive gun sources from the verified current game and chat client.',flush=True)


def build(role):
    assert role in ('game','frontend')
    receipt=read(RECEIPT)
    assert tree(OUT/role)==receipt['sources'][role]
    target='BuildMPCGame' if role=='frontend' else 'BuildMPGame'
    library='cgamex86_64' if role=='frontend' else 'jampgamex86_64'
    flags=('BuildMPEngine','BuildMPDed','BuildMPGame','BuildMPCGame','BuildMPUI','BuildMPRdVanilla',
           'BuildMPRend2','BuildSPEngine','BuildSPGame','BuildSPRdVanilla')
    with (OUT/f'build-{role}.log').open('w') as log:
        subprocess.run(['cmake','-S',str(OUT/role),'-B',str(OUT/f'build-{role}'),
            '-G','Visual Studio 18 2026','-A','x64','-DST_STAFF_QA=OFF',
            '-DST_DEPS='+str(ROOT/'dist/handedness-baseline-06/deps'),
            *[f'-D{flag}={"ON" if flag==target else "OFF"}' for flag in flags]],
            stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['cmake','--build',str(OUT/f'build-{role}'),'--config','Release',
            '--parallel','5','--target',library],stdout=log,stderr=subprocess.STDOUT,check=True)
    write(OUT/f'build-{role}.json',dict(source=sha(RECEIPT),sha256=sha(OUT/f'build-{role}/Release/{library}.dll')))
    print('Built '+role,flush=True)


def files():
    return {'jampgamex86_64.dll':OUT/'build-game/Release/jampgamex86_64.dll',
            'cgamex86_64.dll':OUT/'build-frontend/Release/cgamex86_64.dll'}


def validate():
    receipt=read(RECEIPT)
    assert tree(SOURCE)==receipt['authored'],'Authored source changed'
    hashes={name:sha(path) for name,path in files().items()}
    for role,library in (('game','jampgamex86_64.dll'),('frontend','cgamex86_64.dll')):
        assert tree(OUT/role)==receipt['sources'][role],role+' source changed'
        assert read(OUT/f'build-{role}.json')==dict(source=sha(RECEIPT),sha256=hashes[library])
    evidence={}
    for mode in ('families','network','rules','cheats_off','stock'):
        matching=[path for path in sorted(OUT.glob(mode+'-*/result.json'))
                  if read(path).get('source')==sha(RECEIPT) and read(path).get('files')==hashes]
        assert matching,'Run the current '+mode+' live check first'
        path=matching[-1]
        evidence[mode]=dict(path=str(path),sha256=sha(path))
    checks=[['ctest','--test-dir',str(OUT/'tests'),'-C','Release','--output-on-failure'],
            [sys.executable,'-m','unittest','discover','-s','tests','-p','test_weapon_pack.py','-v']]
    with (OUT/'validation-tests.log').open('w') as log:
        for command in checks:
            subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    write(OUT/'validation.json',dict(source=sha(RECEIPT),files=hashes,evidence=evidence,
        tests=sha(OUT/'validation-tests.log')))
    print('Validated current builds, all gun families, network fallback, ammo rules and stock cycling.')


def install():
    helper=import_module('Install-Profile-Browser')
    helper.stopped()
    home,settings=helper.settings()
    current=read(RECEIPT)['installed']
    assert all(sha(ROOT/name)==digest for name,digest in current.items())
    sources=files()
    assert not any((home/name).exists() for name in sources)
    evidence=read(OUT/'validation.json')
    assert evidence['source']==sha(RECEIPT)
    assert evidence['files']=={name:sha(path) for name,path in sources.items()}
    assert tree(SOURCE)==read(RECEIPT)['authored']
    assert all(sha(record['path'])==record['sha256'] for record in evidence['evidence'].values())
    before={name:current[name] for name in sources}
    after={name:sha(path) for name,path in sources.items()}
    protected={name:digest for name,digest in current.items() if name not in sources}
    backup=ROOT/'dist/backups'/f'weapon-dlc-{datetime.now():%Y%m%d-%H%M%S}'
    payload=dict(before=before,after=after,protected=protected,backup=str(backup),
        preserved_settings=settings,source_sha256=sha(RECEIPT),evidence=sha(OUT/'validation.json'))
    import_module('Install-Handedness').install_transaction(ROOT,sources,before,after,protected,
        backup,ROOT/'dist/weapon-dlc-install.json',payload)
    assert all(sha(Path(name))==digest for name,digest in settings.items())
    print('Installed additive weapon support; existing packages and settings preserved.')


if __name__=='__main__':
    if sys.argv[1]=='prepare': prepare()
    elif sys.argv[1]=='install': install()
    elif sys.argv[1]=='validate': validate()
    else: build(sys.argv[1])
