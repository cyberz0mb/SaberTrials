# Multiplayer client compatibility

Open **SaberTrials.x86_64.exe** in **GameData** to play. The launcher uses that folder as the installation path, so the Mods menu can discover sibling mod folders. Selecting a mod loads it in the current client. For a mod that requires its own engine, open that mod's executable directly. Join through the server browser or enter `/connect host:port` in the console.

The updated Windows client creates a `screenshots` folder on your first in-game capture. Look inside `GameData/base` for Base JKA, `GameData/japlus` for JA+, or `GameData/SaberTrials` for Saber Trials. Windows must allow writes to that game folder.

Install personal map retextures in `GameData/base`. On a pure server, the
server chooses the permitted PK3s and their order. Use `/path` while connected
to see whether it lists the pack as approved. Server owners can install the
matching PK3 in their server's `base` directory and restart the server to
advertise it. The Windows renderers support replacement JPEG images stored
under the original PNG filename, as used by JKA Tex Overhaul 0.3.

For Windows beta 1.8, the Vanilla renderer loaded all 1,051 JPG and PNG files
from that PK3 across isolated test scenes. Rend2 and Vulkan also loaded the
pack's JPEG-encoded monitor texture at its native 1024 × 512 resolution.

The Windows client uses the Saber Trials UI and client-game interfaces in the SaberTrials game directory. For another game directory it requests the stock OpenJK interfaces and passes stock-sized player and vehicle states to the client game. After package resolution, Base JKA uses the bundled x64 client-game module for every HUD choice. JA+ can supply its own mod-specific module or use the bundled JA+ client. The Saber Trials, Base and JA+ client modules shipped in beta 1.7 draw the ballot, voting hint and team vote with the HUD font and a drop shadow. Pure packages, checksums and server download policy still use the engine's normal paths. A server that requires a particular client plugin can require additional files. A 64-bit process cannot load a 32-bit DLL.

Photo Mode requires a Saber Trials game. Base JKA, OpenJK and JA+ still support
live previews in **Setup > Camera** and the normal screenshot command. The JA+
grapple cable uses the owner carried in the hook's snapshot and draws from that
player's hand. A local player can be represented solely by the predicted player
state. The server supplies the hook position and handles pulling and release.

Your display name is shared across mods and servers. The client starts with the
name in your active profile on first use. Changing it in **Profile** or with
`/name` updates the shared name, including color codes and spaces. Each server
applies its own naming rules.

