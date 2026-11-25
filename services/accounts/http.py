"""Small WSGI boundary for player login and approved game-server identity leases.

No public operator, team-edit, or match-result submission routes. The server must
be behind HTTPS; all external URLs derive from one validated configured origin.
"""
from collections import OrderedDict
from html import escape
from http import HTTPStatus
from http.cookies import SimpleCookie, CookieError
import ipaddress
import json
import re
import logging
import sqlite3
import threading
import time
from urllib.parse import parse_qs, urlencode, urlsplit
from .store import AccountStore, AccountError

COOKIE = '__Host-st_login'
MAX_BODY = 16384
log = logging.getLogger(__name__)


class HTTPError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


class Limits:
    """Bounded per-process limiter. Deploy one process/replica with SQLite."""
    def __init__(self, clock):
        self.clock, self.lock, self.entries = clock, threading.Lock(), OrderedDict()

    def take(self, key, maximum):
        with self.lock:
            now = self.clock()
            count, expires = self.entries.get(key, (0, now + 60))
            if now >= expires:
                count, expires = 0, now + 60
            if count >= maximum:
                raise HTTPError(429, 'Too many requests; please wait a minute')
            self.entries[key] = (count + 1, expires)
            self.entries.move_to_end(key)
            while len(self.entries) > 10000:
                self.entries.popitem(last=False)


def origin_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        raise ValueError('PUBLIC_BASE_URL must be an HTTPS origin without a path or credentials')
    return value.rstrip('/')


def page(title, content):
    return f'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} · Saber Trials</title><style>
