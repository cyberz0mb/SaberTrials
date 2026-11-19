# Recovered multiplayer client-game overlay

This directory preserves the complete modified client-game source used by the
paired combat build. Base revision: OpenJK
`1a6a643427aa347553e9073dac5570b33337c4d9`, matching the engine/UI milestone.

Eight modified files were recovered on 2026-10-06 from the earlier local
OpenJK-SaberTrials checkout under Documents/Codex (that checkout was read-only).
The saved `client-streamer-broadcast.patch`, presentation include and
`client-private-duel-collision.patch` were then incorporated. This preserves the
extended FFA scoreboard protocol, private-duel rendering/collision and Streamer
Mode presentation while adding combat-recovery synchronization.

`python tools/Build-Combat.py` restores the checksum-verified pinned archive,
overlays `development-source/bot-roles/codemp` and this directory's `codemp`, then
clean-builds `jampgamex86_64.dll` and `cgamex86_64.dll`. Requires CMake and VS 2026
C++ tools. It writes a production manifest with both hashes. Source overlays and
the upstream archive retain their GPL-2.0 license notices.

`--qa` adds isolated runtime probes from `tests/combat_*_qa.inc`; these builds
must never be installed or distributed. `tools/Test-Combat.py` uses a separate
temporary profile and loopback-only server. A production build restores pristine
files first, removing all QA hooks. Installation verifies the production manifest
and rejects any test commands in either DLL.

The client reads the authoritative preset/recovery settings from serverinfo.
Legacy Saber Trials servers without these settings retain enhanced recovery;
ordinary servers without them use stock recovery.

The October 6 head-portrait follow-up adds `cg_sabertrials_portrait.inc`, four
archived cvars, client-model invalidation and a `CG_Shutdown` cleanup call.
`cg_main.c` is the pinned upstream file with that cleanup call. Use
`tools/Build-Portrait.py` for the matching cgame/UI release and consult
`docs/Head-Portrait.md`; the gameplay overlay still builds with Build-Combat.

## HUD overlay — October 7, 2026

The current cgame also includes `cg_sabertrials_hud.inc` and four archived
`st_hud*` cvars. `ST_HudRegister` loads original HUD art on every client-game
initialization. This update retains the portrait module and original HUD path.

Use `tools/Build-Hud.py`, `tools/Generate-Hud.py`, and `tools/Install-Hud.py` for
the current complete client/UI milestone. The HUD requires its staged
`gfx/sabertrials/hud` assets and updated Setup menus. Older standalone installers
predate those assets; do not use them as a current complete HUD distribution.
The generator requires Pillow. See `docs/HUD.md` for settings and verification.
