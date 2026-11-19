"""Build the hud cgame and matching UI from pinned OpenJK plus source overlays."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, shutil, tempfile

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(tempfile.gettempdir())/'SaberTrials-hud-20261006'

def module(name, file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qa',action='store_true')
    args=parser.parse_args()
    helper=module('overhaul','Build-Overhaul.py')
    WORK.mkdir(parents=True,exist_ok=True)
    if not (WORK/'openjk.zip').exists() and (helper.WORK/'openjk.zip').exists():
        shutil.copy2(helper.WORK/'openjk.zip',WORK/'openjk.zip')
    helper.WORK=WORK;helper.SOURCE=WORK/('OpenJK-'+helper.REVISION)
    source=helper.prepare(args.qa)
    shutil.copy2(ROOT/'development-source/bot-roles/codemp/ui/ui_sabertrials_hud.inc',source/'codemp/ui/ui_sabertrials_hud.inc')
    for overlay in ['bot-roles','client-game']:
        # UI has patches applied by prepare; only copy the gameplay overlays here.
        for sub in ['game','cgame']:
            p=ROOT/'development-source'/overlay/'codemp'/sub
            if p.exists():shutil.copytree(p,source/'codemp'/sub,dirs_exist_ok=True)
    if args.qa:
        p=source/'codemp/ui/ui_atoms.c';s=p.read_text()
        s=s.replace('static void ST_ClientQA_f(void) {',(ROOT/'tests/menu_ui_qa.inc').read_text()+'\nstatic void ST_ClientQA_f(void) {\n    if (ST_MenuQA()) return;')
        p.write_text(s)
        p=source/'codemp/cgame/cg_draw.c'
        p.write_text(p.read_text()+'\n'+(ROOT/'tests/portrait_client_qa.inc').read_text()+'\n'+(ROOT/'tests/hud_client_qa.inc').read_text())
        p=source/'codemp/cgame/cg_consolecmds.c';s=p.read_text()
        marker='static consoleCommand_t\tcommands[] = {'
        assert marker in s
        s=s.replace(marker,'extern void ST_HudQA_f(void);\nextern void ST_PortraitQA_f(void);\n'+marker+'\n { "st_hudqa", ST_HudQA_f }, { "st_portraitqa", ST_PortraitQA_f },')
        p.write_text(s)
    build=WORK/('build-qa' if args.qa else 'build')
    manifest=build/'Release/hud-build-manifest.json';manifest.unlink(missing_ok=True)
    configure=['cmake','-S',str(source),'-B',str(build),'-G','Visual Studio 18 2026','-A','x64']
    for flag in ['BuildMPEngine','BuildMPDed','BuildMPGame','BuildMPRdVanilla','BuildMPRend2','BuildSPEngine','BuildSPGame','BuildSPRdVanilla']:
        configure+=['-D'+flag+'=OFF']
    helper.run(configure+['-DBuildMPCGame=ON','-DBuildMPUI=ON'])
    helper.run(['cmake','--build',str(build),'--config','Release','--clean-first','--parallel','6'])
    record={'kind':'qa' if args.qa else 'production','revision':helper.REVISION,'files':{}}
    for name in ['cgamex86_64.dll','uix86_64.dll']:
        record['files'][name]=hashlib.sha256((build/'Release'/name).read_bytes()).hexdigest()
    manifest.write_text(json.dumps(record,indent=2)+'\n')
    print('Hud build:',manifest)

if __name__=='__main__':main()
