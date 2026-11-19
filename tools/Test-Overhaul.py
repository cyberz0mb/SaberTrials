"""Isolated loopback client checks; never reads or modifies the player's profile."""
from pathlib import Path
import importlib.util
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(tempfile.gettempdir()) / 'SaberTrials-overhaul-20261003'
RUNTIME = WORK / 'runtime'
HOME = RUNTIME / 'home'
MOD = RUNTIME / 'SaberTrials'
PORT = 27973


def command(text):
    password = (WORK / 'rcon-secret.txt').read_text()
    log = HOME / 'SaberTrials/qconsole.log'
    offset = log.stat().st_size if log.exists() else 0
    time.sleep(.12)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(2)
        sock.sendto(b'\xff'*4 + b'rcon ' + password.encode() + b' ' + text.encode() + b'\n', ('127.0.0.1', PORT))
        try:
            reply = sock.recv(65535)[10:].decode(errors='replace')
        except socket.timeout:
            reply = ''
    # Client commands can execute on the next frame, after RCON redirect ends.
    time.sleep(.2)
    if log.exists():
        with log.open('rb') as stream:
            stream.seek(offset)
            reply += stream.read().decode(errors='replace')
    return re.sub(r'\^[0-9]', '', reply).strip()


def value(name):
    response = command(name)
    match = re.search(r'= "([^"]*)"', response)
    if not match:
        raise AssertionError((name, response))
    return match[1]


def start(mode):
    if (WORK / 'test-pid.txt').exists():
        # Refuse to overwrite a running test's credentials or loaded modules.
        pid = int((WORK / 'test-pid.txt').read_text())
        active = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV'], capture_output=True, text=True)
        if f'"{pid}"' in active.stdout:
            raise RuntimeError('Previous test is still running; stop it with this tool first')
    base = RUNTIME / 'base'
    base.mkdir(parents=True, exist_ok=True)
    MOD.mkdir(parents=True, exist_ok=True)
    for asset in (ROOT.parent / 'base').glob('assets*.pk3'):
        dest = base / asset.name
        if not dest.exists():
            os.link(asset, dest)
    for name in ['SDL2.dll', 'OpenAL32.dll', 'rd-vanilla_x86_64.dll']:
        shutil.copy2(ROOT.parent / name, RUNTIME / name)
    for name in ['cgamex86_64.dll', 'jampgamex86_64.dll']:
        shutil.copy2(ROOT / name, MOD / name)
    built = WORK / 'build/Release'
    shutil.copy2(ROOT / 'uix86_64.dll' if mode == 'baseline' else built / 'uix86_64.dll', MOD / 'uix86_64.dll')
    shutil.copytree(ROOT / 'ui', MOD / 'ui', dirs_exist_ok=True)
    shutil.copytree(ROOT / 'server', MOD / 'server', dirs_exist_ok=True, ignore=shutil.ignore_patterns('private'))
    engine = ROOT.parent / 'openjk.x86_64.exe' if mode == 'baseline' else built / 'openjk.x86_64.exe'
    shutil.copy2(engine, RUNTIME / 'openjk.x86_64.exe')
    password = secrets.token_hex(16)
    (WORK / 'rcon-secret.txt').write_text(password)
    (MOD / 'st-overhaul-test.cfg').write_text(f'''set rconPassword {password}
set sv_pure 0
set sv_maxclients 4
set sv_maxOOBRate 0
set sv_maxOOBRateIP 0
set g_gametype 0
set name ST_ClientTest
set model kyle/default
set cl_allowDownload 0
set cl_drawRecording 1
set con_opacity 0.55
set g_synchronousClients 1
map mp/duel3
''')
    launch_engine = ROOT / 'client/SaberTrials.x86_64.exe' if mode == 'installed' else RUNTIME / 'openjk.x86_64.exe'
    args = [str(launch_engine), '+set', 'fs_basepath', str(RUNTIME),
            '+set', 'fs_homepath', str(HOME), '+set', 'fs_game', 'SaberTrials',
            '+set', 'net_ip', '127.0.0.1', '+set', 'net_port', str(PORT),
            '+set', 'r_fullscreen', '0', '+set', 'r_mode', '-1',
            '+set', 'r_customwidth', '1280', '+set', 'r_customheight', '720',
            '+set', 'cl_renderer', 'rd-vanilla', '+set', 's_initsound', '0',
            '+set', 'logfile', '2', '+set', 'developer', '0', '+set', 'com_maxfps', '60']
    for i in range(1, 6):
        args += ['+set', f'sv_master{i}', '']
    args += ['+exec', 'st-overhaul-test.cfg']
    si = subprocess.STARTUPINFO()
    si.dwFlags = subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0
    proc = subprocess.Popen(args, cwd=RUNTIME, startupinfo=si)
    (WORK / 'test-pid.txt').write_text(str(proc.pid))
    print('Started isolated', mode, 'client', proc.pid, flush=True)


