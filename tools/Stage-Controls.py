"""Create a private playable Controls test. Never starts the game."""
from pathlib import Path
import hashlib,json,shutil,zipfile
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'dist/purple-katana-candidate-07'
OUT=ROOT/'dist/controls-candidate-01'
STAGE=OUT/'playable'
MOD='SaberTrialsControlsTest'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    installed=ROOT/'dist/controls-setup-install.json'
    if installed.exists() and json.loads(installed.read_text()).get('installed'):
        raise RuntimeError('Controls/Setup test launchers are retired. Use Launch-SaberTrials-MP.cmd.')
    receipt=json.loads((BASE/'playable/stage-receipt.json').read_text())
    files={}
    def copy(source,relative,expected=None):
        if expected:assert sha(source)==expected,'Baseline artifact drift: '+source.name
        target=STAGE/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target);files[relative]=sha(target)
    for rel,digest in receipt['files'].items():
        p=Path(rel)
        if p.suffix=='.pk3' or p.name in ('SDL2.dll','rd-vanilla_x86_64.dll','rd-rend2_x86_64.dll','cgamex86_64.dll','jampgamex86_64.dll'):
            copy(BASE/'playable'/rel,rel.replace('SaberTrialsPurpleTest',MOD),digest)
    copy(OUT/'build-engine/Release/openjk.x86_64.exe','bin/SaberTrials.x86_64.exe')
    copy(OUT/'build-frontend/Release/uix86_64.dll',f'home/{MOD}/uix86_64.dll')
    mod=STAGE/'home'/MOD
    menus={}
    for filename,name in [('controls','controlsMenu'),('ingame_controls','ingame_controls')]:
        menus[f'ui/jamp/{filename}.menu']='{ menuDef { name "'+name+'" fullscreen 1 rect 0 0 640 480 visible 0 focusColor 1 1 1 1 onESC { close '+name+'; } } }\n'
    package=mod/'zzzz_sabertrials_controls.pk3'
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
        for name,text in menus.items():z.writestr(name,text)
    files[package.relative_to(STAGE).as_posix()]=sha(package)
    config=mod/'openjk.cfg'
    if not config.exists():config.write_text('exec mpdefault.cfg\nseta r_fullscreen 0\nseta r_mode -1\nseta r_customwidth 1280\nseta r_customheight 720\nseta com_introplayed 1\nseta name "Controls Tester"\n')
    fixed=mod/'controls-test.cfg'
    fixed.write_text('// Private Controls test; no automatic map, server join or login.\nset g_hybridStyles 1\nset g_stanceLibrary 1\nset sv_pure 0\n'+''.join(f'set sv_master{i} ""\n' for i in range(1,6))+'set cl_allowDownload 0\n')
    files[fixed.relative_to(STAGE).as_posix()]=sha(fixed)
    args=['+safe','+set','fs_basepath',str(ROOT.parent),'+set','fs_homepath',str(STAGE/'home'),'+set','fs_game',MOD,'+set','fs_forcegame',MOD,'+set','com_unpackLibraries','0','+exec','openjk.cfg','+exec','controls-test.cfg']
    (STAGE/'launch-arguments.json').write_text(json.dumps(args,indent=2))
    launcher=(BASE/'playable/Launch-Purple-Test.ps1').read_text().replace('Purple','Controls')
    (STAGE/'Launch-Controls-Test.ps1').write_text(launcher)
    (STAGE/'READ-ME-FIRST.txt').write_text('Saber Trials Controls preview\n\nUse the Controls Test launcher. Open Controls from the main menu or pause menu.\nChanges affect only this private test profile. Your normal game and Purple test remain unchanged.\n\nMouse shows basic settings first. Open Advanced settings underneath and scroll for extra mouse controls; Apply/Cancel stay visible. Advanced Input contains keyboard and legacy settings only. Bindlist shows 20 entries per page.\nTry searching/rebinding, Replace/Swap/Cancel, Bindlist custom commands, and named Save/Load. Load stages changes; Apply activates them.\nFor a gamepad: enable it in Controller, Apply, stage controller defaults and Apply. Button labels can be changed independently. Physical controller compatibility and in-game feel need your testing.\nNamed configs are in home/SaberTrialsControlsTest beside this document, as shown by the menu.\nUse Controls > Saved Configs to load these reviewable snapshots. Arbitrary executable configs are intentionally rejected.\nThe build includes the existing Purple candidate07 gameplay and stance content. This is a development test, not a released replacement.\n')
    for name in ('launch-arguments.json','Launch-Controls-Test.ps1','READ-ME-FIRST.txt'):files[name]=sha(STAGE/name)
    (STAGE/'stage-receipt.json').write_text(json.dumps({'schema':1,'installed':False,'fs_game':MOD,'files':files},indent=2))
    (ROOT/'Play-SaberTrials-Controls-Test.cmd').write_bytes('@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0dist\\controls-candidate-01\\playable\\Launch-Controls-Test.ps1"\r\nif errorlevel 1 pause\r\n'.encode('ascii'))
    print('Private Controls test staged; normal and Purple installations unchanged.')
if __name__=='__main__':main()
