"""Connection proofs must belong to the server and slot the player joined."""
import unittest
from tests import test_accounts as fixtures
from services.accounts.store import AccountError


class BindingTests(unittest.TestCase):
    setUp = fixtures.AccountTests.setUp
    tearDown = fixtures.AccountTests.tearDown
    require = fixtures.AccountTests.require
    verified = fixtures.AccountTests.verified
    signed_in = fixtures.AccountTests.signed_in
    server = fixtures.AccountTests.server
    def bound(self):
        login = self.signed_in()
        key = self.server()
        configure = getattr(self.store, 'set_server_endpoint', None)
        self.assertTrue(callable(configure), 'Approved servers need an endpoint binding')
        configure('temple', '192.0.2.10:29070')
        c = self.store.challenge(key, 'boot-1', 3, 'a' * 32, client_nonce='b' * 32)
        return key, login['session_token'], c['challenge']

    def test_bound_request_rejects_relay_to_another_server(self):
        key, session, challenge = self.bound()
        for endpoint, nonce, slot in [('192.0.2.11:29070', 'b' * 32, 3),
                                      ('192.0.2.10:29071', 'b' * 32, 3),
                                      ('192.0.2.10:29070', 'c' * 32, 3),
                                      ('192.0.2.10:29070', 'b' * 32, 4)]:
            with self.assertRaises(AccountError):
                self.store.authorize_connection(session, challenge, endpoint, nonce, slot)
        self.store.authorize_connection(session, challenge, '192.0.2.10:29070', 'b' * 32, 3)
        lease = self.store.redeem(key, challenge, 'boot-1', 3, 'a' * 32)
        self.assertEqual(lease['profile']['name'], 'Jawa')

    def test_legacy_authorization_cannot_bypass_binding(self):
        _, session, challenge = self.bound()
        with self.assertRaises(AccountError):
            self.store.authorize_connection(session, challenge)

    def test_address_change_revokes_existing_proofs(self):
        key, session, challenge = self.bound()
        self.store.authorize_connection(session, challenge, '192.0.2.10:29070', 'b' * 32, 3)
        lease = self.store.redeem(key, challenge, 'boot-1', 3, 'a' * 32)
        self.store.set_server_endpoint('temple', '192.0.2.12:29070')
        with self.assertRaises(AccountError):
            self.store.renew(key, lease['lease_token'])

    def test_endpoint_requires_numeric_address_and_port(self):
        self.bound()
        for address in ['evil.test:29070', '192.0.2.1', '192.0.2.1:0', '192.0.2.1:65536',
                        '192.0.2.1:29070\n', 'https://192.0.2.1:29070']:
            with self.assertRaises(AccountError):
                self.store.set_server_endpoint('temple', address)


