"""Stage a secret-free native Linux build. Does not install or run a game server."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, shutil, subprocess, sys, tarfile
ROOT=Path(__file__).resolve().parents[1]
REV='1a6a643427aa347553e9073dac5570b33337c4d9'
def beta_source():
    # The installed game uses an expanded playerState and native game API.
    # Build its Linux engine and module together from the matching trees.
    path = ROOT/'dist/anti-script/linux-engine'
    shutil.copytree(ROOT/'dist/anti-script/engine', path, dirs_exist_ok=True)
    shutil.copytree(ROOT/'dist/bot-navigation-01/game/codemp/game', path/'codemp/game', dirs_exist_ok=True)
    authored = ROOT/'development-source'
    for name in ('server', 'staff'):
        shutil.copytree(authored/'staff/codemp'/name, path/'codemp'/name, dirs_exist_ok=True)
    for file in ('g_event.c','g_event.h','g_event_ui.inc','st_event.c','st_event.h','st_event_account_api.h','st_event_ui.h'):
        shutil.copy2(authored/'bot-roles/codemp/game'/file, path/'codemp/game'/file)
    for patch in ('staff/patches/02-native-guard.patch','linux-beta/tournament-game.patch'):
        subprocess.run(['git','apply','--ignore-space-change','--directory='+str(path.relative_to(ROOT)),
                        str(authored/patch)],check=True,cwd=ROOT)
    cmake = path/'CMakeLists.txt'
    text = cmake.read_text()
    for role in ('staff','accounts'):
        before = (authored/role).as_posix()
        if text.count(before)!=1: raise ValueError('Missing build dependency: '+role)
        text = text.replace(before, '${CMAKE_CURRENT_LIST_DIR}/../../../development-source/'+role)
    cmake.write_text(text)
    return path


def stage(beta=False):
    spec=importlib.util.spec_from_file_location('staff_build',ROOT/'tools/Build-Staff.py')
    build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
    build.verify_dependencies(ROOT/'dist/staff-deps')
    if beta:
        source=beta_source()
    else:
        source=build.prepare(False)
        browser_spec=importlib.util.spec_from_file_location(
            'server_browser_overlay',ROOT/'development-source/server-browser/overlay.py')
        browser=importlib.util.module_from_spec(browser_spec);browser_spec.loader.exec_module(browser)
        browser.server(source)
        spec=importlib.util.spec_from_file_location('anti_script_overlay',ROOT/'development-source/anti-script/overlay.py')
        anti_script=importlib.util.module_from_spec(spec);spec.loader.exec_module(anti_script)
        anti_script.apply(source)
    files={}
    for folder in [source,ROOT/'development-source/staff',ROOT/'development-source/accounts',ROOT/'development-source/bot-roles',ROOT/'development-source/client-game',ROOT/'development-source/server-browser',ROOT/'tests/accounts',ROOT/'tests/staff',ROOT/'tests/tournament',ROOT/'tests/linux',ROOT/'tests/guard-native',ROOT/'tests/server-browser',ROOT/'development-source/anti-script',ROOT/'tests/anti-script']:
        for p in folder.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.tmp','.bak'):
                name=p.relative_to(ROOT).as_posix()
                if folder==source: name='dist/staff-work/OpenJK-'+REV+'/'+p.relative_to(source).as_posix()
                files[name]=p
    for name in ('sodium.tar.gz','sqlite.zip'):
        files['dist/staff-deps/'+name]=ROOT/'dist/staff-deps'/name
    for name in ('tools/build-linux-server.sh','tools/Build-Linux-Server.py','LICENSE.txt','CREDITS.txt','docs/Linux-Server-Upload.md','docs/Anti-Script.md',
                 'services/__init__.py','services/guard_watch.py','tests/test_guard_watch.py'):
        files[name]=ROOT/name
    output=ROOT/('dist/anti-script/linux' if beta else 'dist/linux-tooling')
    output.mkdir(parents=True,exist_ok=True)
    dest=output/'source.tar.gz'
    with tarfile.open(dest,'w:gz') as t:
        for name,p in sorted(files.items()):t.add(p,arcname=name,recursive=False)
    manifest={'revision':REV,'inputs':{name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in sorted(files.items())}}
    (output/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Staged',len(files),'source files; no game assets, configuration secrets or credentials.')
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--beta',action='store_true',help='Stage the installed Windows gameplay and engine for Linux')
    stage(parser.parse_args().beta)
