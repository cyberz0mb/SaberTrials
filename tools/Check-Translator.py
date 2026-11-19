"""Run real chat and Setup checks in an isolated local client/server."""
from datetime import datetime
from importlib import import_module
import os
import re
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode=True
b=import_module('Build-Translator')


def stage(folder,mode,installed=False):
    mod=folder/'home/SaberTrials';mod.mkdir(parents=True)
    if installed:
        assert mode in ('chat','languages','unicode')
        return mod,{name:b.ROOT/name for name in b.files()}
    files=b.files(mode=='settings')
    staged={}
    for name,path in files.items():
        target=folder/name if name.startswith('client/') else mod/name
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
        staged[name]=target
    for name in ('SDL2.dll','OpenAL32.dll'):
        shutil.copyfile(b.ROOT/'client'/name,folder/'client'/name)
    if mode!='missing_helper':
        def ignore(path,names):return [name for name in names if name=='__pycache__' or (mode=='missing_pack' and name=='models')]
        def copy(source,target):
            if '/models/' in source.replace('\\','/') or '/fonts/' in source.replace('\\','/'):os.link(source,target)
            else:shutil.copyfile(source,target)
        shutil.copytree(b.OUT/'runtime',folder/'client/translator',ignore=ignore,copy_function=copy)
    return mod,staged


