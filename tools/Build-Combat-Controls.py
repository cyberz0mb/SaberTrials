"""Integrate approved combat on the verified current engine and multi-team modules."""
from pathlib import Path
from importlib import import_module, util
import argparse, hashlib, json, shutil, subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/combat-controls-01'
BASE={'engine':ROOT/'dist/anti-script/engine','game':ROOT/'dist/multiteam-01/game','frontend':ROOT/'dist/multiteam-01/frontend'}
FLAGS=('BuildMPEngine','BuildMPDed','BuildMPGame','BuildMPCGame','BuildMPUI','BuildMPRdVanilla','BuildMPRend2','BuildMPRdVulkan','BuildSPEngine','BuildSPGame','BuildSPRdVanilla')
TARGETS={'engine':{'BuildMPEngine':'openjk.x86_64','BuildMPDed':'openjkded.x86_64'},'game':{'BuildMPGame':'jampgamex86_64'},'frontend':{'BuildMPCGame':'cgamex86_64','BuildMPUI':'uix86_64'}}
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).is_file() else None
def write(p,v): Path(p).write_text(json.dumps(v,indent=2)+'\n')
def files():
    return {'client/SaberTrials.x86_64.exe':OUT/'build-engine/Release/openjk.x86_64.exe',
            'client/openjkded.x86_64.exe':OUT/'build-engine/Release/openjkded.x86_64.exe',
            'jampgamex86_64.dll':OUT/'build-game/Release/jampgamex86_64.dll',
            'cgamex86_64.dll':OUT/'build-frontend/Release/cgamex86_64.dll',
            'uix86_64.dll':OUT/'build-frontend/Release/uix86_64.dll',
            'z_sabertrials_combat_controls.pk3':OUT/'z_sabertrials_combat_controls.pk3'}
def prepare():
    assert not (OUT/'prepared.json').exists(),'Use build for the prepared candidate'
    multi=json.loads((ROOT/'dist/multiteam-install.json').read_text())
    anti=json.loads((ROOT/'dist/anti-script-install-20261119-174231.json').read_text())
    for name in files():
        if name.endswith('.pk3'):continue
        receipt=anti if name.startswith('client/') else multi
        assert sha(ROOT/name)==receipt['after'][name], 'Installed baseline changed: '+name
        binary=ROOT/'dist/anti-script/build/Release'/('openjk.x86_64.exe' if 'SaberTrials.x' in name else 'openjkded.x86_64.exe') if name.startswith('client/') else ROOT/multi['built_from'][name]
        assert sha(binary)==sha(ROOT/name),'Baseline build differs: '+name
    OUT.mkdir(exist_ok=True)
    spec=util.spec_from_file_location('main_combat_overlay',ROOT/'development-source/combat-controls/overlay.py')
    overlay=util.module_from_spec(spec);spec.loader.exec_module(overlay)
    contract=overlay.assets(OUT)
    for role,base in BASE.items():
        shutil.copytree(base,OUT/role,dirs_exist_ok=True)
        overlay.apply(OUT/role,role,contract)
    protected={}
    for path in [*ROOT.glob('*.pk3'),*ROOT.glob('*.dll'),*(ROOT/'client').glob('*'),*(ROOT/'ui').rglob('*.menu'),ROOT/'tools/launchers/SaberTrials.cmd']:
        name=path.relative_to(ROOT).as_posix()
        if path.is_file() and name not in files(): protected[name]=sha(path)
    write(OUT/'prepared.json',dict(before={n:sha(ROOT/n) for n in files()},protected=protected,contract=contract,
        sources={role:{p.relative_to(OUT/role).as_posix():sha(p) for p in (OUT/role).rglob('*') if p.is_file()} for role in BASE}))
    print('Prepared current main integration.',flush=True)
def build(role):
    record=json.loads((OUT/'prepared.json').read_text())
    assert all(sha(OUT/role/n)==h for n,h in record['sources'][role].items()),'Prepared source drift: '+role
    with (OUT/('build-'+role+'.log')).open('w') as log:
        subprocess.run(['cmake','-S',OUT/role,'-B',OUT/('build-'+role),'-G','Visual Studio 18 2026','-A','x64',
            '-DST_DEPS='+str(ROOT/'dist/handedness-baseline-06/deps'),'-DST_STAFF_QA=OFF',
            *[f'-D{f}={"ON" if f in TARGETS[role] else "OFF"}' for f in FLAGS]],check=True,stdout=log,stderr=subprocess.STDOUT)
        subprocess.run(['cmake','--build',OUT/('build-'+role),'--config','Release','--parallel','5',
            '--target',*TARGETS[role].values()],check=True,stdout=log,stderr=subprocess.STDOUT)
    print(role+' built.',flush=True)
def refresh_controls():
    record=json.loads((OUT/'prepared.json').read_text())
    for role in ('engine','frontend'):
        name='codemp/ui/st_controls_catalog.h'
        assert sha(OUT/role/name)==record['sources'][role][name]
        shutil.copyfile(ROOT/'development-source/controls/st_controls_catalog.h',OUT/role/name)
        record['sources'][role][name]=sha(OUT/role/name)
    write(OUT/'prepared.json',record)
def refresh_sync(operation='compact_sync'):
    record=json.loads((OUT/'prepared.json').read_text())
    spec=util.spec_from_file_location('main_combat_overlay',ROOT/'development-source/combat-controls/overlay.py')
    overlay=util.module_from_spec(spec);spec.loader.exec_module(overlay)
    for role in BASE:
        assert all(sha(OUT/role/n)==h for n,h in record['sources'][role].items()),'Source drift'
        getattr(overlay,operation)(OUT/role,role)
        record['sources'][role]={p.relative_to(OUT/role).as_posix():sha(p) for p in (OUT/role).rglob('*') if p.is_file()}
    write(OUT/'prepared.json',record)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','engine','game','frontend','all','controls','sync','protocol'))
    a=p.parse_args().action
    if a in ('prepare','all'):prepare()
    if a=='controls':refresh_controls()
    if a=='sync':refresh_sync()
    if a=='protocol':refresh_sync('protocol')
    if a=='all':
        for role in BASE:build(role)
    elif a in BASE:build(a)
