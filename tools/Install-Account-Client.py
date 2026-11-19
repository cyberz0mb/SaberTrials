"""Verify/package/install only the native account client and two root menus."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,re,subprocess,sys,time,zipfile

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'dist/staff-build/Release'
STAGE=ROOT/'dist/account-client-staging'
EVIDENCE=ROOT/'dist/verification/accounts-client-20261023'

def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def run(args,log):
    with log.open('w') as out:subprocess.run([str(x) for x in args],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,check=True)

def blocks(text,kind):
    """Read brace-delimited menu/item blocks, ignoring quoted braces/comments."""
    tokens=list(re.finditer(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/|[{}]|[^\s{}]+',text,re.S))
    depth=0;result={}
    for i,t in enumerate(tokens):
        if t.group()=='{':depth+=1
        if t.group()=='}':depth-=1
        if depth<0:raise RuntimeError('Unbalanced menu braces')
        if t.group()!=kind:continue
        if [v.group() for v in tokens[i+1:i+3]]!=['{','name']:raise RuntimeError('Unnamed menu block')
        name=tokens[i+3].group().strip('"');inner=0
        for end in tokens[i+1:]:
            if end.group()=='{':inner+=1
            if end.group()=='}':
                inner-=1
                if inner==0:break
        else:raise RuntimeError('Unclosed menu block')
        if name in result:raise RuntimeError('Duplicate '+kind+': '+name)
        result[name]=text[t.start():end.end()]
    if depth!=0:raise RuntimeError('Unbalanced menu braces')
    return result

def verify():
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    build=read(BUILD/'staff-build-manifest.json');builder=load('staffbuild','tools/Build-Staff.py')
    if build['kind']!='production' or build['inputs']!=builder.input_hashes():raise RuntimeError('Stale or nonproduction build')
    builder.verify_dependencies(ROOT/'dist/staff-deps')
    exe=BUILD/'openjk.x86_64.exe'
    if sha(exe)!=build['files']['openjk.x86_64.exe']:raise RuntimeError('Client hash mismatch')
    binary=exe.read_bytes()
    for forbidden in ('stqacmd','STAFF_CLIENT_QA','STAFF_QA ','st_staffQAProbe'):
        if any(forbidden.encode(enc) in binary for enc in ('utf-8','utf-16le')):raise RuntimeError('QA hook in client')
    menus=read(STAGE/'menu-manifest.json')
    sources={'client/SaberTrials.x86_64.exe':exe}
    for name,root,account in [('ui/jamp/main.menu','main','st_main_account'),('ui/jamp/ingame.menu','ingame','st_pause_account')]:
        # A client-only follow-up can retain the already-installed, verified menu.
        if sha(STAGE/name)!=menus['files'][name] or sha(ROOT/name) not in (menus['originals'][name],menus['files'][name]):raise RuntimeError('Menu or original changed: '+name)
        old=blocks((ROOT/name).read_text(),'menuDef');new=blocks((STAGE/name).read_text(),'menuDef')
        if set(new)!=set(old)|{account}:raise RuntimeError('Unexpected menu additions')
        for key,value in old.items():
            if key==account:continue
            if key!=root:
                if new[key]!=value:raise RuntimeError('Unrelated menu changed: '+key)
            else:
                olditems=blocks(value,'itemDef');newitems=blocks(new[key],'itemDef')
                if set(newitems)!=set(olditems)|{'account_link'}:raise RuntimeError('Unexpected root menu changes')
                for item,body in olditems.items():
                    if item!='account_link' and newitems[item]!=body:raise RuntimeError('Existing menu item changed: '+item)
        items=blocks(new[account],'itemDef')
        if 'exec "login"' not in items['login'] or 'exec "logout"' not in items['logout']:raise RuntimeError('Missing account actions')
        if root=='ingame' and 'st_uiPauseShell' not in blocks(new[root],'itemDef')['account_link']:raise RuntimeError('Photo Mode shell protection missing')
        sources[name]=STAGE/name
    # Meaningful native tests, including the actual engine adapter with fake I/O;
    # no game/server process or local game-server configuration is created.
    run(['cmake','--build','dist/account-native-tests','--config','Release','--parallel','6'],EVIDENCE/'native-build.log')
    for folder,label in [('dist/account-native-tests','account'),('dist/staff-build-tests','staff'),('dist/tournament-tests','tournament')]:
        run(['ctest','--test-dir',folder,'-C','Release','--output-on-failure'],EVIDENCE/(label+'-tests.log'))
    run([sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py'],EVIDENCE/'python-tests.log')
    run([ROOT/'dist/account-native-tests/Release/account_test.exe','--health'],EVIDENCE/'native-https.log')
    if build['inputs']!=builder.input_hashes():raise RuntimeError('Source changed during verification')
    protected={name:sha(ROOT/name) for name in ['jampgamex86_64.dll','cgamex86_64.dll','uix86_64.dll','Launch-SaberTrials-Overhaul.cmd','ui/jamp/ingame_player.menu']}
    for folder in ('ui/assets','shaders','server'):
        for p in (ROOT/folder).rglob('*'):
            if p.is_file():protected[p.relative_to(ROOT).as_posix()]=sha(p)
    for name in ('server.cfg','staff-setup.cfg','jampconfig.cfg'):
        if (ROOT/name).is_file():protected[name]=sha(ROOT/name)
    report={'production':build,'payload':{name:sha(p) for name,p in sources.items()},'protected':protected,
            'checks':{'native_account_tests':True,'native_staff_tests':True,'native_tournament_tests':True,'backend_83_tests':True,'live_native_https_health':True,'menu_structure_and_preservation':True},
            'interactive_game_login_verified':False,'game_or_server_launched':False,'server_identity_adapter_ready':False}
    write(EVIDENCE/'verification.json',report)
    return sources,report

def package(sources,report):
    files={'SaberTrials/'+name:p for name,p in sources.items()}
    # Include the corresponding source and pinned upstream/dependencies for this
    # GPL engine update; never bundle profiles, config, sessions or game assets.
    for name in report['production']['inputs']:files['SaberTrials/'+name]=ROOT/name
    for folder in ('tests/accounts','tests/staff'):
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and p.suffix in ('.cpp','.c','.h','.inc','.txt','.py'):files['SaberTrials/'+p.relative_to(ROOT).as_posix()]=p
    for name in ('tools/Install-Account-Client.py','tools/Stage-Accounts.py','tools/Stage-Tournament.py','tools/Install-Staff.py','docs/Account-Login.md','LICENSE.txt','CREDITS.txt'):
        files['SaberTrials/'+name]=ROOT/name
    upstream=ROOT/'dist/staff-work/openjk.zip'
    if sha(upstream)!=report['production']['source_archive_sha256']:raise RuntimeError('Upstream archive changed')
    files['SaberTrials/source/OpenJK-'+report['production']['source_revision']+'.zip']=upstream
    for name in ('sodium.tar.gz','sqlite.zip'):files['SaberTrials/dist/staff-deps/'+name]=ROOT/'dist/staff-deps'/name
    for name in files:
        if Path(name).suffix.lower() in ('.cfg','.key','.db','.bin','.log','.dm_26') or '/private/' in name:raise RuntimeError('Private/runtime data in candidate: '+name)
    manifest={'kind':'Windows account-client update','interactive_game_verified':False,'files':{name:sha(p) for name,p in files.items()},'checks':report['checks']}
    archive=ROOT/'dist/SaberTrials-account-client-20261023.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name,p in sorted(files.items()):z.write(p,name)
        z.writestr('account-client-manifest.json',json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None or len(z.namelist())!=len(files)+1:raise RuntimeError('Archive integrity failure')
        for name,expected in manifest['files'].items():
            if hashlib.sha256(z.read(name)).hexdigest()!=expected:raise RuntimeError('Archive hash mismatch: '+name)
    archive.with_suffix('.zip.sha256').write_text(sha(archive)+'  '+archive.name+'\n')
    return archive

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('verify','package','install'));args=parser.parse_args()
    sources,report=verify()
    if args.action=='verify':print('Verified production client, account/native regressions, live HTTPS, and preserved menu content.');return
    archive=package(sources,report);print('Verified package:',archive.name)
    if args.action=='install':
        running=subprocess.check_output(['tasklist','/FO','CSV'],text=True).lower()
        if any('"'+n+'"' in running for n in ('sabertrials.x86_64.exe','openjk.x86_64.exe','jamp.exe')):raise RuntimeError('Close Saber Trials before installation')
        for name,expected in report['protected'].items():
            if sha(ROOT/name)!=expected:raise RuntimeError('Protected file changed: '+name)
        for name,expected in report['payload'].items():
            if sha(sources[name])!=expected:raise RuntimeError('Candidate changed: '+name)
        changed={name:p for name,p in sources.items() if sha(ROOT/name)!=sha(p)}
        if not changed:print('The verified update is already installed.');return
        for name,p in sources.items():
            if name not in changed:report['protected'][name]=sha(p)
        backup=ROOT/'dist/backups'/('account-client-'+time.strftime('%Y%m%d-%H%M%S'))
        result=load('installer','tools/Install-Staff.py').transaction(ROOT,changed,backup)
        for name,expected in report['protected'].items():
            if sha(ROOT/name)!=expected:raise RuntimeError('Protected file changed: '+name)
        result.update(protected=report['protected'],checks=report['checks'],archive=archive.name,interactive_game_login_verified=False)
        write(ROOT/'dist/account-client-install-manifest.json',result)
        print('Installed '+str(len(changed))+' changed file(s). Existing gameplay, assets and configuration preserved.')

if __name__=='__main__':main()
