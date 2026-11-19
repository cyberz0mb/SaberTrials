"""Account tests use temporary databases; no Discord or game processes."""
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from pathlib import Path
from services.accounts.store import AccountStore, AccountError


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='st-account-test-')
        self.path = Path(self.temp.name) / 'accounts.sqlite'
        self.now = 1000
        self.store = AccountStore(self.path, clock=lambda: self.now)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_login_link_cannot_be_used_as_poll_secret(self):
        link = self.store.begin()
        self.assertTrue(link.get('request_id'))
        self.assertTrue(link.get('browser_token'))
        self.assertTrue(link.get('poll_token'))
        self.assertNotEqual(link['browser_token'], link['poll_token'])
        with self.assertRaises(AccountError):
            self.store.poll(link['request_id'], link['browser_token'])
        self.assertEqual(self.store.poll(link['request_id'], link['poll_token']),
                         {'status': 'pending'})

    def test_link_expires_without_creating_an_account(self):
        link = self.store.begin()
        self.assertTrue(link.get('expires_at'))
        self.now = link['expires_at']
        with self.assertRaises(AccountError):
            self.store.open_browser(link['request_id'], link['browser_token'])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM players').fetchone()[0], 0)

    def test_pending_link_survives_restart_without_storing_raw_secrets(self):
        link = self.store.begin()
        self.assertTrue(link.get('poll_token'))
        self.store.close()
        self.store = AccountStore(self.path, clock=lambda: self.now)
        self.assertEqual(self.store.poll(link['request_id'], link['poll_token']),
                         {'status': 'pending'})
        saved = '\n'.join(self.store.db.iterdump())
        self.assertNotIn(link['poll_token'], saved)
        self.assertNotIn(link['browser_token'], saved)

    def test_browser_claim_is_single_use_and_cannot_use_poll_token(self):
        link = self.store.begin()
        self.assertTrue(link.get('browser_token'))
        with self.assertRaises(AccountError):
            self.store.open_browser(link['request_id'], link['poll_token'])
        claim = self.store.open_browser(link['request_id'], link['browser_token'])
        self.assertTrue(claim['browser_cookie'])
        self.assertTrue(claim['oauth_state'])
        with self.assertRaises(AccountError):
            self.store.open_browser(link['request_id'], link['browser_token'])

    def test_expired_poll_cannot_be_used(self):
        link = self.store.begin()
        self.assertTrue(link.get('expires_at'))
        self.now = link['expires_at']
        with self.assertRaises(AccountError):
            self.store.poll(link['request_id'], link['poll_token'])

    def require(self, name):
        method = getattr(self.store, name, None)
        self.assertTrue(callable(method), f'Account service must implement {name}')
        return method

    def verified(self, discord='123456789012345678'):
        link = self.store.begin()
        claim = self.store.open_browser(link['request_id'], link['browser_token'])
        self.require('consume_oauth')(link['request_id'], claim['browser_cookie'], claim['oauth_state'])
        form = self.require('verified_identity')(link['request_id'], claim['browser_cookie'], discord)
        return link, claim, form

    def signed_in(self, discord='123456789012345678', name='Jawa'):
        link, claim, form = self.verified(discord)
        self.require('approve')(link['request_id'], claim['browser_cookie'], form['csrf'], name)
        return self.store.poll(link['request_id'], link['poll_token'])

    def server(self, name='temple'):
        return self.require('enroll_server')(name, name.title())

    def connection(self, server, session):
        challenge = self.require('challenge')(server, 'boot-1', 3, 'a' * 32)
        self.require('authorize_connection')(session, challenge['challenge'])
        return challenge

    def test_callback_requires_original_browser_and_single_use_state(self):
        a = self.store.begin()
        b = self.store.begin()
        ca = self.store.open_browser(a['request_id'], a['browser_token'])
        cb = self.store.open_browser(b['request_id'], b['browser_token'])
        consume = self.require('consume_oauth')
        for cookie, state in [(cb['browser_cookie'], ca['oauth_state']),
                              (ca['browser_cookie'], cb['oauth_state'])]:
            with self.assertRaises(AccountError):
                consume(a['request_id'], cookie, state)
        consume(a['request_id'], ca['browser_cookie'], ca['oauth_state'])
        with self.assertRaises(AccountError):
            consume(a['request_id'], ca['browser_cookie'], ca['oauth_state'])

    def test_no_session_until_explicit_confirmation_then_only_one_delivery(self):
        link, claim, form = self.verified()
        self.assertEqual(self.store.poll(link['request_id'], link['poll_token']), {'status': 'pending'})
        with self.assertRaises(AccountError):
            self.require('approve')(link['request_id'], claim['browser_cookie'], 'x' * 43, 'Jawa')
        self.store.approve(link['request_id'], claim['browser_cookie'], form['csrf'], 'Jawa')
        login = self.store.poll(link['request_id'], link['poll_token'])
        self.assertEqual(login['status'], 'complete')
        self.assertEqual(login['profile']['name'], 'Jawa')
        self.assertNotIn('discord', login['profile'])
        with self.assertRaises(AccountError):
            self.store.poll(link['request_id'], link['poll_token'])
        self.assertNotIn(login['session_token'], '\n'.join(self.store.db.iterdump()))

    def test_discord_identity_is_stable_and_cannot_be_renamed_by_login(self):
        first = self.signed_in()
        second = self.signed_in(name='New Name')
        self.assertEqual(first['profile'], second['profile'])
        self.assertEqual(second['profile']['name'], 'Jawa')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM players').fetchone()[0], 1)

    def test_names_are_unique_and_safe_for_native_commands(self):
        self.signed_in()
        link, claim, form = self.verified('223456789012345678')
        approve = self.require('approve')
        for name in ['jAwA', '^1Admin', 'x;quit', 'x"y', 'x\\y', '\nName', 'é' * 40, '']:
            with self.subTest(name=name), self.assertRaises(AccountError):
                approve(link['request_id'], claim['browser_cookie'], form['csrf'], name)
        approve(link['request_id'], claim['browser_cookie'], form['csrf'], 'Another Jawa')
        self.assertEqual(self.store.poll(link['request_id'], link['poll_token'])['profile']['name'], 'Another Jawa')

    def test_disabled_account_cannot_relogin_or_use_old_session(self):
        login = self.signed_in()
        self.require('set_enabled')(login['profile']['account'], False)
        with self.assertRaises(AccountError):
            self.require('profile')(login['session_token'])
        with self.assertRaises(AccountError):
            self.signed_in()

    def test_logout_and_expiry_revoke_session(self):
        login = self.signed_in()
        self.require('logout')(login['session_token'])
        with self.assertRaises(AccountError):
            self.require('profile')(login['session_token'])
        login = self.signed_in()
        self.now = login['expires_at']
        with self.assertRaises(AccountError):
            self.store.profile(login['session_token'])

    def test_redeem_is_bound_to_server_and_exact_connection(self):
        login = self.signed_in()
        server, other = self.server(), self.server('other')
        challenge = self.connection(server, login['session_token'])
        redeem = self.require('redeem')
        for key, instance, slot, generation in [(other, 'boot-1', 3, 'a' * 32),
                (server, 'boot-2', 3, 'a' * 32), (server, 'boot-1', 4, 'a' * 32),
                (server, 'boot-1', 3, 'b' * 32)]:
            with self.subTest(slot=slot, instance=instance), self.assertRaises(AccountError):
                redeem(key, challenge['challenge'], instance, slot, generation)
        lease = redeem(server, challenge['challenge'], 'boot-1', 3, 'a' * 32)
        self.assertEqual(lease['profile'], login['profile'])
        self.assertEqual(lease['generation'], 'a' * 32)
        self.assertEqual(lease['slot'], 3)
        with self.assertRaises(AccountError):
            redeem(server, challenge['challenge'], 'boot-1', 3, 'a' * 32)
        with self.assertRaises(AccountError):
            self.require('renew')(other, lease['lease_token'])

    def test_challenge_requires_live_login_and_cannot_switch_accounts(self):
        a = self.signed_in()
        b = self.signed_in('223456789012345678', 'Luke')
        key = self.server()
        challenge = self.connection(key, a['session_token'])
        with self.assertRaises(AccountError):
            self.store.authorize_connection(b['session_token'], challenge['challenge'])
        self.require('logout')(a['session_token'])
        with self.assertRaises(AccountError):
            self.require('redeem')(key, challenge['challenge'], 'boot-1', 3, 'a' * 32)

    def test_leases_use_current_registered_team_and_fail_after_logout(self):
        login = self.signed_in()
        key = self.server()
        c = self.connection(key, login['session_token'])
        lease = self.require('redeem')(key, c['challenge'], 'boot-1', 3, 'a' * 32)
        self.store.ledger.register_team('jawa', 'Jawa Clan', '[JAWA]')
        self.store.ledger.set_membership(login['profile']['account'], 'jawa')
        updated = self.require('renew')(key, lease['lease_token'])
        self.assertEqual(updated['profile']['team'], 'jawa')
        self.assertEqual(updated['profile']['teamName'], '[JAWA]')
        self.assertNotIn('session_token', updated)
        self.require('logout')(login['session_token'])
        with self.assertRaises(AccountError):
            self.store.renew(key, lease['lease_token'])

    def test_revoked_server_and_rotated_key_stop_existing_leases(self):
        login = self.signed_in()
        key = self.server()
        c = self.connection(key, login['session_token'])
        lease = self.require('redeem')(key, c['challenge'], 'boot-1', 3, 'a' * 32)
        replacement = self.require('rotate_server')('temple')
        with self.assertRaises(AccountError):
            self.require('renew')(key, lease['lease_token'])
        with self.assertRaises(AccountError):
            self.store.renew(replacement, lease['lease_token'])
        self.store.ledger.set_server_enabled('temple', False)
        with self.assertRaises(AccountError):
            self.store.challenge(replacement, 'boot-1', 3, 'a' * 32)

    def test_expired_lease_requires_new_connection_proof(self):
        login = self.signed_in()
        key = self.server()
        c = self.connection(key, login['session_token'])
        lease = self.require('redeem')(key, c['challenge'], 'boot-1', 3, 'a' * 32)
        self.now = lease['expires_at']
        with self.assertRaises(AccountError):
            self.require('renew')(key, lease['lease_token'])

    def test_new_connection_generation_invalidates_old_challenge_and_lease(self):
        login = self.signed_in()
        key = self.server()
        c = self.connection(key, login['session_token'])
        lease = self.require('redeem')(key, c['challenge'], 'boot-1', 3, 'a' * 32)
        self.store.challenge(key, 'boot-1', 3, 'b' * 32)
        with self.assertRaises(AccountError):
            self.require('renew')(key, lease['lease_token'])

    def test_unapproved_server_cannot_issue_identity_challenge(self):
        with self.assertRaises(AccountError):
            self.require('challenge')('x' * 43, 'boot-1', 3, 'a' * 32)

    def test_concurrent_redemption_issues_only_one_lease(self):
        login = self.signed_in()
        key = self.server()
        c = self.connection(key, login['session_token'])
        self.require('redeem')
        barrier = Barrier(2)
        def redeem():
            store = AccountStore(self.path, clock=lambda: self.now)
            try:
                barrier.wait(timeout=10)
                return store.redeem(key, c['challenge'], 'boot-1', 3, 'a' * 32)
            except AccountError:
                return None
            finally:
                store.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: redeem(), range(2)))
        self.assertEqual(sum(r is not None for r in results), 1)

    def test_disabled_then_reenabled_account_cannot_collect_old_approved_login(self):
        original = self.signed_in()
        link, claim, form = self.verified()
        self.store.approve(link['request_id'], claim['browser_cookie'], form['csrf'], '')
        self.store.set_enabled(original['profile']['account'], False)
        self.store.set_enabled(original['profile']['account'], True)
        with self.assertRaises(AccountError):
            self.store.poll(link['request_id'], link['poll_token'])

    def test_concurrent_poll_delivers_a_single_session(self):
        link, claim, form = self.verified()
        self.store.approve(link['request_id'], claim['browser_cookie'], form['csrf'], 'Jawa')
        barrier = Barrier(2)
        def poll():
            store = AccountStore(self.path, clock=lambda: self.now)
            try:
                barrier.wait(timeout=10)
                return store.poll(link['request_id'], link['poll_token'])
            except AccountError:
                return None
            finally:
                store.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: poll(), range(2)))
        self.assertEqual(sum(r is not None for r in results), 1)

    def test_expired_challenge_cannot_authorize_and_bot_slot_shape_rejected(self):
        login = self.signed_in()
        key = self.server()
        for slot, generation in [(True, 'a' * 32), (64, 'a' * 32), (-1, 'a' * 32), (0, 'bad')]:
            with self.subTest(slot=slot, generation=generation), self.assertRaises(AccountError):
                self.store.challenge(key, 'boot-1', slot, generation)
        c = self.store.challenge(key, 'boot-1', 0, 'a' * 32)
        self.now = c['expires_at']
        with self.assertRaises(AccountError):
            self.store.authorize_connection(login['session_token'], c['challenge'])
