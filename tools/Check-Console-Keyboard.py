"""Verify opening, typing, executing and closing the controller console in a match."""
from datetime import datetime
from importlib import import_module
import os
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
b = import_module('Build-Console-Keyboard')


def run(installed=False,chat=False):
    folder = b.OUT/(('installed-' if installed else 'review-')+datetime.now().strftime('%H%M%S'))
    mod = folder/'home/SaberTrials'
    shots = mod/'screenshots'
    shots.mkdir(parents=True)
    if installed:
        exe = b.ROOT/b.EXE
        receipt='chat-keyboard-install.json' if chat else 'console-keyboard-install.json'
        assert b.sha(exe)==b.read(b.ROOT/'dist'/receipt)['after'][b.EXE]
    else:
        exe = folder/b.EXE
        exe.parent.mkdir()
        shutil.copyfile(b.builder.binary('engine-qa'),exe)
        for name in ('SDL2.dll','OpenAL32.dll','rd-rend2_x86_64.dll'):
            shutil.copyfile(b.ROOT/'client'/name,exe.parent/name)
        if chat:shutil.copyfile(b.files(True)['uix86_64.dll'],mod/'uix86_64.dll')
    print(folder,flush=True)
    lines = ['wait 75','set sv_pure 0','set st_controllerMenuLayout 0',
             'devmap mp/ffa3','wait 410','team free','wait 95']

    def press(button):
        lines.extend([f'st_padqa button {button} 1','wait 2',f'st_padqa button {button} 0','wait 3'])

    pointer = (81,314)

    def click(x,y):
        nonlocal pointer
        lines.append(f'st_padqa move {x-pointer[0]} {y-pointer[1]}')
        pointer = (x,y)
        press(0)

    def row(word, chars, y):
        for c in word:
            click(77+53*chars.index(c),y)

    if chat and not installed:
        lines[:0]=['wait 60','ui_openmenu controlsMenu','wait 17','st_controlsqa click 104','wait 12',
                   'st_controlsqa assertrows Controller 9','screenshot_png keyboard-settings','wait 12',
                   'st_controlsqa click 608','wait 5','st_controlsqa click 1302','wait 5','st_controlsqa assertvar st_virtualKeyboard 1',
                   'st_controlsqa click 100','wait 5','st_controlsqa click 10','st_controlsqa text "Pause menu"','wait 5',
                   'st_controlsqa asserthit 500 1','screenshot_png pause-binding']
        lines += ['st_padqa gameplay','wait 18','bind JOY3 messagemode','bind JOY4 messagemode2',
                  'bind JOY5 messagemode3','bind JOY6 togglemenu','bind JOY7 toggleconsole',
                  'set st_virtualKeyboard 0','st_padqa keyboarddevice 1']
        press(3)
        lines.append('st_padqa assertchat 1 0')
        press(3)
        lines.extend(['st_padqa assertchat 0 0','st_padqa keyboarddevice 0'])
        press(3)
        lines.append('st_padqa assertchat 1 1')
        press(3)
        lines.extend(['st_padqa assertchat 0 0','set st_virtualKeyboard 1'])
        press(3)
        lines.extend(['st_padqa assertchat 1 1','screenshot_png public-keyboard'])
        row('h','asdfghjkl-',363)
        row('i','qwertyuiop',331)
        click(516,462)
        lines.extend(['wait 24','st_padqa assertchat 0 0'])
        press(4)
        lines.extend(['st_padqa assertchat 2 1','screenshot_png team-keyboard'])
        press(4)
        lines.extend(['st_padqa assertchat 0 0','st_padqa privatefixture','st_padqa assertchat 3 1','screenshot_png private-keyboard'])
        press(5)
        lines.extend(['st_padqa assertchat 0 0','set st_virtualKeyboard 2'])
        press(3)
        lines.append('st_padqa assertchat 1 0')
        press(3)
        lines.append('st_padqa assertchat 0 0')
        press(7)
        lines.append('st_padqa assertconsole 1 0')
        press(7)
        lines.extend(['st_padqa assertconsole 0 0','set st_virtualKeyboard 1','messagemode','st_padqa assertchat 1 1'])
        press(6)
        lines.extend(['st_setupqa assertmenu ingame','st_padqa assertchat 0 0'])
        press(6)
        lines.append('screenshot_png pause-closed')
    elif not installed:
        lines.extend(['ui_openmenu st_qa_no_menu','wait 18',
                      'bind JOY3 toggleconsole','st_padqa assertconsole 0 0'])
        press(3)
        lines.extend(['wait 30','st_padqa assertconsole 1 1','screenshot_png console-keyboard'])
        press(14) # Select the next key using only the D-pad.
        press(0)
        press(2)
        row('e','qwertyuiop',331)
        row('c','zxcvbnm_.,',395)
        row('h','asdfghjkl-',363)
        row('o','qwertyuiop',331)
        click(270,427)
        row('q','qwertyuiop',331)
        press(2) # Backspace shortcut removes the test character.
        row('42','1234567890',300)
        click(145,427) # Symbols
        click(77,300) # !
        click(516,462)
        # The console appends to the native command queue after the rest of this script.
        lines.extend(['wait 10','st_padqa assertconsole 1 1','screenshot_png console-command'])
        press(3)
        lines.extend(['st_padqa assertconsole 0 0','wait 20','screenshot_png console-closed'])
        press(3)
        lines.append('st_padqa assertconsole 1 1')
        press(1)
        lines.extend(['st_padqa assertconsole 0 0','toggleconsole','st_padqa assertconsole 1 0'])
        press(3)
        lines.append('st_padqa assertconsole 0 0')
    lines.extend(['echo ST_CONSOLE_KEYBOARD_COMPLETE','wait 6'])
    if installed or chat:
        lines.append('quit')
    else:
        # The queued echo runs after this script. Keep the game alive until then.
        lines.append('wait 25')
    (mod/'review.cfg').write_text('\n'.join(lines)+'\n')
    options = dict(fs_basepath=b.ROOT.parent,fs_homepath=folder/'home',fs_game='SaberTrials',com_unpackLibraries=0,
                   logfile=2,net_ip='127.0.0.1',net_port=29201,r_fullscreen=0,r_mode=-1,
                   r_customwidth=1600,r_customheight=900,cl_renderer='rd-rend2',com_maxfps=60,s_initsound=0,com_introplayed=1)
    command = [str(exe),'+safe']
    for name,value in options.items():
        command.extend(['+set',name,str(value)])
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    process = subprocess.Popen(command+['+exec','review.cfg'],cwd=b.ROOT.parent,startupinfo=startup,
        env={**os.environ,'LOCALAPPDATA':str(folder/'local-app-data')},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        if installed or chat:
            assert process.wait(timeout=95)==0
        else:
            import time
            log_path = mod/'qconsole.log'
            deadline = time.monotonic()+45
            while time.monotonic()<deadline and process.poll() is None:
                if log_path.is_file() and re.search(r'^\S+ \S+ 42!$',log_path.read_text(errors='replace'),re.M):
                    break
                time.sleep(.15)
            assert process.poll() is None
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    log = (mod/'qconsole.log').read_text(errors='replace')
    assert all(check not in log for check in ('ST_PAD_CONSOLE_FAIL','ST_PAD_CHAT_FAIL','ST_CONTROLS_FAIL','ST_SETUP_FAIL','Unknown command "st_padqa"')),log[-3000:]
    assert 'ST_CONSOLE_KEYBOARD_COMPLETE' in log and 'entered the game' in log,log[-2000:]
    if chat and not installed:
        assert any('Padawan' in line and line.endswith('hi') for line in log.splitlines()),log[-3000:]
        assert all((shots/f'{name}.png').stat().st_size>10000 for name in ('keyboard-settings','public-keyboard','team-keyboard','private-keyboard'))
    elif not installed:
        assert ']echo 42!' in log and re.search(r'^\S+ \S+ 42!$',log,re.M),log[-3000:]
        assert all((shots/f'{name}.png').stat().st_size>10000 for name in ('console-keyboard','console-command','console-closed'))
    result=dict(source=b.sha(b.RECEIPT),files={name:b.sha(path) for name,path in b.files(True).items()}) if chat and not installed else dict(source=b.sha(b.RECEIPT),engine=b.sha(exe))
    b.write(folder/'result.json',result)
    print('Passed '+folder.name)


if __name__=='__main__':
    chat='--chat' in sys.argv
    if chat:
        b=import_module('Build-Chat-Keyboard')
        b.EXE='client/SaberTrials.x86_64.exe'
    run('--installed' in sys.argv,chat)
