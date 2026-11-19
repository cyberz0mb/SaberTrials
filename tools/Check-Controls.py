"""Exercise the real Controls event handlers in a private menu-only run."""
from pathlib import Path
import argparse,json,os,shutil,subprocess,time
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/controls-candidate-01'
MOD='SaberTrialsControlsTest'
def main():
 p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--height',type=int,default=720);p.add_argument('--production',action='store_true');p.add_argument('--regression',choices=['capture','slider','page','range','write','layout']);a=p.parse_args()
 run=OUT/'verification'/a.tag;assert not run.exists();mod=run/'home'/MOD;mod.mkdir(parents=True)
 for f in (OUT/'playable/home'/MOD).iterdir():
  if f.suffix in ('.pk3','.dll'):shutil.copy2(f,mod/f.name)
 shutil.copy2(OUT/('build-frontend' if a.production else 'build-frontend-qa')/'Release/uix86_64.dll',mod/'uix86_64.dll')
 lines=['wait 60','exec mpdefault.cfg','bind F "vstr custom_alias; say preserved"','seta custom_alias "echo SHOULD_NOT_EXECUTE"','bind H +forward','bind J +forward','ui_openmenu controlsMenu','wait 8']
 def click(n):lines.extend([f'st_controlsqa click {n}','wait 3'])
 def text(t):lines.extend([f'st_controlsqa text "{t}"','wait 2'])
 def state():lines.append('st_controlsqa state')
 def shot(n):lines.extend(['wait 8','screenshot_png controls-'+n,'wait 5'])
 shot('bindings')
 if not a.production and not a.regression:
  click(500);lines+=['st_controlsqa key 83'];state();shot('conflict');click(1701);state();click(1301)
  click(101);shot('bindlist');click(10);text('custom_alias');shot('custom');click(900);shot('command');click(1401)
  click(102);shot('server');click(500);click(1400);state()
  click(103);shot('mouse');click(1900);shot('mouse-expanded');click(1921);click(1921);click(1921);shot('mouse-scrolled');click(1920);click(1920);click(1920);click(1900);click(600);text('7.25');click(1302);state();lines.append('sensitivity')
  click(104);shot('controller');click(601);shot('slider');click(411);shot('buttons');click(1100);shot('choose');click(1401)
  click(105);click(10);text('cl_yawspeed');shot('advanced');click(600);text('225');click(1302);state();lines.append('cl_yawspeed')
  click(106);click(12);text('AAA Menu QA');click(400);state();shot('configs');click(400);state();shot('overwrite');click(1401)
  click(103);click(600);text('3');click(106);click(1000);state();shot('load-confirm');click(1700);state();click(1302);lines+=['sensitivity','cl_yawspeed','bindlist'];state()
  lines+=['st_controlsqa assertvar sensitivity 7.25','st_controlsqa assertvar cl_yawspeed 225','st_controlsqa assertbind 70 "vstr custom_alias; say preserved"','st_controlsqa assertbind 72 +forward','st_controlsqa assertbind 74 +forward','st_controlsqa ingame','wait 12'];shot('ingame-route');state()
 if a.regression=='layout':
  lines+=['st_controlsqa assertrows Mouse 12','st_controlsqa assertrows Advanced 7']
  click(101);lines+=['st_controlsqa asserthit 919 1'];click(1201);click(919);lines+=['st_controlsqa asserthit 1602 1'];click(1401)
  click(104);lines+=['st_controlsqa asserthit 1900 0','st_controlsqa asserthit 1901 0'];shot('controller-settings');click(411);lines+=['st_controlsqa asserthit 1117 1']
  click(103);lines+=['st_controlsqa asserthit 604 0'];click(1900);lines+=['st_controlsqa asserthit 604 1'];lines+=['st_controlskey MWHEELDOWN','wait 3','st_controlskey MWHEELDOWN','wait 3','st_controlskey MWHEELDOWN','wait 3'];lines+=['st_controlsqa asserthit 612 1','st_controlsqa asserthit 1302 1'];click(612);text('-0.03');click(1302);lines+=['st_controlsqa assertvar m_pitch -0.03'];shot('mouse-bottom')
  click(1920);click(1920);click(1920);click(602);click(1302);lines+=['st_controlsqa assertvar m_pitch 0.03'];click(1900);lines+=['st_controlsqa asserthit 604 0'];shot('mouse-basic')
  click(105);lines+=['st_controlsqa asserthit 1900 0','st_controlsqa asserthit 1901 0','st_controlsqa asserthit 606 1'];shot('advanced-clean')
 if a.regression=='capture':
  lines+=['bind JOY6 togglemenu','wait 3'];click(500);lines+=['st_controlskey JOY6','wait 5','st_controlsqa assertmenu','st_controlsqa assertstatus staged'];state()
 if a.regression=='slider':
  click(104);lines+=['st_controlsqa focus 601','st_controlskey RIGHTARROW','wait 3'];click(1302);lines+=['st_controlsqa assertvar st_controllerHorizontal 5.25'];state()
 if a.regression=='page':
  click(104);click(411);click(1100)
  for _ in range(4):click(1201)
  lines+=['st_controlsqa assertpage 4'];state()
 if a.regression=='range':
  (mod/'000 Range.cfg').write_text('bind H +back\nseta r_picmip 99\n')
  click(106);click(1000);state();lines+=['st_controlsqa assertstatus r_picmip'];click(1302);lines+=['st_controlsqa assertbind 72 +forward','st_controlsqa assertvar r_picmip 0']
 if a.regression=='write':
  locked=mod/'ZZ Locked.cfg';locked.write_text('// protected fixture\n');os.chmod(locked,0o444)
  click(106);click(12);text('ZZ Locked');click(400);click(1700);lines+=['st_controlsqa assertstatus retained'];state()
 lines+=['echo ST_CONTROLS_COMPLETE','quit']
 chunks=[[]]
 for line in lines:
  if line.startswith('st_controlskey '):
   chunks[-1].append(line+' controls-step'+str(len(chunks))+'.cfg');chunks.append([])
  else:chunks[-1].append(line)
 for i,chunk in enumerate(chunks):(mod/('controls-qa.cfg' if i==0 else 'controls-step'+str(i)+'.cfg')).write_text('\n'.join(chunk)+'\n')
 exe=OUT/'playable/bin/SaberTrials.x86_64.exe'
 if a.regression:
  private_bin=run/'bin';private_bin.mkdir()
  for f in (OUT/'playable/bin').glob('*.dll'):shutil.copy2(f,private_bin/f.name)
  exe=private_bin/'SaberTrials.x86_64.exe';shutil.copy2(OUT/'build-engine-qa/Release/openjk.x86_64.exe',exe)
 args=[str(exe),'+safe','+set','fs_basepath',str(ROOT.parent),'+set','fs_homepath',str(run/'home'),'+set','fs_game',MOD,'+set','fs_forcegame',MOD,'+set','com_unpackLibraries','0','+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','1280','+set','r_customheight',str(a.height),'+set','cl_renderer','rd-vanilla','+set','s_initsound','0','+set','com_maxfps','60','+set','logfile','2','+set','com_introplayed','1','+exec','controls-qa.cfg']
 si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
 env=os.environ.copy();env['LOCALAPPDATA']=str(run/'local-app-data')
 proc=subprocess.Popen(args,cwd=OUT/'playable/bin',env=env,startupinfo=si,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 (run/'process.json').write_text(json.dumps({'pid':proc.pid,'menu_only':True}))
 print('Menu-only verification running:',proc.pid,flush=True)
 try:proc.wait(timeout=100)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait();raise
 log=(mod/'qconsole.log').read_text(errors='replace')
 assert 'ST_CONTROLS_COMPLETE' in log and 'ST_CONTROLS_FAIL' not in log,log[-2500:]
 assert 'SpawnServer' not in log and 'Server Initialization' not in log
 assert 'Unknown command "st_controlsqa' not in log
 assert a.production or a.regression or 'menu=ingame_controls tab=0' in log, 'In-game Controls route did not open'
 assert 'Only bind,' not in log and 'Setting is protected:' not in log, log[-6000:]
 if a.regression=='write':assert (mod/'ZZ Locked.cfg').read_text()=='// protected fixture\n'
 print('Completed; screenshots:',len(list(mod.rglob('*.png'))))
 if not a.production:
  for line in log.splitlines():
   if 'ST_CONTROLS_QA' in line or line.startswith('"sensitivity"') or line.startswith('"cl_yawspeed"'):print(line)
if __name__=='__main__':main()
