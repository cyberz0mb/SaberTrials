"""Exercise the native Profile browser using private settings, without a map."""
from pathlib import Path
import argparse, hashlib, json, os, re, shutil, subprocess
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/profile-candidate-01'

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--tag',required=True);parser.add_argument('--production',action='store_true');parser.add_argument('--installed',action='store_true');parser.add_argument('--height',type=int,default=720);parser.add_argument('--renderer',default='rd-vanilla');parser.add_argument('--metadata',action='store_true');args=parser.parse_args()
 run=OUT/'verification'/args.tag;assert not run.exists();mod=run/'home/SaberTrials';mod.mkdir(parents=True)
 if not args.installed:
  shutil.copy2(OUT/('build' if args.production else 'build-qa')/'Release/uix86_64.dll',mod/'uix86_64.dll')
  for source in (OUT/'menus').rglob('*'):
   if source.is_file():target=mod/source.relative_to(OUT/'menus');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
 qa=not args.production and not args.installed
 if qa:
  from profile_png import portrait_fixture
  portrait_fixture(mod/'models/players/alora/profile_test.png')
 if args.metadata:
  for model,text in {'luffy':'displayName=Monkey D. Luffy\nuniverse=One Piece\nthemes=Anime,Fantasy\ngroup=luffy\n','aizen':'x'*4097,'Redja':'displayName=Tagged Redja\nuniverse=Community Test\nthemes=Comics\n'}.items():
   target=mod/'models/players'/model/'st_profile.ini';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
  (mod/'models/players/luffy/sounds.cfg').write_text('jaden_male\nm\n')
 lines=['wait 70','set name "Profile QA"','set model kyle/default','ui_openmenu playerMenu','wait 8']
 def cmd(s):lines.extend(['st_profileqa '+s,'wait 4'])
 def shot(n):lines.extend(['screenshot_png profile-'+n,'wait 4'])
 if qa:cmd('portraitfixture')
 shot('sidebar')
 if qa:
  cmd('assertlayout sidebar');cmd('assertdirty 0');cmd('assertlazyfavorites');cmd('choose luffy/default');cmd('assertlive model kyle/default');cmd('assertpending luffy/default');cmd('assertpreview');cmd('assertvoice '+('0' if args.metadata else '1'));cmd('sample');lines+=['wait 83'];cmd('sample');shot('luffy')
  cmd('search "one piece"');cmd('assertrows 1');cmd('assertpending luffy/default');cmd('focusselected');shot('universe');cmd('collection 1');cmd('assertrows 0');cmd('assertpending luffy/default');shot('empty')
  cmd('click 121');cmd('assertdirty 1');cmd('click 501');cmd('assertpending kyle/default');cmd('assertdirty 0')
  cmd('choose luffy/default');cmd('click 502');cmd('assertlive model luffy/default');cmd('appearance 1');cmd('assertlive model luffy/default');cmd('assertpending luffy/red');shot('red-preview');cmd('click 501');cmd('assertpending luffy/default')
  cmd('choose luffy_wano/default');cmd('appearance 1');cmd('assertpending luffy_wano/red');cmd('click 501')
  cmd('choose akaza/default');lines+=['set model kyle/default','wait 3'];cmd('click 502');cmd('assertstatus outside');cmd('assertlive model kyle/default');cmd('reload');cmd('assertpending kyle/default')
  cmd('choose luffy/default');cmd('click 502');cmd('click 510');cmd('assertmenu saberMenu');lines+=['ui_openmenu playerMenu','wait 8']
  cmd('ingame');cmd('assertlayout wide');cmd('assertlive model luffy/default');shot('wide');cmd('search "Bleach"');cmd('assertrows 1');cmd('choose aizen/default');cmd('assertlive model luffy/default');shot('wide-search');cmd('click 501');cmd('assertpending luffy/default')
  cmd('assertactions');cmd('forceparity');cmd('state')
  cmd('choose luffy/default');cmd('assertpreview');cmd('previewmissing');cmd('assertunavailable');cmd('choose luffy/default');cmd('assertpreview')
  cmd('previewskinmissing');cmd('assertunavailable');cmd('choose luffy/default');cmd('assertpreview')
  cmd('click 121');cmd('choose akaza/default');cmd('favorite');cmd('assertfavorite 1');cmd('reload');cmd('choose akaza/default');cmd('assertfavorite 1');cmd('favorite');cmd('assertfavorite 0')
  cmd('click 501');cmd('click 101');cmd('text "Edited Profile"');cmd('assertlive name "Profile QA"');cmd('click 502');cmd('assertlive name "Edited Profile"')
  lines+=['set model "jedi_hm/head_a1|torso_a1|lower_a1"','wait 4'];cmd('reload');cmd('click 101');cmd('text "Composite Profile"');cmd('click 502');cmd('assertlive model "jedi_hm/head_a1|torso_a1|lower_a1"')
  if args.metadata:
   cmd('choose aizen/default');cmd('assertuniverse Bleach');cmd('search "Community Test"');cmd('assertrows 1');cmd('choose Redja/default');cmd('asserttitle "Tagged Redja"');cmd('focusselected');shot('metadata')
 else:
  lines+=['set ui_menuFilesMP ui/jampingame.txt','ui_load','wait 10','ui_openmenu ingame_player','wait 10'];shot('wide')
 lines+=['wait 8','echo ST_PROFILE_COMPLETE','quit']
 (mod/'profile-qa.cfg').write_text('\n'.join(lines)+'\n')
 command=[str(ROOT/'client/SaberTrials.x86_64.exe'),'+safe','+set','fs_basepath',str(ROOT.parent),'+set','fs_homepath',str(run/'home'),'+set','fs_game','SaberTrials','+set','com_unpackLibraries','0','+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','1280','+set','r_customheight',str(args.height),'+set','cl_renderer',args.renderer,'+set','s_initsound','0','+set','com_maxfps','60','+set','logfile','2','+set','com_introplayed','1','+exec','profile-qa.cfg']
 si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0;env=os.environ.copy();env['LOCALAPPDATA']=str(run/'local-app-data')
 proc=subprocess.Popen(command,cwd=ROOT.parent,env=env,startupinfo=si,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);print('Private menu-only Profile check:',args.tag,proc.pid,flush=True)
 try:proc.wait(timeout=100)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait();raise
 log=(mod/'qconsole.log').read_text(errors='replace');fail=[line for line in log.splitlines() if 'ST_PROFILE_FAIL' in line or 'Unknown command "st_profileqa' in line]
 if qa:
  from profile_png import portrait_proportions
  for name,wide in [('sidebar',False),('wide',True)]:
   try:portrait_proportions(mod/('screenshots/profile-'+name+'.png'),wide)
   except AssertionError as error:fail.append(str(error))
 assert proc.returncode==0 and 'ST_PROFILE_COMPLETE' in log and not fail,fail or log[-2000:]
 assert 'Server Initialization' not in log and 'SpawnServer' not in log
 from profile_png import clean_background
 clean_background(mod/'screenshots/profile-wide.png')
 if qa:
  samples=re.findall(r'ST_PROFILE_ANIM frame=([\d.]+) yaw=([\d.]+) loop=(\d+)',log)
  assert len(samples)==2 and samples[0][0]!=samples[1][0] and samples[0][1]!=samples[1][1] and all(s[2]=='1' for s in samples),samples
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 result={'passed':True,'qa':qa,'renderer':args.renderer,'height':args.height,'menu_only':True,'installed':args.installed,'metadata':args.metadata,'screenshots':len(list(mod.rglob('profile-*.png'))),'ui_sha256':sha((ROOT if args.installed else mod)/'uix86_64.dll'),'engine_sha256':sha(ROOT/'client/SaberTrials.x86_64.exe'),'log_sha256':sha(mod/'qconsole.log'),'checker_sha256':sha(Path(__file__)),'source_receipt_sha256':sha(OUT/'source-receipt.json')}
 (run/'result.json').write_text(json.dumps(result,indent=2));print('Passed:',result)
if __name__=='__main__':main()
