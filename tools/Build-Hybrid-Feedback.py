"""Build the isolated player-feedback revision; preserve all accepted candidates."""
from pathlib import Path
import argparse
import importlib.util
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

BASE = load('feedback_base_builder', ROOT/'tools/Build-Hybrid-Styles.py')
OUT = ROOT/'dist/hybrid-candidate-03'
BASE.OUT = OUT
original_inputs, original_overlays = BASE.inputs, BASE.overlays

def inputs():
    return {**original_inputs(), Path(__file__).relative_to(ROOT).as_posix(): BASE.sha(__file__)}

def overlays():
    combat, ui = original_overlays()
    compatibility = load('feedback_model_compat', ROOT/'development-source/hybrid-styles/model_compat.py')
    original_apply = combat.apply
    def apply(root, kind):
        original_apply(root, kind)
        compatibility.apply(root, kind)
    combat.apply = apply
    return combat, ui

BASE.inputs, BASE.overlays = inputs, overlays

def require_uninstalled():
    receipt = ROOT/'dist/hybrid-feedback-install.json'
    if receipt.exists():
        raise ValueError('This candidate has an installation receipt. Preserve it and create a new revision.')

def verify(require_inputs=True):
    return BASE.verify(require_inputs)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare', action='store_true')
    group.add_argument('--sync', action='store_true')
    group.add_argument('--verify', action='store_true')
    group.add_argument('--build', choices=BASE.KINDS+('all',))
    args = parser.parse_args()
    if args.verify:
        verify(); print('Feedback candidate sources, assets and binaries verified.')
    else:
        require_uninstalled()
        if args.prepare: BASE.prepare()
        elif args.sync: BASE.sync()
        elif args.build:
            for kind in BASE.KINDS if args.build=='all' else (args.build,): BASE.build(kind)
