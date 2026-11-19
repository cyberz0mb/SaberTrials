# Match recording and transparent console

Open the **Saber Trials** shortcut or [the current Windows launcher](../tools/launchers/SaberTrials.cmd) with the matching Saber Trials client installed.

## Record a match

1. Join a game or watch a match as a spectator.
2. Open **Controls > Other > Record Match** and press your preferred key.
3. Press that key in gameplay to start recording, and again to stop.

The binding is available from both the title screen and the in-game menu.
No occupied key is replaced automatically. The console command `st_record`
performs the same toggle. The existing `record` and `stoprecord` commands also
remain available. `st_recording` reports 1 while recording and 0 when stopped;
it is read-only. Enable `cl_drawRecording 1` to display the recording indicator.

Stopping prints the saved filename. Automatic names include the date/time and
add a numeric suffix when needed, so rapidly starting another recording does
not replace the previous one. Disconnecting normally finalizes the active
recording. A crash or forced process termination can still leave an incomplete
file.

Recordings are **game replays (`.dm_26`), not MP4 videos**. They contain the
client's received game state; a player's recording is not a server-wide replay
of unseen action. Playback needs compatible game assets and modules.

Files are saved under `SaberTrials/demos` in the engine's writable home folder.
Type `fs_homepath` in the console to find that folder. To play a recording,
use its exact filename, for example:

```
demo demo2026-10-03_10-00-00.dm_26
```

Starting playback leaves the current server. Recording while disconnected or
while watching a replay is rejected. Video export and a replay browser are
future work; this update supplies recording and standard console playback.

## Console appearance

Open **Setup > Input**:

- **Console Overlay** uses a plain dark background instead of the original art.
- **Console Opacity** changes background opacity immediately. Text stays solid.

New profiles default to the overlay at 55% opacity. Existing saved opacity
values are respected. The command-entry strip retains a dark backing even at
zero background opacity, and a disconnected full-screen console remains dark
for readability. Console typing, command history, completion, and colors use
the existing engine behavior.

Equivalent commands are `st_consoleOverlay 1` and `con_opacity 0.55`. Use
`st_consoleOverlay 0` to return to the original background style. These controls
do not change the Turn Speed or Mouse Accel defaults.
