"""Stage/build/install the native Match Rules without starting a game."""
from datetime import datetime
from importlib import import_module
from pathlib import Path
import shutil
import subprocess
import sys
from zipfile import ZipFile, ZIP_DEFLATED

sys.dont_write_bytecode = True
s = import_module('Build-Vulkan')
ROOT=s.ROOT
OUT=ROOT/'dist/match-rules-01'
SRC=ROOT/'development-source/match-rules'
BASE={'frontend':ROOT/'dist/black-sabers-01/frontend','game':ROOT/'dist/profile-uniform-fix/game'}
RECEIPT=OUT/'source-receipt.json'
INSTALL=ROOT/'dist/match-rules-install.json'
MODULES=('uix86_64.dll','cgamex86_64.dll','jampgamex86_64.dll')
PACKAGE='zzzzzzzzzzzzzzzz_sabertrials_match_rules.pk3'
sha,read,write,tree=s.sha,s.read,s.write,s.tree


def module(name):
    return s.module('match_rules_'+name,SRC/(name+'.py'))


def files():
    result={n:OUT/('build-game' if n.startswith('jamp') else 'build-frontend')/'Release'/n for n in MODULES}
    result[PACKAGE]=OUT/PACKAGE
    result.update({p.relative_to(OUT/'menus').as_posix():p for p in (OUT/'menus').rglob('*.menu')})
    return result


def protected(targets):
    paths=[*ROOT.glob('*.dll'),*ROOT.glob('*.pk3'),*ROOT.joinpath('client').glob('*'),
           *ROOT.joinpath('ui').rglob('*.menu'),*ROOT.joinpath('tools/launchers').glob('*.cmd')]
    return {p.relative_to(ROOT).as_posix():sha(p) for p in paths
            if p.is_file() and p.relative_to(ROOT).as_posix() not in targets}


def verify_baseline():
    black=read(ROOT/'dist/black-sabers-install.json')
    uniform=read(ROOT/'dist/profile-uniforms-install.json')
    for n in MODULES:
        expected=(uniform if n.startswith('jamp') else black)['after'][n]
        assert sha(ROOT/n)==expected,'Installed baseline changed: '+n
    assert tree(BASE['frontend'])==read(ROOT/'dist/black-sabers-01/source-receipt.json')['sources']
    for n in ('jampgamex86_64.dll',):
        assert sha(ROOT/n)==sha(ROOT/'dist/profile-uniform-fix/build-game/Release'/n)


def stage(refresh=False):
    OUT.mkdir(exist_ok=True)
    prior=read(RECEIPT) if RECEIPT.exists() else None
    if prior and PACKAGE not in prior['before']:
        assert not (ROOT/PACKAGE).exists(),'New menu package path is already occupied'
        prior['before'][PACKAGE]=None
    assert bool(prior)==refresh,'Use prepare once, then refresh while the candidate is uninstalled.'
    assert not INSTALL.exists(),'Already installed; prepare a separately named candidate for another update.'
    verify_baseline()
    if prior:
        assert all((sha(ROOT/n) if (ROOT/n).is_file() else None)==h for n,h in prior['before'].items()),'Installed targets changed'
        assert all(sha(ROOT/n)==h for n,h in prior['protected'].items()),'Protected install changed'
    def copy_changed(source,target):
        if not Path(target).is_file() or sha(source)!=sha(target):shutil.copyfile(source,target)
        return str(target)
    baseline={role:tree(path) for role,path in BASE.items()}
    for role,path in BASE.items():
        if prior:
            # Also discard this candidate's additions from an interrupted replay.
            for n in set(tree(OUT/role))-set(baseline[role]):
                target=(OUT/role/n).resolve()
                assert target.is_relative_to((OUT/role).resolve())
                target.unlink(missing_ok=True)
        shutil.copytree(path,OUT/role,dirs_exist_ok=True,copy_function=copy_changed)
        assert tree(OUT/role)==baseline[role],role+' source copy mismatch'
    authored=tree(SRC)
    server,ui=module('server'),module('ui')
    server.apply(OUT/'game')
    if hasattr(server,'apply_frontend'):server.apply_frontend(OUT/'frontend')
    ui.apply(OUT/'frontend')
    ui.menus(OUT/'menus')
    with ZipFile(OUT/PACKAGE,'w',ZIP_DEFLATED) as archive:
        for path in sorted((OUT/'menus').rglob('*.menu')):
            archive.write(path,path.relative_to(OUT/'menus').as_posix())
    assert tree(SRC)==authored,'Authored files changed during overlay replay; refresh again'
    sources={role:tree(OUT/role) for role in BASE}
    targets=files()
    before={n:sha(ROOT/n) if (ROOT/n).is_file() else None for n in targets}
    guard=protected(targets)
    if prior:
        assert before==prior['before']
        assert guard==prior['protected']
    changes={role:dict(changed=[n for n,h in sources[role].items() if baseline[role].get(n)!=h],
                       removed=sorted(set(baseline[role])-set(sources[role]))) for role in BASE}
    assert not any(v['removed'] for v in changes.values())
    write(RECEIPT,dict(before=before,protected=guard,baseline=baseline,sources=sources,
        inputs=authored,menus=tree(OUT/'menus'),changes=changes,game_launched=False))
    print('Prepared Match Rules on the current combined installed source; no game launched.',flush=True)


