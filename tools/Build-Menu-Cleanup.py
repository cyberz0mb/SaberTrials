"""Build and install the menu cleanup on the verified multiplayer UI source."""
import argparse
import datetime
from importlib import import_module
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'dist/menu-rollout-01'
OUT = ROOT / 'dist/menu-cleanup-03'
PREVIOUS = ROOT / 'dist/menu-cleanup-02-install.json'
STATE = ROOT / 'dist/menu-cleanup-03-install.json'

sys.path.insert(0, str(ROOT / 'tools'))
rollout = import_module('Build-Menu-Rollout')
sha, read, tree, load = rollout.sha, rollout.read, rollout.tree, rollout.load
PACKAGE = rollout.PACKAGE

OVERLAYS = {
    'ui_st_legacy.inc': 'rich-menu',
    'ui_st_controls.inc': 'controls',
    'ui_st_controls_draw.inc': 'controls',
    'ui_st_setup_draw.inc': 'setup',
    'ui_st_profile.inc': 'profile',
    'ui_st_profile_draw.inc': 'profile',
}


def inputs():
    source = ROOT / 'development-source'
    files = [Path(__file__), ROOT / 'ui/jamp/rules_games.menu', ROOT / 'ui/jamp/rules.menu',
             ROOT / 'ui/jamp/multiplayer.menu', ROOT / 'ui/assets/sabertrials/trophy.png']
    files.extend(source / folder / name for name, folder in OVERLAYS.items())
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in files}


def prepare():
    baseline = read(BASE / 'source-receipt.json')
    assert tree(BASE / 'frontend') == baseline['sources'], 'Rollout source drift'
    assert sha(ROOT / PACKAGE) == baseline['package_sha256'], 'Installed frame artwork drift'
    OUT.mkdir(exist_ok=True)
    frontend = OUT / 'frontend'
    shutil.copytree(BASE / 'frontend', frontend, dirs_exist_ok=True)
    ui = frontend / 'codemp/ui'
    for name, folder in OVERLAYS.items():
        source = ROOT / 'development-source' / folder / name
        if name != 'ui_st_controls.inc':
            shutil.copy2(source, ui / name)
            continue
        # The installed Controls source also routes Saved Configs through Setup.
        destination = ui / name
        current, revised = destination.read_text(), source.read_text()
        for start, stop in (('static void SCUI_Label(', 'static void SCUI_Border('),
                            ('static void SCUI_Button(', 'static void SCUI_Field(')):
            rollout.patch(destination, current[current.index(start):current.index(stop)],
                          revised[revised.index(start):revised.index(stop)])
    rollout.patch(
        ui / 'ui_shared.c', 'void Item_TextField_Paint(itemDef_t *item) {',
        '#ifdef UI_BUILD\nextern void ST_LegacyEditField(itemDef_t*,float,float,const char*);\n#endif\n'
        'void Item_TextField_Paint(itemDef_t *item) {')
    rollout.patch(
        ui / 'ui_shared.c', 'offset = (item->text && *item->text) ? 8 : 0;',
        'offset = (item->text && *item->text) ? 8 : 0;\n#ifdef UI_BUILD\n'
        '\tST_LegacyEditField(item,item->textRect.x+item->textRect.w+offset,'
        'item->textRect.y,buff+editPtr->paintOffset);\n#endif')
    shutil.copy2(ROOT / PACKAGE, OUT / PACKAGE)
    receipt = {
        'baseline_receipt_sha256': sha(BASE / 'source-receipt.json'),
        'prior_install_sha256': sha(PREVIOUS),
        'inputs': inputs(),
        'sources': tree(frontend),
        'package_sha256': sha(OUT / PACKAGE),
    }
    (OUT / 'source-receipt.json').write_text(json.dumps(receipt, indent=2))


def build(qa):
    builder = load('cleanup_profile_builder', ROOT / 'tools/Build-Profile.py')
    builder.OUT = OUT
    original = builder.tree
    builder.tree = lambda p: inputs() if p == builder.SRC else original(p)
    builder.build(qa)


def install():
    helper = load('cleanup_profile_helper', ROOT / 'tools/Install-Profile-Browser.py')
    helper.stopped()
    home, settings = helper.settings()
    assert not (home / 'uix86_64.dll').exists(), 'Home UI override requires inspection'
    assert not STATE.exists(), 'Menu cleanup already installed'
    old = read(PREVIOUS)
    record = read(OUT / 'build-record.json')
    receipt = read(OUT / 'source-receipt.json')
    assert receipt['inputs'] == inputs() and receipt['sources'] == tree(OUT / 'frontend')
    assert receipt['prior_install_sha256'] == sha(PREVIOUS)
    assert all(helper.sha(ROOT / n) == v for n, v in old['after'].items())
    dll = OUT / 'build/Release/uix86_64.dll'
    assert record['ui_api'] == 285 and not record['qa'] and record['ui_sha256'] == sha(dll)
    evidence = {}
    for role, qa, checker, renderer, height in (
        ('wide', True, 'Check-Menu-Rollout.py', 'rd-vanilla', 720),
        ('tall', True, 'Check-Menu-Rollout.py', 'rd-rend2', 1024),
        ('production', False, 'Check-Menu-Rollout.py', 'rd-vanilla', 720),
        ('rich', True, 'Check-Rich-Menus.py', 'rd-vanilla', 720),
    ):
        tag = 'cleanup-' + role + '-final'
        path = OUT / 'verification' / tag / 'result.json'
        proof = read(path)
        build_record = read(OUT / ('build-record-qa.json' if qa else 'build-record.json'))
        assert proof['passed'] and not proof['installed'] and proof['qa'] == qa
        assert proof['ui_sha256'] == build_record['ui_sha256']
        assert proof['source_receipt_sha256'] == build_record['source_receipt_sha256'] == sha(OUT / 'source-receipt.json')
        assert proof['checker_sha256'] == sha(ROOT / 'tools' / checker)
        assert proof['renderer'] == renderer and proof['height'] == height
        assert proof['package_sha256'] == receipt['package_sha256']
        assert proof['log_sha256'] == sha(path.parent / 'home/SaberTrials/qconsole.log')
        if role in ('wide', 'tall'):
            assert proof['matrix'] and 'rules-tournament-scrolled' in proof['screenshots']
        evidence[tag] = sha(path)
    mapping = {'uix86_64.dll': dll}
    before = {n: sha(ROOT / n) for n in mapping}
    after = {n: sha(p) for n, p in mapping.items()}
    protected = {n: helper.sha(ROOT / n) for n in {**old['protected'], **old['after']} if n not in mapping}
    backup = ROOT / 'dist/backups' / ('menu-cleanup-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    payload = dict(before=before, after=after, protected=protected, preserved_settings=settings,
                   backup=str(backup), evidence=evidence, source_receipt_sha256=sha(OUT / 'source-receipt.json'))
    tx = load('cleanup_transaction', ROOT / 'tools/Install-Handedness.py')
    tx.install_transaction(ROOT, mapping, before, after, protected, backup, STATE, payload)
    assert all(helper.sha(ROOT / n) == v for n, v in {**protected, **after}.items())
    assert all(helper.sha(Path(p)) == v for p, v in settings.items())
    print('Installed the verified menu cleanup and preserved player settings.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'build', 'install'])
    parser.add_argument('--qa', action='store_true')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'build':
        build(args.qa)
    else:
        install()
