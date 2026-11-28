# Ignore player chat

In **Controls → Key Bindings → Communication**, select **Ignore player** and assign a key or controller button. Apply the binding. During a match, aim at another player and press the button. The screen shows “Player name is now ignored.” Aim at the same player and press again to restore their chat. Pressing it while aiming at empty space leaves your settings alone.

| Console command | Effect |
| --- | --- |
| `ignore` | Toggle the player under your crosshair. |
| `ignore Raven` or `ignore "Blue Raven"` | Ignore an exact player name. Names can contain spaces. Matching ignores capitalization and color codes. |
| `ignore 4` or `ignore #4` | Ignore the player in slot 4. Use a slot when names match. |
| `ignore all` | Ignore chat from other players, including new arrivals. |
| `unignore Raven` or `unignore 4` | Restore that player's chat, including while ignoring everyone else. |
| `unignore all` | Clear all chat ignores and exceptions. |

Only **Ignore player** appears in Controls. For a console binding, use `bind F8 "ignore"` with your preferred free key.

Ignore covers incoming public, team and private text, including chat beeps and translations. Server notices and match results still appear. Settings apply locally for the current server visit. An individual ignore follows a connected player who renames and ends when that player leaves. Disconnecting clears your ignore settings.
