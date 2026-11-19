"""Central account state. Provider and operator methods are trusted boundaries.

Use one connection per request/thread. Transactions serialize secret redemption;
raw session and server secrets are returned once and never written to the DB.
"""
import hashlib
import hmac
import ipaddress
import secrets
import re
import sqlite3
import time
import unicodedata
from services.ranking.store import RankingStore, display, identifier


class AccountError(ValueError):
    pass


class AccountStore:
    def __init__(self, path, clock=time.time):
        self.ledger = RankingStore(path, clock=clock)
        self.db = self.ledger.db
        self.clock = clock
        self.db.execute('''CREATE TABLE IF NOT EXISTS account_login_links(
            id TEXT PRIMARY KEY, browser_hash TEXT, poll_hash TEXT NOT NULL,
            expires REAL NOT NULL, cookie_hash TEXT, state_hash TEXT)''')
        with self.ledger.transaction():
            columns = {r['name'] for r in self.db.execute('PRAGMA table_info(account_login_links)')}
            for name, definition in [('stage', "TEXT NOT NULL DEFAULT 'new'"),
                    ('discord', 'TEXT'), ('csrf_hash', 'TEXT'), ('player', 'TEXT')]:
                if name not in columns:
                    self.db.execute(f'ALTER TABLE account_login_links ADD COLUMN {name} {definition}')
            statements = [
                '''CREATE TABLE IF NOT EXISTS accounts(
                    player TEXT PRIMARY KEY REFERENCES players(id), discord TEXT NOT NULL UNIQUE,
                    name_key TEXT NOT NULL UNIQUE, enabled INTEGER NOT NULL DEFAULT 1)''',
                '''CREATE TABLE IF NOT EXISTS account_sessions(
                    hash TEXT PRIMARY KEY, player TEXT NOT NULL REFERENCES accounts(player), expires REAL NOT NULL)''',
                '''CREATE TABLE IF NOT EXISTS account_server_keys(
                    server TEXT PRIMARY KEY REFERENCES servers(id), hash TEXT NOT NULL UNIQUE)''',
                '''CREATE TABLE IF NOT EXISTS account_challenges(
                    hash TEXT PRIMARY KEY, server TEXT NOT NULL REFERENCES servers(id),
                    instance TEXT NOT NULL, slot INTEGER NOT NULL, generation TEXT NOT NULL,
                    expires REAL NOT NULL, session TEXT REFERENCES account_sessions(hash) ON DELETE CASCADE)''',
                '''CREATE TABLE IF NOT EXISTS account_leases(
                    hash TEXT PRIMARY KEY, server TEXT NOT NULL REFERENCES servers(id),
                    instance TEXT NOT NULL, slot INTEGER NOT NULL, generation TEXT NOT NULL,
                    expires REAL NOT NULL, session TEXT NOT NULL REFERENCES account_sessions(hash) ON DELETE CASCADE)'''
            ]
            for statement in statements:
                self.db.execute(statement)
            self.db.execute('''CREATE TABLE IF NOT EXISTS account_server_endpoints(
                server TEXT PRIMARY KEY REFERENCES servers(id), endpoint TEXT NOT NULL UNIQUE)''')
            columns = {r['name'] for r in self.db.execute('PRAGMA table_info(account_challenges)')}
            if 'client_nonce' not in columns:
                self.db.execute('ALTER TABLE account_challenges ADD COLUMN client_nonce TEXT')

    def close(self):
        self.ledger.close()

    def begin(self):
        request_id = secrets.token_hex(16)
        browser_token = secrets.token_urlsafe(32)
        poll_token = secrets.token_urlsafe(32)
        expires_at = self.clock() + 600
        with self.ledger.transaction():
            self.db.execute('DELETE FROM account_login_links WHERE expires<=?',
                            (self.clock(),))
            self.db.execute('''INSERT INTO account_login_links
                (id,browser_hash,poll_hash,expires) VALUES(?,?,?,?)''',
                (request_id, digest(browser_token), digest(poll_token), expires_at))
        return dict(request_id=request_id, browser_token=browser_token,
                    poll_token=poll_token, expires_at=expires_at)

    def _link(self, request_id):
        if not isinstance(request_id, str) or len(request_id) != 32:
            raise AccountError('Invalid or expired login request')
        row = self.db.execute('SELECT * FROM account_login_links WHERE id=? AND expires>?',
                              (request_id, self.clock())).fetchone()
        if row is None:
            raise AccountError('Invalid or expired login request')
        return row

    def poll(self, request_id, poll_token):
        with self.ledger.transaction():
            row = self._link(request_id)
            if not matches(row['poll_hash'], poll_token) or row['stage'] == 'delivered':
                raise AccountError('Invalid or expired login request')
            if row['stage'] != 'approved':
                return {'status': 'pending'}
            profile = self._profile(row['player'])
            token = secrets.token_urlsafe(32)
            expires = self.clock() + 7 * 86400
            self.db.execute('INSERT INTO account_sessions VALUES(?,?,?)',
                            (digest(token), row['player'], expires))
            self.db.execute("UPDATE account_login_links SET stage='delivered',discord=NULL,csrf_hash=NULL WHERE id=?",
                            (request_id,))
            return dict(status='complete', session_token=token, expires_at=expires, profile=profile)

    def open_browser(self, request_id, browser_token):
        with self.ledger.transaction():
            row = self._link(request_id)
            if row['browser_hash'] is None or not hmac.compare_digest(
                    row['browser_hash'], digest(browser_token)):
                raise AccountError('Invalid or expired login request')
            cookie = secrets.token_urlsafe(32)
            state = secrets.token_urlsafe(32)
            self.db.execute('''UPDATE account_login_links
                SET browser_hash=NULL,cookie_hash=?,state_hash=?,stage='oauth' WHERE id=?''',
                (digest(cookie), digest(state), request_id))
        return dict(browser_cookie=cookie, oauth_state=state,
                    expires_at=row['expires'])

    def _browser(self, request_id, cookie, stage):
        row = self._link(request_id)
        if row['stage'] != stage or not matches(row['cookie_hash'], cookie):
            raise AccountError('Invalid or expired login request')
        return row

    def consume_oauth(self, request_id, cookie, state):
        """Consume before exchanging the code, so concurrent callbacks cannot win."""
        with self.ledger.transaction():
            row = self._browser(request_id, cookie, 'oauth')
            if not matches(row['state_hash'], state):
                raise AccountError('Invalid or expired login request')
            self.db.execute("UPDATE account_login_links SET stage='exchanging',state_hash=NULL WHERE id=?",
                            (request_id,))

    def verified_identity(self, request_id, cookie, discord):
        """Only call with the ID returned by Discord's authenticated /users/@me."""
        if not isinstance(discord, str) or not re.fullmatch(r'[1-9][0-9]{16,19}', discord):
            raise AccountError('Discord did not return a valid identity')
        csrf = secrets.token_urlsafe(32)
        with self.ledger.transaction():
            self._browser(request_id, cookie, 'exchanging')
            existing = self.db.execute('SELECT player FROM accounts WHERE discord=?', (discord,)).fetchone()
            profile = self._profile(existing['player']) if existing else None
            self.db.execute("UPDATE account_login_links SET stage='confirm',discord=?,csrf_hash=? WHERE id=?",
                            (discord, digest(csrf), request_id))
        return dict(csrf=csrf, profile=profile)

    def approve(self, request_id, cookie, csrf, name):
        with self.ledger.transaction():
            row = self._browser(request_id, cookie, 'confirm')
            if not matches(row['csrf_hash'], csrf):
                raise AccountError('Invalid or expired login request')
            existing = self.db.execute('SELECT player FROM accounts WHERE discord=?', (row['discord'],)).fetchone()
            if existing:
                player = existing['player']
                self._profile(player)
            else:
                name = native_name(name)
                player = secrets.token_hex(16)
                try:
                    self.db.execute('INSERT INTO players VALUES(?,?)', (player, name))
                    self.db.execute('INSERT INTO accounts(player,discord,name_key) VALUES(?,?,?)',
                                    (player, row['discord'], unicodedata.normalize('NFKC', name).casefold()))
                except sqlite3.IntegrityError as exc:
                    raise AccountError('Registered name is already in use') from exc
            self.db.execute("UPDATE account_login_links SET stage='approved',player=?,csrf_hash=NULL WHERE id=?",
                            (player, request_id))

    def _profile(self, player):
        row = self.db.execute('''SELECT a.player,p.name,t.id AS team,t.tag FROM accounts a
            JOIN players p ON p.id=a.player LEFT JOIN members m ON m.player=a.player
            LEFT JOIN teams t ON t.id=m.team WHERE a.player=? AND a.enabled=1''', (player,)).fetchone()
        if not row:
            raise AccountError('Account is unavailable')
        return dict(account=row['player'], name=native_name(row['name']),
                    team=row['team'] or '', teamName=row['tag'] or '', verified=True)

    def _session(self, session_hash):
        row = self.db.execute('SELECT * FROM account_sessions WHERE hash=? AND expires>?',
                              (session_hash, self.clock())).fetchone()
        if not row:
            raise AccountError('Please sign in again')
        self._profile(row['player'])
        return row

    def profile(self, token):
        return self._profile(self._session(digest(token))['player'])

    def logout(self, token):
        # Idempotent; dependent challenges and leases are deleted by foreign keys.
        self.db.execute('DELETE FROM account_sessions WHERE hash=?', (digest(token),))

    def set_enabled(self, player, enabled):
        """Local operator action, never exposed over HTTP."""
        if type(enabled) is not bool:
            raise AccountError('enabled must be boolean')
        with self.ledger.transaction():
            if self.db.execute('UPDATE accounts SET enabled=? WHERE player=?', (int(enabled), player)).rowcount != 1:
                raise AccountError('Unknown account')
            if not enabled:
                self.db.execute('DELETE FROM account_sessions WHERE player=?', (player,))
                self.db.execute('''DELETE FROM account_login_links WHERE player=? OR
                    discord=(SELECT discord FROM accounts WHERE player=?)''', (player, player))

    def enroll_server(self, server, name):
        """Local operator approval. Not self-registration by a remote game server."""
        token = secrets.token_urlsafe(32)
        with self.ledger.transaction():
            self.ledger.register_server(server, name)
            self.db.execute('INSERT INTO account_server_keys VALUES(?,?)', (server, digest(token)))
        return token

    def rotate_server(self, server):
        token = secrets.token_urlsafe(32)
        with self.ledger.transaction():
            if self.db.execute('UPDATE account_server_keys SET hash=? WHERE server=?',
                               (digest(token), server)).rowcount != 1:
                raise AccountError('Unknown server')
            self.db.execute('DELETE FROM account_leases WHERE server=?', (server,))
            self.db.execute('DELETE FROM account_challenges WHERE server=?', (server,))
        return token

    def _server(self, token):
        row = self.db.execute('''SELECT s.id FROM account_server_keys k JOIN servers s ON s.id=k.server
            WHERE k.hash=? AND s.enabled=1''', (digest(token),)).fetchone()
        if not row:
            raise AccountError('Server is not authorized')
        return row['id']

    def set_server_endpoint(self, server, endpoint):
        """Operator-approved game address. Changing it invalidates all proofs."""
        endpoint = native_endpoint(endpoint)
        with self.ledger.transaction():
            if not self.db.execute('SELECT 1 FROM account_server_keys WHERE server=?', (server,)).fetchone():
                raise AccountError('Unknown server')
            try:
                self.db.execute('INSERT INTO account_server_endpoints VALUES(?,?) ON CONFLICT(server) DO UPDATE SET endpoint=excluded.endpoint', (server, endpoint))
            except sqlite3.IntegrityError as exc:
                raise AccountError('Address already registered') from exc
            for table in ('account_challenges', 'account_leases'):
                self.db.execute(f'DELETE FROM {table} WHERE server=?', (server,))

    def challenge(self, server_token, instance, slot, generation, client_nonce=None):
        validate_connection(instance, slot, generation)
        if client_nonce is not None and (not isinstance(client_nonce, str) or not re.fullmatch(r'[a-f0-9]{32}', client_nonce)):
            raise AccountError('Invalid connection nonce')
        token = secrets.token_urlsafe(32)
        expires = self.clock() + 90
        with self.ledger.transaction():
            server = self._server(server_token)
            if client_nonce is not None and not self.db.execute('SELECT 1 FROM account_server_endpoints WHERE server=?', (server,)).fetchone():
                raise AccountError('Server address has not been approved')
            self.db.execute('DELETE FROM account_challenges WHERE expires<=?', (self.clock(),))
            self.db.execute('DELETE FROM account_leases WHERE expires<=?', (self.clock(),))
            self.db.execute('DELETE FROM account_sessions WHERE expires<=?', (self.clock(),))
            # A new slot challenge replaces the previous connection proof.
            for table in ('account_challenges', 'account_leases'):
                self.db.execute(f'DELETE FROM {table} WHERE server=? AND instance=? AND slot=?',
                                (server, instance, slot))
            self.db.execute('''INSERT INTO account_challenges
                (hash,server,instance,slot,generation,expires,client_nonce) VALUES(?,?,?,?,?,?,?)''',
                (digest(token), server, instance, slot, generation, expires, client_nonce))
        return dict(challenge=token, expires_at=expires, server=server,
                    instance=instance, slot=slot, generation=generation)

    def authorize_connection(self, session_token, challenge, endpoint=None, client_nonce=None, slot=None):
        with self.ledger.transaction():
            session_hash = digest(session_token)
            self._session(session_hash)
            row = self.db.execute('''SELECT c.* FROM account_challenges c JOIN servers s ON s.id=c.server
                WHERE c.hash=? AND c.expires>? AND c.session IS NULL AND s.enabled=1''',
                (digest(challenge), self.clock())).fetchone()
            if not row:
                raise AccountError('Connection request is unavailable')
            if row['client_nonce'] is not None:
                address = self.db.execute('SELECT endpoint FROM account_server_endpoints WHERE server=?', (row['server'],)).fetchone()
                if (not address or type(slot) is not int or slot != row['slot'] or
                        client_nonce != row['client_nonce'] or native_endpoint(endpoint) != address['endpoint']):
                    raise AccountError('Connection does not match the joined server')
            elif endpoint is not None or client_nonce is not None or slot is not None:
                raise AccountError('Unbound connection request')
            self.db.execute('UPDATE account_challenges SET session=? WHERE hash=?', (session_hash, row['hash']))
        return {'authorized': True}

    def redeem(self, server_token, challenge, instance, slot, generation):
        validate_connection(instance, slot, generation)
        with self.ledger.transaction():
            server = self._server(server_token)
            row = self.db.execute('''SELECT * FROM account_challenges WHERE hash=? AND server=?
                AND instance=? AND slot=? AND generation=? AND expires>? AND session IS NOT NULL''',
                (digest(challenge), server, instance, slot, generation, self.clock())).fetchone()
            if not row:
                raise AccountError('Connection request is unavailable')
            session = self._session(row['session'])
            token = secrets.token_urlsafe(32)
            expires = min(self.clock() + 60, session['expires'])
            self.db.execute('INSERT INTO account_leases VALUES(?,?,?,?,?,?,?)',
                            (digest(token), server, instance, slot, generation, expires, row['session']))
            self.db.execute('DELETE FROM account_challenges WHERE hash=?', (row['hash'],))
            return dict(lease_token=token, expires_at=expires, instance=instance, slot=slot,
                        generation=generation, profile=self._profile(session['player']))

    def renew(self, server_token, lease_token):
        with self.ledger.transaction():
            server = self._server(server_token)
            row = self.db.execute('SELECT * FROM account_leases WHERE hash=? AND server=? AND expires>?',
                                  (digest(lease_token), server, self.clock())).fetchone()
            if not row:
                raise AccountError('Connection proof expired; sign in to the server again')
            session = self._session(row['session'])
            expires = min(self.clock() + 60, session['expires'])
            self.db.execute('UPDATE account_leases SET expires=? WHERE hash=?', (expires, row['hash']))
            return dict(expires_at=expires, instance=row['instance'], slot=row['slot'],
                        generation=row['generation'], profile=self._profile(session['player']))


