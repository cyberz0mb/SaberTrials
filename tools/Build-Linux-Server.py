"""Stage a secret-free native Linux build. Does not install or run a game server."""
from pathlib import Path
import hashlib, importlib.util, json, subprocess, sys, tarfile
ROOT=Path(__file__).resolve().parents[1]
REV='1a6a643427aa347553e9073dac5570b33337c4d9'
def stage():
    spec=importlib.util.spec_from_file_location('staff_build',ROOT/'tools/Build-Staff.py')
    build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
    build.verify_dependencies(ROOT/'dist/staff-deps')
    source=build.prepare(False)
    browser_spec=importlib.util.spec_from_file_location(
        'server_browser_overlay',ROOT/'development-source/server-browser/overlay.py')
    browser=importlib.util.module_from_spec(browser_spec);browser_spec.loader.exec_module(browser)
    browser.server(source)
    files={}
    for folder in [source,ROOT/'development-source/staff',ROOT/'development-source/accounts',ROOT/'development-source/bot-roles',ROOT/'development-source/client-game',ROOT/'development-source/server-browser',ROOT/'tests/accounts',ROOT/'tests/staff',ROOT/'tests/tournament',ROOT/'tests/linux',ROOT/'tests/guard-native',ROOT/'tests/server-browser']:
        for p in folder.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.tmp','.bak'):
                files[p.relative_to(ROOT).as_posix()]=p
    for name in ('sodium.tar.gz','sqlite.zip'):
        files['dist/staff-deps/'+name]=ROOT/'dist/staff-deps'/name
    for name in ('tools/build-linux-server.sh','tools/Build-Linux-Server.py','LICENSE.txt','CREDITS.txt','docs/Linux-Server-Upload.md',
                 'services/__init__.py','services/guard_watch.py','tests/test_guard_watch.py'):
        files[name]=ROOT/name
    dest=ROOT/'dist/linux-tooling/source.tar.gz'
    with tarfile.open(dest,'w:gz') as t:
        for name,p in sorted(files.items()):t.add(p,arcname=name,recursive=False)
    manifest={'revision':REV,'inputs':{name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in sorted(files.items())}}
    (ROOT/'dist/linux-tooling/source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Staged',len(files),'source files; no game assets, configuration secrets or credentials.')
if __name__=='__main__':stage()
