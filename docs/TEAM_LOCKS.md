# TFFA team locks

In TFFA, open **Call Vote > General > Lock Teams** or **Unlock Teams**.
Console equivalents are `callvote lockteams on` and `callvote lockteams off`.
The normal server-wide vote rules apply, including spectator votes, cooldowns,
per-map call limits, and exclusion of bots from voting.

A passed vote takes effect immediately. All enabled teams keep their current players,
who can continue fighting and respawning. New connections and spectators may
watch but cannot join a team. Players cannot switch teams. Leaving for spectator
is allowed, but rejoining requires an unlock; reconnecting does not reserve a
place or bypass the lock. New bot additions are blocked while locked as well.

Admins can use `st_lockteams on` or `st_lockteams off` in the server console or
through RCON. `st_status` reports the current lock state and `st_cmdlist` lists
the command. Unlock before using `forceteam` to move or admit a player.

Locks reset on map changes and map restarts. They apply only to TFFA, not FFA,
Duel, Tournament, or CTF. The feature locks all enabled teams together; it does not
create a password or prevent spectators from connecting to the server.

The vote is appended at allow-vote index 13 (bit 8192), preserving existing
indices. The shipped `g_allowVote` mask is now 16383 (including menu limit/map
votes; the original team-lock release used 15410). Known older ST default
masks migrate automatically; custom masks and disabled voting remain intact.
For a custom mask, use `toggleallowvote` to inspect the list, then
`toggleallowvote 13` if the team-lock vote is disabled.

## Verification

Verified on 2026-09-04 with the compiled Windows x64 game module and isolated
OpenJK profiles: a player-called lock vote passed and locked entry; team
switching, bot creation, and add-bot votes were blocked; an existing player
respawned, moved to spectator, successfully voted to unlock, and rejoined.
A second client connected with team auto-join enabled and remained spectator;
its explicit blue-team join was rejected. Map restart cleared the lock. The
FFA vote and admin command were rejected, and invalid vote arguments were
rejected. The menu file parsed during startup; final visual placement remains
part of in-game user testing.
