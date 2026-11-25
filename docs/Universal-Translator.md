# Universal translator

Saber Trials can translate **received public, team and private chat offline** on
the Windows x64 client. Each player chooses their reading language. Bot messages
use the same path when the server delivers them as chat. Originals appear
immediately; completed translations carry a language tag in the existing panel.

## Players

Open **Setup > Interface > Translation**, enable **Universal translator**, choose
**Translate into**, then **Apply changes**. Leave **Message language** on
**Automatic** initially. Select an explicit source when short messages, slang or
regional variants are misidentified. **Show original message** is on by default.
Translation itself is off by default and your existing settings are preserved.

There are **15 languages and 17 selectable variants**:

| ID | Language | Pack code |
| --- | --- | --- |
| 1 | English | en |
| 2 | Spanish | es |
| 3 | Russian | ru |
| 4 | Japanese | ja |
| 5 | Chinese, Simplified | zh |
| 6 | Chinese, Traditional | zt |
| 7 | Arabic | ar |
| 8 | German | de |
| 9 | French | fr |
| 10 | Italian | it |
| 11 | Portuguese, European | pt |
| 12 | Portuguese, Brazilian | pb |
| 13 | Korean | ko |
| 14 | Hindi | hi |
| 15 | Polish | pl |
| 16 | Turkish | tr |
| 17 | Ukrainian | uk |

Automatic detection identifies Portuguese generally as `pt` and Chinese as `zh`;
it does not reliably distinguish Brazil/Portugal or Traditional/Simplified input.
The chosen output variant uses its corresponding model. Manual source choices
include all 17 variants. Arabic is general written Arabic; dialect accuracy is
not guaranteed. Other non-English pairs translate through English, which can
reduce accuracy. Machine translations need bilingual review, especially slang,
short messages and mixed languages. Keep the original visible while testing.

Automatic checks each incoming message separately. It ignores protected player
names, game terms and links when identifying the language. Common short chat
such as “hola amigos” or “guten Tag” can be recognized even when the general
detector is uncertain. Ambiguous messages can still appear in the original.

**Known quality limit:** English-to-Korean remains experimental: the current
model mistranslated the simple help request in the test corpus. Korean-to-English
uses the improved OPUS-MT pack and passes that regression. Model output existing
is not proof of semantic accuracy; Korean output needs further model work and
bilingual review before relying on it.

Console controls: `st_translate 0|1`, `st_translateTarget <ID>`,
`st_translateSource 0|<ID>` (0 is automatic), `st_translateOriginal 0|1`.
`st_translatorinfo` prints state/channel counts without message bodies.

## Privacy, audiences and fallback

Translation runs **after** existing server delivery and client chat filters.
Team messages remain team messages; private messages remain visible only to the
sender and intended recipient. Location-bearing team/private messages also work.
The translator cannot request messages the client never received. There is no
server routing or gameplay change. Third-party dimension/chat mods need their
own compatibility checks; this client does not bypass their delivery rules.

No account, API key, subscription or cloud service is required. The helper uses
local model data and pipes only. It does not save messages or collect training
data. Existing game/server console logging keeps its usual behavior; private
chat was already subject to the server's logging rules. The runtime rejects
Python socket operations before importing translation libraries. This is an
application-level network prohibition, not an OS sandbox for arbitrary code.

When disabled, uncertain, unsupported, missing a model, busy beyond the queue
limit or timed out, the original stays available. Turning off original display
hides it only after a translation succeeds. New translations do not replay old
chat automatically. Disconnect and language/on-off changes cancel pending work.

## Text and compatibility

Chat input now accepts UTF-8, including committed IME text and clipboard paste.
Cursor movement, backspace, delete, overwrite and the existing 149-byte send
limit respect complete code points. The byte limit allows fewer CJK characters
than Latin characters. Menu/console input retains its previous encoding.
Received Western legacy chat is still decoded. Older clients may show garbled
characters when receiving non-Western text from a new client.

