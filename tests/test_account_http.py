"""Exercise the WSGI app and real DB; only Discord's external API is replaced."""
import importlib.util
import io
import inspect
import json
import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from services.accounts.store import AccountStore


class DiscordFixture:
    def authorization_url(self, state):
        return 'https://discord.com/oauth2/authorize?' + urlencode({'state': state})

    def identity(self, code):
        if code != 'valid-code':
            raise ValueError('Provider rejected credential SECRET-DO-NOT-ECHO')
        return '123456789012345678'


class AccountHTTPTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('services.accounts.http'), 'HTTP login application must exist')
        from services.accounts.http import AccountApplication
        self.temp = tempfile.TemporaryDirectory(prefix='st-http-')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'accounts.sqlite'
        self.now = 1000
        self.app = AccountApplication(self.path, 'https://login.example.test', DiscordFixture(), clock=lambda: self.now)

    def request(self, method, path, data=None, *, cookie='', auth='', origin=None, raw=None, content_type=None, host='login.example.test', real_ip=None):
        parsed = urlsplit(path)
        if raw is None:
            raw = json.dumps(data or {}).encode() if method == 'POST' else b''
        env = {'REQUEST_METHOD': method, 'PATH_INFO': parsed.path, 'QUERY_STRING': parsed.query,
               'CONTENT_LENGTH': str(len(raw)), 'CONTENT_TYPE': content_type or 'application/json',
               'wsgi.input': io.BytesIO(raw), 'wsgi.url_scheme': 'https',
               'HTTP_HOST': host, 'REMOTE_ADDR': '127.0.0.1',
               'HTTP_COOKIE': cookie, 'HTTP_AUTHORIZATION': 'Bearer ' + auth if auth else ''}
        if origin is not None:
            env['HTTP_ORIGIN'] = origin
        if real_ip is not None:
            env['HTTP_X_REAL_IP'] = real_ip
        result = {}
        def start(status, headers):
            result['status'] = int(status.split()[0])
            result['headers'] = dict(headers)
        result['body'] = b''.join(self.app(env, start)).decode()
        return result

    def begin(self):
        r = self.request('POST', '/v1/login/start')
        self.assertEqual(r['status'], 200)
        return json.loads(r['body'])

    def browser(self, link):
        r = self.request('GET', link['browser_url'])
        self.assertEqual(r['status'], 303)
        cookie = r['headers']['Set-Cookie']
        for flag in ['HttpOnly', 'Secure', 'SameSite=Lax', 'Path=/']:
            self.assertIn(flag, cookie)
        state = parse_qs(urlsplit(r['headers']['Location']).query)['state'][0]
        return cookie.split(';')[0], state

    def callback(self, cookie, state, code='valid-code'):
        return self.request('GET', '/oauth/callback?' + urlencode({'state': state, 'code': code, 'iss': 'https://discord.com'}), cookie=cookie)

    def sign_in(self):
        link = self.begin()
        cookie, state = self.browser(link)
        r = self.callback(cookie, state)
        self.assertEqual(r['status'], 200)
        csrf = re.search(r'name="csrf" value="([A-Za-z0-9_-]+)"', r['body']).group(1)
        r = self.request('POST', '/confirm', cookie=cookie, origin='https://login.example.test',
                         raw=urlencode({'csrf': csrf, 'name': 'Jawa'}).encode(),
                         content_type='application/x-www-form-urlencoded')
        self.assertEqual(r['status'], 200)
        r = self.request('POST', '/v1/login/poll', {'request_id': link['request_id'], 'poll_token': link['poll_token']})
        self.assertEqual(r['status'], 200)
        return json.loads(r['body'])

    def test_browser_sign_in_then_bearer_profile_and_logout(self):
        login = self.sign_in()
        r = self.request('GET', '/v1/me', auth=login['session_token'])
        self.assertEqual(r['status'], 200)
        self.assertEqual(json.loads(r['body'])['name'], 'Jawa')
        self.assertNotIn('123456789012345678', r['body'])
        self.assertEqual(r['headers']['Cache-Control'], 'no-store')
        self.assertEqual(r['headers']['Referrer-Policy'], 'no-referrer')
        self.assertEqual(self.request('POST', '/v1/logout', auth=login['session_token'])['status'], 200)
        self.assertEqual(self.request('GET', '/v1/me', auth=login['session_token'])['status'], 403)

    def test_no_auth_secrets_in_browser_url(self):
        link = self.begin()
        self.assertNotIn(link['poll_token'], link['browser_url'])
        self.assertNotIn('session_token', link)
        r = self.request('GET', '/v1/me?token=' + link['poll_token'])
        self.assertEqual(r['status'], 403)

    def test_callback_wrong_browser_replay_and_provider_failure_fail_closed(self):
        link = self.begin()
        cookie, state = self.browser(link)
        self.assertEqual(self.callback('', state)['status'], 403)
        self.assertEqual(self.callback(cookie, 'x' * 43)['status'], 403)
        r = self.callback(cookie, state, code='bad-code')
        self.assertEqual(r['status'], 502)
        self.assertNotIn('SECRET-DO-NOT-ECHO', r['body'])
        self.assertEqual(self.callback(cookie, state)['status'], 403)
        r = self.request('POST', '/v1/login/poll', {'request_id': link['request_id'], 'poll_token': link['poll_token']})
        self.assertEqual(json.loads(r['body']), {'status': 'pending'})

    def test_confirmation_blocks_cross_site_posts(self):
        link = self.begin()
        cookie, state = self.browser(link)
        r = self.callback(cookie, state)
        csrf = re.search(r'name="csrf" value="([A-Za-z0-9_-]+)"', r['body']).group(1)
        for origin in ('https://evil.test', 'null', None):
            with self.subTest(origin=origin):
                r = self.request('POST', '/confirm', cookie=cookie, origin=origin,
                                 raw=urlencode({'csrf': csrf, 'name': 'Jawa'}).encode(),
                                 content_type='application/x-www-form-urlencoded')
                self.assertEqual(r['status'], 403)

    def test_confirmation_page_preserves_form_origin_without_referring_oauth_code(self):
        link = self.begin()
        cookie, state = self.browser(link)
        r = self.callback(cookie, state)
        self.assertEqual(r['status'], 200)
        # A no-referrer document makes a browser's navigation POST send Origin:
        # null (Fetch standard). strict-origin retains Origin without sharing
        # the callback path/query, including the OAuth authorization code.
        self.assertEqual(r['headers']['Referrer-Policy'], 'strict-origin')
        csrf = re.search(r'name="csrf" value="([A-Za-z0-9_-]+)"', r['body']).group(1)
        r = self.request('POST', '/confirm', cookie=cookie, origin='https://login.example.test',
                         raw=urlencode({'csrf': csrf, 'name': 'Jawa'}).encode(),
                         content_type='application/x-www-form-urlencoded')
        self.assertEqual(r['status'], 200)
        self.assertIn('You’re signed in', r['body'])
        self.assertEqual(r['headers']['Referrer-Policy'], 'no-referrer')

    def test_http_connection_handshake_does_not_give_game_server_player_session(self):
        login = self.sign_in()
        store = AccountStore(self.path, clock=lambda: self.now)
        try:
            key = store.enroll_server('temple', 'Temple')
        finally:
            store.close()
        r = self.request('POST', '/v1/server/challenge', {'instance': 'boot-1', 'slot': 2, 'generation': 'a' * 32}, auth=key)
        self.assertEqual(r['status'], 200)
        challenge = json.loads(r['body'])['challenge']
        r = self.request('POST', '/v1/connection/authorize', {'challenge': challenge}, auth=login['session_token'])
        self.assertEqual(r['status'], 200)
        r = self.request('POST', '/v1/server/redeem', {'challenge': challenge, 'instance': 'boot-1', 'slot': 2, 'generation': 'a' * 32}, auth=key)
        self.assertEqual(r['status'], 200)
        lease = json.loads(r['body'])
        self.assertEqual(lease['profile']['account'], login['profile']['account'])
        self.assertNotIn(login['session_token'], r['body'])
        r = self.request('POST', '/v1/server/renew', {'lease_token': lease['lease_token']}, auth=key)
        self.assertEqual(r['status'], 200)

    def test_v2_connection_checks_observed_address_nonce_and_slot(self):
        login = self.sign_in()
        store = AccountStore(self.path, clock=lambda: self.now)
        try:
            key = store.enroll_server('temple', 'Temple')
            store.set_server_endpoint('temple', '192.0.2.10:29070')
        finally:
            store.close()
        data = {'instance': 'boot-1', 'slot': 2, 'generation': 'a' * 32, 'client_nonce': 'b' * 32}
        r = self.request('POST', '/v2/server/challenge', data, auth=key)
        self.assertEqual(r['status'], 200)
        challenge = json.loads(r['body'])['challenge']
        auth = {'challenge': challenge, 'endpoint': '192.0.2.10:29070', 'client_nonce': 'b' * 32, 'slot': 2}
        for bad in [dict(auth, endpoint='192.0.2.11:29070'), dict(auth, client_nonce=None),
                    dict(auth, slot=True), {'challenge': challenge}]:
            self.assertIn(self.request('POST', '/v2/connection/authorize', bad, auth=login['session_token'])['status'], (400, 403))
        self.assertEqual(self.request('POST', '/v2/connection/authorize', auth, auth=login['session_token'])['status'], 200)

    def test_malformed_oversized_and_unknown_payloads_are_rejected(self):
        for raw in [b'null', b'[]', b'{', b'{"unexpected":"data"}', b'x' * 20000,
                    b'{"a":1,"a":2}']:
            with self.subTest(raw=raw[:30]):
                self.assertIn(self.request('POST', '/v1/login/start', raw=raw)['status'], (400, 413))
        self.assertEqual(self.request('POST', '/v1/login/start', content_type='text/plain')['status'], 415)
        self.assertEqual(self.request('POST', '/v1/operator/enroll-server')['status'], 404)

    def test_login_creation_rate_limited_and_recovers(self):
        statuses = [self.request('POST', '/v1/login/start')['status'] for _ in range(25)]
        self.assertIn(429, statuses)
        self.now += 61
        self.assertEqual(self.request('POST', '/v1/login/start')['status'], 200)

    def test_spoofed_host_is_rejected_and_health_has_no_secrets(self):
        self.assertEqual(self.request('POST', '/v1/login/start', host='evil.test')['status'], 400)
        r = self.request('GET', '/healthz')
        self.assertEqual(r['status'], 200)
        self.assertEqual(json.loads(r['body']), {'status': 'ok'})
        from services.accounts.http import AccountApplication
        for url in ['http://login.example.test', 'https://name:password@example.test', 'https://example.test/path']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                AccountApplication(self.path, url, DiscordFixture())

    def test_form_invalid_utf8_is_a_client_error(self):
        link = self.begin()
        cookie, state = self.browser(link)
        self.callback(cookie, state)
        r = self.request('POST', '/confirm', cookie=cookie, origin='https://login.example.test',
                         raw=b'csrf=\xff', content_type='application/x-www-form-urlencoded')
        self.assertEqual(r['status'], 400)

    def test_edge_ip_is_only_used_when_railway_ingress_is_explicitly_enabled(self):
        from services.accounts.http import AccountApplication
        self.assertIn('railway_edge', inspect.signature(AccountApplication).parameters)
        statuses = [self.request('POST', '/v1/login/start', real_ip=f'192.0.2.{i}')['status'] for i in range(1, 20)]
        self.assertIn(429, statuses, 'Untrusted headers must not bypass the default limiter')
        self.app = AccountApplication(self.path, 'https://login.example.test', DiscordFixture(),
                                      clock=lambda: self.now, railway_edge=True)
        statuses = [self.request('POST', '/v1/login/start', real_ip=f'192.0.2.{i}')['status'] for i in range(1, 20)]
        self.assertEqual(set(statuses), {200}, 'Distinct edge-verified users should not share one proxy quota')
        self.assertEqual(self.request('POST', '/v1/login/start', real_ip='invalid')['status'], 400)


