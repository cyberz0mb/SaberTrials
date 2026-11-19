"""Build the server-only bot dialogue change on the installed combined game."""
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
OUT = ROOT/'dist/bot-chat-01'
SOURCE = ROOT/'development-source/bot-chat'
BASE = ROOT/'dist/weapon-dlc-01/game'
RECEIPT = OUT/'source-receipt.json'
LIB = 'jampgamex86_64.dll'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    Path(path).write_text(json.dumps(data, indent=2)+'\n')


def tree(path):
    return {p.relative_to(path).as_posix(): sha(p) for p in sorted(Path(path).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def files():
    return {LIB: OUT/'build/Release'/LIB}


def prepare():
    prior = read(ROOT/'dist/translator-install.json')
    installed = {**prior['protected'], **prior['after']}
    assert all(sha(ROOT/n) == h for n, h in installed.items()), 'Installed baseline changed'
    assert sha(BASE.parent/'build-game/Release'/LIB) == installed[LIB]
    baseline = tree(BASE)
    assert baseline == read(BASE.parent/'source-receipt.json')['sources']['game']
    OUT.mkdir(exist_ok=True)
    shutil.copytree(BASE, OUT/'game', dirs_exist_ok=True)
    spec = util.spec_from_file_location('bot_chat_overlay', SOURCE/'overlay.py')
    overlay = util.module_from_spec(spec)
    spec.loader.exec_module(overlay)
    overlay.apply(OUT/'game')
    sources = tree(OUT/'game')
    assert {n for n in baseline if baseline[n] != sources[n]} == {
        'codemp/game/ai_main.c', 'codemp/game/ai_main.h', 'codemp/game/ai_util.c'}
    assert sources.keys() - baseline.keys() == {'codemp/game/ai_st_chat.inc', 'codemp/game/st_bot_profile.h'}
    write(RECEIPT, dict(installed=installed, baseline=baseline, sources=sources, authored=tree(SOURCE)))
    print('Prepared profile-first dialogue on the verified installed gameplay.', flush=True)


def build():
    assert tree(OUT/'game') == read(RECEIPT)['sources']
    flags = ('BuildMPEngine', 'BuildMPDed', 'BuildMPGame', 'BuildMPCGame', 'BuildMPUI',
             'BuildMPRdVanilla', 'BuildMPRend2', 'BuildSPEngine', 'BuildSPGame', 'BuildSPRdVanilla')
    with (OUT/'build.log').open('w') as log:
        for command in (
            ['cmake', '-S', str(OUT/'game'), '-B', str(OUT/'build'), '-G', 'Visual Studio 18 2026',
             '-A', 'x64', '-DST_STAFF_QA=OFF', '-DST_DEPS='+str(ROOT/'dist/handedness-baseline-06/deps'),
             *[f'-D{f}={"ON" if f == "BuildMPGame" else "OFF"}' for f in flags]],
            ['cmake', '--build', str(OUT/'build'), '--config', 'Release', '--parallel', '5',
             '--target', 'jampgamex86_64']):
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    write(OUT/'build.json', dict(source=sha(RECEIPT), files={n:sha(p) for n,p in files().items()}))
    print('Built gameplay module.', flush=True)


def test():
    with (OUT/'tests.log').open('w') as log:
        for command in (
            ['cmake', '-S', str(ROOT/'tests/bot-chat'), '-B', str(OUT/'tests'),
             '-G', 'Visual Studio 18 2026', '-A', 'x64'],
            ['cmake', '--build', str(OUT/'tests'), '--config', 'Release', '--parallel', '3'],
            ['ctest', '--test-dir', str(OUT/'tests'), '-C', 'Release', '--output-on-failure']):
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    write(OUT/'tests.json', dict(authored=tree(SOURCE), tests=tree(ROOT/'tests/bot-chat'), log=sha(OUT/'tests.log')))
    print('Passed dialogue selection, fallback, formatting, rate-limit and safety checks.', flush=True)


def validate():
    receipt = read(RECEIPT)
    assert tree(SOURCE) == receipt['authored'] and tree(OUT/'game') == receipt['sources']
    hashes = {n:sha(p) for n,p in files().items()}
    assert read(OUT/'build.json') == dict(source=sha(RECEIPT), files=hashes)
    assert read(OUT/'tests.json') == dict(authored=tree(SOURCE), tests=tree(ROOT/'tests/bot-chat'), log=sha(OUT/'tests.log'))
    matches = [p for p in sorted(OUT.glob('runtime-*/result.json'))
               if read(p)['source'] == sha(RECEIPT) and read(p)['files'] == hashes]
    assert matches, 'Run the current live bot check first'
    write(OUT/'validation.json', dict(source=sha(RECEIPT), files=hashes, tests=sha(OUT/'tests.json'),
          runtime=dict(path=str(matches[-1]), sha256=sha(matches[-1]))))
    print('Validated current source, build and live bot evidence.', flush=True)


def install():
    helper = import_module('Install-Profile-Browser')
    helper.stopped()
    home, settings = helper.settings()
    validate()
    current = read(RECEIPT)['installed']
    assert all(sha(ROOT/n) == h for n,h in current.items())
    assert not (home/LIB).exists(), 'Home profile shadows the gameplay module'
    sources = files()
    before = {LIB:current[LIB]}
    after = {LIB:sha(sources[LIB])}
    protected = {n:h for n,h in current.items() if n != LIB}
    backup = ROOT/'dist/backups'/f'bot-chat-{datetime.now():%Y%m%d-%H%M%S}'
    payload = dict(before=before, after=after, protected=protected, backup=str(backup),
        preserved_settings=settings, source_sha256=sha(RECEIPT), evidence=sha(OUT/'validation.json'))
    import_module('Install-Handedness').install_transaction(ROOT, sources, before, after, protected,
        backup, ROOT/'dist/bot-chat-install.json', payload)
    assert all(sha(Path(n)) == h for n,h in settings.items())
    print('Installed profile-first bot chat; translator, gameplay features and settings preserved.', flush=True)


if __name__ == '__main__':
    {'prepare':prepare, 'build':build, 'test':test, 'validate':validate, 'install':install}[sys.argv[1]]()
