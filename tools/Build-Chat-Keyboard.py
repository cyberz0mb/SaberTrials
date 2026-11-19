"""Build chat keyboard and binding options on the installed console keyboard."""
from datetime import datetime
from importlib import import_module
import shutil
import sys

sys.dont_write_bytecode=True
base=import_module('Build-Console-Keyboard')
builder,ROOT=base.builder,base.ROOT
OUT=ROOT/'dist/chat-keyboard-01'
RECEIPT=OUT/'source-receipt.json'
builder.OUT,builder.RECEIPT=OUT,RECEIPT
sha,read,write,tree,replace=base.sha,base.read,base.write,base.tree,base.replace


def prepare(refresh=False):
    prior=read(ROOT/'dist/console-keyboard-install.json')
    installed={**prior['protected'],**prior['after']}
    assert all(sha(ROOT/name)==digest for name,digest in installed.items()), 'Installed client changed'
    for role,origin in (('engine',base),('frontend',base.base)):
        assert tree(origin.OUT/role)==read(origin.RECEIPT)['sources'][role]
        if not refresh:shutil.copytree(origin.OUT/role,OUT/role,dirs_exist_ok=True)
    controls=ROOT/'development-source/controls'
    engine=OUT/'engine'
    client=engine/'codemp/client'
    ui=OUT/'frontend/codemp/ui'
    for name in ('cl_st_pad_menu.inc','cl_st_console_pad.inc','cl_st_console_pad.h'):
        shutil.copyfile(controls/name,client/name)
    if refresh:
        for name in ('cl_uiapi.cpp','cl_console.cpp','cl_keys.cpp','cl_input.cpp'):
            shutil.copyfile(base.OUT/'engine/codemp/client'/name,client/name)
        shutil.copyfile(base.OUT/'engine/shared/sdl/sdl_input.cpp',engine/'shared/sdl/sdl_input.cpp')
        shutil.copyfile(base.base.OUT/'frontend/codemp/ui/ui_st_profile_actions.inc',ui/'ui_st_profile_actions.inc')
    for name in ('st_controller.inc','st_keyboard_detection.inc'):
        shutil.copyfile(controls/name,engine/'shared/sdl'/name)
    for folder in (engine/'codemp/ui',ui):
        shutil.copyfile(controls/'st_controls_catalog.h',folder/'st_controls_catalog.h')
    shutil.copyfile(controls/'ui_st_controls_draw.inc',ui/'ui_st_controls_draw.inc')
    replace(ui/'ui_st_profile_actions.inc','if(id==102||(id==101&&trap->Cvar_VariableValue("st_uiPadClick"))){SPN_Open();return;}',
            'const int keyboard=trap->Cvar_VariableValue("st_virtualKeyboard");\n'
            ' if(id==102||(id==101&&(keyboard==1||(keyboard==0&&trap->Cvar_VariableValue("st_uiPadClick")&&\n'
            '    !trap->Cvar_VariableValue("st_physicalKeyboard"))))){SPN_Open();return;}')
    sdl=engine/'shared/sdl/sdl_input.cpp'
    replace(sdl,'#include <cmath>','#include <cmath>\n#include <vector>')
    replace(sdl,'#include "st_controller.inc"','#include "st_keyboard_detection.inc"\n#include "st_controller.inc"')
    replace(sdl,'\tIN_JoyMove( );','\tST_UpdatePhysicalKeyboard();\n\tIN_JoyMove( );')
    replace(sdl,'if( !cls.glconfig.isFullscreen && ( Key_GetCatcher( ) & KEYCATCH_CONSOLE ) )',
            'if( !cls.glconfig.isFullscreen && ( Key_GetCatcher( ) & KEYCATCH_CONSOLE ) && !Con_PadKeyboardActive() )')
    keys=client/'cl_keys.cpp'
    replace(keys,'#include "cl_uiapi.h"','#include "cl_uiapi.h"\n#include "cl_st_console_pad.h"')
    replace(keys,'#include "cl_st_console_pad.h"\n#include "cl_st_pad_menu.inc"','#include "cl_st_pad_menu.inc"')
    replace(keys,'\tif (!(catcher & KEYCATCH_CONSOLE)) Con_ClosePadKeyboard();','\tCon_UpdatePadKeyboard(catcher);')
    replace(keys,'\tif( down )\n\t\tCL_KeyDownEvent( key, time );',
            '\tif(key==A_MOUSE1&&Con_PadKeyboardActive()){if(down)Con_PadKeyboardMouseClick();return;}\n'
            '\tif( down )\n\t\tCL_KeyDownEvent( key, time );')
    replace(client/'cl_input.cpp','void CL_MouseEvent( int dx, int dy, int time ) {',
            '#include "cl_st_console_pad.h"\n\nvoid CL_MouseEvent( int dx, int dy, int time ) {\n'
            '\tif(Con_PadKeyboardActive()){Con_PadKeyboardMove(dx,dy);return;}')
    console=client/'cl_console.cpp'
    replace(console,'#include "client.h"','#include "client.h"\n#include "cl_st_console_pad.h"')
    replace(console,'Key_SetCatcher( Key_GetCatcher( ) ^ KEYCATCH_CONSOLE );',
            'Key_SetCatcher( Key_GetCatcher( ) ^ KEYCATCH_CONSOLE );\n'
            '\tif((Key_GetCatcher()&KEYCATCH_CONSOLE)&&Con_AutoKeyboard(false))Con_OpenPadKeyboard();')
    source=console.read_text(encoding='utf8')
    line='Key_SetCatcher( Key_GetCatcher( ) ^ KEYCATCH_MESSAGE );'
    assert source.count(line)==4
    source=source.replace(line,line+'\n\tif((Key_GetCatcher()&KEYCATCH_MESSAGE)&&Con_AutoKeyboard(false))Con_SetPadKeyboard(KEYCATCH_MESSAGE);')
    console.write_text(source,encoding='utf8')
    replace(console,'if ( Key_GetCatcher( ) & KEYCATCH_MESSAGE )\n\t{',
            'if ( (Key_GetCatcher() & KEYCATCH_MESSAGE) && !Con_PadKeyboardActive() )\n\t{')
    replace(console,'\n\t\tCon_DrawPadKeyboard();','')
    replace(console,'\t\t\tCon_DrawNotify ();\n\t\t}\n\t}\n}',
            '\t\t\tCon_DrawNotify ();\n\t\t}\n\t}\n\tCon_DrawPadKeyboard();\n}')
    path=client/'cl_uiapi.cpp'
    replace(path,' if(!Q_stricmp(Cmd_Argv(1),"assertconsole")){',
            ' if(!Q_stricmp(Cmd_Argv(1),"keyboarddevice")){Cvar_SetValue("st_testKeyboardDevice",atoi(Cmd_Argv(2)));return;}\n'
            ' if(!Q_stricmp(Cmd_Argv(1),"gameplay")){UIVM_SetActiveMenu(UIMENU_NONE);Key_SetCatcher(0);return;}\n'
            ' if(!Q_stricmp(Cmd_Argv(1),"assertchat")){\n'
            '  int kind=(Key_GetCatcher()&KEYCATCH_MESSAGE)?chat_playerNum>=0?3:chat_team?2:1:0;\n'
            '  if(kind!=atoi(Cmd_Argv(2))||Con_PadKeyboardActive()!=!!atoi(Cmd_Argv(3)))Com_Printf("ST_PAD_CHAT_FAIL actual %d %d expected %s %s catcher %d mode %d\\n",kind,int(Con_PadKeyboardActive()),Cmd_Argv(2),Cmd_Argv(3),Key_GetCatcher(),Cvar_VariableIntegerValue("st_virtualKeyboard"));\n'
            '  return;\n }\n'
            ' if(!Q_stricmp(Cmd_Argv(1),"privatefixture")){\n'
            '  chat_playerNum=1;chat_team=qfalse;Field_Clear(&chatField);chatField.widthInChars=30;\n'
            '  Key_SetCatcher(KEYCATCH_MESSAGE);if(Con_AutoKeyboard(true))Con_SetPadKeyboard(KEYCATCH_MESSAGE);return;\n }\n'
            ' if(!Q_stricmp(Cmd_Argv(1),"assertconsole")){')
    write(RECEIPT,dict(installed=installed,sources={role:tree(OUT/role) for role in ('engine','frontend')}))
    print('Prepared chat keyboard and bindings.',flush=True)


