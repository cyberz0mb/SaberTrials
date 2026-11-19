"""Exercise upgrade/rollback over all accepted layers using disposable files."""
from pathlib import Path
import json
import shutil
import unittest
from unittest.mock import patch
import test_hybrid_update as fixture
import test_hybrid_ui_buffer_install as buffer_fixture

class FeedbackUpdate(unittest.TestCase):
    def setUp(self):
        self.base = buffer_fixture.HybridUIBufferFix()
        self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.base.mod.install(True)
        self.root = self.base.root
        self.before = fixture.tree(self.root)
        tool = 'Update-Hybrid-Feedback.py'
        fixture.write(self.root/'tools'/tool,(fixture.ROOT/'tools'/tool).read_text())
        parent=self.root/'dist/hybrid-candidate-02'
        candidate=self.root/'dist/hybrid-candidate-03'
        shutil.copytree(parent,candidate)
        manifest=json.loads((candidate/'manifest.json').read_text())
        for kind in manifest['builds']:
            fixture.write(candidate/kind/'source.c',kind+' feedback revision')
            manifest['sources'][kind]=fixture.tree(candidate/kind)
            for name in manifest['builds'][kind]:
                path=candidate/f'build-{kind}/Release'/name
                fixture.write(path,'feedback '+name)
                manifest['builds'][kind][name]=fixture.sha(path)
        fixture.record(candidate/'manifest.json',manifest)
        fixture.write(self.root/'tools/Build-Hybrid-Feedback.py',
            "from pathlib import Path\nimport json\nOUT=Path(__file__).resolve().parents[1]/'dist/hybrid-candidate-03'\ndef verify():return json.loads((OUT/'manifest.json').read_text())\n")
        self.mod=fixture.load(self.root/'tools'/tool)

    def test_install_preserves_history_settings_and_restores_exact_previous_build(self):
        self.mod.install(True)
        for name,digest in self.before.items():
            if name.startswith(('dist/hybrid-candidate-01/','dist/hybrid-candidate-02/','dist/hybrid-ui-buffer-fix/')) or name.endswith('install.json'):
                self.assertEqual(fixture.sha(self.root/name),digest,name)
        latest=self.mod.LEGACY.verify_installed()
        self.assertEqual(latest['after']['cgamex86_64.dll'],fixture.sha(self.root/'cgamex86_64.dll'))
        self.mod.restore()
        for name in fixture.BINARIES:
            self.assertEqual(fixture.sha(self.root/name),self.before[name],name)
        self.assertEqual(self.base.base.cfg.read_text(),'user binds')
        self.assertEqual((self.root/'server.cfg').read_text(),'user server preferences')

    def test_original_restore_unwinds_all_four_layers(self):
        self.mod.install(True)
        self.mod.LEGACY.restore()
        for name,digest in self.base.base.original.items():
            self.assertEqual(fixture.sha(self.root/name),digest,name)
        for name in ('hybrid-feedback-install.json','hybrid-ui-buffer-install.json','hybrid-loadout-install.json','hybrid-install.json'):
            self.assertTrue(json.loads((self.root/'dist'/name).read_text())['restored'],name)

    def test_replacement_failure_rolls_back_all_new_modules(self):
        real=self.mod.TX.install_transaction
        real_replace=self.mod.TX.os.replace
        failed=[False]
        def fail_once(source,target):
            if Path(target)==self.root/'jampgamex86_64.dll' and not failed[0]:
                failed[0]=True
                raise OSError('injected module failure')
            return real_replace(source,target)
        def transaction(*args,**kwargs):return real(*args,**kwargs,replace=fail_once)
        with patch.object(self.mod.TX,'install_transaction',transaction):
            with self.assertRaisesRegex(OSError,'injected module'):self.mod.install(True)
        for name in fixture.BINARIES:
            self.assertEqual(fixture.sha(self.root/name),self.before[name],name)
        self.assertFalse(self.mod.STATE.exists())
        self.base.mod.verify_installed()

    def test_earlier_backup_corruption_stops_before_installation(self):
        receipt=json.loads((self.root/'dist/hybrid-ui-buffer-install.json').read_text())
        fixture.write(Path(receipt['backup'])/'uix86_64.dll','corrupt')
        with self.assertRaisesRegex(RuntimeError,'backup differs'):self.mod.install(True)
        for name in fixture.BINARIES:
            self.assertEqual(fixture.sha(self.root/name),self.before[name],name)
        self.assertFalse(self.mod.STATE.exists())

if __name__=='__main__':unittest.main()