The JA+ wheel has five pages with 39 selections. It covers the 37 entries in the published JA+ emote list and retains `amdance` and `amtaunt` for servers that support those aliases. The server controls availability and plays each animation. [JA+ command list](https://jkhub.org/tutorials/specific-mods/japlus/ja-command-list-r218/) · [JA+ emote settings](https://jkhub.org/sites/japlus/bitvalueCalculator.php.html)

In **Profile → Emotes → JA+ wheel**, choose a page, select an emote in the library and a wheel slot, then choose **Assign to slot**. **Clear slot** leaves that position empty. All eight positions on each of the five pages are editable. Changes save immediately to the local player's Saber Trials home directory and apply on the next wheel opening. The Saber Trials wheel has its own layout.

Selecting a JA+ emote loops a preview on the profile character. It reads the active humanoid's animation table, including the JA+ animation pack when available. Some server aliases use representative Jedi Academy motions, and paired actions preview one participant. The server chooses the actual motion in a match.

Hold your wheel binding and change pages with the mouse wheel, Left/Right arrows, or controller bumpers. Select with the pointer or keys 1–8 and release to confirm. Each opening starts on page one. Base JKA keeps its single page of five gestures. If the external mod has its own bindings, assign a free key to `+st_emotewheel`. On disconnect the client returns to the Saber Trials game directory when the session started there.

## Validation

Build with `python tools/Build-Mod-Compatibility.py build`. The build uses the combined pickup/ladder source and the pinned OpenJK archive already used by the project. Install with `python tools/Build-Mod-Compatibility.py install`. The installer checks the installed client version and backs up replaced files.

Run `python tests/compatibility/playback.py record dist/compat/qa` to record stock OpenJK play. Repeat with `play`, `retail`, `wheel` and `trials` to exercise the installed mod directories, retail assets with the bundled modules, wheel input and command delivery to a local pure listen-server fixture, and the Saber Trials modules with adaptive networking.

Use `profile` to assign and clear slots through the Profile editor, restart the test client with the same home directory, and check the commands received from the edited JA+ wheel.

## Saber Trials menus and chat on other servers

The Windows client opens the full Saber Trials pause menu on base JKA, OpenJK and JA+ connections. When the game asks for character selection, the same Saber Trials Player Profile opens automatically. **Player > Emotes** opens the wheel editor. **Server menu** opens the connected mod's original menus.

Open **Setup > Interface** to adjust chat, select an outgoing chat color and configure offline text translation. Choose **Apply changes** to save. Select **Chat box > Server mod** to use the connected mod's chat display. Translation uses chat accepted by the current game's standard chat handler. The recipient's server and chat renderer determine which colors are visible.

The client includes the chosen color in public, team and private messages sent through the chat field, console and binds. An explicit color at the start of a message takes priority. **Default** leaves the server's normal public, team or private color in effect.

The full interface uses the companion file `client/SaberTrialsUI.x86_64.dll` shipped next to the executable. In **Setup > Interface > HUD style**, choose **Saber Trials** or **Server mod**, then **Apply changes**. The Saber Trials combat HUD shows health, armor, weapon, ammo or Force, and score from the received player state. Its scale, panel opacity and low-health pulse use the Interface settings. Server mod is the initial choice on foreign servers. Spectators, vehicles, mounted guns, Siege objectives and the full scoreboard use the mod's presentation. Handedness and extra combat styles require Saber Trials gameplay support.

Run `python tests/compatibility/personal_ui.py` after installing to exercise character selection, pause, Profile, settings, saving chat color, translation, JA+ wheel editing and the original server menu on a pure local fixture. Run `python tests/compatibility/peer_color.py` for a local stock OpenJK observer over UDP. Its `--replay` mode records the server's messages and plays them on a separate stock client with a fresh profile. Check the observer's chat box for cyan public, team and private messages, red explicit text and the server default.

## JA+ sabers and controls

Join a JA+ server using the usual Saber Trials shortcut. In **Profile > Sabers > Crystal**, choose a hilt, set its RGB sliders or hex value, choose a blade style and apply. Each hilt can use Normal, Flame, Electric, Flame 2 or Electric 2. All blades on a hilt share its color. The client keeps these choices between JA+ sessions. A server that advertises RGB as disabled locks the controls and the client drops the custom colors from its next update.

| Controls category | Action | Console binding |
| --- | --- | --- |
| Movement | Hold to fire or pull with the grapple | `+st_jaGrapple` |
| Movement | Toggle jetpack | `st_jaJetpack` |
| Combat | Challenge the target to a full Force duel | `st_jaFullForceDuel` |

Assign your own keys in Controls. These actions appear and send input only during a JA+ game. The server decides whether an action succeeds. Saber Trials sends the original plugin's per-hilt userinfo fields and renders the colors the server publishes for each player. The JA+ renderer uses the installed mod's blade effects when available and a tinted base effect otherwise. The server and each observer's client determine what other players see. [Original JA+ client plugin documentation](https://mrwonko.de/jk3files/Jedi%20Academy/Mods/Multiplayer/120347/)

Use **Apply changes** in Controls or **Apply and return** when leaving. If the grapple does nothing, press and release the key during play, then run `/st_jaStatus`. It reports the assigned key, whether the client sent a grapple press, and the server's advertised hook rule. An unreported rule leaves the decision to the server. JA+ can enable hooks for everyone, limit them to mercenaries, or disable them. [Slider's grapple settings](https://www.lucasforumsarchive.com/thread/128489-ja-mod-v20-amp-clientside-plugin-v10)

Enter `/st_jaStatus` to check whether JA+ and RGB are active and whether the server published each hilt's color. It prints your selections as packed `0xRRGGBB` decimal values and the server's packed RGB in JA+ byte order. Servers that require Slider's original plugin can limit enhanced features or require their own files. When the server enables suspended grappling, release stops the pull and **Use** detaches the hook. [JA+ grapple controls](https://mrwonko.de/jk3files/Jedi%20Academy/Mods/Multiplayer/120347/)

Run `python tests/compatibility/ja_features.py` to exercise the saber menu, outgoing inputs, the RGB restriction, and isolation on base JKA and Saber Trials. It uses a local receiver in a JA+ game directory and a base JKA fixture with pure checks enabled. The native Saber Trials check uses its non-pure development configuration. Run `python tests/compatibility/ja_render.py` to check the actual blade, lighting and hook drawing functions using known player and hook data.

Run `python tests/compatibility/ja_presentation.py rd-rend2` and repeat with `rd-vulkan` for the crystal swatches, emote previews, the Controls binding and the lighting grid on `t2_rancor`. On a live JA+ server, `/st_jaLight` reports the map, player position and sampled lighting for comparison if an area still renders dark.

### Optional build inputs

Some compatibility and packaging scripts expect locally supplied community HUD
and cosmetic archives and generated HUD font variants. These inputs are kept
separate from the source repository. Use assets you have permission to use.
