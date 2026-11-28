"""Build the rounded black blade on the installed frontend; no game is launched."""
from datetime import datetime
from importlib import import_module
from pathlib import Path
import shutil
import subprocess
import sys
from zipfile import ZipFile, ZIP_DEFLATED

sys.dont_write_bytecode = True
support = import_module('Build-Vulkan')
ROOT = support.ROOT
OUT = ROOT / 'dist/black-sabers-01'
BASE = ROOT / 'dist/profile-uniform-fix/frontend'
SOURCE = ROOT / 'development-source/saber-crystals'
RECEIPT = OUT / 'source-receipt.json'
INSTALL = ROOT / 'dist/black-sabers-install.json'
PACKAGE = 'zzzzzzzzzzzz_sabertrials_crystals.pk3'
MODULES = ('uix86_64.dll', 'cgamex86_64.dll')
sha, read, write, tree = support.sha, support.read, support.write, support.tree


def inputs():
    return {name: sha(SOURCE / name) for name in ('st_crystal_blade.inc', 'st_crystals.shader', 'black_blade.py')}


def files():
    return {**{name: OUT / 'build/Release' / name for name in MODULES}, PACKAGE: OUT / PACKAGE}


def prepare():
    prior = read(ROOT / 'dist/profile-uniforms-install.json')
    current = {name: sha(ROOT / name) for name in (*MODULES, PACKAGE)}
    for name in MODULES:
        assert current[name] == prior['after'][name] == sha(ROOT / prior['built_from'][name])
    assert not RECEIPT.exists(), 'Prepared receipt exists; use build or a new output directory'
    OUT.mkdir(exist_ok=True)
    baseline = tree(BASE)
    def copy_changed(source, target):
        if not Path(target).is_file() or sha(source) != sha(target): shutil.copyfile(source, target)
        return str(target)
    shutil.copytree(BASE, OUT / 'frontend', dirs_exist_ok=True, copy_function=copy_changed)
    assert tree(OUT / 'frontend') == baseline
    for role in ('ui', 'cgame'):
        shutil.copyfile(SOURCE / 'st_crystal_blade.inc', OUT / 'frontend/codemp' / role / 'st_crystal_blade.inc')
    sources = tree(OUT / 'frontend')
    assert sources.keys() == baseline.keys()
    assert {n for n in sources if sources[n] != baseline[n]} == {
        'codemp/ui/st_crystal_blade.inc', 'codemp/cgame/st_crystal_blade.inc'}
    generator = support.module('black_blade_mesh', SOURCE / 'black_blade.py')
    model = generator.capsule()
    shader = (SOURCE / 'st_crystals.shader').read_bytes()
    with ZipFile(ROOT / PACKAGE) as original, ZipFile(OUT / PACKAGE, 'w', ZIP_DEFLATED) as updated:
        # Preserve all approved colored textures, masks and materials.
        old_shader = original.read('shaders/st_crystals.shader').decode()
        assert old_shader.split('gfx/st_crystals/blackCore')[0].split() == shader.decode().split('gfx/st_crystals/blackCore')[0].split()
        for item in original.infolist():
            updated.writestr(item, shader if item.filename == 'shaders/st_crystals.shader' else original.read(item))
        assert generator.MODEL not in original.namelist()
        updated.writestr(generator.MODEL, model)
    with ZipFile(ROOT / PACKAGE) as original, ZipFile(OUT / PACKAGE) as updated:
        assert set(updated.namelist()) - set(original.namelist()) == {generator.MODEL}
        for name in original.namelist():
            if name != 'shaders/st_crystals.shader': assert original.read(name) == updated.read(name), name
    protected = {}
    paths = [*ROOT.glob('*.dll'), *ROOT.glob('*.pk3'), *ROOT.joinpath('client').glob('*'),
             *ROOT.joinpath('ui').rglob('*.menu'), *ROOT.joinpath('tools/launchers').glob('*.cmd')]
    for path in paths:
        name = path.relative_to(ROOT).as_posix()
        if path.is_file() and name not in current: protected[name] = sha(path)
    write(RECEIPT, dict(installed=current, protected=protected, sources=sources, inputs=inputs(),
        baseline=baseline, package=sha(OUT / PACKAGE), model=dict(vertices=114,triangles=224,bytes=len(model)),
        gameplay_tested=False, user_requested_manual_gameplay_testing=True))
    print('Prepared rounded 3D black blade and conditional White Core rim; colored assets preserved.', flush=True)


