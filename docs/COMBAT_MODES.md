# Combat modes

Main integration: [Block, Parry and Feint](Combat-Controls-Main.md)
provides server modes `g_manualBlocking 0` (Classic), `1` (Combined) and `2`
(Manual only). Combined retains automatic defense. Manual-only requires the
guard input even with Original JKA/active defense off; physical blade clashes
remain. These latched settings require a map restart. Classic retains Walk
guard. The main build defaults to [Attack-timed parries](Combat-Controls-Main.md):
tap Attack near incoming melee contact, with or without Block. This works
outside Master in all three modes; Manual-only does not otherwise regain auto-block.
The legacy guard-press timing documented below applies when `st_attackParry 0`
or to existing bot/NPC input.

The server chooses **Saber Trials Combat** or **Original JKA**. Both client and
server gameplay modules must be updated together. Restart the game/server after
installing the pair. Existing Saber Trials combat settings remain the default.

## Administrator controls

Enter these in the host/server console. A remote administrator prefixes each
command with `rcon` after setting their RCON password.

```text
st_combat original
st_applyrules
st_status
```

`st_combat original` queues Original JKA for the normal round-end rule-change
boundary. `st_applyrules` applies queued rules now and restarts the map; players
respawn. Use `st_combat trials` to return to Saber Trials Combat.
`st_cancelrules` cancels pending admin commands, including combat options.
`st_status` shows the active preset, effective options, saved preferences and queue.

Individual preferences apply only in Saber Trials Combat:

| Command | Enabled behavior |
|---|---|
| `st_combatoption defense on` | Active guard, Attack-timed parries and counters; Combined blocking is the default |
| `st_combatoption recovery on` | Faster ordinary parry recovery, synchronized with the client |
| `st_combatoption shields on` | Configured spawn shields and regeneration after avoiding damage |
| `st_combatoption nofall on` | No falling damage |
| `st_combatoption speed on` | Free level-three Force Speed at spawn |
| `st_combatoption forceregen on` | Configured Force regeneration interval, normally 100 ms |
| `st_combatoption master on` | Fixed Master saber contact damage and stronger perfect-parry stagger |

Use `off` instead of `on` to disable an option. These commands also queue for the
round boundary. Master retains the existing `st_master on/off` alias and is off
by default; the other six preferences default to on.

Original JKA ignores all seven preferences without erasing them. It uses the
pinned OpenJK stock saber-defense values and recovery times, stock spawn armor
(25% of maximum health in FFA/TFFA, zero in Duel/Power Duel, class armor in Siege),
no armor regeneration, normal falling damage, the player's chosen Force Speed
allocation, and a 200 ms Force regeneration interval. Returning to Saber Trials
reactivates the saved preferences.

This is a combat preset on the existing OpenJK foundation. Force/weapon
restrictions, Duel series, tournaments, bot roles, private-duel isolation,
statistics, dismemberment visuals, recording and Streamer Mode remain separately
configured. It does not turn the entire mod into an unmodified retail executable.

## Server configuration

| Setting | Default | Purpose |
|---|---|---|
| `st_combatMode` | `1` | `0` Original JKA; `1` Saber Trials Combat |
| `st_activeDefense` | `1` | Active guard/parry preference |
| `st_parryRecovery` | `1` | Faster recovery preference |
| `st_shields` | `1` | Spawn shield/regeneration preference |
| `st_noFallDamage` | `1` | No falling damage preference |
| `st_forceSpeed` | `1` | Free Force Speed preference |
| `st_fastForceRegen` | `1` | Faster Force regeneration preference |
| `st_forceRegenInterval` | `100` | Interval in ms, clamped to 50–1000 when enabled |
| `st_masterModeActive` | `0` | Existing Master preference; use the queued admin command |

The eight new settings are archived and latched: direct `set`/`seta` edits take
effect on map restart. Direct latched edits are engine settings and are not
removed by `st_cancelrules`; set the old value again to cancel those. Prefer the
admin commands for a visible, cancellable queue. Persist dedicated-server choices
in the server's startup configuration; `writeconfig` can save a chosen profile.

The preset manages the `DF_NO_FALLING` bit of `dmflags`, preserving all unrelated
bits, and selects `g_forceRegenTime` at restart. Use `st_forceRegenInterval` for
custom Saber Trials regeneration instead of setting `g_forceRegenTime` in a
shared startup config. Existing `st_shield*`, parry and Master tuning still apply
when their corresponding feature is enabled.

## Player check

### Historical private manual-block candidate (November 19)

The following records the private acceptance build. For the November 20 main
installation, native Controls entries and compact settings synchronization, use
[the current combat controls guide](Combat-Controls-Main.md).

The separate candidate08 test launcher now includes a held upper-body defensive
pose for single sabers, duals and staff. Block can remain held while moving or
aiming; releasing it restores the ready stance. Hit reactions, attacks and
recovery retain priority. Stances offers Guard and Guard + walk previews.
This is part of the private manual-block/feint candidate, not the older production
package described below. See [manual-block testing](Combat-Controls-Main.md).

The animation follows `g_manualBlocking`: inactive in Classic, active with Trials
active defense in Combined, and available independently of that preference in
Manual only. The server publishes `st_activeDefense` so client prediction agrees.
Matching animation assets are required when manual blocking is enabled, including
servers with hybrid attacks disabled. Damage and existing parry windows are unchanged.

Connected testing on November 19 corrected prediction's guard eligibility to
use the replicated Saber Defense known-power bit; numeric defense levels are
server-only. The matching Feint adapter uses stable simulation time instead of
the command timestamp reused by stock saber randomness. See the local-test
documents for reproduction and regression evidence. The same launcher is reused.

### Combat preset check

1. Start a local match and run `st_status` in the console.
2. Queue Original JKA, verify the current mode stays active, then run
   `st_applyrules`. Confirm the status changes after the restart.
3. In FFA, confirm normal spawn armor and no shield regeneration; falling damage
   returns. Walk still works as the normal movement input.
4. Queue Trials and apply it. Confirm the selected combat additions return.
5. Turn off one option, apply, and switch between both presets. Confirm the
   individual choice is remembered. Confirm recording and Streamer Mode still work.

## Installed update and rollback

The local production pair is installed in the mod folder. The incremental
`dist/SaberTrials-combat-20261006.zip` contains both modules, shared server config,
buildable source overlays and documentation; it requires the existing mod and
OpenJK installation. It contains no base-game or character assets.

For rollback, close the game and server, then restore **both** DLLs from
`dist/backups/combat-20261006` to the mod folder. Restore the pair together so
server combat and client prediction agree. The existing launcher, engine and UI
remain compatible with either pair.
