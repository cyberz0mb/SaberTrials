"""UI-only correction transactions in temporary fixtures; never launch the game."""
from pathlib import Path
import json
import shutil
import unittest
from unittest.mock import patch
import test_hybrid_update as fixture

class HybridUIBufferFix(unittest.TestCase):
 def setUp(self):
  self.base=fixture.HybridUpdate();self.base.setUp();self.addCleanup(self.base.tearDown)
  self.root=self.base.root;self.update=self.base.mod
  fixture.write(self.root/'tools/Fix-Hybrid-UI-Buffer.py',(fixture.ROOT/'tools/Fix-Hybrid-UI-Buffer.py').read_text())
  parent=self.root/'dist/hybrid-candidate-02'
  fixture.write(parent/'frontend/codemp/ui/ui_main.c','static char UIPAFtext[60000];\n')
  m=json.loads((parent/'manifest.json').read_text());m['sources']['frontend']=fixture.tree(parent/'frontend');fixture.record(parent/'manifest.json',m)
  self.update.install(True)
  self.previous_ui=fixture.sha(self.root/'uix86_64.dll')
  self.previous_receipts={p.name:p.read_bytes() for p in (self.root/'dist').glob('*install.json')}
  fix=self.root/'dist/hybrid-ui-buffer-fix';shutil.copytree(parent/'frontend',fix/'source')
  fixture.write(fix/'source/codemp/ui/ui_main.c','static char UIPAFtext[131072];\n')
  fixture.write(fix/'build/Release/uix86_64.dll','ui-buffer-correction')
  fixture.write(self.root/'tools/Build-Hybrid-UI-Buffer-Fix.py','build marker')
  m=dict(sources=fixture.tree(fix/'source'),inputs={'tools/Build-Hybrid-UI-Buffer-Fix.py':fixture.sha(self.root/'tools/Build-Hybrid-UI-Buffer-Fix.py')},builds={'uix86_64.dll':fixture.sha(fix/'build/Release/uix86_64.dll')},parent_manifest_sha256=fixture.sha(parent/'manifest.json'))
  fixture.record(fix/'manifest.json',m)
  self.mod=fixture.load(self.root/'tools/Fix-Hybrid-UI-Buffer.py')
 def test_only_ui_changes_and_immediate_restore_preserves_both_prior_layers(self):
  old={name:fixture.sha(self.root/name) for name in fixture.BINARIES if name!='uix86_64.dll'}
  self.mod.install(True)
  self.assertNotEqual(fixture.sha(self.root/'uix86_64.dll'),self.previous_ui)
  for name,digest in old.items():self.assertEqual(fixture.sha(self.root/name),digest)
  for name,data in self.previous_receipts.items():self.assertEqual((self.root/'dist'/name).read_bytes(),data)
  latest=self.update.LEGACY.verify_installed()
  self.assertEqual(set(latest['after']),{'uix86_64.dll'})
  self.mod.restore()
  self.assertEqual(fixture.sha(self.root/'uix86_64.dll'),self.previous_ui)
  for name,data in self.previous_receipts.items():self.assertEqual((self.root/'dist'/name).read_bytes(),data)
  self.assertEqual(self.base.cfg.read_text(),'user binds')
 def test_original_rollback_unwinds_all_three_layers(self):
  self.mod.install(True);self.update.LEGACY.restore()
  for name,digest in self.base.original.items():self.assertEqual(fixture.sha(self.root/name),digest)
  for name in ('hybrid-ui-buffer-install.json','hybrid-loadout-install.json','hybrid-install.json'):
   self.assertTrue(json.loads((self.root/'dist'/name).read_text())['restored'])
  self.assertEqual(self.base.cfg.read_text(),'user binds')
 def test_ui_hotfix_rejects_additional_source_changes(self):
  source=self.root/'dist/hybrid-ui-buffer-fix/source/source.c';source.write_text('unexpected gameplay change')
  manifest=self.root/'dist/hybrid-ui-buffer-fix/manifest.json';m=json.loads(manifest.read_text());m['sources']=fixture.tree(source.parent);fixture.record(manifest,m)
  with self.assertRaisesRegex(RuntimeError,'only the UI animation buffer'):self.mod.install(True)
  self.assertEqual(fixture.sha(self.root/'uix86_64.dll'),self.previous_ui)
 def test_receipt_failure_rolls_back_replaced_ui(self):
  real=self.mod.TX.install_transaction;real_replace=self.mod.TX.os.replace
  def fail_receipt(source,target):
   if Path(target)==self.root/'dist/hybrid-ui-buffer-install.json':raise OSError('injected receipt failure')
   return real_replace(source,target)
  def transaction(*args,**kwargs):return real(*args,**kwargs,replace=fail_receipt)
  with patch.object(self.mod.TX,'install_transaction',transaction):
   with self.assertRaisesRegex(OSError,'injected'):self.mod.install(True)
  self.assertEqual(fixture.sha(self.root/'uix86_64.dll'),self.previous_ui)
  self.assertFalse((self.root/'dist/hybrid-ui-buffer-install.json').exists())

if __name__=='__main__':unittest.main()
