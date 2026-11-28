# Text colors and saved chat color

The existing shared client/server palette already accepts all ten numeric
escape codes. The Windows Unicode chat renderer previously masked its digit
index with `&7` and had only eight brushes, so `^8` and `^9` displayed incorrectly.
It now uses ten brushes: `^8` orange, `^9` gray, and `^0` true black. Per the
user's preference, black is RGB 0/0/0 with no added light outline in chat,
the chat preview, or the custom menu font.

| Code | Color |
| --- | --- |
| `^1` | Red |
| `^2` | Green |
| `^3` | Yellow |
| `^4` | Blue |
| `^5` | Cyan |
| `^6` | Magenta |
| `^7` | White |
| `^8` | Orange |
| `^9` | Gray |
| `^0` | Black |

Profile's name keyboard exposes all ten as pointer/controller accessible color
keys, ordered 1–9 then 0. Choosing one inserts its escape code at the caret and
updates the existing live name preview. Choosing another color at the same
position replaces the preceding code instead of consuming more name capacity.
Caret movement and backspace treat complete color escapes as single tokens.

Setup > UI Settings > Chat includes **Chat text color**. `st_chatColor` is a
personal archived preference, default `-1` (server default), with choices 0–9.
The chat box preview shows the draft color on the sample outgoing message.
Apply saves it; Cancel preserves the previous choice. It prefixes messages
submitted through the public, team and private chat fields, including gamepad
entry. Inline codes can still change individual words. It does not recolor
other players' messages or alter manually executed console `say` commands.

The input preview uses the preference too. The sender reserves room for the
two-byte escape, and truncates only at complete UTF-8/color-token boundaries
if the preference changed while editing. No server/gameplay changes are needed.

`tools/Build-Text-Colors.py` uses the installed controller-response engine and
menu-selection UI as receipt-verified baselines. It builds/installs only the
client executable and UI module, preserving those updates, the Berserker
gameplay, menu assets, border animation, translator and saved settings. No game
is launched: the user requested to perform in-game testing personally.

The follow-up `tools/Build-Black-Text.py` preserves the later anti-script engine
and multi-team frontend while removing the original black outline. It installs
only the client executable and UI module; gameplay and other text colors are
unchanged.
