"""Verify, back up and install the remaining MP menu presentation."""
import argparse,datetime,hashlib,importlib.util,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/menu-rollout-01';STATE=ROOT/'dist/menu-rollout-install.json'
PACKAGE='zzzzzzzzzz_sabertrials_rollout.pk3';PREVIOUS=ROOT/'dist/rich-menus-install.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def read(p):return json.loads(p.read_text())
def load(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def candidate():
 b=load('menu_rollout_builder',ROOT/'tools/Build-Menu-Rollout.py');r=read(OUT/'source-receipt.json');base=read(b.BASE/'source-receipt.json');receipt=sha(OUT/'source-receipt.json')
 assert b.tree(b.BASE/'frontend')==base['sources'] and r['baseline_receipt_sha256']==sha(b.BASE/'source-receipt.json')
 assert r['inputs']==b.inputs() and r['sources']==b.tree(OUT/'frontend') and r['assets']==b.tree(OUT/'assets') and r['package_sha256']==sha(OUT/PACKAGE)
 changed={n for n,v in base['sources'].items() if r['sources'].get(n)!=v};added=set(r['sources'])-set(base['sources'])
 expected={'codemp/ui/'+n for n in ('ui_main.c','ui_shared.c','ui_atoms.c','ui_force.c','ui_sabertrials_presentation.inc')}
 assert changed==expected and added=={'codemp/ui/ui_st_legacy.inc'} and set(base['sources'])<=set(r['sources']),(changed,added)
 assert '#define UI_API_VERSION 285' in (OUT/'frontend/codemp/ui/ui_public.h').read_text()
 with zipfile.ZipFile(OUT/PACKAGE) as z:
  assert set(z.namelist())==set(r['assets']) and len(z.namelist())==len(r['assets'])
  for n,v in r['assets'].items():assert n.startswith('ui/assets/sabertrials/rollout/') and len(n)<64 and hashlib.sha256(z.read(n)).hexdigest()==v
 builds={}
 for qa in (True,False):
  variant='build-qa' if qa else 'build';x=read(OUT/('build-record-qa.json' if qa else 'build-record.json'))
  assert x['qa']==qa and x['ui_api']==285 and x['source_receipt_sha256']==receipt and x['builder_sha256']==sha(ROOT/'tools/Build-Menu-Rollout.py')
  assert x['ui_sha256']==sha(OUT/variant/'Release/uix86_64.dll');builds[qa]=x['ui_sha256']
 evidence=[]
 for p in (OUT/'verification').glob('*/result.json'):
  x=read(p)
  if x.get('passed') and not x.get('installed') and x.get('source_receipt_sha256')==receipt and x.get('ui_sha256')==builds.get(x.get('qa')) and x.get('package_sha256')==r['package_sha256']:
   mod=p.parent/'home/SaberTrials';assert sha(mod/'qconsole.log')==x['log_sha256'] and sha(mod/'uix86_64.dll')==x['ui_sha256'] and sha(mod/PACKAGE)==r['package_sha256']
   evidence.append((p,x))
 roles={}
 for role,qa,renderer,height,checker in [('wide',True,'rd-vanilla',720,'Check-Menu-Rollout.py'),('tall',True,'rd-rend2',1024,'Check-Menu-Rollout.py'),('production',False,'rd-vanilla',720,'Check-Menu-Rollout.py'),('rich-regression',True,'rd-vanilla',720,'Check-Rich-Menus.py')]:
  matches=[(p,x) for p,x in evidence if x['qa']==qa and x['renderer']==renderer and x['height']==height and x.get('checker_sha256')==sha(ROOT/'tools'/checker)]
  if role in ('wide','tall'):matches=[(p,x) for p,x in matches if x.get('matrix') and len(x.get('inventory',{}).get('offline',[]))>=49 and len(x['inventory'].get('ingame',[]))>=32]
  assert matches,'Missing current verification: '+role
  p,x=matches[-1];prefix='rich-' if role=='rich-regression' else 'rollout-'
  assert all((p.parent/'home/SaberTrials/screenshots'/(prefix+n+'.png')).is_file() for n in x['screenshots'])
  roles[role]={'result':str(p),'sha256':sha(p)}
 data=(OUT/'build/Release/uix86_64.dll').read_bytes();assert not any(marker in data for marker in (b'st_legacyqa',b'ST_LEGACY_FAIL',b'st_mainqa',b'st_controlsqa',b'st_setupqa',b'st_profileqa'))
 return {'source_receipt_sha256':receipt,'ui_sha256':builds[False],'package_sha256':r['package_sha256'],'evidence':roles,'changed_sources':sorted(changed)}
def verify(settings=False):
 x=read(STATE)
 for n,v in {**x['protected'],**x['after']}.items():assert sha(ROOT/n)==v,'Installed/protected file drift: '+n
 for n,v in x['before'].items():
  if v is not None:assert sha(Path(x['backup'])/n)==v,'Backup drift: '+n
 if settings:
  for n,v in x['preserved_settings'].items():assert sha(Path(n))==v,'Personal config changed: '+n
 print('Verified the menu rollout, backups and protected files.',flush=True);return x
def install():
 assert not STATE.exists(),'Already installed; use verify'
 proof=candidate();old=read(PREVIOUS);r=read(OUT/'source-receipt.json');assert r['prior_install_sha256']==sha(PREVIOUS) and all(sha(ROOT/n)==v for n,v in old['after'].items())
 review=read(OUT/'final-review.json');assert review['complete'] and not review['unresolved_important'] and review['source_receipt_sha256']==proof['source_receipt_sha256']
 helper=load('rollout_profile_helper',ROOT/'tools/Install-Profile-Browser.py');helper.stopped();home,settings=helper.settings()
 assert not (home/'uix86_64.dll').exists() and not (home/PACKAGE).exists(),'Home UI override requires inspection'
 for p in home.glob('*.pk3'):
  with zipfile.ZipFile(p) as z:assert not any(n.lower()=='uix86_64.dll' or n.lower().startswith('ui/assets/sabertrials/rollout/') for n in z.namelist()),'Home UI override requires inspection'
 mapping={'uix86_64.dll':OUT/'build/Release/uix86_64.dll',PACKAGE:OUT/PACKAGE};before={n:sha(ROOT/n) for n in mapping}
 after={'uix86_64.dll':proof['ui_sha256'],PACKAGE:proof['package_sha256']}
 # Snapshot current authored assets/configs instead of treating edits since the
 # previous installation as permission to restore older versions.
 protected={n:sha(ROOT/n) for n in {**old['protected'],**old['after']} if n not in mapping}
 backup=ROOT/'dist/backups'/('menu-rollout-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
 payload={'installed':True,'before':before,'after':after,'protected':protected,'preserved_settings':settings,'backup':str(backup),'proof':proof,'review_sha256':sha(OUT/'final-review.json'),'ui_api':285,'gameplay_unchanged':True}
 tx=load('rollout_transaction',ROOT/'tools/Install-Handedness.py');tx.install_transaction(ROOT,mapping,before,after,protected,backup,STATE,payload);verify(settings=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['check','install','verify']);p.add_argument('--settings',action='store_true');a=p.parse_args()
 if a.action=='check':candidate();print('Current menu rollout candidate passed verification.')
 elif a.action=='install':install()
 else:verify(a.settings)
