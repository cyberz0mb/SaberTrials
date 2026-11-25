# Adaptive network optimization

Open **Setup → Network**, choose a mode and select **Apply changes**. Auto is the default. Manual exposes the five connection values. Off releases adaptive settings. Network statistics is a separate toggle in all three modes. The console command `st_netStatus` prints the same information.

## What Auto adjusts

| Setting | Behavior verified in the MP source | Auto behavior |
|---|---|---|
| `cl_timeNudge` | `CL_SetCGameTime` subtracts the offset from the client clock. The release engine clamps it to −30 through +30 ms and prevents time from going backwards. | Uses 0 through +8 ms. A stable distant connection gets zero additional delay. Variable arrival times can get a small interpolation cushion. |
| `cl_maxpackets` | The Internet send path supports 20–1000 packets/s and runs once per client frame. | Starts at 1000 in Auto. After two windows with at least 2% incoming loss, Auto tries 75% of the measured outgoing packet rate. If loss fails to improve by one percentage point in the next window, it restores 1000. Two healthy windows also restore 1000. |
| `cl_packetdup` | Values 0–5 select how far back to fetch commands for the next outgoing message. | Uses one prior packet of commands, or two on a lossy connection. Incoming loss is a heuristic for this choice. The client cannot directly measure outgoing loss. |
| `snaps` | The server controls the snapshot interval. | Requests the advertised server FPS, subject to its snapshot maximum. Without either value, Auto uses the Setup maximum of 125 or a higher advertised minimum. |
| `rate` | A userinfo request in bytes/s. The server controls actual bandwidth. | Requests the advertised maximum as soon as active play starts. Without a positive advertised maximum, requests the Setup maximum of 1000000 B/s or a higher advertised minimum. |

Setup → Network shows live connection values while Auto is selected and active. In the console, `st_netStatus` shows `Rate req` in bytes/s, `MaxPPS` as the configured packet target, and `Sent/s` as the measured outgoing command packets per second. A 30 FPS server can have a 30-snapshot request and a different client packet target. Actual packet frequency also depends on client frame rate. Some servers keep fixed rate and snapshot policies private.

Auto yields a setting when another owner changes its value. Repeating its current value preserves ownership. Saving a config during Auto, leaving the server, or switching back to Manual preserves the player's personal settings.

## Measurement and rollback

Auto starts measuring on entry to active play. It compares two consecutive ten-second windows before switching profiles. The next two windows are a trial. A rise of over 3 percentage points in incoming loss, 12 ms in mean arrival variation, 45 ms in mean snapshot ping, or insufficient samples rolls the trial back. A rollback holds the previous profile for at least 60 seconds before reconsideration. Mode changes and map transitions clear measurements. Local in-process matches retain their normal packet timing.

Ping comes from the engine's command acknowledgment estimate. Jitter compares local snapshot arrival intervals with the corresponding server-time intervals. Incoming loss estimates missing **complete sequenced messages**, counting reliable-only messages and reassembled fragments correctly. Reordering can appear as loss. The HUD uses dashes while samples are unavailable. Prediction, command creation and saber resolution use their original code paths.

## Time nudge in beta 1.7

Auto uses 0 ms on stable and distant connections, +4 ms for rate-delayed snapshots, +6 ms for variable arrival times and +8 ms on a lossy link. During sampling or rollback it restricts the personal value to 0 through +8. Consequently, a saved negative value becomes 0 when Auto takes ownership. Setting `cl_timeNudge -10` while already connected in Auto overrides this one setting for that connection. `st_netStatus` shows the live value.

The engine subtracts nudge from its client game clock. A value of -10 advances that clock by 10 ms relative to 0, and outgoing user commands use the client clock as their timestamp. When the latest snapshot has less than 10 ms of headroom, that offset can put the client ahead of the newest server data. Saber contact and damage still depend on server processing.

## Build and validation

The current Full and Lite Windows clients use `tools/Build-Mod-Compatibility.py build`. Both that build and the standalone network test build use `development-source/network/st_network.h` for policy and pacing, `cl_st_network.inc` for runtime tuning and measurements, and `live_settings.py` for the native Setup, cvar and transmit hooks. The standalone fixture is built with `python tests/network/local.py build-fixture` after preparing the standalone engine with `python tools/Build-Adaptive-Network.py build`. Run it with `python tests/network/local.py fixture`.

| Local check | Result |
|---|---|
| Release client on `mp/duel1` | Loaded the updated modules, entered play, displayed diagnostics and retained custom network values through Auto, Manual and Off. |
| Native Setup UI with test input enabled | Cycled all modes, gated manual edits, saved a manual rate and toggled diagnostics. |
| In-process transport fixture with a 30 Hz server and a 90000 B/s budget | Checks the server-received rate, 30-snapshot request, full packet target, loss backoff, recovery, and restoration of saved Manual values. |
| Deterministic policy and pacing tests | Exercised positive and absent rate caps, packet adjustment with no usable ping acknowledgments, stable high ping, jitter, loss, server rate delay, rollback, cooldown, frame rounding and recovery after a stall. |
| Separate dedicated-server IPv4 session | Both programs started. Localhost UDP datagrams did not reach their receiver in this environment, including in an independent two-socket check. The end-to-end test is available in `tests/network/runtime.py`. |

For the US and European beta, compare Auto against the same player's manual configuration on the same server and map. Check both directions of transatlantic play, Wi-Fi jitter, motion corrections and perceived hit consistency. Include one standard Jedi Academy/OpenJK server and reconnect after switching servers. Real-route improvement, stock-server interoperability and live anti-cheat coexistence still need player testing.