:root{{color-scheme:dark;font-family:system-ui,sans-serif;color:#c8e8f3;background:#071017}}
body{{margin:0;min-height:100vh;display:grid;place-items:center;background:radial-gradient(ellipse at top,#103447,transparent 70%)}}
main{{max-width:32rem;margin:2rem;padding:2.5rem;border-left:2px solid #43caff;background:#07121be6}}
small{{color:#43caff;letter-spacing:.22em}}h1{{font-size:1.8rem}}p{{line-height:1.6}}
label{{display:block;margin-top:1.5rem}}input{{display:block;box-sizing:border-box;width:100%;padding:.8rem;margin:.5rem 0 1.5rem;background:#061019;border:1px solid #458093;color:#fff;font:inherit}}
button{{padding:.9rem 1.4rem;background:#43caff;border:0;color:#05131b;font:inherit;font-weight:650;cursor:pointer}}
button:hover{{background:#a4e9ff}}a{{color:#65d5ff}}.hint{{font-size:.85rem;color:#92b3c4}}
</style><main><small>SABER TRIALS</small><h1>{escape(title)}</h1>{content}</main></html>'''


class AccountApplication:
    def __init__(self, path, public_url, provider, clock=time.time, railway_edge=False):
        self.path, self.public_url, self.provider, self.clock = path, origin_url(public_url), provider, clock
        self.host = urlsplit(self.public_url).netloc.lower()
        self.limits = Limits(clock)
        self.railway_edge = railway_edge

    def client_address(self, env):
        if self.railway_edge and env.get('PATH_INFO') != '/healthz':
            # Only enable on the dedicated Railway HTTP-edge-only service. No TCP
            # proxy or untrusted services may have direct access to this listener.
            try:
                return str(ipaddress.ip_address(env.get('HTTP_X_REAL_IP', '')))
            except ValueError:
                raise HTTPError(400, 'Valid ingress address required') from None
        return env.get('REMOTE_ADDR', 'unknown')

    def __call__(self, env, start_response):
        store = None
        headers = [('Cache-Control', 'no-store'), ('Referrer-Policy', 'no-referrer'),
                   ('X-Content-Type-Options', 'nosniff'), ('X-Frame-Options', 'DENY'),
                   ('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"),
                   ('Strict-Transport-Security', 'max-age=31536000')]
        try:
            path = env.get('PATH_INFO', '')
            # Health checks can use the platform's internal Host; all auth routes cannot.
            if path != '/healthz' and env.get('HTTP_HOST', '').lower() != self.host:
                raise HTTPError(400, 'Invalid host')
            origin = env.get('HTTP_ORIGIN')
            if origin is not None and origin != self.public_url:
                raise HTTPError(403, 'Cross-site request rejected')
            self.limits.take('global', 6000)
            self.limits.take(('ip', self.client_address(env)), 600)
            store = AccountStore(self.path, clock=self.clock)
            status, result, content_type, extra = self.route(store, env)
            if path == '/oauth/callback' and status == 200:
                # no-referrer makes navigation form POSTs send Origin: null.
                # Keep the real origin for /confirm while excluding the OAuth
                # callback path and code from any Referer header.
                headers = [(key, 'strict-origin' if key == 'Referrer-Policy' else value)
                           for key, value in headers]
            headers.extend(extra)
        except HTTPError as exc:
            status, result, content_type = exc.status, {'error': exc.message}, 'application/json'
        except AccountError as exc:
            status, result, content_type = 403, {'error': str(exc)}, 'application/json'
        except UnicodeError:
            status, result, content_type = 400, {'error': 'Invalid text encoding'}, 'application/json'
        except (sqlite3.Error, OSError):
            # No exception text, request URLs, headers or query strings in logs.
            log.error('Account storage unavailable')
            status, result, content_type = 503, {'error': 'Account service temporarily unavailable'}, 'application/json'
        except Exception:
            log.error('Account request failed')
            status, result, content_type = 500, {'error': 'Unable to complete request'}, 'application/json'
        finally:
            if store:
                store.close()
        if content_type == 'application/json':
            result = json.dumps(result, separators=(',', ':'), allow_nan=False)
        body = result.encode('utf-8')
        headers.extend([('Content-Type', content_type + '; charset=utf-8'), ('Content-Length', str(len(body)))])
        if status == 429:
            headers.append(('Retry-After', '60'))
        start_response(f'{status} {HTTPStatus(status).phrase}', headers)
        return [body]

    def route(self, store, env):
        method, path = env.get('REQUEST_METHOD'), env.get('PATH_INFO')
        if (method, path) == ('GET', '/healthz'):
            store.db.execute('SELECT 1').fetchone()
            return self.json({'status': 'ok'})
        if (method, path) == ('GET', '/'):
            return 200, page('Your Saber Trials account', '<p>Start sign-in from Saber Trials to link this device.</p><p>Your registered name follows you across approved servers.</p>'), 'text/html', []
        if (method, path) == ('GET', '/login'):
            q = query(env.get('QUERY_STRING', ''), {'request', 'token'})
            claim = store.open_browser(q['request'], q['token'])
            cookie = f'{COOKIE}={q["request"]}.{claim["browser_cookie"]}; Path=/; Max-Age=600; Secure; HttpOnly; SameSite=Lax'
            return 303, '', 'text/html', [('Location', self.provider.authorization_url(claim['oauth_state'])), ('Set-Cookie', cookie)]
        if (method, path) == ('GET', '/oauth/callback'):
            q = query(env.get('QUERY_STRING', ''), {'state'}, {'code', 'iss', 'error', 'error_description'})
            request_id, cookie = browser_cookie(env)
            if q.get('iss', 'https://discord.com') != 'https://discord.com':
                raise HTTPError(403, 'Invalid identity provider')
            store.consume_oauth(request_id, cookie, q['state'])
            if 'error' in q or 'code' not in q:
                raise HTTPError(403, 'Sign-in cancelled. Return to the game to start again')
            try:
                discord_id = self.provider.identity(q['code'])
            except Exception:
                raise HTTPError(502, 'Discord sign-in failed. Return to the game to start again') from None
            form = store.verified_identity(request_id, cookie, discord_id)
            if form['profile']:
                name = f'<p>Sign in as <strong>{escape(form["profile"]["name"])}</strong>.</p>'
            else:
                name = '<label for="name">Choose your ranked name</label><input id="name" name="name" maxlength="48" autocomplete="nickname" required>'
            html = page('Confirm game sign-in', '<p>Only continue if you started this sign-in from your own game. Do not approve a link someone sent you.</p>'
                f'<form action="/confirm" method="post"><input type="hidden" name="csrf" value="{form["csrf"]}">{name}'
                '<button type="submit">Sign in to Saber Trials</button></form><p class="hint">This device stays signed in for up to 7 days. You can log out in the game.</p>')
            return 200, html, 'text/html', []
        if (method, path) == ('POST', '/confirm'):
            if env.get('HTTP_ORIGIN') != self.public_url:
                raise HTTPError(403, 'Cross-site request rejected')
            request_id, cookie = browser_cookie(env)
            if env.get('CONTENT_TYPE', '').split(';')[0] != 'application/x-www-form-urlencoded':
                raise HTTPError(415, 'Expected a form')
            form = query(read_body(env).decode('utf-8'), {'csrf'}, {'name'})
            store.approve(request_id, cookie, form['csrf'], form.get('name', ''))
            return 200, page('You’re signed in', '<p>Return to Saber Trials to continue.</p>'), 'text/html', [
                ('Set-Cookie', f'{COOKIE}=; Path=/; Max-Age=0; Secure; HttpOnly; SameSite=Lax')]
        if (method, path) == ('GET', '/v1/me'):
            return self.json(store.profile(bearer(env)))
        routes = {
            '/v2/server/challenge': ({'instance', 'slot', 'generation', 'client_nonce'}, lambda d: store.challenge(bearer(env), **d)),
            '/v2/connection/authorize': ({'challenge', 'endpoint', 'client_nonce', 'slot'}, lambda d: store.authorize_connection(bearer(env), **d)),
            '/v1/login/start': (set(), lambda d: self.start_login(store, env)),
            '/v1/login/poll': ({'request_id', 'poll_token'}, lambda d: store.poll(d['request_id'], d['poll_token'])),
            '/v1/logout': (set(), lambda d: (store.logout(bearer(env)) or {'logged_out': True})),
            '/v1/connection/authorize': ({'challenge'}, lambda d: store.authorize_connection(bearer(env), d['challenge'])),
            '/v1/server/challenge': ({'instance', 'slot', 'generation'}, lambda d: store.challenge(bearer(env), **d)),
            '/v1/server/redeem': ({'challenge', 'instance', 'slot', 'generation'}, lambda d: store.redeem(bearer(env), **d)),
            '/v1/server/format-result': ({'event', 'mode', 'participants'}, lambda d: store.format_result(bearer(env), **d)),
            '/v1/server/renew': ({'lease_token'}, lambda d: store.renew(bearer(env), d['lease_token']))
        }
        if method != 'POST' or path not in routes:
            raise HTTPError(404, 'Not found')
        if env.get('CONTENT_TYPE', '').split(';')[0] != 'application/json':
            raise HTTPError(415, 'Expected JSON')
        try:
            data = json.loads(read_body(env), object_pairs_hook=unique_object,
                              parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        except (ValueError, UnicodeError):
            raise HTTPError(400, 'Invalid JSON') from None
        required, handler = routes[path]
        if not isinstance(data, dict) or set(data) != required:
            raise HTTPError(400, 'Invalid request fields')
        if path.startswith('/v2/') and (not isinstance(data.get('client_nonce'), str) or
                                       not re.fullmatch(r'[a-f0-9]{32}', data['client_nonce'])):
            raise HTTPError(400, 'Invalid connection nonce')
        return self.json(handler(data))

    def start_login(self, store, env):
        self.limits.take('login-global', 120)
        self.limits.take(('login-ip', self.client_address(env)), 10)
        link = store.begin()
        browser_url = self.public_url + '/login?' + urlencode({'request': link['request_id'], 'token': link.pop('browser_token')})
        return dict(link, browser_url=browser_url, poll_interval=5)

    @staticmethod
    def json(value):
        return 200, value, 'application/json', []


def bearer(env):
    value = env.get('HTTP_AUTHORIZATION', '')
    if not value.startswith('Bearer ') or value.count(' ') != 1:
        raise AccountError('Authentication required')
    return value[7:]


def browser_cookie(env):
    try:
        cookies = SimpleCookie()
        cookies.load(env.get('HTTP_COOKIE', ''))
        request, secret = cookies[COOKIE].value.split('.')
        return request, secret
    except (KeyError, ValueError, CookieError):
        raise AccountError('Sign-in browser is unavailable; start again from the game') from None


def query(value, required, optional=frozenset()):
    try:
        data = parse_qs(value, keep_blank_values=True, max_num_fields=8, strict_parsing=True)
        if not required <= set(data) <= required | optional or any(len(v) != 1 for v in data.values()):
            raise ValueError()
        return {k: v[0] for k, v in data.items()}
    except ValueError:
        raise HTTPError(400, 'Invalid request fields') from None


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Duplicate field')
        value[key] = item
    return value


def read_body(env):
    try:
        length = int(env.get('CONTENT_LENGTH', '0'))
    except (ValueError, TypeError):
        raise HTTPError(400, 'Invalid content length') from None
    if length < 0 or length > MAX_BODY:
        raise HTTPError(413, 'Request too large')
    body = env['wsgi.input'].read(length)
    if len(body) != length:
        raise HTTPError(400, 'Incomplete request')
    return body
