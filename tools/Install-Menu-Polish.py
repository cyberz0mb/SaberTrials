"""Install only the verified native UI polish, preserving the existing game."""
from pathlib import Path
import argparse,datetime,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/menu-polish-01';STATE=ROOT/'dist/menu-polish-install.json'
REVISION=1
def configure(revision):
 global REVISION,OUT,STATE,PREVIOUS_STATE
 assert revision>=1;REVISION=revision;OUT=ROOT/('dist/menu-polish-%02d'%revision)
 STATE=ROOT/('dist/menu-polish-install.json' if revision==1 else 'dist/menu-polish-%02d-install.json'%revision)
 PREVIOUS_STATE=ROOT/('dist/profile-browser-install.json' if revision==1 else 'dist/menu-polish-install.json' if revision==2 else 'dist/menu-polish-%02d-install.json'%(revision-1))
configure(1)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def read(p):return json.loads(p.read_text())
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def candidate():
 b=load('polish_builder',ROOT/'tools/Build-Menu-Polish.py');b.configure(REVISION);r=read(OUT/'source-receipt.json');base=read(b.BASE/'source-receipt.json')
 assert r['baseline_receipt_sha256']==sha(b.BASE/'source-receipt.json')
 assert b.tree(b.BASE/'frontend')==base['sources'],'Historical Profile source changed'
 assert r['inputs']==b.inputs() and r['sources']==b.tree(OUT/'frontend'),'Candidate source drift'
 changed={name for name,digest in base['sources'].items() if r['sources'].get(name)!=digest};added=set(r['sources'])-set(base['sources'])
 allowed={'codemp/ui/'+p.name for paths in b.FILES.values() for p in paths}
 assert changed and changed<=allowed and added==({'codemp/ui/st_menu_interaction.h','codemp/ui/ui_st_menu_style.inc'}-set(base['sources'])),(changed,added)
 assert set(base['sources'])<=set(r['sources'])
 assert '#define UI_API_VERSION 285' in (OUT/'frontend/codemp/ui/ui_public.h').read_text()
 builds={}
 for qa in (False,True):
  record=read(OUT/('build-record-qa.json' if qa else 'build-record.json'));kind='build-qa' if qa else 'build'
  assert record['source_receipt_sha256']==sha(OUT/'source-receipt.json') and record['builder_sha256']==sha(ROOT/'tools/Build-Menu-Polish.py') and record['qa']==qa and record['ui_api']==285
  assert record['ui_sha256']==sha(OUT/kind/'Release/uix86_64.dll');builds[kind]=record['ui_sha256']
 evidence=[]
 for p in sorted((OUT/'verification').glob('*/result.json')):
  x=read(p)
  if x.get('passed') and not x.get('installed') and x.get('source_receipt_sha256')==sha(OUT/'source-receipt.json'):evidence.append((p,x))
 chosen={}
 for role,qa,renderer,height,checker in [('interaction',True,'rd-vanilla',720,'Check-Menu-Polish.py'),('rend2_tall',True,'rd-rend2',1024,'Check-Menu-Polish.py'),('profile',True,'rd-vanilla',720,'Check-Profile.py'),('production',False,'rd-vanilla',720,'Check-Menu-Polish.py')]:
  digest=builds['build-qa' if qa else 'build']
  matches=[(p,x) for p,x in evidence if x.get('qa')==qa and x.get('renderer')==renderer and x.get('height')==height and x.get('ui_sha256')==digest and x.get('checker_sha256')==sha(ROOT/'tools'/checker)]
  if role=='profile':matches=[(p,x) for p,x in matches if x.get('metadata')]
  assert matches,'Missing matching proof: '+role
  p,x=matches[-1];mod=p.parent/'home/SaberTrials';assert sha(mod/'uix86_64.dll')==digest and sha(mod/'qconsole.log')==x['log_sha256']
  log=(mod/'qconsole.log').read_text(errors='replace');assert all(marker not in log for marker in ('ST_PROFILE_FAIL','ST_CONTROLS_FAIL','ST_SETUP_FAIL','Server Initialization','SpawnServer'))
  assert ('ST_PROFILE_COMPLETE' if role=='profile' else 'ST_MENU_POLISH_COMPLETE') in log
  chosen[role]={'result':str(p),'sha256':sha(p)}
 regression=read(OUT/'regressions-final.json');assert regression['ui_sha256']==builds['build-qa'] and regression['source_receipt_sha256']==sha(OUT/'source-receipt.json')
 assert all(regression.get(k) for k in ('setup','controls','controller_slider','binding_capture','menu_only'))
 data=(OUT/'build/Release/uix86_64.dll').read_bytes();assert not any(s in data for s in (b'st_profileqa',b'st_setupqa',b'st_controlsqa',b'ST_PROFILE_FAIL',b'ST_MENU_SCROLL_CHECK'))
 return {'source_receipt_sha256':sha(OUT/'source-receipt.json'),'builds':builds,'source_changes':sorted(changed),'source_additions':sorted(added),'verification':chosen,'regression_sha256':sha(OUT/'regressions-final.json')}
def verify(settings=False):
 state=read(STATE)
 for name,digest in {**state['protected'],**state['after']}.items():assert sha(ROOT/name)==digest,'Protected/installed file changed: '+name
 for name,digest in state['before'].items():assert sha(Path(state['backup'])/name)==digest
 if settings:
  for name,digest in state['preserved_settings'].items():assert sha(Path(name))==digest,'Personal settings changed: '+name
 print('Installed menu UI, backups, and protected game files verified.')
 return state
def install():
 assert not STATE.exists(),'Already installed; use verify.'
 proof=candidate();profile=load('profile_install',ROOT/'tools/Install-Profile-Browser.py');profile.stopped()
 previous=profile if REVISION==1 else load('previous_polish',Path(__file__))
 if REVISION>1:previous.configure(REVISION-1)
 old=previous.verify()
 assert sha(PREVIOUS_STATE)==read(OUT/'source-receipt.json')['baseline_install_sha256']
 home,snapshot=profile.settings();assert not list(home.glob('*x86_64.dll')),'Home-directory DLL override must be inspected first'
 target='uix86_64.dll';sources={target:OUT/'build/Release'/target};before={target:sha(ROOT/target)};after={target:sha(sources[target])}
 protected={**old['protected'],**{k:v for k,v in old['after'].items() if k!=target}}
 backup=ROOT/'dist/backups'/('menu-polish-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
 state={'installed':True,'before':before,'after':after,'protected':protected,'backup':str(backup),'preserved_settings':snapshot,'revision':REVISION,'previous_receipt':str(PREVIOUS_STATE.relative_to(ROOT)),'previous_receipt_sha256':sha(PREVIOUS_STATE),'proof':proof,'ui_api':285,'gameplay_unchanged':True,'live_multiplayer_tested':False}
 helper=load('polish_transaction',ROOT/'tools/Install-Handedness.py');helper.install_transaction(ROOT,sources,before,after,protected,backup,STATE,state);verify(settings=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--revision',type=int,default=1);p.add_argument('action',choices=['check','install','verify']);a=p.parse_args();configure(a.revision);{'check':candidate,'install':install,'verify':verify}[a.action]()