Bundled Noto fonts and Windows DirectWrite/Direct2D provide Cyrillic, CJK,
Arabic bidi/shaping and Devanagari shaping in the chat panel. The classic and
Rend2 renderers use reusable, bounded textures; no chat images are written to
disk. Latin Western panel text retains the existing JKA font. The existing
console log can contain UTF-8 bytes, but its on-screen font is not a Unicode
viewer. The translator handles text chat. Change the menu language separately
under **Setup → Interface → Menu language** and select **Apply changes**.
Real keyboard/IME composition and native-speaker acceptance remain user tests.

The engine, cgame, UI and **both renderers** must be installed together: native
cgame API **240**, renderer API **12**. The multiplayer network protocol and
server game module are unchanged. A PK3 alone cannot install this feature.
This packaging requires Windows 10 or later; Linux/macOS helpers are not built.

## Model packs and storage

The full local installation contains 32 directed English model pairs, fonts and
the isolated helper, about **3.93 GB / 3.66 GiB** in total. Files live beside the
executable in `client/translator`, under `models`, `fonts`, `terms` and
`Lib/site-packages`, with `worker.py`, `languages.json` and the Python runtime.
Only two translation models are cached in memory at once.

An English-reading player does **not** need foreign menu/interface packs.
However, offline translation still requires the incoming source-to-English
models. Selecting English does not eliminate that translation data. To read
all supported sources in English, retain every `models/*-en` folder. For another
reading language, retain those incoming models plus `models/en-<target>`.
For example, Brazilian Portuguese uses `en-pb`. The full install includes all
output directions so the player can change languages without another download.

Close the game before changing packs. Move an entire unused model folder outside
`models` to remove it; restore the complete verified folder to add it back. Never
mix model versions. Keep all bundled fonts, even when translation is disabled,
because original Unicode chat and chat input use them. Missing fonts produce a
visible restore-files message. Restart after restoring files.

Models and terminology are data. Do not install community executable files or
replace the helper with an unreviewed download. The game never downloads models.
Developer preparation uses the pinned lock in
[dependencies.json](../development-source/translator/dependencies.json).
`python tools/Prepare-Translator.py --download` retrieves those exact dependencies;
without that flag it verifies the existing download cache. Preparation does not
install into the active game.

## Runtime budgets

The helper uses CTranslate2 CPU/int8 inference with two threads and below-normal
priority. Automatic detection considers its full language set and requires a
leading probability of at least 0.5 and a 0.2 lead over the next candidate.
Unsupported/ambiguous detections retain the original instead of forcing a guess.

The local synthetic benchmark on an Intel Core i7-13620H measured about **570 MB
peak working set and 3.68 GB peak committed memory**, with first automatic
translation around **1.68 seconds**, model-switch messages roughly **0.23-0.43
seconds**, representative two-step routes **0.51-0.66 seconds**, and cached repeats
below a millisecond. The final run was measured after the other test clients exited.
These are local measurements, not minimum-hardware certification. Detailed
inputs, outputs and timing are in `dist/translator-02/benchmark.json`.

Enforced limits: 4 GiB helper committed memory; 16 queued jobs and 16 results;
8-second work expiry/response deadline; 30-second retry delay after helper
failure; 128 cached messages; 511-byte received body and 1,536-byte translated
body. Rendering never waits for inference. Native tests check nonblocking submit,
cancellation and repeated language/model changes inside the job's memory limit.
A slow first load can finish after a message has expired from the chat panel.

## Terminology, provenance and licenses

UTF-8 terminology JSON files under `terms` can protect exact spellings and supply
reviewed complete phrases. Use the language codes in the table above:

```json
{
  "version": 1,
  "id": "community-terms",
  "preserve": ["Force Push", "Saber Trials"],
  "phrases": [
    {"source": "en", "target": "pb", "text": "good game", "translation": "bom jogo"}
  ]
}
```

Limits: 32 files, 64 KiB per file, 256 terms and 256 phrases per file; terms are
2-64 characters and phrases 1-256. No control characters or bidi override codes.
Exact phrases match the whole message ignoring case, with the first alphabetic
file definition winning. Names, addresses and recognized game terms are copied
unchanged; translating around protected spans can reduce grammatical fluency.
Slash commands are skipped. Terminology is not a substitute for trained models.
Contribute voluntary examples with language, region, intended meaning, rights
and an independent bilingual review; do not harvest other players' chat.

