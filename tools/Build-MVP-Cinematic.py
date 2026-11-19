"""Build the isolated MVP montage candidate from verified installed baselines."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist/mvp-cinematic-candidate-03'
SRC = ROOT / 'development-source/mvp-cinematic'
ART_GENERATOR = ROOT / 'tools/Generate-MVP-Art.ps1'
PROFILE_RECEIPT = ROOT / 'dist/profile-scoreboard-01/source-receipt.json'
PROFILE_OVERLAYS = {
    'codemp/ui/ui_st_profile.inc':'development-source/profile/ui_st_profile.inc',
    'codemp/ui/ui_st_profile_draw.inc':'development-source/profile/ui_st_profile_draw.inc',
    'codemp/ui/st_presentation_draw.inc':'development-source/bot-roles/codemp/ui/st_presentation_draw.inc',
    'codemp/cgame/cg_sabertrials_presentation.inc':'development-source/client-game/codemp/cgame/cg_sabertrials_presentation.inc',
}
BASES = {
    'engine': ROOT / 'dist/controls-setup-release-01/setup/engine',
    'game': ROOT / 'dist/hybrid-candidate-03/game',
    'frontend': ROOT / 'dist/menu-cleanup-03/frontend',
}
ARTIFACTS = {'engine': ('openjk.x86_64.exe', 'rd-vanilla_x86_64.dll', 'rd-rend2_x86_64.dll'),
             'game': ('jampgamex86_64.dll',), 'frontend': ('cgamex86_64.dll','uix86_64.dll')}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def tree(path):
    return {p.relative_to(path).as_posix(): sha(p) for p in sorted(path.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def installed():
    files = list(ROOT.glob('*.dll')) + list(ROOT.glob('*.pk3')) + list(ROOT.glob('*.cfg'))
    files += [ROOT / 'client' / name for name in ('SaberTrials.x86_64.exe', 'rd-vanilla_x86_64.dll', 'rd-rend2_x86_64.dll')]
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in files}


def profile_inputs():
    receipt=read(PROFILE_RECEIPT)
    assert sha(PROFILE_RECEIPT)=='c83f3a3389f129098c782b8b02840ff38946ee1c9b245720f34c9755c5a1eee7'
    expected=receipt['inputs']
    assert {name:sha(ROOT/name) for name in PROFILE_OVERLAYS.values()}==expected
    return dict(receipt_sha256=sha(PROFILE_RECEIPT),inputs=expected)


def apply_profile(dest):
    profile_inputs()
    for target,source in PROFILE_OVERLAYS.items():
        shutil.copy2(ROOT/source,dest/target)
        (dest/target).touch()


def accepted_installation(expected):
    """Accept only the recorded promotion of this candidate over its baseline."""
    receipt = ROOT / 'dist/mvp-cinematic-install.json'
    result = dict(expected)
    if receipt.exists():
        state = read(receipt)
        if state.get('installed') and not state.get('restored'):
            for name, digest in state['after'].items():
                if name in result and result[name] in (state['before'].get(name),state.get('original_before',{}).get(name)):
                    result[name] = digest
    return result


def verify_baseline():
    controls = read(ROOT / 'dist/controls-setup-release-01/setup/source-receipt.json')
    hybrid = read(ROOT / 'dist/hybrid-candidate-03/manifest.json')
    menu = read(ROOT / 'dist/menu-cleanup-03/source-receipt.json')
    for kind, path in BASES.items():
        expected = menu['sources'] if kind=='frontend' else (hybrid if kind == 'game' else controls)['sources'][kind]
        if tree(path) != expected:
            raise ValueError('Baseline source drift: ' + kind)
    for receipt, names in (
        ('controls-setup-install.json', ('client/SaberTrials.x86_64.exe', 'cgamex86_64.dll')),
        ('hybrid-feedback-install.json', ('jampgamex86_64.dll',)),
        ('menu-cleanup-03-install.json', ('uix86_64.dll',)),
    ):
        state = read(ROOT / 'dist' / receipt)
        expected = accepted_installation(state['after'])
        for name in names:
            if sha(ROOT / name) != expected[name]:
                raise ValueError('Installed baseline drift: ' + name)


def prepare():
    verify_baseline()
    OUT.mkdir(parents=True, exist_ok=True)
    receipt_path = OUT / 'manifest.json'
    if receipt_path.exists():
        old = read(receipt_path)
        current = installed()
        if any(current.get(name) != digest for name, digest in accepted_installation(old['installed']).items()):
            raise ValueError('Installed files changed during candidate work')
    overlay = load('mvp_overlay', SRC / 'overlay.py')
    styles = load('style_playability', SRC / 'style_overlay.py')
    subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                    str(ART_GENERATOR), '-Output', str(OUT / 'assets/ui/assets/sabertrials/mvp'),
                    '-Metrics', str(OUT / 'st_mvp_hud_type.h')], check=True)
    menu_path=OUT/'assets/ui/jamp/rules_moves.menu'
    menu_path.parent.mkdir(parents=True,exist_ok=True)
    menu_text=(ROOT/'ui/jamp/rules_moves.menu').read_text()
    for old,new in (('FAST','Blue'),('MEDIUM','Yellow'),('STRONG','Red')):
        assert menu_text.count('"@MENUS_SINGLE_'+old+'"')+menu_text.count('"Single Saber, '+new+'"')==1
        menu_text=menu_text.replace('"@MENUS_SINGLE_'+old+'"','"Single Saber, '+new+'"')
    menu_path.write_text(menu_text,newline='\n')
    state = {'scope': 'Normal Orange availability, color names, quiet replay and final linger', 'installed': installed(),
             'profile':profile_inputs(),
             'inputs': tree(SRC), 'art_generator': sha(ART_GENERATOR),
             'assets': tree(OUT / 'assets'), 'sources': {}, 'builds': {}}
    for kind, base in BASES.items():
        dest = OUT / kind
        # Regenerate this feature-owned tree from the immutable verified baseline.
        def copy_changed(source, target):
            if not Path(target).exists() or sha(source) != sha(target):
                shutil.copy2(source, target)
                # Restoring an older baseline must invalidate an incremental
                # object too; copy2 alone preserves the old source timestamp.
                Path(target).touch()
            return target
        shutil.copytree(base, dest, dirs_exist_ok=True, copy_function=copy_changed)
        overlay.apply(dest, kind)
        styles.apply(dest, kind)
        if kind == 'frontend':
            styles.ui(dest)
            apply_profile(dest)
            shutil.copy2(OUT / 'st_mvp_hud_type.h', dest / 'codemp/cgame/st_mvp_hud_type.h')
        state['sources'][kind] = tree(dest)
    write(receipt_path, state)
    print('MVP sources prepared and baseline verified.', flush=True)


def verify():
    state = read(OUT / 'manifest.json')
    if 'profile' in state and state['profile']!=profile_inputs():
        raise ValueError('Verified Profile/scoreboard inputs changed')
    if tree(SRC) != state['inputs'] or installed() != accepted_installation(state['installed']):
        raise ValueError('MVP inputs or installed files changed')
    if sha(ART_GENERATOR) != state['art_generator'] or tree(OUT / 'assets') != state['assets']:
        raise ValueError('MVP presentation assets changed')
    for kind in BASES:
        if tree(OUT / kind) != state['sources'][kind]:
            raise ValueError('Candidate source drift: ' + kind)
    for kind, expected in state['builds'].items():
        for name, digest in expected.items():
            if sha(OUT / ('build-' + kind) / 'Release' / name) != digest:
                raise ValueError('Candidate binary drift: ' + kind + '/' + name)
    return state


def build(kind):
    state = verify()
    # A rebuild replaces this component's old binaries. Keep verification for
    # the other components, and leave this one unstageable if compilation fails.
    state['builds'].pop(kind, None)
    write(OUT / 'manifest.json', state)
    helper = load('mvp_build_flags', ROOT / 'tools/Prepare-Handedness-Baseline.py')
    target = {'engine': 'BuildMPEngine', 'game': 'BuildMPGame', 'frontend': 'BuildMPCGame'}[kind]
    targets = {target} | ({'BuildMPRdVanilla', 'BuildMPRend2'} if kind == 'engine' else set())
    if kind=='frontend': targets.add('BuildMPUI')
    folder = OUT / ('build-' + kind)
    log = OUT / ('build-' + kind + '.log')
    commands = [
        ['cmake', '-S', str(OUT / kind), '-B', str(folder), '-G', 'Visual Studio 18 2026', '-A', 'x64',
         '-DST_DEPS=' + str(ROOT / 'dist/handedness-baseline-06/deps'), '-DST_STAFF_QA=OFF'] +
        ['-D' + flag + '=' + ('ON' if flag in targets else 'OFF') for flag in helper.FLAGS],
        ['cmake', '--build', str(folder), '--config', 'Release', '--parallel', '6'],
    ]
    with log.open('w', encoding='utf-8') as output:
        for command in commands:
            result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT)
            if result.returncode:
                output.flush()
                print(log.read_text(encoding='utf-8', errors='replace')[-7000:])
                raise RuntimeError('Build failed: ' + str(log))
    state = verify()
    state['builds'][kind] = {name: sha(folder / 'Release' / name) for name in ARTIFACTS[kind]}
    write(OUT / 'manifest.json', state)
    print('Built MVP ' + kind, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--build', choices=tuple(BASES) + ('all',))
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if args.prepare:
        prepare()
    if args.build:
        for kind in BASES if args.build == 'all' else (args.build,):
            build(kind)
    if args.verify:
        verify()
        print('MVP source, binaries and installed-file preservation verified.')
