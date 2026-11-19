"""Verify preview sliders, saved values and the gameplay chat panel."""
import argparse
from datetime import datetime
from importlib import import_module
import json
import os
import shutil
import subprocess
import sys

sys.dont_write_bytecode=True
b=import_module('Build-Chat-Panel')


def run(mode):
    qa=mode in ('wide','tall')
    run=b.OUT/f'{mode}-{datetime.now():%H%M%S}'
    mod=run/'home/SaberTrials'
    shots=mod/'screenshots'
    shots.mkdir(parents=True)
    files=b.files(qa)
    exe=b.build_tools.EXE
    if mode=='installed':
        files={name:b.ROOT/name for name in files}
        assert {name:b.sha(path) for name,path in files.items()}==b.read(b.ROOT/'dist/chat-panel-install.json')['after']
    else:
        for name,path in files.items():
            target=run/name if name==exe else mod/name
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target)
        for name in ('SDL2.dll','OpenAL32.dll','rd-vanilla_x86_64.dll','rd-rend2_x86_64.dll'):
            shutil.copyfile(b.ROOT/'client'/name,run/'client'/name)
    print(run,flush=True)
    names=[]
    lines=['wait 70','set name "Chat Review"','set st_chatSize 1','set st_chatWidth 42',
           'set st_chatHeight 20','set st_chatOpacity 65','bind F12 st_togglechat']

    def shot(name):
        names.append(name)
        lines.extend(['wait 8','screenshot_png '+name,'wait 8'])

    if qa:
        (mod/'000 Legacy Chat.cfg').write_text('seta st_chatSize 2\n')
        catalog=json.loads((b.ROOT/'development-source/setup/catalog.json').read_text())
        ids={row['name']:2400+i for i,row in enumerate(catalog)}
        lines.extend(['ui_openmenu setup_menu','wait 16','st_setupqa click 2002','wait 12'])
        shot('preview-default')
        for name,start,end in [('st_chatSize',0,.9),('st_chatWidth',0,.8),('st_chatHeight',0,.75),('st_chatOpacity',0,.3)]:
            lines.extend([f'st_setupqa dragstart {ids[name]} {start}',f'st_setupqa dragmove {end}','wait 8'])
            shot('preview-'+name[7:].lower())
            lines.append('st_setupqa dragend')
        lines.extend(['st_setupqa assertdirty 1','st_setupqa assertvar st_chatSize 1',
                      'st_setupqa assertvar st_chatWidth 42','st_setupqa assertvar st_chatHeight 20',
                      'st_setupqa assertvar st_chatOpacity 65','st_setupqa click 2901','wait 8',
                      'st_setupqa assertdirty 0'])
        shot('preview-cancelled')
        lines.extend([f'st_setupqa dragstart {ids["st_chatWidth"]} .5','st_setupqa dragend','wait 8',
                      'st_setupqa click 2902','wait 8','st_setupqa assertvar st_chatWidth 45.6',
                      'st_setupqa click 2904','wait 8','st_setupqa click 3000','wait 8',
                      'st_setupqa click 2902','wait 8','st_setupqa assertvar st_chatSize 120',
                      'st_setupqa click 2900','wait 8','set st_chatSize 1','set st_chatWidth 42'])

    lines.extend(['set sv_pure 0','set g_gametype 0','set st_mvpPrototype 0','set cg_chatBox 18000',
                  'set st_portraitMode 0','devmap mp/ffa3','wait 400','team free','wait 80',
                  'ui_openmenu ingame_setup','wait 10'])
    if qa:
        lines.extend(['st_setupqa click 2002','wait 12'])
        shot('preview-ingame')
        lines.extend(['ui_openmenu st_qa_no_menu','st_inspectqa key 27 1','wait 20'])
    else:
        lines.extend(['togglemenu','wait 20'])
    lines.extend(['set cg_thirdPerson 1','weapon 1','wait 150','say First chat message.',
                  'say The chat panel is ready for a quick test. This longer sentence should wrap inside the frame.',
                  'say See you near the stairs.','wait 25'])
    shot('gameplay-chat')
    lines.append('st_togglechat')
    shot('gameplay-collapsed')
    lines.extend(['set st_chatSize 115','set st_chatWidth 51','set st_chatHeight 26','set st_chatOpacity 26','st_togglechat'])
    shot('gameplay-resized')
    lines.extend(['echo ST_CHAT_CHECK_COMPLETE','wait 10','quit'])
    (mod/'review.cfg').write_text('\n'.join(lines)+'\n')

    width,height=(1280,1024) if mode=='tall' else (1600,900)
    options=dict(fs_basepath=b.ROOT.parent,fs_homepath=run/'home',fs_game='SaberTrials',com_unpackLibraries=0,
        logfile=2,net_ip='127.0.0.1',net_port=29194+('tall','wide','production','installed').index(mode),
        r_fullscreen=0,r_mode=-1,r_customwidth=width,r_customheight=height,
        cl_renderer='rd-vanilla' if mode=='tall' else 'rd-rend2',com_maxfps=60,s_initsound=0,com_introplayed=1)
    command=[str(files[exe] if mode=='installed' else run/exe),'+safe']
    for name,value in options.items():
        command.extend(['+set',name,str(value)])
    startup=subprocess.STARTUPINFO()
    startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow=0
    process=subprocess.Popen(command+['+exec','review.cfg'],cwd=b.ROOT.parent,startupinfo=startup,
        env={**os.environ,'LOCALAPPDATA':str(run/'local-app-data')},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        assert process.wait(timeout=100)==0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    log=(mod/'qconsole.log').read_text(errors='replace')
    errors=[line for line in log.splitlines() if any(word in line for word in
            ('ST_SETUP_FAIL','Unknown command "st_togglechat"'))]
    assert 'ST_CHAT_CHECK_COMPLETE' in log and 'First chat message' in log and not errors,errors or log[-1500:]
    assert all((shots/(name+'.png')).stat().st_size>10000 for name in names)
    if qa:
        previews = ('default','size','width','height','opacity')
        assert len({b.sha(shots/f'preview-{name}.png') for name in previews})==len(previews)
    b.write(run/'result.json',dict(source=b.sha(b.RECEIPT),mode=mode,qa=qa,
        files={name:b.sha(path) for name,path in files.items()},screenshots=names))
    print(f'Passed {run.name}, {len(names)} screenshots')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('wide','tall','production','installed'))
    run(parser.parse_args().mode)
