"""Pinned staff native build. No downloads or game installation are implicit."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import tarfile
import zipfile
import importlib.util
import shutil

ROOT = Path(__file__).resolve().parents[1]
DEPS = ROOT/'dist/staff-deps'

def input_hashes():
    paths=[]
    for folder in ('bot-roles','client-game','client-overhaul','staff','accounts'):
        paths.extend(p for p in (ROOT/'development-source'/folder).rglob('*') if p.is_file() and p.suffix not in ('.pyc','.tmp','.bak'))
    paths.extend(ROOT/name for name in ('tools/Build-Staff.py','tools/Build-Overhaul.py'))
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}

def verify_dependencies(cache):
    lock = json.loads((ROOT/'development-source/staff/dependencies/lock.json').read_text())
    for name in ('sodium', 'sqlite'):
        d = lock[name]
        archive = cache/d['archive']
        if not archive.is_file() or hashlib.sha256(archive.read_bytes()).hexdigest() != d['sha256']:
            raise RuntimeError(name+' checksum mismatch or missing pinned archive')
    vendor=ROOT/'development-source/accounts/codemp/accounts/vendor'
    for name,entry in json.loads((vendor/'lock.json').read_text())['files'].items():
        if hashlib.sha256((vendor/name).read_bytes()).hexdigest()!=entry['sha256']:
            raise RuntimeError('Account dependency checksum mismatch: '+name)
    return lock

def run(args):
    subprocess.run([str(a) for a in args], check=True)

def dependencies():
    lock = verify_dependencies(DEPS)
    # Always restore verified source inputs; a previously edited extraction is not trusted.
    with tarfile.open(DEPS/'sodium.tar.gz') as a:
        a.extractall(DEPS, filter='data')
    with zipfile.ZipFile(DEPS/'sqlite.zip') as a:
        for name in a.namelist():
            if not (DEPS/name).resolve().is_relative_to(DEPS.resolve()):
                raise RuntimeError('Unsafe SQLite archive path')
        a.extractall(DEPS)
    sodium = DEPS/lock['sodium']['directory']
    # Match OpenJK's /MD runtime while keeping sodium statically linked; crypto source is untouched.
    props = sodium/'builds/msvc/properties/ReleaseLIB.props'
    props.write_text(props.read_text().replace('<RuntimeLibrary>MultiThreaded</RuntimeLibrary>', '<RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary>'))
    msbuild = Path('C:/Program Files/Microsoft Visual Studio/18/Community/MSBuild/Current/Bin/MSBuild.exe')
    run([msbuild, sodium/'builds/msvc/vs2026/libsodium/libsodium.vcxproj', '/p:Configuration=ReleaseLIB', '/p:Platform=x64', '/m:6', '/verbosity:minimal', '/nologo'])
    return lock

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tests-only', action='store_true')
    p.add_argument('--prepare-only', action='store_true')
    p.add_argument('--qa', action='store_true')
    args = p.parse_args()
    if args.prepare_only:
        print(prepare(args.qa)); return
    inputs=input_hashes()
    lock = dependencies()
    # Native adapter tests must read the same freshly patched engine source
    # as the production build, including bot allocation and disconnect hooks.
    source=prepare(args.qa) if not args.tests_only else None
    build = ROOT/'dist/staff-build-tests'
    run(['cmake', '-S', ROOT/'tests/staff', '-B', build, '-G', 'Visual Studio 18 2026', '-A', 'x64'])
    run(['cmake', '--build', build, '--config', 'Release', '--parallel', '6'])
    run(['ctest', '--test-dir', build, '-C', 'Release', '--output-on-failure'])
    (build/'inputs.json').write_text(json.dumps(lock, indent=2)+'\n')
    if not args.tests_only:
        build=ROOT/('dist/staff-build-qa' if args.qa else 'dist/staff-build')
        options=['cmake','-S',source,'-B',build,'-G','Visual Studio 18 2026','-A','x64']
        for flag in ('BuildMPDed','BuildMPGame','BuildMPCGame','BuildMPEngine'):
            options+=['-D'+flag+'=ON']
        for flag in ('BuildMPUI','BuildMPRdVanilla','BuildMPRend2','BuildSPEngine','BuildSPGame','BuildSPRdVanilla'):
            options+=['-D'+flag+'=OFF']
        options+=['-DST_STAFF_QA='+('ON' if args.qa else 'OFF')]
        run(options)
        run(['cmake','--build',build,'--config','Release','--parallel','6'])
        if inputs!=input_hashes():raise RuntimeError('Source inputs changed during the build; rebuild before release')
        manifest={'kind':'qa' if args.qa else 'production','files':{},'inputs':inputs,
                  'source_revision':'1a6a643427aa347553e9073dac5570b33337c4d9',
                  'source_archive_sha256':'50dee49ccc3dc2b7a3333f6fb1cf50da976b40a38ba01d0971afe47d4ee5b52d'}
        for name in ('openjk.x86_64.exe','openjkded.x86_64.exe','jampgamex86_64.dll','cgamex86_64.dll'):
            manifest['files'][name]=hashlib.sha256((build/'Release'/name).read_bytes()).hexdigest()
        (build/'Release/staff-build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

def prepare(qa=False, patches=True, work=None):
    spec=importlib.util.spec_from_file_location('overhaul',ROOT/'tools/Build-Overhaul.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    work=Path(work) if work is not None else ROOT/'dist/staff-work'
    work.mkdir(parents=True,exist_ok=True)
    if not (work/'openjk.zip').exists():
        cache=ROOT/('source/OpenJK-'+helper.REVISION+'.zip')
        if not cache.exists():cache=Path.home()/'AppData/Local/Temp/SaberTrials-photo-20261012/openjk.zip'
        shutil.copy2(cache,work/'openjk.zip')
    helper.WORK=work;helper.SOURCE=work/('OpenJK-'+helper.REVISION)
    source=helper.prepare(False)
    for overlay in ('bot-roles','client-game','staff','accounts'):
        folder=ROOT/'development-source'/overlay/'codemp'
        if folder.exists():shutil.copytree(folder,source/'codemp',dirs_exist_ok=True)
    for patch in sorted((ROOT/'development-source/staff/patches').glob('*.patch')) if patches else []:
        helper.run(['git','apply','--directory='+str(source),'--unsafe-paths',str(patch)])
    client=source/'codemp/client/cl_main.cpp'
    text=client.read_text()
    marker='\trecursive = qtrue;\n\n\tif (G2VertSpaceClient)'
    if text.count(marker)!=1:raise RuntimeError('Account shutdown hook changed')
    client.write_text('#include "cl_account.h"\n'+text.replace(marker,'\trecursive = qtrue;\n\tCL_AccountShutdown();\n\n\tif (G2VertSpaceClient)',1))
    account_hooks(source)
    if qa:
        file=source/'codemp/game/g_svcmds.c';s=file.read_text()
        marker='qboolean\tConsoleCommand( void ) {'
        if marker not in s:raise RuntimeError('Staff QA console hook changed')
        file.write_text(s.replace(marker,(ROOT/'tests/staff/game_qa.inc').read_text()+'\n'+marker+'\n if(ST_StaffQA()) return qtrue;',1))
        file=source/'codemp/game/g_mover.c'
        file.write_text(file.read_text()+'\n'+(ROOT/'tests/staff/mover_qa.inc').read_text())
        file=source/'codemp/cgame/cg_draw.c';s=file.read_text();marker='static void CG_Draw2D( void ) {'
        if marker not in s:raise RuntimeError('Staff QA drawing hook changed')
        s=s.replace(marker,(ROOT/'tests/staff/cgame_qa.inc').read_text()+'\n'+marker,1)
        file.write_text(s.replace('if (ST_PhotoActive()) { ST_PhotoDraw(); return; }','ST_CGameQA();\n\tif (ST_PhotoActive()) { ST_PhotoDraw(); return; }',1))
    # The source core is shared with tests; link only engine/dedicated targets.
    cmake=source/'CMakeLists.txt'
    cmake.write_text(cmake.read_text()+'''\nget_filename_component(ST_MOD_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
add_subdirectory("${ST_MOD_ROOT}/development-source/staff" staff-core)
add_subdirectory("${ST_MOD_ROOT}/development-source/accounts" account-core)
foreach(st_target ${MPEngine} ${MPDed})
  if(TARGET ${st_target})
    target_sources(${st_target} PRIVATE "${MPDir}/server/sv_staff.cpp" "${MPDir}/server/sv_account.cpp")
    target_include_directories(${st_target} PRIVATE "${MPDir}/game")
    target_link_libraries(${st_target} st_staff_core st_account_core)
    if(ST_STAFF_QA)
      target_compile_definitions(${st_target} PRIVATE ST_STAFF_QA)
    endif()
  endif()
endforeach()
if(TARGET ${MPEngine})
  target_sources(${MPEngine} PRIVATE "${MPDir}/client/cl_staff.cpp" "${MPDir}/client/cl_account.cpp")
  target_link_libraries(${MPEngine} st_account_core)
endif()
if(TARGET ${MPGame} AND ST_STAFF_QA)
  target_compile_definitions(${MPGame} PRIVATE ST_STAFF_QA)
endif()
''')
    return source

def account_hooks(source):
    """Connect private native account workers to the pinned engine lifecycle."""
    def edit(relative, old, new):
        path=source/relative
        text=path.read_text()
        if text.count(old)!=1:raise RuntimeError('Account engine hook changed: '+relative)
        path.write_text(text.replace(old,new,1))
    for name in ('cl_main.cpp','cl_parse.cpp','cl_cgame.cpp'):
        path=source/'codemp/client'/name
        text=path.read_text()
        if '#include "cl_account.h"' not in text:text='#include "cl_account.h"\n'+text
        if text.count('CL_StaffReset();')!=1:raise RuntimeError('Account reset hook changed: '+name)
        path.write_text(text.replace('CL_StaffReset();','CL_StaffReset(); CL_AccountResetConnection();',1))
    edit('codemp/client/cl_cgame.cpp',
         '\tCom_DPrintf( "serverCommand: %i : %s\\n", serverCommandNumber, s );',
         '\tCmd_TokenizeString(s);\n\tif (CL_AccountServerCommand()) return qfalse;\n\tCom_DPrintf( "serverCommand: %i : %s\\n", serverCommandNumber, s );')
    for name in ('sv_client.cpp','sv_ccmds.cpp','sv_gameapi.cpp'):
        path=source/'codemp/server'/name
        path.write_text('#include "sv_account.h"\n'+path.read_text())
    edit('codemp/server/sv_client.cpp',
         'qboolean bProcessed = qfalse;\n\n\tCmd_TokenizeString( s );',
         'qboolean bProcessed = qfalse;\n\n\tCmd_TokenizeString( s );\n\tif (SV_AccountCommand((int)(cl-svs.clients))) return;')
    edit('codemp/server/sv_ccmds.cpp',
         'if (com_dedicated->integer) Cmd_AddCommand("staff", SV_StaffConsole_f, "Permanent staff administration");',
         'Cmd_AddCommand("accountserver", SV_AccountConsole_f, "Configure approved account service access");\n\tif (com_dedicated->integer) Cmd_AddCommand("staff", SV_StaffConsole_f, "Permanent staff administration");')
    edit('codemp/server/sv_gameapi.cpp','static const STGameAPI* staffAPI;', '''static const STGameAPI* staffAPI;
static const STEventAccountAPI* accountAPI;
bool GVM_AccountAvailable() {
 return gvm && !gvm->isLegacy && accountAPI && accountAPI->version==1 && accountAPI->size==sizeof(STEventAccountAPI) && accountAPI->SetAccount && accountAPI->ClearAccount && accountAPI->GetSnapshot;
}
int GVM_AccountSet(int slot,const unsigned char generation[16],const STEProfile* profile) {
 if(!GVM_AccountAvailable())return 0;
 VMSwap v(gvm);return accountAPI->SetAccount(slot,generation,profile);
}
void GVM_AccountClear(int slot) {
 if(GVM_AccountAvailable()){VMSwap v(gvm);accountAPI->ClearAccount(slot);}
}''')
    for marker in ('void GVM_InitGame( int levelTime, int randomSeed, int restart ) {',
                   'void GVM_ShutdownGame( int restart ) {'):
        edit('codemp/server/sv_gameapi.cpp',marker,marker+'\n    SV_AccountReset();')
    edit('codemp/server/sv_gameapi.cpp','void GVM_RunFrame( int levelTime ) {',
         'void GVM_RunFrame( int levelTime ) {\n    SV_AccountFrame();')
    edit('codemp/server/sv_gameapi.cpp','if(!ST_ValidGameAPI(staffAPI))staffAPI=NULL;', '''if(!ST_ValidGameAPI(staffAPI))staffAPI=NULL;
        typedef const STEventAccountAPI* (*AccountExport)();
        AccountExport accountExport=(AccountExport)Sys_LoadFunction(gvm->dllHandle,"GetSaberTrialsEventAccountAPI");
        accountAPI=accountExport?accountExport():NULL;''')
    edit('codemp/server/sv_gameapi.cpp','staffAPI=NULL;\n\t// fall back', 'staffAPI=NULL;accountAPI=NULL;\n\t// fall back')
    edit('codemp/server/sv_gameapi.cpp','staffAPI=NULL;\n\tVM_Free', 'staffAPI=NULL;accountAPI=NULL;\n\tVM_Free')

if __name__ == '__main__':
    main()
