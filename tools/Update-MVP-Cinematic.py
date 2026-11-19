"""Install a verified general replay update, preserving the accepted rollback chain."""
from pathlib import Path
import argparse,datetime,importlib.util,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def main(args):
    installer=load('install','Install-MVP-Cinematic.py');builder=load('build','Build-MVP-Cinematic.py')
    transaction=load('transaction','Install-Handedness.py');out=builder.OUT
    previous=installer.verify();candidate=builder.verify();installer.stopped()
    assert set(candidate['builds'])=={'engine','game','frontend'}
    server=builder.read(out/'server-build.json')
    assert server['sources']==candidate['sources']['engine']
    assert server['candidate_manifest_sha256']==builder.sha(out/'manifest.json')
    evidence={}
    binaries=[('engine','openjk.x86_64.exe','bin/SaberTrials.x86_64.exe'),
        ('engine','rd-vanilla_x86_64.dll','bin/rd-vanilla_x86_64.dll'),
        ('engine','rd-rend2_x86_64.dll','bin/rd-rend2_x86_64.dll'),
        ('game','jampgamex86_64.dll','home/SaberTrials/jampgamex86_64.dll'),
        ('frontend','cgamex86_64.dll','home/SaberTrials/cgamex86_64.dll'),
        ('frontend','uix86_64.dll','home/SaberTrials/uix86_64.dll')]
    for name in args.evidence:
        folder=out/'qa'/name;result=builder.read(folder/'result.json')
        if 'returncodes' in result:
            assert result['finished'] and all(v==0 for v in result['returncodes'].values())
            assert result['server_sha256']==server['binary_sha256']
            assert 7000<=result['elapsed']['a'][0]<8000 and 0<result['elapsed']['b'][0]<2500
            folders=[folder/p for p in ('server','viewer-a','viewer-b')]
        elif result.get('passed') and ('cases' in result or 'automaticDiagnostics' in result):
            assert result['returncode']==0
            if 'cases' in result:assert len(result['cases'])==11 and result['defaultEnabled']
            else:assert result['automaticDiagnostics']==0 and result['finalSceneSimilarity']>.97
            folders=[folder]
        else:
            assert result['returncode']==0 and len(result['elapsed'])==1
            assert 0<int(result['elapsed'][0])<16000
            folders=[folder]
        for tested in folders:
            staged=builder.read(tested/'stage-receipt.json')['files']
            for kind,binary,relative in binaries:
                assert staged[relative]==candidate['builds'][kind][binary],'Stale native test: '+name+'/'+relative
        evidence[name]=builder.sha(folder/'result.json')
    assert len(evidence)>=4,'Need general FFA, team/objective, Duel and network evidence'
    home=installer.personal_home()
    assert not list(home.glob('*x86_64.dll')) and not (home/'ui/assets/sabertrials/mvp').exists()
    settings={str(p):installer.sha(p) for folder in (ROOT,home) for p in folder.glob('*.cfg')}
    desktop=Path(subprocess.check_output(['powershell','-NoProfile','-Command',"[Environment]::GetFolderPath('Desktop')"],text=True).strip())
    settings[str(desktop/'Saber Trials.lnk')]=installer.sha(desktop/'Saber Trials.lnk')
    protected=dict(previous['protected'])
    for name in ('assets/branding/SaberTrials.ico','Saber Trials.lnk'):
        protected[name]=installer.sha(ROOT/name);assert protected[name]
    files={name:Path(source) for name,source in previous['sources'].items() if name in previous['after']}
    files.update({'client/SaberTrials.x86_64.exe':out/'build-engine/Release/openjk.x86_64.exe',
        'client/openjkded.x86_64.exe':out/'build-server/Release/openjkded.x86_64.exe',
        'client/rd-vanilla_x86_64.dll':out/'build-engine/Release/rd-vanilla_x86_64.dll',
        'client/rd-rend2_x86_64.dll':out/'build-engine/Release/rd-rend2_x86_64.dll',
        'jampgamex86_64.dll':out/'build-game/Release/jampgamex86_64.dll',
        'cgamex86_64.dll':out/'build-frontend/Release/cgamex86_64.dll',
        'uix86_64.dll':out/'build-frontend/Release/uix86_64.dll',
        'tools/launchers/SaberTrials.cmd':ROOT/'tools/launchers/SaberTrials.cmd'})
    files.update({name:out/'assets'/name for name in candidate['assets']})
    before={name:installer.sha(ROOT/name) for name in files}
    assert all(before[name]=={**previous['protected'],**previous['after']}.get(name) for name in files)
    protected={name:digest for name,digest in protected.items() if name not in files}
    after={name:installer.sha(source) for name,source in files.items()}
    assert after['client/openjkded.x86_64.exe']==server['binary_sha256']
    backup=ROOT/'dist/backups'/('mvp-general-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    receipt=ROOT/'dist/mvp-style-linger-promotion.json';assert not receipt.exists(),'Update already promoted'
    state=dict(schema=2,installed=True,restored=False,candidate=str(out),before=before,after=after,
        original_before=previous.get('original_before',previous['before']),protected=protected,
        preserved_settings=settings,backup=str(backup),previous_backup=previous['backup'],
        candidate_manifest_sha256=builder.sha(out/'manifest.json'),server_build_sha256=builder.sha(out/'server-build.json'),
        sources={name:str(source) for name,source in files.items()},evidence=evidence,
        profile_integration=candidate['profile'],
        game_api=239,cgame_api=238,ui_api=285,renderer_api=11,
        scope='Orange and color labels; final replay linger and quiet normal console; verified Profile/scoreboard integration')
    installer.stopped()
    transaction.install_transaction(ROOT,files,before,after,protected,backup,receipt,state)
    transaction.atomic_record(backup/'previous-install-receipt.json',previous)
    transaction.atomic_record(installer.STATE,state)
    installer.verify(settings=True);builder.verify()
    print('Installed general match-end replay in the main launcher and matching dedicated server.')
    print('Verified preserved settings, packages, shortcuts and official icon; integrated approved Profile/scoreboard UI.')
    print('Rollback:',backup)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',nargs='+',required=True);main(p.parse_args())
