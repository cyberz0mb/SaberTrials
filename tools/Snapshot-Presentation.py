"""Capture immutable inputs for the approved presentation pass (no credentials)."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'dist/presentation-input'
assert not DEST.exists(), 'Presentation input snapshot already exists'
paths=[]
for folder in ['ui','development-source/client-game','development-source/bot-roles/codemp/ui','development-source/client-overhaul/patches']:
    paths += [p for p in (ROOT/folder).rglob('*') if p.is_file()]
paths += [p for name in ['uix86_64.dll','cgamex86_64.dll','jampgamex86_64.dll','client/SaberTrials.x86_64.exe','st-tournament-preview-*.cfg'] for p in ROOT.glob(name)]
manifest={}
for p in paths:
    key=p.relative_to(ROOT).as_posix(); target=DEST/key;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(p,target);manifest[key]=hashlib.sha256(p.read_bytes()).hexdigest()
(DEST/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Snapshotted',len(manifest),'presentation inputs and protected binaries')
