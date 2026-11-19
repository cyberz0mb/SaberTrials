# Private humanoid animation compatibility

The reported Akaza T-pose was traced to the installed model's private facial
animation file, rather than the mesh or the chosen combat damage/timing.

| Installed asset | Animation source | Frames | Bones |
|---|---|---:|---:|
| `GameData/base/akaza.pk3` / `models/players/akaza/model.glm` | `models/players/_humanoid/akaza_face.gla` | 21,376 | 53 |
| `GameData/base/zzz_JangoFett.pk3` / `models/players/jangothefett/model.glm` | shared `_humanoid/_humanoid.gla` | 22,443 with installed stance package | 53 |
| `zz_sabertrials_stances_v1.pk3` | shared `_humanoid/_humanoid.gla` | 22,443 | 53 |

The ready stance frames start at 22,374 and end at 22,442. Akaza's private file
does not contain them, although the model uses the shared humanoid animation
table naming them. Jango uses the extended shared file and therefore works.

Binary comparison confirmed identical names, bone order and parent hierarchy.
Akaza changes eight facial bind matrices (`ceyebrow`, `jaw`, `lblip2`, `leye`,
`rblip2`, `ltlip2`, `rtlip2`, `reye`). Only facial expression frames 0–17 have
different compressed transforms; every body-frame transform from 18 through
21,375 matches the shared file.

## Runtime change

`development-source/hybrid-styles/model_compat.py` installs one shared C++ helper
and hooks it immediately after a disk read, before model-cache ownership and
endianness conversion:

- Vanilla and dedicated: `RE_RegisterModels_GetDiskFile`, `tr_model.cpp`.
- Rend2: `CModelCacheManager::LoadFile`, `tr_cache.cpp`.

The helper verifies the source and donor before importing frames. It supports
the stock 21,376-frame and community 22,374-frame prefixes with the same
53-bone topology and body bind matrices. All existing body transforms must
match the canonical source. Private facial matrices and expression frames
may differ and remain unchanged. Unsupported rigs are left intact, with a
developer-console explanation; this is not a claim that their custom stances
are supported. A separate per-model UI capability indication remains useful
for unsupported private animation layouts.

The helper preserves the private skeleton, existing frame indices and entire
compressed-pose pool. It appends missing canonical frames and remaps their
pose indices into an appended pool. Only `numFrames`, `ofsCompBonePool` and
`ofsEnd` change in the header. Installed PK3s, exported models and editable
source files are untouched. No animation-source redirection can erase the
character's facial adaptations.

The replacement uses `Z_Malloc(TAG_FILESYS)` and is transferred through the
existing cache ownership path. Both old raw and temporary donor buffers are
freed once. The canonical GLA bypasses the adapter to avoid recursive loads;
cached models bypass disk loading altogether.

## Verification

Run `tests/hybrid-models/run.py --installed-akaza` using the project's Python.
It extracts read-only fixtures into `dist/hybrid-model-tests`, compiles the
native helper with MSVC, and runs three tests:

1. Synthetic pose preservation, imported frame correctness, allowed private
   facial changes, incompatible body edits, unknown frame layouts, malformed
   offsets, invalid indices, cyclic parent rejection and truncated files.
2. The exact engine adapter with mocked filesystem/zone ownership, checking
   allocation transfer, original and donor cleanup, recursion exclusion and
   missing-donor behavior.
3. The actual installed Akaza and shared stance files, checking every original
   skeleton byte, existing frame-index byte, pose-pool byte and decoded pose,
   plus every imported frame against the canonical donor.

All three native tests passed on 2026-10-30. They are data/ownership checks,
not visual game acceptance. No game, server or Blender process was launched.
