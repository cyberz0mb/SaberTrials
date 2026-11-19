import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


class AccountPackageTests(unittest.TestCase):
    def test_package_excludes_runtime_secrets_and_existing_destination(self):
        self.assertIsNotNone(importlib.util.find_spec('services.accounts.packaging'))
        from services.accounts.packaging import build
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='st-package-') as folder:
            root = Path(folder) / 'source'
            shutil.copytree(repo / 'services', root / 'services', ignore=shutil.ignore_patterns('__pycache__', 'private', '*.sqlite', '.env'))
            (root / 'services/accounts/.env').write_text('SECRET=never-ship')
            private = root / 'services/accounts/private'
            private.mkdir()
            (private / 'server-key.json').write_text('{"server_token":"never-ship"}')
            output = Path(folder) / 'package'
            build(root, output)
            self.assertTrue((output / 'Dockerfile').is_file())
            self.assertTrue((output / 'services/accounts/http.py').is_file())
            self.assertTrue((output / 'railway.json').is_file())
            manifest = json.loads((output / 'manifest.json').read_text())
            for name, digest in manifest['files'].items():
                content = (output / name).read_bytes()
                self.assertEqual(hashlib.sha256(content).hexdigest(), digest)
                self.assertNotIn(b'never-ship', content)
            self.assertFalse((output / 'services/accounts/private').exists())
            self.assertFalse((output / 'services/accounts/.env').exists())
            self.assertFalse((output / 'services/discord').exists())
            with self.assertRaises(FileExistsError): build(root, output)