def run(mode,installed=False,renderer='rd-rend2'):
    folder=b.OUT/(('installed-' if installed else '')+mode+'-'+renderer+'-'+datetime.now().strftime('%H%M%S'))
    mod,files=stage(folder,mode,installed)
    source_hash=b.sha(b.RECEIPT)
    print(folder,flush=True)
    lines=['wait 70','set name "Translator Tester"','set sv_pure 0','set g_gametype 6','set g_warmup 0',
        'set st_mvpPrototype 0','set st_portraitMode 0','set cg_chatBox 30000',
        'set st_chatSize 100','set st_chatHeight 36','set st_chatWidth 65','set st_translate 1',
        'set st_translateSource 0','set st_translateTarget 1','set st_translateOriginal 1']
    if mode=='settings':
        catalog=b.read(b.ROOT/'development-source/setup/catalog.json')
        index=next(i for i,row in enumerate(catalog) if row['name']=='st_translate')
        target_index=next(i for i,row in enumerate(catalog) if row['name']=='st_translateTarget')
        source_index=next(i for i,row in enumerate(catalog) if row['name']=='st_translateSource')
        lines+=['ui_openmenu setup_menu','wait 30','st_setupqa click 2002','wait 10',
                'st_setupqa scroll 205','wait 30','screenshot_png translator-settings',
                'st_setupqa assertvar st_translate 1','st_setupqa click '+str(2200+index),
                *['st_setupqa click '+str(2200+target_index) for _ in range(11)],
                *['st_setupqa click '+str(2200+source_index) for _ in range(6)],
                'wait 15','screenshot_png translator-language-settings',
                'st_setupqa assertdirty 1','st_setupqa assertvar st_translate 1',
                'st_setupqa click 2902','wait 15','st_setupqa assertvar st_translate 0',
                'st_setupqa assertvar st_translateTarget 12','st_setupqa assertvar st_translateSource 6',
                'st_setupqa click 2900','wait 15']
    else:
        lines+=['devmap mp/ffa3','wait 450','team red','wait 100','ui_openmenu ingame_setup','wait 10',
                'togglemenu','wait 30','say "¿Dónde está mi equipo? Necesito ayuda."','wait 1200',
                'echo ST_TRANSLATOR_CASE_english','st_translatorinfo','screenshot_png english']
        if mode in ('languages','unicode'):
            languages=b.read(b.SOURCE/'languages.json')
            for language in languages[1:]:
                if mode=='unicode' and language['code'] not in ('ar','pb','ko'):continue
                lines+=['set st_translateSource 1','set st_translateTarget '+str(language['id']),'wait 80',
                    'say "Where is my team? I need help."','wait 1100',
                    'echo ST_TRANSLATOR_CASE_'+language['code'],'st_translatorinfo','screenshot_png lang-'+language['code']]
        elif mode=='chat':
            lines+=['set st_translateTarget 2','set st_translateSource 1','wait 80',
                'say "Good game everyone, see you tomorrow."','wait 450',
                'echo ST_TRANSLATOR_CASE_spanish','st_translatorinfo','screenshot_png spanish',
                'say_team "This is team-only chat."','wait 30','tell 0 "This is a private message."','wait 120',
                'echo ST_TRANSLATOR_CASE_private','st_translatorinfo',
                'set cg_teamChatsOnly 1','say "This public message is hidden."','wait 80','set cg_teamChatsOnly 0',
                'echo ST_TRANSLATOR_CASE_muted','st_translatorinfo',
                'set st_translateOriginal 0','wait 30','screenshot_png translated-only',
                'set st_translate 0','wait 50','say "Translation is disabled."','wait 80',
                'echo ST_TRANSLATOR_CASE_disabled','st_translatorinfo','screenshot_png disabled',
                'set st_translate 1','set st_translateSource 0','set st_translateTarget 1','wait 40',
                'say "El equipo rojo esta cerca de nuestra base."','disconnect','wait 40',
                'devmap mp/ffa3','wait 450','team red','wait 100','ui_openmenu ingame_setup','wait 10','togglemenu','wait 60',
                'echo ST_TRANSLATOR_CASE_reconnected','st_translatorinfo']
    lines+=['echo ST_TRANSLATOR_CHECK_COMPLETE','wait 15','quit']
    (mod/'test.cfg').write_bytes(('\n'.join(lines)+'\n').encode('cp1252'))
    options=dict(fs_basepath=b.ROOT.parent,fs_homepath=folder/'home',fs_game='SaberTrials',com_unpackLibraries=0,
        logfile=2,net_ip='127.0.0.1',net_port=29400+2*['chat','settings','missing_pack','missing_helper','languages','unicode'].index(mode)+(renderer=='rd-vanilla'),r_fullscreen=0,r_mode=-1,r_customwidth=1600,r_customheight=900,
        cl_renderer=renderer,com_maxfps=60,s_initsound=0,com_introplayed=1)
    command=[str(files['client/SaberTrials.x86_64.exe'] if installed else folder/'client/SaberTrials.x86_64.exe'),'+safe']
    for name,value in options.items():command.extend(['+set',name,str(value)])
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    process=subprocess.Popen(command+['+exec','test.cfg'],cwd=b.ROOT.parent,startupinfo=startup,
        env={**os.environ,'LOCALAPPDATA':str(folder/'local-app-data')},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:assert process.wait(timeout=360 if mode=='languages' else 150)==0
    finally:
        if process.poll() is None:process.kill();process.wait()
    log=(mod/'qconsole.log').read_text(encoding='cp1252',errors='replace')
    assert 'ST_TRANSLATOR_CHECK_COMPLETE' in log and 'ST_SETUP_FAIL' not in log,log[-2500:]
    clean=re.sub(r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d ','',log,flags=re.M)
    states=dict(re.findall(r'ST_TRANSLATOR_CASE_(\w+)\s+ST_TRANSLATOR ([^\n]+)',clean))
    counts={key:int(re.search(r'translated=(\d+)',value)[1]) for key,value in states.items()}
    if mode=='chat':
        assert counts['english']==1 and counts['spanish']==2,states
        assert counts['private']==counts['muted']==counts['disabled']==4,states
        assert 'team=1 private=1' in states['private'],states
        assert counts['reconnected']==0,states
    elif mode in ('languages','unicode'):
        expected=17 if mode=='languages' else 4
        assert len(states)==expected,states
        assert list(counts.values())==list(range(1,expected+1)),states
        assert all('pending=0' in state and 'status=Ready - offline' in state for state in states.values()),states
    elif mode=='missing_pack':assert counts['english']==0 and 'pack unavailable' in states['english'],states
    elif mode=='missing_helper':assert counts['english']==0 and 'Translator unavailable' in states['english'],states
    runtime=b.ROOT/'client/translator' if installed else b.OUT/'runtime'
    assert b.sha(b.RECEIPT)==source_hash,'Candidate source changed during check'
    b.write(folder/'result.json',dict(proof_version=2,mode=mode,installed=installed,renderer=renderer,source=source_hash,files={name:b.sha(path) for name,path in files.items()},
                                    runtime=b.sha(runtime/'worker.py'),states=states,log=b.sha(mod/'qconsole.log')))
    print('Passed '+mode,flush=True)


if __name__=='__main__':run(sys.argv[1],'--installed' in sys.argv,'rd-vanilla' if '--vanilla' in sys.argv else 'rd-rend2')
