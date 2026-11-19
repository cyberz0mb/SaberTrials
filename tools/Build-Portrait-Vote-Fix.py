"""Build only Rend2 and game fixes over the verified installed handedness sources."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,shutil,subprocess,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'dist/handedness-baseline-06'
OUT=ROOT/'dist/portrait-vote-fix'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,data):p.write_text(json.dumps(data,indent=2)+'\n')
def inputs():
    names=['tools/Build-Portrait-Vote-Fix.py',
        'development-source/client-overhaul/patches/renderer-rend2-overlay-viewport.patch',
        'development-source/bot-roles/codemp/game/g_cmds.c',
        'development-source/bot-roles/codemp/game/g_sabertrials.c']
    return {n:sha(ROOT/n) for n in names}
def main():
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--build',choices=['engine','game']);a=p.parse_args()
    helper=load('baseline',ROOT/'tools/Prepare-Handedness-Baseline.py')
    extractor=load('regression',ROOT/'tests/portrait-vote/check.py')
    if a.prepare:
        assert not OUT.exists(),'Use a fresh output directory'
        accepted=read(ROOT/'dist/handedness-ingame-install.json')
        protected={**accepted['protected'],**accepted['after']}
        for n,h in protected.items():assert sha(ROOT/n)==h,n
        before=inputs();record=read(BASE/'provenance.json');OUT.mkdir()
        expected={};changes={}
        for component in ('engine','game'):
            source=BASE/component;target=OUT/component
            assert helper.tree(source)==record['components'][component]
            shutil.copytree(source,target)
            assert helper.tree(target)==record['components'][component]
            if component=='engine':
                patch=ROOT/'development-source/client-overhaul/patches/renderer-rend2-overlay-viewport.patch'
                subprocess.run(['git','apply','--directory='+str(target),'--unsafe-paths',str(patch)],check=True)
            else:
                for name,signature in [('g_cmds.c','qboolean G_VoteGametype('),('g_sabertrials.c','void ST_QueueGametype(')]:
                    rel='codemp/game/'+name;f=target/rel;text=f.read_text()
                    new=extractor.function((ROOT/'development-source/bot-roles'/rel).read_text(),signature)
                    old=extractor.function(text,signature)
                    assert text.count(old)==1
                    f.write_text(text.replace(old,new),encoding='utf-8',newline='\n')
            expected[component]=helper.tree(target)
            changes[component]=[n for n,h in expected[component].items() if record['components'][component].get(n)!=h]
        assert changes=={'engine':['codemp/rd-rend2/tr_main.cpp'],'game':['codemp/game/g_cmds.c','codemp/game/g_sabertrials.c']},changes
        assert before==inputs()
        write(OUT/'manifest.json',{'installed':False,'baseline':str(BASE),'baseline_sha256':sha(BASE/'provenance.json'),
            'inputs':before,'sources':expected,'changes':changes,'protected':protected,'builds':{}})
        print('Prepared three-file fix from verified installed sources.');return
    assert a.build
    m=read(OUT/'manifest.json');assert inputs()==m['inputs']
    component=a.build;source=OUT/component
    assert helper.tree(source)==m['sources'][component]
    build=OUT/('build-'+component)
    enabled='BuildMPRend2' if component=='engine' else 'BuildMPGame'
    subprocess.run(['cmake','-S',str(source),'-B',str(build),'-G','Visual Studio 18 2026','-A','x64',
        '-DST_DEPS='+str(BASE/'deps'), '-DST_STAFF_QA=OFF',
        *[f'-D{flag}={"ON" if flag==enabled else "OFF"}' for flag in helper.FLAGS]],check=True)
    target='rd-rend2_x86_64' if component=='engine' else 'jampgamex86_64'
    subprocess.run(['cmake','--build',str(build),'--config','Release','--target',target,'--parallel','6'],check=True)
    assert helper.tree(source)==m['sources'][component] and inputs()==m['inputs']
    name='rd-rend2_x86_64.dll' if component=='engine' else 'jampgamex86_64.dll'
    # Read again so independent component builds can finish safely in either order.
    m=read(OUT/'manifest.json');m['builds'][component]={name:sha(build/'Release'/name)};write(OUT/'manifest.json',m)
    print('Built',name)
if __name__=='__main__':main()
