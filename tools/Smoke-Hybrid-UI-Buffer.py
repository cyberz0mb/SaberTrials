"""Open production menus in an isolated home, capture evidence, quit. No map/server."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
FIX=ROOT/'dist/hybrid-ui-buffer-fix'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main(renderer):
 folder=FIX/'qa'/('startup-'+renderer)
 if folder.exists():raise RuntimeError('Preserve previous startup evidence; choose a fresh run')
 mod=folder/'home/SaberTrials';mod.mkdir(parents=True)
 files={}
 for name in ('SaberTrials.x86_64.exe','rd-vanilla_x86_64.dll','rd-rend2_x86_64.dll','SDL2.dll','OpenAL32.dll'):
  files['bin/'+name]=ROOT/'client'/name
 files['home/SaberTrials/uix86_64.dll']=FIX/'build/Release/uix86_64.dll'
 for name,source in files.items():
  dst=folder/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dst)
 cfg='''wait 60
screenshot_png ui-buffer-main
ui_openmenu saberMenu
wait 60
screenshot_png ui-buffer-saber
set ui_saberStyleSlot1 4
set ui_saberStyleSlot2 5
set ui_saberStyleSlot3 6
ui_openmenu st_hybrid_main
wait 60
screenshot_png ui-buffer-loadout
wait 10
quit
'''
 (mod/'ui-buffer-smoke.cfg').write_text(cfg,encoding='ascii')
 environment=os.environ.copy();environment['LOCALAPPDATA']=str(folder/'local-app-data')
 (folder/'local-app-data').mkdir()
 args=[str(folder/'bin/SaberTrials.x86_64.exe'),'+set','fs_basepath',str(ROOT.parent),
  '+set','fs_homepath',str(folder/'home'),'+set','fs_game','SaberTrials',
  '+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','1280','+set','r_customheight','800',
  '+set','cl_renderer','rd-'+renderer,'+set','com_maxfps','60','+set','s_initsound','0',
  '+set','com_introplayed','1','+set','logfile','1','+set','g_hybridStyles','1','+set','g_stanceLibrary','1',
  '+set','sv_pure','0','+exec','ui-buffer-smoke.cfg']
 startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
 proc=subprocess.Popen(args,cwd=folder/'bin',env=environment,startupinfo=startup,
  stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:code=proc.wait(timeout=45)
 except subprocess.TimeoutExpired:
  proc.kill();proc.wait();raise RuntimeError('Menu startup did not finish; evidence preserved at '+str(folder))
 log=(mod/'qconsole.log').read_text(errors='replace')
 required=['ui-buffer-main.png','ui-buffer-saber.png','ui-buffer-loadout.png']
 shots={name:sha(mod/'screenshots'/name) for name in required if (mod/'screenshots'/name).is_file()}
 no_server=not any(word in log for word in ('------ Server Initialization ------','------ Server Initialization -----','InitGame:','SpawnServer:'))
 failures=[line for line in log.splitlines() if 'exceeds the allowed' in line or 'recursive error' in line]
 result=dict(returncode=code,renderer=renderer,map_or_server_started=not no_server,
  files={name:sha(folder/name) for name in files},screenshots=shots,errors=failures)
 (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 if code or not no_server or failures or len(shots)!=3:raise RuntimeError('Startup verification failed: '+str(result))
 print('Production '+renderer+' menu startup/captures/exit passed; no map or server. Evidence: '+str(folder))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--renderer',choices=['vanilla','rend2'],default='vanilla');a=p.parse_args();main(a.renderer)
