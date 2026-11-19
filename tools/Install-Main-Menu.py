"""Verify and install only the approved main-menu UI and original frame art."""
from pathlib import Path
import argparse,datetime,hashlib,importlib.util,json,re,zipfile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/main-menu-01';STATE=ROOT/'dist/main-menu-install.json';PACKAGE='zzzzzzzz_sabertrials_main.pk3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def read(p):return json.loads(p.read_text())
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def sources():return {'uix86_64.dll':OUT/'build/Release/uix86_64.dll','ui/jamp/main.menu':OUT/'menus/ui/jamp/main.menu',PACKAGE:OUT/PACKAGE}
def candidate():
 b=load('main_builder',ROOT/'tools/Build-Main-Menu.py');r=read(OUT/'source-receipt.json');baseline=read(b.BASE/'source-receipt.json')
 assert r['baseline_receipt_sha256']==sha(b.BASE/'source-receipt.json') and b.tree(b.BASE/'frontend')==baseline['sources']
 assert r['inputs']==b.inputs() and r['sources']==b.tree(OUT/'frontend')
 assert r['assets']==b.tree(OUT/'assets') and r['menus']==b.tree(OUT/'menus') and r['package_sha256']==sha(OUT/PACKAGE)
 changed={name for name,digest in baseline['sources'].items() if r['sources'].get(name)!=digest};added=set(r['sources'])-set(baseline['sources'])
 assert changed=={'codemp/ui/ui_main.c','codemp/ui/ui_atoms.c'} and added=={'codemp/ui/st_main_core.h','codemp/ui/st_main_geometry.h','codemp/ui/ui_st_main.inc'},(changed,added)
 assert set(baseline['sources'])<=set(r['sources']) and '#define UI_API_VERSION 285' in (OUT/'frontend/codemp/ui/ui_public.h').read_text()
 # Other menus, account actions and Exit confirmation remain byte-for-byte text.
 blocks=load('main_blocks',ROOT/'tools/Stage-Tournament-Frontend.py');old=(OUT/'original-main.menu').read_text();new=(OUT/'menus/ui/jamp/main.menu').read_text()
 def strip_roots(text):
  for root in ('main','mainMenu'):
   a,z=blocks.block_span(text,'menuDef',root);text=text[:a]+text[z:]
  return re.sub(r'\s+',' ',text).strip()
 assert strip_roots(old)==strip_roots(new),'Non-main menu changed'
 expected={**r['menus'],**r['assets']}
 with zipfile.ZipFile(OUT/PACKAGE) as z:
  assert len(z.namelist())==len(expected) and set(z.namelist())==set(expected)
  for name,digest in expected.items():assert len(name)<64 and hashlib.sha256(z.read(name)).hexdigest()==digest
 builds={}
 for qa in (False,True):
  kind='build-qa' if qa else 'build';x=read(OUT/('build-record-qa.json' if qa else 'build-record.json'))
  assert x['qa']==qa and x['ui_api']==285 and x['source_receipt_sha256']==sha(OUT/'source-receipt.json') and x['builder_sha256']==sha(ROOT/'tools/Build-Main-Menu.py')
  assert x['ui_sha256']==sha(OUT/kind/'Release/uix86_64.dll');builds[kind]=x['ui_sha256']
 evidence=[]
 for p in sorted((OUT/'verification').glob('*/result.json')):
  x=read(p)
  if x.get('passed') and not x.get('installed') and x.get('source_receipt_sha256')==sha(OUT/'source-receipt.json') and x.get('checker_sha256')==sha(ROOT/'tools/Check-Main-Menu.py'):evidence.append((p,x))
 chosen={}
 for role,qa,renderer,height in [('vanilla',True,'rd-vanilla',720),('rend2',True,'rd-rend2',720),('tall',True,'rd-vanilla',1024),('production',False,'rd-vanilla',720)]:
  digest=builds['build-qa' if qa else 'build'];matches=[(p,x) for p,x in evidence if x['qa']==qa and x['renderer']==renderer and x['height']==height and x['ui_sha256']==digest];assert matches,'Missing proof: '+role
  p,x=matches[-1];mod=p.parent/'home/SaberTrials';assert sha(mod/'uix86_64.dll')==digest and sha(mod/PACKAGE)==r['package_sha256'] and sha(mod/'qconsole.log')==x['log_sha256']
  log=(mod/'qconsole.log').read_text(errors='replace');assert 'ST_MAIN_COMPLETE' in log and all(s not in log for s in ('ST_MAIN_FAIL','Server Initialization','SpawnServer'))
  chosen[role]={'result':str(p),'sha256':sha(p)}
 data=(OUT/'build/Release/uix86_64.dll').read_bytes();assert all(s not in data for s in (b'st_mainqa',b'ST_MAIN_FAIL',b'st_profileqa',b'st_controlsqa',b'st_setupqa'))
 return {'source_receipt_sha256':sha(OUT/'source-receipt.json'),'builds':builds,'verification':chosen,'package_sha256':r['package_sha256']}
