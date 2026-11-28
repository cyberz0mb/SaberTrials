import importlib.util
import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout, closing
from pathlib import Path
from services.accounts.store import AccountStore, AccountError


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='st-ops-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_startup_requires_https_credentials_and_explicit_existing_storage(self):
        self.assertIsNotNone(importlib.util.find_spec('services.accounts.runtime'))
        from services.accounts.runtime import configure
        valid = {'PUBLIC_BASE_URL': 'https://login.example.test', 'DISCORD_CLIENT_ID': '1562891535312355419',
                 'DISCORD_CLIENT_SECRET': 'test-only', 'ST_DATA_DIR': str(self.root), 'PORT': '8080'}
        for key in ['PUBLIC_BASE_URL', 'DISCORD_CLIENT_SECRET', 'ST_DATA_DIR']:
            env = valid.copy()
            del env[key]
            with self.subTest(key=key), self.assertRaises(ValueError): configure(env)
        for changes in [{'PUBLIC_BASE_URL': 'http://example.test'}, {'PORT': '-1'},
                        {'ST_DATA_DIR': str(self.root / 'missing')}, {'ST_TRUSTED_PROXY': '*'}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError): configure(dict(valid, **changes))
        config = configure(valid)
        self.assertEqual(config['path'], self.root / 'accounts.sqlite')
        self.assertEqual(config['port'], 8080)

    def test_server_enrollment_writes_key_only_to_new_private_file_and_revokes(self):
        self.assertIsNotNone(importlib.util.find_spec('services.accounts.operator'))
        from services.accounts.operator import main
        db, keyfile = self.root / 'accounts.sqlite', self.root / 'server-key.json'
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(['--database', str(db), 'server-add', 'temple', 'Temple', '--out', str(keyfile)]), 0)
        key = json.loads(keyfile.read_text())['server_token']
        self.assertNotIn(key, output.getvalue())
        original = keyfile.read_bytes()
        with self.assertRaises(FileExistsError):
            main(['--database', str(db), 'server-rotate', 'temple', '--out', str(keyfile)])
        self.assertEqual(keyfile.read_bytes(), original)
        store = AccountStore(db)
        self.addCleanup(store.close)
        try:
            result = store.challenge(key, 'boot-1', 0, 'a' * 32)
        except AccountError:
            self.fail('Duplicate enrollment must leave the existing server authorized')
        self.assertEqual(result['server'], 'temple')
        with redirect_stdout(output):
            main(['--database', str(db), 'server-disable', 'temple'])
        with self.assertRaises(AccountError): store.challenge(key, 'boot-1', 0, 'a' * 32)

    def test_operator_can_approve_game_endpoint(self):
        from services.accounts.operator import main
        db = self.root / 'accounts.sqlite'
        store = AccountStore(db)
        self.addCleanup(store.close)
        key = store.enroll_server('temple', 'Temple')
        try:
            with redirect_stdout(io.StringIO()):
                main(['--database', str(db), 'server-address', 'temple', '192.0.2.10:29070'])
        except SystemExit:
            self.fail('Operator must support approving a game endpoint')
        self.assertEqual(store.challenge(key, 'boot', 0, 'a' * 32, client_nonce='b' * 32)['server'], 'temple')

    def test_startup_migration_preserves_a_recoverable_old_database(self):
        from services.accounts import runtime
        prepare = getattr(runtime, 'prepare_store', None)
        self.assertTrue(callable(prepare), 'Startup needs a pre-migration snapshot')
        db = self.root / 'accounts.sqlite'
        old = AccountStore(db)
        old.ledger.register_verified_player('saved-player', 'Saved Player')
        # Recreate the original empty challenge table on every supported SQLite version.
        old.db.execute('DROP TABLE account_challenges')
        old.db.execute('''CREATE TABLE account_challenges(
            hash TEXT PRIMARY KEY, server TEXT NOT NULL REFERENCES servers(id),
            instance TEXT NOT NULL, slot INTEGER NOT NULL, generation TEXT NOT NULL,
            expires REAL NOT NULL, session TEXT REFERENCES account_sessions(hash) ON DELETE CASCADE)''')
        old.db.execute('DROP TABLE account_server_endpoints')
        old.close()
        prepare(db)
        backups = list(self.root.glob('accounts-before-connection-binding-*.sqlite'))
        self.assertEqual(len(backups), 1)
        with closing(sqlite3.connect(backups[0])) as snapshot:
            self.assertEqual(snapshot.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(snapshot.execute('SELECT name FROM players').fetchone()[0], 'Saved Player')
            self.assertNotIn('client_nonce', [r[1] for r in snapshot.execute('PRAGMA table_info(account_challenges)')])
        prepare(db)
        self.assertEqual(list(self.root.glob('accounts-before-connection-binding-*.sqlite')), backups)
        current = AccountStore(db)
        self.addCleanup(current.close)
        self.assertEqual(current.db.execute('SELECT name FROM players').fetchone()[0], 'Saved Player')

    def test_consistent_backup_is_restorable_and_does_not_overwrite(self):
        self.assertIsNotNone(importlib.util.find_spec('services.accounts.operator'))
        from services.accounts.operator import main
        db, backup = self.root / 'accounts.sqlite', self.root / 'backup.sqlite'
        store = AccountStore(db)
        key = store.enroll_server('temple', 'Temple')
        store.close()
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(['--database', str(db), 'backup', '--out', str(backup)]), 0)
        restored = AccountStore(backup)
        self.addCleanup(restored.close)
        self.assertEqual(restored.challenge(key, 'boot-2', 0, 'b' * 32)['server'], 'temple')
        with self.assertRaises(FileExistsError):
            main(['--database', str(db), 'backup', '--out', str(backup)])

    def test_duplicate_enrollment_cannot_disable_existing_server(self):
        from services.accounts.operator import main
        db = self.root / 'accounts.sqlite'
        store = AccountStore(db)
        self.addCleanup(store.close)
        key = store.enroll_server('temple', 'Temple')
        with self.assertRaises(sqlite3.IntegrityError):
            main(['--database', str(db), 'server-add', 'temple', 'Duplicate', '--out', str(self.root / 'new-key.json')])
        try:
            result = store.challenge(key, 'boot-1', 0, 'a' * 32)
        except AccountError:
            self.fail('Duplicate enrollment must leave the existing server authorized')
        self.assertEqual(result['server'], 'temple')