def current(authored=True):
    r=read(RECEIPT)
    if authored:assert tree(SRC)==r['inputs'],'Authored source changed; refresh candidate'
    assert tree(OUT/'menus')==r['menus'],'Menu candidate changed'
    for role in BASE:assert tree(OUT/role)==r['sources'][role],role+' source changed'
    return r


def build(staged_only=False,only=None):
    current(not staged_only)
    flags=('BuildMPEngine','BuildMPDed','BuildMPGame','BuildMPCGame','BuildMPUI',
           'BuildMPRdVanilla','BuildMPRend2','BuildMPRdVulkan','BuildSPEngine','BuildSPGame','BuildSPRdVanilla')
    for role,targets in (('frontend',('uix86_64','cgamex86_64')),('game',('jampgamex86_64',))):
        if only and only!=role:continue
        on=('BuildMPUI','BuildMPCGame') if role=='frontend' else ('BuildMPGame',)
        with (OUT/f'build-{role}.log').open('w') as log:
            for cmd in (
                ['cmake','-S',str(OUT/role),'-B',str(OUT/('build-'+role)),'-G','Visual Studio 18 2026','-A','x64',
                 '-DST_STAFF_QA=OFF','-DST_DEPS='+str(ROOT/'dist/handedness-baseline-06/deps'),
                 *[f'-D{f}={"ON" if f in on else "OFF"}' for f in flags]],
                ['cmake','--build',str(OUT/('build-'+role)),'--config','Release','--parallel','5','--target',*targets]):
                subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
        print('Compiled '+role+' production modules.',flush=True)
        write(OUT/f'compiled-{role}.json',dict(source=sha(RECEIPT),
            files={name+'.dll':sha(OUT/('build-'+role)/'Release'/(name+'.dll')) for name in targets}))
    compiled=[OUT/f'compiled-{r}.json' for r in ('frontend','game')]
    if all(p.is_file() and read(p)['source']==sha(RECEIPT) for p in compiled):
        for p in compiled:
            for name,digest in read(p)['files'].items():assert sha(files()[name])==digest
        write(OUT/'build.json',dict(source=sha(RECEIPT),files={n:sha(p) for n,p in files().items()}))


def install():
    r=current()
    helper=import_module('Install-Profile-Browser')
    helper.stopped()
    home,settings=helper.settings()
    target=files()
    assert not any((home/n).exists() for n in target),'Saved-profile files shadow the candidate'
    after={n:sha(p) for n,p in target.items()}
    assert read(OUT/'build.json')==dict(source=sha(RECEIPT),files=after)
    checks=read(OUT/'verification.json')
    assert checks['passed'] and checks['build_sha256']==sha(OUT/'build.json')
    assert checks['source_sha256']==sha(RECEIPT)
    assert checks['tests']['test_source_sha256']==tree(ROOT/'tests/match-rules')
    for n,h in r['before'].items():assert (sha(ROOT/n) if (ROOT/n).is_file() else None)==h,'Target drift: '+n
    for n,h in r['protected'].items():assert sha(ROOT/n)==h,'Protected drift: '+n
    backup=ROOT/'dist/backups'/f'match-rules-{datetime.now():%Y%m%d-%H%M%S}'
    payload=dict(before=r['before'],after=after,protected=r['protected'],backup=str(backup),
        preserved_settings=settings,source_sha256=sha(RECEIPT),build_sha256=sha(OUT/'build.json'),
        verification_sha256=sha(OUT/'verification.json'),game_launched=False,gameplay_tested=False)
    import_module('Install-Handedness').install_transaction(ROOT,target,r['before'],after,r['protected'],backup,INSTALL,payload)
    for n,h in settings.items():assert sha(Path(n))==h
    verify()


def verify():
    r=read(INSTALL)
    for n,h in {**r['after'],**r['protected']}.items():assert sha(ROOT/n)==h,n
    for n,h in r['before'].items():
        if h is not None:assert sha(Path(r['backup'])/n)==h,n
    for n,h in r['preserved_settings'].items():assert sha(Path(n))==h,n
    assert sha(OUT/'verification.json')==r['verification_sha256']
    print('Combined Match Rules installation, backups, protected assets and saved settings verified. No game launched.',flush=True)


if __name__=='__main__':
    {'prepare':lambda:stage(False),'refresh':lambda:stage(True),'build':build,
     'build-snapshot':lambda:build(True),'install':install,'verify':verify}[sys.argv[1]]()
