"""Retire completed shortcuts and keep the normal launcher out of the project root."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / 'dist/launcher-layout.json'
INSTALL = ROOT / 'dist/mvp-cinematic-install.json'
MAIN = 'tools/launchers/SaberTrials.cmd'
MOVES = {'Launch-SaberTrials-Overhaul.cmd': MAIN}
for name in ('Play-SaberTrials-Purple-Test.cmd', 'Preview-SaberTrials-Purple-Katana.cmd',
             'Review-Katana-In-Blender.cmd'):
    MOVES[name] = 'tools/launchers/development/' + name
RETIRED = (
    'Launch-SaberTrials-MP.cmd', 'Launch-SaberTrials-Local-Duel.cmd',
    'Play-SaberTrials-MVP-Test.cmd', 'Play-SaberTrials-Duel-Replay-Test.cmd',
    'Play-SaberTrials-1v1-Tournament-Replay-Test.cmd', 'Test-SaberTrials-New-Styles.cmd',
    'Preview-SaberTrials-Stances.cmd', 'Restore-SaberTrials-Before-Hybrids.cmd',
    'Restore-SaberTrials-Before-Loadouts.cmd', 'Restore-SaberTrials-Before-Style-Feedback.cmd',
    'Restore-Tournament-Preview.cmd',
)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def child(name):
    path = (ROOT / name).resolve()
    assert path.is_relative_to(ROOT.resolve()) and path != ROOT.resolve(), name
    return path


def relocated(name, raw):
    text = raw.decode('ascii').replace('\r\n', '\n')
    if name == 'Launch-SaberTrials-Overhaul.cmd':
        anchor = 'for %%I in ("%~dp0..") do set "GAMEDATA=%%~fI"'
        assert text.count(anchor) == 1
        text = text.replace(anchor, 'for %%I in ("%~dp0..\\..") do set "STROOT=%%~fI"\n'
                            'for %%I in ("%STROOT%\\..") do set "GAMEDATA=%%~fI"')
        text = text.replace('%~dp0client\\', '%STROOT%\\client\\')
        text = text.replace('Saber Trials Overhaul', 'Saber Trials')
    else:
        assert text.startswith('@echo off\n')
        text = text[len('@echo off\n'):]
        if text.startswith('setlocal\n'):
            text = text[len('setlocal\n'):]
        text = text.replace('%~dp0', '%STROOT%\\')
        text = '@echo off\nsetlocal\nfor %%I in ("%~dp0..\\..\\..") do set "STROOT=%%~fI"\n' + text
        if not text.rstrip().endswith('endlocal'):
            text = text.rstrip() + '\nendlocal\n'
    return text.replace('\n', '\r\n').encode('ascii')


def main():
    if RECEIPT.exists():
        record = json.loads(RECEIPT.read_text())
        for name, digest in record['after'].items():
            assert sha(child(name)) == digest, 'Relocated launcher changed: ' + name
        assert not list(ROOT.glob('*.cmd')), 'A launcher has reappeared in the main folder.'
        print('Launchers are already organized.')
        return
    names = set(MOVES) | set(RETIRED)
    assert {p.name for p in ROOT.glob('*.cmd')} == names, 'Inspect changed launcher inventory first.'
    state = json.loads(INSTALL.read_text())
    for name, digest in {**state['after'], **state['protected']}.items():
        assert sha(child(name)) == digest, 'Installed file changed: ' + name
    originals = {name: child(name).read_bytes() for name in names}
    outputs = {new: relocated(old, originals[old]) for old, new in MOVES.items()}
    assert all(not child(name).exists() for name in outputs)
    backup = child('dist/backups/launcher-cleanup-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True)
    for name in names:
        shutil.copy2(child(name), backup / name)
        assert sha(backup / name) == hashlib.sha256(originals[name]).hexdigest()
    shutil.copy2(INSTALL, backup / INSTALL.name)
    # Work only on the exact reviewed files; never delete a directory or use a wildcard.
    try:
        for name, raw in outputs.items():
            path = child(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            assert path.read_bytes() == raw
        for name in names:
            path = child(name)
            assert path.read_bytes() == originals[name], 'Source changed during cleanup: ' + name
            path.unlink()
        updated = json.loads(json.dumps(state))
        for field in ('after', 'protected', 'sources'):
            for name in names:
                updated[field].pop(name, None)
        for old, new in MOVES.items():
            field = 'after' if old in state['after'] else 'protected'
            updated[field][new] = sha(child(new))
            if field == 'after':
                updated['sources'][new] = str(child(new))
        # Keep the original installation's before/backup set for historical rollback.
        updated['launcher_layout'] = str(RECEIPT)
        updated['retired_launchers'] = list(RETIRED)
        record = dict(completed=True, removed=list(RETIRED), moved=MOVES, backup=str(backup),
                      before={name: hashlib.sha256(raw).hexdigest() for name, raw in originals.items()},
                      after={name: sha(child(name)) for name in outputs},
                      previous_install_receipt_sha256=sha(backup / INSTALL.name))
        spec = importlib.util.spec_from_file_location('launcher_transaction', ROOT / 'tools/Install-Handedness.py')
        transaction = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(transaction)
        transaction.atomic_record(RECEIPT, record)
        transaction.atomic_record(INSTALL, updated)
        for name, digest in {**updated['after'], **updated['protected']}.items():
            assert sha(child(name)) == digest, 'Preserved/relocated file changed: ' + name
    except BaseException:
        for name, raw in originals.items():
            path = child(name)
            assert not path.exists() or path.read_bytes() == raw
            path.write_bytes(raw)
        for name, raw in outputs.items():
            path = child(name)
            if path.exists():
                assert path.read_bytes() == raw
                path.unlink()
        shutil.copy2(backup / INSTALL.name, INSTALL)
        if RECEIPT.exists():
            RECEIPT.unlink()
        raise
    print('Removed 11 completed/redundant launchers. Relocated main launcher and three unfinished animation tools.')
    print('Game files and settings preserved. Backup:', backup)


if __name__ == '__main__':
    main()
