"""Compile native compatibility checks; optionally read installed Akaza assets.

Only test fixtures/build products are written. No game/server is launched and no
installed PK3 or editable model source is modified.
"""
from pathlib import Path
import argparse
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--build',type=Path,default=ROOT/'dist/hybrid-model-tests')
    parser.add_argument('--installed-akaza',action='store_true')
    args=parser.parse_args()
    build=args.build.resolve(); build.mkdir(parents=True,exist_ok=True)
    configure=['cmake','-S',str(Path(__file__).parent),'-B',str(build),'-G','Visual Studio 18 2026','-A','x64']
    if args.installed_akaza:
        for package,member,filename,key in [
            (ROOT.parent/'base/akaza.pk3','models/players/_humanoid/akaza_face.gla','akaza-original.gla','ST_PRIVATE_GLA'),
            (ROOT/'zz_sabertrials_stances_v1.pk3','models/players/_humanoid/_humanoid.gla','canonical.gla','ST_CANONICAL_GLA')]:
            with zipfile.ZipFile(package) as archive:
                destination=build/filename; destination.write_bytes(archive.read(member))
            configure.append(f'-D{key}={destination}')
    subprocess.run(configure,check=True)
    subprocess.run(['cmake','--build',str(build),'--config','Release'],check=True)
    subprocess.run(['ctest','--test-dir',str(build),'-C','Release','--output-on-failure'],check=True)

if __name__=='__main__': main()
