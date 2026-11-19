"""Build a minimal upload directory from an explicit list; never copy game data."""
import argparse
import hashlib
import json
from pathlib import Path

FILES = {
    'Dockerfile': 'services/accounts/Dockerfile',
    'requirements.txt': 'services/accounts/requirements.txt',
    'railway.json': 'services/accounts/deployment.json',
    'services/__init__.py': 'services/__init__.py',
    **{f'services/accounts/{name}.py': f'services/accounts/{name}.py' for name in
       ('__init__', '__main__', 'store', 'http', 'discord', 'runtime', 'operator')},
    **{f'services/ranking/{name}.py': f'services/ranking/{name}.py' for name in
       ('__init__', 'store', 'rating', 'tournament')},
}


def build(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(destination)
    payloads = {}
    for target, relative in FILES.items():
        path = (source / relative).resolve()
        if not path.is_relative_to(source):
            raise ValueError('Package source escapes the project')
        payloads[target] = path.read_bytes()
    destination.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for target, content in payloads.items():
        path = destination / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        hashes[target] = hashlib.sha256(content).hexdigest()
    (destination / 'manifest.json').write_text(json.dumps({'schemaVersion': 1, 'files': hashes}, indent=2) + '\n', encoding='utf-8')
    return hashes


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    files = build(Path(__file__).resolve().parents[2], args.output)
    print(f'Prepared {len(files)} source/configuration files and a SHA-256 manifest.')
