# Windows source checkpoint

Build the offline installer after generating the matching Full and Lite beta ZIPs
in `dist/private-beta`. Run `python tools/Package-Windows-Installer.py` with
Inno Setup 7's `ISCC.exe` on PATH, or pass its path with `--compiler`. Use
`--work` to stage large builds on another drive. The installer takes its version
from the same file as the client and derives its edition contents from the ZIPs.

This checkpoint preserves the source used for the November 12, 2026 Windows
installation. The normal client, UI, game/cgame, renderers and dedicated
executable came from different source trees. Keep these roles separate when
reconstructing the build.

| Source role | Matching targets | Recorded baseline |
| --- | --- | --- |
| `engine` | `openjk.x86_64` (installed as `SaberTrials.x86_64.exe`) | Chat panel engine |
| `frontend` | `uix86_64`, `cgamex86_64` | Chat panel UI plus Weapon DLC client |
| `game` | `jampgamex86_64` | Weapon DLC gameplay |
| `dedicated-renderers` | `openjkded.x86_64`, `rd-vanilla_x86_64`, `rd-rend2_x86_64` | Enhanced Maps and Enhanced Models |

The [checkpoint manifest](../development-source/windows-checkpoint/manifest.json)
pins the upstream OpenJK revision, archive hash, changed source bytes and
resulting tree for each role. The overlays are relative to that upstream
source. Continue feature work in the editable feature directories and build
tools, then regenerate the checkpoint when capturing a new build.

## Reconstruct the source and authored UI packages

From the repository root, run:

```powershell
python tools/Restore-Windows-Source.py
```

Use `--archive PATH` to supply a local copy of the pinned OpenJK source archive.
The script verifies the archive and restores the four source trees and UI
packages under `dist/windows-checkpoint`. Game data and compatible animation
packages are separate inputs.

## Compile

Use Visual Studio 2026 with Desktop Development with C++, CMake and x64
dependencies prepared through [Build-Staff.py](../tools/Build-Staff.py) and its
[dependency lock](../development-source/staff/dependencies/lock.json).
Configure each role in its own build directory with the `Visual Studio 18 2026`
generator, `-A x64`, `-DST_STAFF_QA=OFF` and `-DST_DEPS=PATH_TO_DEPS`. Turn
on the indicated CMake options and set the other multiplayer and
single-player build options to `OFF`.

| Role | Enable |
| --- | --- |
| `engine` | `BuildMPEngine` |
| `frontend` | `BuildMPUI`, `BuildMPCGame` |
| `game` | `BuildMPGame` |
| `dedicated-renderers` | `BuildMPEngine`, `BuildMPDed`, `BuildMPRdVanilla`, `BuildMPRend2` |

Build the targets in Release. The restored source is checked byte for byte
against the recorded source trees. Toolchain dependencies and matching runtime
packages are still needed for a clean-machine build and playtest. The Windows
checkpoint is separate from the Tournament-enabled and Linux server builds.
For historical install and verification procedures, see the feature guides
linked in the [changelog](CHANGELOG.md).
