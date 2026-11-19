"""Production entry point: one Waitress process, one persistent SQLite volume."""
import ipaddress
import os
import sqlite3
import uuid
from pathlib import Path
from .discord import DiscordProvider
from .http import AccountApplication, origin_url
from .store import AccountStore


def configure(env):
    url = origin_url(env.get('PUBLIC_BASE_URL', ''))
    secret = env.get('DISCORD_CLIENT_SECRET', '')
    client = env.get('DISCORD_CLIENT_ID', '1562891535312355419')
    if not secret:
        raise ValueError('DISCORD_CLIENT_SECRET is required')
    path = Path(env.get('ST_DATA_DIR', ''))
    if not env.get('ST_DATA_DIR') or not path.is_absolute() or not path.is_dir():
        raise ValueError('ST_DATA_DIR must name an existing absolute persistent directory')
    # Railway injects this only when a volume is actually attached.
    if env.get('RAILWAY_ENVIRONMENT_ID') and env.get('RAILWAY_VOLUME_MOUNT_PATH') != str(path):
        raise ValueError('Attach a Railway volume at ST_DATA_DIR before starting')
    port = int(env.get('PORT', '8080'))
    if not 1 <= port <= 65535:
        raise ValueError('PORT must be between 1 and 65535')
    proxy = env.get('ST_TRUSTED_PROXY', '')
    # No wildcard: do not trust user-supplied forwarded IPs on arbitrary connections.
    if proxy:
        ipaddress.ip_address(proxy)
    edge = env.get('ST_RAILWAY_EDGE_ONLY', '0')
    if edge not in ('0', '1') or (edge == '1' and not env.get('RAILWAY_ENVIRONMENT_ID')):
        raise ValueError('Railway edge mode requires a Railway environment')
    return dict(path=path / 'accounts.sqlite', port=port, public_url=url,
                provider=DiscordProvider(client, secret, url + '/oauth/callback'), proxy=proxy,
                railway_edge=edge == '1')


def prepare_store(path):
    """Save the previous schema once before the additive connection migration."""
    if path.is_file():
        source = sqlite3.connect(f'{path.as_uri()}?mode=ro', uri=True)
        try:
            columns = {row[1] for row in source.execute('PRAGMA table_info(account_challenges)')}
            if columns and 'client_nonce' not in columns:
                snapshot = path.parent / f'accounts-before-connection-binding-{uuid.uuid4().hex}.sqlite'
                fd = os.open(snapshot, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.close(fd)
                target = sqlite3.connect(snapshot)
                try:
                    source.backup(target)
                    if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise ValueError('Pre-migration snapshot failed integrity check')
                finally:
                    target.close()
                print('Account database snapshot preserved before connection migration.')
        finally:
            source.close()
    # Fail during startup if the mounted DB is unavailable or migration fails.
    store = AccountStore(path)
    store.close()


def main():
    config = configure(os.environ)
    prepare_store(config['path'])
    app = AccountApplication(config['path'], config['public_url'], config['provider'],
                             railway_edge=config['railway_edge'])
    from waitress import serve
    options = dict(host='0.0.0.0', port=config['port'], threads=4, connection_limit=100,
                   channel_timeout=30, max_request_body_size=16384,
                   max_request_header_size=16384, expose_tracebacks=False,
                   clear_untrusted_proxy_headers=True)
    if config['proxy']:
        options.update(trusted_proxy=config['proxy'], trusted_proxy_count=1,
                       trusted_proxy_headers={'x-forwarded-for', 'x-forwarded-proto'})
    serve(app, **options)
