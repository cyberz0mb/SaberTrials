"""Extract production functions instead of reimplementing selection in tests."""
from pathlib import Path
import argparse,json,math
from check_candidate import function
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);a=p.parse_args();out=a.candidate.resolve()
folder=out/'test-fixtures';folder.mkdir(exist_ok=True)
code=[]
for name,signatures in [('bg_pmove.c',['static int PM_GetStockSaberStance(void)','int PM_GetSaberStance(void)']),
                        ('bg_panimate.c',['qboolean BG_SaberStanceAnim( int anim )','qboolean BG_InSaberStandAnim( int anim )'])]:
 text=(out/'game/codemp/game'/name).read_text()
 code.extend(function(text,s) for s in signatures)
(folder/'candidate_functions.inc').write_text('\n\n'.join(code)+'\n')
library=json.loads((out/'assets/library.json').read_text());fixture=['static void fill_animation_fixture(animation_t* a) {']
for row in library['stances']:
 name=row['animation']
 for key,value in [('firstFrame',row['frame']),('numFrames',row['count']),('frameLerp',math.ceil(1000/row['fps'])),('loopFrames',row['loop'])]:
  fixture.append(f' a[{name}].{key}={value};')
fixture.append('}')
(folder/'candidate_animation_fixture.inc').write_text('\n'.join(fixture)+'\n');print('Extracted actual candidate selection and readiness functions.')
