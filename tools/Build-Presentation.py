"""Build only UI and cgame. QA fixtures never enter production output."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,shutil,tempfile
ROOT=Path(__file__).resolve().parents[1]
WORK=Path(tempfile.gettempdir())/'SaberTrials-presentation-20261023'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sources():
    files=[]
    for folder in ['development-source/client-game','development-source/bot-roles/codemp/ui','development-source/bot-roles/codemp/game','development-source/client-overhaul/patches','development-source/bot-roles/patches']:
        files += [p for p in (ROOT/folder).rglob('*') if p.is_file()]
    return {p.relative_to(ROOT).as_posix():digest(p) for p in files}
def replace(s,a,b):
    assert s.count(a)==1, (a[:100],s.count(a));return s.replace(a,b)
def main():
    p=argparse.ArgumentParser();p.add_argument('--qa',action='store_true');a=p.parse_args()
    spec=importlib.util.spec_from_file_location('overhaul',ROOT/'tools/Build-Overhaul.py')
    h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    input_sources=sources()
    WORK.mkdir(parents=True,exist_ok=True)
    if not (WORK/'openjk.zip').exists():shutil.copy2(ROOT/'dist/staff-work/openjk.zip',WORK/'openjk.zip')
    h.WORK=WORK;h.SOURCE=WORK/('OpenJK-'+h.REVISION);source=h.prepare(a.qa)
    for overlay in ['bot-roles','client-game']:
        for sub in ['game','cgame']:
            src=ROOT/'development-source'/overlay/'codemp'/sub
            if src.exists():shutil.copytree(src,source/'codemp'/sub,dirs_exist_ok=True)
    if a.qa:
        path=source/'codemp/ui/ui_atoms.c';s=path.read_text()
        qa=(ROOT/'tests/menu_ui_qa.inc').read_text()
        qa=replace(qa,'if (!Q_stricmp(op, "state")) {','if (!Q_stricmp(op,"presentation")) { extern void ST_UISetPresentationFixture(const char*); ST_UISetPresentationFixture(UI_Argv(2));\n    } else if (!Q_stricmp(op, "state")) {')
        s=replace(s,'static void ST_ClientQA_f(void) {',qa+'\nstatic void ST_ClientQA_f(void) {\n if(ST_MenuQA())return;')
        path.write_text(s)
        path=source/'codemp/ui/ui_sabertrials_presentation.inc';s=path.read_text()
        s=replace(s,'static void ST_UIPresentation(void) {',(ROOT/'tests/presentation_ui_qa.inc').read_text()+'\nstatic void ST_UIPresentation(void) {')
        s=replace(s,'menuDef_t*menu=Menu_GetFocused();','menuDef_t*menu=Menu_GetFocused();\n if(ST_UIPresentationQA(menu))return;')
        path.write_text(s)
        path=source/'codemp/ui/ui_main.c';s=path.read_text()
        s=replace(s,'static int UI_FeederCount(float feederID)\n{','static int UI_FeederCount(float feederID)\n{\n if(feederID==FEEDER_SERVERS && ST_UIFixtureBrowser()) return 14;')
        mark='} else if (feederID == FEEDER_SERVERS) {\n\t\tif (index >= 0 && index < uiInfo.serverStatus.numDisplayServers) {'
        s=replace(s,mark,'} else if (feederID == FEEDER_SERVERS) {\n if(ST_UIFixtureBrowser()) return ST_UIFixtureServerText(index,column);\n\t\tif (index >= 0 && index < uiInfo.serverStatus.numDisplayServers) {')
        s=replace(s,'qboolean UI_FeederSelection(float feederFloat, int index, itemDef_t *item)\n{','qboolean UI_FeederSelection(float feederFloat, int index, itemDef_t *item)\n{\n if(feederFloat==FEEDER_SERVERS && ST_UIFixtureBrowser()){stpFixtureSelection=index;return qtrue;}')
        path.write_text(s)
    build=WORK/('build-qa' if a.qa else 'build');manifest=build/'Release/presentation-build.json';manifest.unlink(missing_ok=True)
    flags=['BuildMPEngine','BuildMPDed','BuildMPGame','BuildMPRdVanilla','BuildMPRend2','BuildSPEngine','BuildSPGame','BuildSPRdVanilla']
    h.run(['cmake','-S',str(source),'-B',str(build),'-G','Visual Studio 18 2026','-A','x64',*[f'-D{f}=OFF' for f in flags],'-DBuildMPCGame=ON','-DBuildMPUI=ON'])
    h.run(['cmake','--build',str(build),'--config','Release','--parallel','6'])
    assert sources()==input_sources,'Sources changed during build; rebuild from a stable input'
    manifest.write_text(json.dumps({'kind':'qa' if a.qa else 'production','revision':h.REVISION,'sources':input_sources,'files':{n:digest(build/'Release'/n) for n in ['uix86_64.dll','cgamex86_64.dll']}},indent=2)+'\n')
    print('Presentation build:',manifest)
if __name__=='__main__':main()
