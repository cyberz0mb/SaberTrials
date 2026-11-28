"""Exercise stick motion and fast face-button taps through SDL and the real menus."""
from datetime import datetime
from importlib import import_module
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys

b = import_module('Build-Controller-Response')
root, out = b.root, b.out


def test_ui():
    frontend = out / 'test-frontend'
    menu_base = root / 'dist/menu-selection-01'
    assert b.builder.sha(menu_base/'build/Release/uix86_64.dll') == b.builder.sha(root/'uix86_64.dll')
    shutil.copytree(menu_base / 'frontend', frontend, dirs_exist_ok=True)
    ui = frontend / 'codemp/ui'
    shutil.copyfile(root / 'tests/controls-native/virtual_pad_live.cpp', ui / 'virtual_pad_live.cpp')
    with (ui / 'CMakeLists.txt').open('a') as cmake:
        cmake.write('\ntarget_sources(${MPUI} PRIVATE virtual_pad_live.cpp)\n')
    overlay = b.builder.module('controls_overlay', b.controls / 'gamepad_menu_overlay.py')
    overlay.swap(ui/'ui_main.c', 'void UI_Refresh( int realtime )\n{', '''extern const char* ST_VirtualPadDrive(int,float,float);
void UI_Refresh( int realtime )
{
    static int lastPhase = 0;
    int phase = (int)trap->Cvar_VariableValue("st_virtualPadPhase");
    const char* error = ST_VirtualPadDrive(phase, uiInfo.uiDC.cursorx, uiInfo.uiDC.cursory);
    if (error) Com_Error(ERR_DROP,"Virtual controller setup failed: %s",error);
    if (phase != lastPhase) {
        menuDef_t* menu = Menu_GetFocused();
        Com_Printf("PAD_OBS phase=%d menu=%s tab=%d x=%d y=%d active=%d catcher=%d unfocused=%d\\n",phase,
            menu ? menu->window.name : "none",scui.tab,(int)uiInfo.uiDC.cursorx,(int)uiInfo.uiDC.cursory,
            (int)trap->Cvar_VariableValue("st_controllerActive"),trap->Key_GetCatcher(),(int)trap->Cvar_VariableValue("com_unfocused"));
        lastPhase = phase;
    }''')
    build = out / 'build-test-ui'
    with (out / 'test-ui-build.log').open('w') as log:
        subprocess.run(['cmake', '-S', str(frontend), '-B', str(build), '-G', 'Visual Studio 18 2026', '-A', 'x64',
                        '-DST_STAFF_QA=OFF', '-DST_DEPS='+str(root/'dist/handedness-baseline-06/deps'),
                        '-DBuildMPUI=ON', *['-D'+flag+'=OFF' for flag in (
                            'BuildMPGame','BuildMPDed','BuildMPEngine','BuildMPCGame','BuildMPRdVanilla',
                            'BuildMPRend2','BuildMPRdVulkan','BuildSPEngine','BuildSPGame','BuildSPRdVanilla')]],
                       check=True, stdout=log, stderr=subprocess.STDOUT)
        subprocess.run(['cmake','--build',str(build),'--config','Release','--parallel','5','--target','uix86_64'],
                       check=True, stdout=log, stderr=subprocess.STDOUT)


def run(executable, virtual_sdl=None):
    folder = out / ('run-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    mod = folder / 'home/SaberTrials'
    mod.mkdir(parents=True)
    client = folder / 'client'
    client.mkdir()
    exe = executable
    if executable != root / b.target:
        exe = client / 'SaberTrials.x86_64.exe'
        shutil.copyfile(executable, exe)
        shutil.copyfile(virtual_sdl or root/'client/SDL2.dll', client/'SDL2.dll')
        for name in ('OpenAL32.dll','rd-vanilla_x86_64.dll'):
            shutil.copyfile(root/'client'/name, client/name)
    lines = ['wait 70','ui_openmenu controlsMenu','wait 15']
    if virtual_sdl:
        shutil.copyfile(out/'build-test-ui/Release/uix86_64.dll', mod/'uix86_64.dll')
        lines += ['set st_controllerEnabled 0','bind JOY0 toggleconsole','bind JOY1 togglemenu',
                  'set st_virtualPadPhase 1','wait 50','set st_virtualPadPhase 2','wait 320',
                  'set st_virtualPadPhase 3','wait 40','set st_virtualPadPhase 4','wait 40',
                  'set st_virtualPadPhase 5','wait 12']
    lines += ['screenshot_png controller-check','wait 4','echo PAD_CHECK_DONE','quit']
    (mod/'test.cfg').write_text('\n'.join(lines)+'\n')
    cmd = [str(exe), '+safe']
    for key, val in dict(fs_basepath=root.parent, fs_homepath=folder/'home', fs_game='SaberTrials',
                         logfile=2, net_ip='127.0.0.1', net_port=29950, com_unpackLibraries=0,
                         cl_renderer='rd-vanilla', r_fullscreen=0, r_mode=4, com_maxfps=60,
                         s_initsound=0, com_introplayed=1).items():
        cmd.extend(['+set', key, str(val)])
    startup=subprocess.STARTUPINFO()
    if not virtual_sdl:
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow=0
    subprocess.run(cmd+['+exec','test.cfg'], cwd=root.parent, startupinfo=startup, check=True, timeout=90,
                   env={**os.environ,'LOCALAPPDATA':str(folder/'local')},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    log=(mod/'qconsole.log').read_text(errors='replace')
    assert 'PAD_CHECK_DONE' in log and 'ERROR:' not in log and (mod/'screenshots/controller-check.png').exists(), folder
    if virtual_sdl:
        states={int(p):(menu,int(tab),int(x),int(y),int(active)) for p,menu,tab,x,y,active in
                re.findall(r'PAD_OBS phase=(\d+) menu=(\w+) tab=(\d+) x=(\d+) y=(\d+) active=(\d+)',log)}
        print(states, flush=True)
        assert states[2][0]=='controlsMenu' and states[2][1]!=4 and states[2][4]==1, states
        assert abs(states[3][2]-372)<4 and abs(states[3][3]-130)<4, states
        assert states[4][:2]==('controlsMenu',4) and states[5][0]=='main', states
    return str(folder.relative_to(out))


if __name__ == '__main__':
    op = sys.argv[1]
    if op=='test-ui':
        test_ui()
    elif op=='installed':
        print('Installed client passed its menu startup check:',run(root/b.target))
    elif op=='check':
        sdl = Path(sys.argv[2]).resolve(strict=True)
        tests = out/'tests'
        subprocess.run(['cmake','-S',str(root/'tests/controls-native'),'-B',str(tests)],check=True)
        subprocess.run(['cmake','--build',str(tests),'--config','Release'],check=True)
        subprocess.run(['ctest','--test-dir',str(tests),'-C','Release','--output-on-failure'],check=True)
        virtual = run(b.binary,sdl)
        shipping = run(b.binary)
        b.builder.write(out/'verification.json',dict(passed=True,candidate=b.builder.sha(b.binary),
            virtual_menu=virtual,shipping_menu=shipping,virtual_sdl=b.builder.sha(sdl),
            shipping_sdl=b.builder.sha(root/'client/SDL2.dll')))
        print('Verified virtual controller navigation and shipping client startup.')
