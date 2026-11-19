"""Build DLC animation compatibility on the verified installed combined source."""
from datetime import datetime
from importlib import import_module,util
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/dlc-pose-01';SOURCE=ROOT/'development-source/dlc-poses';RECEIPT=OUT/'source-receipt.json'
BASES={'engine':ROOT/'dist/translator-02/engine','frontend':ROOT/'dist/translator-02/frontend','game':ROOT/'dist/bot-chat-01/game'}
ROLES={'game':('game','BuildMPGame','jampgamex86_64','jampgamex86_64.dll'),
       'cgame':('frontend','BuildMPCGame','cgamex86_64','cgamex86_64.dll'),
       'ui':('frontend','BuildMPUI','uix86_64','uix86_64.dll'),
       'vanilla':('engine','BuildMPRdVanilla','rd-vanilla_x86_64','client/rd-vanilla_x86_64.dll'),
       'rend2':('engine','BuildMPRend2','rd-rend2_x86_64','client/rd-rend2_x86_64.dll'),
       'dedicated':('engine','BuildMPDed','openjkded.x86_64','client/openjkded.x86_64.exe')}
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,data):Path(path).write_text(json.dumps(data,indent=2)+'\n')
def tree(path):return {p.relative_to(path).as_posix():sha(p) for p in sorted(Path(path).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
def binary(role):return OUT/('build-'+role)/'Release'/(ROLES[role][2]+('.exe' if role=='dedicated' else '.dll'))
def files():return {v[3]:binary(role) for role,v in ROLES.items()}
def prepare():
    previous=read(RECEIPT) if RECEIPT.exists() else None
    previous_sha=sha(RECEIPT) if previous else None
    prior=read(ROOT/'dist/bot-chat-install.json');current={**prior['protected'],**prior['after']}
    assert all(sha(ROOT/n)==h for n,h in current.items())
    spec=util.spec_from_file_location('dlc_pose_overlay',SOURCE/'overlay.py');overlay=util.module_from_spec(spec);spec.loader.exec_module(overlay)
    baselines={}
    for role,path in BASES.items():
        expected=read(path.parent/'source-receipt.json')['sources']
        if role!='game':expected=expected[role]
        baselines[role]=tree(path);assert baselines[role]==expected,role+' source drift'
        shutil.copytree(path,OUT/role,dirs_exist_ok=True);overlay.apply(OUT/role,role)
    # Source receipts must also correspond to the actual installed binaries.
    checks={'jampgamex86_64.dll':ROOT/'dist/bot-chat-01/build/Release/jampgamex86_64.dll',
            'cgamex86_64.dll':ROOT/'dist/translator-02/build-cgame/Release/cgamex86_64.dll',
            'uix86_64.dll':ROOT/'dist/translator-02/build-ui/Release/uix86_64.dll',
            'client/rd-vanilla_x86_64.dll':ROOT/'dist/translator-02/build-vanilla/Release/rd-vanilla_x86_64.dll',
            'client/rd-rend2_x86_64.dll':ROOT/'dist/translator-02/build-rend2/Release/rd-rend2_x86_64.dll'}
    assert all(sha(p)==current[n] for n,p in checks.items())
    write(RECEIPT,dict(installed=current,baseline=baselines,sources={r:tree(OUT/r) for r in BASES},authored=tree(SOURCE)))
    # A changed client source need not rebuild unchanged renderer/game trees.
    # Carry a binary only when its complete source tree and build hash agree.
    if previous:
        for role,(source,_,_,_) in ROLES.items():
            record=OUT/f'build-{role}.json'
            if record.exists() and binary(role).exists() and previous['sources'][source]==read(RECEIPT)['sources'][source]:
                if read(record)==dict(source=previous_sha,sha256=sha(binary(role))):
                    write(record,dict(source=sha(RECEIPT),sha256=sha(binary(role))))
    print('Prepared compatible DLC poses on the latest installed game.',flush=True)
def build(role):
    source,target,library,_=ROLES[role];assert tree(OUT/source)==read(RECEIPT)['sources'][source]
    flags=('BuildMPEngine','BuildMPDed','BuildMPGame','BuildMPCGame','BuildMPUI','BuildMPRdVanilla','BuildMPRend2','BuildSPEngine','BuildSPGame','BuildSPRdVanilla')
    with (OUT/f'build-{role}.log').open('w') as log:
        subprocess.run(['cmake','-S',str(OUT/source),'-B',str(OUT/f'build-{role}'),'-G','Visual Studio 18 2026','-A','x64',
            '-DST_STAFF_QA=OFF','-DST_DEPS='+str(ROOT/'dist/handedness-baseline-06/deps'),
            *[f'-D{f}={"ON" if f==target else "OFF"}' for f in flags]],stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['cmake','--build',str(OUT/f'build-{role}'),'--config','Release','--parallel','5','--target',library],stdout=log,stderr=subprocess.STDOUT,check=True)
    write(OUT/f'build-{role}.json',dict(source=sha(RECEIPT),sha256=sha(binary(role))))
    print('Built '+role,flush=True)
def validate():
    receipt=read(RECEIPT);source=sha(RECEIPT);hashes={n:sha(p) for n,p in files().items()}
    assert tree(SOURCE)==receipt['authored'] and all(tree(OUT/r)==receipt['sources'][r] for r in BASES)
    assert all(read(OUT/f'build-{r}.json')==dict(source=source,sha256=sha(binary(r))) for r in ROLES)
    fixtures=read(OUT/'fixtures/receipt.json')
    for name,item in fixtures.items():
        assert sha(item['package'])==item['package_sha256'] and sha(OUT/'fixtures'/item.get('file',f'{name}.gla'))==item['sha256']
    evidence={}
    review=read(OUT/'visual-review.json');assert review['source']==source
    assert all(sha(OUT/n)==h for n,h in review['images'].items())
    evidence['visual-review.json']=sha(OUT/'visual-review.json')
    for renderer in ('vanilla','rend2'):
        candidates=[p for p in sorted(OUT.glob(f'runtime-{renderer}-*/result.json'))
                    if read(p)['source']==source and read(p)['full']]
        assert candidates,'Missing full live '+renderer+' validation'
        p=candidates[-1];result=read(p);assert len(result['cases'])==43
        expected={n:h for n,h in hashes.items() if n in ('jampgamex86_64.dll','cgamex86_64.dll','uix86_64.dll','client/rd-'+renderer+'_x86_64.dll')}
        expected['client/SaberTrials.x86_64.exe']=receipt['installed']['client/SaberTrials.x86_64.exe']
        assert result['files']==expected
        log=p.parent/'home/SaberTrials/qconsole.log'
        assert sha(log)==result['log'] and 'ERROR:' not in log.read_text(errors='replace')
        assert 'added compatible stance frames to models/players/_humanoid/alien_mkx.gla in memory.' in log.read_text(errors='replace')
        for i,case in enumerate(result['cases']):
            assert (p.parent/'home/SaberTrials/screenshots'/f"pose-{i}-{case['model']}.png").exists()
        evidence[p.relative_to(OUT).as_posix()]=sha(p)
    candidates=[p for p in sorted(OUT.glob('network-*/result.json')) if read(p)['source']==source]
    assert candidates,'Missing dedicated server/client validation'
    p=candidates[-1];result=read(p);assert len(result['cases'])==8
    names={'server/jampgamex86_64.dll':'jampgamex86_64.dll','server/openjkded.x86_64.exe':'client/openjkded.x86_64.exe',
           'client/cgamex86_64.dll':'cgamex86_64.dll','client/uix86_64.dll':'uix86_64.dll',
           'client/rd-vanilla_x86_64.dll':'client/rd-vanilla_x86_64.dll'}
    expected={n:hashes[v] for n,v in names.items()}
    expected['client/SaberTrials.x86_64.exe']=receipt['installed']['client/SaberTrials.x86_64.exe']
    assert result['files']==expected
    for role,h in result['logs'].items():assert sha(p.parent/role/'home/SaberTrials/qconsole.log')==h
    evidence[p.relative_to(OUT).as_posix()]=sha(p)
    with (OUT/'native-tests.log').open('w') as log:
        subprocess.run(['cmake','-S',str(ROOT/'tests/dlc-poses'),'-B',str(OUT/'tests'),
            '-DST_ENGINE:PATH='+str(OUT/'engine'),'-DST_POSE_HEADERS:PATH='+str(OUT/'engine/codemp/ghoul2')],
            check=True,stdout=log,stderr=subprocess.STDOUT)
        subprocess.run(['cmake','--build',str(OUT/'tests'),'--config','Release','--parallel','4'],check=True,stdout=log,stderr=subprocess.STDOUT)
        subprocess.run(['ctest','--test-dir',str(OUT/'tests'),'-C','Release','--output-on-failure'],check=True,stdout=log,stderr=subprocess.STDOUT)
    evidence['native-tests.log']=sha(OUT/'native-tests.log')
    assert '100% tests passed out of 13' in (OUT/'native-tests.log').read_text()
    write(OUT/'validation.json',dict(source=source,files=hashes,evidence=evidence,fixtures=sha(OUT/'fixtures/receipt.json'),
        tests=tree(ROOT/'tests/dlc-poses'),tools={p.name:sha(p) for p in (ROOT/'tools').glob('*DLC-Poses*.py')}))
    print('Validated 13 native checks, 86 renderer cases and 8 dedicated server/client cases.',flush=True)

def install():
    helper=import_module('Install-Profile-Browser');helper.stopped();home,settings=helper.settings()
    receipt=read(RECEIPT);current=receipt['installed'];sources=files()
    assert tree(SOURCE)==receipt['authored'] and all(tree(OUT/r)==receipt['sources'][r] for r in BASES)
    assert all(sha(ROOT/n)==h for n,h in current.items())
    assert all(not (home/n).exists() for n in sources)
    validation=read(OUT/'validation.json');assert validation['source']==sha(RECEIPT)
    assert validation['files']=={n:sha(p) for n,p in sources.items()}
    assert all(sha(OUT/n)==h for n,h in validation['evidence'].items())
    assert validation['tests']==tree(ROOT/'tests/dlc-poses')
    assert validation['tools']=={p.name:sha(p) for p in (ROOT/'tools').glob('*DLC-Poses*.py')}
    assert validation['fixtures']==sha(OUT/'fixtures/receipt.json')
    assert all(sha(v['package'])==v['package_sha256'] for v in read(OUT/'fixtures/receipt.json').values())
    assert all(read(OUT/f'build-{r}.json')==dict(source=sha(RECEIPT),sha256=sha(binary(r))) for r in ROLES)
    before={n:current[n] for n in sources};after={n:sha(p) for n,p in sources.items()};protected={n:h for n,h in current.items() if n not in sources}
    backup=ROOT/'dist/backups'/f'dlc-poses-{datetime.now():%Y%m%d-%H%M%S}'
    payload=dict(before=before,after=after,protected=protected,backup=str(backup),preserved_settings=settings,
        source_sha256=sha(RECEIPT),evidence=sha(OUT/'validation.json'))
    import_module('Install-Handedness').install_transaction(ROOT,sources,before,after,protected,backup,ROOT/'dist/dlc-pose-install.json',payload)
    assert all(sha(n)==h for n,h in settings.items())
    print('Installed DLC pose compatibility; model packages and saved settings preserved.',flush=True)

def verify():
    receipt=read(ROOT/'dist/dlc-pose-install.json');allfiles={**receipt['protected'],**receipt['after']}
    assert all(sha(ROOT/n)==h for n,h in allfiles.items())
    assert all(sha(n)==h for n,h in receipt['preserved_settings'].items())
    assert receipt['source_sha256']==sha(RECEIPT) and receipt['evidence']==sha(OUT/'validation.json')
    assert all(sha(v['package'])==v['package_sha256'] for v in read(OUT/'fixtures/receipt.json').values())
    evidence={}
    for renderer in ('vanilla','rend2'):
        candidates=[p for p in sorted(OUT.glob(f'installed-{renderer}-*/result.json'))
                    if read(p)['source']==sha(RECEIPT) and read(p)['installed']]
        assert candidates,'Missing installed '+renderer+' smoke'
        p=candidates[-1];result=read(p);assert len(result['cases'])>=9
        assert all(allfiles[n]==h for n,h in result['files'].items())
        assert sha(p.parent/'home/SaberTrials/qconsole.log')==result['log']
        evidence[p.relative_to(OUT).as_posix()]=sha(p)
    write(OUT/'installed-verification.json',dict(source=sha(RECEIPT),receipt=sha(ROOT/'dist/dlc-pose-install.json'),
        verified_files=len(allfiles),preserved_settings=len(receipt['preserved_settings']),evidence=evidence,
        model_packages_unchanged=True))
    print(f'Installed verification passed: {len(allfiles)} files, {len(receipt["preserved_settings"])} settings files, both renderer smokes.',flush=True)

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='validate':validate()
    elif sys.argv[1]=='install':install()
    elif sys.argv[1]=='verify':verify()
    else:build(sys.argv[1])
