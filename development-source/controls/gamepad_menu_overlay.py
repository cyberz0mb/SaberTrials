"""Integrate normalized gamepad menu input into the verified client sources."""
import shutil


def swap(path, old, new):
    source = path.read_text(encoding='utf8')
    assert source.count(old) == 1, (path, old)
    path.write_text(source.replace(old, new), encoding='utf8')


def wire(engine, frontend, source):
    controls = source/'controls'
    client = engine/'codemp/client'
    ui = frontend/'codemp/ui'
    for tree in (engine, frontend):
        shutil.copyfile(controls/'st_controls_catalog.h', tree/'codemp/ui/st_controls_catalog.h')
    shutil.copyfile(source/'client-runtime/st_controller_move.inc', client/'cl_st_controller.inc')
    shutil.copyfile(controls/'st_controller.inc', engine/'shared/sdl/st_controller.inc')
    shutil.copyfile(controls/'cl_st_pad_menu.inc', client/'cl_st_pad_menu.inc')
    swap(engine/'shared/sdl/sdl_input.cpp', 'if (STPadFrame()) return;',
         'if (STPadFrame((SDL_GetWindowFlags(SDL_window) & SDL_WINDOW_INPUT_FOCUS) != 0)) return;')
    swap(engine/'shared/sdl/sdl_input.cpp', '#include <SDL.h>', '#include <SDL.h>\n#include <cmath>')
    swap(engine/'shared/sys/sys_public.h', '\tSE_MAX',
         '\tSE_GAMEPAD_BUTTON,\n\tSE_GAMEPAD_POINTER,\n\tSE_MAX')
    swap(engine/'shared/sys/sys_event.cpp', '"SE_CONSOLE"',
         '"SE_CONSOLE",\n\t\t"SE_GAMEPAD_BUTTON",\n\t\t"SE_GAMEPAD_POINTER"')
    swap(client/'cl_keys.cpp', 'static int keyCatchers = 0;',
         '#include "cl_st_pad_menu.inc"\n\n'
         'void CL_GamepadButtonEvent(int button,qboolean down,unsigned time) {CL_GamepadButton(button,down,time);}\n'
         'void CL_GamepadPointerEvent(int dx,int dy) {CL_GamepadPointer(dx,dy);}\n\n'
         'static int keyCatchers = 0;')
    swap(client/'cl_uiapi.cpp', '#include "cl_st_controls.inc"',
         '#include "cl_st_controls.inc"\n'
         '#ifdef ST_CONTROLS_QA\n'
         'extern void CL_GamepadButtonEvent(int,qboolean,unsigned);\n'
         'extern void CL_GamepadPointerEvent(int,int);\n'
         'static void ST_PadQA_f() {\n'
         ' if(Cmd_Argc()!=4)return;\n'
         ' const int a=atoi(Cmd_Argv(2)),b=atoi(Cmd_Argv(3));\n'
         ' if(!Q_stricmp(Cmd_Argv(1),"move"))CL_GamepadPointerEvent(a,b);\n'
         ' else if(!Q_stricmp(Cmd_Argv(1),"button"))CL_GamepadButtonEvent(a,b?qtrue:qfalse,Sys_Milliseconds());\n'
         '}\n#endif')
    swap(client/'cl_uiapi.cpp', '\tCmd_AddCommand("st_controlskey",STC_QAKey_f,"Controls regression input");',
         '\tCmd_AddCommand("st_controlskey",STC_QAKey_f,"Controls regression input");\n'
         '\tCmd_AddCommand("st_padqa",ST_PadQA_f,"Gamepad menu regression input");')
    swap(client/'cl_keys.cpp', 'if ( catcher != keyCatchers )\n\t\tKey_ClearStates();',
         'if ( catcher != keyCatchers ) {\n\t\tCL_ReleaseGamepadMenuButtons();\n\t\tKey_ClearStates();\n\t}')
    common = engine/'codemp/qcommon/common.cpp'
    swap(common, 'int Com_EventLoop( void ) {',
         '#ifndef DEDICATED\nextern void CL_GamepadButtonEvent(int,qboolean,unsigned);\n'
         'extern void CL_GamepadPointerEvent(int,int);\n#endif\nint Com_EventLoop( void ) {')
    swap(common, '\t\tcase SE_CONSOLE:',
         '\t\tcase SE_GAMEPAD_BUTTON:\n#ifndef DEDICATED\n'
         '\t\t\tCL_GamepadButtonEvent(ev.evValue, (qboolean)ev.evValue2, ev.evTime);\n#endif\n\t\t\tbreak;\n'
         '\t\tcase SE_GAMEPAD_POINTER:\n#ifndef DEDICATED\n'
         '\t\t\tCL_GamepadPointerEvent(ev.evValue,ev.evValue2);\n#endif\n\t\t\tbreak;\n\t\tcase SE_CONSOLE:')
    swap(ui/'ui_main.c', 'if (SWI_Key(key, down) || SWB_Key(key, down)) return;',
         'if (SWI_Key(key, down)) return;\n'
         '\tif (!(SCUI_IsMenu() && scui.capture)) {\n'
         '\t\tif (key == A_JOY9) key = A_MWHEELUP;\n'
         '\t\telse if (key == A_JOY10) key = A_MWHEELDOWN;\n\t}\n'
         '\tif (SWB_Key(key, down)) return;')
    swap(ui/'ui_st_saber_inspect.inc', 'trap->Key_IsDown(A_JOY9) - trap->Key_IsDown(A_JOY10)',
         'trap->Cvar_VariableValue("st_uiBumperZoom")')
    swap(ui/'ui_st_saber_inspect.inc', 'trap->Cvar_VariableValue("st_controllerEnabled") != 0',
         'trap->Cvar_VariableValue("st_controllerActive") != 0')
    shutil.copyfile(controls/'ui_st_controls_draw.inc',ui/'ui_st_controls_draw.inc')
    path = ui/'ui_st_controls.inc'
    authored = (controls/path.name).read_text(encoding='utf8')
    for prefix in ('static void SCUI_Mouse(void)',):
        old = next(line for line in path.read_text(encoding='utf8').splitlines() if line.startswith(prefix))
        new = next(line for line in authored.splitlines() if line.startswith(prefix))
        swap(path,old,new)
    swap(path, '#include "ui_st_controls_draw.inc"',
         authored[authored.index('static float SCUI_SettingNumber('):authored.index('static void SCUI_SelectAction(')]
         +'#include "ui_st_controls_draw.inc"')
    swap(path, 'if(r.b==1||r.b==2){Com_sprintf(value,sizeof(value),"%d",((int)r.number+1)%(r.b==1?2:3));',
         'if(r.b==1||r.b==2){const auto& setting=stcSettings[r.a];\n'
         ' int next=(int)r.number<(int)setting.max?(int)r.number+1:(int)setting.min;\n'
         ' if(r.a==19)next=r.number==2?1:2;\n'
         ' Com_sprintf(value,sizeof(value),"%d",next);')
    swap(path, 'float min=h.a==22?0:1,max=h.a==22?.95f:10,step=h.a==22?.01f:.25f;',
         'const auto& setting=stcSettings[h.a];const float min=setting.min,max=setting.max,step=h.a==22?.01f:.25f;')
