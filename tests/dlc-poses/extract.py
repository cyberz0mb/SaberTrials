from pathlib import Path
import sys
source=Path(sys.argv[1]).read_text()
start=source.index('qboolean G2API_SetBoneAnim(')
end=source.index('qboolean G2API_GetBoneAnim(',start)
Path(sys.argv[2]).write_text(source[start:end])
