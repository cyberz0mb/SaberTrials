"""Build/install visible native menu selections. Does not launch the game."""
from datetime import datetime
from importlib import import_module, util
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
support = import_module('Build-Vulkan')
ROOT = support.ROOT
OUT = ROOT / 'dist/menu-selection-01'
SOURCE = ROOT / 'development-source/menu-selection'
BASE = ROOT / 'dist/vulkan-01/frontend'
RECEIPT = OUT / 'source-receipt.json'
INSTALL = ROOT / 'dist/menu-selection-install.json'
LIB = 'uix86_64.dll'
MENUS = ('ui/jamp/createserver.menu', 'ui/jamp/ingame_callvote.menu')
sha, read, write, tree = support.sha, support.read, support.write, support.tree


def overlay():
    spec = util.spec_from_file_location('menu_selection_overlay', SOURCE / 'overlay.py')
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def files():
    return {LIB: OUT / 'build/Release' / LIB, **{name: OUT / 'menus' / name for name in MENUS}}


def prepare():
    assert tree(BASE) == read(BASE.parent / 'source-receipt.json')['sources']['frontend'], 'UI source changed'
    installed = sha(ROOT / LIB)
    assert installed == sha(BASE.parent / 'build-ui/Release' / LIB)
    assert read(ROOT / 'dist/vulkan-install.json')['after'][LIB] == installed
    OUT.mkdir(exist_ok=True)
    destination = OUT / 'frontend'
    assert not RECEIPT.exists(), 'Prepared receipt exists; use build or a fresh output directory'
    # A failed staging attempt can be resumed by restoring the pinned inputs;
    # compare bytes to avoid recopying thousands of unchanged source files.
    def copy_changed(source, target):
        if not Path(target).is_file() or sha(source) != sha(target):
            shutil.copyfile(source, target)
        return str(target)
    shutil.copytree(BASE, destination, dirs_exist_ok=True, copy_function=copy_changed)
    patch = overlay()
    patch.apply(destination)
    baseline, sources = tree(BASE), tree(destination)
    changed = {name for name in baseline if baseline[name] != sources[name]}
    assert changed == {'codemp/ui/ui_shared.c', 'codemp/ui/ui_st_legacy.inc'}, changed
    assert sources.keys() - baseline.keys() == {'codemp/ui/ui_st_selection.inc'}
    menus = {}
    for name in MENUS:
        target = OUT / 'menus' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        menus[name] = sha(ROOT / name)
        target.write_bytes(patch.menu(name, (ROOT / name).read_bytes()))
    targets = {LIB, *MENUS}
    protected = {}
    paths = [*ROOT.glob('*.dll'), *ROOT.glob('*.pk3'), *ROOT.joinpath('client').glob('*'),
             *ROOT.joinpath('ui').rglob('*.menu')]
    for path in paths:
        name = path.relative_to(ROOT).as_posix()
        if path.is_file() and name not in targets:
            protected[name] = sha(path)
    write(RECEIPT, dict(installed={LIB: installed, **menus}, protected=protected,
        baseline=sha(BASE.parent / 'source-receipt.json'), sources=sources, authored=tree(SOURCE),
        menus={name: sha(OUT / 'menus' / name) for name in MENUS}))
    print('Prepared selected-row rendering and Saber Trials team slot colors.', flush=True)


def refresh():
    receipt = read(RECEIPT)
    assert sha(SOURCE / 'overlay.py') == receipt['authored']['overlay.py'], 'Overlay changed; prepare a fresh source tree'
    shutil.copyfile(SOURCE / 'ui_st_selection.inc', OUT / 'frontend/codemp/ui/ui_st_selection.inc')
    actual = tree(OUT / 'frontend')
    for name, digest in receipt['sources'].items():
        if name != 'codemp/ui/ui_st_selection.inc':
            assert actual[name] == digest, 'Unexpected source change: ' + name
    receipt.update(sources=actual, authored=tree(SOURCE))
    write(RECEIPT, receipt)


def build():
    receipt = read(RECEIPT)
    assert tree(OUT / 'frontend') == receipt['sources'] and tree(SOURCE) == receipt['authored']
    flags = ('BuildMPEngine', 'BuildMPDed', 'BuildMPGame', 'BuildMPCGame', 'BuildMPUI',
             'BuildMPRdVanilla', 'BuildMPRend2', 'BuildMPRdVulkan',
             'BuildSPEngine', 'BuildSPGame', 'BuildSPRdVanilla')
    with (OUT / 'build.log').open('w') as log:
        for command in (
            ['cmake', '-S', str(OUT / 'frontend'), '-B', str(OUT / 'build'), '-G', 'Visual Studio 18 2026',
             '-A', 'x64', '-DST_STAFF_QA=OFF', '-DST_DEPS=' + str(ROOT / 'dist/handedness-baseline-06/deps'),
             *[f'-D{f}={"ON" if f == "BuildMPUI" else "OFF"}' for f in flags]],
            ['cmake', '--build', str(OUT / 'build'), '--config', 'Release', '--parallel', '5',
             '--target', 'uix86_64']):
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    write(OUT / 'build.json', dict(source=sha(RECEIPT), library=sha(files()[LIB]), in_game_tested=False))
    print('Compiled production UI. No game launched.', flush=True)


def install():
    helper = import_module('Install-Profile-Browser')
    helper.stopped()
    home, settings = helper.settings()
    receipt = read(RECEIPT)
    assert tree(SOURCE) == receipt['authored'] and tree(OUT / 'frontend') == receipt['sources']
    assert read(OUT / 'build.json') == dict(source=sha(RECEIPT), library=sha(files()[LIB]), in_game_tested=False)
    assert all(sha(ROOT / name) == digest for name, digest in receipt['installed'].items())
    assert all(sha(ROOT / name) == digest for name, digest in receipt['protected'].items())
    assert not (home / LIB).exists(), 'Saved-profile UI shadows the installed module'
    assert not any((home / name).exists() for name in MENUS), 'Saved-profile menus shadow this update'
    mapping = files()
    after = {name: sha(path) for name, path in mapping.items()}
    assert all(after[name] == digest for name, digest in receipt['menus'].items())
    backup = ROOT / 'dist/backups' / f'menu-selection-{datetime.now():%Y%m%d-%H%M%S}'
    record = dict(before=receipt['installed'], after=after, protected=receipt['protected'],
        backup=str(backup), preserved_settings=settings, source_sha256=sha(RECEIPT),
        build_sha256=sha(OUT / 'build.json'), in_game_tested=False,
        in_game_testing='User requested to perform in-game testing personally.',
        traveling_border_light_preserved=True, gameplay_unchanged=True)
    import_module('Install-Handedness').install_transaction(ROOT, mapping, receipt['installed'], after,
        receipt['protected'], backup, INSTALL, record)
    assert all(sha(Path(name)) == digest for name, digest in settings.items())
    print('Installed selection highlights and team colors; gameplay, assets, and cfgs preserved.', flush=True)


if __name__ == '__main__':
    {'prepare': prepare, 'refresh': refresh, 'build': build, 'install': install}[sys.argv[1]]()
