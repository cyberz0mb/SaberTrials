"""Verify and transactionally install only the approved rich UI DLL and artwork."""
from pathlib import Path
import argparse,datetime,hashlib,importlib.util,json,zipfile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/rich-menus-01';STATE=ROOT/'dist/rich-menus-install.json';PACKAGE='zzzzzzzzz_sabertrials_rich.pk3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def read(p):return json.loads(p.read_text())
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def candidate():
 b=load('rich_builder',ROOT/'tools/Build-Rich-Menus.py');r=read(OUT/'source-receipt.json');baseline=read(b.BASE/'source-receipt.json')
 assert b.tree(b.BASE/'frontend')==baseline['sources'] and r['baseline_receipt_sha256']==sha(b.BASE/'source-receipt.json')
 assert r['inputs']==b.inputs() and r['sources']==b.tree(OUT/'frontend') and r['assets']==b.tree(OUT/'assets') and r['menus']==b.tree(OUT/'menus')
 assert r['package_sha256']==sha(OUT/PACKAGE)
 changed={k for k,v in baseline['sources'].items() if r['sources'].get(k)!=v};added=set(r['sources'])-set(baseline['sources'])
 expected={'codemp/ui/'+n for n in ('ui_main.c','ui_st_controls.inc','ui_st_controls_draw.inc','ui_st_setup_draw.inc','ui_st_profile.inc','ui_st_profile_draw.inc','ui_st_main.inc')}
 assert changed==expected and added=={'codemp/ui/ui_st_rich.inc','codemp/ui/st_rich_type.h'},(changed,added)
 assert set(baseline['sources'])<=set(r['sources']) and '#define UI_API_VERSION 285' in (OUT/'frontend/codemp/ui/ui_public.h').read_text()
 for n,v in r['menus'].items():assert sha(ROOT/n)==v,'An installed menu changed since staging: '+n
 with zipfile.ZipFile(OUT/PACKAGE) as z:
  entries={**r['assets'],**r['menus']};assert len(z.namelist())==len(entries) and set(z.namelist())==set(entries)
  for n,v in entries.items():assert len(n)<64 and hashlib.sha256(z.read(n)).hexdigest()==v
 builds={}
 for qa in (False,True):
  kind='build-qa' if qa else 'build';x=read(OUT/('build-record-qa.json' if qa else 'build-record.json'))
  assert x['qa']==qa and x['ui_api']==285 and x['source_receipt_sha256']==sha(OUT/'source-receipt.json') and x['builder_sha256']==sha(ROOT/'tools/Build-Rich-Menus.py')
  assert x['ui_sha256']==sha(OUT/kind/'Release/uix86_64.dll');builds[qa]=x['ui_sha256']
 evidence=[]
 for p in (OUT/'verification').glob('*/result.json'):
  x=read(p)
  if x.get('passed') and not x.get('installed') and x.get('checker_sha256')==sha(ROOT/'tools/Check-Rich-Menus.py') and x.get('source_receipt_sha256')==sha(OUT/'source-receipt.json') and x.get('ui_sha256')==builds.get(x.get('qa')) and x.get('package_sha256')==r['package_sha256']:
   mod=p.parent/'home/SaberTrials';assert sha(mod/'qconsole.log')==x['log_sha256'] and sha(mod/'uix86_64.dll')==x['ui_sha256'] and sha(mod/PACKAGE)==r['package_sha256']
   assert all((mod/('screenshots/rich-'+n+'.png')).is_file() for n in x['screenshots']);evidence.append((p,x))
 selected={}
 for role,qa,renderer,height in [('wide',True,'rd-vanilla',720),('tall',True,'rd-rend2',1024),('production',False,'rd-vanilla',720)]:
  matches=[(p,x) for p,x in evidence if x['qa']==qa and x['renderer']==renderer and x['height']==height and x['live']];assert matches,'Missing fresh evidence: '+role
  p,x=matches[-1];selected[role]={'result':str(p),'sha256':sha(p)}
 data=(OUT/'build/Release/uix86_64.dll').read_bytes();assert not any(s in data for s in (b'ST_MAIN_FAIL',b'st_profileqa',b'st_setupqa',b'st_controlsqa',b'st_mainqa'))
 return {'source_receipt_sha256':sha(OUT/'source-receipt.json'),'ui_sha256':builds[False],'package_sha256':r['package_sha256'],'verification':selected,'changed_sources':sorted(changed)}
def verify():
 x=read(STATE)
 for n,v in {**x['protected'],**x['after']}.items():assert sha(ROOT/n)==v,'Installed/protected file drift: '+n
 for n,v in x['before'].items():
  if v is not None:assert sha(Path(x['backup'])/n)==v
 for n,v in x['preserved_settings'].items():assert sha(Path(n))==v,'Personal settings changed: '+n
 print('Rich menus verified; gameplay, other packages and personal settings preserved.');return x
def install():
 assert not STATE.exists(),'Already installed; use verify'
 proof=candidate();helper=load('rich_profile_helper',ROOT/'tools/Install-Profile-Browser.py');helper.stopped()
 prior=load('rich_main_installer',ROOT/'tools/Install-Main-Menu.py');old=prior.verify()
 assert sha(ROOT/'dist/main-menu-install.json')==read(OUT/'source-receipt.json')['baseline_install_sha256']
 review=read(OUT/'final-review.json');assert review['complete'] and review['source_receipt_sha256']==proof['source_receipt_sha256'] and not review['unresolved_important']
 mapping={'uix86_64.dll':OUT/'build/Release/uix86_64.dll',PACKAGE:OUT/PACKAGE};before={n:sha(ROOT/n) for n in mapping};after={n:sha(p) for n,p in mapping.items()}
 protected={n:v for n,v in {**old['protected'],**old['after']}.items() if n not in mapping};home,settings=helper.settings()
 assert not list(home.glob('*x86_64.dll')),'Home UI override needs inspection'
 for p in home.glob('*.pk3'):
  with zipfile.ZipFile(p) as z:assert not any(n.lower()=='uix86_64.dll' or n.lower().startswith('ui/assets/sabertrials/rich/') for n in z.namelist()),'Home UI override needs inspection'
 backup=ROOT/'dist/backups'/('rich-menus-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
 state={'installed':True,'before':before,'after':after,'protected':protected,'backup':str(backup),'preserved_settings':settings,'proof':proof,'review_sha256':sha(OUT/'final-review.json'),'ui_api':285,'gameplay_unchanged':True,'future_video_installed':False}
 tx=load('rich_transaction',ROOT/'tools/Install-Handedness.py');tx.install_transaction(ROOT,mapping,before,after,protected,backup,STATE,state);verify()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['check','install','verify']);a=p.parse_args();print({'check':candidate,'install':install,'verify':verify}[a.action]())
