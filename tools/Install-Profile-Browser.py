"""Verify/install the approved Profile UI only, using transaction backups."""
from pathlib import Path
import argparse,datetime,hashlib,importlib.util,json,subprocess,sys,zipfile
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/profile-candidate-01';STATE=ROOT/'dist/profile-browser-install.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def read(p):return json.loads(p.read_text())
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def stopped():
 ids=subprocess.check_output(['powershell','-NoProfile','-Command',"Get-Process -Name 'SaberTrials.x86_64','openjk.x86_64','openjkded.x86_64','taystjk.x86_64','jamp','jampDed' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id; exit 0"],text=True)
 assert not ids.strip(),'Close Jedi Academy/Saber Trials before replacing the UI.'
def settings():
 documents=subprocess.check_output(['powershell','-NoProfile','-Command',"[Environment]::GetFolderPath('MyDocuments')"],text=True).strip()
 home=Path(documents)/'My Games/OpenJK/SaberTrials'
 return home,{str(p):sha(p) for folder in (ROOT,home) for p in folder.glob('*.cfg') if p.is_file()}
def sources():
 mapping={'uix86_64.dll':OUT/'build/Release/uix86_64.dll','zzzzzzz_sabertrials_profile.pk3':OUT/'zzzzzzz_sabertrials_profile.pk3'}
 mapping.update({p.relative_to(OUT/'menus').as_posix():p for p in (OUT/'menus').rglob('*.menu')})
 assert set(mapping)=={'uix86_64.dll','zzzzzzz_sabertrials_profile.pk3','ui/jamp/player.menu','ui/jamp/ingame_player.menu'}
 return mapping
def candidate():
 builder=load('profile_builder',ROOT/'tools/Build-Profile.py');receipt=read(OUT/'source-receipt.json');stage=read(OUT/'stage-receipt.json')
 assert builder.tree(builder.BASE/'frontend')==read(builder.BASE/'source-receipt.json')['sources']['frontend'],'Baseline drift'
 assert receipt['baseline']==sha(builder.BASE/'source-receipt.json') and receipt['inputs']==builder.tree(builder.SRC)
 current=builder.tree(OUT/'frontend');assert current==receipt['sources'],'Candidate source drift'
 baseline=read(builder.BASE/'source-receipt.json')['sources']['frontend']
 changes={name for name,digest in baseline.items() if current.get(name)!=digest}
 assert changes=={'codemp/ui/ui_main.c','codemp/ui/ui_atoms.c','codemp/ui/ui_sabertrials_profile.inc'},changes
 added=set(current)-set(baseline)
 assert added=={'codemp/ui/'+name for name in ('st_profile_core.h','st_profile_tags.h','st_profile_stock_voices.h','ui_st_profile.inc','ui_st_profile_catalog.inc','ui_st_profile_actions.inc','ui_st_profile_draw.inc')},added
 assert '#define UI_API_VERSION 285' in (OUT/'frontend/codemp/ui/ui_public.h').read_text()
 assert stage['source_receipt_sha256']==sha(OUT/'source-receipt.json')
 for kind,record in stage['build_records'].items():
  assert record['qa']==(kind=='build-qa') and record['ui_api']==285
  assert record['source_receipt_sha256']==sha(OUT/'source-receipt.json') and record['builder_sha256']==sha(ROOT/'tools/Build-Profile.py')
  assert record['ui_sha256']==stage['builds'][kind]==sha(OUT/kind/'Release/uix86_64.dll')
 for rel,digest in stage['menus'].items():assert sha(OUT/'menus'/rel)==digest
 for rel,digest in stage['package'].items():assert sha(OUT/rel)==digest
 with zipfile.ZipFile(OUT/'zzzzzzz_sabertrials_profile.pk3') as package:
  assert len(package.namelist())==2 and set(package.namelist())==set(stage['menus'])
  for rel,digest in stage['menus'].items():assert hashlib.sha256(package.read(rel)).hexdigest()==digest
 # Select evidence by exact content/version, not a mutable or hard-coded tag.
 # Older immutable runs remain available but cannot validate a newer build.
 evidence=[];source_sha=sha(OUT/'source-receipt.json');checker_sha=sha(ROOT/'tools/Check-Profile.py')
 for path in sorted((OUT/'verification').glob('*/result.json')):
  result=read(path)
  if result.get('passed') and not result.get('installed') and result.get('source_receipt_sha256')==source_sha and result.get('checker_sha256')==checker_sha:evidence.append((path.parent,result))
 chosen={}
 for role,renderer,height,metadata in (('vanilla','rd-vanilla',720,True),('rend2','rd-rend2',720,False),('tall','rd-vanilla',1024,False)):
  matches=[(folder,result) for folder,result in evidence if result.get('qa') and result.get('renderer')==renderer and result.get('height')==height and result.get('metadata')==metadata and result.get('ui_sha256')==stage['builds']['build-qa']]
  assert matches,'Matching native proof missing: '+role
  folder,result=matches[-1];chosen[role]={'folder':str(folder),'result_sha256':sha(folder/'result.json')}
  assert result['passed'] and result['qa'] and result['menu_only'] and not result['installed']
  assert result['renderer']==renderer and result['height']==height and result['metadata']==metadata
  assert result['ui_sha256']==stage['builds']['build-qa'] and result['source_receipt_sha256']==sha(OUT/'source-receipt.json')
  assert sha(folder/'home/SaberTrials/uix86_64.dll')==result['ui_sha256']
  assert sha(folder/'home/SaberTrials/qconsole.log')==result['log_sha256']
  log=(folder/'home/SaberTrials/qconsole.log').read_text(errors='replace')
  assert 'ST_PROFILE_COMPLETE' in log and 'ST_PROFILE_FAIL' not in log
  assert 'Server Initialization' not in log and 'SpawnServer' not in log
 matches=[(folder,result) for folder,result in evidence if not result.get('qa') and result.get('ui_sha256')==stage['builds']['build'] and result.get('renderer')=='rd-vanilla']
 assert matches,'Matching production proof missing'
 folder,production=matches[-1];chosen['production']={'folder':str(folder),'result_sha256':sha(folder/'result.json')}
 assert production['passed'] and not production['qa'] and production['ui_sha256']==stage['builds']['build']
 assert sha(folder/'home/SaberTrials/uix86_64.dll')==production['ui_sha256'] and sha(folder/'home/SaberTrials/qconsole.log')==production['log_sha256']
 data=(OUT/'build/Release/uix86_64.dll').read_bytes()
 assert all(marker not in data for marker in (b'st_profileqa',b'ST_PROFILE_FAIL',b'st_controlsqa',b'st_setupqa',b'st_clientqa')),'QA commands in production'
 stage['verification']=chosen;return stage
