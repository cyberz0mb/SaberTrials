"""Transactional hybrid-update tests in disposable fixtures; never touch game files."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
BINARIES={
 'client/SaberTrials.x86_64.exe':('engine','openjk.x86_64.exe'),
 'client/openjkded.x86_64.exe':('engine','openjkded.x86_64.exe'),
 'client/rd-vanilla_x86_64.dll':('engine','rd-vanilla_x86_64.dll'),
 'client/rd-rend2_x86_64.dll':('engine','rd-rend2_x86_64.dll'),
 'jampgamex86_64.dll':('game','jampgamex86_64.dll'),
 'cgamex86_64.dll':('frontend','cgamex86_64.dll'),
 'uix86_64.dll':('frontend','uix86_64.dll')}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
def write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(data)
def record(path,data):write(path,json.dumps(data))
def tree(path):return {p.relative_to(path).as_posix():sha(p) for p in path.rglob('*') if p.is_file()}
def load(path):
 spec=importlib.util.spec_from_file_location('updater_fixture',path)
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

class HybridUpdate(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='st_hybrid_update_');self.root=Path(self.temp.name)
  for name in ('Install-Hybrid-Styles.py','Update-Hybrid-Styles.py','Install-Handedness.py'):
   write(self.root/'tools'/name,(ROOT/'tools'/name).read_text())
  write(self.root/'tools/Build-Hybrid-Styles.py',"from pathlib import Path\nimport json\nOUT=Path(__file__).resolve().parents[1]/'dist/hybrid-candidate-02'\ndef verify():return json.loads((OUT/'manifest.json').read_text())\n")
  for n in (1,2):
   folder=self.root/f'dist/hybrid-candidate-0{n}';sources={};builds={k:{} for k in ('engine','game','frontend')}
   for target,(kind,name) in BINARIES.items():
    src=folder/f'build-{kind}/Release'/name;write(src,f'version{n}/{name}');sources[target]=src;builds[kind][name]=sha(src)
   for name in ('ui/jamp/saber.menu','ui/jamp/ingame_saber.menu'):
    src=folder/'menus'/name;write(src,f'menu{n}/{name}');sources[name]=src
   for name in ('zz_sabertrials_stances_v1.pk3', 'zzz_sabertrials_hybrid_v1.pk3' if n==1 else 'zz_sabertrials_styles_v1.pk3'):
    src=folder/'assets'/name;write(src,'stances' if 'stances_' in name else f'asset{n}');sources[name]=src
   for kind in builds:write(folder/kind/'source.c',f'source{n}/{kind}')
   m=dict(inputs={'obsolete-worktree-input':'historical'},builds=builds,sources={k:tree(folder/k) for k in builds},menus=tree(folder/'menus'),assets=tree(folder/'assets'))
   record(folder/'manifest.json',m)
   if n==1:self.old_sources=sources
  before={};after={};backup=self.root/'dist/backups/first'
  for target,source in self.old_sources.items():
   write(self.root/target,source.read_text());after[target]=sha(source)
   if target.endswith('.pk3'):before[target]=None
   else:write(backup/target,'original/'+target);before[target]=sha(backup/target)
  write(self.root/'server.cfg','user server preferences')
  self.cfg=self.root/'documents/My Games/OpenJK/SaberTrials/openjk_mp.cfg';write(self.cfg,'user binds')
  self.original=dict(before)
  state=dict(installed=True,restored=False,before=before,after=after,backup=str(backup),sources={k:str(v) for k,v in self.old_sources.items()},protected={'server.cfg':sha(self.root/'server.cfg')},source_manifest=str(self.root/'dist/hybrid-candidate-01/manifest.json'),source_manifest_sha256=sha(self.root/'dist/hybrid-candidate-01/manifest.json'))
  record(self.root/'dist/hybrid-install.json',state)
  self.receipt=(self.root/'dist/hybrid-install.json').read_bytes()
  self.old_tree=tree(self.root/'dist/hybrid-candidate-01')
  self.mod=load(self.root/'tools/Update-Hybrid-Styles.py')
  def fake_os(cmd,**kwargs):return str(self.root/'documents') if 'GetFolderPath' in cmd[-1] else ''
  self.os_patch=patch('subprocess.check_output',side_effect=fake_os);self.os_patch.start()
 def tearDown(self):self.os_patch.stop();self.temp.cleanup()
 def test_update_and_restore_preserve_previous_receipt_sources_and_settings(self):
  self.mod.install(True)
  self.assertEqual((self.root/'dist/hybrid-install.json').read_bytes(),self.receipt)
  self.assertEqual(tree(self.root/'dist/hybrid-candidate-01'),self.old_tree)
  self.assertEqual(self.cfg.read_text(),'user binds')
  self.assertEqual((self.root/'server.cfg').read_text(),'user server preferences')
  self.assertTrue((self.root/'zz_sabertrials_styles_v1.pk3').is_file())
  self.assertTrue((self.root/'zzz_sabertrials_hybrid_v1.pk3').is_file())
  self.mod.verify_installed()
  latest=self.mod.LEGACY.verify_installed()
  self.assertEqual(latest['after']['uix86_64.dll'],sha(self.root/'dist/hybrid-candidate-02/build-frontend/Release/uix86_64.dll'))
  self.mod.restore()
  for name,source in self.old_sources.items():self.assertEqual(sha(self.root/name),sha(source))
  self.assertFalse((self.root/'zz_sabertrials_styles_v1.pk3').exists())
  self.assertEqual((self.root/'dist/hybrid-install.json').read_bytes(),self.receipt)
  self.mod.LEGACY.verify_installed()
 def test_old_restore_unwinds_latest_update_before_original_baseline(self):
  self.mod.install(True)
  self.mod.LEGACY.restore()
  for name,digest in self.original.items():self.assertEqual(sha(self.root/name),digest)
  self.assertTrue(json.loads((self.root/'dist/hybrid-loadout-install.json').read_text())['restored'])
  self.assertTrue(json.loads((self.root/'dist/hybrid-install.json').read_text())['restored'])
  self.assertEqual(self.cfg.read_text(),'user binds')
 def test_install_failure_restores_every_replaced_file(self):
  real=self.mod.TX.install_transaction;real_replace=self.mod.TX.os.replace
  failed=[False]
  def fail_once(source,target):
   if Path(target)==self.root/'cgamex86_64.dll' and not failed[0]:failed[0]=True;raise OSError('injected replacement failure')
   return real_replace(source,target)
  def transaction(*args,**kwargs):return real(*args,**kwargs,replace=fail_once)
  with patch.object(self.mod.TX,'install_transaction',transaction):
   with self.assertRaisesRegex(OSError,'injected'):self.mod.install(True)
  for name,source in self.old_sources.items():self.assertEqual(sha(self.root/name),sha(source))
  self.assertFalse((self.root/'dist/hybrid-loadout-install.json').exists())
  self.assertEqual((self.root/'dist/hybrid-install.json').read_bytes(),self.receipt)
 def test_recorded_artifact_drift_stops_update_before_any_replacement(self):
  write(self.root/'dist/hybrid-candidate-01/game/source.c','changed historical source')
  with self.assertRaisesRegex(RuntimeError,'source drift'):self.mod.install(True)
  self.assertFalse((self.root/'dist/hybrid-loadout-install.json').exists())
  for name,source in self.old_sources.items():self.assertEqual(sha(self.root/name),sha(source))

if __name__=='__main__':unittest.main()
