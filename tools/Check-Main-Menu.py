"""Native main-menu appearance, motion and navigation checks in a private profile."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/main-menu-01';PACKAGE='zzzzzzzz_sabertrials_main.pk3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--renderer',default='rd-vanilla');p.add_argument('--height',type=int,default=720);p.add_argument('--production',action='store_true');p.add_argument('--installed',action='store_true');a=p.parse_args()
 run=OUT/'verification'/a.tag;assert not run.exists();mod=run/'home/SaberTrials';mod.mkdir(parents=True);qa=not a.production and not a.installed
 if not a.installed:
  shutil.copy2(OUT/('build-qa' if qa else 'build')/'Release/uix86_64.dll',mod/'uix86_64.dll');shutil.copy2(OUT/PACKAGE,mod/PACKAGE)
 shots=[];lines=['wait 70','set st_menuMotion 0','set name "Main Menu QA"','set model kyle/default','ui_openmenu main','wait 10']
 def cmd(s):lines.extend(['st_mainqa '+s,'wait 4'])
 def shot(n):shots.append(n);lines.extend(['wait 8','screenshot_png main-'+n,'wait 4'])
 shot('static')
 if qa:
  cmd('assertroot');cmd('focus account_link');cmd('next');shot('motion-focus');cmd('focus play');cmd('assertmotion 0');cmd('sample');lines+=['wait 35'];cmd('sample')
  cmd('focus profile');cmd('assertfocus profile');shot('hover-profile');cmd('click profile');cmd('assertmenu playerMenu');shot('profile');lines+=['st_profileqa click 500','wait 8'];cmd('assertroot')
  cmd('focus play');cmd('next');cmd('next');cmd('assertfocus controls');cmd('controller');cmd('assertmenu controlsMenu');lines+=['st_controlsqa click 1300','wait 8'];cmd('assertroot')
  cmd('click setup');cmd('assertmenu setup_menu');lines+=['st_setupqa click 2900','wait 8'];cmd('assertroot')
  cmd('click play');cmd('assertmenu multiplayermenu');cmd('click back');cmd('assertroot')
  cmd('click account_link');cmd('assertmenu st_main_account');shot('account');cmd('click back');cmd('assertroot')
  cmd('click exit');cmd('assertmenu st_main_exit');shot('exit');cmd('click back');cmd('assertroot')
  cmd('click motion');cmd('assertmotion 1');cmd('sample');shot('motion');lines+=['wait 45'];cmd('sample');shot('motion-later')
  cmd('click motion');cmd('assertmotion 0');shot('motion-off')
 else:
  lines+=['set st_menuMotion 1','ui_openmenu main','wait 10'];shot('motion')
 lines+=['wait 30','echo ST_MAIN_COMPLETE','quit'];(mod/'main-check.cfg').write_text('\n'.join(lines)+'\n')
 command=[str(ROOT/'client/SaberTrials.x86_64.exe'),'+safe','+set','fs_basepath',str(ROOT.parent),'+set','fs_homepath',str(run/'home'),'+set','fs_game','SaberTrials','+set','com_unpackLibraries','0','+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','1280','+set','r_customheight',str(a.height),'+set','cl_renderer',a.renderer,'+set','com_maxfps','60','+set','s_initsound','0','+set','logfile','2','+set','com_introplayed','1','+exec','main-check.cfg']
 si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0;env=os.environ.copy();env['LOCALAPPDATA']=str(run/'local-app-data')
 proc=subprocess.Popen(command,cwd=ROOT.parent,env=env,startupinfo=si,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);print('Private main-menu check:',a.tag,proc.pid,flush=True)
 try:proc.wait(timeout=100)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait();raise
 log=(mod/'qconsole.log').read_text(errors='replace');errors=[line for line in log.splitlines() if 'ST_MAIN_FAIL' in line or 'Unknown command "st_mainqa' in line]
 assert proc.returncode==0 and 'ST_MAIN_COMPLETE' in log and not errors,errors or log[-1500:]
 assert 'Server Initialization' not in log and 'SpawnServer' not in log
 assert all((mod/('screenshots/main-'+n+'.png')).is_file() for n in shots),'Missing screenshot'
 if qa:
  samples=re.findall(r'ST_MAIN_ANIM motion=(\d) heads=(\d+) x=([\d.-]+) y=([\d.-]+)',log)
  assert len(samples)==4 and samples[0][0]==samples[1][0]=='0' and samples[0][1]==samples[1][1]=='0' and samples[2][0]==samples[3][0]=='1' and samples[2][2:]!=samples[3][2:],samples
 if qa:
  from profile_png import read
  width,height,pixel_a=read(mod/'screenshots/main-motion.png');_,_,pixel_b=read(mod/'screenshots/main-motion-later.png')
  points=[(x,y) for y in range(3,int(height*.08),2) for x in range(6,width-6,2)]
  points += [(x,y) for y in range(int(height*.88),height-5,2) for x in range(6,width-6,2)]
  points += [(x,y) for x in (12,18,width-18,width-12) for y in range(30,height-30,2)]
  changed=sum(1 for x,y in points if max(abs(c-d) for c,d in zip(pixel_a(x,y),pixel_b(x,y)))>12)
  assert changed>15,('No visible traveling frame lights',changed)
  _,_,focused=read(mod/'screenshots/main-motion-focus.png')
  gold=sum(1 for y in range(int(height*443/480),int(height*457/480)) for x in range(int(width*524/640),int(width*612/640)) if focused(x,y)[0]>140 and focused(x,y)[1]>80 and focused(x,y)[2]<140)
  assert gold>10,('Motion control has no visible keyboard focus',gold)
 result={'passed':True,'qa':qa,'installed':a.installed,'renderer':a.renderer,'height':a.height,'menu_only':True,'checker_sha256':sha(Path(__file__)),'source_receipt_sha256':sha(OUT/'source-receipt.json'),'ui_sha256':sha((ROOT if a.installed else mod)/'uix86_64.dll'),'log_sha256':sha(mod/'qconsole.log'),'screenshots':len(shots)}
 (run/'result.json').write_text(json.dumps(result,indent=2));print('Passed:',result)
if __name__=='__main__':main()
