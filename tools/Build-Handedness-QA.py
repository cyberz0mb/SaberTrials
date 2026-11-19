"""Add menu-only probes to a copy of a verified final frontend source tree.

Uses the exact production engine/renderers; only the isolated QA UI differs.
Never installs or launches a client/server.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, shutil, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def qa_texts(frontend):
    """Return the exact two QA-only edits without changing any source files."""
    names=('codemp/ui/ui_atoms.c','codemp/ui/ui_main.c')
    result={name:(frontend/name).read_text() for name in names}
    probes='\n'.join((ROOT/'tests/handedness'/name).read_text() for name in ('ui_qa.inc','lock_qa.inc'))
    edits=(
        (names[0],'typedef struct consoleCommand_s {',probes+'\ntypedef struct consoleCommand_s {'),
        (names[0],'static consoleCommand_t\tcommands[] = {',
         'static consoleCommand_t\tcommands[] = {\n {"st_handqa",ST_HandQA_f},\n {"st_lockqa",ST_LockQA_f},'),
        (names[1],'\t\tST_UIPresentation();',
         '\t\tST_UIPresentation();\n\t\t{ extern void ST_LockQAPaint(void); ST_LockQAPaint(); }'),
    )
    for name,old,new in edits:
        if result[name].count(old)!=1:
            raise RuntimeError('QA source anchor changed: '+name+': '+old)
        result[name]=result[name].replace(old,new)
    return result


def input_hashes():
    names=('tools/Build-Handedness-QA.py','tools/Prepare-Handedness-Baseline.py',
           'tests/handedness/ui_qa.inc','tests/handedness/lock_qa.inc')
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}


def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
    baseline=a.baseline.resolve();builder=load('accepted_baseline',ROOT/'tools/Prepare-Handedness-Baseline.py')
    builder.safe_output(baseline)
    record=json.loads((baseline/'provenance.json').read_text())
    provenance_hash=builder.sha(baseline/'provenance.json')
    inputs=input_hashes()
    assert builder.tree(baseline/'frontend')==record['components']['frontend']
    for name,digest in record['builds']['engine'].items():
        builder.require_hash(baseline/'build-engine/Release'/name,digest)
    out=baseline/'qa';assert not out.exists() and not out.is_symlink(),'Choose a fresh accepted baseline for new QA'
    assert out.resolve().is_relative_to(baseline),'QA output escapes baseline'
    source=out/'source';shutil.copytree(baseline/'frontend',source)
    assert builder.tree(source)==record['components']['frontend'],'Frontend changed while copying'
    edits=qa_texts(source)
    for name,text in edits.items():(source/name).write_text(text,encoding='utf-8',newline='\n')
    before=builder.tree(source)
    expected=dict(record['components']['frontend'])
    expected.update({name:hashlib.sha256(text.encode('utf-8')).hexdigest() for name,text in edits.items()})
    assert before==expected,'Unexpected changes outside the two QA UI files'
    flags=builder.FLAGS
    subprocess.run(['cmake','-S',str(source),'-B',str(out/'build'),'-G','Visual Studio 18 2026','-A','x64',
                    *[f'-D{flag}={"ON" if flag=="BuildMPUI" else "OFF"}' for flag in flags]],check=True)
    subprocess.run(['cmake','--build',str(out/'build'),'--config','Release','--parallel','6'],check=True)
    assert builder.tree(source)==before,'QA source changed during build'
    assert builder.tree(baseline/'frontend')==record['components']['frontend'],'Accepted frontend changed during QA build'
    assert input_hashes()==inputs,'QA build inputs changed during compilation'
    builder.require_hash(baseline/'provenance.json',provenance_hash)
    release=out/'Release';release.mkdir()
    shutil.copy2(out/'build/Release/uix86_64.dll',release/'uix86_64.dll')
    for name in ('openjk.x86_64.exe','rd-vanilla_x86_64.dll','rd-rend2_x86_64.dll'):
        shutil.copy2(baseline/'build-engine/Release'/name,release/name)
        builder.require_hash(release/name,record['builds']['engine'][name])
    (out/'qa-manifest.json').write_text(json.dumps({'installed':False,'baseline':str(baseline),
        'production_engine_renderers':True,'baseline_provenance_sha256':provenance_hash,
        'inputs':inputs,'source':before,'qa_source_changes':sorted(edits),
        'files':{p.name:builder.sha(p) for p in release.iterdir()}},indent=2)+'\n')
    print('QA-only UI and exact production engine/renderers:',release)


if __name__=='__main__':main()
