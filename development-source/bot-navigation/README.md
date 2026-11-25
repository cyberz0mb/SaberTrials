# Berserker pursuit and recovery

This server gameplay overlay replaces the Berserker's unconditional forward
command with enemy pursuit and local movement recovery. Other personalities
keep their existing movement rules.

- Periodically select a live opposing player, prefer visible threats and retain
  a useful target instead of switching back and forth. Teammates, spectators,
  disconnected/dead clients and unrelated private duels are excluded.
- Route toward the target's reachable waypoint when the target is out of sight.
  Preserve the stock map's doors, elevators and authored Force jumps.
- Use a direct shortcut only after a standing player hull can reach the target's
  floor. Check clearance, support, slope, lava/slime and hurt triggers, including
  the descent. Allow a drop of at most 512 units with falling damage disabled,
  or 96 units with falling damage enabled. Reject drops onto moving platforms.
- After 1.8 seconds without displacement, commit to a safe side detour or a
  checked short obstacle hop, and choose another nearby waypoint. Temporarily
  avoid reacquiring the failed waypoint. Do not count riding a moving lift or
  nearby combat footwork as a navigation failure.
- Disable the stock low-health flee/chase alternation for Berserkers. Preserve
  their ordinary close-range saber footwork and the other roles' behavior.

`st_botnav` in a local/server console prints each Berserker's current navigation
mode, target, waypoint and recovery counters. It does not alter the match.

Build with `python tools/Build-Bot-Navigation.py prepare`, then `build`, then
`install`. Preparation verifies the combined emote-wheel gameplay source and
installed module before layering the change. Only `jampgamex86_64.dll` is
installed, transactionally, with the previous module backed up. Personal cfgs,
client modules, renderers and assets are preserved. `refresh` recopies the two
authored include files after a compiler-driven correction without replacing the
rest of the prepared source.

The user requested to perform gameplay testing personally. Compilation and file
verification are recorded separately from gameplay acceptance; the build and
install tool never launches the game. Maps still need usable waypoint routes
for paths which cannot be reached by a checked local shortcut.
