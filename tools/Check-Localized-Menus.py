"""Smoke-test localized menus with isolated settings and native screenshots."""
from argparse import ArgumentParser
from importlib import import_module
import json
import os
import shutil
import subprocess

build = import_module('Build-Localized-Menus')


def run(renderer, installed):
    root, out = build.ROOT, build.OUT
    folder = out/('installed-'+renderer if installed else 'review-'+renderer)
    mod = folder/'home/SaberTrials'
    mod.mkdir(parents=True,exist_ok=True)
    # Earlier runs staged an external catalog here. The current executable embeds it.
    staged_catalog = mod/build.LEGACY_PACK
    if staged_catalog.is_file():
        staged_catalog.rename(mod.parent/(build.LEGACY_PACK+'.retired'))
    targets = build.files()
    if installed:
        paths = {name:root/name for name in targets}
        assert {name:build.sha(path) for name,path in paths.items()} == build.read(build.INSTALL_RECEIPT)['after']
        exe = root/'client/SaberTrials.x86_64.exe'
    else:
        exe = folder/'bin/SaberTrials.x86_64.exe'
        exe.parent.mkdir(exist_ok=True)
        shutil.copyfile(targets['client/SaberTrials.x86_64.exe'],exe)
        for name in ('OpenAL32.dll','SDL2.dll'):
            shutil.copyfile(root/'client'/name,exe.parent/name)
        for name in ('rd-vanilla_x86_64.dll','rd-rend2_x86_64.dll'):
            shutil.copyfile(targets['client/'+name],exe.parent/name)
        if not (exe.parent/'translator').exists():
            (exe.parent/'translator').mkdir()
            shutil.copytree(root/'client/translator/fonts',exe.parent/'translator/fonts')
        shutil.copyfile(build.build.binary('qa'),mod/'uix86_64.dll')
    lines = ['wait 80']
    captures = []

    def open_menu(menu):
        lines.extend(['ui_openmenu '+menu,'wait 25'])

    def shot(label):
        captures.append(label)
        lines.extend(['wait 12','screenshot_png '+label,'wait 7'])

    if not installed:
        open_menu('setup_menu')
        lines.extend(['st_setupqa click 2002','wait 15','st_setupqa assertvar st_menuLanguage 1'])
        shot('setup-english')
        lines.extend(['st_setupqa click '+str(2200+len(json.loads(
            (root/'development-source/setup/catalog.json').read_text()))),
                      'wait 10','st_setupqa assertdirty 1','st_setupqa assertvar st_menuLanguage 1',
                      'st_setupqa click 2902','wait 15','st_setupqa assertvar st_menuLanguage 2'])
        shot('setup-spanish')
    for language,name in ((2,'spanish'),(4,'japanese'),(7,'arabic'),(14,'hindi'),(13,'korean'),(17,'ukrainian')):
        lines.append(f'set st_menuLanguage {language}')
        open_menu('main')
        shot('main-'+name)
        if language in (2,4,7):
            open_menu('controlsMenu')
            shot('controls-'+name)
        if language in (2,4):
            open_menu('playerMenu')
            shot('profile-'+name)
            open_menu('multiplayermenu')
            shot('play-'+name)
            open_menu('rulesMenu_games')
            shot('rules-'+name)
    lines.append('set st_menuLanguage 1')
    open_menu('main')
    shot('main-back-to-english')
    if installed:
        # Leave and reopen the UI across a renderer restart and an FFA match
        # to validate the installed UI and gameplay module together.
        lines.extend(['set st_menuLanguage 7','vid_restart','wait 85'])
        open_menu('main')
        shot('main-after-restart')
        lines.extend(['set g_gametype 0','devmap mp/ffa3','wait 350','team free','wait 45'])
        open_menu('ingame')
        shot('pause-arabic')
    lines.extend(['echo ST_MENU_LANGUAGE_COMPLETE','wait 5','quit'])
    (mod/'menu-language-test.cfg').write_text('\n'.join(lines)+'\n',encoding='ascii')
    settings = {'fs_basepath':root.parent,'fs_homepath':folder/'home','fs_game':'SaberTrials',
                'com_unpackLibraries':0,'r_fullscreen':0,'r_mode':-1,'r_customwidth':1280,'r_customheight':720,
                'cl_renderer':renderer,'com_maxfps':60,'sv_pure':0,'s_initsound':0,'logfile':2}
    command = [str(exe),'+safe']
    for key,value in settings.items():
        command += ['+set',key,str(value)]
    command += ['+exec','menu-language-test.cfg']
    startup = subprocess.STARTUPINFO()
    startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    subprocess.run(command,cwd=root.parent,env={**os.environ,'LOCALAPPDATA':str(folder/'local-app-data')},
        check=True,timeout=140,startupinfo=startup,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    log = (mod/'qconsole.log').read_text(errors='replace')
    assert 'ST_MENU_LANGUAGE_COMPLETE' in log and 'ST_SETUP_FAIL' not in log, log[-3600:]
    assert captures and all(f'Wrote screenshots/{name}.png' in log and
        (mod/'screenshots'/f'{name}.png').is_file() for name in captures)
    if installed:
        assert 'CL_InitCGame:' in log and 'entered the game' in log and 'DISCONNECTED' not in log
    build.write(folder/'result.json',dict(source=build.sha(build.RECEIPT),
        files={name:build.sha(path) for name,path in targets.items()},captures=captures))
    print('Passed',folder.name)


if __name__=='__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--installed',action='store_true')
    parser.add_argument('--vanilla',action='store_true')
    args = parser.parse_args()
    run('rd-vanilla' if args.vanilla else 'rd-rend2',args.installed)
