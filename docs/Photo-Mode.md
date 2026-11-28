# Photo Mode

In a Saber Trials game, open the pause menu and choose **Photo Mode**. On other
servers the menu shows **Requires a Saber Trials server**. The scene previews field of view
and tilt as you edit. **Apply camera**, **Start / Resume** and **Take photo**
save valid values.
**Start / Resume** closes the menu. **Take photo** saves a clean PNG after the
menu closes, with no HUD, portrait, composition grid or control hints.

## Local solo play

**Scene: Live / Freeze** controls whether the scene keeps moving. Live is the
default. Freeze is available when you are the only human in a local game;
bots are allowed. You can continue moving the camera while the scene is frozen.
The game resumes when Photo Mode exits or another human connects.

| Key | Action in the solo/replay camera |
| --- | --- |
| WASD and mouse | Move and look |
| Space / Ctrl | Move up / down |
| Shift | Move slowly |
| Mouse wheel | Zoom |
| Enter or left click | Save a clean photo |
| Tab | Camera settings |
| F | Live / Freeze in local solo play |
| Escape | Exit Photo Mode |

Freeze affects the local scene, not the operating system or audio playback.
It does not pause a remote multiplayer server. Map changes, disconnects and
leaving Photo Mode release any pause owned by Photo Mode.

## Playing on a live Saber Trials server

Choose **Photo Mode > Start / Resume** to orbit your character during ordinary
on-foot play. Move the mouse or use the arrow keys to turn the camera around
your character. Scroll to change the distance, press Enter or left-click to take
a clean PNG, and press Escape to return to play. The match continues while
you frame the shot. Orbit uses the mod's third-person camera and wall collision.
Your saved camera distance, angles and key bindings are preserved.

## Saber Trials spectators and recordings

If you are already spectating, Photo Mode uses the game's ordinary
spectator movement so the server sends the scene visible from that position.
Use the Photo Mode menu to capture, change the lens/tilt, or exit. Online movement
uses the normal spectator speed. The Scene toggle is unavailable online.

During a recorded demo, `st_photo` opens the movable camera. It uses the controls
above. Replay footage contains only the objects recorded by that client;
moving to a distant room cannot recover objects absent from the recording.
This first version does not add replay scrubbing or replay freeze controls.

## Capture and saved preferences

Images are saved in the active game profile's `SaberTrials/screenshots` folder
as timestamped PNG files. `st_photoCapture` can also be bound to a spare key.
It enters Photo Mode when eligible and waits for an open menu/console to close
before capturing. The composition grid and control hints remain optional.

Your HUD, portrait, Streamer Mode, normal FOV and control bindings are preserved.
Photo lens/tilt/speed preferences are separate. Reset camera restores Photo Mode
defaults only. Use the Saber Trials overhaul launcher so the updated client
can enforce local-only Freeze.

## Build and scope

`tools/Build-Photo.py` builds engine, cgame and UI against the pinned OpenJK
revision. `tools/Stage-Photo.py` changes only the Photo Mode page in the pause
menu. `tools/Test-Photo.py` runs an isolated native game and captures evidence;
test commands are compiled only with `--qa` and are excluded from production.
`tools/Install-Photo.py` verifies build/test hashes, backs up each replacement,
checks protected files and packages the corresponding source overlays.
The update archive also includes the checksum-verified upstream OpenJK source
archive under `source/`. The complete changed game/cgame/UI overlays and patches
are included; the build helper pins that source revision and verifies its hash.

The installed server game module and existing combat/ranked rules are unchanged.
The renderer used for native verification is vanilla; Rend2 and physical input
feel still require a player check. See `dist/photo-install-manifest.json` for
installed hashes and the rollback backup location.
