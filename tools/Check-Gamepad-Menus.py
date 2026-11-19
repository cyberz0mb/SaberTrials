"""Exercise gamepad menu dispatch in an isolated Windows client."""
from datetime import datetime
from importlib import import_module
import os
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
b = import_module('Build-Gamepad-Menus')


def run(installed=False, profile_keyboard=False):
    run = b.OUT/(('installed-' if installed else 'review-')+datetime.now().strftime('%H%M%S'))
    mod = run/'home/SaberTrials'
    screenshots = mod/'screenshots'
    screenshots.mkdir(parents=True)
    files = b.files(qa=not installed)
    if installed:
        files = {name:b.ROOT/name for name in files}
        receipt = 'name-keyboard-install.json' if profile_keyboard else 'gamepad-menus-install.json'
        assert {name:b.sha(path) for name,path in files.items()}==b.read(b.ROOT/'dist'/receipt)['after']
    else:
        client = run/'client'
        client.mkdir()
        for name in ('SDL2.dll','OpenAL32.dll','rd-vanilla_x86_64.dll','rd-rend2_x86_64.dll'):
            shutil.copyfile(b.ROOT/'client'/name,client/name)
        for name,path in files.items():
            shutil.copyfile(path,run/name if name.startswith('client/') else mod/name)
    exe = b.ROOT/'client/SaberTrials.x86_64.exe' if installed else run/'client/SaberTrials.x86_64.exe'
    print(run,flush=True)
    lines = ['wait 90','set st_controllerEnabled 0','set st_controllerMenuSpeed 5',
             'set st_controllerMenuLayout 0','ui_openmenu controlsMenu','wait 24']

    def press(button):
        lines.extend([f'st_padqa button {button} 1','wait 2',f'st_padqa button {button} 0','wait 10'])

    if profile_keyboard:
        lines = ['wait 90','set name Padawan','set st_controllerMenuLayout 0','ui_openmenu playerMenu','wait 26']
        if not installed:
            def click(x,y):
                lines.extend(['st_inspectqa move 0 0',f'st_padqa move {x} {y}','wait 3'])
                press(0)

            click(140,96)
            lines += ['st_profileqa assertkeyboard 1','screenshot_png name-keyboard']
            click(515,326)  # Clear
            click(117,326)  # Shift
            click(297,257)  # G
            click(117,326)  # Lowercase
            click(159,257)  # s
            click(205,192)  # 3
            click(179,326)  # Symbols
            click(110,192)  # !
            press(2)        # Erase
            press(11)       # Focus the first symbol and select without stick motion
            press(0)
            click(500,368)  # Done
            lines += ['st_profileqa assertkeyboard 0','st_profileqa assertname Gs3!',
                      'st_controlsqa assertvar name Padawan']
            click(140,96)
            click(515,326)
            press(1)
            lines += ['st_profileqa assertkeyboard 0','st_profileqa assertname Gs3!']
            click(568,456)  # Apply
            lines += ['st_controlsqa assertvar name Gs3!','st_profileqa assertdirty 0']
            lines += ['st_profileqa click 101','st_profileqa assertkeyboard 0','st_profileqa text MouseEntry',
                      'st_profileqa assertname MouseEntry','st_controlsqa assertvar name Gs3!']
            lines += ['set sv_pure 0','set g_gametype 0','devmap mp/ffa3','wait 400','team free','wait 80',
                      'ui_openmenu ingame_player','wait 26']
            click(140,68)
            lines += ['st_profileqa assertkeyboard 1','screenshot_png name-keyboard-ingame']
            press(1)
            lines += ['st_profileqa assertkeyboard 0']
    elif not installed:
        lines.extend(['st_inspectqa move 0 0','st_padqa move 372 130','wait 8'])
        press(0)
        lines.extend(['st_controlsqa state','screenshot_png controller-settings',
                      'st_inspectqa move 0 0','st_padqa move 207 371','wait 8',
                      'st_padqa button 0 1','st_padqa move 80 0','st_padqa button 0 0','wait 8',
                      'st_controlsqa assertvar st_controllerMenuSpeed 5',
                      'st_inspectqa move 0 0','st_padqa move 560 454','wait 8'])
        press(0)
        lines.append('st_controlsqa assertvar st_controllerMenuSpeed 10.00')
        press(1)
        lines.append('st_mainqa assertroot')
        lines.extend(['set st_controllerMenuLayout 1','ui_openmenu controlsMenu','wait 16',
                      'st_inspectqa move 0 0','st_padqa move 372 130','wait 8'])
        press(1)
        lines.append('st_controlsqa state')
        press(0)
        lines.extend(['st_mainqa assertroot','set sv_pure 0','set g_gametype 0','devmap mp/ffa3','wait 400','team free','wait 80'])
        press(6)
        lines.append('st_setupqa assertmenu ingame')
    lines.extend(['echo ST_GAMEPAD_MENU_COMPLETE','wait 8','quit'])
    (mod/'review.cfg').write_text('\n'.join(lines)+'\n')
    options = dict(fs_basepath=b.ROOT.parent,fs_homepath=run/'home',fs_game='SaberTrials',com_unpackLibraries=0,
                   logfile=2,net_ip='127.0.0.1',net_port=29198,r_fullscreen=0,r_mode=-1,
                   r_customwidth=1600,r_customheight=900,cl_renderer='rd-rend2',com_maxfps=60,s_initsound=0,com_introplayed=1)
    command = [str(exe),'+safe']
    for name,value in options.items():
        command.extend(['+set',name,str(value)])
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    process = subprocess.Popen(command+['+exec','review.cfg'],cwd=b.ROOT.parent,startupinfo=startup,
        env={**os.environ,'LOCALAPPDATA':str(run/'local-app-data')},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        assert process.wait(timeout=90)==0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    log = (mod/'qconsole.log').read_text(errors='replace')
    errors = [line for line in log.splitlines() if re.search(r'ST_(CONTROLS|SETUP|MAIN|PROFILE)_FAIL|Unknown command "st_',line)]
    assert 'ST_GAMEPAD_MENU_COMPLETE' in log and not errors,errors or log[-1200:]
    if profile_keyboard and not installed:
        assert all((screenshots/f'{name}.png').stat().st_size>10000 for name in ('name-keyboard','name-keyboard-ingame'))
    elif not installed:
        assert log.count('ST_CONTROLS_QA menu=controlsMenu tab=4')==2
        assert (screenshots/'controller-settings.png').stat().st_size>10000
    b.write(run/'result.json',dict(source=b.sha(b.RECEIPT),files={name:b.sha(path) for name,path in files.items()}))
    print('Passed '+run.name)


if __name__=='__main__':
    keyboard = '--profile-keyboard' in sys.argv
    if keyboard:
        candidate = import_module('Build-Name-Keyboard')
        b.OUT, b.RECEIPT = candidate.OUT, candidate.RECEIPT
    run('--installed' in sys.argv, keyboard)
