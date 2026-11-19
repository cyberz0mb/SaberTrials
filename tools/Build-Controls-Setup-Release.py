"""Rebase the accepted menus on the installed gameplay, without installing."""
from pathlib import Path
import argparse, importlib.util, json, re, sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist/controls-setup-release-01'
BASE = ROOT / 'dist/hybrid-candidate-03'


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def modules():
    controls = load('release_controls', 'Build-Controls.py')
    controls.BASE = BASE
    controls.OUT = OUT / 'controls'
    original_patch = controls.patch

    def patch(path, old, new):
        if old == '#define UI_API_VERSION 283':
            old = '#define UI_API_VERSION 220'
        original_patch(path, old, new)

    controls.patch = patch
    setup = load('release_setup', 'Build-Setup.py')
    setup.BASE = controls.OUT
    setup.OUT = OUT / 'setup'
    return controls, setup


def verify(setup):
    receipt = json.loads((setup.OUT / 'source-receipt.json').read_text())
    baseline = json.loads((BASE / 'manifest.json').read_text())
    changes = {}
    allowed = {
        'engine': {'codemp/ui/ui_public.h', 'codemp/client/cl_uiapi.cpp',
                   'codemp/client/cl_main.cpp', 'codemp/client/cl_input.cpp',
                   'codemp/client/cl_keys.cpp', 'shared/sdl/sdl_input.cpp'},
        'frontend': {'codemp/ui/ui_public.h', 'codemp/ui/CMakeLists.txt',
                     'codemp/ui/ui_main.c', 'codemp/ui/ui_atoms.c',
                     'codemp/ui/ui_syscalls.c', 'shared/qcommon/q_platform.h',
                     'codemp/cgame/cg_draw.c'},
    }
    for kind in ('engine', 'frontend'):
        current = setup.tree(setup.OUT / kind)
        assert current == receipt['sources'][kind], 'Release source drift: ' + kind
        assert setup.tree(BASE / kind) == baseline['sources'][kind]
        changed = {p for p, h in baseline['sources'][kind].items() if current.get(p) != h}
        assert changed == allowed[kind], (kind, changed ^ allowed[kind])
        added = set(current) - set(baseline['sources'][kind])
        assert all(Path(p).name.startswith(('st_', 'cl_st_', 'ui_st_')) for p in added)
        changes[kind] = {'modified': sorted(changed), 'added': sorted(added)}
        for header, version in [('cgame/cg_public.h', 219), ('game/g_public.h', 218), ('ui/ui_public.h', 285)]:
            token = {'cgame': 'CGAME', 'game': 'GAME', 'ui': 'UI'}[header.split('/')[0]]
            assert re.search(r'#define\s+' + token + r'_API_VERSION\s+' + str(version) + r'\b',
                             (setup.OUT / kind / 'codemp' / header).read_text())
    before = (BASE / 'frontend/codemp/cgame/cg_draw.c').read_text()
    after = (setup.OUT / 'frontend/codemp/cgame/cg_draw.c').read_text()
    assert after == before.replace('static void ST_DrawStreamerPresentation( void ) {',
                                  'static void ST_DrawStreamerPresentation( void ) {\n if(!cg_draw2D.integer)return;')
    (OUT / 'gameplay-preservation.json').write_text(json.dumps({
        'baseline_manifest_sha256': setup.sha(BASE / 'manifest.json'),
        'release_source_sha256': setup.sha(setup.OUT / 'source-receipt.json'),
        'game_api': 218, 'cgame_api': 219, 'ui_api': 285, 'changes': changes,
        'gameplay_sources_unchanged': True,
        'cgame_only_change': 'Honor Clean Capture for streamer overlays',
    }, indent=2))
    print('Release sources verified against installed gameplay; API 218/219/285.')


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--build-only-internal':
        assert sys.argv[2] in ('engine', 'frontend') and sys.argv[3] in ('0', '1')
        modules()[1].build(sys.argv[2], bool(int(sys.argv[3])))
        sys.exit(0)
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--build', choices=['engine', 'frontend'])
    parser.add_argument('--qa', action='store_true')
    parser.add_argument('--all', action='store_true')
    args = parser.parse_args()
    controls, setup = modules()
    if args.prepare:
        controls.OUT.mkdir(parents=True, exist_ok=True)
        controls.prepare()
        setup.prepare()
    verify(setup)
    if args.build:
        setup.build(args.build, args.qa)
    if args.all:
        import subprocess
        for qa in (False, True):
            for kind in ('engine', 'frontend'):
                log = OUT / ('build-' + kind + ('-qa' if qa else '') + '.log')
                print('Building', kind, 'QA' if qa else 'production', flush=True)
                # Keep full compiler output as a reviewable artifact.
                with log.open('w') as output:
                    result = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                                             '--build-only-internal', kind, str(int(qa))],
                                            stdout=output, stderr=subprocess.STDOUT)
                if result.returncode:
                    print(log.read_text(errors='replace')[-6000:])
                    raise RuntimeError('Build failed: ' + str(log))
                print('Built', kind, 'QA' if qa else 'production', flush=True)
