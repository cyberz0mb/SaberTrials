"""Build the paired Saber Trials game/client-game modules from pinned source."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(tempfile.gettempdir()) / 'SaberTrials-combat-20261006'
spec = importlib.util.spec_from_file_location('client_build', ROOT / 'tools/Build-Overhaul.py')
client_build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_build)
SOURCE = WORK / ('OpenJK-' + client_build.REVISION)


def prepare():
    WORK.mkdir(exist_ok=True)
    archive = client_build.WORK / 'openjk.zip'
    if not archive.exists():
        client_build.WORK.mkdir(parents=True, exist_ok=True)
        client_build.urllib.request.urlretrieve(
            'https://codeload.github.com/JACoders/OpenJK/zip/' + client_build.REVISION, archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != client_build.ARCHIVE_SHA256:
        raise RuntimeError('Pinned source checksum mismatch')
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            if not (WORK / member.filename).resolve().is_relative_to(SOURCE.resolve()):
                raise RuntimeError('Unsafe source archive path')
        z.extractall(WORK)
    for overlay in ['bot-roles', 'client-game']:
        shutil.copytree(ROOT / 'development-source' / overlay / 'codemp', SOURCE / 'codemp', dirs_exist_ok=True)
    return SOURCE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--qa', action='store_true')
    args = parser.parse_args()
    manifest_path = WORK/'build/Release/combat-manifest.json'
    if manifest_path.exists(): manifest_path.unlink()
    prepare()
    if args.qa:
        source = SOURCE / 'codemp/game/g_svcmds.c'
        s = source.read_text()
        hook = (ROOT / 'tests/combat_game_qa.inc').read_text()
        s = s.replace('svcmd_t svcmds[] = {', hook + '\nsvcmd_t svcmds[] = {\n { "st_combatqa", Svcmd_STCombatQA_f, qfalse },')
        if 'static void Svcmd_STCombatQA_f' not in s:
            raise RuntimeError('QA insertion point missing')
        source.write_text(s, newline='\n')
        source = SOURCE / 'codemp/game/w_saber.c'
        source.write_text(source.read_text() + '\n' + (ROOT/'tests/combat_saber_qa.inc').read_text(), newline='\n')
        source = SOURCE / 'codemp/cgame/cg_consolecmds.c'
        s = source.read_text()
        marker = 'static consoleCommand_t\tcommands[] = {'
        if marker not in s: raise RuntimeError('Client QA insertion point missing')
        s = s.replace(marker, (ROOT/'tests/combat_client_qa.inc').read_text() + '\n' + marker + '\n { "st_predictionqa", CG_STPredictionQA_f },')
        source.write_text(s, newline='\n')
    if args.prepare_only:
        return
    configure = ['cmake', '-S', str(SOURCE), '-B', str(WORK/'build'), '-G', 'Visual Studio 18 2026', '-A', 'x64']
    for flag in ['BuildMPEngine', 'BuildMPDed', 'BuildMPUI', 'BuildMPRdVanilla', 'BuildMPRend2', 'BuildSPEngine', 'BuildSPGame', 'BuildSPRdVanilla']:
        configure += ['-D'+flag+'=OFF']
    configure += ['-DBuildMPGame=ON', '-DBuildMPCGame=ON']
    client_build.run(configure)
    # Restored archive/overlay timestamps can be older than existing objects.
    client_build.run(['cmake','--build',str(WORK/'build'),'--config','Release','--clean-first','--parallel','6'])
    out = WORK/'build/Release'
    manifest = {'kind': 'qa' if args.qa else 'production', 'source_revision':client_build.REVISION,
                'source_archive_sha256':client_build.ARCHIVE_SHA256, 'files':{}}
    for name in ['jampgamex86_64.dll','cgamex86_64.dll']:
        manifest['files'][name] = hashlib.sha256((out/name).read_bytes()).hexdigest()
    (out/'combat-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Built combat module pair:',manifest['kind'])


if __name__ == '__main__':
    main()
