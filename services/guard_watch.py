"""Turn Saber Trials Guard traffic records from stdin into JSON incident reports."""

import argparse
from datetime import datetime, timezone
import json
import re
import sys


NATIVE_RECORD = re.compile(
    r'(?:[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} )?'
    r'\[ST-GUARD\] v=1 join_rate=(?P<join_rate>[0-9]{1,10})'
    r' reliable_rate=(?P<reliable_rate>[0-9]{1,10})'
    r' malformed_connect=(?P<malformed_connect>[0-9]{1,10})'
    r' source_limit=(?P<source_limit>[0-9]{1,10})'
)


def watch(lines, output, *, min_drops):
    for line in lines:
        match = NATIVE_RECORD.fullmatch(line.rstrip('\r\n'))
        if match is None:
            continue
        drops = {reason: int(count) for reason, count in match.groupdict().items()}
        if any(count > 2**32 - 1 for count in drops.values()):
            continue
        total = sum(drops.values())
        if total >= min_drops:
            print(json.dumps({
                'reported_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                'total_dropped': total,
                'drops': drops,
            }), file=output, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--min-drops', type=int, default=1, help='minimum drops in one engine report')
    args = parser.parse_args()
    if args.min_drops < 1:
        parser.error('--min-drops must be positive')
    sys.stdin.reconfigure(errors='replace')
    watch(sys.stdin, sys.stdout, min_drops=args.min_drops)


if __name__ == '__main__':
    main()
