"""Offline, pipe-only translation of authorized received chat. No network or chat log."""
from collections import OrderedDict
import gc
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import unicodedata

os.environ['OMP_NUM_THREADS'] = '2'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '2'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'


def deny_network(event, args):
    if event.startswith('socket.'):
        raise PermissionError('The Saber Trials translator is offline')


sys.addaudithook(deny_network)
ROOT = Path(__file__).resolve().parent
LANGUAGES = {row['id']: row['code'] for row in json.loads((ROOT / 'languages.json').read_text())}
MAX_OUTPUT = 1536
COLOR = re.compile(r'\^[0-9]')
ADDRESS = r'(?:https?://|www\.)[^\s]+|[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}|\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b|\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?::\d+)?(?:/[^\s]*)?'


def decode_chat(raw):
    # New clients send UTF-8. Legacy Western names/chat can coexist in the same line.
    text = raw.decode('utf8', errors='surrogateescape')
    return ''.join(bytes([ord(c)-0xdc00]).decode('cp1252', errors='replace')
                   if 0xdc80 <= ord(c) <= 0xdcff else c for c in text)


def safe_text(text):
    return not any(unicodedata.category(c) == 'Cc' or c in '\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069' for c in text)


def safe_path(root, name):
    if not isinstance(name, str) or '\\' in name or ':' in name:
        raise ValueError('Invalid pack path')
    path = root / name
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Pack path escapes its folder')
    return path


def load_pack(root, source, target):
    folder = root / 'models' / (source + '-' + target)
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    if (manifest.get('version'), manifest.get('source'), manifest.get('target')) != (1, source, target):
        raise ValueError('Incompatible model pack')
    files = manifest.get('files', {})
    if not isinstance(files, dict) or not 2 <= len(files) <= 32:
        raise ValueError('Invalid model manifest')
    for name, digest in files.items():
        path = safe_path(folder, name)
        if path.suffix not in ('.bin', '.json', '.model', '.txt', '.md'):
            raise ValueError('Model packs contain data only')
        with path.open('rb') as stream:
            actual_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual_hash != digest:
            raise ValueError('Model checksum mismatch')
    tokenizer = manifest.get('tokenizer')
    required = {'model/model.bin'} | ({'source.model','target.model'} if tokenizer=='sentencepiece_dual' else
        {'sentencepiece.model' if tokenizer=='sentencepiece' else 'bpe.model'})
    if tokenizer not in ('sentencepiece', 'sentencepiece_dual', 'bpe') or not required <= files.keys():
        raise ValueError('Missing model or tokenizer')
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    if actual != set(files) | {'manifest.json'}:
        raise ValueError('Unlisted files in model pack')
    return folder, tokenizer


def terms(root):
    preserve, phrases = [], {}
    folders = root / 'terms'
    paths = sorted(folders.glob('*.json'))
    if len(paths) > 32:
        return preserve, phrases
    for path in paths:
        try:
            if path.stat().st_size > 65536:
                continue
            data = json.loads(path.read_text(encoding='utf-8'))
            if data.get('version') != 1 or set(data) - {'version', 'id', 'preserve', 'phrases'}:
                continue
            words, rows = data.get('preserve', []), data.get('phrases', [])
            if not isinstance(words, list) or not isinstance(rows, list) or len(words) > 256 or len(rows) > 256:
                continue
            for word in words:
                if isinstance(word, str) and 2 <= len(word) <= 64 and not any(ord(c) < 32 for c in word):
                    preserve.append(word)
            for row in rows:
                src, dst, original, translated = (row[k] for k in ('source', 'target', 'text', 'translation'))
                if src not in LANGUAGES.values() or dst not in LANGUAGES.values() or src == dst:
                    continue
                if not all(isinstance(v, str) and 0 < len(v) <= 256 and not any(ord(c) < 32 for c in v)
                           for v in (original, translated)):
                    continue
                if not safe_text(original) or not safe_text(translated):
                    continue
                phrases.setdefault((src, dst, original.casefold()), translated)
        except (ValueError, KeyError, TypeError, OSError, UnicodeError):
            continue
    return sorted(set(preserve), key=len, reverse=True), phrases


