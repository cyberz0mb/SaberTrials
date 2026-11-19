"""Exercise the native Setup handlers in a private menu-only profile."""
from pathlib import Path
import argparse,json,os,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/setup-candidate-01';MOD='SaberTrialsSetupTest'
def main():
 p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--height',type=int,default=720);p.add_argument('--production',action='store_true');p.add_argument('--renderer',default='rd-vanilla');p.add_argument('--case',choices=['menu','display','timeout','keep','recovery','recovery-write','import','editing','pause'],default='menu');a=p.parse_args()
 run=OUT/'verification'/a.tag;assert not run.exists();mod=run/'home'/MOD;mod.mkdir(parents=True)
 for f in (OUT/'playable/home'/MOD).iterdir():
  if f.suffix in ('.pk3','.dll'):shutil.copy2(f,mod/f.name)
 variant='' if a.production else '-qa'
 for n in ('uix86_64.dll','cgamex86_64.dll'):shutil.copy2(OUT/f'build-frontend{variant}/Release'/n,mod/n)
 bindir=run/'bin';bindir.mkdir()
 for f in (OUT/'playable/bin').glob('*.dll'):shutil.copy2(f,bindir/f.name)
 exe=bindir/'SaberTrials.x86_64.exe';shutil.copy2(OUT/f'build-engine{variant}/Release/openjk.x86_64.exe',exe)
 lines=['wait 60','exec mpdefault.cfg','set s_volume 0.8','bind F "vstr custom_alias; say preserved"','bind H +forward','bind J +forward','ui_openmenu setup_menu','wait 10']
 def click(n):lines.extend([f'st_setupqa click {n}','wait 4'])
 def cmd(s):lines.extend(['st_setupqa '+s,'wait 3'])
 def shot(n):lines.extend(['wait 6','screenshot_png setup-'+n,'wait 3'])
 shot('video')
 if not a.production and a.case=='pause':
  cmd('pause');shot('pause-rail');cmd('pauseclick controls');cmd('assertmenu ingame_controls');shot('pause-controls');lines+=['st_controlsqa click 1300','wait 6'];cmd('assertmenu ingame');cmd('pauseclick setup');cmd('assertmenu ingame_setup');shot('pause-setup');click(2900);cmd('assertmenu ingame');shot('pause-back')
 if not a.production and a.case in ('recovery','recovery-write'):cmd('assertvar r_customwidth 1280')
 if not a.production and a.case=='import':
  (mod/'000 Rend2.cfg').write_text('seta cl_renderer rd-rend2\nseta r_hdr 1\n')
  click(2904);click(3000);click(2902);lines+=['wait 60'];click(3201);cmd('assertvar cl_renderer rd-rend2');cmd('assertvar r_hdr 1')
 if not a.production and a.case=='editing':
  catalog=json.loads((ROOT/'development-source/setup/catalog.json').read_text());fps=next(i for i,r in enumerate(catalog) if r['name']=='com_maxfps')
  click(2004);click(2200+fps);cmd('text "144"');click(2100);cmd('assertdirty 1');click(2902);cmd('assertvar com_maxfps 144')
  click(2200+fps);cmd('text "-10"');click(2100);cmd('assertstatus unsupported');cmd('assertdirty 0');click(2901);cmd('assertdirty 0');cmd('assertvar com_maxfps 144')
 if not a.production and a.case=='menu':
  cmd('assertdirty 0');click(2004);shot('network');cmd('set cl_timeNudge -12');cmd('set com_maxfps 125');cmd('assertvar cl_timeNudge 0');cmd('assertdirty 1');click(2001);shot('sound');cmd('set s_volume 0.35');click(2901);cmd('assertdirty 0');cmd('assertvar cl_timeNudge 0')
  cmd('set s_volume NaN');cmd('assertstatus unsupported');click(2901)
  cmd('set s_volume 0.25');cmd('set rate 26000');lines+=['set rate 27000','wait 3'];click(2902);cmd('assertstatus outside');cmd('assertvar rate 27000');cmd('assertvar s_volume 0.8');click(2901)
  click(2004);cmd('set cl_timeNudge -12');cmd('set com_maxfps 125');click(2902);cmd('assertvar cl_timeNudge -12');cmd('assertvar com_maxfps 125')
  click(2002);shot('interface');click(2100);cmd('text "radar"');shot('search');click(2600+next(i for i,r in enumerate(json.loads((ROOT/'development-source/setup/catalog.json').read_text())) if r['name']=='cg_drawRadar'));cmd('asserttab 2');shot('search-jump')
  click(2003);shot('game');click(2005);shot('recording');cmd('set cg_draw2D 0');cmd('set st_streamerMode 1');cmd('assertstatus Clean');click(2902);cmd('assertvar cg_draw2D 0');shot('capture');click(2901)
  click(2904);click(2102);cmd('text "AAA Setup QA"');click(3100);shot('configs');click(2900);click(2004);cmd('set cl_timeNudge 0');click(2902);click(2904);click(3000);shot('config-loaded');click(2902);cmd('assertvar cl_timeNudge -12');cmd('assertvar com_maxfps 125');cmd('assertvar cg_draw2D 0')
  click(2900);click(2004);click(2903);shot('reset-confirm');click(3201);cmd('assertdirty 1');click(2901);cmd('assertvar cl_timeNudge -12')
  click(3302);lines+=['wait 8','st_controlsqa click 106','wait 8'];cmd('assertmanager 1');shot('controls-shortcut');cmd('state')
  click(2900);cmd('ingame');shot('ingame');cmd('state')
 if not a.production and a.case in ('display','timeout','keep'):
  cmd('set r_mode -1');cmd('set r_customwidth 1024');click(2902);lines+=['wait 60'];shot('display-confirm')
  if a.case=='display':click(3202);lines+=['wait 60'];cmd('assertvar r_customwidth 1280')
  elif a.case=='keep':click(3201);cmd('assertvar r_customwidth 1024')
  else:lines+=['wait 3000'];cmd('assertvar r_customwidth 1280')
  shot('display-result')
 lines+=['wait 60','echo ST_SETUP_COMPLETE','quit']
 if a.case in ('recovery','recovery-write'):
  (mod/'_st_setup_display_recovery.cfg').write_text('// SaberTrials personal config v1\nunbindall\nseta cl_renderer rd-vanilla\nseta r_mode -1\nseta r_customwidth 1280\nseta r_customheight 720\nseta r_fullscreen 0\n')
  if a.case=='recovery-write':
   config=mod/'openjk.cfg';config.write_text('seta r_customwidth 1024\n');os.chmod(config,0o444)
 chunks=[[]]
 for line in lines:
  chunks[-1].append(line)
  if line in ('st_setupqa click 2902','st_setupqa click 3202'):
   chunks[-1].append('st_setupqa continue setup-step'+str(len(chunks))+'.cfg');chunks.append([])
 for i,chunk in enumerate(chunks):(mod/('setup-qa.cfg' if i==0 else 'setup-step'+str(i)+'.cfg')).write_text('\n'.join(chunk)+'\n')
 args=[str(exe),'+safe','+set','fs_basepath',str(ROOT.parent),'+set','fs_homepath',str(run/'home'),'+set','fs_game',MOD,'+set','fs_forcegame',MOD,'+set','com_unpackLibraries','0','+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','1024' if a.case in ('recovery','recovery-write') else '1280','+set','r_customheight',str(a.height),'+set','cl_renderer',a.renderer,'+set','s_initsound','0','+set','com_maxfps','60','+set','logfile','2','+set','com_introplayed','1','+exec','setup-qa.cfg']
 si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0;env=os.environ.copy();env['LOCALAPPDATA']=str(run/'local-app-data')
 proc=subprocess.Popen(args,cwd=bindir,env=env,startupinfo=si,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);(run/'process.json').write_text(json.dumps({'pid':proc.pid,'menu_only':True}));print('Menu-only Setup check:',a.tag,proc.pid,flush=True)
 try:proc.wait(timeout=100)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait();raise
 log=(mod/'qconsole.log').read_text(errors='replace');failures=[l for l in log.splitlines() if 'ST_SETUP_FAIL' in l or 'Unknown command "st_setupqa' in l]
 assert 'ST_SETUP_COMPLETE' in log and not failures,failures or log[-1600:]
 assert 'SpawnServer' not in log and 'Server Initialization' not in log
 if a.case=='recovery-write':assert (mod/'_st_setup_display_recovery.cfg').exists(),'Recovery record removed despite failed profile write'
 if a.case in ('recovery','display','keep','timeout','import'):assert not (mod/'_st_setup_display_recovery.cfg').exists(),'Confirmed/restored display recovery was not retired'
 print('Passed; screenshots:',len(list(mod.rglob('*.png'))));print('\n'.join(l for l in log.splitlines() if 'ST_SETUP_STATE' in l))
if __name__=='__main__':main()
