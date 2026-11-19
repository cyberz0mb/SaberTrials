"""Build the Windows menu localization on the verified FFA/controller install."""
from datetime import datetime
from importlib import import_module, util
from pathlib import Path
import shutil
import sys
import json
import re

sys.dont_write_bytecode = True
build = import_module('Build-Translator')
ROOT = build.ROOT
OUT = ROOT/'dist/menu-language-01'
SOURCE = ROOT/'development-source/menu-language'
BASE = ROOT/'dist/ffa-controller-01'
RECEIPT = OUT/'source-receipt.json'
FIRST_INSTALL = ROOT/'dist/menu-language-install.json'
LEGACY_PACK = 'zzzzzzzzzzzzzz_sabertrials_languages.pk3'
REVISION_INSTALL = ROOT/'dist/menu-language-revision-install.json'
INSTALL_RECEIPT = (REVISION_INSTALL if FIRST_INSTALL.is_file() and
                   LEGACY_PACK in build.read(FIRST_INSTALL)['after'] else FIRST_INSTALL)
build.OUT, build.RECEIPT = OUT, RECEIPT
sha, read, write, tree = build.sha, build.read, build.write, build.tree
ROLES = ('engine','ui','qa','rend2','vanilla')


def prepare():
    prior = read(ROOT/'dist/ffa-controller-install.json')
    installed = {**prior['protected'], **prior['after']}
    if INSTALL_RECEIPT == REVISION_INSTALL:
        installed.update(read(FIRST_INSTALL)['after'])
    assert all(sha(ROOT/name)==digest for name,digest in installed.items()), 'Installed files changed'
    for role in ('engine','frontend'):
        assert tree(BASE/role)==read(BASE/'source-receipt.json')['sources'][role], role+' source changed'
        shutil.copytree(BASE/role,OUT/role,dirs_exist_ok=True)
    spec = util.spec_from_file_location('menu_language_overlay',SOURCE/'overlay.py')
    overlay = util.module_from_spec(spec)
    spec.loader.exec_module(overlay)
    overlay.apply(OUT/'engine',OUT/'frontend')
    embed_catalogs()
    write(RECEIPT,dict(installed=installed,sources={role:tree(OUT/role) for role in ('engine','frontend')}))
    print('Prepared menu localization on the current client')


def embed_catalogs():
    review = import_module('Build-Menu-Languages')
    languages = json.loads((ROOT/'development-source/translator/languages.json').read_text())
    directory = OUT/'engine/codemp/win32'
    resources = directory/'menu-catalogs'
    resources.mkdir(exist_ok=True)
    declarations = []
    for language in languages[1:]:
        path = SOURCE/'catalogs'/f'{language["id"]}.tsv'
        catalog = dict(row.split('\t',1) for row in path.read_text(encoding='utf8').splitlines())
        catalog = {key:value for key,value in catalog.items()
                   if not re.search(r'(.{2,12})(?:[ ,、，]*\1){5,}',value,re.I)}
        catalog.update(review.reviewed(language['code']))
        data = ''.join(f'{key}\t{value}\n' for key,value in sorted(catalog.items())).encode('utf8')
        assert 0 < len(data) <= 1024*1024
        (resources/path.name).write_bytes(data)
        declarations.append(f'{4100+language["id"]} RCDATA "menu-catalogs/{path.name}"')
    script = directory/'openjk.rc'
    script.write_bytes(script.read_bytes()+('\n'+'\n'.join(declarations)+'\n').encode('ascii'))


def files(qa=False):
    roles = ('engine','qa' if qa else 'ui','rend2','vanilla')
    return {build.ROLES[role][3]:build.binary(role) for role in roles}


def install():
    helper = import_module('Install-Profile-Browser')
    helper.stopped()
    home,settings = helper.settings()
    assert not (home/'uix86_64.dll').exists(), 'Profile has a UI override'
    baseline = read(RECEIPT)['installed']
    sources = files()
    assert all(sha(ROOT/name)==digest for name,digest in baseline.items())
    for role in ROLES:
        assert read(OUT/f'build-{role}.json')==dict(source=sha(RECEIPT),sha256=sha(build.binary(role)))
    after = {name:sha(path) for name,path in sources.items()}
    proof = OUT/'review-rd-rend2/result.json'
    for renderer in ('rd-rend2','rd-vanilla'):
        review = read(OUT/f'review-{renderer}/result.json')
        assert review['files']==after and review['source']==sha(RECEIPT)
    before = {name:baseline.get(name) for name in sources}
    protected = {name:digest for name,digest in baseline.items()
                 if name not in sources and name != LEGACY_PACK}
    backup = ROOT/'dist/backups'/f'menu-language-{datetime.now():%Y%m%d-%H%M%S}'
    state = dict(before=before,after=after,protected=protected,backup=str(backup),evidence=sha(proof),
                 source=sha(RECEIPT),preserved_settings=settings)
    if LEGACY_PACK in baseline:
        state['retired_catalog'] = {LEGACY_PACK:baseline[LEGACY_PACK]}
    import_module('Install-Handedness').install_transaction(ROOT,sources,before,after,protected,backup,
        INSTALL_RECEIPT,state)
    if LEGACY_PACK in baseline:
        old_pack = ROOT/LEGACY_PACK
        assert sha(old_pack) == baseline[LEGACY_PACK]
        old_pack.rename(backup/LEGACY_PACK)
    print('Installed menu localization')


if __name__ == '__main__':
    op = sys.argv[1]
    if op == 'prepare': prepare()
    elif op == 'install': install()
    else: build.build(op)
