# Saber Trials role-bot source snapshot

These source overrides include TFFA team-lock votes and the 2026-09-12 menu
voting/settings update. The latter enables menu limit/map votes and validates
limit proposals on the server.

The build checkout was based on JACoders/OpenJK commit
`1a6a643427aa347553e9073dac5570b33337c4d9`. Keeping this revision recorded
allows the snapshot to be reconstructed while the complete public source tree
and reproducible build instructions are prepared.

This snapshot includes the earlier Saber Trials gameplay, Tournament, Streamer server support, and monitor-only Guard changes as well as the FFA/TFFA/CTF role-bot implementation. Overlay the `codemp` directory onto the same OpenJK/Saber Trials source revision, then configure and build the `jampgamex86_64` target.

The client prediction addition for pass-through private duels is recorded in
`patches/client-private-duel-collision.patch`. Apply it to the matching
`codemp/cgame/cg_predict.c` before building `cgamex86_64`; it mirrors the
server collision rule so hidden duel participants never cause prediction
jitter or an invisible wall.

The Streamer Mode broadcast additions are recorded in
`patches/client-streamer-broadcast.patch`. They add the client cvars, kill-feed
event hook, and smooth follow-camera integration. Insert
`development-source/client-streamer/cg_streamer_presentation.inc` immediately
before `CG_Draw2D` in `codemp/cgame/cg_draw.c`; it contains the exact kill-feed,
line-of-sight spectator-label, grouped-team-score, and match-clock presentation
source used by the shipped `cgamex86_64.dll`.

The Profile roster addition is recorded in
`patches/ui-built-in-character-roster.patch`. Apply it to
`codemp/ui/ui_main.c` before building `uix86_64`; it exposes selected built-in
NPC actors without copying base-game models, skins, textures, or portraits.

The matching UI menu, server configuration, and documentation remain in the live mod directories. This development-source folder is excluded from `tools/Build-Pk3.ps1` and ignored by the game engine.

The menu actions are in `codemp/ui/ui_sabertrials_menu.inc`. Apply
`patches/ui-menu-controls.patch` to include and dispatch them from `ui_main.c`,
alongside the existing roster patch. Rebuild `uix86_64` for the editable vote
fields, current-mode map list, and validated Turn Speed/Mouse Accel settings.

The paired input sliders and numeric fields also require
`patches/ui-input-sliders.patch` applied to `codemp/ui/ui_shared.c`. It keeps
their slider values compact and within bounds and allows a click leaving
either number box to activate the next control immediately. The menu actions
include per-row and combined draft resets, compact values, and field viewport
resets. Recompile `ui_main.c` after editing the `.inc` if incremental dependency
tracking does not notice the change.
