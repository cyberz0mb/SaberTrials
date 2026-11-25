"""Rebuild only the SDL input client on the installed Vulkan-capable engine."""
from datetime import datetime
from importlib import import_module
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
builder = import_module('Build-Vulkan')
root = builder.ROOT
base = builder.OUT
out = root / 'dist/controller-response-01'
builder.OUT = out
target = 'client/SaberTrials.x86_64.exe'
controls = root / 'development-source/controls'
binary = out / 'build-engine/Release/openjk.x86_64.exe'


def prepare():
    checkpoint = builder.read(base / 'source-receipt.json')['sources']['engine']
    installed = builder.sha(root / target)
    assert builder.read(base / 'build-engine.json') == dict(
        source=builder.sha(base / 'source-receipt.json'), sha256=installed)
    assert builder.tree(base / 'engine') == checkpoint, 'Combined engine source has changed'
    engine = out / 'engine'
    shutil.copytree(base / 'engine', engine, dirs_exist_ok=True)
    sdl = engine / 'shared/sdl'
    for name in ('st_controller.inc', 'st_pad_devices.inc'):
        shutil.copyfile(controls / name, sdl / name)
    shutil.copyfile(controls / 'cl_st_pad_menu.inc', engine / 'codemp/client/cl_st_pad_menu.inc')
    wheel = builder.module('emote_overlay', root / 'development-source/emotes/overlay.py')
    wheel.wire_pad_wheel(sdl / 'st_controller.inc')
    overlay = builder.module('menu_overlay', controls / 'gamepad_menu_overlay.py')
    overlay.wire_pad_events(sdl / 'sdl_input.cpp')
    updated = builder.tree(engine)
    changes = {n for n in updated.keys() | checkpoint.keys() if updated.get(n) != checkpoint.get(n)}
    assert changes == {'shared/sdl/st_controller.inc', 'shared/sdl/st_pad_devices.inc',
                       'shared/sdl/sdl_input.cpp', 'codemp/client/cl_st_pad_menu.inc'}, changes
    builder.write(out / 'source-receipt.json', dict(before=installed, sources={'engine': updated}))
    print('Prepared controller input on the matching installed engine.', flush=True)


def install():
    helper = import_module('Install-Profile-Browser')
    helper.stopped()
    state = builder.read(out / 'source-receipt.json')
    assert builder.sha(root / target) == state['before']
    after = builder.sha(binary)
    assert builder.read(out / 'build-engine.json') == dict(source=builder.sha(out / 'source-receipt.json'), sha256=after)
    evidence = builder.read(out / 'verification.json')
    assert evidence['candidate'] == after and evidence['passed']
    _, settings = helper.settings()
    protected = {}
    for record in ('bot-navigation-install.json', 'menu-selection-install.json'):
        previous = builder.read(root / 'dist' / record)
        protected.update(previous['protected'])
        protected.update(previous['after'])
    assert protected.pop(target) == state['before']
    backup = root / 'dist/backups' / ('controller-response-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    payload = dict(before={target: state['before']}, after={target: after}, protected=protected,
                   backup=str(backup), preserved_settings=settings, evidence=builder.sha(out / 'verification.json'),
                   source_sha256=builder.sha(out / 'source-receipt.json'))
    import_module('Install-Handedness').install_transaction(root, {target: binary}, payload['before'],
        payload['after'], protected, backup, root / 'dist/controller-response-install.json', payload)
    assert helper.settings()[1] == settings
    print('Installed and verified the updated client.', flush=True)


if __name__ == '__main__':
    {'prepare': prepare, 'build': lambda: builder.build('engine'), 'install': install}[sys.argv[1]]()
