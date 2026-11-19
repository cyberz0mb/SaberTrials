"""Install/restore a menu-only visual preview. Never launch JKA or change gameplay/accounts."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
TARGET = 'ui/jamp/ingame_player.menu'
STATE = ROOT/'dist/tournament-visual-preview-install.json'
STAGE = ROOT/'dist/tournament-visual-preview'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


menus = load('visual_menus', 'tools/Stage-Tournament.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def idle():
    processes = subprocess.check_output(['tasklist', '/FO', 'CSV'], text=True).lower()
    if any('"'+n+'"' in processes for n in ('sabertrials.x86_64.exe', 'openjk.x86_64.exe', 'jamp.exe', 'openjkded.x86_64.exe')):
        raise RuntimeError('Close Saber Trials before changing preview files.')


def sets(values):
    return ' ; '.join('setcvar '+name+' "'+str(value)+'"' for name, value in values.items())


def cfg(mode):
    v = {f'ui_stPv{i}': '' for i in range(61)}
    v.update({f'ui_stPv{k}': '0' for k in ('CanJoin', 'CanLeave', 'CanReady', 'HasBracket')})
    for i in range(4):
        v[f'ui_stPvBracketPage{i+1}'] = '1'
    for i in range(5):
        v[f'ui_stPvSubAvailable{i}'] = '0'
    values = {0: 'Ready check | 5v5 TFFA / 50 kills', 11: 'Ready', 12: '0  -  0',
              44: 'Both complete lineups must select Ready. Click again to unready.',
              45: 'VISUAL PREVIEW - sample players; no account or match actions.',
              46: '8 / 8 teams registered', 47: 'Blue Horizon', 48: 'Crimson Guard',
              49: '5/5 present | 4/5 ready', 50: '5/5 present | 5/5 ready',
              51: 'Time played 0:00 / 10:00',
              54: 'No replacement available in this sample. Try the reconnect preview.'}
    for i, name in enumerate(('You (sample)', 'Mira', 'Orion', 'Rook', 'Nova')):
        values[1+i] = name+' | '+('Not ready' if i == 0 else 'READY')
    for i, name in enumerate(('Kade', 'Echo', 'Vex', 'Sol', 'Ash')):
        values[6+i] = name+' | READY'
    v['ui_stPvCanReady'] = v['ui_stPvHasBracket'] = '1'
    if mode == 'individual':
        values.update({0: 'Ready check | Individual / 10 rounds', 46: '32 / 32 players registered',
                       47: 'You (sample)', 48: 'Duelist 2', 49: '1/1 present | 0/1 ready',
                       50: '1/1 present | 1/1 ready', 6: 'Duelist 2 | READY', 51: 'Rounds played 0 / 10'})
        for n in (2, 3, 4, 5, 7, 8, 9, 10):
            values[n] = ''
    if mode == 'registration':
        values.update({0: 'Registration | Individual / 10 rounds', 46: '8 / 32 players registered',
                       47: 'Current match', 48: 'Opponent', 49: 'Waiting for bracket', 50: 'Waiting for bracket',
                       12: 'All 10 rounds; deciding round at 5-5', 51: '',
                       44: 'An even 8-32 players required. The operator locks the bracket.'})
        for n in range(1, 11):
            values[n] = ''
        v['ui_stPvCanJoin'] = '1'
        v['ui_stPvCanReady'] = v['ui_stPvHasBracket'] = '0'
    if mode == 'reconnect':
        values.update({0: 'Paused | 5v5 TFFA / 50 kills', 1: 'Absent teammate | Disconnected',
                       49: '4/5 present | 0/5 ready', 50: '5/5 present | 0/5 ready', 52: 'Reconnect: 7:42',
                       44: 'Match paused: waiting for reconnect or a registered substitute.',
                       54: 'Sample reserve: choose the absent teammate below.', 56: 'Replace absent teammate'})
        for n in range(2, 11):
            values[n] = values[n].replace('READY', 'Not ready')
        v['ui_stPvCanReady'] = '0'
        v['ui_stPvSubAvailable0'] = '1'
    for i in range(31):
        values[i+13] = f'{i+1}. '+(f'Duelist {i*2+1} / Duelist {i*2+2}' if i < 16 else 'TBD / TBD')+(' [Current]' if i == 0 else '')
    v.update({'ui_stPv'+str(k): str(value) for k, value in values.items()})
    v['ui_stPvUnreadyCount'] = values[49] if mode != 'reconnect' else '5/5 present | 0/5 ready'
    v['ui_stPvReadyCount'] = re.sub(r'(\d+)/(\d+) ready',
        lambda match: str(int(match[1])+1)+'/'+match[2]+' ready', v['ui_stPvUnreadyCount'])
    return ''.join('set '+key+' "'+value.replace(';', ',')+'"\n' for key, value in v.items())


def preview():
    text = menus.tournament().replace('ui_stEvent', 'ui_stPv').replace('ui_ste', 'ui_stPv')
    text = text.replace('ingame_tournament', 'st_preview_lobby').replace('st_event_', 'st_preview_')
    text = text.replace('exec "tournament status"', 'setcvar ui_stPv55 "Visual preview only."')
    text = text.replace('exec "tournament bracket"', 'setcvar ui_stPv55 "Sample bracket only."')
    text = text.replace('Current matchup, upcoming opponents and completed results', 'VISUAL PREVIEW / sample 32-player bracket')
    text = text.replace('open st_pause_account', 'open st_preview_account')
    text = text.replace('onOpen { setcvar ui_stPv55 "Visual preview only." ; setfocus back ; }',
                        'onOpen { show ready ; hide preview_unready ; setcvar ui_stPv11 "Ready" ; setfocus back ; }', 1)
    text = text.replace('exec "tournament ready"',
                        sets({'ui_stPv11': 'Unready', 'ui_stPv1': 'You (sample) | READY',
                              'ui_stPv55': 'Preview: ready selected. No match will start.'})+
                        ' ; setcvartocvar ui_stPv49 ui_stPvReadyCount ; hide ready ; show preview_unready ; setfocus preview_unready')
    unready = menus.event_button('preview_unready', 'Unready', 18, 371, 120,
        sets({'ui_stPv11': 'Ready', 'ui_stPv1': 'You (sample) | Not ready', 'ui_stPv55': 'Preview: not ready.'})+
        ' ; setcvartocvar ui_stPv49 ui_stPvUnreadyCount ; hide preview_unready ; show ready ; setfocus ready', 'ui_stPvCanReady').replace('visible 1', 'visible 0')
    a, b = menus.span(text, 'st_preview_lobby')
    text = text[:b-1]+unready+text[b-1:]
    text = text.replace('exec "tournament join"', sets({'ui_stPvCanJoin': 0, 'ui_stPvCanLeave': 1,
        'ui_stPv46': '9 / 32 players registered', 'ui_stPv55': 'Preview: registration confirmed.'}))
    text = text.replace('exec "tournament leave"', sets({'ui_stPvCanJoin': 1, 'ui_stPvCanLeave': 0,
        'ui_stPv46': '8 / 32 players registered', 'ui_stPv55': 'Preview: registration removed.'}))
    for i in range(5):
        text = text.replace(f'exec "st_preview_substitute {i}"', sets({'ui_stPvSubAvailable0': 0,
            'ui_stPvCanReady': 1, 'ui_stPv0': 'Ready check | 5v5 TFFA / 50 kills', 'ui_stPv52': '',
            'ui_stPv1': 'You (sample) | Not ready', 'ui_stPv49': '5/5 present | 0/5 ready',
            'ui_stPv56': '', 'ui_stPv54': 'Preview replacement complete.',
            'ui_stPv44': 'Both complete lineups must select Ready. Click again to unready.',
            'ui_stPv55': 'Preview: substitute selected. Everyone must ready again.'}))
    # A read-only account sample uses the real popup layout and never starts OAuth.
    account = menus.account('st_preview_account')
    account = re.sub(r'ui_stAccount(\w+)', r'ui_stPvAccount\1', account)
    account = account.replace('exec "login"', 'setcvar ui_stPvAccountStatus "Preview only. No sign-in is performed."')
    account = account.replace('exec "logout"', 'setcvar ui_stPvAccountStatus "Preview only. Your account is unchanged."')
    account = account.replace('onOpen { setfocus back ; }', 'onOpen { '+sets({
        'ui_stPvAccountName': 'Sample ranked player', 'ui_stPvAccountTeam': 'Sample team: Blue Horizon',
        'ui_stPvAccountStatus': 'VISUAL PREVIEW - your real account is unchanged.',
        'ui_stPvAccountCanLogin': 1, 'ui_stPvAccountCanLogout': 0})+' ; setfocus back ; }')
    text += account
    chooser = menus.panel('ingame_tournament', 'TOURNAMENT / VISUAL PREVIEW', 65, 80, 510, 320, 'setfocus back ;')
    chooser += menus.label('help', 'Sample data only. Choose a screen to inspect.', 20, 48, 470, '.68')
    for i, (mode, name) in enumerate((('team', 'Team lobby / 5v5'), ('individual', 'Individual lobby / 32 players'),
                                    ('registration', 'Registration / Join / Leave'), ('reconnect', 'Reconnect / Substitutes'))):
        chooser += menus.event_button('sample'+str(i), name, 20, 85+i*42, 470,
            f'exec "exec st-ui-preview-{mode}.cfg" ; open st_preview_lobby')
    chooser += menus.button('back', 'Back', 390, 274, 100, 'close ingame_tournament')
    text += chooser+'}\n'
    # Fail closed if any production action or account field escaped rewriting.
    assert not re.search(r'ui_stAccount|ui_stEvent|ui_ste\d|st_event_', text)
    assert re.findall(r'\bexec\s+"([^"]+)"', text) == [
        'exec st-ui-preview-'+m+'.cfg' for m in ('team', 'individual', 'registration', 'reconnect')]
    for script in re.findall(r'\b(?:action|onOpen|onESC|onFocus|leaveFocus)\s*\{([^}]*)\}', text):
        tokens = re.findall(r'"[^"\n]*"|[^\s;]+|;', script)
        serialized = sum(len(t.strip('"')) + (2 if len(t.strip('"')) > 1 else 0) + 1 for t in tokens)
        assert serialized < 2048, 'Menu script exceeds native parser limit'
    return text


def install():
    raise RuntimeError('Pause-menu preview retired. Use Stage-Tournament-Frontend.py stage/install for Play -> Tournament.')
    idle()
    if STATE.exists() and json.loads(STATE.read_text()).get('installed'):
        print('Visual preview is already installed.'); return
    STAGE.mkdir(parents=True, exist_ok=True)
    original = (ROOT/TARGET).read_text()
    a, b = menus.span(original, 'ingame_tournament')
    updated = original[:a]+preview()+original[b:]
    updated = updated.replace('Join, leave, view, or vote to start the Saber Trials Tournament.',
                              'Preview tournament menus using sample data. No match is started.')
    candidate = STAGE/'ingame_player.menu'; candidate.write_text(updated)
    configs = {}
    for mode in ('team', 'individual', 'registration', 'reconnect'):
        name = 'st-ui-preview-'+mode+'.cfg'
        assert not (ROOT/name).exists(), 'Refusing to replace an existing CFG'
        content = cfg(mode)
        assert all(re.fullmatch(r'set ui_stPv\w+ "[^"\n;]*"', line) for line in content.splitlines())
        configs[name] = content
    before = json.loads((ROOT/'dist/verification/tournament-ui-20261023/installed-before.json').read_text())
    protected = {n: sha(ROOT/n) for n in before if n != TARGET}
    backup = ROOT/'dist/backups'/('tournament-visual-'+time.strftime('%Y%m%d-%H%M%S'))
    installer = load('preview_transaction', 'tools/Install-Staff.py')
    made = []
    try:
        for name, content in configs.items():
            with (ROOT/name).open('x') as output: output.write(content)
            made.append(name)
        result = installer.transaction(ROOT, {TARGET: candidate}, backup)
    except Exception:
        for name in made: (ROOT/name).unlink()
        raise
    assert all(sha(ROOT/n) == h for n, h in protected.items())
    result.update(installed=True, menu_only=True, game_or_server_launched=False, protected=protected,
                  preview_configs={n: sha(ROOT/n) for n in made})
    STATE.write_text(json.dumps(result, indent=2)+'\n')
    print('Installed one visual-preview menu and four UI-only sample files. Gameplay, accounts and personal CFGs unchanged.')


def restore():
    idle(); record = json.loads(STATE.read_text())
    if not record['installed']: print('Preview is already restored.'); return
    backup = (ROOT/record['backup']).resolve()
    assert backup.is_relative_to((ROOT/'dist/backups').resolve())
    assert sha(ROOT/TARGET) == record['after'][TARGET], 'Menu changed since preview installation'
    assert sha(backup/TARGET) == record['before'][TARGET], 'Backup changed'
    for n, h in record['preview_configs'].items():
        assert n in ['st-ui-preview-'+m+'.cfg' for m in ('team', 'individual', 'registration', 'reconnect')]
        assert sha(ROOT/n) == h, 'Preview CFG changed'
    pending = (ROOT/TARGET).with_suffix('.preview-restore')
    with pending.open('xb') as output: output.write((backup/TARGET).read_bytes())
    os.replace(pending, ROOT/TARGET)
    for n in record['preview_configs']: (ROOT/n).unlink()
    assert sha(ROOT/TARGET) == record['before'][TARGET]
    record['installed'] = False; STATE.write_text(json.dumps(record, indent=2)+'\n')
    print('Original Player menu restored. UI-only sample files removed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'restore'))
    args = parser.parse_args()
    install() if args.action == 'install' else restore()
