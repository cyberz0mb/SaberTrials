"""Install only the verified Rend2 and game DLL fixes; never starts/stops a game."""
from pathlib import Path
import argparse,datetime,hashlib,importlib.util,json,subprocess,sys,uuid
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];FIX=ROOT/'dist/portrait-vote-fix'
PROOF=ROOT/'dist/verification/portrait-vote-20261024'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
    p=argparse.ArgumentParser();p.add_argument('--install',action='store_true');a=p.parse_args()
    state=ROOT/'dist/portrait-vote-install.json';assert not state.exists()
    m=read(FIX/'manifest.json');helper=module('baseline',ROOT/'tools/Prepare-Handedness-Baseline.py')
    for name,digest in m['inputs'].items():assert sha(ROOT/name)==digest,name
    assert sha(Path(m['baseline'])/'provenance.json')==m['baseline_sha256']
    for component in ('engine','game'):assert helper.tree(FIX/component)==m['sources'][component]
    before_test=read(PROOF/'before/evidence.json');test=read(PROOF/'after/evidence.json')
    assert not before_test['passed'] and test['passed'] and test['returncode']==0 and not test['map_or_server_started']
    for name,digest in test['source'].items():assert sha(FIX/name)==digest,name
    sources={'client/rd-rend2_x86_64.dll':FIX/'build-engine/Release/rd-rend2_x86_64.dll',
             'jampgamex86_64.dll':FIX/'build-game/Release/jampgamex86_64.dll'}
    assert sha(sources['client/rd-rend2_x86_64.dll'])==m['builds']['engine']['rd-rend2_x86_64.dll']
    assert sha(sources['jampgamex86_64.dll'])==m['builds']['game']['jampgamex86_64.dll']
    evidence={}
    for tag,renderer in [('native-simulation-720-r2','simulation'),('native-production-1080','production'),('native-vanilla-720','vanilla')]:
        folder=PROOF/tag;proof=read(folder/'evidence.json')
        assert proof['passed'] and proof['returncode']==0 and not proof['map_or_server_started'] and proof['renderer']==renderer
        assert proof['checker']==sha(ROOT/'tools/Check-Portrait-Viewport.py')
        assert proof['probe']==sha(ROOT/'tests/portrait-vote/portrait_qa.inc')
        for name,digest in proof['files'].items():assert sha(folder/name)==digest,name
        assert sha(folder/'bin/SaberTrials.x86_64.exe')==sha(ROOT/'client/SaberTrials.x86_64.exe')
        if renderer=='production':assert sha(folder/'bin/rd-rend2_x86_64.dll')==sha(sources['client/rd-rend2_x86_64.dll'])
        evidence[tag]=sha(folder/'evidence.json')
    current=read(ROOT/'dist/handedness-ingame-install.json');protected={**current['protected'],**current['after']}
    assert protected==m['protected']
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    for name,path in sources.items():
        data=path.read_bytes()
        for marker in (b'st_viewportqa',b'st_portraitviewportqa',b'st_handqa',b'st_lockqa'):assert marker not in data,name
    before={n:sha(ROOT/n) for n in sources};after={n:sha(path) for n,path in sources.items()}
    if not a.install:print('READY: two files verified; installed files unchanged.');return
    running=subprocess.check_output(['powershell','-NoProfile','-Command',
        "Get-Process -Name 'SaberTrials.x86_64','openjk.x86_64','openjkded.x86_64','taystjk.x86_64','taystjkded.x86_64','jamp','jampDed' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id; exit 0"],text=True)
    assert not running.strip(),'Close the game before installation'
    installer=module('transaction',ROOT/'tools/Install-Handedness.py')
    backup=ROOT/'dist/backups'/('portrait-vote-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
    payload={'installed':True,'before':before,'after':after,'backup':str(backup),
        'source_manifest':str(FIX/'manifest.json'),'source_manifest_sha256':sha(FIX/'manifest.json'),
        'native_evidence':evidence,'unit_evidence_sha256':sha(PROOF/'after/evidence.json'),
        'supersedes':str(ROOT/'dist/handedness-ingame-install.json'),
        'protected':{n:d for n,d in protected.items() if n not in sources},'live_server_tested':False}
    installer.install_transaction(ROOT,sources,before,after,protected,backup,state,payload)
    print('Installed only Rend2 portrait placement and gametype-vote fixes. Backup:',backup)
if __name__=='__main__':main()