def recording_check():
    before = set((HOME / 'SaberTrials/demos').glob('*.dm_26'))
    reply = command('st_record')
    assert 'recording to demos/' in reply.lower(), reply
    time.sleep(2)
    assert value('st_recording') == '1'
    command('screenshot_png ST-recording')
    reply = command('st_record')
    assert 'saved recording:' in reply.lower(), reply
    assert value('st_recording') == '0'
    for _ in range(2):
        assert 'recording to demos/' in command('st_record').lower()
        time.sleep(.2)
        assert 'saved recording:' in command('st_record').lower()
    created = set((HOME / 'SaberTrials/demos').glob('*.dm_26')) - before
    assert len(created) == 3, created
    for demo in created:
        data = demo.read_bytes()
        assert len(data) > 100 and data[-8:] == b'\xff'*8, demo
    print('PASS recording toggle, status, saved paths, unique files, and finalized demos', flush=True)
    (WORK / 'recording-result.json').write_text(json.dumps({'files': [str(p) for p in sorted(created)]}, indent=2))


def click(menu, item):
    response = command(f'st_clientqa move {menu} {item}')
    assert 'QA item missing' not in response and 'Unknown command' not in response, response
    command('st_clientqa click')


def ui_check():
    command('bind F6 "screenshot_png"')
    command('ui_openmenu ingame_controls')
    click('ingame_controls', 'othercontrolbutton')
    click('ingame_controls', 'st_record_bind')
    command('st_clientqa bindf8')
    response = command('bind F8')
    assert 'st_record' in response, response
    assert 'screenshot_png' in command('bind F6')
    command('screenshot_png ST-record-controls')
    command('st_clientqa escape')
    command('ui_openmenu ingame_setup')
    click('ingame_setup', 'inputmenubutton')
    command('screenshot_png ST-console-controls')
    click('ingame_setup', 'st_yaw_value')
    command('st_clientqa type 175.25')
    click('ingame_setup', 'st_input_apply')
    assert value('cl_yawspeed') == '175.25'
    assert value('st_consoleOverlay') == '1'
    click('ingame_setup', 'st_console_overlay')
    assert value('st_consoleOverlay') == '0'
    click('ingame_setup', 'st_console_overlay')
    assert value('st_consoleOverlay') == '1'
    command('st_clientqa escape')
    command('toggleconsole')
    time.sleep(.5)
    for opacity, name in [('0', 'clear'), ('.55', 'translucent'), ('1', 'opaque')]:
        command('con_opacity ' + opacity)
        command('echo Saber Trials console readability check 1234567890')
        command('screenshot_png ST-console-' + name)
    command('con_opacity .55')
    command('toggleconsole')
    print('PASS real menu clicks, record-key rebinding, unrelated binding preserved, input regression, console options', flush=True)


def keyboard_check():
    command('st_engineqa f8')
    assert value('st_recording') == '1'
    command('st_engineqa f8')
    assert value('st_recording') == '0'
    command('toggleconsole')
    command('st_engineqa type "set st_typing_check 175.25"')
    command('screenshot_png ST-console-typed')
    command('st_engineqa enter')
    assert value('st_typing_check') == '175.25'
    command('toggleconsole')
    print('PASS real engine key binding and typed console command', flush=True)


