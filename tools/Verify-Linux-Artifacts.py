"""Run inside the compiler VM: inspect compiled output without starting JKA."""
import ctypes,hashlib,json,pathlib,re,subprocess
root=pathlib.Path('/home/builder/sabertrials')
manifest=json.loads(pathlib.Path('/home/builder/source-manifest.json').read_text())
changes=[]
for name,expected in manifest['inputs'].items():
    if name.startswith(('dist/staff-work/','development-source/','tests/')):
        p=root/name
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:changes.append(name)
if changes:raise SystemExit('Build source mismatch: '+json.dumps(changes))
report={'architecture':'x86_64','game_server_started':False,'source_matches':True,'artifacts':{}}
for name in ('openjkded.x86_64','codemp/game/jampgamex86_64.so'):
    path=root/'dist/linux-server-build'/name
    versions=subprocess.check_output(['readelf','--version-info',str(path)],text=True)
    deps=subprocess.check_output(['ldd',str(path)],text=True)
    if 'not found' in deps:raise SystemExit('Unresolved dependency')
    header=subprocess.check_output(['readelf','-h',str(path)],text=True)
    if 'ELF64' not in header or 'X86-64' not in header:raise SystemExit('Wrong binary architecture')
    dynamic=subprocess.check_output(['readelf','-d',str(path)],text=True)
    report['artifacts'][path.name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'elf':header,'dependencies':deps,'needed':re.findall(r'Shared library: \[(.*?)\]',dynamic),
        'symbol_versions':sorted(set(re.findall(r'(?:GLIBC|GLIBCXX|CXXABI|CURL_OPENSSL)_[0-9.]+',versions)))}
    if b'st_staffqa' in path.read_bytes():raise SystemExit('QA hook found in release')
report['abi_probe']=subprocess.check_output(['python3',str(root/'tests/linux/module_abi_test.py'),str(root/'dist/linux-server-build/codemp/game/jampgamex86_64.so')],text=True)
report['https_probe']=subprocess.check_output([str(root/'dist/linux-tests-accounts/account_test'),'--health'],text=True)
report['compiler']=subprocess.check_output(['g++','--version'],text=True).splitlines()[0]
(root/'dist/linux-evidence/artifacts.json').write_text(json.dumps(report,indent=2)+'\n')
print('Source hashes, ELF architecture, dependencies, module APIs and native HTTPS verified. No game server started.')
