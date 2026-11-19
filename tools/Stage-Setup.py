"""Stage Setup in its own runtime; never modifies an existing game/test profile."""
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'dist/controls-candidate-01';OUT=ROOT/'dist/setup-candidate-01';STAGE=OUT/'playable';MOD='SaberTrialsSetupTest'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 installed=ROOT/'dist/controls-setup-install.json'
 if installed.exists() and json.loads(installed.read_text()).get('installed'):
  raise RuntimeError('Controls/Setup test launchers are retired. Use Launch-SaberTrials-MP.cmd.')
 p=argparse.ArgumentParser();p.add_argument('--qa',action='store_true');a=p.parse_args();receipt=json.loads((BASE/'playable/stage-receipt.json').read_text());files={}
 def copy(src,rel,digest=None):
  if digest:assert sha(src)==digest,'Controls artifact drift: '+str(src)
  target=STAGE/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target);files[rel]=sha(target)
 for rel,digest in receipt['files'].items():
  path=Path(rel)
  if path.suffix=='.pk3' or path.name in ('SDL2.dll','rd-vanilla_x86_64.dll','rd-rend2_x86_64.dll','jampgamex86_64.dll'):
   copy(BASE/'playable'/rel,rel.replace('SaberTrialsControlsTest',MOD),digest)
 variant='-qa' if a.qa else ''
 copy(OUT/f'build-engine{variant}/Release/openjk.x86_64.exe','bin/SaberTrials.x86_64.exe')
 for name in ('uix86_64.dll','cgamex86_64.dll'):copy(OUT/f'build-frontend{variant}/Release'/name,f'home/{MOD}/'+name)
 mod=STAGE/'home'/MOD
 package=mod/'zzzzz_sabertrials_setup.pk3'
 with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('ui/jamp/ingame.menu',(ROOT/'development-source/setup/ingame.menu').read_bytes())
  for filename,name in (('setup','setup_menu'),('ingame_setup','ingame_setup')):
   z.writestr(f'ui/jamp/{filename}.menu','{ menuDef { name "'+name+'" fullscreen 1 rect 0 0 640 480 visible 0 focusColor 1 1 1 1 } }\n')
 files[package.relative_to(STAGE).as_posix()]=sha(package)
 cfg=mod/'openjk.cfg'
 if not cfg.exists():cfg.write_text('exec mpdefault.cfg\nseta r_fullscreen 0\nseta r_mode -1\nseta r_customwidth 1280\nseta r_customheight 720\nseta com_introplayed 1\nseta cl_allowDownload 0\nseta name "Setup Tester"\n')
 fixed=mod/'setup-test.cfg';fixed.write_text('// Isolated Setup test; no map, server, join, or login.\nset g_hybridStyles 1\nset g_stanceLibrary 1\nset sv_pure 0\n'+''.join(f'set sv_master{i} ""\n' for i in range(1,6)))
 files[fixed.relative_to(STAGE).as_posix()]=sha(fixed)
 args=['+safe','+set','fs_basepath',str(ROOT.parent),'+set','fs_homepath',str(STAGE/'home'),'+set','fs_game',MOD,'+set','fs_forcegame',MOD,'+set','com_unpackLibraries','0','+exec','openjk.cfg','+exec','setup-test.cfg']
 (STAGE/'launch-arguments.json').write_text(json.dumps(args,indent=2))
 launcher=(BASE/'playable/Launch-Controls-Test.ps1').read_text().replace('Controls','Setup')
 launcher=launcher.replace('foreach ($item', 'if ($receipt.qa) { throw \"This is an automated-check build. Stage the production Setup candidate first.\" }\nforeach ($item',1)
 (STAGE/'Launch-Setup-Test.ps1').write_text(launcher)
 (STAGE/'READ-ME-FIRST.txt').write_text('Saber Trials Setup test\n\nUse Play-SaberTrials-Setup-Test.cmd and open Setup. Main/pause Setup shares six tabs: Video, Sound, Interface, Game Options, Network, Recording.\nSearch jumps to a setting. Apply/Cancel cover pending edits across tabs. Reset this tab stages only that tab. Display changes have Keep/Revert and timeout recovery.\nSaved Configs is in Setup; Controls links to the same manager. Load stages the full personal snapshot; Apply activates it.\nClean Capture in Recording hides HUD and streamer overlays.\nThe first launch uses stock controls; subsequent staging preserves this test profile. Normal game, Controls Test and Purple Test remain unchanged.\nThis build includes the existing Purple candidate07 gameplay/stance content. Test the connected-menu paths and appearance in game.\n')
 for n in ('launch-arguments.json','Launch-Setup-Test.ps1','READ-ME-FIRST.txt'):files[n]=sha(STAGE/n)
 (STAGE/'stage-receipt.json').write_text(json.dumps({'schema':1,'qa':a.qa,'installed':False,'fs_game':MOD,'files':files},indent=2))
 if not a.qa:(ROOT/'Play-SaberTrials-Setup-Test.cmd').write_bytes(b'@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0dist\\setup-candidate-01\\playable\\Launch-Setup-Test.ps1"\r\nif errorlevel 1 pause\r\n')
 print('Private Setup test staged'+(' (QA)' if a.qa else '')+'. Existing installations/profiles preserved.')
if __name__=='__main__':main()
