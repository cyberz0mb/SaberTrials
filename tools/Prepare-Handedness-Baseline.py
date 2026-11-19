"""Prepare isolated handedness sources from the installed component baselines.

Default: prepare and verify only. --build engine|game|frontend|all explicitly
builds isolated candidates. --prepared PATH builds an existing verified result.
Never installs, launches a game/server, or modifies dist/handedness-work.
"""
from pathlib import Path
import argparse
import ctypes
import datetime
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
REVISION = '1a6a643427aa347553e9073dac5570b33337c4d9'
UPSTREAM = '50dee49ccc3dc2b7a3333f6fb1cf50da976b40a38ba01d0971afe47d4ee5b52d'
ARCHIVES = {
    'account': ('SaberTrials-account-client-20261023.zip', 'e1b2205a4b97c362d6f9a24bd7220fcc462f50d5f861aced86121ab89c9f157c'),
    'staff': ('SaberTrials-staff-20261022.zip', '133071c8d5f8320f015c747556cf460916943f1dd3cce42aaceeb4e09076b8fc'),
}
INSTALLED = {
    'client/SaberTrials.x86_64.exe': '75e8784b37838699eca54db2340b5f074ce02ac72f7fae2232799502437349a5',
    'jampgamex86_64.dll': '06f536a392ad9a14011d9705be28ae55290eb06318795b99c6704b4ef834cd15',
    'cgamex86_64.dll': 'a2b5dae5ed048347bcf6812ceaf6f4f2e884fe3a7bed42b6d99a794ec07c3c78',
    'uix86_64.dll': '4fbd13e417fbc4327e496cc12c146b8753719793e6b6f32ba03c965fab24ab09',
}
FLAGS = ('BuildMPEngine','BuildMPDed','BuildMPGame','BuildMPCGame','BuildMPUI','BuildMPRdVanilla','BuildMPRend2','BuildSPEngine','BuildSPGame','BuildSPRdVanilla')
TARGETS = {
    'engine': ('BuildMPEngine','BuildMPDed','BuildMPRdVanilla','BuildMPRend2'),
    'game': ('BuildMPGame',),
    'frontend': ('BuildMPCGame','BuildMPUI'),
}
ARTIFACTS = {
    'engine': ('openjk.x86_64.exe','openjkded.x86_64.exe','rd-vanilla_x86_64.dll','rd-rend2_x86_64.dll'),
    'game': ('jampgamex86_64.dll',),
    'frontend': ('cgamex86_64.dll','uix86_64.dll'),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_hash(path, expected):
    if sha(path) != expected:
        raise RuntimeError(f'Input hash mismatch: {path}')


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n', encoding='utf-8')


def tree(path):
    root = Path(path)
    return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def run(args):
    subprocess.run([str(a) for a in args], check=True)


def safe_output(path):
    path = Path(path).resolve()
    if path.parent != (ROOT/'dist').resolve() or not path.name.startswith('handedness-baseline-'):
        raise RuntimeError('Output must be a new dist/handedness-baseline-* directory')
    return path


def native_short_path(path):
    # Sodium's VS project uses deep relative source paths. Its compiler still
    # encounters MAX_PATH even when Python extracted the same files correctly.
    # Use the existing Windows short-name alias; no junction or drive is made.
    if sys.platform != 'win32':
        return path
    buffer = ctypes.create_unicode_buffer(32768)
    length = ctypes.windll.kernel32.GetShortPathNameW(str(path), buffer, len(buffer))
    if not length or length >= len(buffer):
        raise RuntimeError('Cannot obtain the isolated dependency short path')
    return Path(buffer.value)


def archive_inputs(kind, destination):
    filename, digest = ARCHIVES[kind]
    archive = ROOT/'dist'/filename
    require_hash(archive, digest)
    with zipfile.ZipFile(archive) as z:
        manifest = json.loads(z.read('account-client-manifest.json' if kind=='account' else 'SaberTrials/staff-release-manifest.json'))
        payload = manifest['files' if kind=='account' else 'payload']
        for name, expected in payload.items():
            if hashlib.sha256(z.read(name)).hexdigest() != expected:
                raise RuntimeError('Archived payload mismatch: '+name)
        destination.mkdir(parents=True)
        for entry in z.infolist():
            if not entry.filename.startswith('SaberTrials/') or entry.is_dir():
                continue
            relative = entry.filename[len('SaberTrials/'):]
            target = (destination/relative).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise RuntimeError('Archive traversal: '+entry.filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(entry))
    require_hash(destination/f'source/OpenJK-{REVISION}.zip', UPSTREAM)
    return manifest


def exact_replace(text, old, new, label):
    if text.count(old) != 1:
        raise RuntimeError('Reconstruction anchor changed: '+label)
    return text.replace(old, new)


def prepare(output):
    output = safe_output(output)
    if output.exists():
        raise RuntimeError('Refusing to overwrite an existing baseline; use --prepared to build it')
    for name, expected in INSTALLED.items():
        require_hash(ROOT/name, expected)
    feature_before = tree(ROOT/'development-source/handedness')
    output.mkdir(parents=True)
    feature = output/'inputs/handedness'
    shutil.copytree(ROOT/'development-source/handedness', feature, ignore=shutil.ignore_patterns('__pycache__'))
    if tree(feature) != feature_before or tree(ROOT/'development-source/handedness') != feature_before:
        raise RuntimeError('Handedness source changed while snapshotting')
    print('Frozen handedness source snapshot; concurrent overlay edits are now independent.', flush=True)
    account, staff, presentation = (output/'inputs'/n for n in ('account','staff','presentation'))
    archive_inputs('account', account)
    archive_inputs('staff', staff)
    aim_record = read(ROOT/'dist/staff-aim-install-manifest.json')['build']
    presentation_record = read(ROOT/'dist/presentation-install.json')['build']
    require_hash(ROOT/'tools/Build-Overhaul.py', aim_record['inputs']['tools/Build-Overhaul.py'])
    if aim_record['files']['jampgamex86_64.dll'] != INSTALLED['jampgamex86_64.dll'] or presentation_record['files'] != {n:INSTALLED[n] for n in ('uix86_64.dll','cgamex86_64.dll')}:
        raise RuntimeError('Installed-component manifest identity changed')

    # Reconstruct precisely the two gameplay-relevant aim changes, from the
    # verified account archive; never read pending gameplay source as a base.
    name = 'development-source/bot-roles/codemp/game/g_staff.c'
    text = (account/name).read_text()
    removed = [
        'int ST_StaffGenerationForClient(int slot,unsigned char generation[16]){return engine?engine->GenerationForClient(slot,generation):0;}\n',
        ' if(ST_EventActive()&&ST_EventCanJoin(ent->s.number,ent->client->sess.sessionTeam)&&ent->client->sess.sessionTeam!=TEAM_SPECTATOR)return qtrue;\n',
        ' if(action->command==ST_CMD_TOURNAMENT)return ST_EventStaff(action,result);\n',
    ]
    for old in removed:
        text = exact_replace(text, old, '', name)
    (staff/name).write_text(text, newline='\n')
    require_hash(staff/name, aim_record['inputs'][name])
    api = 'development-source/staff/codemp/staff/st_staff_game_api.h'
    (staff/api).write_text(exact_replace((account/api).read_text(), ', ST_CMD_TOURNAMENT', '', api), newline='\n')
    require_hash(staff/api, aim_record['inputs'][api])
    for name, expected in aim_record['inputs'].items():
        if name.startswith('development-source/bot-roles/codemp/game/') or name == api:
            require_hash(staff/name, expected)

    # Snapshot only the recorded presentation inputs; exclude pending/new
    # unrecorded files. Helper client includes are archival, not current.
    for name, expected in presentation_record['sources'].items():
        require_hash(ROOT/name, expected)
        target = presentation/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/name, target)
    for name in ('tools/Build-Overhaul.py','tools/Build-Presentation.py'):
        target = presentation/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/name, target)
    for p in (account/'development-source/client-overhaul').glob('*.inc'):
        shutil.copy2(p, presentation/'development-source/client-overhaul'/p.name)
    work = presentation/'work'
    work.mkdir()
    shutil.copy2(account/f'source/OpenJK-{REVISION}.zip', work/'openjk.zip')
    helper = module('baseline_presentation', presentation/'tools/Build-Overhaul.py')
    helper.WORK, helper.SOURCE = work, work/('OpenJK-'+REVISION)
    front_source = helper.prepare(False)
    for overlay in ('bot-roles','client-game'):
        for sub in ('game','cgame'):
            src = presentation/'development-source'/overlay/'codemp'/sub
            if src.exists():
                shutil.copytree(src, front_source/'codemp'/sub, dirs_exist_ok=True)

    engine_source = module('baseline_account', account/'tools/Build-Staff.py').prepare(False)
    game_source = module('baseline_aim', staff/'tools/Build-Staff.py').prepare(False)
    # Cgame/UI directly compile shared game files. Record every difference and
    # only accept the already identified staff movement patch difference.
    shared = set()
    for sub in ('cgame','ui'):
        shared.update(re.findall(r'\$\{MPDir\}/game/([^"\s]+)', (front_source/f'codemp/{sub}/CMakeLists.txt').read_text()))
        for path in (front_source/'codemp'/sub).rglob('*'):
            if path.suffix in ('.c','.cpp','.h','.inc'):
                shared.update(re.findall(r'#include\s+"(?:\.\./)?game/([^"\s]+)"',path.read_text()))
    differences = {name:{'game':sha(game_source/'codemp/game'/name),'frontend':sha(front_source/'codemp/game'/name)}
                   for name in sorted(shared) if (game_source/'codemp/game'/name).exists() and sha(game_source/'codemp/game'/name) != sha(front_source/'codemp/game'/name)}
    if set(differences) != {'bg_pmove.c'}:
        raise RuntimeError('Unexpected shared gameplay/frontend differences: '+repr(differences))
    frontend_only = {name:sha(front_source/'codemp/game'/name) for name in sorted(shared) if not (game_source/'codemp/game'/name).exists()}
    if frontend_only != {'st_event_ui.h':presentation_record['sources']['development-source/bot-roles/codemp/game/st_event_ui.h']}:
        raise RuntimeError('Unexpected frontend-only game dependencies: '+repr(frontend_only))

    seed = output/'seed'
    shutil.copytree(engine_source, seed)
    # Replace directories entirely: overlay-copy would leave archived pending
    # g_event files behind, even if currently absent from the game CMake list.
    for sub, source in (('game',game_source),('cgame',front_source),('ui',front_source)):
        target = seed/'codemp'/sub
        if not target.resolve().is_relative_to(output.resolve()):
            raise RuntimeError('Invalid isolated replacement target')
        shutil.rmtree(target)
        shutil.copytree(source/'codemp'/sub, target)
    baseline = tree(seed)
    module('baseline_feature', feature/'prepare.py').apply(seed)
    patched = tree(seed)
    changes = {n:{'before':baseline.get(n),'after':patched.get(n)} for n in sorted(set(baseline)|set(patched)) if baseline.get(n)!=patched.get(n)}
    component_sources = {}
    for kind in TARGETS:
        dst = output/kind
        shutil.copytree(seed, dst)
        if kind == 'frontend':
            # Feature has no movement-rule changes. Refuse to erase any future
            # intentional overlay change when restoring accepted prediction.
            if patched['codemp/game/bg_pmove.c'] != baseline['codemp/game/bg_pmove.c']:
                raise RuntimeError('Feature now modifies bg_pmove; component merge requires review')
            shutil.copy2(front_source/'codemp/game/bg_pmove.c', dst/'codemp/game/bg_pmove.c')
            for name in frontend_only:
                shutil.copy2(front_source/'codemp/game'/name,dst/'codemp/game'/name)
        if kind == 'game':
            shutil.copy2(staff/api, dst/'codemp/staff/st_staff_game_api.h')
        if kind != 'engine':
            if patched['CMakeLists.txt'] != baseline['CMakeLists.txt']:
                raise RuntimeError('Feature modifies core build registration; component merge requires review')
            # Neither game nor frontend links the native account/staff cores.
            # Keep their native CMake root without engine-only registrations.
            shutil.copy2(front_source/'CMakeLists.txt',dst/'CMakeLists.txt')
        # Guard against unintended bridge/event code entering the production
        # engine or gameplay sources. The accepted engine already has a client
        # tournament command; retain it without adding the newer server bridge.
        if (dst/'codemp/server/sv_account.cpp').exists() or (dst/'codemp/game/g_event.c').exists():
            raise RuntimeError('Pending bridge/event source leaked into component '+kind)
        component_sources[kind] = tree(dst)
    if tree(feature) != feature_before:
        raise RuntimeError('Frozen feature snapshot changed during preparation')
    for name, expected in INSTALLED.items():
        require_hash(ROOT/name, expected)
    record = {
        'kind':'isolated accepted-baseline candidate; not installed',
        'root':str(output),'revision':REVISION,'upstream_sha256':UPSTREAM,
        'archives':ARCHIVES,'installed':INSTALLED,
        'preparation_script_sha256':sha(__file__),
        'aim_manifest_sha256':sha(ROOT/'dist/staff-aim-install-manifest.json'),
        'presentation_manifest_sha256':sha(ROOT/'dist/presentation-install.json'),
        'presentation_sources':presentation_record['sources'],
        'input_trees':{n:tree(output/'inputs'/n/'development-source') for n in ('account','staff','presentation')},
        'helper_scripts':{f'{n}/tools/{p.name}':sha(p) for n in ('account','staff','presentation') for p in (output/'inputs'/n/'tools').glob('Build-*.py')},
        'reconstructions':{'g_staff_removed_lines':removed,'game_api_removed':', ST_CMD_TOURNAMENT',
                           'g_staff_sha256':sha(staff/'development-source/bot-roles/codemp/game/g_staff.c'),'game_api_sha256':sha(staff/api)},
        'shared_component_differences':differences,'frontend_only_headers':frontend_only,'baseline_sources':baseline,
        'current_feature_still_matches_snapshot':feature_before==tree(ROOT/'development-source/handedness'),
        'feature_inputs':feature_before,'feature_changes':changes,'components':component_sources,
        'builds':{},
    }
    write(output/'provenance.json', record)
    print('Prepared verified component sources:', output, flush=True)
    return output


