"""Build Photo Mode engine/cgame/UI from the pinned source and current overlays."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, shutil, tempfile

ROOT = Path(__file__).resolve().parent.parent
WORK = Path.home()/'AppData/Local/Temp/SaberTrials-photo-20261012'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--qa',action='store_true')
    p.add_argument('--incremental',action='store_true')
    args=p.parse_args()
    spec=importlib.util.spec_from_file_location('overhaul',ROOT/'tools/Build-Overhaul.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    WORK.mkdir(parents=True,exist_ok=True)
    if not (WORK/'openjk.zip').exists():
        cache=helper.WORK/'openjk.zip'
        if not cache.exists():cache=Path.home()/'AppData/Local/Temp/SaberTrials-overhaul-20261003/openjk.zip'
        if cache.exists():shutil.copy2(cache,WORK/'openjk.zip')
    helper.WORK=WORK;helper.SOURCE=WORK/('OpenJK-'+helper.REVISION)
    source=helper.prepare(args.qa)
    for overlay in ['bot-roles','client-game']:
        for sub in ['game','cgame']:
            folder=ROOT/'development-source'/overlay/'codemp'/sub
            if folder.exists():shutil.copytree(folder,source/'codemp'/sub,dirs_exist_ok=True)
    if args.qa:
        atoms=source/'codemp/ui/ui_atoms.c';s=atoms.read_text()
        s=s.replace('static void ST_ClientQA_f(void) {',(ROOT/'tests/menu_ui_qa.inc').read_text()+'\nstatic void ST_ClientQA_f(void) {\n if (ST_MenuQA()) return;')
        atoms.write_text(s)
        view=source/'codemp/cgame/cg_view.c'
        view.write_text(view.read_text()+'\n'+(ROOT/'tests/photo_client_qa.inc').read_text())
        cc=source/'codemp/cgame/cg_consolecmds.c';s=cc.read_text()
        marker='static consoleCommand_t\tcommands[] = {'
        assert marker in s
        cc.write_text(s.replace(marker,'extern void ST_PhotoQA_f(void);\n'+marker+'\n { "st_photoqa", ST_PhotoQA_f },'))
        engine=source/'codemp/client/cl_main.cpp';s=engine.read_text()
        marker='static void ST_EngineQA_f( void ) {'
        s=s.replace(marker,(ROOT/'tests/photo_engine_qa.inc').read_text()+'\n'+marker+'\n if (ST_PhotoEngineQA()) return;')
        engine.write_text(s)
    build=WORK/('build-qa' if args.qa else 'build')
    manifest=build/'Release/photo-build-manifest.json';manifest.unlink(missing_ok=True)
    configure=['cmake','-S',str(source),'-B',str(build),'-G','Visual Studio 18 2026','-A','x64']
    for flag in ['BuildMPDed','BuildMPGame','BuildMPRdVanilla','BuildMPRend2','BuildSPEngine','BuildSPGame','BuildSPRdVanilla']:
        configure+=['-D'+flag+'=OFF']
    helper.run(configure+['-DBuildMPEngine=ON','-DBuildMPCGame=ON','-DBuildMPUI=ON'])
    cmd=['cmake','--build',str(build),'--config','Release','--parallel','6']
    if not args.incremental:cmd+=['--clean-first']
    helper.run(cmd)
    record={'kind':'qa' if args.qa else 'production','revision':helper.REVISION,'files':{}}
    for name in ['openjk.x86_64.exe','cgamex86_64.dll','uix86_64.dll']:
        record['files'][name]=hashlib.sha256((build/'Release'/name).read_bytes()).hexdigest()
    manifest.write_text(json.dumps(record,indent=2)+'\n')
    print('Photo build:',manifest)

if __name__=='__main__':main()
