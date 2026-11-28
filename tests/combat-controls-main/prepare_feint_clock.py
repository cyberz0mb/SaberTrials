"""Keep the regression's legacy random/time interaction literal production code."""
from pathlib import Path
import sys
candidate,out=map(Path,sys.argv[1:])
def function(path,signature):
    source=path.read_text();start=source.index(signature);opening=source.index('{',start)
    depth=1;end=opening+1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[start:end]
math=candidate/'engine/shared/qcommon/q_math.c'
parts=[function(math,'int Q_rand( int *seed )'),function(math,'float Q_random( int *seed )'),
       function(candidate/'game/codemp/game/bg_saber.c','int PM_irand_timesync(int val1, int val2)')]
out.mkdir(parents=True,exist_ok=True)
(out/'feint_clock_fixture.inc').write_text('\n'.join(parts)+'\n')
