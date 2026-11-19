"""Verify and install a production game/cgame pair, with backup and rollback."""
from pathlib import Path
import hashlib
import json
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
BUILD = Path(tempfile.gettempdir())/'SaberTrials-combat-20261006/build/Release'
NAMES = ('jampgamex86_64.dll', 'cgamex86_64.dll')
VERSION = 'combat-20261006'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((BUILD/'combat-manifest.json').read_text())
    if manifest['kind'] != 'production': raise RuntimeError('Refusing to install QA modules')
    for name in NAMES:
        if digest(BUILD/name) != manifest['files'][name]: raise RuntimeError('Build hash mismatch: '+name)
        if any(marker in (BUILD/name).read_bytes() for marker in
               [b'st_combatqa', b'st_predictionqa', b'QA spawn armor=', b'QA prediction recovery=']):
            raise RuntimeError('QA hook found: '+name)
    backup = ROOT/'dist/backups'/VERSION
    backup.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        if not (backup/name).exists(): shutil.copy2(ROOT/name, backup/name)
    old_hashes = {name:digest(backup/name) for name in NAMES}
    (backup/'backup-manifest.json').write_text(json.dumps(old_hashes,indent=2)+'\n')
    # Stage both modules before replacing either. Roll back the current pair on failure.
    with tempfile.TemporaryDirectory(prefix='combat-install-') as temporary:
        previous = Path(temporary)
        for name in NAMES:
            shutil.copy2(ROOT/name, previous/name)
            shutil.copy2(BUILD/name, ROOT/(name+'.tmp'))
        replaced = []
        try:
            for name in NAMES:
                (ROOT/(name+'.tmp')).replace(ROOT/name)
                replaced.append(name)
            for name in NAMES:
                if digest(ROOT/name) != manifest['files'][name]: raise RuntimeError('Installed hash mismatch')
        except Exception:
            for name in reversed(replaced): shutil.copy2(previous/name, ROOT/name)
            raise
        finally:
            for name in NAMES:
                staged = ROOT/(name+'.tmp')
                if staged.exists(): staged.unlink()
    (ROOT/'client/combat-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    paths = [ROOT/name for name in NAMES]
    paths += [ROOT/p for p in ['client/combat-manifest.json','LICENSE.txt','CREDITS.txt',
        'tools/Build-Combat.py','tools/Build-Overhaul.py','tools/Install-Combat.py','tools/Test-Combat.py',
        'docs/COMBAT_MODES.md','docs/ADMIN_COMMANDS.md','docs/OVERHAUL_PROGRESS.md',
        'docs/V1_SCOPE.md','server/sabertrials-common.cfg']]
    paths += sorted((ROOT/'tests').glob('combat_*_qa.inc'))
    for directory in ['development-source/bot-roles/codemp','development-source/client-game']:
        paths += sorted(p for p in (ROOT/directory).rglob('*') if p.is_file())
    package = ROOT/'dist'/('SaberTrials-'+VERSION+'.zip')
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in paths: archive.write(path,'SaberTrials/'+path.relative_to(ROOT).as_posix())
    package.with_suffix('.zip.sha256').write_text(digest(package)+'  '+package.name+'\n')
    print('Installed verified production combat pair. Backup:',backup)
    print('Incremental update:',package)


if __name__ == '__main__': main()
