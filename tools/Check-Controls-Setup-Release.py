"""Run existing native regressions on the installed-game release baseline."""
from pathlib import Path
import argparse, importlib.util, sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tool', choices=['Setup', 'Controls'], required=True)
    args, rest = parser.parse_known_args()
    path = ROOT / 'tools' / ('Check-' + args.tool + '.py')
    spec = importlib.util.spec_from_file_location('release_check', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT = ROOT / 'dist/controls-setup-release-01/setup'
    module.MOD = 'SaberTrials'
    sys.argv = [str(path)] + rest
    module.main()
