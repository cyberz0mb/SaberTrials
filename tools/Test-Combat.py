"""Loopback-only combat integration checks with an isolated writable profile."""
from pathlib import Path
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
WORK = Path(tempfile.gettempdir())/'SaberTrials-combat-20261006'
RUNTIME = WORK/'runtime'
MOD = RUNTIME/'SaberTrials'
HOME = RUNTIME/'home'
PORT = 27974


def command(text):
    log = HOME/'SaberTrials/qconsole.log'
    offset = log.stat().st_size if log.exists() else 0
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        sock.settimeout(.3)
        secret = (WORK/'test-secret.txt').read_text()
        sock.sendto(b'\xff'*4+b'rcon '+secret.encode()+b' '+text.encode()+b'\n',('127.0.0.1',PORT))
        pieces=[]
        while True:
            try: pieces.append(sock.recv(65535)[10:].decode(errors='replace'))
            except (socket.timeout, ConnectionResetError): break
    time.sleep(.05)
    if log.exists():
        with log.open('rb') as stream:
            stream.seek(offset)
            pieces.append(stream.read().decode(errors='replace'))
    return re.sub(r'\^[0-9]','', ''.join(pieces))


def start(client=False, installed=False):
    if (WORK/'test-pid.txt').exists():
        pid=int((WORK/'test-pid.txt').read_text())
        r=subprocess.run(['tasklist','/FI',f'PID eq {pid}','/FO','CSV'],capture_output=True,text=True)
        if f'"{pid}"' in r.stdout: raise RuntimeError('Test server already running')
    MOD.mkdir(parents=True,exist_ok=True); (RUNTIME/'base').mkdir(exist_ok=True)
    for asset in (ROOT.parent/'base').glob('assets*.pk3'):
        dest=RUNTIME/'base'/asset.name
        if not dest.exists(): os.link(asset,dest)
    for name in ['jampgamex86_64.dll','cgamex86_64.dll']:
        shutil.copy2((ROOT if installed else WORK/'build/Release')/name,MOD/name)
    shutil.copytree(ROOT/'server',MOD/'server',dirs_exist_ok=True,ignore=shutil.ignore_patterns('private'))
    secret=secrets.token_hex(16); (WORK/'test-secret.txt').write_text(secret)
    (MOD/'st-combat-test.cfg').write_text(f'''set rconPassword {secret}
set sv_pure 0
set sv_maxclients 8
set sv_maxOOBRate 0
set sv_maxOOBRateIP 0
set g_gametype 0
set g_doWarmup 0
set fraglimit 0
set timelimit 0
set bot_minplayers 0
set st_combatMode 1
set st_masterModeActive 0
set st_activeDefense 1
set st_parryRecovery 1
set st_shields 1
set st_noFallDamage 1
set st_forceSpeed 1
set st_fastForceRegen 1
set st_forceRegenInterval 100
set st_shieldMax 50
set st_shieldRegenAmount 2
set g_synchronousClients 1
set name CombatTest
set model kyle/default
set cl_allowDownload 0
set dmflags 16
map mp/ffa3
''')
    engine = ROOT/'client/SaberTrials.x86_64.exe' if client else ROOT.parent/'openjkded.x86_64.exe'
    if client:
        for name in ['SDL2.dll','OpenAL32.dll','rd-vanilla_x86_64.dll']:
            shutil.copy2(ROOT.parent/name,RUNTIME/name)
        shutil.copy2(ROOT/'uix86_64.dll',MOD/'uix86_64.dll')
        for directory in ['ui','shaders']:
            shutil.copytree(ROOT/directory, MOD/directory, dirs_exist_ok=True)
        if (ROOT/'textures/streamer').exists():
            shutil.copytree(ROOT/'textures/streamer',MOD/'textures/streamer',dirs_exist_ok=True)
    args=[str(engine),'+set','fs_basepath',str(RUNTIME),
          '+set','fs_homepath',str(HOME),'+set','fs_game','SaberTrials',
          '+set','net_ip','127.0.0.1','+set','net_port',str(PORT),'+set','logfile','2']
    for i in range(1,6): args+=['+set',f'sv_master{i}','']
    if client:
        args+=['+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','1280',
               '+set','r_customheight','720','+set','cl_renderer','rd-vanilla','+set','s_initsound','0',
               '+set','com_maxfps','60']
    args+=['+exec','st-combat-test.cfg']
    si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    proc=subprocess.Popen(args,cwd=RUNTIME,startupinfo=si,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    (WORK/'test-pid.txt').write_text(str(proc.pid))
    for _ in range(70):
        if 'Saber Trials gametype' in command('st_status'): break
        if proc.poll() is not None: raise RuntimeError('Server exited during startup')
        time.sleep(.2)
    else: raise RuntimeError('Server startup timed out; inspect isolated qconsole.log')
    print('Started isolated combat server',proc.pid,flush=True)


def initial_check():
    reply=command('st_combat original')
    assert 'Combat preset queued: Original JKA' in reply, reply
    print('PASS combat preset command registered',flush=True)


def expect(text, *parts):
    reply = command(text)
    for part in parts: assert part in reply, (text, part, reply)
    return reply


def state(**fields):
    reply = expect('st_combatqa', 'QA mode=')
    for key, value in fields.items():
        assert re.search(r'\b'+key+'='+re.escape(str(value))+r'(?:\s|$)', reply), (key,value,reply)
    return reply


def apply():
    command('st_applyrules')
    time.sleep(1)


def suite(client=False):
    command('bot_thinktime 100000')
    if not client: command('addbot kyle 1')
    time.sleep(2)
    state(mode=1,recovery='350,200,75,0',regen=22,decay=59,passive=0,active=1,window=1,counterWeaponTime=0,masterDamage=30,dmflags=24,forceRegen=100,cooldownBypass=0)
    expect('st_combatqa spawn 0','armor=50','speed=3')
    if client: expect('st_predictionqa','recovery=350,200,75,0')
    initial_check()
    expect('st_combatoption recovery off','Combat option queued')
    state(mode=1,recovery='350,200,75,0')
    command('st_cancelrules')
    expect('st_status','Queued combat preset: none','recovery: on (saved on; queued none)')
    for text in ['st_combat nonsense','st_combat trials extra','st_combatoption recovery maybe','st_combatoption fake on']:
        expect(text,'Usage:')
    expect('st_status','Queued combat preset: none')
    command('st_combatoption master on')
    command('st_combat original'); apply()
    state(mode=0,recovery='500,300,150,50',regen=20,decay=60,passive=1,active=1,window=0,counterWeaponTime=500,masterDamage=30,dmflags=16,forceRegen=200)
    expect('st_status','master: off (saved on)','shields: off (saved on; queued none)')
    expect('st_combatqa spawn 0','armor=25','speed=0')
    if client: expect('st_predictionqa','recovery=500,300,150,50')
    print('PASS queued/canceled/invalid commands and Original combat gates',flush=True)
    command('st_combat trials'); apply()
    state(mode=1,masterDamage=50,regen=22,recovery='350,200,75,0')
    for option in ['defense','recovery','shields','nofall','speed','forceregen']:
        command(f'st_combatoption {option} off')
    apply()
    state(mode=1,recovery='500,300,150,50',regen=20,decay=60,passive=1,active=1,window=0,counterWeaponTime=500,masterDamage=50,dmflags=16,forceRegen=200)
    expect('st_combatqa spawn 0','armor=25','speed=0')
    if client: expect('st_predictionqa','recovery=500,300,150,50')
    command('st_combatoption shields on'); apply()
    state(mode=1,regen=22,recovery='500,300,150,50',window=0,forceRegen=200)
    command('st_combat original'); apply()
    command('st_combat trials'); apply()
    expect('st_status','shields: on (saved on; queued none)','defense: off (saved off; queued none)')
    # A direct setting is latched and applied by a normal restart too.
    command('set st_parryRecovery 1')
    state(recovery='500,300,150,50')
    command('map_restart 0'); time.sleep(1)
    state(recovery='350,200,75,0',window=0)
    if client: expect('st_predictionqa','recovery=350,200,75,0')
    print('PASS independent modifiers, preserved preferences, Master damage and latched restart',flush=True)
    # Verify normal round completion automatically activates the queued mode.
    command('st_combat original')
    command('timelimit 0.02'); time.sleep(7)
    if client:
        command('+attack'); command('-attack')  # ready at the real intermission
    time.sleep(1)
    state(mode=0,recovery='500,300,150,50')
    command('timelimit 0')
    print('PASS automatic round-boundary preset change',flush=True)
    command('writeconfig combat-persist.cfg')
    saved = (HOME/'SaberTrials/combat-persist.cfg').read_text()
    for entry in ['seta st_combatMode "0"','seta st_activeDefense "0"','seta st_shields "1"']:
        assert entry in saved, entry
    command('set g_gametype 3'); command('map mp/duel3'); time.sleep(4)
    expect('st_combatqa spawn 0','armor=0','speed=0')
    command('st_combat trials'); apply()
    expect('st_combatqa spawn 0','armor=50','speed=0')
    print('PASS archived settings and Duel-specific stock armor',flush=True)


def production_check():
    expect('st_status','Combat preset: Saber Trials Combat','Force regeneration interval: 100ms')
    expect('st_cmdlist','st_combat <original|trials>','st_combatoption')
    command('st_combat original'); apply()
    expect('st_status','Combat preset: Original JKA','Force regeneration interval: 200ms',
           'defense: off (saved on; queued none)','shields: off (saved on; queued none)')
    expect('st_record','recording to demos/')
    time.sleep(.5)
    expect('st_record','Saved recording:')
    command('st_combat trials'); apply()
    expect('st_status','Combat preset: Saber Trials Combat','recovery: on (saved on; queued none)')
    log=(HOME/'SaberTrials/qconsole.log').read_text(errors='replace')
    assert 'Info string length exceeded' not in log
    print('PASS installed production pair: preset transitions, saved options, status/help, recording, no settings overflow')


if __name__=='__main__':
    action=sys.argv[1]
    if action=='start': start()
    elif action=='start-client': start(client=True)
    elif action=='start-installed': start(client=True,installed=True)
    elif action=='command': print(command(sys.argv[2]))
    elif action=='initial': initial_check()
    elif action=='suite': suite('client' in sys.argv)
    elif action=='production': production_check()
    else: raise SystemExit('Use start, start-client, start-installed, command TEXT, initial, suite [client]')