def build(output, kinds):
    output = safe_output(output)
    record = read(output/'provenance.json')
    if Path(record['root']).resolve() != output:
        raise RuntimeError('Prepared trees cannot be relocated: engine core registrations use absolute frozen paths')
    for name, expected in record['installed'].items():
        require_hash(ROOT/name, expected)
    for kind in kinds:
        if tree(output/kind) != record['components'][kind]:
            raise RuntimeError('Prepared source changed: '+kind)
    for name, expected in record['input_trees'].items():
        if tree(output/'inputs'/name/'development-source') != expected:
            raise RuntimeError('Frozen dependency/core sources changed: '+name)
    for relative, expected in record['helper_scripts'].items():
        require_hash(output/'inputs'/relative, expected)
    account = output/'inputs/account'
    if 'engine' in kinds:
        dependencies = module('baseline_dependencies', account/'tools/Build-Staff.py')
        # Keep native dependency object paths short and wholly isolated.
        dependencies.DEPS = output/'deps'
        dependencies.DEPS.mkdir(exist_ok=True)
        dependencies.DEPS = native_short_path(dependencies.DEPS)
        for name in ('sodium.tar.gz','sqlite.zip'):
            shutil.copy2(account/'dist/staff-deps'/name,dependencies.DEPS/name)
        def dependency_run(args):
            # MSBuild expands its working directory to the long path again.
            # Normalize only ClCompile paths in the extracted project so CL
            # never opens a long cwd plus an uncollapsed ../../../../ path.
            project = Path(args[1])
            original = project.read_text()
            substitutions = {}
            def source_path(match):
                relative = match.group(1)
                resolved = (project.parent/relative).resolve()
                # Preserve basenames: MSBuild derives .obj names from them,
                # and short aliases from distinct folders can collide.
                absolute = native_short_path(resolved.parent)/resolved.name
                substitutions[relative] = str(absolute)
                return '<ClCompile Include="'+str(absolute)+'"'
            patched = re.sub(r'<ClCompile Include="([^"]+)"', source_path, original)
            before = sha(project)
            project.write_text(patched)
            record['dependency_project_adjustment'] = {
                'purpose':'Normalize native compiler source paths only; source bytes unchanged',
                'before_sha256':before,'after_sha256':sha(project),'source_paths':substitutions,
            }
            write(output/'provenance.json', record)
            run(args)
        dependencies.run = dependency_run
        dependencies.dependencies()
        record['dependency_sources'] = {
            p.relative_to(output/'deps').as_posix():sha(p)
            for p in sorted((output/'deps').rglob('*'))
            if p.is_file() and p.suffix.lower() in ('.c','.h','.props','.vcxproj','.lib')
        }
    for kind in kinds:
        source, destination = output/kind, output/('build-'+kind)
        run(['cmake','-S',source,'-B',destination,'-G','Visual Studio 18 2026','-A','x64',
             *[f'-D{flag}={"ON" if flag in TARGETS[kind] else "OFF"}' for flag in FLAGS],'-DST_STAFF_QA=OFF',
             *(['-DST_DEPS='+str(output/'deps')] if kind=='engine' else [])])
        run(['cmake','--build',destination,'--config','Release','--parallel','6'])
        if tree(source) != record['components'][kind]:
            raise RuntimeError('Source changed during build: '+kind)
        for name, expected in record['input_trees'].items():
            if tree(output/'inputs'/name/'development-source') != expected:
                raise RuntimeError('Frozen dependency/core sources changed during build: '+name)
        record['builds'][kind] = {name:sha(destination/'Release'/name) for name in ARTIFACTS[kind]}
        record.setdefault('auxiliary_build_outputs', {})[kind] = {
            p.name:sha(p) for p in (destination/'Release').iterdir()
            if p.suffix.lower() in ('.dll','.exe') and p.name not in ARTIFACTS[kind]
        }
        record.setdefault('build_tool_sha256', {})[kind] = sha(__file__)
        write(output/'provenance.json', record)
    for name, expected in record['installed'].items():
        require_hash(ROOT/name, expected)
    print('Isolated component builds complete; nothing installed:', output, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--prepared', type=Path)
    parser.add_argument('--build', choices=(*TARGETS,'all'))
    args = parser.parse_args()
    if args.output and args.prepared:
        parser.error('--output and --prepared are mutually exclusive')
    if args.prepared:
        if not args.build:
            parser.error('--prepared requires --build')
        output = args.prepared
    else:
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')
        output = prepare(args.output or ROOT/'dist'/('handedness-baseline-'+stamp))
    if args.build:
        build(output, list(TARGETS) if args.build=='all' else [args.build])


if __name__ == '__main__':
    main()
