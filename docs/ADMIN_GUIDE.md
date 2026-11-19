# Saber Trials server administration

## Permanent staff accounts

The staff update adds server-local **Owner > Admin > Moderator** appointments.
Use [STAFF_ACCOUNTS.md](STAFF_ACCOUNTS.md) to enroll an Owner, authenticate,
appoint lower roles, revoke access and recover an identity. Use the updated
Overhaul client and matching server/game modules.

Authenticated staff use `freeze`, `unfreeze`, `ghost on|off`, `summon` and
`travel` directly. Role assignments persist until changed or removed; names,
clan tags and Discord roles do not grant authority. Existing server-console
rule commands below remain separate and keep their current names.

## Player vote commands

- `callvote forcemode restricted`
- `callvote forcemode full`
- `callvote gametype duel`
- `callvote gametype ffa`
- `callvote gametype tffa`
- `callvote gametype ctf`
- `callvote kick <player name>`
- `callvote addbot <sabermaster|duelist|sentinel|berserker|trickster|defender|flagcatcher>`

Players and spectators can call and cast these votes. Bots are excluded. Force Mode and Game Type changes wait until the next round boundary; player/bot removal and bot addition execute immediately after passing. The server accepts only roles valid for the current game type. See `BOT_ROLES.md`.

## Administrator console commands

- `st_cmdlist` - list Saber Trials server commands and their usage
- `st_setforcemode restricted|full` - queue a Force Mode change
- `st_gametype duel|ffa|tffa|ctf` - queue a Game Type change
- `st_weapons off` - queue Sabers Only for TFFA and CTF
- `st_weapons on` - queue All Weapons for TFFA and CTF
- `st_master on|off` - queue Master or Standard combat for the next round
- `st_cancelrules` - cancel queued rule changes
- `st_applyrules` - apply queued changes immediately and restart/change the map
- `st_status` - print current and queued rules; in FFA, also print every connected player's FFA K/D and challenge Duel W/L
- `st_ban <player name|client number>` - store the connected human player's exact IPv4 address in the persistent ban list and disconnect them immediately
- `st_addbot <role> [red|blue] [skill 1-5]` - add a random character using a role valid for Duel, FFA, TFFA, or CTF
- `st_kickbot <bot name|client number>` - remove a bot while refusing human targets
- `st_botstatus` - list connected bot roles and teams

Use `status` to find client numbers, `listip` to review stored IP bans, and `removeip <ip>` to unban an address. Quote a player name containing spaces. `st_ban` refuses bots, the local listen-server host, unsupported addresses, and servers configured with `g_filterBan 0` allow-list mode. An IP ban can affect other people sharing the same public address.

## Saber Trials Guard

Saber Trials Guard defaults to monitor-only mode. It watches human players for suspicious command timing, extreme displacement after authoritative server movement, rapid attack-button automation, invalid input values, command flooding, repeated unknown commands, and attempts to use cheat-protected commands. Bots are ignored.

The monitor never changes player input and never warns, moves, kicks, or bans anyone. Scores decay by one point every 30 seconds and must be treated as review evidence rather than proof. Higher-confidence observations and scores at or above five are summarized in `security.log` with `action=none`.

- `st_anticheat monitor` - enable observation-only monitoring
- `st_anticheat off` - stop collecting new observations without deleting existing map data
- `st_acstatus` - show every connected human's score and category counts
- `st_acplayer <player>` - show one player's details and most recent observation

The category letters are `T` timing, `M` movement, `A` attack, `I` input, and `C` command. The data resets with the map. `st_anticheat enforce` is deliberately unavailable in this version.

### Traffic protection development checkpoint

The dedicated engine candidate limits remote challenge and connect traffic in
separate server-wide buckets and rejects truncated connection data. The existing
per-IP connectionless limiter has a fixed cap on tracked addresses. The engine
also throttles excessive reliable commands from connected remote clients while
continuing to process their movement. These controls work independently of the
anti-cheat monitor.

Set `sv_guardJoinRate` for each handshake phase and `sv_guardCommandRate` for each
connected client. Both default to 32 requests per second with one second of burst
capacity. Set a rate to 0 to disable that limit. The engine emits aggregate
`[ST-GUARD]` drop counts at most once every five seconds.

The engine writes its own `guard-traffic.log` in the server's writable game
directory. Use that file with the Python watcher. Set `--min-drops` to the
minimum count to report per window and use the host's log rotation policy.

```sh
tail -n 0 -F /path/to/guard-traffic.log | python3 guard_watch.py --min-drops 10
```

The watcher emits JSON reports for the host to collect. Throttling and packet
rejection happen inside the engine.

