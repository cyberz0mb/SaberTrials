"""Build/install ten-color entry and saved chat color without launching a game."""
from datetime import datetime
from importlib import import_module
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
support = import_module('Build-Vulkan')
ROOT = support.ROOT
OUT = ROOT / 'dist/text-colors-01'
SOURCE = ROOT / 'development-source/text-colors'
RECEIPT = OUT / 'source-receipt.json'
INSTALL = ROOT / 'dist/text-colors-install.json'
BASES = {'engine': ROOT / 'dist/controller-response-01/engine',
         'frontend': ROOT / 'dist/menu-selection-01/frontend'}
EXE, UI = 'client/SaberTrials.x86_64.exe', 'uix86_64.dll'
DEPS = ROOT / 'dist/handedness-baseline-06/deps'
sha, read, write, tree = support.sha, support.read, support.write, support.tree


def authored():
    sources = ROOT / 'development-source'
    return {**{'text-colors/'+n: h for n, h in tree(SOURCE).items()},
        **{n: sha(sources / n) for n in ('profile/ui_st_name_keyboard.inc',
            'setup/st_setup_catalog.h', 'setup/ui_st_chat_preview.inc', 'translator/st_chat_raster.h')}}


def binary(role):
    return OUT / ('build-'+role) / 'Release' / ('openjk.x86_64.exe' if role == 'engine' else UI)


def files():
    return {EXE: binary('engine'), UI: binary('ui')}


def prepare():
    expected = {
        'engine': read(BASES['engine'].parent / 'source-receipt.json')['sources']['engine'],
        'frontend': read(BASES['frontend'].parent / 'source-receipt.json')['sources']}
    current = {name: sha(ROOT / name) for name in (EXE, UI)}
    assert current[EXE] == sha(BASES['engine'].parent / 'build-engine/Release/openjk.x86_64.exe')
    assert current[EXE] == read(ROOT / 'dist/controller-response-install.json')['after'][EXE]
    assert current[UI] == sha(BASES['frontend'].parent / 'build/Release' / UI)
    assert current[UI] == read(ROOT / 'dist/menu-selection-install.json')['after'][UI]
    assert not RECEIPT.exists(), 'Prepared receipt exists; use build or a fresh output directory'
    OUT.mkdir(exist_ok=True)
    patch = support.module('text_color_overlay', SOURCE / 'overlay.py')
    for role, base in BASES.items():
        assert tree(base) == expected[role], 'Baseline source changed: ' + role
        def copy_changed(source, target):
            if not Path(target).is_file() or sha(source) != sha(target):
                shutil.copyfile(source, target)
            return str(target)
        shutil.copytree(base, OUT / role, dirs_exist_ok=True, copy_function=copy_changed)
        getattr(patch, role)(OUT / role)
    sources = {role: tree(OUT / role) for role in BASES}
    assert {n for n in expected['engine'] if sources['engine'][n] != expected['engine'][n]} == {
        'codemp/client/cl_keys.cpp', 'codemp/client/cl_st_chat_input.inc',
        'codemp/client/cl_st_chat_text.inc', 'codemp/client/st_chat_raster.h', 'codemp/ui/st_setup_catalog.h'}
    assert sources['engine'].keys() - expected['engine'].keys() == {'codemp/client/cl_st_chat_color.h'}
    assert {n for n in expected['frontend'] if sources['frontend'][n] != expected['frontend'][n]} == {
        'codemp/ui/st_setup_catalog.h', 'codemp/ui/ui_st_name_keyboard.inc',
        'codemp/ui/ui_st_chat_preview.inc'}
    assert sources['frontend'].keys() == expected['frontend'].keys()
    assert sha(OUT / 'engine/codemp/ui/st_setup_catalog.h') == sha(OUT / 'frontend/codemp/ui/st_setup_catalog.h')
    protected = {}
    paths = [*ROOT.glob('*.dll'), *ROOT.glob('*.pk3'), *ROOT.joinpath('client').glob('*'),
             *ROOT.joinpath('ui').rglob('*.menu')]
    for path in paths:
        name = path.relative_to(ROOT).as_posix()
        if path.is_file() and name not in current:
            protected[name] = sha(path)
    write(RECEIPT, dict(installed=current, protected=protected, sources=sources, authored=authored(),
        bases={role: sha(path.parent / 'source-receipt.json') for role, path in BASES.items()}))
    print('Prepared full text palette, Unicode chat color fix, and saved outgoing chat color.', flush=True)


