from datetime import datetime, timezone
from io import StringIO
import json
import unittest

from services import guard_watch


RECORD = '[ST-GUARD] v=1 join_rate=4 reliable_rate=8 malformed_connect=1 source_limit=0'


class GuardWatchTests(unittest.TestCase):
    def test_reports_only_native_records_meeting_threshold(self):
        output = StringIO()
        lines = [f'Player: {RECORD}\n', f'{RECORD} trailing text\n', f'{RECORD}\n']
        guard_watch.watch(lines, output, min_drops=13)
        report = json.loads(output.getvalue())
        self.assertEqual(report['total_dropped'], 13)
        self.assertEqual(report['drops']['reliable_rate'], 8)
        self.assertEqual(datetime.fromisoformat(report['reported_at']).tzinfo, timezone.utc)

    def test_ignores_small_windows_and_impossible_counts(self):
        output = StringIO()
        lines = [RECORD, RECORD.replace('join_rate=4', 'join_rate=9999999999')]
        guard_watch.watch(lines, output, min_drops=14)
        self.assertEqual(output.getvalue(), '')

    def test_reads_default_openjk_timestamp_prefix(self):
        output = StringIO()
        guard_watch.watch([f'2026-11-07 20:15:30 {RECORD}\r\n'], output, min_drops=1)
        self.assertEqual(json.loads(output.getvalue())['total_dropped'], 13)