class Translator:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.preserve, self.phrases = terms(self.root)
        self.identifier = None
        self.model = self.tokenizer = None
        self.pair = None
        self.models = OrderedDict()
        self.cache = OrderedDict()

    def load(self, source, target):
        if self.pair == (source, target):
            return
        pair = (source, target)
        if pair in self.models:
            self.model, self.tokenizer, self.encode, self.decode = self.models[pair]
            self.models.move_to_end(pair)
            self.pair = pair
            return
        self.model = self.tokenizer = None
        self.encode = self.decode = None
        self.pair = None
        if len(self.models) >= 2:
            self.models.popitem(last=False)
        gc.collect()
        folder, kind = load_pack(self.root, source, target)
        import ctranslate2
        self.model = ctranslate2.Translator(str(folder / 'model'), device='cpu', compute_type='int8',
                                            inter_threads=1, intra_threads=2, max_queued_batches=1)
        if kind in ('sentencepiece','sentencepiece_dual'):
            import sentencepiece
            sp = sentencepiece.SentencePieceProcessor(model_file=str(folder / ('source.model' if kind=='sentencepiece_dual' else 'sentencepiece.model')))
            target_sp = sentencepiece.SentencePieceProcessor(model_file=str(folder / 'target.model')) if kind=='sentencepiece_dual' else sp
            self.encode = lambda text: sp.encode(text, out_type=str)
            self.decode = lambda tokens: target_sp.decode(tokens).replace('\u2581', ' ')
            self.tokenizer = (sp,target_sp)
        else:
            from sacremoses import MosesTokenizer, MosesDetokenizer, MosesPunctNormalizer
            from subword_nmt.apply_bpe import BPE
            with (folder / 'bpe.model').open(encoding='utf-8') as stream:
                bpe = BPE(stream)
            normalizer, tokenizer, detokenizer = MosesPunctNormalizer(source), MosesTokenizer(source), MosesDetokenizer(target)
            self.encode = lambda text: bpe.segment_tokens(tokenizer.tokenize(normalizer.normalize(text)))
            self.decode = lambda tokens: detokenizer.detokenize(' '.join(tokens).replace('@@ ', '').split())
            self.tokenizer = (bpe, normalizer, tokenizer, detokenizer)
        self.pair = (source, target)
        self.models[self.pair] = (self.model, self.tokenizer, self.encode, self.decode)

    def detect(self, text):
        if self.identifier is None:
            import py3langid
            from py3langid.langid import LanguageIdentifier
            model = Path(py3langid.__file__).parent / 'data/model.npz.xz'
            self.identifier = LanguageIdentifier.from_modelpath(model, norm_probs=True)
        ranked = self.identifier.rank(text)
        language, confidence = ranked[0]
        # Short chat has close language/dialect candidates. Require a clear lead,
        # retaining all detector languages so unrelated input is never forced into our set.
        return language if confidence >= .5 and confidence-ranked[1][1] >= .2 else None

    def neural(self, text):
        sentences = re.split(r'(?<=[。！？])(?=\S)|(?<=[.!?؟।])(\s+)', text)
        if len(sentences) > 1:
            output = []
            for piece in sentences:
                if not piece:
                    continue
                if output and not output[-1].endswith(' ') and not piece.isspace() and self.pair[1] not in ('ja', 'zh', 'zt'):
                    output.append(' ')
                output.append(piece if piece.isspace() else self.neural(piece).strip())
            return ''.join(output)
        tokens = self.encode(text)
        if not tokens or len(tokens) > 192:
            raise ValueError('Input too long')
        result = self.model.translate_batch([tokens], beam_size=2, max_decoding_length=192,
                                            repetition_penalty=1.1, disable_unk=True)[0]
        return self.decode(result.hypotheses[0])

    def translate(self, raw, names, source, target):
        if (source != 0 and source not in LANGUAGES) or target not in LANGUAGES or not 0 < len(raw) <= 511:
            return 'invalid', ''
        try:
            text = unicodedata.normalize('NFC', COLOR.sub('', decode_chat(raw))).strip()
            protected = [COLOR.sub('', n) for n in decode_chat(names).split('\n') if n]
        except UnicodeError:
            return 'encoding', ''
        if not text or not safe_text(text) or re.search(r'(^|\s)[/\\]\w', text):
            return 'skipped', ''
        if text in protected or re.fullmatch(ADDRESS, text):
            return 'same', ''
        destination = LANGUAGES[target]
        # Reviewed exact phrases help short gaming expressions without pretending to be a model.
        for (src, dst, original), translated in self.phrases.items():
            if dst == destination and original == text.casefold() and (source == 0 or LANGUAGES[source] == src):
                return 'ok', translated
        origin = LANGUAGES.get(source) if source else self.detect(text)
        if origin is None:
            return 'uncertain', ''
        if origin not in LANGUAGES.values():
            return 'unsupported', ''
        if origin == destination:
            return 'same', ''
        key = (origin, destination, text, tuple(protected))
        if key in self.cache:
            self.cache.move_to_end(key)
            return 'ok', self.cache[key]
        # Protected spans never enter the model and are copied byte-for-byte.
        words = sorted(set(self.preserve + protected), key=len, reverse=True)
        patterns = [ADDRESS]
        for word in words:
            if 0 < len(word) <= 64:
                patterns.append(r'(?<!\w)' + re.escape(word) + r'(?!\w)')
        pattern = re.compile('|'.join(patterns))
        pieces, end = [], 0
        for match in pattern.finditer(text):
            pieces.append((False, text[end:match.start()]))
            pieces.append((True, match.group()))
            end = match.end()
        pieces.append((False, text[end:]))
        route = [(origin, destination)] if 'en' in (origin, destination) else [(origin, 'en'), ('en', destination)]
        # Batch each leg by message, so pivoting does not repeatedly swap models for protected spans.
        for source_code, target_code in route:
            try:
                self.load(source_code, target_code)
            except (OSError, ValueError, RuntimeError):
                return 'missing', ''
            converted = []
            for fixed, part in pieces:
                if fixed or not any(c.isalpha() for c in part):
                    converted.append((fixed, part))
                else:
                    before, after = len(part) - len(part.lstrip()), len(part) - len(part.rstrip())
                    converted.append((False, part[:before] + self.neural(part.strip()).strip() + (part[-after:] if after else '')))
            pieces = converted
        output = [part for fixed, part in pieces]
        translated = ''.join(output).replace('^', '').replace('\n', ' ').replace('\r', ' ').strip()
        try:
            encoded = translated.encode('utf8')
        except UnicodeError:
            return 'encoding', ''
        if not translated or len(encoded) > MAX_OUTPUT or not safe_text(translated):
            return 'too_long', ''
        if translated == text:
            return 'same', ''
        self.cache[key] = translated
        if len(self.cache) > 128:
            self.cache.popitem(last=False)
        return 'ok', translated


def serve():
    translator = Translator()
    while True:
        line = sys.stdin.buffer.readline(8193)
        if not line:
            return
        if len(line) > 8192 or not line.endswith(b'\n'):
            return
        ticket = 0
        try:
            fields = line.decode('ascii').split()
            if len(fields) != 6 or fields[0] != 'STTR2':
                return
            ticket, source, target = map(int, fields[1:4])
            if not 0 < ticket < 2**32 or len(fields[4]) > 1022 or len(fields[5]) > 4096:
                return
            text = bytes.fromhex(fields[4])
            names = b'' if fields[5] == '-' else bytes.fromhex(fields[5])
            status, translated = translator.translate(text, names, source, target)
        except Exception:
            status, translated = 'failed', ''
        encoded = translated.encode('utf8').hex() if translated else '-'
        sys.stdout.buffer.write(f'STTR2 {ticket} {status} {encoded}\n'.encode('ascii'))
        sys.stdout.buffer.flush()


if __name__ == '__main__':
    serve()