def build():
    record = read(RECEIPT)
    assert inputs() == record['inputs'] and tree(OUT / 'frontend') == record['sources']
    flags = ('BuildMPEngine','BuildMPDed','BuildMPGame','BuildMPCGame','BuildMPUI',
             'BuildMPRdVanilla','BuildMPRend2','BuildMPRdVulkan','BuildSPEngine','BuildSPGame','BuildSPRdVanilla')
    with (OUT / 'build.log').open('w') as log:
        for command in (
            ['cmake','-S', str(OUT / 'frontend'), '-B', str(OUT / 'build'), '-G', 'Visual Studio 18 2026',
             '-A', 'x64', '-DST_STAFF_QA=OFF', '-DST_DEPS='+str(ROOT / 'dist/handedness-baseline-06/deps'),
             *[f'-D{f}={"ON" if f in ("BuildMPUI","BuildMPCGame") else "OFF"}' for f in flags]],
            ['cmake','--build', str(OUT / 'build'), '--config','Release','--parallel','5',
             '--target','uix86_64','cgamex86_64']):
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    write(OUT / 'build.json', dict(source=sha(RECEIPT), files={name:sha(path) for name,path in files().items()}))
    print('Compiled production UI and client-game modules. No game launched.', flush=True)


def check():
    record = read(RECEIPT)
    assert inputs() == record['inputs'] and tree(OUT / 'frontend') == record['sources']
    built = read(OUT / 'build.json')
    assert built == dict(source=sha(RECEIPT), files={n:sha(p) for n,p in files().items()})
    verify = OUT / 'verification'
    verify.mkdir(exist_ok=True)
    (verify / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.20)
project(BlackBladeContract LANGUAGES CXX)
add_executable(black_blade_contract "../../../../tests/black-sabers/render_contract.cpp")
target_include_directories(black_blade_contract PRIVATE "../frontend/shared" "../frontend/codemp")
target_compile_definitions(black_blade_contract PRIVATE _CRT_SECURE_NO_WARNINGS)
target_compile_features(black_blade_contract PRIVATE cxx_std_17)
''')
    with (verify / 'build.log').open('w') as log:
        for command in (
            ['cmake','-S',str(verify),'-B',str(verify / 'build'),'-G','Visual Studio 18 2026','-A','x64'],
            ['cmake','--build',str(verify / 'build'),'--config','Release']):
            subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
    result = subprocess.check_output([str(verify / 'build/Release/black_blade_contract.exe')], text=True)
    (verify / 'result.txt').write_text(result)
    generator = support.module('black_blade_check', SOURCE / 'black_blade.py')
    with ZipFile(OUT / PACKAGE) as package:
        assert package.testzip() is None
        assert len(package.namelist()) == len(set(package.namelist()))
        assert package.read(generator.MODEL) == generator.capsule()
        assert package.read('shaders/st_crystals.shader') == (SOURCE / 'st_crystals.shader').read_bytes()
    write(OUT / 'verification.json', dict(passed=True, build_sha256=sha(OUT / 'build.json'),
        contract_sha256=sha(ROOT / 'tests/black-sabers/render_contract.cpp'), result=result.strip(),
        gameplay_tested=False))
    print(result.strip(), flush=True)
    print('Packaged mesh, shaders and archive integrity verified.', flush=True)


def install():
    helper = import_module('Install-Profile-Browser')
    helper.stopped()
    home, settings = helper.settings()
    record = read(RECEIPT)
    assert inputs() == record['inputs'] and tree(OUT / 'frontend') == record['sources']
    assert all(sha(ROOT / name) == h for name,h in record['installed'].items())
    assert all(sha(ROOT / name) == h for name,h in record['protected'].items())
    assert not any((home / name).exists() for name in MODULES), 'Saved-profile modules shadow the update'
    assert not (ROOT / 'shaders/st_crystals.shader').exists() and not (home / 'shaders/st_crystals.shader').exists()
    after = {name:sha(path) for name,path in files().items()}
    assert read(OUT / 'build.json') == dict(source=sha(RECEIPT), files=after)
    checked = read(OUT / 'verification.json')
    assert checked['passed'] and checked['build_sha256'] == sha(OUT / 'build.json')
    assert checked['contract_sha256'] == sha(ROOT / 'tests/black-sabers/render_contract.cpp')
    assert after[PACKAGE] == record['package']
    backup = ROOT / 'dist/backups' / f'black-sabers-{datetime.now():%Y%m%d-%H%M%S}'
    payload = dict(before=record['installed'], after=after, protected=record['protected'], backup=str(backup),
        preserved_settings=settings, source_sha256=sha(RECEIPT), build_sha256=sha(OUT / 'build.json'),
        verification_sha256=sha(OUT / 'verification.json'),
        gameplay_tested=False, user_requested_manual_gameplay_testing=True, colored_saber_assets_preserved=True)
    import_module('Install-Handedness').install_transaction(ROOT, files(), record['installed'], after,
        record['protected'], backup, INSTALL, payload)
    assert all(sha(Path(name)) == h for name,h in settings.items())
    print('Installed rounded black blade and White Core edge toggle; current gameplay and saved settings preserved.', flush=True)


if __name__ == '__main__':
    {'prepare':prepare, 'build':build, 'check':check, 'install':install}[sys.argv[1]]()
