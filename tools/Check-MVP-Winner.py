"""Native Duel/legacy tournament boundary checks in an isolated local home."""
from pathlib import Path
import argparse
import importlib.util
import json
import os
import re
import secrets
import socket
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('winner_stage', ROOT / 'tools/Stage-MVP-Cinematic.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


def main(args):
    folder = stage.OUT / 'qa' / args.run
    if folder.exists():
        raise RuntimeError('Use a new run name to preserve evidence')
    mod = stage.installed_home(folder) if args.installed else stage.stage(folder)
    tournament = args.case in ('match', 'champion', 'forfeit')
    password = secrets.token_hex(16)
    first_round = None
    settings = stage.match_settings()
    if args.installed:
        settings = [line for line in settings if not line.startswith('set st_mvpPrototype ')]
    lines = settings + [
        'set rconPassword "' + password + '"',
        'set g_gametype 3', 'set st_duelBestOf ' + ('3' if args.case == 'series' or tournament else '1'),
        'set st_tournamentBestOf 3', 'set st_tournamentFinalBestOf 3',
        'set st_mvpTestSingleSaber 1',
        'set st_tournamentArenas "mp/duel1"', 'set duel_fraglimit 0',
        'set sv_maxclients 4', 'devmap mp/duel1', 'wait 180', 'team free', 'wait 90']
    for n in range(1, 4 if tournament else 2):
        lines += ['addbot "Kyle Katarn" 1 free 0 "Winner Bot %d" duelist' % n]
    lines += ['wait 240', 'st_mvptestready', 'setviewpos 480 640 200 90', 'wait 120', 'st_mvpproof']
    if tournament:
        lines += ['st_mvpwinnerproof %s 1 1' % ('champion' if args.case == 'champion' else 'match')]
    lines += ['wait 380']
    if args.case == 'series':
        # First real round must produce no replay and carry its 1-0 score
        # through the controller's normal map_restart into the deciding round.
        first_round = lines + ['st_mvpproof', 'st_mvptestready', '+attack', 'wait 600', '-attack']
        lines = ['wait 120', 'st_mvptestready', 'setviewpos 480 640 200 90',
                 'wait 120', 'st_mvpproof', 'wait 380']
    if args.case == 'forfeit':
        lines += ['st_tournament forfeit 1']
    elif args.case == 'disconnect':
        lines += ['kick "Winner Bot 1"']
    elif args.case == 'suicide':
        lines += ['kill']
    else:
        lines += ['st_mvpproof', 'st_mvptestready', '+attack']
    for n in range(26):
        lines += ['wait 18', 'screenshot_png winner-%02d' % n]
        if n % 4 == 0:
            lines += ['st_mvpproof status']
        if n == 16:
            lines += ['-attack']
        if args.skip and n == 16:
            lines += ['st_mvpskip']
    lines += ['-attack']
    # Let the engine's appended map_restart run before queuing another phase.
    # A giant cfg with later waits/quit would block the very transition tested.
    (mod / 'winner-qa.cfg').write_text('\n'.join(first_round or lines) + '\n', encoding='ascii')
    (mod / 'winner-next.cfg').write_text('\n'.join(lines) + '\n', encoding='ascii')
    (mod / 'winner-finish.cfg').write_text('screenshot_png winner-after\nst_mvpproof status\n'
        'set st_mvpPrototype 0\ndisconnect\nwait 20\nquit\n', encoding='ascii')
    environment = os.environ.copy()
    environment['LOCALAPPDATA'] = str(folder / 'local-app-data')
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    options=stage.arguments(folder,args.renderer,args.installed)
    options[options.index('net_port')+1]=str(args.port)
    process = subprocess.Popen([str(stage.executable(folder, args.installed))] +
        options + ['+exec', 'winner-qa.cfg'],
        cwd=ROOT.parent if args.installed else folder / 'bin', env=environment, startupinfo=startup,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print('Winner check running: ' + args.case, flush=True)
    started = time.monotonic()
    next_sent = first_round is None
    finish_sent = False
    phase_ready = None
    def command(config):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
            connection.sendto(b'\xff\xff\xff\xff' +
                ('rcon ' + password + ' exec ' + config + '\n').encode('ascii'), ('127.0.0.1', args.port))
    while process.poll() is None:
        log_path = mod / 'qconsole.log'
        live = log_path.read_text(errors='replace') if log_path.exists() else ''
        initialized = live.count('------- Game Initialization -------')
        if not next_sent and initialized >= 2:
            phase_ready = phase_ready or time.monotonic()
            if time.monotonic() - phase_ready > 3:
                command('winner-next.cfg'); next_sent = True; phase_ready = None
        required = 3 if first_round else 2
        if not finish_sent and 'MVP_PLAYBACK stopped' in live and initialized >= required:
            phase_ready = phase_ready or time.monotonic()
            if time.monotonic() - phase_ready > 3:
                command('winner-finish.cfg'); finish_sent = True
        if time.monotonic() - started > 100:
            process.kill(); process.wait()
            raise RuntimeError('Winner check timed out; evidence retained')
        time.sleep(.25)
    log = (mod / 'qconsole.log').read_text(errors='replace')
    events = [line for line in log.splitlines() if 'WINNER_' in line or 'MVP_PLAYBACK' in line or 'MVP_SHOT' in line]
    finals = re.findall(r'WINNER_FINAL kind=(\d+) winner=(\d+) loser=(\d+) score=(-?\d+)-(-?\d+) card=(\d+) forfeit=(\d+) clips=(\d+)', log)
    elapsed = [int(v) for v in re.findall(r'MVP_PLAYBACK stopped elapsed=(\d+)', log)]
    result = dict(case=args.case, renderer=args.renderer, installed=args.installed, returncode=process.returncode,
                  finals=finals, elapsed=elapsed, events=events)
    (folder / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)
    assert process.returncode == 0 and len(finals) == 1, 'Expected one completed result'
    assert finish_sent, 'Automatic next-round/bracket transition was not observed'
    kind, winner, loser, score, other, card, forfeit, clips = map(int, finals[0])
    assert kind == (3 if args.case == 'champion' else 2 if tournament else 1)
    assert len(elapsed) == 1, 'Intermediate/next rounds must not replay this result'
    if args.case in ('suicide', 'disconnect', 'forfeit'):
        assert card == 1 and clips == 0
        assert forfeit == (args.case != 'suicide')
        assert elapsed[0] <= 3500
    else:
        assert card == 0 and clips == 1
        assert score == (2 if args.case == 'series' or tournament else 1)
        assert other == (1 if tournament else 0)
        assert elapsed[0] <= 8500
        if not args.skip:
            assert elapsed[0] >= 7500
        else:
            assert elapsed[0] < 4500, 'Skip did not finish playback early'
    if args.case == 'series':
        assert 'WINNER_ROUND intermediate' in log
    if args.case == 'champion':
        assert 'Tournament Champion:' in log, 'Final did not advance to champion'
    stage.helper().verify()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--case', choices=('duel', 'series', 'match', 'champion', 'forfeit', 'suicide', 'disconnect'), required=True)
    parser.add_argument('--renderer', choices=('vanilla', 'rend2'), default='vanilla')
    parser.add_argument('--skip', action='store_true')
    parser.add_argument('--installed', action='store_true')
    parser.add_argument('--port',type=int,default=29079)
    main(parser.parse_args())
