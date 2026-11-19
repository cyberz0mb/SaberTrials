# Saber Trials administrator command list

For permanent Owner/Admin/Moderator accounts and the plain-name `freeze`,
`unfreeze`, `ghost`, `summon` and `travel` commands, see
[STAFF_ACCOUNTS.md](STAFF_ACCOUNTS.md). Those commands require authenticated
staff access; the operator-console commands below retain their existing paths.

Commands can be entered directly in the host/dedicated-server console. A remote administrator can enter `/rconPassword <password>` once, followed by `/rcon <command>`. For example: `/rcon st_status`. Keep that password private.

## Saber Trials rule commands

| Command | Effect |
|---|---|
| `st_status` | Show the active and queued rules, TFFA/CTF weapon mode, shield settings/current values, fall and saber-damage settings, parry timing, Duel series length, dismemberment chance, and FFA player records. |
| `st_combat original` | Queue Original JKA combat; saved Saber Trials preferences are retained but inactive. |
| `st_combat trials` | Queue Saber Trials Combat using saved feature preferences. |
| `st_combatoption <option> <on\|off>` | Queue `defense`, `recovery`, `shields`, `nofall`, `speed`, `forceregen`, or `master`. |
| `st_setforcemode restricted` | Queue Restricted Force for the next round boundary. |
| `st_setforcemode full` | Queue Full Force for the next round boundary. |
| `st_gametype duel` | Queue Duel for the next round boundary. |
| `st_gametype ffa` | Queue FFA for the next round boundary. |
| `st_gametype tffa` | Queue TFFA for the next round boundary. |
| `st_lockteams on` | Immediately lock both TFFA teams to their current players. |
| `st_lockteams off` | Immediately reopen TFFA team entry and switching. |
| `st_gametype ctf` | Queue CTF for the next round boundary. |
| `st_weapons off` | Queue Sabers Only for TFFA and CTF at the next round boundary. |
| `st_weapons on` | Queue All Weapons for TFFA and CTF at the next round boundary. |
| `st_master on` | Queue the Master preference: fixed 50-point unblocked saber contact and stronger timed defense, effective only in Saber Trials Combat. |
| `st_master off` | Queue the standard Saber Trials combat model for the next round. |
| `st_applyrules` | Apply all queued rule changes immediately. This restarts or changes the map. |
| `st_cancelrules` | Cancel queued combat preset/options, Force Mode, Game Type, weapon, and Master Mode commands. Direct latched cvar edits are separate. |

`st_queue_forcemode` is an alias for `st_setforcemode`. `st_queue_gametype` is an alias for `st_gametype`.

See [Combat modes](COMBAT_MODES.md) for server settings, independent options,
paired client/server requirements and a short in-game check.

## Monitor-only anti-cheat commands

| Command | Effect |
|---|---|
| `st_anticheat monitor` | Enable Saber Trials Guard observation. It records evidence but takes no action. |
| `st_anticheat off` | Stop new observations; existing per-map observations remain inspectable. |
| `st_acstatus` | List connected humans with decaying score and timing/movement/attack/input/command counts. |
| `st_acplayer <player>` | Show one player's detailed monitor summary and latest observation. |

Observations are written to `security.log` with `action=none`. They are not proof and must not be used as an automatic permanent-ban decision.

## Bot role commands

| Command | Effect |
|---|---|
| `st_addbot duelist [team] [skill]` | Add a random Duelist character in FFA/TFFA. |
| `st_addbot sentinel [team] [skill]` | Add a random Sentinel character in FFA/TFFA. |
| `st_addbot berserker [team] [skill]` | Add a random Berserker character in FFA/TFFA. |
| `st_addbot trickster [skill]` | Add a random Trickster character in FFA only. |
| `st_addbot defender [team] [skill]` | Add a Defender that protects its own territory in CTF. |
| `st_addbot flagcatcher [team] [skill]` | Add a Flag Catcher that captures and scores in CTF. |
| `st_addbot sabermaster [skill]` | Add the elite Saber Master in Duel; unavailable during Tournament. |
| `st_kickbot <bot>` | Remove a bot by name or client number; human targets are refused. |
| `st_botstatus` | List every connected bot's client number, role, and team. |

