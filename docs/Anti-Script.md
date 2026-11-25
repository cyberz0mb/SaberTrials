# Anti-script detection and enforcement

Development candidate. Use Monitor for multiplayer validation. The new engine setting is independent of the existing Guard monitor, its suspicion scores, and server combat-balance settings.

| Server CFG or console command | What players experience |
| --- | --- |
| `set sv_stAntiScript 0` (default) | No anti-script collection, penalties or account admission checks. |
| `set sv_stAntiScript 1` | Observe and record. Guests can play. Existing bans are inactive in this mode. |
| `set sv_stAntiScript 2` | A verified account and access to the server's strike database are required for gameplay. Active bans deny admission. Only corroborated evidence can advance a strike. |

**Account setup.** Enroll the server using the existing [account bridge](Account-Server-Bridge.md). The native connection must exchange a challenge before the server knows the player's identity. A joining player can establish that connection while the server holds game entry. Verification has a 90-second timeout. A failed verification or unavailable database carries no strike. Each server keeps its own history.

## Detection

The updated client follows commands that actually execute through OpenJK's command buffer, including nested `exec`, `execq`, `vstr` and commands expanded from a binding. No additional files are opened by the detector. The client sends an action signature, command time and execution identifier. CFG contents, chat, key names, account tokens and cvar values are excluded from the report.

Graphics, HUD, sensitivity, style settings, chat binds and ordinary press/release binds are allowed. A client report requires a balanced sequence of observed actions with an executed wait between its steps in the same invocation. Repeated action evidence uses primary attack, alternate attack and six movement directions. Simultaneous chords, rapid single-button attacks, unusual movement speed, camera flicks, pokes and other manual techniques cannot produce a strike on their own.

The server compares accepted player commands against three repetitions of a timed pattern spanning multiple server frames. It compares a matching client report from the same connection and requires at least two distinct actions. It ignores bots, spectators, dead players, vehicle occupants, chat input and significant command discontinuities. Single-source evidence is throttled and recorded for review. The account ledger deduplicates by account and by execution within the server-issued connection generation. A ten-minute account cooldown follows corroborated activity and survives restarts and reconnects.

**Limits.** Modified clients can withhold or falsify their own reports. Stock clients lack this telemetry. External input devices and macros can produce indistinguishable inputs. A network hitch, packet loss, low frame rate, an unrecognized command, or overlapping physical inputs can prevent corroboration. Server behavior alone never issues a strike. The detector is deliberately selective. Human playtests must establish a false-positive rate.

## Penalties

| Strike | In-game notification and action |
| --- | --- |
| 1 | Private center-screen warning. “Warning: Anti-cheating is active. You have been warned.” |
| 2 | Public center-screen warning. “[Player] has been detected cheating.” |
| 3 | Public center-screen notice and kick. “[Player] has been kicked for cheating.” |
| 4 | Public center-screen notice and 30-day ban. “[Player] has been temp-banned for cheating.” |
| 5 | Public center-screen notice and permanent ban. “[Player] has been perma-banned for cheating.” |

Ban expiration restores admission with four strikes. The next independently confirmed incident produces strike five. The server commits the incident and penalty to SQLite before issuing any notification or kick.

## Operator commands

Use the server console or authenticated RCON.

| Command | Effect |
| --- | --- |
| `st_as players` | Lists connected humans and available verified account IDs. |
| `st_as evidence <account-id>` | Shows strikes, ban status and the latest 25 evidence records. |
| `st_as evidence guest` | Shows anonymous Monitor observations. |
| `st_as evidence <id-or-guest> <before-event-id>` | Reads the next page of older records. |
| `st_as clear <account-id>` | Resets strikes. An existing ban still applies. |
| `st_as revoke <account-id>` | Revokes the ban. Existing strikes still apply. |

The evidence log includes UTC epoch seconds, the violation type, comparable timing data, penalty, strike count and ban expiry. An expiry of -1 denotes a permanent ban. Clear and revoke operations retain the audit trail. Back up the private per-port `anti-script.sqlite` beside the existing server account credential when migrating a server. Never package the database with the client.

## Build and validate

The change requires an updated multiplayer client engine and dedicated/listen server engine. It uses the existing game DLL, center-print HUD and network user-command layout. Existing clients can join in Monitor. Enforce requires a client capable of completing the account bridge.

On the Windows development checkout with the Vulkan engine source and pinned staff dependencies staged:

```powershell
python tools/Build-Anti-Script.py all
cmake -S tests/anti-script -B dist/anti-script/tests -A x64 -DOPENJK_SOURCE="$PWD/dist/anti-script/engine"
cmake --build dist/anti-script/tests --config Release --parallel 1
ctest --test-dir dist/anti-script/tests -C Release --output-on-failure
```

The Windows builder stages candidates under `dist/anti-script/build/Release`. The Linux source/archive builder also stages the hooks and tests. Public rollout requires head-to-head testing with signed-in players, real detection and all five notices, account loss, map restart, expiry/rejoin, accessibility inputs, manual advanced play and representative latency. The automated server adapter uses substitute engine callbacks. It does not measure false positives in real matches or render HUD messages.

### Verification recorded November 18, 2026

Five native anti-script suites passed on Linux with undefined-behavior checks enabled. The command-buffer suite used the pinned OpenJK parser and script expansion functions with in-memory test CFGs. The server lifecycle suite used the real anti-script adapter and SQLite ledger with substitute engine calls. The updated account server adapter, 47 account backend tests and seven Guard tests also passed. Twelve native object files compiled, including client input, server client processing and client/dedicated variants of the command buffer. No complete Windows executable, hosted multiplayer result, rendered HUD check, or measured human false-positive rate was verified in this run.

### Windows verification on November 19, 2026

Both x64 Release engines built successfully. The dedicated server loaded `mp/duel1`, reported the default value of `0`, and switched to Monitor through its console. A local player joined a Windows listen server in Monitor. With a controlled movement fixture and fixed engine frame time, SQLite recorded the client script report and the server's repeated-input observation. The guest received zero strikes. A separate ordinary-timing run recorded only the client report. All five anti-script suites, 47 account service tests and seven Guard tests passed on Windows.

Before enabling Enforce on a hosted server, verify account admission, the five HUD notifications and reconnect behavior with test accounts, then review Monitor evidence from human matches under typical latency.
