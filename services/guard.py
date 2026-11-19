"""Summarize a Saber Trials incident snapshot with the local Guard model."""

import argparse
from http.client import HTTPConnection, HTTPException
import json
import sys


OLLAMA_PORT = 11434
MODEL = 'qwen3.5:4b'
COUNTERS = ('window_seconds', 'join_attempts', 'distinct_sources', 'rejected_commands', 'slow_frames')
REPORT_KINDS = ('connection_burst', 'command_burst', 'slowdown', 'inconclusive')
MAX_SUMMARY = 400
REPORT_SCHEMA = {
    'type': 'object',
    'properties': {
        'kind': {'type': 'string', 'enum': list(REPORT_KINDS)},
        'summary': {'type': 'string', 'minLength': 1, 'maxLength': MAX_SUMMARY},
    },
    'required': ['kind', 'summary'],
    'additionalProperties': False,
}


def analyze(snapshot):
    if not isinstance(snapshot, dict) or snapshot.keys() != set(COUNTERS):
        raise ValueError(f'Expected counters: {", ".join(COUNTERS)}')
    if any(type(value) is not int or not 0 <= value <= 2**31 - 1 for value in snapshot.values()):
        raise ValueError('Counters must be nonnegative 32-bit integers')
    if not snapshot['window_seconds'] or snapshot['distinct_sources'] > snapshot['join_attempts']:
        raise ValueError('Expected a positive window and at most one distinct source per join attempt')

    request = {
        'model': MODEL,
        'stream': False,
        'think': False,
        'format': REPORT_SCHEMA,
        'options': {'num_ctx': 2048, 'num_predict': 256, 'temperature': 0},
        'messages': [
            {'role': 'system', 'content': (
                'Summarize this Saber Trials server telemetry window in one sentence. '
                'Use only the given counters. A single window cannot establish intent, '
                'identify an attacker, or establish a change from baseline. '
                'Use inconclusive when the evidence is ambiguous. Return only kind and summary.'
            )},
            {'role': 'user', 'content': json.dumps(snapshot)},
        ],
    }
    connection = HTTPConnection('127.0.0.1', OLLAMA_PORT, timeout=30)
    try:
        connection.request('POST', '/api/chat', json.dumps(request), {'Content-Type': 'application/json'})
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError(f'Local Ollama returned HTTP {response.status} for {MODEL}')
        body = response.read(8193)
    except (OSError, HTTPException) as exc:
        raise ValueError('Local Ollama is unavailable or timed out') from exc
    finally:
        connection.close()

    try:
        if len(body) > 8192:
            raise ValueError
        response_data = json.loads(body)
        if response_data['done'] is not True:
            raise ValueError
        report = json.loads(response_data['message']['content'])
        if not isinstance(report, dict) or report.keys() != {'kind', 'summary'}:
            raise ValueError
        summary = report['summary']
        if report['kind'] not in REPORT_KINDS or not isinstance(summary, str):
            raise ValueError
        if not summary.strip() or len(summary) > MAX_SUMMARY:
            raise ValueError
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError('Local Ollama returned an invalid report') from exc
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, epilog=f'JSON input fields: {", ".join(COUNTERS)}.')
    parser.add_argument('snapshot', type=argparse.FileType('rb'), help='JSON snapshot file, or - to read stdin')
    args = parser.parse_args()
    try:
        data = args.snapshot.read(2049)
        if len(data) > 2048:
            raise ValueError('Snapshot exceeds 2048 bytes')
        print(json.dumps(analyze(json.loads(data))))
    except (OSError, ValueError) as exc:
        print(f'Guard: {exc}', file=sys.stderr)
        return 1
    finally:
        if args.snapshot is not sys.stdin.buffer:
            args.snapshot.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