def verify(check_settings=False):
 state=read(STATE);assert state['installed'] and not state.get('restored')
 for rel,digest in {**state['protected'],**state['after']}.items():assert sha(ROOT/rel)==digest,'Installed/protected file changed: '+rel
 backup=Path(state['backup']).resolve();assert backup.is_relative_to((ROOT/'dist/backups').resolve())
 for rel,digest in state['before'].items():
  if digest is not None:assert sha(backup/rel)==digest,'Backup changed: '+rel
 assert sha(OUT/'stage-receipt.json')==state['stage_receipt_sha256']
 if check_settings:
  for name,digest in state['preserved_settings'].items():assert sha(Path(name))==digest,'Settings changed during installation: '+name
 print('Installed Profile UI/menus, protected gameplay files, and backups verified.')
 return state
def install():
 assert not STATE.exists(),'Already installed; use verify.'
 stopped();stage=candidate();old=read(ROOT/'dist/controls-setup-install.json')
 review=read(OUT/'final-review.json');assert review['complete'] and review['material_findings_resolved'] and review['stage_receipt_sha256']==sha(OUT/'stage-receipt.json'),'Final review/fix verification required'
 assert old['installed'] and not old.get('restored')
 for rel,digest in old['after'].items():assert sha(ROOT/rel)==digest,'Controls/Setup baseline changed: '+rel
 mapping=sources();home,snapshot=settings()
 assert not list(home.glob('*x86_64.dll')),'Inspect home-directory DLL overrides first.'
 assert not any((home/'ui/jamp'/name).exists() for name in ('player.menu','ingame_player.menu')),'Inspect home-directory menu overrides first.'
 for path in home.glob('*.pk3'):
  with zipfile.ZipFile(path) as package:assert not ({name.lower() for name in package.namelist()}&{'uix86_64.dll','ui/jamp/player.menu','ui/jamp/ingame_player.menu'}),'Inspect home-directory Profile package overrides first.'
 protected={}
 for folder in ('client','ui','server','models','scripts','sound','textures','fonts','ext_data'):
  for p in (ROOT/folder).rglob('*'):
   if p.is_file() and p.relative_to(ROOT).as_posix() not in mapping:protected[p.relative_to(ROOT).as_posix()]=sha(p)
 for p in list(ROOT.glob('*.dll'))+list(ROOT.glob('*.pk3'))+list(ROOT.glob('*.cmd')):
  if p.name not in mapping:protected[p.name]=sha(p)
 before={rel:sha(ROOT/rel) for rel in mapping};after={rel:sha(path) for rel,path in mapping.items()}
 backup=ROOT/'dist/backups'/('profile-browser-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
 state={'installed':True,'restored':False,'backup':str(backup),'before':before,'after':after,'protected':protected,'preserved_settings':snapshot,'stage_receipt_sha256':sha(OUT/'stage-receipt.json'),'verification':stage['verification'],'previous_receipt':'dist/controls-setup-install.json','previous_receipt_sha256':sha(ROOT/'dist/controls-setup-install.json'),'sources':{rel:str(p) for rel,p in mapping.items()},'ui_api':285,'gameplay_unchanged':True,'live_multiplayer_tested':False}
 helper=load('profile_transaction',ROOT/'tools/Install-Handedness.py')
 helper.install_transaction(ROOT,mapping,before,after,protected,backup,STATE,state);verify(check_settings=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('action',choices=['check','install','verify']);args=parser.parse_args()
 {'check':candidate,'install':install,'verify':verify}[args.action]()
