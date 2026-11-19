"""Offline operator commands. Never exposed as public HTTP administration."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
from .store import AccountStore


def private_file(path):
    # O_EXCL prevents overwriting an earlier credential or backup.
    return os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w', encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('server-add', 'server-rotate', 'server-disable', 'account-disable', 'account-enable'):
        sub = commands.add_parser(command)
        sub.add_argument('id')
        if command == 'server-add':
            sub.add_argument('name')
        if command in ('server-add', 'server-rotate'):
            sub.add_argument('--out', required=True, help='New private file for the server credential')
    backup = commands.add_parser('backup')
    backup.add_argument('--out', required=True)
    address = commands.add_parser('server-address')
    address.add_argument('id')
    address.add_argument('endpoint', help='Approved numeric game IP:port (IPv6 uses [IP]:port)')
    args = parser.parse_args(argv)
    store = AccountStore(args.database)
    try:
        if args.command in ('server-add', 'server-rotate'):
            output = Path(args.out)
            with private_file(output) as stream:
                key = None
                try:
                    key = store.enroll_server(args.id, args.name) if args.command == 'server-add' else store.rotate_server(args.id)
                    json.dump({'server_id': args.id, 'server_token': key}, stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                except Exception:
                    # Rotation may have committed before a disk failure: disable the
                    # server, never leave an unknown usable key and claim success.
                    if key is not None:
                        store.ledger.set_server_enabled(args.id, False)
                    raise
            print('Server credential saved to the specified private file.')
        elif args.command == 'server-address':
            store.set_server_endpoint(args.id, args.endpoint)
            print('Game address approved; previous connection proofs revoked.')
        elif args.command == 'server-disable':
            store.ledger.set_server_enabled(args.id, False)
            print('Server disabled.')
        elif args.command.startswith('account-'):
            store.set_enabled(args.id, args.command == 'account-enable')
            print('Account status updated.')
        else:
            with private_file(args.out):
                pass
            target = sqlite3.connect(args.out)
            try:
                store.db.backup(target)
            finally:
                target.close()
            print('Consistent database backup created. Keep it private.')
    finally:
        store.close()
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit('Operator action failed. Check IDs, database access and output path; no credential was printed.')
