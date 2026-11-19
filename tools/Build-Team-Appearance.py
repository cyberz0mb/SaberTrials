"""Stage team appearance against the installed Saber Trials engine and modules."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist/team-appearance-01'
RECEIPT = OUT / 'source-receipt.json'
FRONTEND = ROOT / 'dist/tffa-assists-01'
ENGINE = ROOT / 'dist/saber-inspect-01'
GAME = FRONTEND
SOURCE = ROOT / 'development-source/client-game/codemp/cgame'
spec = spec_from_file_location('build_tools', ENGINE / 'candidate.py')
build_tools = module_from_spec(spec)
spec.loader.exec_module(build_tools)
build_tools.OUT, build_tools.RECEIPT = OUT, RECEIPT
build_tools.ROLES['game'] = ('game', 'BuildMPGame', 'jampgamex86_64.dll', 'jampgamex86_64.dll')
build_tools.ROLES['qa-cgame'] = build_tools.ROLES['cgame']
sha, read, write, tree, insert = (build_tools.sha, build_tools.read, build_tools.write,
                                  build_tools.tree, build_tools.insert)


def prepare():
    prior = read(ROOT / 'dist/tffa-assists-install.json')
    installed = {**prior['protected'], **prior['after']}
    assert all(sha(ROOT / name) == digest for name, digest in installed.items())
    assert sha(GAME/'build-game/Release/jampgamex86_64.dll') == installed['jampgamex86_64.dll']
    assert sha(ENGINE/'build-engine/Release/openjk.x86_64.exe') == installed[build_tools.EXE]
    assert sha(FRONTEND/'build-frontend/Release/cgamex86_64.dll') == installed['cgamex86_64.dll']
    paths = {'frontend': FRONTEND/'frontend', 'engine': ENGINE/'engine', 'game': GAME/'game'}
    baseline = {role: tree(path) for role, path in paths.items()}
    assert baseline['engine'] == read(ENGINE/'source-receipt.json')['sources']['engine']

    def copy_changed(source, destination):
        source, destination = Path(source), Path(destination)
        if not destination.is_file() or sha(source) != sha(destination):
            shutil.copyfile(source, destination)
        return str(destination)

    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = [pool.submit(shutil.copytree, path, OUT/role, dirs_exist_ok=True, copy_function=copy_changed)
                for role, path in paths.items()]
        for job in jobs:
            job.result()
    for role in ('frontend', 'engine'):
        shutil.copyfile(ROOT/'development-source/setup/st_setup_catalog.h', OUT/role/'codemp/ui/st_setup_catalog.h')
    import_module('team_appearance_overlay').wire(OUT/'frontend', OUT/'game', SOURCE, insert)
    sources = {role: tree(OUT/role) for role in paths}
    changed = {role: sorted(name for name, digest in sources[role].items() if baseline[role].get(name) != digest)
               for role in paths}
    write(RECEIPT, dict(installed=installed, sources=sources, changed=changed))
    print(changed, flush=True)


def install(tags):
    helper = import_module('Install-Profile-Browser')
    helper.stopped()
    home, settings = helper.settings()
    receipt = read(RECEIPT)
    installed = receipt['installed']
    sources = {build_tools.ROLES[role][3]: build_tools.binary(role) for role in ('engine', 'ui', 'cgame', 'game')}
    assert not any((home/name).exists() for name in sources if name.endswith('.dll'))
    assert all(sha(ROOT/name) == digest for name, digest in installed.items())
    before = {name: installed[name] for name in sources}
    after = {name: sha(path) for name, path in sources.items()}
    evidence = {}
    for tag in tags:
        path = OUT / tag / 'result.json'
        result = read(path)
        assert result['source'] == sha(RECEIPT)
        expected = dict(after)
        if result['mode'] == 'settings':
            expected['uix86_64.dll'] = sha(build_tools.binary('qa'))
            expected['cgamex86_64.dll'] = sha(build_tools.binary('qa-cgame'))
        assert result['binaries'] == expected
        evidence[result['mode']] = sha(path)
    assert set(evidence) == {'settings', 'production'}
    protected = {name: digest for name, digest in installed.items() if name not in sources}
    backup = ROOT/'dist/backups'/f'team-appearance-{datetime.now():%Y%m%d-%H%M%S}'
    state = ROOT/'dist/team-appearance-install.json'
    payload = dict(before=before, after=after, protected=protected, backup=str(backup),
                   evidence=evidence, preserved_settings=settings, source_sha256=sha(RECEIPT))
    import_module('Install-Handedness').install_transaction(ROOT, sources, before, after,
                                                            protected, backup, state, payload)
    assert all(sha(Path(name)) == digest for name, digest in settings.items())
    print('Installed team appearance settings.')


if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        prepare()
    elif sys.argv[1] == 'install':
        install(sys.argv[2:])
    else:
        build_tools.build(sys.argv[1])
