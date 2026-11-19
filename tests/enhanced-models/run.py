"""Read-only archive inspection; extracts transient engine test inputs, not releases."""
import argparse
from pathlib import Path
import json
import struct
import subprocess
import time
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'dist/enhanced-models/validation'
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('archives',nargs='+',type=Path)
    args=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    checker=ROOT/'dist/enhanced-models/build-check/Release/st-glm-check.exe'
    fixture=OUT/'input.glm'
    rows=[]; seed=None
    start=time.perf_counter()
    def check(data,rend2=False):
        fixture.write_bytes(data)
        r=subprocess.run([checker,fixture]+(['--rend2'] if rend2 else []),capture_output=True,text=True)
        return r.returncode,r.stdout.strip()
    for archive in args.archives:
        with zipfile.ZipFile(archive) as z:
            for name in z.namelist():
                if not name.lower().endswith('.glm'): continue
                data=z.read(name); code,msg=check(data); gpu_code,gpu_msg=check(data,True)
                rows.append({'archive':archive.name,'name':name,'bytes':len(data),'exit':code,'result':msg,'rend2_exit':gpu_code,'rend2_result':gpu_msg})
                if code==0 and seed is None: seed=data
    mutations=[]
    if seed is None: raise RuntimeError('No valid fixture')
    def mutate(name,offset,value):
        data=bytearray(seed); struct.pack_into('<I',data,offset,value & 0xffffffff)
        code,msg=check(data); mutations.append({'name':name,'exit':code,'result':msg})
    u=lambda off:struct.unpack_from('<I',seed,off)[0]
    ns=u(152); lod=u(148); s=lod+4+ns*4; vo=s+u(s+16)
    for name,off,val in [('version',4,7),('size',160,0xffffffff),('surfaces',152,0xffffffff),
                         ('hierarchy',156,0xffffffff),('lod',148,0xffffffff),
                         ('surface span',s+36,0xffffffff),('vertex offset',s+16,0xffffffff),
                         ('vertex count',s+12,1000),('triangle count',s+20,2000),
                         ('triangle index',s+u(s+24),0xffffffff),
                         ('bone ref',s+u(s+32),u(140)),('nonfinite vertex',vo,0x7fc00000)]:
        mutate(name,off,val)
    for cut in (0,3,163,len(seed)-1):
        code,msg=check(seed[:cut]); mutations.append({'name':f'truncated {cut}','exit':code,'result':msg})
    fixture.unlink()
    report={'stock':rows,'malformed':mutations,'elapsed_seconds':time.perf_counter()-start}
    (OUT/'report.json').write_text(json.dumps(report,indent=2))
    failures=[r for r in rows if r['exit'] or r['rend2_exit']] + [r for r in mutations if r['exit']!=1]
    print(f'{len(rows)} stock GLMs; {len(mutations)} malformed fixtures; {len(failures)} failures')
    for row in failures: print(row)
    raise SystemExit(bool(failures))
if __name__=='__main__': main()
