"""Check native intro playback, normal startup, skipping and menu handoff."""
import argparse
from datetime import datetime
from importlib import import_module
import os
import shutil
import subprocess
import time

b = import_module('Build-Studio-Intro')


def check(scenario, installed=False):
    renderer = scenario if scenario.startswith('rd-') else 'rd-rend2'
    folder = 'installed-' + scenario if installed else scenario
    root = b.OUT / 'checks' / folder
    run = root / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    mod = run / 'home/SaberTrials'
    mod.mkdir(parents=True)
    if not installed:
        shutil.copy2(b.OUT / b.PACKAGE, mod / b.PACKAGE)
    package = b.ROOT / b.PACKAGE if installed else mod / b.PACKAGE
    assert b.sha(package) == b.read(b.RECEIPT)['package_sha256']
    end = ['wait 30', 'screenshot_png studio-main-menu', 'wait 15', 'echo ST_STUDIO_INTRO_DONE', 'quit']
    (mod / 'studio-end.cfg').write_text('\n'.join(end) + '\n', encoding='ascii')
    cvars = dict(fs_basepath=b.ROOT.parent, fs_homepath=run / 'home', fs_game='SaberTrials',
                 com_unpackLibraries=0, logfile=2, com_bootlogo=1, developer=1,
                 r_fullscreen=0, r_mode=-1, r_customwidth=1280, r_customheight=720,
                 cl_renderer=renderer, com_maxfps=60, con_notifytime=0, st_translate=0,
                 s_initsound=1, r_renderScale=0, r_ext_supersample=0)
    command = [str(b.ROOT / 'client/SaberTrials.x86_64.exe')]
    for name, value in cvars.items():
        command += ['+set', name, str(value)]
    if scenario == 'startup':
        # Only +set startup arguments, just as in the regular game launcher.
        (mod / 'autoexec.cfg').write_text('set nextmap "exec studio-end.cfg"\n', encoding='ascii')
    else:
        lines = ['wait 65', 'set nextmap "exec studio-end.cfg"', 'cinematic openinglogos.roq']
        if scenario == 'skip':
            lines += ['wait 30', 'st_emoteinputqa SPACE 1', 'st_emoteinputqa SPACE 0']
        else:
            lines += ['wait 230', 'screenshot_png studio-intro', 'wait 5']
        (mod / 'studio-test.cfg').write_text('\n'.join(lines) + '\n', encoding='ascii')
        command += ['+exec', 'studio-test.cfg']
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    start = time.monotonic()
    proc = subprocess.Popen(command, cwd=b.ROOT.parent, startupinfo=startup,
                            env={**os.environ, 'LOCALAPPDATA': str(run / 'local-app-data')},
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        code = proc.wait(timeout=100)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    output = (mod / 'qconsole.log').read_text(errors='replace')
    assert code == 0 and 'ST_STUDIO_INTRO_DONE' in output, run
    assert 'trFMV::play(), playing openinglogos.roq' in output, 'Intro never started'
    assert output.count('trFMV::play(), playing openinglogos.roq') == 1, 'Intro repeated'
    assert 'finished cinematic' in output, 'Intro did not finish'
    assert output.index('finished cinematic') < output.index('ST_STUDIO_INTRO_DONE'), 'Client quit during playback'
    assert 'Failed to open "openinglogos.roq"' not in output
    assert 'invalid RoQ ID' not in output and 'ERROR:' not in output
    assert (mod / 'screenshots/studio-main-menu.png').is_file(), 'Menu screenshot never reached disk'
    if scenario not in ('startup', 'skip'):
        assert (mod / 'screenshots/studio-intro.png').is_file()
    assert 'Server Initialization' not in output
    report = dict(passed=True, installed=installed, scenario=scenario, renderer=renderer,
                  executable=b.sha(b.ROOT / 'client/SaberTrials.x86_64.exe'),
                  renderer_sha256=b.sha(b.ROOT / 'client' / (renderer + '_x86_64.dll')),
                  package=b.sha(package), log=b.sha(mod / 'qconsole.log'),
                  elapsed=round(time.monotonic() - start, 2),
                  screenshots={p.name: b.sha(p) for p in (mod / 'screenshots').glob('*.png')},
                  run=str(run))
    b.write(root / 'result.json', report)
    print('Passed ' + folder + '\n' + str(run), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scenario', choices=('rd-vanilla', 'rd-rend2', 'rd-vulkan', 'startup', 'skip'))
    parser.add_argument('--installed', action='store_true')
    args = parser.parse_args()
    check(args.scenario, args.installed)