## Streamer Mode

Open Setup > Streamer Mode while connected. Turning Streamer Mode on enables its presentation layer; turning it off restores the normal HUD. Clean HUD hides ordinary combat clutter but retains a small centered health-icon, `health/shield` digit, and shield-icon readout for active players. Spectators do not see that readout. The compact overlay keeps player names and scores visible, while the kill feed records recent defeats. Player Labels are spectator-only, require direct line of sight, and do not reveal players through walls. TFFA and CTF can use a Red/Blue score overlay. Match Clock can be Off, Elapsed, or Remaining; Remaining automatically falls back to elapsed time on servers without a time limit. Letterbox adds cinematic bars.

Use Spectator Camera to enter spectator mode, then choose Free Camera or Previous/Next Player. Smooth Follow softens abrupt view turns only while following another player. Camera FOV is adjustable from 60 to 120. Freecam Speed is adjustable from 150 to 800 and is honored only while that user is a free spectator, so it cannot change player movement or server combat.

The settings are saved locally for that player. Recommended broadcast defaults are Streamer Mode On, Clean HUD On, Names / Scores On, Kill Feed On, Player Labels On, Smooth Follow On, Team Overlay On, Match Clock Remaining, Letterbox Off, FOV 90, and Freecam Speed 400.

## TFFA and CTF weapons

TFFA and CTF are Sabers Only by default. `st_weapons on` queues the normal full weapon set for the next round; `st_weapons off` queues Sabers Only again. The choice persists across later rounds and map changes until another command changes it. It does not alter Duel or FFA weapon rules. Use `st_status` to inspect both the active and queued mode, `st_cancelrules` to cancel it, or `st_applyrules` to apply it immediately with a restart.

## Kick-vote protection

The local listen-server host is protected automatically. For dedicated servers, place staff GUIDs in `st_staffGuids`, separated by spaces:

`seta st_staffGuids "GUID_ONE GUID_TWO"`

Keep this value in the loose `server\sabertrials-common.cfg` file on the server rather than publishing real staff GUIDs inside a public package.

## Presets

- `exec server/sabertrials-duel.cfg`
- `exec server/sabertrials-ffa.cfg`
- `exec server/sabertrials-tffa.cfg`
- `exec server/sabertrials-ctf.cfg`

The included maps are temporary stock-map choices for local development and can be changed without rebuilding the mod.

## Duel series

Duel defaults to best-of-three. Round scores survive the automatic restart, the first player to two round wins takes the series, and only then does the loser return to the queue. A draw awards no point.

- `seta st_duelBestOf "3"` - best-of-three (default)
- `seta st_duelBestOf "1"` - stock one-round winner-stays rotation

Odd values up to 9 are supported for server experimentation. Even values are rounded up to the next odd value.

## Tournament

Tournament is a 4–32 player randomized single-elimination bracket built on Duel. Waiting and eliminated entrants are held in spectator mode, while only the active pair can join the arena. One kill ends each round; the same pair returns until the best-of series is decided. Empty seeds automatically become byes. The bracket and match W/L records survive arena changes.

Typical setup:

```text
st_tournament open
st_tournament add 0
st_tournament add 1
st_tournament add 2
st_tournament add 3
st_tournament start
```

Humans may register from Profile > Tournament or with `/tournament join` while registration is open. They may call `callvote tournament start` once four players are registered. Otherwise, registration starts automatically after five minutes when the minimum is met. They can inspect progress using `/tournament status` or `/tournament bracket`. Use `st_tournament status` and `st_tournament bracket` from the server console for the administrator view.

Ordinary matches default to best-of-three and the final to best-of-five. Configure these with `st_tournament format 3|5` and `st_tournament finalformat 3|5`. The default rotation is `mp/duel1 mp/duel2 mp/duel3 mp/duel4`; replace it with `st_tournament arenas <maps...>`.

Use `st_tournament pause|resume` to hold or continue the active match, `st_tournament forfeit <player>` to resolve an abandoned matchup, and `st_tournament reset` to end the bracket and restore the normal Duel queue. An active player has 60 seconds to reconnect before forfeiting automatically; if both active players disappear, the bracket pauses for administrator action.

## FFA scoreboard records

The FFA scoreboard uses two separate per-map records:

- `FFA K/D` counts ordinary FFA kills and deaths. Suicides and environmental deaths count as deaths; switching teams does not.
- `Duel W/L` counts completed, accepted one-on-one challenges. A simultaneous-death draw changes neither record.

A challenge result appears only in Duel W/L, so it is never counted twice in FFA K/D. Use `st_status` in the server console to inspect the same values without opening the client scoreboard.