class DiscordProviderTests(unittest.TestCase):
    def test_authorization_uses_identify_and_fixed_callback(self):
        self.assertIsNotNone(importlib.util.find_spec('services.accounts.discord'), 'Discord provider must exist')
        from services.accounts.discord import DiscordProvider
        provider = DiscordProvider('1562891535312355419', 'test-secret', 'https://login.example.test/oauth/callback')
        url = urlsplit(provider.authorization_url('x' * 43))
        self.assertEqual(url.netloc, 'discord.com')
        q = parse_qs(url.query)
        self.assertEqual(q['scope'], ['identify'])
        self.assertEqual(q['response_type'], ['code'])
        self.assertEqual(q['redirect_uri'], ['https://login.example.test/oauth/callback'])
        self.assertNotIn('test-secret', url.geturl())

    def test_identity_requires_discord_user_not_a_bot(self):
        self.assertIsNotNone(importlib.util.find_spec('services.accounts.discord'), 'Discord provider must exist')
        from services.accounts.discord import DiscordProvider, ProviderError
        from unittest.mock import patch
        # The network boundary is external. Real provider builds and validates requests/responses.
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        def response(value): return Response(json.dumps(value).encode())
        provider = DiscordProvider('1562891535312355419', 'test-secret', 'https://login.example.test/oauth/callback')
        for user, valid in [({'id': '123456789012345678', 'username': 'jawa', 'discriminator': '0', 'avatar': None}, True),
                            ({'id': '123456789012345678', 'bot': True}, False), ({'id': 123}, False)]:
            responses = [response({'access_token': 'discord-test-token', 'token_type': 'Bearer', 'scope': 'identify', 'expires_in': 604800, 'refresh_token': 'refresh'}), response(user)]
            with self.subTest(user=user), patch('services.accounts.discord.urlopen', side_effect=responses) as network:
                if valid:
                    self.assertEqual(provider.identity('code'), '123456789012345678')
                    token_request = network.call_args_list[0].args[0]
                    self.assertEqual(token_request.full_url, 'https://discord.com/api/v10/oauth2/token')
                    self.assertEqual(parse_qs(token_request.data.decode())['grant_type'], ['authorization_code'])
                    self.assertEqual(network.call_args_list[1].args[0].get_header('Authorization'), 'Bearer discord-test-token')
                else:
                    with self.assertRaises(ProviderError): provider.identity('code')
