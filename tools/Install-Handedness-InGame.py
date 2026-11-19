"""Install the verified pause-menu-only correction, with a one-file backup."""
from pathlib import Path
import argparse,datetime,hashlib,importlib.util,json,re,sys,uuid
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--install',action='store_true');a=parser.parse_args()
    state=ROOT/'dist/handedness-ingame-install.json';assert not state.exists()
    stage=ROOT/'dist/handedness-ingame-staging';manifest=read(stage/'manifest.json')
    name='ui/jamp/ingame_saber.menu';source=stage/name;target=ROOT/name
    for n,d in manifest['inputs'].items():assert sha(ROOT/n)==d,n
    assert sha(source)==manifest['files'][name]
    run=ROOT/'dist/verification/handedness-20261024/ingame-hand-03';proof=read(run/'evidence.json')
    assert proof['passed'] and proof['returncodes']==[0,0] and not proof['map_or_server_started']
    assert proof['checker_sha256']==sha(ROOT/'tools/Check-Handedness-InGame.py')
    assert proof['staged_menu_sha256']==sha(source)
    for n,d in {**proof['files'],**proof['logs']}.items():assert sha(run/n)==d,n
    expected,count=re.subn(r'(?im)^(\s*fullscreen\s+)0\b',r'\g<1>1',source.read_text(),count=1)
    assert count==1 and expected==(run/'home/SaberTrials'/name).read_text()
    qa=read(ROOT/'dist/handedness-baseline-06/qa/qa-manifest.json')
    assert sha(run/'bin/SaberTrials.x86_64.exe')==sha(ROOT/'client/SaberTrials.x86_64.exe')
    assert sha(run/'bin/rd-vanilla_x86_64.dll')==sha(ROOT/'client/rd-vanilla_x86_64.dll')
    assert sha(run/'home/SaberTrials/uix86_64.dll')==qa['files']['uix86_64.dll']
    accepted=read(ROOT/'dist/handedness-install.json')
    protected={**accepted['protected'],**accepted['after']}
    for n,d in protected.items():assert sha(ROOT/n)==d,n
    before={name:sha(target)};after={name:sha(source)}
    if not a.install:
        print('READY: pause-menu selector verified; no installed changes.');return
    spec=importlib.util.spec_from_file_location('hand_install',ROOT/'tools/Install-Handedness.py')
    installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
    backup=ROOT/'dist/backups'/('handedness-ingame-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
    payload={'installed':True,'before':before,'after':after,'backup':str(backup),
        'evidence':str(run),'evidence_sha256':sha(run/'evidence.json'),
        'supersedes_protected_entry':name,'previous_manifest_sha256':sha(ROOT/'dist/handedness-install.json'),
        'protected':{n:d for n,d in protected.items() if n!=name}}
    installer.install_transaction(ROOT,{name:source},before,after,protected,backup,state,payload)
    print('Installed pause-menu Right/Left selector; no binaries or settings changed.')

if __name__=='__main__':main()
