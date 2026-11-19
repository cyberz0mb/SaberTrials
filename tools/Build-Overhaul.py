"""Rebuild the pinned Saber Trials client/UI without changing game/cgame DLLs."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
REVISION = '1a6a643427aa347553e9073dac5570b33337c4d9'
ARCHIVE_SHA256 = '50dee49ccc3dc2b7a3333f6fb1cf50da976b40a38ba01d0971afe47d4ee5b52d'
WORK = Path(tempfile.gettempdir()) / 'SaberTrials-overhaul-20261003'
SOURCE = WORK / ('OpenJK-' + REVISION)


def run(args):
    env = {key.upper(): value for key, value in os.environ.items()}
    env['Path'] = env.pop('PATH')
    subprocess.run(args, check=True, env=env)


def prepare(qa=False):
    WORK.mkdir(parents=True, exist_ok=True)
    archive = WORK / 'openjk.zip'
    if not archive.exists():
        urllib.request.urlretrieve('https://codeload.github.com/JACoders/OpenJK/zip/' + REVISION, archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise RuntimeError('Pinned source archive checksum mismatch')
    # This dedicated extraction is disposable; restoring files also removes QA hooks.
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            target = (WORK / member.filename).resolve()
            if not target.is_relative_to(SOURCE.resolve()):
                raise RuntimeError('Archive path escapes the pinned checkout')
        z.extractall(WORK)
    overlay = ROOT / 'development-source/bot-roles'
    for include in (overlay / 'codemp/ui').glob('*.inc'):
        shutil.copy2(include, SOURCE / 'codemp/ui' / include.name)
    for include in (ROOT / "development-source/client-overhaul").glob("*.inc"):
        shutil.copy2(include, SOURCE / "codemp/client" / include.name)
    patches = [overlay / 'patches' / name for name in (
        'ui-built-in-character-roster.patch', 'ui-menu-controls.patch', 'ui-input-sliders.patch')]
    patches += sorted((ROOT / 'development-source/client-overhaul/patches').glob('*.patch'))
    for patch in patches:
        run(['git', 'apply', '--directory=' + str(SOURCE), '--unsafe-paths', str(patch)])
    if qa:
        atoms = SOURCE / 'codemp/ui/ui_atoms.c'
        s = atoms.read_text()
        hook = (ROOT / 'tests/overhaul_ui_qa.inc').read_text()
        s = s.replace('typedef struct consoleCommand_s {', hook + '\n\ntypedef struct consoleCommand_s {')
        s = s.replace('static consoleCommand_t\tcommands[] = {',
                      'static consoleCommand_t\tcommands[] = {\n    { "st_clientqa", ST_ClientQA_f },')
        atoms.write_text(s, newline='\n')
        client = SOURCE / 'codemp/client/cl_main.cpp'
        s = client.read_text()
        hook = (ROOT / 'tests/overhaul_engine_qa.inc').read_text()
        s = s.replace('void CL_Init( void )', hook + '\n\nvoid CL_Init( void )')
        s = s.replace('Cmd_AddCommand ("record", CL_Record_f, "Record a demo" );',
                      'Cmd_AddCommand ("record", CL_Record_f, "Record a demo" );\n'
                      '    Cmd_AddCommand("st_engineqa", ST_EngineQA_f, "Test-only events");')
        if 'static void ST_EngineQA_f' not in s:
            raise RuntimeError('Engine QA insertion point changed')
        client.write_text(s, newline='\n')
    return SOURCE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--qa', action='store_true', help='Test-only UI event injection; never install this build')
    args = parser.parse_args()
    source = prepare(args.qa)
    if args.prepare_only:
        print('Prepared', source)
        return
    configure = ['cmake', '-S', str(source), '-B', str(WORK / 'build'),
                 '-G', 'Visual Studio 18 2026', '-A', 'x64']
    for name in ('BuildMPDed', 'BuildMPGame', 'BuildMPCGame', 'BuildMPRdVanilla',
                 'BuildMPRend2', 'BuildSPEngine', 'BuildSPGame', 'BuildSPRdVanilla'):
        configure.append('-D' + name + '=OFF')
    configure += ['-DBuildMPEngine=ON', '-DBuildMPUI=ON']
    run(configure)
    run(['cmake', '--build', str(WORK / 'build'), '--config', 'Release', '--parallel', '6'])
    output = WORK / 'build/Release'
    manifest = {'kind': 'qa' if args.qa else 'production', 'source_revision': REVISION,
                'source_archive_sha256': ARCHIVE_SHA256, 'files': {}}
    for name in ['openjk.x86_64.exe', 'uix86_64.dll']:
        manifest['files'][name] = hashlib.sha256((output / name).read_bytes()).hexdigest()
    (output / 'build-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Built', 'QA (do not install)' if args.qa else 'production', 'client/UI in', WORK / 'build/Release')


if __name__ == '__main__':
    main()
