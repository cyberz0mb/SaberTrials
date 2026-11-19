"""Native menu-only interaction checks; never reads/writes personal configs."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/menu-polish-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 global OUT
 p=argparse.ArgumentParser();p.add_argument('--revision',type=int,default=1);p.add_argument('--tag',required=True);p.add_argument('--renderer',default='rd-vanilla');p.add_argument('--height',type=int,default=720);p.add_argument('--production',action='store_true');p.add_argument('--installed',action='store_true');p.add_argument('--profile',action='store_true');p.add_argument('--metadata',action='store_true');a=p.parse_args();assert a.revision>=1;OUT=ROOT/('dist/menu-polish-%02d'%a.revision)
 if a.profile:
  spec=importlib.util.spec_from_file_location('profile_checks',ROOT/'tools/Check-Profile.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.OUT=OUT
  sys.argv=['profile','--tag',a.tag,'--renderer',a.renderer,'--height',str(a.height)]+(['--production'] if a.production else [])+(['--installed'] if a.installed else [])+(['--metadata'] if a.metadata else []);m.main();return
 run=OUT/'verification'/a.tag;assert not run.exists();mod=run/'home/SaberTrials';mod.mkdir(parents=True)
 qa=not a.production and not a.installed
 if not a.installed:shutil.copy2(OUT/('build-qa' if qa else 'build')/'Release/uix86_64.dll',mod/'uix86_64.dll')
 shots=[];lines=['wait 70','set name "Menu Polish QA"','set model kyle/default','ui_openmenu playerMenu','wait 10']
 def cmd(op):lines.extend(['st_profileqa '+op,'wait 4'])
 def shot(n):shots.append(n);lines.extend(['wait 8','screenshot_png polish-'+n,'wait 4'])
 shot('profile')
 if qa:
  cmd('scrollcheck profile');cmd('scrollcheck controls');shot('controls-mouse');cmd('scrollcheck setup');shot('setup');cmd('scrollcheck finish')
  cmd('choose alora/default');cmd('favorite');shot('heart');cmd('favorite');cmd('focusselected');shot('tooltip');cmd('click 501');cmd('ingame');cmd('assertlayout wide');cmd('scrollcheck profile');shot('wide')
 else:
  lines+=['ui_openmenu controlsMenu','wait 12'];shot('controls');lines+=['ui_openmenu setup_menu','wait 12'];shot('setup');lines+=['set ui_menuFilesMP ui/jampingame.txt','ui_load','wait 10','ui_openmenu ingame_player','wait 10'];shot('wide')
 lines+=['wait 30','echo ST_MENU_POLISH_COMPLETE','quit'];(mod/'menu-polish.cfg').write_text('\n'.join(lines)+'\n')
 command=[str(ROOT/'client/SaberTrials.x86_64.exe'),'+safe','+set','fs_basepath',str(ROOT.parent),'+set','fs_homepath',str(run/'home'),'+set','fs_game','SaberTrials','+set','com_unpackLibraries','0','+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','1280','+set','r_customheight',str(a.height),'+set','cl_renderer',a.renderer,'+set','com_maxfps','60','+set','s_initsound','0','+set','logfile','2','+set','com_introplayed','1','+exec','menu-polish.cfg']
 si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0;env=os.environ.copy();env['LOCALAPPDATA']=str(run/'local-app-data')
 proc=subprocess.Popen(command,cwd=ROOT.parent,env=env,startupinfo=si,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);print('Private menu-only interaction check:',a.tag,proc.pid,flush=True)
 try:proc.wait(timeout=100)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait();raise
 log=(mod/'qconsole.log').read_text(errors='replace');errors=[s for s in log.splitlines() if 'ST_PROFILE_FAIL' in s or 'ST_SETUP_FAIL' in s or 'ST_CONTROLS_FAIL' in s]
 assert proc.returncode==0 and 'ST_MENU_POLISH_COMPLETE' in log and not errors,errors or log[-1500:]
 assert 'Server Initialization' not in log and 'SpawnServer' not in log
 assert all((mod/('screenshots/polish-'+name+'.png')).is_file() for name in shots),'Missing completed screenshot'
 if qa:assert all('ST_MENU_SCROLL_CHECK '+name+' completed' in log for name in ('Profile','Controls','Setup')) and log.count('ST_MENU_SCROLL_CHECK Profile completed')==2
 result={'passed':True,'qa':qa,'installed':a.installed,'renderer':a.renderer,'height':a.height,'menu_only':True,'checker_sha256':sha(Path(__file__)),'source_receipt_sha256':sha(OUT/'source-receipt.json'),'ui_sha256':sha((ROOT if a.installed else mod)/'uix86_64.dll'),'log_sha256':sha(mod/'qconsole.log'),'screenshots':len(list(mod.rglob('polish-*.png')))}
 (run/'result.json').write_text(json.dumps(result,indent=2));print('Passed:',result)
if __name__=='__main__':main()