Use Call Vote > Bots for player-facing additions. Call Vote > Kick handles both players and bots safely. See `BOT_ROLES.md` for the behavior and tuning details. Duel uses only Saber Master; Tournament intentionally keeps classic bots.

Use `st_cmdlist` in the server console or through RCON for the complete Saber Trials command list. Use `cvarlist st_*` separately to list all Saber Trials settings and their current values. OpenJK's ordinary `cmdlist st_*` cannot see game-module server commands.

## Tournament commands

Tournament is a 4–32 player single-elimination competition layered on Duel. Only the current pair enters the arena; waiting and eliminated players remain spectators. One kill ends a round and the same pair returns until its series is decided. Seeds are randomized, empty seeds become byes, arenas rotate after each matchup, ordinary matches are best-of-three, and the final is best-of-five.

| Command | Effect |
|---|---|
| `st_tournament open` | Reset the previous bracket and open registration. If necessary, switch to Duel and load the first configured arena. |
| `st_tournament add <player>` | Register a connected player or bot by name/client number. |
| `st_tournament remove <player>` | Remove an entrant while registration is open. |
| `st_tournament start` | Randomize seeds and begin once 4–32 connected entrants are registered. |
| `st_tournament status` | Show phase, format, arena, active pair, and every entrant's match W/L. |
| `st_tournament bracket` | Show the current round and its completed/current/upcoming matchups. |
| `st_tournament format <3\|5>` | Set the match series length. Default: 3. |
| `st_tournament finalformat <3\|5>` | Set the final series length. Default: 5. |
| `st_tournament arenas <maps...>` | Set the ordered arena rotation. |
| `st_tournament pause` | Pause the competition and return everyone to spectator. |
| `st_tournament resume` | Resume once both active competitors are connected. |
| `st_tournament forfeit <player>` | Eliminate one of the two active competitors and advance the opponent. |
| `st_tournament reset` | End Tournament and restore the normal Duel queue. |

Players use Profile > Tournament or `/tournament join`, `/tournament leave`, `/tournament status`, and `/tournament bracket`. They can use `callvote tournament open` to select Tournament and `callvote tournament start` to begin early. Otherwise it auto-starts after five minutes once four players are registered. A disconnected active competitor has 60 seconds to return before forfeiting; if both disappear, Tournament pauses for an administrator.

## Included game-mode presets

These commands load the mode immediately using its current stock development map:

| Command | Mode and map |
|---|---|
| `exec server/sabertrials-duel.cfg` | Duel on `mp/duel1` |
| `exec server/sabertrials-ffa.cfg` | FFA on `mp/ffa3` |
| `exec server/sabertrials-tffa.cfg` | TFFA on `mp/ffa3` |
| `exec server/sabertrials-ctf.cfg` | CTF on `mp/ctf1` |

## Live gameplay settings

