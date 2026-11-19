# Client overhaul source

First milestone: bindable replay recording, readable transparent console, and
menu integration. The rating library is separately maintained in services/ranking.

## Rebuild on Windows x64

Use Python 3.10+, Git, CMake, and Visual Studio 2026 with the C++ workload:

```
python tools/Build-Overhaul.py
python tools/Install-Overhaul.py
```

The build restores JACoders/OpenJK revision
`1a6a643427aa347553e9073dac5570b33337c4d9` from GitHub's archive, verifies SHA-256
`50dee49ccc3dc2b7a3333f6fb1cf50da976b40a38ba01d0971afe47d4ee5b52d`, applies the
three existing UI patches and the patches in this directory, and builds only
the multiplayer engine and UI. It does not reconstruct or replace game/cgame.
This engine/UI builder leaves the gameplay modules in place. The missing
client-game sources were recovered for the October 6 combat milestone; use
`tools/Build-Combat.py` for that separate paired game/cgame build. See
`development-source/client-game/README.md`.

Source and outputs go into `%TEMP%/SaberTrials-overhaul-20261003`. A production
build manifest hashes the executable and UI module. The installer checks these
hashes and refuses QA builds or binaries containing the test-only commands.
It installs inside the mod, backs up the existing UI DLL once, and creates an
incremental ZIP under dist. The ZIP requires an existing Saber Trials/OpenJK
installation. Parent GameData engines and base packages are never replaced.

## Verification

```
python -m unittest discover -s tests -v
python tools/Build-Overhaul.py --qa
python tools/Test-Overhaul.py start qa
python tools/Test-Overhaul.py recording
python tools/Test-Overhaul.py ui
python tools/Test-Overhaul.py keyboard
python tools/Test-Overhaul.py lifecycle
python tools/Test-Overhaul.py start qa
python tools/Test-Overhaul.py title
```

Allow the test client a few seconds to load before running checks. The runtime
uses a separate home folder and loopback-only local server; it does not touch
the player's profile. It hardlinks read-only stock asset packages into the
temporary test installation and copies the current game/cgame modules there.
Lifecycle and title-screen verification each close the test client. UI/keyboard checks inject
events through test-only entry points into the actual handlers and save
screenshots for visual inspection. Their hooks exist only in `--qa` builds.

Always rebuild **without `--qa`** before installation. Production verification
can use `start production`, `recording`, and `lifecycle`; UI event injection is
intentionally unavailable there. A rebuild restores the pinned source files
before patching, removing both QA hooks.

GPL-2.0 applies to the OpenJK-derived changes; preserve upstream notices.
The build manifest and pinned archive identify the corresponding source.
