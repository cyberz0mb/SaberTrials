"""Exercise DLC profile chat, role fallback and translation in a local match."""
from datetime import datetime
from importlib import import_module
import os
import re
import shutil
import subprocess
import sys
from zipfile import ZipFile

sys.dont_write_bytecode = True
b = import_module('Build-Bot-Chat')


def fixtures(mod):
    (mod/'botfiles').mkdir()
    (mod/'scripts').mkdir()
    records = {}
    for name, package, role in [('Trickster', 'hisoka', 'trickster'), ('Sentinel', 'luffy', 'sentinel'),
                                 ('Duelist', 'luffy', 'duelist'), ('Berserker', 'akaza', 'berserker')]:
        path = b.ROOT.parent/'base'/(package+'.pk3')
        with ZipFile(path) as archive:
            member = next(n for n in archive.namelist() if n.endswith('.jkb'))
            original = archive.read(member)
        # Keep the real installed dialogue bytes/line endings. Only raise the
        # probability in this private fixture so each event can be asserted.
        text = re.sub(rb'(chatfrequency\s+)\d+', rb'\g<1>10', original)
        personality = 'botfiles/qa_'+name.lower()+'.jkb'
        (mod/personality).write_bytes(text)
        records[name] = dict(package=str(path), sha256=b.sha(path), member=member,
                             personality=b.sha(mod/personality), role=role)
    # Same combat settings as the custom Trickster, with only its dialogue
    # removed. This isolates fallback from unrelated navigation differences.
    fallback = (mod/'botfiles/qa_trickster.jkb').read_bytes().split(b'BEGIN_CHAT_GROUPS')[0]
    (mod/'botfiles/qa_fallback.jkb').write_bytes(fallback+b'BEGIN_CHAT_GROUPS\r\n')
    for name in (*records, 'Fallback'):
        (mod/'scripts'/('qa_'+name.lower()+'.bot')).write_text(
            '{\nname "QA_'+name+'"\nmodel "kyle/default"\npersonality "botfiles/qa_'+name.lower()+'.jkb"\n}\n')
    return records


def run(installed=False):
    folder = b.OUT/f'{"installed" if installed else "runtime"}-{datetime.now():%Y%m%d-%H%M%S}'
    mod = folder/'home/SaberTrials'
    mod.mkdir(parents=True)
    staged = {}
    for name, source in b.files().items():
        staged[name] = b.ROOT/name if installed else mod/name
        if not installed: shutil.copyfile(source, staged[name])
    hashes = {name:b.sha(path) for name,path in staged.items()}
    source_hash = b.sha(b.RECEIPT)
    models = fixtures(mod)
    lines = ['wait 60', 'set name "Bot Chat Tester"', 'set sv_pure 0', 'set g_gametype 0',
        'set sv_maxclients 12', 'set g_warmup 0', 'set fraglimit 0', 'set timelimit 0',
        'set bot_minplayers 0', 'set st_mvpPrototype 0', 'set sv_allowDownload 0',
        'set st_botTricksterChat 5000', 'set cg_chatBox 60000', 'set st_translate 1',
        'set st_translateSource 1', 'set st_translateTarget 2', 'set st_translateOriginal 1',
        *['set sv_master'+str(i)+' ""' for i in range(1,6)],
        'devmap mp/duel1', 'wait 450', 'team free', 'wait 90',
        'ui_openmenu ingame_setup', 'wait 10', 'togglemenu', 'wait 20', 'god']
    for name, record in models.items():
        lines += [f'addbot QA_{name} 3 free 0 QA_{name} '+record['role'], 'wait 360']
    lines += ['addbot QA_Fallback 3 free 0 QA_Fallback trickster', 'wait 4500',
        'st_botstatus', 'st_translatorinfo', 'screenshot_png profile-chat',
        'echo ST_BOT_CHAT_CHECK_COMPLETE', 'wait 15', 'quit']
    (mod/'test.cfg').write_text('\n'.join(lines)+'\n')
    options = dict(fs_basepath=b.ROOT.parent, fs_homepath=folder/'home', fs_game='SaberTrials',
        com_unpackLibraries=0, logfile=2, net_ip='127.0.0.1', net_port=29584, r_fullscreen=0,
        r_mode=-1, r_customwidth=1280, r_customheight=720, cl_renderer='rd-vanilla', com_maxfps=60,
        s_initsound=0, com_introplayed=1, cl_allowDownload=0)
    command = [str(b.ROOT/'client/SaberTrials.x86_64.exe'), '+safe']
    for name,value in options.items(): command += ['+set',name,str(value)]
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    print(folder, flush=True)
    process = subprocess.Popen(command+['+exec','test.cfg'], cwd=b.ROOT.parent, startupinfo=startup,
        env={**os.environ,'LOCALAPPDATA':str(folder/'local-app-data')},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try: assert process.wait(timeout=180) == 0
    finally:
        if process.poll() is None: process.kill(); process.wait()
    log = (mod/'qconsole.log').read_text(encoding='utf8', errors='replace')
    assert 'ST_BOT_CHAT_CHECK_COMPLETE' in log, log[-2500:]
    assert 'Personality file contains no GeneralBotInfo' not in log
    game_log = (mod/'games.log').read_text(encoding='utf8', errors='replace')
    spoken = {}
    for name in (*models, 'Fallback'):
        spoken[name] = re.findall(r'say: QA_'+name+r': ([^\r\n]+)', game_log)
        assert spoken[name], (name, log[-3000:])
        if name != 'Fallback':
            text = (mod/'botfiles'/('qa_'+name.lower()+'.jkb')).read_text(errors='replace')
            for line in spoken[name]:
                # Lines with the normal %s/%a name substitution are checked by
                # their fixed prefix; all others must come from the DLC verbatim.
                assert line in text or any(p.split('%')[0].strip() and line.startswith(p.split('%')[0].strip())
                    for p in text.splitlines() if '%' in p), (name, line)
    fallback = {'Relax. I am only passing through.', 'Your saber looks safer switched off.',
        'I am definitely not behind you.', 'Was that supposed to be a challenge?'}
    assert set(spoken['Fallback']) <= fallback
    assert all(not (set(lines) & fallback) for name,lines in spoken.items() if name != 'Fallback')
    states = re.findall(r'ST_TRANSLATOR [^\n]+', log)
    assert states and int(re.search(r'translated=(\d+)', states[-1])[1]) > 0, states
    assert source_hash == b.sha(b.RECEIPT)
    assert hashes == {name:b.sha(path) for name,path in staged.items()}
    b.write(folder/'result.json', dict(source=source_hash, files=hashes, installed=installed,
        profiles=models, spoken=spoken, translator=states[-1], log=b.sha(mod/'qconsole.log'),
        game_log=b.sha(mod/'games.log')))
    print('Passed all four roles, DLC dialogue priority, empty-profile fallback and bot translation.', flush=True)


if __name__ == '__main__': run('--installed' in sys.argv)
