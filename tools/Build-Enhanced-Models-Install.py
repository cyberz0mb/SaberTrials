"""Compose independent Map and Model overlays for the currently installed client.

Builds only; never installs. The installed map/game module is verified and kept.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,re,shutil,subprocess
R=Path(__file__).resolve().parents[1];O=R/'dist/enhanced-model-install';B=R/'dist/mvp-cinematic-candidate-03'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def overlay(name):
    p=R/'development-source'/name/'overlay.py'
    spec=importlib.util.spec_from_file_location(name.replace('-','_'),p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepare-only',action='store_true')
    targets=parser.add_mutually_exclusive_group();targets.add_argument('--client-runtime-only',action='store_true');targets.add_argument('--vanilla-policy-only',action='store_true');args=parser.parse_args()
    targeted_update=None
    maps=read(R/'dist/enhanced-maps/engine-build.json');installed=read(R/'dist/enhanced-maps-install.json')
    assert maps['engine_checkpoint_manifest']==sha(B/'manifest.json')
    for n,h in maps['inputs'].items():assert sha(R/'development-source/enhanced-maps'/n)==h,('map source drift',n)
    for n,h in installed['after'].items():assert sha(R/n)==h,('installed baseline drift',n)
    receipt=read(B/'manifest.json')
    for n,h in receipt['sources']['engine'].items():assert sha(B/'engine'/n)==h,('checkpoint drift',n)
    if args.client_runtime_only or args.vanilla_policy_only:
        previous=read(O/'build.json')
        for group,files in previous['inputs'].items():
            if group=='client-runtime' and args.client_runtime_only:continue
            for n,h in files.items():
                if args.vanilla_policy_only and group=='enhanced-models' and n=='st_cosmetic_render.inc':continue
                assert sha(R/'development-source'/group/n)==h,('source drift',group,n)
        for n,h in previous['binaries'].items():assert sha(O/'build/Release'/n)==h
        if args.vanilla_policy_only:
            target=O/'engine/codemp/rd-common/st_cosmetic_render.inc';source=R/'development-source/enhanced-models/st_cosmetic_render.inc'
            old=target.read_text();new=source.read_text()
            branch=re.search(r'// ST_VANILLA_COMPAT_BEGIN\n#ifndef ST_COSMETIC_REND2\n.*?\n#endif\n// ST_VANILLA_COMPAT_END\n',new,re.S)
            assert branch and new[:branch.start()]+new[branch.end():]==old,'Update changes Rend2-visible source'
            targeted_update={'kind':'Vanilla compatibility policy only','rend2_preprocessor_equivalent':True,'source_before_sha256':sha(target),'source_after_sha256':sha(source),'preserved_binaries':{n:h for n,h in previous['binaries'].items() if n!='rd-vanilla_x86_64.dll'}}
            shutil.copy2(source,target)
    else:
        shutil.copytree(B/'engine',O/'engine',dirs_exist_ok=True)
        overlay('enhanced-maps').apply(O/'engine');overlay('enhanced-models').apply(O/'engine')
    if not args.vanilla_policy_only:overlay('client-runtime').apply(O/'engine')
    if args.prepare_only:return
    options=('BuildMPEngine','BuildMPDed','BuildMPRdVanilla','BuildMPRend2','BuildMPGame','BuildMPCGame','BuildMPUI','BuildSPEngine','BuildSPGame','BuildSPRdVanilla')
    enabled=set(options[:4])
    with (O/'build.log').open('w') as f:
        subprocess.run(['cmake','-S',str(O/'engine'),'-B',str(O/'build'),'-G','Visual Studio 18 2026','-A','x64',
            '-DST_DEPS='+str(R/'dist/handedness-baseline-06/deps'),'-DST_STAFF_QA=OFF',
            '-DCMAKE_SHARED_LINKER_FLAGS_RELEASE=/INCREMENTAL:NO /MAP']+['-D'+k+'='+('ON' if k in enabled else 'OFF') for k in options],stdout=f,stderr=subprocess.STDOUT,check=True)
        target_args=['--target','rd-vanilla_x86_64'] if args.vanilla_policy_only else (['--target','openjk.x86_64'] if args.client_runtime_only else [])
        subprocess.run(['cmake','--build',str(O/'build'),'--config','Release','--parallel','8']+target_args,stdout=f,stderr=subprocess.STDOUT,check=True)
    result={'installed_map_baseline':installed['after'],'checkpoint':sha(B/'manifest.json'),
      'binaries':{n:sha(O/'build/Release'/n) for n in ('openjk.x86_64.exe','openjkded.x86_64.exe','rd-vanilla_x86_64.dll','rd-rend2_x86_64.dll')},
      'inputs':{group:{p.name:sha(p) for p in (R/'development-source'/group).iterdir() if p.is_file()} for group in ('enhanced-maps','enhanced-models','client-runtime')},
      'protected_modules':{n:sha(R/n) for n in ('cgamex86_64.dll','jampgamex86_64.dll','uix86_64.dll')},'installed':False}
    if targeted_update:
        for n,h in targeted_update['preserved_binaries'].items():assert result['binaries'][n]==h,('Unexpected rebuilt binary',n)
        result['targeted_update']=targeted_update
    (O/'build.json').write_text(json.dumps(result,indent=2));print('Combined Map + Model engine built; not installed.')
if __name__=='__main__':main()
