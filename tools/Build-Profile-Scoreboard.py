"""Stage the Profile and scoreboard presentation on the installed client modules."""
import argparse
import datetime
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist/profile-scoreboard-01'
UI_BASE = ROOT / 'dist/menu-cleanup-03'
CG_BASE = ROOT / 'dist/mvp-cinematic-candidate-02'
STATE = ROOT / 'dist/profile-scoreboard-install.json'
rollout = import_module('Build-Menu-Rollout')
sha, tree, read = rollout.sha, rollout.tree, rollout.read
PACKAGE = rollout.PACKAGE
INPUTS = {
    'frontend': {
        'codemp/ui/ui_st_profile.inc': 'development-source/profile/ui_st_profile.inc',
        'codemp/ui/ui_st_profile_draw.inc': 'development-source/profile/ui_st_profile_draw.inc',
    },
    'cgame-source': {
        'codemp/ui/st_presentation_draw.inc': 'development-source/bot-roles/codemp/ui/st_presentation_draw.inc',
        'codemp/cgame/cg_sabertrials_presentation.inc':
            'development-source/client-game/codemp/cgame/cg_sabertrials_presentation.inc',
    },
}


def hashes():
    return {path: sha(ROOT / path) for files in INPUTS.values() for path in files.values()}


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def prepare():
    ui = read(UI_BASE / 'source-receipt.json')
    cg = read(CG_BASE / 'manifest.json')
    base = {
        'frontend': (UI_BASE / 'frontend', ui['sources']),
        'cgame-source': (CG_BASE / 'frontend', cg['sources']['frontend']),
    }
    installed = {
        'uix86_64.dll': read(UI_BASE / 'build-record.json')['ui_sha256'],
        'cgamex86_64.dll': cg['builds']['frontend']['cgamex86_64.dll'],
        PACKAGE: ui['package_sha256'],
    }
    assert all(sha(ROOT / name) == digest for name, digest in installed.items()), 'Installed client baseline changed'
    OUT.mkdir(exist_ok=True)
    for key, (source, baseline) in base.items():
        assert tree(source) == baseline, 'Source baseline changed: ' + key
        destination = OUT / key
        shutil.copytree(source, destination, dirs_exist_ok=True)
        for target, authored in INPUTS[key].items():
            shutil.copyfile(ROOT / authored, destination / target)
        current = tree(destination)
        assert current.keys() == baseline.keys()
        assert all(current[name] == digest for name, digest in baseline.items() if name not in INPUTS[key])
    shutil.copy2(ROOT / PACKAGE, OUT / PACKAGE)
    write(OUT / 'source-receipt.json', dict(inputs=hashes(), installed=installed,
          sources={key: tree(OUT / key) for key in base}))


def build(role):
    ui = role != 'cgame'
    source = 'frontend' if ui else 'cgame-source'
    receipt = OUT / 'source-receipt.json'
    state = read(receipt)
    assert hashes() == state['inputs'] and tree(OUT / source) == state['sources'][source]
    folder = OUT / ('build-' + role)
    flags = ('BuildMPEngine','BuildMPDed','BuildMPGame','BuildMPCGame','BuildMPUI',
             'BuildMPRdVanilla','BuildMPRend2','BuildSPEngine','BuildSPGame','BuildSPRdVanilla')
    target = 'BuildMPUI' if ui else 'BuildMPCGame'
    args = ['cmake', '-S', str(OUT / source), '-B', str(folder), '-G', 'Visual Studio 18 2026', '-A', 'x64',
            '-DST_DEPS=' + str(ROOT / 'dist/handedness-baseline-06/deps'), '-DST_STAFF_QA=OFF']
    args.extend(f'-D{flag}={"ON" if flag == target else "OFF"}' for flag in flags)
    args.append('-DCMAKE_CXX_FLAGS=' + ('/DST_CONTROLS_QA' if role == 'qa' else ''))
    with (OUT / f'build-{role}.log').open('w') as log:
        subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['cmake', '--build', str(folder), '--config', 'Release', '--parallel', '4'],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    module = 'uix86_64.dll' if ui else 'cgamex86_64.dll'
    write(OUT / f'build-{role}.json', dict(source_sha256=sha(receipt), module=module,
          sha256=sha(folder / 'Release' / module)))
    print('Built ' + role, flush=True)


def install():
    helper = import_module('Install-Profile-Browser')
    helper.stopped()
    home, settings = helper.settings()
    assert not any((home / name).exists() for name in ('uix86_64.dll', 'cgamex86_64.dll'))
    receipt = OUT / 'source-receipt.json'
    state = read(receipt)
    assert hashes() == state['inputs']
    assert all(sha(ROOT / name) == digest for name, digest in state['installed'].items())
    proofs = {}
    for tag, ui_role in (('wide', 'qa'), ('tall', 'qa'), ('production', 'ui')):
        path = OUT / 'verification' / ('checked-' + tag) / 'result.json'
        result = read(path)
        assert result['source_sha256'] == sha(receipt)
        assert result['ui_sha256'] == read(OUT / f'build-{ui_role}.json')['sha256']
        assert result['cgame_sha256'] == read(OUT / 'build-cgame.json')['sha256']
        assert result['log_sha256'] == sha(path.parent / 'home/SaberTrials/qconsole.log')
        proofs[tag] = sha(path)
    sources = {}
    for role in ('ui', 'cgame'):
        record = read(OUT / f'build-{role}.json')
        path = OUT / ('build-' + role) / 'Release' / record['module']
        assert record['source_sha256'] == sha(receipt) and sha(path) == record['sha256']
        sources[record['module']] = path
    before = {name: state['installed'][name] for name in sources}
    after = {name: sha(path) for name, path in sources.items()}
    protected = {p.relative_to(ROOT).as_posix(): sha(p) for p in (
        ROOT / PACKAGE, ROOT / 'jampgamex86_64.dll', ROOT / 'client/SaberTrials.x86_64.exe',
        ROOT / 'client/rd-vanilla_x86_64.dll', ROOT / 'client/rd-rend2_x86_64.dll')}
    backup = ROOT / 'dist/backups' / ('profile-scoreboard-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    payload = dict(before=before, after=after, protected=protected, preserved_settings=settings,
                   backup=str(backup), evidence=proofs, source_sha256=sha(receipt))
    import_module('Install-Handedness').install_transaction(ROOT, sources, before, after, protected, backup, STATE, payload)
    assert all(helper.sha(Path(path)) == digest for path, digest in settings.items())
    print('Installed Profile and scoreboard presentation.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'ui', 'qa', 'cgame', 'install'))
    action = parser.parse_args().action
    if action == 'prepare':
        prepare()
    elif action == 'install':
        install()
    else:
        build(action)
