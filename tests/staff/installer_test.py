"""Installation failure must restore old binaries and preserve unrelated assets."""
import importlib.util,os,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('installer',Path(__file__).resolve().parents[2]/'tools/Install-Staff.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)

class InstallerTests(unittest.TestCase):
    def test_partial_replace_rolls_back(self):
        with tempfile.TemporaryDirectory(prefix='staff-install-test-') as temp:
            root=Path(temp);source=root/'source';source.mkdir()
            for name in ('engine','game','cgame'):(root/name).write_bytes(b'old');(source/name).write_bytes(b'new')
            (root/'menu').write_bytes(b'protected');calls=[]
            def fail_second(src,dst):
                calls.append(dst)
                if len(calls)==2:raise PermissionError('injected locked target')
                os.replace(src,dst)
            with self.assertRaises(PermissionError):installer.transaction(root,{name:source/name for name in ('engine','game','cgame')},root/'backup',fail_second)
            self.assertTrue(all((root/name).read_bytes()==b'old' for name in ('engine','game','cgame')))
            self.assertEqual((root/'menu').read_bytes(),b'protected')
            self.assertFalse(list(root.glob('*.staff-pending')))
    def test_replacement_and_backup_hashes(self):
        with tempfile.TemporaryDirectory(prefix='staff-install-test-') as temp:
            root=Path(temp);(root/'engine').write_bytes(b'old');(root/'new').write_bytes(b'new')
            result=installer.transaction(root,{'engine':root/'new'},root/'backup')
            self.assertEqual((root/'engine').read_bytes(),b'new');self.assertEqual((root/'backup/engine').read_bytes(),b'old')
            self.assertEqual(result['after']['engine'],installer.digest(root/'engine'))
if __name__=='__main__':unittest.main()
