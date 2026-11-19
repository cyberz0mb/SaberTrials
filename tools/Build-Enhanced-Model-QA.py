"""Build an isolated, cheat-gated cgame pose fixture. Never install or ship it."""
from pathlib import Path
import shutil,subprocess,json,hashlib
R=Path(__file__).resolve().parents[1];W=R/'dist/enhanced-model-qa';src=W/'frontend'
shutil.copytree(R/'dist/mvp-cinematic-candidate-03/frontend',src,dirs_exist_ok=True)
p=src/'codemp/cgame/cg_players.c';s=p.read_text()
anchor='qboolean CG_G2PlayerHeadAnims( centity_t *cent )'
assert s.count(anchor)==1
s=s.replace(anchor,'#include "st_model_qa.inc"\n\n'+anchor)
anchor='\tif ( cent->currentState.eFlags & EF_DEAD )\n\t{//Dead people close their eyes'
assert s.count(anchor)==1
s=s.replace(anchor,'\tif (ST_ModelQA(cent)) return qtrue;\n\n'+anchor)
p.write_text(s);shutil.copy2(R/'tests/enhanced-models/model_qa.inc',p.with_name('st_model_qa.inc'))
flags=('BuildMPEngine','BuildMPDed','BuildMPRdVanilla','BuildMPRend2','BuildMPGame','BuildMPCGame','BuildMPUI','BuildSPEngine','BuildSPGame','BuildSPRdVanilla')
with (W/'build.log').open('w') as f:
    subprocess.run(['cmake','-S',str(src),'-B',str(W/'build'),'-G','Visual Studio 18 2026','-A','x64',
        '-DST_DEPS='+str(R/'dist/handedness-baseline-06/deps'),'-DST_STAFF_QA=OFF']+['-D'+k+'='+('ON' if k=='BuildMPCGame' else 'OFF') for k in flags],stdout=f,stderr=subprocess.STDOUT,check=True)
    subprocess.run(['cmake','--build',str(W/'build'),'--config','Release','--parallel','6'],stdout=f,stderr=subprocess.STDOUT,check=True)
out=W/'build/Release/cgamex86_64.dll'
(W/'receipt.json').write_text(json.dumps({'fixture_only':True,'cgame_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'hook_sha256':hashlib.sha256(p.with_name('st_model_qa.inc').read_bytes()).hexdigest()},indent=2))
print('Built private model QA cgame; not installed.')
