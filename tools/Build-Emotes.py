"""Build the localized Saber Trials client and server with emote support."""
from datetime import datetime
from importlib import import_module, util
import os
import shutil
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZipFile

sys.dont_write_bytecode = True
builder = import_module('Build-Translator')
ROOT = builder.ROOT
OUT = ROOT/'dist/emotes-01'
RECEIPT = OUT/'source-receipt.json'
FIRST_INSTALL = ROOT/'dist/emotes-install.json'
PREVIOUS_UPDATE = ROOT/'dist/emotes-update-install.json'
INSTALL = ROOT/'dist/emote-wheel-install.json'
WHEEL_ART = 'zzzzzzzzzzzzzz_sabertrials_emote_wheel.pk3'
PREVIOUS = ROOT/'dist/menu-language-revision-install.json'
SOURCE = ROOT/'development-source/emotes'
BASES = {'engine': ROOT/'dist/menu-language-01/engine',
         'frontend': ROOT/'dist/menu-language-01/frontend',
         'game': ROOT/'dist/dlc-pose-01/game'}
builder.OUT, builder.RECEIPT = OUT, RECEIPT
builder.ROLES.update(game=('game','BuildMPGame','jampgamex86_64','jampgamex86_64.dll'),
                     dedicated=('engine','BuildMPDed','openjkded.x86_64','client/openjkded.x86_64.exe'))
ROLES = ('engine','ui','cgame','game','dedicated')
sha, read, write, tree = builder.sha, builder.read, builder.write, builder.tree


def baseline():
    prior = read(PREVIOUS)
    return {**prior['protected'], **prior['after']}


def files():
    return {**{builder.ROLES[role][3]: builder.binary(role) for role in ROLES}, WHEEL_ART: OUT/WHEEL_ART}


def package_wheel():
    art = OUT/'wheel-art'
    dependencies = str(ROOT/'dist/hud-style-deps')
    subprocess.run([sys.executable,str(SOURCE/'wheel_art.py'),str(art)],check=True,
                   env={**os.environ,'PYTHONPATH':dependencies})
    with ZipFile(OUT/WHEEL_ART,'w',compression=ZIP_DEFLATED) as archive:
        for image in sorted(art.glob('emote_*.png')):
            archive.write(image,'ui/assets/sabertrials/rich/'+image.name)


def prepare():
    current = baseline()
    for install_receipt in (FIRST_INSTALL,PREVIOUS_UPDATE,INSTALL):
        if install_receipt.exists():
            current.update(read(install_receipt)['after'])
    assert all(sha(ROOT/name)==digest for name,digest in current.items()), 'Client or server baseline changed'
    for role,path in BASES.items():
        assert tree(path) == read(path.parent/'source-receipt.json')['sources'][role], role+' source changed'
        shutil.copytree(path,OUT/role,dirs_exist_ok=True)
    spec = util.spec_from_file_location('emote_overlay',SOURCE/'overlay.py')
    overlay = util.module_from_spec(spec)
    spec.loader.exec_module(overlay)
    overlay.apply(*(OUT/role for role in BASES))
    package_wheel()
    write(RECEIPT,dict(installed=current,sources={role:tree(OUT/role) for role in BASES},authored=tree(SOURCE),
                       wheel_art=sha(OUT/WHEEL_ART)))


def install():
    helper = import_module('Install-Profile-Browser')
    helper.stopped()
    home,settings = helper.settings()
    receipt = read(RECEIPT)
    assert tree(SOURCE) == receipt['authored']
    assert not any((home/name).exists() for name in ('uix86_64.dll','cgamex86_64.dll','jampgamex86_64.dll'))
    sources = files()
    after = {name:sha(path) for name,path in sources.items()}
    assert after[WHEEL_ART] == receipt['wheel_art']
    evidence = {}
    for target in ('rd-rend2','rd-vanilla','network'):
        proof = OUT/target/'result.json'
        assert read(proof)['files'] == after and read(proof)['source'] == sha(RECEIPT)
        evidence[target] = sha(proof)
    for role in ROLES:
        assert read(OUT/f'build-{role}.json') == dict(source=sha(RECEIPT),sha256=sha(builder.binary(role)))
    previous = receipt['installed']
    assert all(sha(ROOT/name)==digest for name,digest in previous.items())
    before = {name:previous.get(name) for name in sources}
    protected = {name:value for name,value in previous.items() if name not in sources}
    backup = ROOT/'dist/backups'/f'emotes-{datetime.now():%Y%m%d-%H%M%S}'
    state = dict(before=before,after=after,protected=protected,evidence=evidence,
                 backup=str(backup),preserved_settings=settings)
    import_module('Install-Handedness').install_transaction(ROOT,sources,before,after,protected,backup,INSTALL,state)
    (ROOT/'dlc/emotes').mkdir(parents=True,exist_ok=True)


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'prepare':
        prepare()
    elif action == 'install':
        install()
    else:
        builder.build(action)
