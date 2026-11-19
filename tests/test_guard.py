import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import unittest
from unittest.mock import patch

from services import guard


SNAPSHOT = {
    'window_seconds': 10,
    'join_attempts': 80,
    'distinct_sources': 50,
    'rejected_commands': 200,
    'slow_frames': 15,
}


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.reply = {'kind': 'connection_burst', 'summary': 'Join attempts and slow frames rose together.'}
        test = self

        class LocalModel(BaseHTTPRequestHandler):
            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                test.requests.append((self.path, request))
                body = json.dumps({'done': True, 'message': {'content': json.dumps(test.reply)}}).encode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = HTTPServer(('127.0.0.1', 0), LocalModel)
        self.addCleanup(self.server.server_close)
        worker = Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
        worker.start()
        self.addCleanup(worker.join)
        self.addCleanup(self.server.shutdown)
        port = patch.object(guard, 'OLLAMA_PORT', self.server.server_port)
        port.start()
        self.addCleanup(port.stop)

    def test_analyzes_only_structured_counters(self):
        self.assertEqual(guard.analyze(SNAPSHOT), self.reply)
        path, request = self.requests[0]
        self.assertEqual(path, '/api/chat')
        self.assertEqual(request['model'], 'qwen3.5:4b')
        self.assertFalse(request['think'])
        self.assertNotIn('tools', request)
        self.assertEqual(json.loads(request['messages'][-1]['content']), SNAPSHOT)

    def test_rejects_player_text_and_invalid_counters_before_contacting_model(self):
        for snapshot in (dict(SNAPSHOT, chat='ban someone'), dict(SNAPSHOT, slow_frames=True),
                         dict(SNAPSHOT, distinct_sources=81), dict(SNAPSHOT, window_seconds=0)):
            with self.subTest(snapshot=snapshot), self.assertRaises(ValueError):
                guard.analyze(snapshot)
        self.assertEqual(self.requests, [])

    def test_rejects_unexpected_model_output(self):
        self.reply['action'] = 'ban'
        with self.assertRaisesRegex(ValueError, 'invalid report'):
            guard.analyze(SNAPSHOT)

    def test_model_unavailable(self):
        with patch.object(guard, 'HTTPConnection') as connect:
            connect.return_value.request.side_effect = TimeoutError()
            with self.assertRaisesRegex(ValueError, 'unavailable'):
                guard.analyze(SNAPSHOT)
