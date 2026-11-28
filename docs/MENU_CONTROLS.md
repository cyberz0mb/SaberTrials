# Menu voting and personal settings

Press Escape during a match to use the existing **Vote**, **Call Vote**, and
**Setup** tabs. Vote casts Yes or No on the active proposal. Call Vote creates
a new proposal; changing a field alone does not alter the match.

## Call Vote

- **General:** restart/next map, warmup on/off, Restricted/Full Force,
  and TFFA Lock/Unlock Teams.
- **Game Type:** enter a Time Limit and a Frag Limit, then click the matching
  **Vote** button. CTF shows Capture Limit instead of Frag Limit. The Type
  selector offers FFA, Duel, Power Duel, TFFA, CTF, Siege, PUG, and Ladder. Submit it with
  **Call Game Type Vote**.
- **Map:** select a locally installed map for the current game type and click
  **Call Map Vote**. The server must also have the map and accept its mode.
- **Kick:** select a player or bot, then call the vote. Staff protection applies.
- **Bots:** choose a role supported by the current game type.

Limits apply to the current mode, independently of the proposed Type selection.
Time Limit accepts minutes from 0 to 1440; score limits accept whole numbers
from 0 to 999. Zero means unlimited. A passed limit vote takes effect after the
server's normal vote execution delay; lowering a limit below the current time
or score can end the round. Game-type and Force-mode changes retain their
existing next-round scheduling. Tournament keeps its fixed one-kill rounds and
rejects Frag Limit votes while it controls Duel.

Spectators can call and cast votes. Existing cooldowns, per-map limits, majority
requirements, and server overrides apply. The shipped `g_allowVote` mask is
16383, enabling all 14 supported vote commands. Known older shipped masks,
including 15410, migrate automatically; disabled voting and other custom masks
are preserved. Operators can use `toggleallowvote` to customize the list.

## Setup

Existing Video, More Video, Sound, Game Options, Streamer Mode, and Defaults
remain available.

**Network** provides Allow Downloads, Max Packets, Packet Dup, Snaps, Rate, and
Time Nudge. These change your local settings immediately. Requested network
rates remain subject to the engine and server limits. OpenJK's Time Nudge is a
session setting; the other listed network settings are archived by the engine.

**Input** provides:

- **Turn Speed** (`cl_yawspeed`): keyboard/bound turn-command speed, separate
  from mouse sensitivity. Accepts 0–10000, including decimals.
- **Mouse Accel** (`cl_mouseAccel`): acceleration amount. Zero disables it;
  positive values enable it using the client's current acceleration style.
  Accepts 0–100, including decimals.

Each row has a slider, an editable number box, and **Reset**. The sliders cover
Turn Speed 0–500 and Mouse Accel 0–2 for convenient adjustment; the number boxes
accept the wider ranges above. Both controls share the same draft value. A value
beyond a slider's range is preserved until you move that slider.

**Reset** restores that row; **Reset Input Defaults** restores Turn Speed 140
and Mouse Accel 0. Click **Apply Input** to save both draft values, including
resets. Invalid values leave both existing settings intact. These are personal
settings and do not require a vote. Mouse sensitivity remains under Controls.

Click a number to type a replacement, including decimals. Backspace, Delete,
Home, and End work while editing. Apply, Reset, and the other controls respond
to the first click when leaving a number box. Values use compact formatting,
and each box allows 32 characters instead of filling up with trailing zeros.

## Build source

Overlay `development-source/bot-roles/codemp` onto the OpenJK revision recorded
in `development-source/bot-roles/SOURCE_NOTE.md`. Apply the three UI patches:
`ui-built-in-character-roster.patch`, `ui-menu-controls.patch`, and
`ui-input-sliders.patch`, then build
`jampgamex86_64` and `uix86_64`. The existing client module is compatible.
After changing the menu action `.inc`, force `ui_main.c` to rebuild if the
build system does not track that include automatically.

## Verification

Built the Windows x64 gameplay and UI modules and tested with an isolated
OpenJK profile on September 12–13, 2026. Menu actions called and passed
time-limit, frag-limit, CTF capture-limit, and map votes; the server applied
the limits and reloaded the selected map. Invalid limit values were rejected.
Turn Speed 240 and Mouse Accel 0.125 were saved and read back after restarting
the client; invalid input preserved both previous values. Rendered and checked
the General, Game Type, Map, Network, and Input pages. The CTF page substitutes
Capture Limit, and its map list contains CTF arenas. The previous default vote
mask migrated to 16383; disabled voting remained disabled after a restart.

On September 14, exercised the Input page through actual UI mouse/key events
in an isolated test build: replacing digits, decimals, Backspace/Delete,
switching fields, clicking Apply directly from editing, dragging/clicking
sliders, preserving larger manually entered values, per-row/all-input resets,
invalid-input rejection, and slider boundary clamping. Checked the rendered
page after resetting a long entry. Test-only commands are removed from the
installed production UI module.