def files(qa=False):
    return {builder.ROLES[role][3]:builder.binary(role) for role in (('engine-qa','qa') if qa else ('engine','ui'))}


def install(tag):
    helper=import_module('Install-Profile-Browser');helper.stopped()
    home,settings=helper.settings()
    installed=read(RECEIPT)['installed']
    assert all(sha(ROOT/name)==digest for name,digest in installed.items()), 'Installed client changed during testing'
    assert not (home/'uix86_64.dll').exists(), 'Profile has a UI override'
    evidence=OUT/tag/'result.json'
    assert read(evidence)==dict(source=sha(RECEIPT),files={name:sha(path) for name,path in files(True).items()})
    for role in ('engine','engine-qa','ui','qa'):
        assert read(OUT/f'build-{role}.json')==dict(source=sha(RECEIPT),sha256=sha(builder.binary(role)))
    sources=files()
    before={name:installed[name] for name in sources}
    after={name:sha(path) for name,path in sources.items()}
    protected={name:digest for name,digest in installed.items() if name not in sources}
    backup=ROOT/'dist/backups'/f'chat-keyboard-{datetime.now():%Y%m%d-%H%M%S}'
    payload=dict(before=before,after=after,protected=protected,backup=str(backup),source_sha256=sha(RECEIPT),
                 evidence=sha(evidence),preserved_settings=settings)
    import_module('Install-Handedness').install_transaction(ROOT,sources,before,after,protected,backup,
        ROOT/'dist/chat-keyboard-install.json',payload)
    print('Installed chat keyboard and bindings.')


if __name__=='__main__':
    op=sys.argv[1]
    if op in ('prepare','refresh'):prepare(op=='refresh')
    elif op=='install':install(sys.argv[2])
    else:builder.build(op)