Each version-1 model manifest records source/target codes, tokenizer type,
upstream URL, archive SHA-256, license note and hashes of every runtime data file.
The worker rejects missing/extra files, unsafe paths and executable extensions.
Tokenizers are `sentencepiece`, `sentencepiece_dual` or `bpe`. Pack hashes establish
expected bytes, not universal model quality or permission to redistribute.

- Python 3.14.10, CTranslate2 4.9.0, SentencePiece 0.2.3 and py3langid 0.4.0 retain
  their bundled dependency license notices (PSF, MIT, Apache-2.0 and BSD).
- Most model directions use packages from the [Argos index](https://github.com/argosopentech/argospm-index).
  Per-package README/license notes are retained. Several older packages lack
  explicit model-license files; their final public redistribution review remains
  open. See the [maintainer licensing discussion](https://github.com/argosopentech/argos-translate/issues/76)
  and [missing-license discussion](https://github.com/argosopentech/argos-translate/issues/507).
- Korean to English uses [Helsinki-NLP OPUS-MT, 2019-12-18](https://github.com/Helsinki-NLP/OPUS-MT-train/tree/master/models/ko-en),
  converted locally to CTranslate2 int8. Its CC-BY-4.0 license, original README and
  conversion attribution are included. It replaces the initial Korean prototype
  model after incorrect help-request translations were found during testing.
- [Noto fonts](https://github.com/notofonts/noto-fonts) and
  [Noto CJK](https://github.com/notofonts/noto-cjk) retain their OFL-1.1 notices.

No public model bundle is published by these local preparation/install steps.

## Building and verification

Editable integration lives in `development-source/translator`. The Setup catalog
is generated with `tools/Generate-Setup-Catalog.py`. Local preparation verifies
the accepted English/Spanish install and overlays the verified pre-translator
source checkpoints. For a fresh checkout, follow the
[Windows checkpoint guide](WINDOWS-BUILD-CHECKPOINT.md), then use
`python tools/Build-Translator.py prepare dist/windows-checkpoint`.
Set `ST_DEPS` to the prepared native dependencies when needed. Fresh-checkout
builds remain staged; the local transaction installer requires a verified prior
installation. All outputs/evidence for this expansion use `dist/translator-02`.

```powershell
python tools/Prepare-Translator.py --download
python tools/Build-Translator.py prepare
python tools/Build-Translator.py engine
python tools/Build-Translator.py cgame
python tools/Build-Translator.py ui
python tools/Build-Translator.py qa
python tools/Build-Translator.py vanilla
python tools/Build-Translator.py rend2
cmake -S tests/translator -B dist/translator-02/tests -G "Visual Studio 18 2026" -A x64
cmake --build dist/translator-02/tests --config Release
& dist/translator-02/runtime/python.exe -B tools/Check-Translator-Languages.py
python tools/Benchmark-Translator.py
python tools/Check-Translator.py chat
python tools/Check-Translator.py settings
python tools/Check-Translator.py missing_pack
python tools/Check-Translator.py missing_helper
python tools/Check-Translator.py languages
python tools/Check-Translator.py languages --vanilla
python tools/Check-Translator-Network.py
python tools/Build-Translator.py validate
```

Run the Python translator tests in their own process with the prepared runtime:

```powershell
& dist/translator-02/runtime/python.exe -B tests/test_translator.py
```

The worker installs a process-wide network audit hook. A shared test process
would also block the loopback sockets used by other suites.

Tests cover every directed model, representative non-English pivots, detection,
Unicode boundaries/editing, real font rasterization, protected terms, missing
components, bounded queues, cancellation and offline execution. Live checks use
isolated profiles and synthetic chat, with screenshot review. Three production
clients check public/team/private audiences, location labels and UTF-8 server
transport. Location checks use a private copy of the stock map with named
location markers; the original map and server module are unchanged. Production UI omits test controls. Installation keeps a rollback backup
and verifies gameplay/assets/settings against the prior combined installation.

Native-speaker quality, real IME input, low-end machines, third-party chat mods
and remote public-host acceptance remain separate from these local checks.
