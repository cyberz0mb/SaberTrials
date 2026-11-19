"""Exercise a real local saber finish and retain native screenshots/logs."""
from pathlib import Path
import argparse
import ctypes
from ctypes import wintypes
import importlib.util
import json
import os
import re
import secrets
import socket
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('mvp_stage', ROOT / 'tools/Stage-MVP-Cinematic.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class MemoryCounters(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('pageFaults', wintypes.DWORD)] + [
        (name, ctypes.c_size_t) for name in ('peakWorking', 'working', 'peakPaged', 'paged',
        'peakNonPaged', 'nonPaged', 'pagefile', 'peakPagefile', 'private')]


def memory(process):
    info = MemoryCounters()
    info.cb = ctypes.sizeof(info)
    get_memory = ctypes.windll.psapi.GetProcessMemoryInfo
    get_memory.argtypes = [wintypes.HANDLE, ctypes.POINTER(MemoryCounters), wintypes.DWORD]
    return info.private if get_memory(int(process._handle), ctypes.byref(info), info.cb) else 0


def main(args):
    folder = stage.OUT / 'qa' / args.run
    if folder.exists():
        raise RuntimeError('Choose a new run name to preserve evidence')
    mod = stage.installed_home(folder) if args.installed else stage.stage(folder)
    if args.npc_regression:
        # A private, early-listed definition avoids the stock 2048-byte NPC
        # filename-list limit in installations with many custom NPC packages.
        npc = mod / 'ext_data/NPCs/000_mvp_qa.npc'
        npc.parent.mkdir(parents=True, exist_ok=True)
        npc.write_text('mvp_regression\n{\nplayerModel kyle\nweapon WP_NONE\n'
                       'health 30\nclass CLASS_STORMTROOPER\nrank crewman\n'
                       'playerTeam TEAM_ENEMY\nenemyTeam TEAM_PLAYER\n}\n')
    lines = stage.match_settings(scrimmage=args.scrimmage)
    password=secrets.token_hex(16)
    lines += ['set rconPassword "'+password+'"']
    target_kills=args.kills or (5 if args.scrimmage else 1)
    players=args.players or (4 if args.scrimmage else 2)
    lines += ['set fraglimit %d'%target_kills,'set sv_maxclients %d'%players,
              'set model "'+args.model+'"','set st_mvpTestSingleSaber 0']
    if args.dual:lines+=['set saber2 single_1']
    team_mode=args.team or args.gametype in (7,8)
    if team_mode:lines+=['set g_gametype %d'%(args.gametype or 6),'set g_teamForceBalance 0','set g_autoJoin 0']
    if args.gametype==7:lines+=['set g_siegeRespawn 0','set g_siegeTeamSwitch 0']
    if args.installed:
        lines = [line for line in lines if not line.startswith('set st_mvpPrototype ')]
    if args.trails is not None:
        lines += ['set cg_saberTrail ' + str(args.trails)]
    if args.dismember is not None:
        lines += ['set cg_dismember ' + str(args.dismember)]
    if args.npc_regression:
        lines += ['set g_allowNPC 1']
    # The NPC regression has explicit clear-space coordinates on Yavin.
    test_map = args.map or ('mp/duel6' if args.npc_regression else stage.TEST_MAP)
    lines += [('devmap' if args.npc_regression or args.gametype or test_map == 'mp/duel1' else 'map') + ' ' + test_map,
              'wait 180', 'team red' if team_mode else 'team free', 'wait 90']
    if args.nonfinal:
        lines += ['kill', 'wait 300', '+attack', 'wait 30', '-attack', 'wait 120']
    for number in range(1,players):
        lines += ['addbot "Kyle Katarn" 1 %s 0 "MVP Bot %d" duelist' % ('blue' if team_mode else 'free',number)]
    lines += ['wait 240', 'st_mvptestready']
    if args.gametype==7:
        # Siege starts active play after its normal teams-ready countdown.
        lines+=['wait 1800','st_mvptestready']
    if args.npc_regression:
        lines += ['setviewpos -1280 -1280 400 0', 'wait 60']
    elif test_map == 'mp/duel1':
        # Keep the combat fixture out of Bespin's narrow spawn alcoves and
        # away from the other two bots. The playable match never uses this.
        lines += ['setviewpos 480 640 200 90', 'wait 120']
    lines += ['st_mvpproof']
    if args.npc_regression:
        lines += ['setviewpos -1024 -1024 420 90', 'wait 120',
                  'npc spawn mvp_regression', 'wait 600', 'npc kill all', 'wait 120']
    lines += ['wait 650']
    if target_kills>1:
        for shot in range(target_kills-1):
            lines += ['+attack','wait 140','-attack','wait 240']
            if test_map == 'mp/duel1':
                # Avoid piling blocking corpses on one repeated strike spot.
                lines += ['setviewpos %d 640 200 90' % (640+160*shot), 'wait 80']
            lines += ['st_mvpproof','wait 80']
    lines += ['st_mvpproof status', 'screenshot_png mvp-ready', '+attack',
             'wait 15']
    for index in range(24):
        lines += ['wait 20', 'screenshot_png mvp-%02d' % index, 'st_mvpproof status']
        # Fast screenshot readback can otherwise release the final attack
        # before the fixture's finishing swing reaches its target.
        if index == (12 if args.scrimmage else 4):
            lines += ['-attack']
        # Without PNG readback, command waits reach the early samples before
        # intermission. Send the skip later so it exercises active playback.
        if args.skip and index == (13 if args.no_screenshots else 5):
            lines += ['togglemenu' if args.skip_key == 'escape' else 'st_mvpskip']
    lines += ['wait 3200' if target_kills>1 else 'wait 1600', 'screenshot_png mvp-results', 'set st_mvpPrototype 0',
              'map_restart 0', 'wait 120', 'st_mvpproof status', 'disconnect', 'wait 30', 'quit']
    if args.no_screenshots:
        lines = [line for line in lines if not line.startswith('screenshot_png ')]
        # PNG readback normally consumes wall time. Without it, wait counts run
        # faster, so leave enough time for natural playback before resetting.
        lines.insert(lines.index('set st_mvpPrototype 0'), 'wait 600')
    if args.video_restart:
        position = lines.index('set st_mvpPrototype 0')
        lines[position:position] = ['vid_restart', 'wait 600', 'st_mvpproof status']
    if args.npc_regression:
        # Isolate the non-player death: it must not create an MVP kill or
        # playback. Ordinary opponent-kill counting is covered by scrimmage.
        lines = [line for line in lines if line not in ('+attack', '-attack')]
    (mod / 'mvp-qa.cfg').write_text('\n'.join(lines) + '\n', encoding='ascii')
    environment = os.environ.copy()
    environment['LOCALAPPDATA'] = str(folder / 'local-app-data')
    command = [str(stage.executable(folder, args.installed))] + stage.arguments(folder, args.renderer, args.installed)
    command[command.index('net_port')+1]=str(args.port)
    command += ['+exec', 'mvp-qa.cfg']
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    process = subprocess.Popen(command, cwd=ROOT.parent if args.installed else folder / 'bin', env=environment, startupinfo=startup,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print('Native MVP check running, pid=' + str(process.pid), flush=True)
    started = time.monotonic()
    usage = []
    playback_seen=None
    replay_images=0
    kill_seen=None
    ended=False
    while process.poll() is None:
        usage.append((round(time.monotonic() - started, 2), memory(process)))
        if not args.no_screenshots or args.gametype:
            live_path=mod/'qconsole.log'
            live=live_path.read_text(errors='replace') if live_path.exists() else ''
            if args.gametype and 'MVP_CAPTURE kill=' in live and not ended:
                kill_seen=kill_seen or time.monotonic()
                if time.monotonic()-kill_seen>1.5:
                    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
                        sock.sendto(b'\xff'*4+('rcon '+password+' st_mvpproof end\n').encode(),('127.0.0.1',args.port))
                    ended=True
            if 'MVP_PLAYBACK start' in live and not args.no_screenshots:
                playback_seen=playback_seen or time.monotonic()
                if replay_images<6 and time.monotonic()-playback_seen>replay_images*.6:
                    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
                        sock.sendto(b'\xff'*4+('rcon '+password+' screenshot_png replay-%02d\n'%replay_images).encode(),('127.0.0.1',args.port))
                    replay_images+=1
        if time.monotonic() - started > max(100,target_kills*10+60):
            process.kill()
            process.wait()
            raise RuntimeError('MVP runtime timed out; evidence retained in ' + str(folder))
        time.sleep(.25)
    code = process.returncode
    log_path = mod / 'qconsole.log'
    log = log_path.read_text(errors='replace') if log_path.exists() else ''
    events = [line for line in log.splitlines() if 'MVP_' in line or 'Kill:' in line]
    elapsed = re.findall(r'MVP_PLAYBACK stopped elapsed=(\d+)', log)
    screenshots = sorted(p.name for p in (mod / 'screenshots').glob('*.png'))
    result = {'returncode': code, 'installed': args.installed, 'map': test_map, 'players':players,'killLimit':target_kills,'model':args.model,'dual':args.dual,'team':team_mode,'gametype':args.gametype or (6 if args.team else 0),'renderer': args.renderer, 'skip': args.skip, 'skipKey': args.skip_key if args.skip else None,
              'screenshotCapture': not args.no_screenshots,
              'videoRestart': args.video_restart, 'nonfinal': args.nonfinal,
              'trails': args.trails, 'dismember': args.dismember,
              'scrimmage': args.scrimmage,
              'npcRegression': args.npc_regression,
              'events': events, 'elapsed': elapsed, 'screenshots': screenshots,
              'peakProcessPrivateBytes': max((value for _, value in usage), default=0)}
    (folder / 'process-memory.json').write_text(json.dumps(usage) + '\n')
    (folder / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({**result, 'screenshots': len(screenshots),
                     'events': [line for line in events if 'MVP_STATUS' not in line]}, indent=2))
    statuses = re.findall(r'MVP_STATUS time=\d+ frames=(\d+) budgetBytes=(\d+) kill=(\d+)', log)
    if args.npc_regression:
        game_log = (mod / 'games.log').read_text(errors='replace')
        assert code == 0 and 'Killing NPC mvp_regression' in log, 'NPC death path was not exercised'
        assert any(int(victim) >= 64 for victim in re.findall(r'Kill: \d+ (\d+) \d+:',game_log))
        assert not elapsed and 'MVP_CAPTURE' not in log and 'MVP_FINAL' not in log
        assert any(int(row[0]) > 0 for row in statuses), 'Capture did not continue after NPC death'
        assert statuses[-1] == ('0','0','0'), statuses[-2:]
        stage.helper().verify()
        return
    if args.nonfinal:
        game_log = (mod / 'games.log').read_text(errors='replace')
        assert code == 0 and 'by MOD_SUICIDE' in game_log and 'by MOD_SABER' in game_log
        assert not elapsed and 'MVP_PLAYBACK start' not in log
        # A nonfinal kill is now retained for the completed-match montage.
        assert statuses[-1] == ('0','0','0'), statuses[-2:]
        stage.helper().verify()
        return
    if code or not elapsed or 'MVP_CAPTURE' not in log or 'MVP_PLAYBACK start' not in log:
        raise RuntimeError('MVP capture/playback did not complete; inspect ' + str(log_path))
    duration = int(elapsed[0])
    schedules = re.findall(r'MVP_PLAYBACK start .* shots=(\d+) kills=(\d+) duration=(\d+)', log)
    assert len(schedules) == 1, schedules
    shots, replay_kills, scheduled_ms = map(int, schedules[0])
    assert 0 < scheduled_ms <= 15000
    assert len(elapsed) == 1, 'Replay unexpectedly restarted: ' + str(elapsed)
    if args.skip:
        assert 0 < duration < scheduled_ms, duration
    else:
        assert scheduled_ms <= duration < scheduled_ms + (250 if args.no_screenshots else 1000), duration
    if target_kills>1:
        assert replay_kills>=1, schedules
        assert re.search(r'MVP_FINAL winner=0 total=%d clips=[1-9]'%target_kills,log), 'Incorrect MVP or missing kills'
        assert log.count('MVP_CAPTURE kill=') == target_kills
    if args.video_restart:
        assert statuses[-2] == ('0','0','0'), statuses[-2:]
    assert statuses and statuses[-1] == ('0', '0', '0'), statuses[-1:]
    assert max(int(row[1]) for row in statuses) <= 256 * 1024 * 1024
    effects = re.findall(r'MVP_EFFECTS trails=(\d+) limbs=(\d+) cuts=(\d+) settings=(-?\d+)/(-?\d+)',log)
    if args.trails is not None or args.dismember is not None or args.require_limb:
        assert len(effects) == 1, effects
        trails, limbs, cuts, trail_setting, dismember_setting = map(int,effects[0])
        if args.trails is not None:
            assert trail_setting == args.trails
            used_saber='by MOD_SABER' in (mod/'games.log').read_text(errors='replace')
            if args.trails==0:assert trails==0,effects
            elif used_saber:assert trails>0,effects
        if args.dismember is not None:
            assert dismember_setting == args.dismember
            if args.dismember == 0:
                assert limbs == 0 and cuts == 0, effects
        if args.require_limb:
            assert re.search(r'MVP_LIMBS captured=[1-8] ',log), 'No actual severed part captured'
            if dismember_setting >= 2:
                assert limbs > 0 and cuts > 0, effects
    stage.helper().verify()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--installed', action='store_true')
    parser.add_argument('--renderer', choices=('vanilla', 'rend2'), default='vanilla')
    parser.add_argument('--skip', action='store_true')
    parser.add_argument('--skip-key', choices=('escape','enter'), default='escape')
    parser.add_argument('--no-screenshots', action='store_true')
    parser.add_argument('--video-restart', action='store_true')
    parser.add_argument('--nonfinal', action='store_true')
    parser.add_argument('--trails', type=int, choices=(0,1,2))
    parser.add_argument('--dismember', type=int, choices=(0,1,2))
    parser.add_argument('--require-limb', action='store_true')
    parser.add_argument('--scrimmage', action='store_true')
    parser.add_argument('--npc-regression', action='store_true')
    parser.add_argument('--players',type=int)
    parser.add_argument('--kills',type=int)
    parser.add_argument('--map')
    parser.add_argument('--model',default='kyle/default')
    parser.add_argument('--dual',action='store_true')
    parser.add_argument('--team',action='store_true')
    parser.add_argument('--gametype',type=int,choices=(7,8))
    parser.add_argument('--port',type=int,default=29079)
    main(parser.parse_args())
