"""Apply the console keyboard to the verified Windows engine."""
from datetime import datetime
from importlib import import_module
import shutil
import sys

sys.dont_write_bytecode = True
base = import_module('Build-Name-Keyboard')
builder, ROOT = base.builder, base.ROOT
OUT = ROOT/'dist/console-keyboard-01'
RECEIPT = OUT/'source-receipt.json'
builder.OUT, builder.RECEIPT = OUT, RECEIPT
sha, read, write, tree = base.sha, base.read, base.write, base.tree
EXE = 'client/SaberTrials.x86_64.exe'


def replace(path, old, new):
    source = path.read_text(encoding='utf8')
    assert source.count(old)==1, (path, old)
    path.write_text(source.replace(old,new),encoding='utf8')


def prepare():
    prior = read(ROOT/'dist/name-keyboard-install.json')
    installed = {**prior['protected'], **prior['after']}
    assert all(sha(ROOT/name)==digest for name,digest in installed.items()), 'Installed client changed'
    assert sha(base.RECEIPT)==prior['source_sha256']
    assert tree(base.OUT/'engine')==read(base.RECEIPT)['sources']['engine']
    assert sha(base.OUT/'build-engine/Release/openjk.x86_64.exe')==installed[EXE]
    engine = OUT/'engine'
    shutil.copytree(base.OUT/'engine',engine,dirs_exist_ok=True)
    controls = ROOT/'development-source/controls'
    client = engine/'codemp/client'
    for name in ('cl_st_pad_menu.inc','cl_st_console_pad.inc','cl_st_console_pad.h'):
        shutil.copyfile(controls/name,client/name)
    shutil.copyfile(controls/'st_controller.inc',engine/'shared/sdl/st_controller.inc')
    replace(engine/'shared/sdl/sdl_input.cpp','#include "st_controller.inc"',
            '#include "client/cl_st_console_pad.h"\n#include "st_controller.inc"')
    replace(client/'cl_keys.cpp','#include "cl_st_pad_menu.inc"',
            '#include "cl_st_console_pad.h"\n#include "cl_st_pad_menu.inc"')
    replace(client/'cl_keys.cpp','\tkeyCatchers = catcher;',
            '\tif (!(catcher & KEYCATCH_CONSOLE)) Con_ClosePadKeyboard();\n\tkeyCatchers = catcher;')
    replace(client/'cl_console.cpp','void Con_DrawConsole( void ) {',
            '#include "cl_st_console_pad.inc"\n\nvoid Con_DrawConsole( void ) {')
    replace(client/'cl_console.cpp','\tif ( con.displayFrac ) {\n\t\tCon_DrawSolidConsole( con.displayFrac );',
            '\tif ( con.displayFrac ) {\n\t\tCon_DrawSolidConsole( con.displayFrac );\n\t\tCon_DrawPadKeyboard();')
    replace(client/'cl_console.cpp','con.finalFrac = con_height->value;',
            'con.finalFrac = Con_PadKeyboardActive() ? Com_Clamp(.30f,.55f,con_height->value) : con_height->value;')
    path = client/'cl_uiapi.cpp'
    replace(path,'extern void CL_GamepadPointerEvent(int,int);',
            'extern void CL_GamepadPointerEvent(int,int);\n#include "cl_st_console_pad.h"')
    replace(path,' if(Cmd_Argc()!=4)return;\n const int a=atoi(Cmd_Argv(2)),b=atoi(Cmd_Argv(3));',
            ' if(!Q_stricmp(Cmd_Argv(1),"assertconsole")){\n'
            '  const int state=(Key_GetCatcher()&KEYCATCH_CONSOLE)!=0;\n'
            '  if(state!=atoi(Cmd_Argv(2))||Con_PadKeyboardActive()!=!!atoi(Cmd_Argv(3)))Com_Printf("ST_PAD_CONSOLE_FAIL state\\n");\n'
            '  return;\n }\n'
            ' if(Cmd_Argc()!=4)return;\n const int a=atoi(Cmd_Argv(2)),b=atoi(Cmd_Argv(3));')
    write(RECEIPT,dict(installed=installed,sources={'engine':tree(engine)}))
    print('Prepared controller console keyboard.',flush=True)


def install(tag):
    helper = import_module('Install-Profile-Browser')
    helper.stopped()
    _, settings = helper.settings()
    installed = read(RECEIPT)['installed']
    assert all(sha(ROOT/name)==digest for name,digest in installed.items()), 'Installed client changed during testing'
    for role in ('engine','engine-qa'):
        assert read(OUT/f'build-{role}.json')==dict(source=sha(RECEIPT),sha256=sha(builder.binary(role)))
    evidence = OUT/tag/'result.json'
    assert read(evidence)==dict(source=sha(RECEIPT),engine=sha(builder.binary('engine-qa')))
    sources = {EXE:builder.binary('engine')}
    before, after = {EXE:installed[EXE]}, {EXE:sha(sources[EXE])}
    protected = {name:digest for name,digest in installed.items() if name!=EXE}
    backup = ROOT/'dist/backups'/f'console-keyboard-{datetime.now():%Y%m%d-%H%M%S}'
    payload = dict(before=before,after=after,protected=protected,backup=str(backup),
                   source_sha256=sha(RECEIPT),evidence=sha(evidence),preserved_settings=settings)
    import_module('Install-Handedness').install_transaction(ROOT,sources,before,after,protected,backup,
        ROOT/'dist/console-keyboard-install.json',payload)
    print('Installed controller console keyboard.')


if __name__=='__main__':
    operation = sys.argv[1]
    if operation=='prepare':prepare()
    elif operation=='install':install(sys.argv[2])
    else:builder.build(operation)
