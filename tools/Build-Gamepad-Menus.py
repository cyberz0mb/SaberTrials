"""Build and install gamepad menu navigation on the combined Windows client."""
from datetime import datetime
from importlib import import_module, util
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
builder = import_module('Build-Translator')
ROOT = builder.ROOT
OUT = ROOT/'dist/gamepad-menus-01'
RECEIPT = OUT/'source-receipt.json'
builder.OUT, builder.RECEIPT = OUT, RECEIPT
sha, read, write, tree = builder.sha, builder.read, builder.write, builder.tree
BASES = {'engine':ROOT/'dist/translator-02', 'frontend':ROOT/'dist/dlc-pose-01'}
builder.ROLES['engine-qa'] = builder.ROLES['engine']


def prepare(refresh=False):
    prior = read(ROOT/'dist/dlc-pose-install.json')
    installed = {**prior['protected'], **prior['after']}
    assert all(sha(ROOT/name)==digest for name,digest in installed.items()), 'Installed client changed'
    OUT.mkdir(exist_ok=True)
    for role, base in BASES.items():
        assert tree(base/role)==read(base/'source-receipt.json')['sources'][role], role+' source changed'
        if not refresh:
            shutil.copytree(base/role,OUT/role,dirs_exist_ok=True)
    for role, base in (('engine',BASES['engine']),('ui',BASES['frontend'])):
        _, _, library, name = builder.ROLES[role]
        filename = library+('.exe' if role=='engine' else '.dll')
        assert sha(base/('build-'+role)/'Release'/filename)==installed[name], role+' binary changed'
    source = ROOT/'development-source'
    spec = util.spec_from_file_location('menu_overlay',source/'controls/gamepad_menu_overlay.py')
    overlay = util.module_from_spec(spec)
    spec.loader.exec_module(overlay)
    if refresh:
        files = {'engine':('shared/sdl/sdl_input.cpp','shared/sys/sys_public.h','shared/sys/sys_event.cpp',
                           'codemp/client/cl_keys.cpp','codemp/client/cl_uiapi.cpp','codemp/qcommon/common.cpp'),
                 'frontend':('codemp/ui/ui_main.c','codemp/ui/ui_st_saber_inspect.inc','codemp/ui/ui_st_controls.inc')}
        for role, paths in files.items():
            for name in paths:
                shutil.copyfile(BASES[role]/role/name,OUT/role/name)
    overlay.wire(OUT/'engine',OUT/'frontend',source)
    write(RECEIPT,dict(installed=installed,sources={role:tree(OUT/role) for role in BASES}))
    print('Prepared gamepad menu sources.',flush=True)


def files(qa=False):
    return {builder.ROLES[role][3]:builder.binary(role) for role in (('engine-qa','qa') if qa else ('engine','ui'))}


def install(tag):
    helper = import_module('Install-Profile-Browser')
    helper.stopped()
    home, settings = helper.settings()
    receipt = read(RECEIPT)
    installed = receipt['installed']
    assert all(sha(ROOT/name)==digest for name,digest in installed.items()), 'Installed client changed during testing'
    sources = files()
    assert not (home/'uix86_64.dll').exists(), 'Profile has a UI module override'
    after = {name:sha(path) for name,path in sources.items()}
    for role in ('engine','engine-qa','ui','qa'):
        assert read(OUT/f'build-{role}.json')==dict(source=sha(RECEIPT),sha256=sha(builder.binary(role)))
    evidence = OUT/tag/'result.json'
    report = read(evidence)
    assert report['source']==sha(RECEIPT) and report['files']=={name:sha(path) for name,path in files(qa=True).items()}
    before = {name:installed[name] for name in sources}
    protected = {name:digest for name,digest in installed.items() if name not in sources}
    backup = ROOT/'dist/backups'/f'gamepad-menus-{datetime.now():%Y%m%d-%H%M%S}'
    payload = dict(before=before,after=after,protected=protected,backup=str(backup),
                   source_sha256=sha(RECEIPT),evidence=sha(evidence),preserved_settings=settings)
    import_module('Install-Handedness').install_transaction(ROOT,sources,before,after,protected,backup,
        ROOT/'dist/gamepad-menus-install.json',payload)
    print('Installed gamepad menu navigation.')


if __name__=='__main__':
    operation = sys.argv[1]
    if operation in ('prepare','refresh'):
        prepare(operation=='refresh')
    elif operation=='install':
        install(sys.argv[2])
    else:
        builder.build(operation)
