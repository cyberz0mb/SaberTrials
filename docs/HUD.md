# Saber Trials HUD

The gameplay HUD follows the accepted dark glass/cyan concept. Health and armor
sit at the lower left, saber style and Force at the lower right, and score above
the live head portrait. Panels, icons and original geometric lettering stay
proportional across screen sizes. The central fighting area remains clear.

Open **Setup > UI Settings > HUD appearance** from either menu. Choose Saber
Trials or Original JKA, toggle the score or low-health pulse, and set HUD size
(75–125%) and panel opacity (0–100%) with sliders or typed values. Click Apply
for size/opacity; the other switches take effect immediately. Reset HUD defaults
affects only these HUD settings. Portrait options remain separate.

Console settings: `st_hudStyle 1` (Saber Trials, default), `0` (original);
`st_hudScale 100`; `st_hudOpacity 55`; `st_hudPulse 1`. Original JKA retains the
existing `cg_hudFiles` selection. `cg_drawScores`, `cg_drawStatus`, `cg_draw2D`,
and Streamer Mode's clean HUD keep their existing roles.

Numbers come from the received player state. Bars fill to the player's maximum
health/armor and Force capacity; over-cap numbers remain accurate. Armor keeps
JKA's maximum-health-based meter capacity. Weapons show ammunition and a Force
readout when applicable. Duel scores include the frag limit when one is set;
team games also show red/blue totals. Siege objectives and vehicle HUDs retain
their existing specialized displays. Following a player shows the received
player's values; free spectators have no invented health/ammo readouts.

## Assets and build

`tools/Generate-Hud.py` creates original transparent TGA panel/icon assets and a
stroke-letter atlas, plus both Setup pages from accepted portrait-era menu
snapshots. No Blender, external font, or separate user-created PK3 is required.
Generation is reproducible and leaves the portrait menu and character files intact.

`tools/Build-Hud.py` builds cgame and UI from pinned OpenJK plus the existing
overlays. `tools/Test-Hud.py` uses a separate local test profile. QA hooks are
never shipped. `tools/Install-Hud.py` verifies production hashes, preserves a
rollback backup, and packages the corresponding source. Older menu/portrait
installers predate this milestone. The subsequent interface update
moves the controls to UI Settings; install that refinement last to preserve the
current navigation and compact pause menu.
