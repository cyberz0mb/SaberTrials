"""Copy only local animation fixtures to ignored verification storage; never change base."""
from pathlib import Path
import zipfile,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'dist/verification/handedness-20261024/assets';out.mkdir(parents=True,exist_ok=True)
manifest={}
for name in ('assets1','japlus_gla_anims'):
    source=ROOT.parent/'base'/f'{name}.pk3'
    with zipfile.ZipFile(source) as z:data=z.read('models/players/_humanoid/_humanoid.gla')
    (out/f'{name}.gla').write_bytes(data)
    manifest[name]={'source':str(source),'gla_sha256':hashlib.sha256(data).hexdigest(),'size':len(data)}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(out)
