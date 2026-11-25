"""Build/install Berserker pursuit on the exact installed combined gameplay.

No game is launched and no gameplay tests are performed by this tool.
"""
from datetime import datetime
from importlib import import_module, util
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist/bot-navigation-01'
SOURCE = ROOT / 'development-source/bot-navigation'
BASE = ROOT / 'dist/emotes-01/game'
RECEIPT = OUT / 'source-receipt.json'
INSTALL = ROOT / 'dist/bot-navigation-install.json'
LIB = 'jampgamex86_64.dll'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + '\n')


def tree(path):
    return {p.relative_to(path).as_posix(): sha(p) for p in sorted(Path(path).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def binary():
    return OUT / 'build/Release' / LIB


def prepare():
    baseline = tree(BASE)
    assert baseline == read(BASE.parent / 'source-receipt.json')['sources']['game'], 'Combined source changed'
    installed = sha(ROOT / LIB)
    expected = sha(BASE.parent / 'build-game/Release' / LIB)
    assert installed == expected, 'Installed gameplay differs from the combined source baseline'
    assert read(ROOT / 'dist/emote-wheel-install.json')['after'][LIB] == installed
    OUT.mkdir(exist_ok=True)
    destination = OUT / 'game'
    assert not destination.exists(), 'Prepared source exists; use build, or a new output directory'
    shutil.copytree(BASE, destination)
    spec = util.spec_from_file_location('berserker_navigation_overlay', SOURCE / 'overlay.py')
    overlay = util.module_from_spec(spec)
    spec.loader.exec_module(overlay)
    overlay.apply(destination)
    sources = tree(destination)
    changed = {name for name in baseline if baseline[name] != sources[name]}
    assert changed == {'codemp/game/ai_main.c', 'codemp/game/ai_main.h', 'codemp/game/g_svcmds.c'}, changed
    assert sources.keys() - baseline.keys() == {
        'codemp/game/ai_st_berserker.inc', 'codemp/game/st_berserker_state.h'}
    protected = {p.relative_to(ROOT).as_posix(): sha(p)
                 for p in [*ROOT.glob('*.dll'), *ROOT.glob('*.pk3'), *ROOT.joinpath('client').rglob('*')]
                 if p.is_file() and p != ROOT / LIB}
    write(RECEIPT, dict(installed=installed, protected=protected, baseline=baseline,
                       sources=sources, authored=tree(SOURCE)))
    print('Prepared Berserker navigation over the exact installed gameplay source.', flush=True)


def refresh():
    """Refresh only our editable include files after a compiler-driven correction."""
    receipt = read(RECEIPT)
    assert sha(SOURCE / 'overlay.py') == receipt['authored']['overlay.py'], 'Overlay changed; prepare a fresh source tree'
    for name in ('ai_st_berserker.inc', 'st_berserker_state.h'):
        shutil.copyfile(SOURCE / name, OUT / 'game/codemp/game' / name)
    actual = tree(OUT / 'game')
    for name, digest in receipt['sources'].items():
        if name not in ('codemp/game/ai_st_berserker.inc', 'codemp/game/st_berserker_state.h'):
            assert actual[name] == digest, 'Unexpected prepared-source change: ' + name
    receipt['sources'] = actual
    receipt['authored'] = tree(SOURCE)
    write(RECEIPT, receipt)


def build():
    receipt = read(RECEIPT)
    assert tree(OUT / 'game') == receipt['sources'] and tree(SOURCE) == receipt['authored']
    flags = ('BuildMPEngine', 'BuildMPDed', 'BuildMPGame', 'BuildMPCGame', 'BuildMPUI',
             'BuildMPRdVanilla', 'BuildMPRend2', 'BuildSPEngine', 'BuildSPGame', 'BuildSPRdVanilla')
    with (OUT / 'build.log').open('w') as log:
        for command in (
            ['cmake', '-S', str(OUT / 'game'), '-B', str(OUT / 'build'), '-G', 'Visual Studio 18 2026',
             '-A', 'x64', '-DST_STAFF_QA=OFF', '-DST_DEPS=' + str(ROOT / 'dist/handedness-baseline-06/deps'),
             *[f'-D{f}={"ON" if f == "BuildMPGame" else "OFF"}' for f in flags]],
            ['cmake', '--build', str(OUT / 'build'), '--config', 'Release', '--parallel', '5',
             '--target', 'jampgamex86_64']):
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    write(OUT / 'build.json', dict(source=sha(RECEIPT), library=sha(binary()), gameplay_tested=False))
    print('Compiled production gameplay module. Gameplay testing is left to the user.', flush=True)


def install():
    helper = import_module('Install-Profile-Browser')
    helper.stopped()
    home, settings = helper.settings()
    receipt = read(RECEIPT)
    assert tree(SOURCE) == receipt['authored'] and tree(OUT / 'game') == receipt['sources']
    assert read(OUT / 'build.json') == dict(source=sha(RECEIPT), library=sha(binary()), gameplay_tested=False)
    assert sha(ROOT / LIB) == receipt['installed']
    assert all(sha(ROOT / name) == digest for name, digest in receipt['protected'].items())
    assert not (home / LIB).exists(), 'Home profile shadows the gameplay module'
    backup = ROOT / 'dist/backups' / f'bot-navigation-{datetime.now():%Y%m%d-%H%M%S}'
    before, after = {LIB: receipt['installed']}, {LIB: sha(binary())}
    payload = dict(before=before, after=after, protected=receipt['protected'], backup=str(backup),
                   preserved_settings=settings, source_sha256=sha(RECEIPT),
                   build_sha256=sha(OUT / 'build.json'), gameplay_tested=False,
                   gameplay_testing='User requested to perform gameplay testing personally.')
    import_module('Install-Handedness').install_transaction(
        ROOT, {LIB: binary()}, before, after, receipt['protected'], backup, INSTALL, payload)
    assert all(sha(Path(name)) == digest for name, digest in settings.items())
    print('Installed Berserker navigation; backup and settings preserved. No game launched.', flush=True)


if __name__ == '__main__':
    {'prepare': prepare, 'refresh': refresh, 'build': build, 'install': install}[sys.argv[1]]()