| Command | Saber Trials default | Valid/useful range |
|---|---:|---|
| `seta st_duelBestOf "3"` | 3 | Odd values 1–9; even values round up. |
| `seta st_tournamentBestOf "3"` | 3 | Tournament matches: 3 or 5. |
| `seta st_tournamentFinalBestOf "5"` | 5 | Tournament final: 3 or 5. |
| `seta st_tournamentArenas "mp/duel1 mp/duel2 mp/duel3 mp/duel4"` | Four arenas | Space-separated Duel map rotation. |
| `seta st_tournamentAutoStart "300"` | 300 sec | Registration wait before automatic start; clamped to 30–3600 seconds. |
| `seta st_parryWindow "350"` | 350 ms | 100–450 ms. Higher is easier. |
| `seta st_parryCooldown "750"` | 750 ms | Up to 1500 ms; always at least 100 ms longer than the parry window. |
| `seta st_counterWindow "550"` | 550 ms | 250–1000 ms. Higher gives more time to counter. |
| `seta g_forceRegenTime "100"` | 100 ms | Lower regenerates Force faster; stock OpenJK is 200 ms. |
| `seta st_dismemberChance "100"` | 100% | 0–100. Zero disables server-generated dismemberment. |
| `seta st_masterSaberDamage "50"` | 50 | 10–150 fixed damage for a committed, unblocked saber contact in Master Mode. |
| `seta st_masterParryStagger "700"` | 700 ms | 400–1200 ms attacker stagger and matching counter opportunity after a perfect parry in Master Mode. |
| `seta st_shieldMax "100"` | 100 | 1–200 starting shield and regeneration cap in every game type. |
| `seta st_shieldRegenDelay "5000"` | 5000 ms | 0–30000 ms without damage before shield regeneration begins. |
| `seta st_shieldRegenAmount "2"` | 2/sec | 1–10 shield points restored per second. |
| `seta st_anticheatMode "1"` | 1 | 1 enables monitor-only mode; 0 disables new observations. |
| `seta st_acLogThreshold "5"` | 5 | Suspicion score at which throttled summaries begin entering `security.log`; 1–100. |
| `seta st_acCommandLimit "30"` | 30/sec | Client-command burst threshold; clamped to 10–100. |
| `seta st_acAttackLimit "14"` | 14/sec | Primary-attack press threshold; clamped to 8–30. |
| `seta st_acScoreDecay "30"` | 30 sec | Seconds per one-point score decay; clamped to 5–300. |
| `seta st_botSkill "4"` | 4 | Default skill used by role-vote/admin bot additions; 1–5. |
| `seta st_botDuelCooldown "6000"` | 6000 ms | Duelist delay before choosing another challenge target. |
| `seta st_botSentinelReaction "90"` | 90 ms | Fair reaction delay before guarding a visible nearby saber attack. |
| `seta st_botTricksterChat "12000"` | 12000 ms | Minimum interval between preset Trickster chat lines. |

Changes to these values take effect without rebuilding the mod. Use `st_status` to confirm the active values.

## Streamer Mode settings

These are client settings and are normally changed through Setup > Streamer Mode. They do not alter combat or the server's rules.

| Command | Default | Effect |
|---|---:|---|
| `seta st_streamerMode "1"` | 0 | Enable Streamer Mode; use 0 to restore the normal presentation. |
| `seta st_streamerCleanHud "1"` | 1 | Hide the standard combat HUD while Streamer Mode is active. |
| `seta st_streamerOverlay "1"` | 1 | Show the compact player-name and score overlay. |
| `seta st_streamerKillFeed "1"` | 1 | Show recent defeats with attacker, attack type, and target. |
| `seta st_streamerPlayerNames "1"` | 1 | Show line-of-sight name labels while spectating. |
| `seta st_streamerCameraSmooth "1"` | 1 | Smooth fast camera turns while following a player. |
| `seta st_streamerTeamOverlay "1"` | 1 | Group Red and Blue scores in TFFA and CTF. |
| `seta st_streamerMatchClock "2"` | 2 | Match clock: 0 off, 1 elapsed, 2 remaining when a time limit exists. |
| `seta st_streamerLetterbox "1"` | 0 | Add cinematic top and bottom bars. |
| `seta st_streamerFov "90"` | 90 | Set spectator camera FOV from 60 to 120. |
| `seta st_streamerCameraSpeed "400"` | 400 | Set free-spectator movement speed from 150 to 800. |

## Voting and staff protection

