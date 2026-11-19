"""Build only the pinned native UI; never rebuild accepted combat modules."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import tempfile

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(tempfile.gettempdir()) / 'SaberTrials-menu-20261006'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qa', action='store_true')
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('overhaul', ROOT/'tools/Build-Overhaul.py')
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    WORK.mkdir(exist_ok=True)
    archive = WORK/'openjk.zip'
    if not archive.exists() and (helper.WORK/'openjk.zip').exists():
        shutil.copy2(helper.WORK/'openjk.zip', archive)
    helper.WORK = WORK
    helper.SOURCE = WORK/('OpenJK-'+helper.REVISION)
    source = helper.prepare(args.qa)
    if args.qa:
        atoms = source/'codemp/ui/ui_atoms.c'
        text = atoms.read_text()
        extra = (ROOT/'tests/menu_ui_qa.inc').read_text()
        text = text.replace('static void ST_ClientQA_f(void) {', extra+'\nstatic void ST_ClientQA_f(void) {\n    if (ST_MenuQA()) return;')
        atoms.write_text(text)
    build = WORK/('build-qa' if args.qa else 'build')
    output = build/'Release'
    manifest_path = output/'menu-build-manifest.json'
    manifest_path.unlink(missing_ok=True)
    configure = ['cmake','-S',str(source),'-B',str(build),'-G','Visual Studio 18 2026','-A','x64']
    for name in ('BuildMPDed','BuildMPGame','BuildMPCGame','BuildMPRdVanilla','BuildMPRend2',
                 'BuildSPEngine','BuildSPGame','BuildSPRdVanilla','BuildMPEngine'):
        configure.append('-D'+name+'=OFF')
    helper.run(configure+['-DBuildMPUI=ON'])
    helper.run(['cmake','--build',str(build),'--config','Release','--clean-first','--parallel','6'])
    manifest = {'kind':'qa' if args.qa else 'production','source_revision':helper.REVISION,
                'files':{'uix86_64.dll':hashlib.sha256((output/'uix86_64.dll').read_bytes()).hexdigest()}}
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    print('Built native menu UI:', output)

if __name__ == '__main__': main()