def title_controls_check():
    # Main-menu definitions load only after disconnecting. RCON then goes away,
    # so execute this sequence client-side and verify fresh assignment in its log.
    script = MOD / 'st-title-controls.cfg'
    script.write_text('''unbind F8
disconnect
wait 15
ui_openmenu controlsMenu
wait 5
st_clientqa move controlsMenu othercontrolbutton
st_clientqa click
wait 5
st_clientqa move controlsMenu st_record_bind
st_clientqa click
st_clientqa bindf8
wait 5
bind F8
screenshot_png ST-title-record-controls
wait 5
echo ST_TITLE_COMPLETE
quit
''')
    log = HOME / 'SaberTrials/qconsole.log'
    offset = log.stat().st_size
    command('exec st-title-controls.cfg')
    for _ in range(60):
        time.sleep(.25)
        with log.open('rb') as stream:
            stream.seek(offset)
            result = re.sub(r'\^[0-9]', '', stream.read().decode(errors='replace'))
        if 'ST_TITLE_COMPLETE' in result:
            break
    assert 'QA item missing' not in result and 'Unknown command' not in result, result[-3000:]
    assert 'Bind F8 = "st_record"' in result and 'ST_TITLE_COMPLETE' in result, result[-3000:]
    print('PASS title-screen Controls > Other recording-key assignment', flush=True)


def lifecycle_check():
    demos = HOME / 'SaberTrials/demos'
    before = set(demos.glob('*.dm_26'))
    # All four commands run in one frame, deliberately forcing a timestamp collision.
    (MOD / 'st-collision.cfg').write_text('st_record\nst_record\nst_record\nst_record\n')
    command('exec st-collision.cfg')
    new = set(demos.glob('*.dm_26')) - before
    assert len(new) == 2, new
    for path in new:
        assert path.read_bytes()[-8:] == b'\xff' * 8
    assert any(re.search(r'_\d{4}\.dm_26$', p.name) for p in new), new
    files = json.loads((WORK / 'recording-result.json').read_text())['files']
    replay = max((Path(f) for f in files), key=lambda p: p.stat().st_size)
    before = set(demos.glob('*.dm_26'))
    command('st_record')
    time.sleep(.5)
    log = HOME / 'SaberTrials/qconsole.log'
    offset = log.stat().st_size
    # RCON ends when the local server disconnects; the queued script continues client-side.
    script = MOD / 'st-lifecycle.cfg'
    script.write_text(f'''disconnect
st_recording
st_record
timescale 0.1
demo "{replay.name}"
wait 30
st_record
screenshot_png ST-replay
wait 30
disconnect
timescale 1
st_recording
echo ST_LIFECYCLE_COMPLETE
quit
''')
    command('exec st-lifecycle.cfg')
    for _ in range(60):
        time.sleep(.25)
        with log.open('rb') as stream:
            stream.seek(offset)
            result = re.sub(r'\^[0-9]', '', stream.read().decode(errors='replace'))
        if 'ST_LIFECYCLE_COMPLETE' in result:
            break
    assert 'Cannot record while playing a replay.' in result, result
    assert 'You must be in a level to record.' in result, result
    assert 'ST_LIFECYCLE_COMPLETE' in result, result
    assert result.count('Cvar st_recording = "0"') == 2, result[-3000:]
    new = set(demos.glob('*.dm_26')) - before
    assert len(new) == 1, new
    assert next(iter(new)).read_bytes()[-8:] == b'\xff' * 8
    print('PASS same-frame filename collisions, disconnect finalization, replay playback, and invalid-state rejection', flush=True)


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'start':
        start(sys.argv[2])
    elif action == 'command':
        print(command(sys.argv[2]))
    elif action == 'recording':
        recording_check()
    elif action == 'ui':
        ui_check()
    elif action == 'keyboard':
        keyboard_check()
    elif action == 'title':
        title_controls_check()
    elif action == 'lifecycle':
        lifecycle_check()
    else:
        raise SystemExit('Use start baseline|qa|production|installed, command TEXT, recording, ui, keyboard, or lifecycle')
