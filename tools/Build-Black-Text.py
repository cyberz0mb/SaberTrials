"""Remove added black text outlines on the current combined client/UI."""
from importlib import import_module
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
b = import_module('Build-Text-Colors')
b.OUT = b.ROOT / 'dist/black-text-01'
b.RECEIPT = b.OUT / 'source-receipt.json'
b.INSTALL = b.ROOT / 'dist/black-text-install.json'
b.BASES = {'engine': b.ROOT / 'dist/anti-script/engine',
           'frontend': b.ROOT / 'dist/multiteam-01/frontend'}


def prepare():
    root = b.ROOT
    installed = {name: b.sha(root / name) for name in (b.EXE, b.UI)}
    assert installed[b.EXE] == b.sha(root / 'dist/anti-script/build/Release/openjk.x86_64.exe')
    assert installed[b.UI] == b.sha(root / 'dist/multiteam-01/build-frontend/Release/uix86_64.dll')
    assert installed[b.UI] == b.read(root / 'dist/multiteam-install.json')['after'][b.UI]
    assert not b.RECEIPT.exists(), 'Prepared receipt exists; use engine/ui or a fresh output directory'
    b.OUT.mkdir(exist_ok=True)
    before = {role: b.tree(path) for role, path in b.BASES.items()}
    for role, source in b.BASES.items():
        def copy_changed(source, target):
            if not Path(target).is_file() or b.sha(source) != b.sha(target):
                shutil.copyfile(source, target)
            return str(target)
        shutil.copytree(source, b.OUT / role, dirs_exist_ok=True, copy_function=copy_changed)
        assert b.tree(b.OUT / role) == before[role]
    engine = b.OUT / 'engine/codemp/client'
    ui = b.OUT / 'frontend/codemp/ui'
    shutil.copyfile(root / 'development-source/translator/st_chat_raster.h', engine / 'st_chat_raster.h')
    shutil.copyfile(root / 'development-source/setup/ui_st_chat_preview.inc', ui / 'ui_st_chat_preview.inc')
    patch = b.support.module('plain_black_overlay', b.SOURCE / 'overlay.py')
    patch.remove_black_outline(ui / 'ui_st_rich.inc')
    sources = {role: b.tree(b.OUT / role) for role in b.BASES}
    for role, changed in {'engine': {'codemp/client/st_chat_raster.h'},
                          'frontend': {'codemp/ui/ui_st_chat_preview.inc', 'codemp/ui/ui_st_rich.inc'}}.items():
        assert sources[role].keys() == before[role].keys()
        assert {n for n in sources[role] if sources[role][n] != before[role][n]} == changed
    raster = (engine / 'st_chat_raster.h').read_text()
    assert 'outlineBlack' not in raster and 'colors[10][3]={{0,0,0}' in raster
    assert 'if(c[0]==0&&c[1]==0&&c[2]==0)' not in (ui / 'ui_st_rich.inc').read_text()
    protected = {}
    paths = [*root.glob('*.dll'), *root.glob('*.pk3'), *root.joinpath('client').glob('*'),
             *root.joinpath('ui').rglob('*.menu'), *root.joinpath('tools/launchers').glob('*.cmd')]
    for path in paths:
        name = path.relative_to(root).as_posix()
        if path.is_file() and name not in installed:
            protected[name] = b.sha(path)
    b.write(b.RECEIPT, dict(installed=installed, protected=protected, sources=sources,
        authored=b.authored(), baseline_sources=before, pure_black=True,
        baseline_binaries={b.EXE: 'dist/anti-script/build/Release/openjk.x86_64.exe',
                           b.UI: 'dist/multiteam-01/build-frontend/Release/uix86_64.dll'}))
    print('Prepared plain RGB 0/0/0 black text on the installed combined client.', flush=True)


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'prepare': prepare()
    elif action == 'install': b.install()
    elif action in ('engine', 'ui'):
        if action == 'engine': b.DEPS = b.ROOT / 'dist/staff-deps'
        b.build(action)
    else: raise SystemExit('Choose prepare, engine, ui or install.')
