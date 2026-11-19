"""Build an isolated matching hybrid-style candidate. Never install or launch it."""
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
OUT = ROOT/'dist/hybrid-candidate-02'
BASE = ROOT/'dist/feint-candidate-01'
MENU_BASE = ROOT/'dist/stance-candidate-02/menus'
ASSET_BASE = ROOT/'dist/stance-candidate-02/assets/zz_sabertrials_stances_v1.pk3'
KINDS = ('engine', 'game', 'frontend')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree(path):
    path = Path(path)
    return {p.relative_to(path).as_posix():sha(p) for p in sorted(path.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    Path(path).write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8', newline='\n')


def inputs():
    files = [Path(__file__)] + list((ROOT/'development-source/hybrid-styles').rglob('*'))
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files)
            if p.is_file() and '__pycache__' not in p.parts}


def baseline():
    # The accepted first hybrid is now installed. Its immutable source receipt
    # pins the inputs without treating that authorized install as source drift.
    # Installation integrity is checked separately by the transactional updater.
    accepted = read(ROOT/'dist/hybrid-candidate-01/manifest.json')['baseline']
    old = read(BASE/'manifest.json')
    for kind in KINDS:
        if tree(BASE/kind) != accepted['sources'][kind] or old['sources'][kind] != accepted['sources'][kind]:
            raise ValueError('Accepted feint source drift: '+kind)
    stance = read(ROOT/'dist/stance-candidate-02/sources.json')
    if tree(MENU_BASE) != stance['menus'] or stance['menus'] != accepted['menus']:
        raise ValueError('Accepted stance menu sources changed')
    if sha(ASSET_BASE) != stance['library_sha256'] or sha(ASSET_BASE) != accepted['assets']:
        raise ValueError('Accepted stance assets changed')
    return dict(sources=old['sources'], menus=tree(MENU_BASE), assets=sha(ASSET_BASE))


def assets():
    animation = module('hybrid_animation', ROOT/'development-source/hybrid-styles/animation.py')
    m = animation.generate(ASSET_BASE, BASE/'game/codemp/game/anims.h', OUT/'assets')
    shutil.copy2(ASSET_BASE, OUT/'assets'/ASSET_BASE.name)
    return animation, m


def overlays():
    return [module('hybrid_'+name, ROOT/'development-source/hybrid-styles'/f'{name}_overlay.py')
            for name in ('combat','ui')]


def prepare(recover=False):
    b = baseline()
    if (OUT/'manifest.json').exists() or (not recover and any((OUT/k).exists() for k in KINDS)):
        raise ValueError('Candidate source already exists; use --sync, never overwrite it')
    if recover:
        # Preserve a forensic inventory of a failed generated attempt. Restoring
        # baseline files is confined to this unmanifested candidate; no deletion.
        if OUT.resolve().parent != (ROOT/'dist').resolve() or OUT.name != 'hybrid-candidate-02':
            raise ValueError('Unexpected recovery target')
        report = OUT/'failed-preparation-sources.json'
        if report.exists():
            report = OUT/('failed-preparation-sources-'+str(len(list(OUT.glob('failed-preparation-sources*.json'))))+'.json')
        write(report, {k:tree(OUT/k) for k in KINDS if (OUT/k).exists()})
    before = inputs()
    animation, am = assets()
    combat, ui = overlays()
    m = dict(installed=False, baseline=b, inputs=before, sources={}, changes={}, builds={})
    for kind in KINDS:
        shutil.copytree(BASE/kind, OUT/kind, dirs_exist_ok=recover)
        animation.apply(OUT/kind, OUT/'assets', am)
        combat.apply(OUT/kind, kind)
        ui.apply(OUT/kind, kind)
        m['sources'][kind] = tree(OUT/kind)
        m['changes'][kind] = [n for n,h in m['sources'][kind].items() if b['sources'][kind].get(n)!=h]
    shutil.copytree(MENU_BASE, OUT/'menus', dirs_exist_ok=recover)
    ui.apply_menus(OUT/'menus')
    m.update(menus=tree(OUT/'menus'), assets=tree(OUT/'assets'))
    if before != inputs():
        raise ValueError('Overlay changed during preparation; inspect before recovery')
    write(OUT/'manifest.json', m)
    verify()
    print('Hybrid candidate prepared. Original installation unchanged; no process launched.')


