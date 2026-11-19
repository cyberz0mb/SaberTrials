"""Stage the narrow staff-prediction prerequisite in separate source copies.

Does not activate feints/styles or install anything. The new combat core remains
independent until authoritative state, prediction and animation adapters exist.
"""
from pathlib import Path
import argparse,importlib.util,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/combat-foundation-01'
BASE=ROOT/'dist/stance-candidate-02'
spec=importlib.util.spec_from_file_location('combat_audit',ROOT/'tools/Audit-Combat-Foundation.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

def tree(root):return {str(p.relative_to(root)).replace('\\','/'):audit.sha(p) for p in root.rglob('*') if p.is_file()}

def fixtures(frontend):
    code=[]
    for side,path in [('Server',BASE/'game'),('Client',frontend)]:
        text=(path/'codemp/game/bg_pmove.c').read_text()
        code.append(audit.body(text,'static float PM_CmdScale(').replace('PM_CmdScale',side+'Scale',1))
        prefix=audit.body(text,'void Pmove (')
        prefix=prefix[prefix.index('{')+1:prefix.index('finalTime = pmove->cmd.serverTime;')]
        code.append('static void '+side+'Staff(pmove_t* pmove) {'+prefix+'\n}\n')
    folder=OUT/'fixtures';folder.mkdir(parents=True,exist_ok=True)
    (folder/'movement_functions.inc').write_text('\n'.join(code),encoding='utf-8',newline='\n')

def verify():
    audit.verify_baseline()
    m=json.loads((OUT/'candidate.json').read_text())
    for kind in ('game','frontend'):
        if tree(OUT/'candidate'/kind)!=m['sources'][kind]:raise ValueError('Candidate drift: '+kind)
    if audit.sha(OUT/'candidate/frontend/codemp/game/bg_pmove.c')!=audit.sha(BASE/'game/codemp/game/bg_pmove.c'):
        raise ValueError('Movement parity changed')
    return m

def stage():
    baseline,_,_=audit.verify_baseline()
    target=OUT/'candidate'
    if target.exists():raise ValueError('Candidate exists; verify or build it without overwriting')
    for kind in ('game','frontend'):shutil.copytree(BASE/kind,target/kind)
    source=BASE/'game/codemp/game/bg_pmove.c'
    dest=target/'frontend/codemp/game/bg_pmove.c'
    a=source.read_text();b=dest.read_text()
    # Assert the complete difference is exactly the inspected staff prerequisite.
    b=b.replace('#include "st_stance_runtime.h"',
        '#include "st_stance_runtime.h"\n#include "../staff/st_staff_movement.h"',1)
    b=b.replace('\tint\t\tumove = 0; //cmd->upmove;',
        '\tint\t\tumove = (pm->ps->pm_type == PM_NOCLIP && pm->ps->stats[ST_STAFF_STAT] == ST_STAFF_GHOST) ? cmd->upmove : 0;',1)
    prefix=audit.body(a,'void Pmove (')
    guard=prefix[prefix.index('\t// Apply the same restrictions'):prefix.index('\tfinalTime = pmove->cmd.serverTime;')]
    b=b.replace('\tfinalTime = pmove->cmd.serverTime;',guard+'\tfinalTime = pmove->cmd.serverTime;',1)
    if a!=b:raise ValueError('Unreviewed additional shared-movement differences')
    # Byte-identical canonical shared source; no broad merge.
    shutil.copy2(source,dest)
    header=Path('codemp/staff/st_staff_movement.h')
    if audit.sha(target/'frontend'/header)!=audit.sha(BASE/'game'/header):raise ValueError('Staff constant drift')
    sources={k:tree(target/k) for k in ('game','frontend')}
    changes={k:[n for n,h in sources[k].items() if baseline['sources'][k].get(n)!=h] for k in sources}
    if changes!={'game':[],'frontend':['codemp/game/bg_pmove.c']}:
        raise ValueError('Unexpected staged changes: '+str(changes))
    audit.write(OUT/'candidate.json',{'installed':False,'features_enabled':[],
        'base_manifest_sha256':audit.sha(BASE/'sources.json'),'sources':sources,'changes':changes,'builds':{}})
    fixtures(target/'frontend');verify()
    print('Staged one shared-movement correction; no live installation or new combat enabled.')

def build(kind):
    m=verify()
    flags=('BuildMPEngine','BuildMPDed','BuildMPGame','BuildMPCGame','BuildMPUI','BuildMPRdVanilla',
           'BuildMPRend2','BuildSPEngine','BuildSPGame','BuildSPRdVanilla')
    enabled=('BuildMPGame',) if kind=='game' else ('BuildMPCGame','BuildMPUI')
    folder=OUT/('build-'+kind)
    subprocess.run(['cmake','-S',str(OUT/'candidate'/kind),'-B',str(folder),'-G','Visual Studio 18 2026','-A','x64',
        '-DST_DEPS='+str(ROOT/'dist/handedness-baseline-06/deps'),'-DST_STAFF_QA=OFF',
        *['-D'+f+'='+('ON' if f in enabled else 'OFF') for f in flags]],check=True)
    subprocess.run(['cmake','--build',str(folder),'--config','Release','--parallel','6'],check=True)
    m=verify()
    artifacts=('jampgamex86_64.dll',) if kind=='game' else ('cgamex86_64.dll','uix86_64.dll')
    m['builds'][kind]={n:audit.sha(folder/'Release'/n) for n in artifacts}
    audit.write(OUT/'candidate.json',m)
    print('Built staged '+kind+'; not installed.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage',action='store_true');p.add_argument('--verify',action='store_true')
    p.add_argument('--baseline-fixtures',action='store_true');p.add_argument('--build',choices=('game','frontend'))
    args=p.parse_args()
    if args.baseline_fixtures:fixtures(BASE/'frontend')
    elif args.stage:stage()
    elif args.build:build(args.build)
    elif args.verify:verify();print('Baseline, installation and staged candidate verified.')
    else:p.error('Choose --stage, --verify, --build or --baseline-fixtures')
