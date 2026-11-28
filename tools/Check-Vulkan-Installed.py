"""Exercise the installed executable and DLLs using a disposable, copied profile."""
from datetime import datetime
from importlib import import_module
import os
import re
import shutil
import subprocess

i = import_module('Install-Vulkan')
b = i.b
m = import_module('Check-Vulkan-Materials')


def launch(run, lines, renderer=None):
    mod = run / 'home/SaberTrials'
    (mod / 'installed-check.cfg').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    cvars = dict(fs_basepath=b.ROOT.parent, fs_homepath=run / 'home', fs_game='SaberTrials',
        com_unpackLibraries=0, logfile=2, net_ip='127.0.0.1', net_port=29731, sv_pure=0,
        s_initsound=0, com_introplayed=1, developer=1, r_fullscreen=0, r_mode=-1,
        r_customwidth=1280, r_customheight=720, com_maxfps=125, con_notifytime=0,
        st_translate=0, r_renderScale=0, r_ext_supersample=0)
    if renderer is not None:
        cvars['cl_renderer'] = renderer
    # Normal startup must read the copied profile; +safe skips openjk.cfg entirely.
    command = [str(b.ROOT / 'client/SaberTrials.x86_64.exe')]
    for name, value in cvars.items():
        command += ['+set', name, str(value)]
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    process = subprocess.Popen(command + ['+exec', 'installed-check.cfg'], cwd=b.ROOT.parent,
        startupinfo=startup, env={**os.environ, 'LOCALAPPDATA': str(run / 'local-app-data')},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        code = process.wait(timeout=150)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    log = (mod / 'qconsole.log').read_text(errors='replace')
    clean = re.sub(r'\^[0-9]', '', log)
    assert code == 0 and 'ST_INSTALLED_DONE' in clean, 'Installed run failed: ' + str(run)
    assert 'Saved graphics settings retained.' not in log, 'Unexpected fallback: ' + str(run)
    assert 'ERROR:' not in log, 'Runtime error: ' + str(run)
    loads = re.findall(r'Trying to load "(rd-[^"]+)" from "([^"]+)"', log)
    assert loads and all(os.path.normcase(p) == os.path.normcase(str(b.ROOT / 'client')) for _, p in loads)
    assert 'VM_Create: uix86_64.dll succeeded' in log, 'Installed UI did not load'
    return clean


def check():
    i.h.stopped()
    state = i.verify()
    home, settings = i.h.settings()
    root = b.OUT / 'checks' / ('installed-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    original_cfg = (home / 'openjk.cfg').read_text(errors='replace')
    default = re.search(r'seta? cl_renderer "([^"]+)"', original_cfg)
    default = default[1] if default else 'rd-vanilla'
    results = {}
    models = ['ichigo_hollow/default', 'denji/default', 'leia/default']
    expected, packages = {}, {}
    for model in models:
        names, package = m.expected_materials(model)
        expected[model] = sorted(names)
        packages[str(package)] = b.sha(package)
        addon = package.with_name(package.stem + '_rend2.pk3')
        if addon.exists():
            packages[str(addon)] = b.sha(addon)
    for scenario in ('saved-default', 'vulkan-materials-switching'):
        run = root / scenario
        mod = run / 'home/SaberTrials'
        mod.mkdir(parents=True)
        for path in home.glob('*.cfg'):
            shutil.copyfile(path, mod / path.name)
        lines = ['wait 100', 'st_activeRenderer', 'st_rendererError', 'screenshot_png installed-menu']
        if scenario == 'vulkan-materials-switching':
            lines += ['set g_gametype 0', 'set g_warmup 0', 'set cg_forceModel 0',
                'set model ' + models[0], 'devmap mp/ffa3', 'wait 450', 'team free', 'wait 140',
                'st_emoteuiqa resume', 'set cg_thirdPerson 1', 'set cg_thirdPersonAngle 180',
                'set cg_thirdPersonRange 100', 'wait 30']
            for model in models:
                lines += ['set model ' + model, 'wait 160',
                    'screenshot_png ' + model.replace('/', '-'), 'wait 30']
            lines += ['shaderlist', 'imagelist', 'st_activeRenderer', 'disconnect', 'wait 80']
            for renderer in ('rd-rend2', 'rd-vulkan', 'rd-vanilla', 'rd-vulkan'):
                lines += ['set cl_renderer ' + renderer, 'vid_restart', 'wait 120',
                    'st_activeRenderer', 'screenshot_png switch-' + renderer, 'wait 20']
        lines += ['st_activeRenderer', 'st_rendererError', 'echo ST_INSTALLED_DONE', 'quit']
        log = launch(run, lines, None if scenario == 'saved-default' else 'rd-vulkan')
        active = re.findall(r'Cvar st_activeRenderer = "([^"]*)"', log)
        assert active and active[-1] == (default if scenario == 'saved-default' else 'rd-vulkan')
        failures = []
        if scenario == 'vulkan-materials-switching':
            assert all(r in active for r in ('rd-rend2', 'rd-vanilla', 'rd-vulkan'))
            for names in expected.values():
                for material in names:
                    rows = [line for line in log.splitlines() if re.search(
                        r'(?<![\w/])' + re.escape(material) + r'\s*(?:\(DEFAULTED\))?\s*$', line, re.I)]
                    if not rows or any('(DEFAULTED)' in row for row in rows):
                        failures.append(material)
            assert not failures, 'Defaulted/missing installed character materials: ' + ', '.join(failures)
        results[scenario] = dict(passed=True, active_renderers=active, failed_materials=failures,
            log=b.sha(mod / 'qconsole.log'),
            screenshots={p.name: b.sha(p) for p in (mod / 'screenshots').glob('*.png')})
        print('Passed installed ' + scenario + '.', flush=True)
    assert i.h.settings()[1] == settings == state['preserved_settings'], 'Original profile changed'
    for path, digest in packages.items():
        assert b.sha(path) == digest, 'Model package changed: ' + path
    i.verify(check_settings=True)
    result = dict(passed=True, installed=True, source=state['source'], inputs=state['after'],
        checker=b.sha(__file__), scenarios=results, expected_materials=expected,
        packages=packages, saved_default=default, settings_preserved=True)
    b.write(root / 'result.json', result)
    state['post_install_validation'] = dict(path=str(root / 'result.json'), sha256=b.sha(root / 'result.json'))
    i.t.atomic_record(i.STATE, state)
    print(root, flush=True)


if __name__ == '__main__':
    check()
