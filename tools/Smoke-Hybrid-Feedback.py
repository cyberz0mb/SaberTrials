"""Verify staged production menus and Akaza poses in an isolated client; no server."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
CANDIDATE=ROOT/'dist/hybrid-candidate-03'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main(renderer,run):
    folder=CANDIDATE/'qa'/('menus-'+renderer+'-'+run)
    if folder.exists():raise RuntimeError('Preserve previous evidence; choose another --run')
    mod=folder/'home/SaberTrials';mod.mkdir(parents=True)
    files={}
    for name in ('openjk.x86_64.exe','rd-vanilla_x86_64.dll','rd-rend2_x86_64.dll'):
        files['bin/'+name]=CANDIDATE/'build-engine/Release'/name
    for name in ('SDL2.dll','OpenAL32.dll'):files['bin/'+name]=ROOT/'client'/name
    files['home/SaberTrials/uix86_64.dll']=CANDIDATE/'build-frontend/Release/uix86_64.dll'
    for source in (CANDIDATE/'assets').glob('*.pk3'):
        files['home/SaberTrials/'+source.name]=source
    for source in (CANDIDATE/'menus').rglob('*'):
        if source.is_file():files['home/SaberTrials/'+source.relative_to(CANDIDATE/'menus').as_posix()]=source
    for name,source in files.items():
        target=folder/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    # An isolated onOpen test driver calls the real production menu handler.
    # No QA code is compiled into the modules or added to the installed menus.
    menu=mod/'ui/jamp/saber.menu';text=menu.read_text();end=text.rfind('}')
    driver='''menuDef {
 name st_feedback_open rect 0 0 640 480 visible 1
 onOpen { close st_feedback_open; uiScript stStanceOpenMain; }
}
'''
    menu.write_text(text[:end]+driver+text[end:],newline='\n')
    config='''wait 60
screenshot_png feedback-main
set model akaza/default
set saberStyleLoadout "4 5 6"
set saberStances "111111000000"
ui_openmenu saberMenu
wait 60
screenshot_png feedback-saber
ui_openmenu st_feedback_open
wait 60
screenshot_png feedback-akaza-upright
set saberStances "222222000000"
ui_openmenu st_feedback_open
wait 60
screenshot_png feedback-akaza-highguard
set ui_stanceHand 1
wait 60
screenshot_png feedback-akaza-left
set ui_stanceMotion 1
wait 135
screenshot_png feedback-akaza-swing
set model jangothefett/default
ui_openmenu st_feedback_open
wait 60
screenshot_png feedback-jango-highguard
set ui_saberStyleSlot1 4
set ui_saberStyleSlot2 5
set ui_saberStyleSlot3 6
ui_openmenu st_hybrid_main
wait 60
screenshot_png feedback-loadout
wait 15
quit
'''
    (mod/'feedback-smoke.cfg').write_text(config,encoding='ascii')
    environment=os.environ.copy();environment['LOCALAPPDATA']=str(folder/'local-app-data')
    (folder/'local-app-data').mkdir()
    args=[str(folder/'bin/openjk.x86_64.exe'),'+set','fs_basepath',str(ROOT.parent),
        '+set','fs_homepath',str(folder/'home'),'+set','fs_game','SaberTrials',
        '+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','1280','+set','r_customheight','800',
        '+set','cl_renderer','rd-'+renderer,'+set','com_maxfps','60','+set','s_initsound','0',
        '+set','com_introplayed','1','+set','logfile','1','+set','developer','1',
        '+set','g_hybridStyles','1','+set','g_stanceLibrary','1','+set','sv_pure','0',
        '+exec','feedback-smoke.cfg']
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    process=subprocess.Popen(args,cwd=folder/'bin',env=environment,startupinfo=startup,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:code=process.wait(timeout=45)
    except subprocess.TimeoutExpired:
        process.kill();process.wait();raise RuntimeError('Menu check timed out; evidence retained: '+str(folder))
    log=(mod/'qconsole.log').read_text(errors='replace')
    expected=('main','saber','akaza-upright','akaza-highguard','akaza-left','akaza-swing','jango-highguard','loadout')
    shots={name:sha(mod/'screenshots'/('feedback-'+name+'.png')) for name in expected
           if (mod/'screenshots'/('feedback-'+name+'.png')).is_file()}
    no_server=not any(word in log for word in ('Server Initialization','InitGame:','SpawnServer:'))
    failures=[line for line in log.splitlines() if 'exceeds the allowed' in line or 'recursive error' in line]
    imported='added compatible stance frames to models/players/_humanoid/akaza_face.gla in memory.' in log
    result=dict(returncode=code,renderer=renderer,files={name:sha(folder/name) for name in files},
        test_driver='Isolated menu onOpen calls production stStanceOpenMain',
        map_or_server_started=not no_server,akaza_frames_imported=imported,screenshots=shots,errors=failures)
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    if code or not no_server or failures or not imported or len(shots)!=len(expected):
        raise RuntimeError('Menu verification failed; inspect '+str(folder/'result.json'))
    print('Production '+renderer+' menus and Akaza compatibility loaded successfully: '+str(folder))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--renderer',choices=('vanilla','rend2'),default='vanilla')
    parser.add_argument('--run',default='01')
    args=parser.parse_args();main(args.renderer,args.run)