| Command | Effect |
|---|---|
| `seta st_voteCooldown "60"` | Set seconds between vote calls. |
| `seta st_voteMaxCalls "3"` | Set how many votes each person may initiate per map. |
| `seta st_staffGuids "GUID_ONE GUID_TWO"` | Protect listed administrators/moderators from kick votes. |
| `seta g_allowVote "16383"` | Enable all supported menu votes, including limits, maps, warmup, Force Mode, Game Type, Tournament, Kick, Add Bot, and TFFA team locking. |

Do not publish real staff GUIDs or the RCON password in a public beta package.

## Player vote commands

Administrators may give these to players and spectators:

- `callvote forcemode restricted`
- `callvote forcemode full`
- `callvote gametype duel`
- `callvote gametype ffa`
- `callvote gametype tffa`
- `callvote gametype ctf`
- `callvote kick <player name>`
- `callvote addbot <sabermaster|duelist|sentinel|berserker|trickster|defender|flagcatcher>`
- `vote yes`
- `vote no`

Force Mode and Game Type votes queue a next-round change. A successful kick vote acts immediately.

## Essential OpenJK server commands

| Command | Effect |
|---|---|
| `status` | List connected players and their client numbers. |
| `st_ban <player name\|client number>` | Permanently ban a connected human player's exact IPv4 address and disconnect them immediately. |
| `listip` | List the server's stored IP bans. |
| `removeip <ip>` | Remove an exact address from the IP-ban list. |
| `kick <player name>` | Remove a player by name. |
| `clientkick <client number>` | Remove a player using the number shown by `status`. |
| `forceteam <player> <team>` | Move a player; common team values are `red`, `blue`, `free`, and `spectator`. |
| `say <message>` | Broadcast a server message. |
| `map <map name>` | Load a map with cheats disabled. Example: `map mp/ffa3`. |
| `map_restart 0` | Restart the current map immediately. |
| `addbot <name> [skill 1-5] [team] [delay ms] [alternate name]` | Add a bot. Example: `addbot Luke 4 free`. |
| `botlist` | List available bots. |
| `serverinfo` | Print settings visible in the server browser. |
| `dumpuser <client number>` | Print a connected player's user information. |
| `exec <cfg path>` | Execute a server configuration file. |

`st_ban` is available only from the server console or through RCON. Use a quoted name if it contains spaces, such as `st_ban "Player Name"`. The ban remains after a restart until `removeip` is used. Because several people can share one public address, an IP ban may also prevent other players on the same home or school network from joining.

## Protected defaults

- Ordinary fall-impact damage is always disabled. Lethal map voids still kill.
- TFFA and CTF start in Sabers Only mode. Guns, explosives, mines, melee weapons, and map weapon pickups are disabled until `st_weapons on` takes effect.
- The selected TFFA/CTF weapon mode persists until another `st_weapons` command changes it. Duel and FFA weapon rules are unchanged.
- `d_saberSPStyleDamage "1"` keeps OpenJK's standard saber-damage model.
- `g_saberDamageScale "1"` keeps the normal damage scale.
- Dismemberment changes death visuals, not damage.
- Every player starts with 100 shields. After five seconds without damage, shields regenerate at two points per second up to 100.
- Force Speed is enabled at maximum level 3 for every player and bot by default.
- Master Mode is disabled by default. When enabled, committed unblocked saber contacts deal the configured fixed damage and interact normally with shields; idle blade contact remains nonlethal.

## Quick examples

Queue Full Force and TFFA, inspect the queue, then apply both now:

```text
st_setforcemode full
st_gametype tffa
st_weapons off
st_master on
st_status
st_applyrules
```

Return to the Saber Trials beta combat baseline:

```text
seta st_parryWindow "350"
seta st_parryCooldown "750"
seta st_counterWindow "550"
seta g_forceRegenTime "100"
seta st_duelBestOf "3"
seta st_dismemberChance "100"
seta g_allowVote "16383"
st_status
```

Ban client 3, review the stored list, and later remove the example address:

```text
status
st_ban 3
listip
removeip 203.0.113.25
```
