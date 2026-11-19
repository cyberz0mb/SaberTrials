"""Capture and exercise the rich menus using isolated settings and UI-only files."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/rich-menus-01';PACKAGE='zzzzzzzzz_sabertrials_rich.pk3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--renderer',default='rd-vanilla');p.add_argument('--height',type=int,default=720);p.add_argument('--production',action='store_true');p.add_argument('--installed',action='store_true');p.add_argument('--live',action='store_true');a=p.parse_args()
 run=OUT/'verification'/a.tag;assert not run.exists();mod=run/'home/SaberTrials';mod.mkdir(parents=True);qa=not a.production and not a.installed
 receipt=json.loads((OUT/'source-receipt.json').read_text());receipt_sha=sha(OUT/'source-receipt.json')
 record=json.loads((OUT/('build-record-qa.json' if qa else 'build-record.json')).read_text())
 selected=(ROOT if a.installed else OUT/('build-qa' if qa else 'build')/'Release')/'uix86_64.dll'
 assert record['source_receipt_sha256']==receipt_sha and record['ui_sha256']==sha(selected),'Stale build; rebuild this candidate before checking it'
 assert sha((ROOT if a.installed else OUT)/PACKAGE)==receipt['package_sha256'],'Candidate package drift'
 if not a.installed:
  shutil.copy2(OUT/('build-qa' if qa else 'build')/'Release/uix86_64.dll',mod/'uix86_64.dll');shutil.copy2(OUT/PACKAGE,mod/PACKAGE)
 lines=['wait 70','set st_menuMotion 1','set name "Menu Review"','set model kyle/default','set sensitivity 5','set s_volume 0.8','set st_controllerHorizontal 5','unbind F12','ui_openmenu main','wait 10'];shots=[]
 def shot(name):shots.append(name);lines.extend(['wait 8','screenshot_png rich-'+name,'wait 4'])
 def cmd(name,op):lines.extend(['st_'+name+'qa '+op,'wait 4'])
 shot('main')
 if qa:
  cmd('main','click profile');cmd('profile','assertlayout sidebar');cmd('profile','assertdirty 0');shot('profile')
  cmd('profile','scrollcheck profile');cmd('profile','scrollcheck controls');shot('mouse-advanced');cmd('profile','scrollcheck setup');shot('setup-scrolled');cmd('profile','scrollcheck finish')
  cmd('profile','choose alora/default');cmd('profile','favorite');shot('favorite');cmd('profile','favorite');cmd('profile','click 501');cmd('profile','click 500')
  cmd('main','click controls');cmd('controls','assertmenu');shot('controls');cmd('controls','click 103');shot('mouse-basic');cmd('controls','click 1900');shot('mouse-expanded');cmd('controls','click 104');shot('controller');cmd('controls','click 105');shot('advanced');cmd('controls','click 1300')
  cmd('main','click setup');shot('setup');cmd('setup','click 2001');shot('sound');cmd('setup','click 2002');shot('interface');cmd('setup','click 2004');shot('network');cmd('setup','click 2900')
  # Real field editing, staging, cancellation, apply, keyboard focus and sliders.
  cmd('main','click controls');cmd('controls','click 103');cmd('controls','click 600');cmd('controls','text "6.25"');cmd('controls','click 1302');cmd('controls','assertvar sensitivity 6.25')
  cmd('controls','click 600');cmd('controls','text "7"');cmd('controls','click 1301');cmd('controls','assertvar sensitivity 6.25')
  cmd('controls','click 104');cmd('controls','focus 601');cmd('controls','key 173');cmd('controls','click 1302');cmd('controls','assertvar st_controllerHorizontal 5.25')
  cmd('controls','click 100');cmd('controls','click 500');cmd('controls','key 152');cmd('controls','assertbind 152 ""');cmd('controls','click 1302');cmd('controls','assertbind 152 +forward');cmd('controls','click 1300')
  cmd('main','click setup');cmd('setup','click 2001');cmd('setup','set s_volume 0.35');cmd('setup','assertvar s_volume 0.8');cmd('setup','assertdirty 1');cmd('setup','click 2901');cmd('setup','assertdirty 0')
  cmd('setup','set s_volume 0.25');cmd('setup','click 2902');cmd('setup','assertvar s_volume 0.25');cmd('setup','click 2900')
  cmd('main','click motion');cmd('main','assertmotion 0');shot('motion-off');cmd('main','click motion');cmd('main','assertmotion 1');cmd('main','sample');shot('motion-a');lines+=['wait 45'];cmd('main','sample');shot('motion-b')
 else:
  lines+=['ui_openmenu playerMenu','wait 10'];shot('profile');lines+=['ui_openmenu controlsMenu','wait 10'];shot('controls');lines+=['ui_openmenu setup_menu','wait 10'];shot('setup')
 if a.live:
  lines+=['closemenus','set g_gametype 0','set sv_maxclients 1','set g_warmup 0','devmap mp/ffa3','wait 150','team spectator','wait 45','ui_openmenu ingame_setup','wait 15'];shot('live-setup')
  lines+=['ui_openmenu ingame_controls','wait 15'];shot('live-controls');lines+=['ui_openmenu ingame_player','wait 15'];shot('live-profile')
 else:
  if qa:cmd('profile','ingame');cmd('profile','assertlayout wide')
  else:lines+=['set ui_menuFilesMP ui/jampingame.txt','ui_load','wait 10','ui_openmenu ingame_player','wait 10']
  shot('wide')
 lines+=['wait 20','echo ST_RICH_COMPLETE','quit'];(mod/'rich-check.cfg').write_text('\n'.join(lines)+'\n')
 command=[str(ROOT/'client/SaberTrials.x86_64.exe'),'+safe','+set','fs_basepath',str(ROOT.parent),'+set','fs_homepath',str(run/'home'),'+set','fs_game','SaberTrials','+set','com_unpackLibraries','0','+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','1280','+set','r_customheight',str(a.height),'+set','cl_renderer',a.renderer,'+set','com_maxfps','60','+set','s_initsound','0','+set','logfile','2','+set','com_introplayed','1','+exec','rich-check.cfg']
 si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0;env=os.environ.copy();env['LOCALAPPDATA']=str(run/'local-app-data')
 proc=subprocess.Popen(command,cwd=ROOT.parent,env=env,startupinfo=si,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);print('Checking rich native menus:',a.tag,proc.pid,flush=True)
 try:proc.wait(timeout=140)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait();raise
 log=(mod/'qconsole.log').read_text(errors='replace');errors=[s for s in log.splitlines() if any(x in s for x in ('ST_PROFILE_FAIL','ST_CONTROLS_FAIL','ST_SETUP_FAIL','ST_MAIN_FAIL','Unknown command "st_','ERROR: Could not'))]
 assert proc.returncode==0 and 'ST_RICH_COMPLETE' in log and not errors,errors or log[-2500:]
 assert all((mod/('screenshots/rich-'+n+'.png')).is_file() for n in shots),'Missing completed screenshot'
 if not a.live:assert 'Server Initialization' not in log and 'SpawnServer' not in log
 if qa:assert all('ST_MENU_SCROLL_CHECK '+n+' completed' in log for n in ('Profile','Controls','Setup'))
 assert sha(OUT/'source-receipt.json')==receipt_sha,'Sources changed during verification'
 result={'passed':True,'qa':qa,'installed':a.installed,'live':a.live,'renderer':a.renderer,'height':a.height,'source_receipt_sha256':receipt_sha,'checker_sha256':sha(Path(__file__)),'ui_sha256':sha((ROOT if a.installed else mod)/'uix86_64.dll'),'package_sha256':sha((ROOT if a.installed else mod)/PACKAGE),'log_sha256':sha(mod/'qconsole.log'),'screenshots':shots}
 (run/'result.json').write_text(json.dumps(result,indent=2));print('Passed',a.tag,len(shots),'screenshots',flush=True)
if __name__=='__main__':main()