For local testing, bots accept valid duel challenges immediately. Human-versus-human challenges still require the challenged player to accept normally.

Private challenges are supported in FFA and between opposing teams in TFFA. While a challenge is active, both participants are visually isolated from ordinary players. Duelists and outsiders can pass through one another, preventing hidden players from creating invisible collision barriers. A spectator must cycle to either duelist and follow that player to watch the fight.

The stock challenge-duel shell glow and distance tint are disabled.

## Parry and counter system

Saber Trials uses the player's Walk control (Shift by default) as active guard:

- Face the incoming attack without attacking to retain a limited passive defense.
- Hold Walk for a wider guard angle. Walking speed is the natural tradeoff.
- Press Walk just before impact to perfect parry. The default timing window is 350 ms.
- A perfect parry knocks the attacker off balance and gives the defender 550 ms to press Attack and counter immediately.
- A new perfect-parry attempt cannot begin for 750 ms, preventing button spam. Normal held guard remains available during that time.

Perfect parries use the normal saber-clash feedback without an extra message. Use these settings to tune match feel without rebuilding:

- `seta st_parryWindow "350"` - perfect-parry timing window; clamped from 100 to 450 ms
- `seta st_parryCooldown "750"` - time between attempts; always at least 100 ms longer than the parry window
- `seta st_counterWindow "550"` - immediate counter opportunity; clamped from 250 to 1000 ms

Use `st_status` in the server console to see the active timing and per-map perfect-parry count. These values are the initial playtest baseline, not final balance.

## Master Mode

Master Mode is optional and disabled by default. `st_master on` queues it for the next round, and `st_master off` queues the standard Saber Trials damage model. The selection persists until changed again and applies to every supported game type. A host can also select Master Mode in Create Game > Advanced > Advanced Game Rules before starting a server.

In Master Mode, each committed unblocked saber contact against a player deals a fixed 50 damage and is absorbed by the shared shield system normally. Multiple saber traces in the same damage batch do not stack beyond that configured amount, helping fights last longer. Idle blade contact stays nonlethal. Active guard and perfect parry can intercept body-contact traces, and a perfect parry staggers the attacker for 700 ms while giving the defender the same counter opportunity. Facing, timing, attacking state, broken-parry state, and unblockable attacks still matter.

- `seta st_masterSaberDamage "50"` - fixed committed-contact damage; clamped from 10 to 150
- `seta st_masterParryStagger "700"` - perfect-parry stagger/counter time; clamped from 400 to 1200 ms

These settings take effect without rebuilding. They are intended for beta balancing; `st_status` prints their active values. Standard Mode retains the normal `d_saberSPStyleDamage 1` and `g_saberDamageScale 1` baseline.

## Regenerating shields

Every player and bot starts each life with 100 shields in Duel, FFA, TFFA, and CTF. Taking damage resets a five-second recharge delay, whether the damage was absorbed by shields or reached health. After that delay, shields regenerate at two points per second until they return to 100. Master Mode saber strikes are absorbed by shields normally.

- `seta st_shieldMax "100"` - starting shield and regeneration cap; clamped from 1 to 200
- `seta st_shieldRegenDelay "5000"` - delay after damage before regeneration resumes; clamped from 0 to 30000 ms
- `seta st_shieldRegenAmount "2"` - points restored each second; clamped from 1 to 10

Shield regeneration remains intentionally slow. `st_status` prints the active shield maximum, rate, and delay.

## Damage and falling

Ordinary fall impacts cause no damage in Duel, FFA, TFFA, or CTF. Falling into a lethal map void still kills normally.

- `dmflags` always includes the no-falling-damage bit (`8`)
- `d_saberSPStyleDamage "1"` retains OpenJK's default saber damage model
- `g_saberDamageScale "1"` retains the normal damage scale

Dismemberment changes the death visual only; it does not increase saber damage.

## Force recovery

Force energy regenerates at a 100 ms interval by default, twice as quickly as stock OpenJK/Jedi Academy. Server operators can tune it without rebuilding:

- `seta g_forceRegenTime "100"` - Saber Trials default
- Higher values recover more slowly; lower positive values recover more quickly.

## Dismemberment

Saber dismemberment is enabled in Duel, FFA, TFFA, and CTF. It applies to qualifying saber killing blows and does not increase saber damage or make ordinary hits instantly lethal.

- `seta st_dismemberChance "100"` - percentage chance, from 0 through 100
- `100` is the Saber Trials default; `0` disables server-generated dismemberment

Clients using the Saber Trials client module render the complete visual tier, including head and waist cuts. A specific saber definition can still prohibit dismemberment through its saber data flags.