def verify(require_inputs=True):
    b = baseline()
    m = read(OUT/'manifest.json')
    if b != m['baseline']:
        raise ValueError('Baseline provenance drift')
    if require_inputs and inputs() != m['inputs']:
        raise ValueError('Overlay changed; use explicit --sync before rebuilding')
    for kind in KINDS:
        if tree(OUT/kind) != m['sources'][kind]:
            raise ValueError('Candidate source drift: '+kind)
    for folder in ('menus','assets'):
        if tree(OUT/folder) != m[folder]:
            raise ValueError('Candidate content drift: '+folder)
    for kind, files in m['builds'].items():
        for name, h in files.items():
            if sha(OUT/('build-'+kind)/'Release'/name) != h:
                raise ValueError('Candidate binary drift: '+name)
    return m


def sync():
    m = verify(False)
    previous_sources = dict(m['sources'])
    previous_builds = dict(m['builds'])
    before = inputs()
    animation, am = assets()
    combat, ui = overlays()
    for kind in KINDS:
        for name in m['changes'][kind]:
            if name in m['baseline']['sources'][kind]:
                shutil.copy2(BASE/kind/name, OUT/kind/name)
        animation.apply(OUT/kind, OUT/'assets', am)
        combat.apply(OUT/kind, kind)
        ui.apply(OUT/kind, kind)
        m['sources'][kind] = tree(OUT/kind)
        m['changes'][kind] = [n for n,h in m['sources'][kind].items()
                              if m['baseline']['sources'][kind].get(n)!=h]
    for name in m['baseline']['menus']:
        shutil.copy2(MENU_BASE/name, OUT/'menus'/name)
    ui.apply_menus(OUT/'menus')
    m.update(inputs=before, menus=tree(OUT/'menus'), assets=tree(OUT/'assets'),
             builds={k:v for k,v in previous_builds.items() if previous_sources[k]==m['sources'][k]})
    if before != inputs():
        raise ValueError('Overlay changed during synchronization')
    write(OUT/'manifest.json', m)
    print('Candidate regenerated; changed components must be rebuilt. Unchanged builds retained by source hash.')


def build(kind):
    m = verify()
    if kind in m['builds']:
        print('Verified existing '+kind+' build matches its unchanged sources.')
        return
    helper = module('hand_build', ROOT/'tools/Prepare-Handedness-Baseline.py')
    folder = OUT/('build-'+kind)
    subprocess.run(['cmake', '-S', str(OUT/kind), '-B', str(folder), '-G',
                    'Visual Studio 18 2026', '-A', 'x64',
                    '-DST_DEPS='+str(ROOT/'dist/handedness-baseline-06/deps'),
                    '-DST_STAFF_QA=OFF', *['-D'+f+'='+('ON' if f in helper.TARGETS[kind] else 'OFF')
                                         for f in helper.FLAGS]], check=True)
    subprocess.run(['cmake','--build',str(folder),'--config','Release','--parallel','6'], check=True)
    m = verify()
    m['builds'][kind] = {n:sha(folder/'Release'/n) for n in helper.ARTIFACTS[kind]}
    write(OUT/'manifest.json', m)
    print('Built '+kind+'; not installed or launched.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare', action='store_true')
    group.add_argument('--recover-prepare', action='store_true', help='Restore a failed, unmanifested generated attempt only; no deletion')
    group.add_argument('--sync', action='store_true')
    group.add_argument('--verify', action='store_true')
    group.add_argument('--assets', action='store_true')
    group.add_argument('--build', choices=KINDS+('all',))
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.recover_prepare:
        prepare(recover=True)
    elif args.sync:
        sync()
    elif args.assets:
        if (OUT/'manifest.json').exists():
            raise ValueError('Existing candidate: use --sync to regenerate assets')
        baseline()
        assets()
        print('Append-only assets generated; no installation.')
    elif args.build:
        for k in KINDS if args.build=='all' else (args.build,):
            build(k)
    else:
        verify()
        print('Candidate sources/assets/binaries and accepted source baseline verified.')
