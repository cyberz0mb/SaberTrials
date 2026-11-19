"""Real offline models plus failure, encoding and protection regressions."""
import importlib.util
import json
from pathlib import Path
import socket
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('st_translation_worker',ROOT/'development-source/translator/worker.py')
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)


class TranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.translator=worker.Translator(ROOT/'dist/translator-02/runtime')

    def test_real_spanish_and_multiple_sentences(self):
        status,text=self.translator.translate('¿Dónde está mi equipo? Necesito ayuda.'.encode('cp1252'),b'',2,1)
        self.assertEqual(status,'ok');self.assertIn('team',text.lower());self.assertIn('help',text.lower())

    def test_real_english_and_accents(self):
        status,text=self.translator.translate(b'Good game everyone, see you tomorrow.',b'',1,2)
        self.assertEqual(status,'ok');self.assertIn('mañana',text);text.encode('cp1252')

    def test_names_terms_addresses(self):
        status,text=self.translator.translate(b'Hisoka usa Force Push en 127.0.0.1:29070',b'Hisoka',2,1)
        self.assertEqual(status,'ok')
        for word in ('Hisoka','Force Push','127.0.0.1:29070'):self.assertIn(word,text)
        self.assertEqual(self.translator.translate(b'gg',b'gg',0,2)[0],'same')
        self.assertEqual(self.translator.translate(b'play.example.com:29070',b'',0,2)[0],'same')

    def test_fallback_and_commands(self):
        self.assertEqual(self.translator.translate(b'/connect 127.0.0.1:29070',b'',1,2)[0],'skipped')
        self.assertEqual(self.translator.translate(b'Waar is mijn team? Ik heb hulp nodig.',b'',0,1)[0],'unsupported')
        self.assertEqual(self.translator.translate(b'The red team is near our base.',b'',0,1)[0],'same')
        self.assertEqual(self.translator.translate(b'hello',b'',99,1)[0],'invalid')
        self.assertEqual(self.translator.translate(b'hello\x01world',b'',1,2)[0],'skipped')

    def test_missing_and_modified_packs(self):
        with tempfile.TemporaryDirectory() as temp:
            t=worker.Translator(temp)
            self.assertEqual(t.translate(b'Where is my team?',b'',1,2)[0],'missing')
            folder=Path(temp)/'models/en-es';folder.mkdir(parents=True)
            (folder/'manifest.json').write_text(json.dumps(dict(version=1,source='en',target='es',tokenizer='sentencepiece',
                files={'../escape.bin':'0'*64,'sentencepiece.model':'0'*64})))
            self.assertEqual(t.translate(b'Where is my team?',b'',1,2)[0],'missing')

    def test_network_is_disabled(self):
        with self.assertRaises(PermissionError):socket.socket()
        with self.assertRaises(PermissionError):socket.getaddrinfo('example.com',443)

    def test_reviewed_phrases_and_cache_bound(self):
        self.assertEqual(self.translator.translate(b'gg',b'',0,2),('ok','buena partida'))
        t=worker.Translator(ROOT/'dist/translator-02/runtime')
        t.load=lambda *_:None
        t.neural=lambda text:'traducido '+text
        for n in range(150):self.assertEqual(t.translate(('Message number '+str(n)).encode(),b'',1,2)[0],'ok')
        self.assertEqual(len(t.cache),128)

    def test_unicode_and_pivot(self):
        self.assertEqual(worker.decode_chat('Hisoka 日本語'.encode('utf8')+b' \xe9'),'Hisoka 日本語 é')
        status,text=self.translator.translate('Onde está meu time? Preciso de ajuda.'.encode('utf8'),b'',12,8)
        self.assertEqual(status,'ok');self.assertIn('Team',text);self.assertIn('Hilfe',text)
        self.assertLessEqual(len(self.translator.models),2)
        for bad in ('hello\u202eworld','hello\u2066world'):
            self.assertEqual(self.translator.translate(bad.encode(),b'',1,2)[0],'skipped')

    def test_korean_help_request(self):
        for message in ('도움이 필요해요.','도와주세요.'):
            status,text=self.translator.translate(message.encode('utf8'),b'',13,1)
            self.assertEqual(status,'ok');self.assertIn('help',text.lower())

    def test_all_detected_fixtures(self):
        fixtures=json.loads((ROOT/'tests/translator/language-fixtures.json').read_text(encoding='utf8'))
        for code,text in fixtures.items():
            self.assertEqual(self.translator.detect(text),{'pb':'pt','zt':'zh'}.get(code,code),code)


if __name__=='__main__':unittest.main()
