"""Build the menu and HUD update against the combined Windows installation."""
from datetime import datetime
from importlib import import_module
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import shutil
import sys
from zipfile import ZipFile

sys.dont_write_bytecode = True
base = import_module('Build-Team-Appearance')
ROOT = base.ROOT
OUT = ROOT/'dist/ui-hud-polish-01'
RECEIPT = OUT/'source-receipt.json'
HUD = 'zzzzzzzzzzzzz_sabertrials_hud_theme.pk3'
ABOUT = 'ui/jamp/ingame_about.menu'
build_tools = base.build_tools
build_tools.OUT, build_tools.RECEIPT = OUT, RECEIPT
sha, read, write, tree, insert = base.sha, base.read, base.write, base.tree, base.insert


def prepare():
    prior = read(ROOT/'dist/tffa-kd-install.json')
    installed = {**prior['protected'], **prior['after'], ABOUT: sha(ROOT/ABOUT)}
    assert all(sha(ROOT/name) == digest for name, digest in installed.items())
    kd = ROOT/'dist/tffa-kd-01'
    combined = ROOT/'dist/team-appearance-01'
    verified = {'jampgamex86_64.dll': kd/'build-game/Release/jampgamex86_64.dll',
                'cgamex86_64.dll': kd/'build-frontend/Release/cgamex86_64.dll',
                'uix86_64.dll': combined/'build-ui/Release/uix86_64.dll',
                build_tools.EXE: combined/'build-engine/Release/openjk.x86_64.exe'}
    assert all(sha(path) == installed[name] for name, path in verified.items())
    paths = {'frontend': kd/'frontend', 'engine': combined/'engine', 'game': kd/'game'}
    baseline = {role: tree(path) for role, path in paths.items()}

    def copy_changed(source, target):
        if sha(Path(source)) != sha(Path(target)):
            shutil.copyfile(source,target)
        return str(target)

    with ThreadPoolExecutor(max_workers=3) as pool:
        copies = [pool.submit(shutil.copytree,path,OUT/role,dirs_exist_ok=True,copy_function=copy_changed)
                  for role,path in paths.items()]
        for copy in copies:
            copy.result()
    source = ROOT/'development-source'
    import_module('ui_hud_polish_overlay').wire(OUT/'frontend',OUT/'engine',OUT/'game',source,insert)

    art = OUT/'saber-icons'
    art.mkdir(exist_ok=True)
    import_module('hud_theme_art').icons(art)
    names = ('saber_mark.png','staff_mark.png','dual_mark.png')
    icons = {'gfx/sabertrials/hud_theme/'+name: (art/name).read_bytes() for name in names}
    with ZipFile(ROOT/HUD) as before, ZipFile(OUT/HUD, 'w') as after:
        assert set(icons) <= set(before.namelist())
        for item in before.infolist():
            after.writestr(item, icons.get(item.filename, before.read(item)))
    about = OUT/ABOUT
    about.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source/'menu/ingame_about.menu',about)
    sources = {role: tree(OUT/role) for role in paths}
    changed = {role: sorted(name for name, digest in files.items() if baseline[role].get(name)!=digest)
               for role,files in sources.items()}
    write(RECEIPT, dict(installed=installed,sources=sources,changed=changed,
                        assets={name: sha(OUT/name) for name in (HUD,ABOUT)}))
    print(changed)


def files(qa=False):
    roles = ('engine','qa' if qa else 'ui','cgame','game')
    return {build_tools.EXE: build_tools.binary(roles[0]),
            'uix86_64.dll': build_tools.binary(roles[1]),
            'cgamex86_64.dll': build_tools.binary(roles[2]),
            'jampgamex86_64.dll': build_tools.binary(roles[3]),
            HUD: OUT/HUD, ABOUT: OUT/ABOUT}


def install(*review_tags):
    helper = import_module('Install-Profile-Browser')
    helper.stopped()
    home, settings = helper.settings()
    receipt = read(RECEIPT)
    current = receipt['installed']
    assert all(sha(ROOT/name)==digest for name,digest in current.items())
    sources = files()
    assert not any((home/name).exists() for name in sources if name.endswith('.dll'))
    after = {name: sha(path) for name,path in sources.items()}
    assert all(after[name]==digest for name,digest in receipt['assets'].items())
    evidence = {}
    for tag in review_tags:
        path = OUT/tag/'result.json'
        report = read(path)
        assert report['source'] == sha(RECEIPT)
        assert report['files'] == {name: sha(p) for name,p in files(report['qa']).items()}
        evidence[report['mode']] = sha(path)
    assert set(evidence)=={'wide','tall','production'}
    before = {name: current[name] for name in sources}
    protected = {name: digest for name,digest in current.items() if name not in sources}
    backup = ROOT/'dist/backups'/f'ui-hud-polish-{datetime.now():%Y%m%d-%H%M%S}'
    state = ROOT/'dist/ui-hud-polish-install.json'
    payload = dict(before=before,after=after,protected=protected,backup=str(backup),evidence=evidence,
                   preserved_settings=settings,source_sha256=sha(RECEIPT))
    import_module('Install-Handedness').install_transaction(ROOT,sources,before,after,protected,backup,state,payload)
    assert all(sha(Path(name))==digest for name,digest in settings.items())
    print('Installed the UI and HUD update.')


if __name__=='__main__':
    if sys.argv[1]=='prepare':
        prepare()
    elif sys.argv[1]=='install':
        install(*sys.argv[2:])
    else:
        build_tools.build(sys.argv[1])