def build(role):
    source = 'engine' if role == 'engine' else 'frontend'
    receipt = read(RECEIPT)
    assert tree(OUT / source) == receipt['sources'][source] and authored() == receipt['authored']
    flags = ('BuildMPEngine', 'BuildMPDed', 'BuildMPGame', 'BuildMPCGame', 'BuildMPUI',
             'BuildMPRdVanilla', 'BuildMPRend2', 'BuildMPRdVulkan',
             'BuildSPEngine', 'BuildSPGame', 'BuildSPRdVanilla')
    target = 'BuildMPEngine' if role == 'engine' else 'BuildMPUI'
    library = 'openjk.x86_64' if role == 'engine' else 'uix86_64'
    with (OUT / f'build-{role}.log').open('w') as log:
        for command in (
            ['cmake', '-S', str(OUT / source), '-B', str(OUT / ('build-'+role)),
             '-G', 'Visual Studio 18 2026', '-A', 'x64', '-DST_STAFF_QA=OFF',
             '-DST_DEPS=' + str(DEPS),
             *[f'-D{f}={"ON" if f == target else "OFF"}' for f in flags]],
            ['cmake', '--build', str(OUT / ('build-'+role)), '--config', 'Release',
             '--parallel', '5', '--target', library]):
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    write(OUT / f'build-{role}.json', dict(source=sha(RECEIPT), sha256=sha(binary(role)), in_game_tested=False))
    print('Compiled production '+role+'. No game launched.', flush=True)


def refresh():
    receipt = read(RECEIPT)
    assert sha(SOURCE / 'overlay.py') == receipt['authored']['text-colors/overlay.py']
    assert sha(ROOT / 'development-source/setup/st_setup_catalog.h') == receipt['authored']['setup/st_setup_catalog.h']
    mapping = {
        'engine': {'codemp/client/cl_st_chat_color.h': SOURCE / 'cl_st_chat_color.h',
                   'codemp/client/st_chat_raster.h': ROOT / 'development-source/translator/st_chat_raster.h'},
        'frontend': {'codemp/ui/ui_st_name_keyboard.inc': ROOT / 'development-source/profile/ui_st_name_keyboard.inc',
                     'codemp/ui/ui_st_chat_preview.inc': ROOT / 'development-source/setup/ui_st_chat_preview.inc'}}
    for role, entries in mapping.items():
        for name, path in entries.items(): shutil.copyfile(path, OUT / role / name)
        actual = tree(OUT / role)
        for name, h in receipt['sources'][role].items():
            if name not in entries: assert actual[name] == h, 'Unexpected source change: '+name
        receipt['sources'][role] = actual
    receipt['authored'] = authored()
    write(RECEIPT, receipt)


def install():
    helper = import_module('Install-Profile-Browser')
    helper.stopped()
    home, settings = helper.settings()
    receipt = read(RECEIPT)
    assert authored() == receipt['authored']
    assert all(tree(OUT / role) == receipt['sources'][role] for role in BASES)
    assert all(sha(ROOT / name) == h for name, h in receipt['installed'].items())
    assert all(sha(ROOT / name) == h for name, h in receipt['protected'].items())
    assert not (home / UI).exists(), 'Saved-profile UI shadows the installed module'
    for role in ('engine', 'ui'):
        assert read(OUT / f'build-{role}.json') == dict(source=sha(RECEIPT), sha256=sha(binary(role)), in_game_tested=False)
    mapping = files()
    after = {name: sha(path) for name, path in mapping.items()}
    backup = ROOT / 'dist/backups' / f'text-colors-{datetime.now():%Y%m%d-%H%M%S}'
    record = dict(before=receipt['installed'], after=after, protected=receipt['protected'],
        backup=str(backup), preserved_settings=settings, source_sha256=sha(RECEIPT),
        builds={role: sha(OUT / f'build-{role}.json') for role in ('engine', 'ui')},
        in_game_tested=False, in_game_testing='User requested to perform in-game testing personally.',
        gameplay_unchanged=True, controller_update_preserved=True, menu_selection_preserved=True)
    import_module('Install-Handedness').install_transaction(ROOT, mapping, receipt['installed'], after,
        receipt['protected'], backup, INSTALL, record)
    assert all(sha(Path(name)) == h for name, h in settings.items())
    print('Installed text colors and saved chat color. Gameplay, input updates, assets and cfgs preserved.', flush=True)


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'prepare': prepare()
    elif action == 'refresh': refresh()
    elif action == 'install': install()
    elif action in ('engine', 'ui'): build(action)
    else: raise SystemExit('Choose prepare, refresh, engine, ui or install.')
