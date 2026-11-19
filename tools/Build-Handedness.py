"""Build the handedness candidate in isolation. Never installs or launches a server."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, shutil, subprocess
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'dist/handedness-work'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--prepare-only',action='store_true')
    p.add_argument('--preview',action='store_true');a=p.parse_args()
    WORK.mkdir(parents=True,exist_ok=True)
    if not (WORK/'openjk.zip').exists():shutil.copy2(ROOT/'dist/staff-work/openjk.zip',WORK/'openjk.zip')
    staff=load('staff',ROOT/'tools/Build-Staff.py')
    def inputs():
        paths=[ROOT/'tools/Build-Handedness.py']
        for folder in ('development-source/handedness','tests/handedness'):
            paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
        return {**staff.input_hashes(),**{p.relative_to(ROOT).as_posix():digest(p) for p in paths}}
    before=inputs()
    source=staff.prepare(False,work=WORK)
    feature=load('handedness',ROOT/'development-source/handedness/prepare.py')
    feature.apply(source)
    if a.preview:
        renderer_include=source/'codemp/ghoul2/st_lock_renderer.inc'
        renderer_include.write_text('#define ST_LOCK_DIAGNOSTICS 1\n'+renderer_include.read_text())
        feature.change(source,'codemp/ui/ui_atoms.c','typedef struct consoleCommand_s {',
                       (ROOT/'tests/handedness/ui_qa.inc').read_text()+'\n'+(ROOT/'tests/handedness/lock_qa.inc').read_text()+'\ntypedef struct consoleCommand_s {')
        feature.change(source,'codemp/ui/ui_atoms.c','static consoleCommand_t\tcommands[] = {',
                       'static consoleCommand_t\tcommands[] = {\n {"st_handqa",ST_HandQA_f},\n {"st_lockqa",ST_LockQA_f},')
        feature.change(source,'codemp/ui/ui_main.c','\t\tST_UIPresentation();',
                       '\t\tST_UIPresentation();\n\t\t{ extern void ST_LockQAPaint(void); ST_LockQAPaint(); }')
    if a.prepare_only:print(source);return
    build=ROOT/('dist/handedness-preview-build' if a.preview else 'dist/handedness-build')
    manifest=build/'build-kind.json';manifest.unlink(missing_ok=True)
    flags={k:False for k in ('BuildMPEngine','BuildMPDed','BuildMPGame','BuildMPCGame','BuildMPUI','BuildMPRdVanilla','BuildMPRend2','BuildSPEngine','BuildSPGame','BuildSPRdVanilla')}
    for k in ('BuildMPEngine','BuildMPUI','BuildMPRdVanilla'):flags[k]=True
    if not a.preview:
        for k in ('BuildMPEngine','BuildMPDed','BuildMPGame','BuildMPCGame','BuildMPRend2'):flags[k]=True
    subprocess.run(['cmake','-S',str(source),'-B',str(build),'-G','Visual Studio 18 2026','-A','x64',*[f'-D{k}={"ON" if v else "OFF"}' for k,v in flags.items()]],check=True)
    subprocess.run(['cmake','--build',str(build),'--config','Release','--parallel','6'],check=True)
    if before!=inputs():raise RuntimeError('Source changed during build; candidate must be rebuilt')
    outputs={p.name:digest(p) for p in (build/'Release').iterdir() if p.suffix.lower() in ('.dll','.exe')}
    manifest.write_text(json.dumps({'kind':'candidate-not-installed','preview_only':a.preview,'source':str(source),'inputs':before,'outputs':outputs},indent=2)+'\n')
if __name__=='__main__':main()