def verify(settings=False):
 x=read(STATE)
 for name,digest in {**x['protected'],**x['after']}.items():assert sha(ROOT/name)==digest,'Protected/installed file changed: '+name
 for name,digest in x['before'].items():
  if digest is not None:assert sha(Path(x['backup'])/name)==digest
 if settings:
  for name,digest in x['preserved_settings'].items():assert sha(Path(name))==digest,'Personal configuration changed: '+name
 print('Installed main menu, original assets, backups and protected game files verified.');return x
def install():
 assert not STATE.exists(),'Already installed; use verify.'
 review=read(OUT/'final-review.json');assert review['complete'] and not review['critical_findings'] and not review['important_findings'] and all(x['resolved'] for x in review['minor_findings']) and review['source_receipt_sha256']==sha(OUT/'source-receipt.json'),'Review/fix proof does not match candidate'
 proof=candidate();helper=load('profile_helper',ROOT/'tools/Install-Profile-Browser.py');helper.stopped()
 previous=load('previous_ui',ROOT/'tools/Install-Menu-Polish.py');previous.configure(2);old=previous.verify()
 r=read(OUT/'source-receipt.json');assert r['previous_install_sha256']==sha(ROOT/'dist/menu-polish-02-install.json') and r['original_main_sha256']==sha(ROOT/'ui/jamp/main.menu')
 home,snapshot=helper.settings();assert not list(home.glob('*x86_64.dll')) and not (home/'ui/jamp/main.menu').exists(),'Home-directory override requires inspection'
 for p in home.glob('*.pk3'):
  with zipfile.ZipFile(p) as z:assert not any(n.lower() in ('ui/jamp/main.menu','uix86_64.dll') for n in z.namelist()),'Home-directory package override requires inspection'
 mapping=sources();before={name:sha(ROOT/name) for name in mapping};after={name:sha(p) for name,p in mapping.items()}
 protected={k:v for k,v in {**old['protected'],**old['after']}.items() if k not in mapping}
 backup=ROOT/'dist/backups'/('main-menu-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
 state={'installed':True,'before':before,'after':after,'protected':protected,'backup':str(backup),'preserved_settings':snapshot,'previous_receipt':'dist/menu-polish-02-install.json','previous_receipt_sha256':sha(ROOT/'dist/menu-polish-02-install.json'),'proof':proof,'review_sha256':sha(OUT/'final-review.json'),'ui_api':285,'gameplay_unchanged':True,'live_multiplayer_tested':False,'final_video_installed':False}
 transaction=load('main_transaction',ROOT/'tools/Install-Handedness.py');transaction.install_transaction(ROOT,mapping,before,after,protected,backup,STATE,state);verify(settings=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['check','install','verify']);a=p.parse_args();{'check':candidate,'install':install,'verify':verify}[a.action]()