def digest(token):
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        raise AccountError('Invalid or expired login request')
    return hashlib.sha256(token.encode('ascii')).hexdigest()


def matches(stored, token):
    return stored is not None and hmac.compare_digest(stored, digest(token))


def native_name(name):
    try:
        # Check before stripping: silently dropping newlines would mask bad input.
        name = display(name, 48)
        if len(name.encode('utf-8')) > 63 or any(c in name for c in '\\";'):
            raise ValueError()
        return name
    except (ValueError, UnicodeError) as exc:
        raise AccountError('Choose a name without color codes, commands or control characters (up to 48 characters / 63 bytes)') from exc


def validate_connection(instance, slot, generation):
    try:
        identifier(instance)
    except ValueError as exc:
        raise AccountError('Invalid server instance') from exc
    if type(slot) is not int or not 0 <= slot < 64 or not isinstance(generation, str) or not re.fullmatch(r'[a-f0-9]{32}', generation):
        raise AccountError('Invalid game connection')


def native_endpoint(value):
    """Numeric address only; no DNS rebinding, URL parsing or implicit port."""
    if not isinstance(value, str) or len(value) > 64 or '%' in value:
        raise AccountError('Invalid server address')
    match = re.fullmatch(r'(?:\[([^\]]+)\]|([^:]+)):([0-9]{1,5})', value)
    if not match or not 1 <= int(match[3]) <= 65535:
        raise AccountError('Invalid server address')
    try:
        address = ipaddress.ip_address(match[1] or match[2])
    except ValueError as exc:
        raise AccountError('Invalid server address') from exc
    if address.is_unspecified or address.is_multicast:
        raise AccountError('Invalid server address')
    host = f'[{address.compressed}]' if address.version == 6 else str(address)
    return f'{host}:{int(match[3])}'
