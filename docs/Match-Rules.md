# Host Match and Match Rules

Open **Host Match > Match Rules** before hosting, or **Pause > About > Match
tools > Match Rules (host)** while running your own local match. Review the draft before
starting or applying it. Apply now restarts only when needed; Apply next
round/map leaves the current match running. Cancel edits discards the local
draft; Discard queue separately cancels rules already queued on the server.

Match Rules extends the native Host Match advanced screen with Combat,
Force & Weapons, Health & Movement, Teams & Bots, Match, and Server pages.
The screen uses the existing Saber Trials frame, controls and traveling lights.
Opening it starts an isolated draft. Changing fields does not change an active
match until the host applies the draft.

Blocking offers Automatic (legacy automatic/Walk defense), Manual, and Both.
Attack-timed parry, timing, enhanced defense, feints and Master Mode remain
separate controls. Descriptions explain saved options that are currently
inactive. Feints retain the currently supported ordinary single-saber styles;
this menu does not introduce different combat choreography.

Force supports Full, Restricted (Jump, Speed, Saber Attack and Saber Defense),
and Custom. Each Custom power can be disabled or capped at levels 1-3. These are
maximum levels, not free grants; the existing free-Speed option is separate and
obeys Custom caps. Custom weapons use an explicit disable mask; melee and saber
remain available. Custom weapon restrictions apply in FFA as well as team modes.

Starting health 0 and starting shields -1 keep existing mode/combat defaults.
Custom health/shields do not override Siege class rules. Regenerating shields
retain their established maximum 1-200 and recharge amount 1-10. The minimum
respawn delay is independent of automatic respawn and does not override Duel,
Power Duel or Siege respawn rules.

Connection capacity includes humans, bots and spectators and is separate from
the optional per-team cap. Keep at least one connection beyond the bot roster.
That connection can be occupied by the listen host or another human. Choose
additional connection slots if you want spare room after the host has joined.
Bots have independent character definitions, roles and skill. Choices are
validated for the current game type; Power Duel uses its existing automatic
classic bot behavior. A roster replacement removes bots only, never humans.

Map rotation is ordered and limited to 32 installed maps. Entries must be valid
map identifiers and refer to available BSP files. The new server commands are
server-console/operator actions; joining a remote server does not confer host
rights or permit an ordinary client to change its rules.

Presets are structured `.stmatch.fcf` data stored under `match-presets`. The
final suffix lets the native filesystem read them on pure servers; the contents
remain strictly parsed data. They include
numeric rules, Force caps, custom weapon restrictions, selected map, rotation,
server name and bot roster. Passwords are deliberately excluded. Loading does
not execute a configuration or arbitrary command text. Invalid, incomplete or
mode-incompatible presets fail without replacing the current draft.
Preset names use letters, digits, underscores and hyphens, up to 40 characters.
Deleting a preset writes a zero-byte tombstone because the native UI filesystem
does not expose file removal. The browser hides it; the name can be reused.
Saving during a match snapshots the live bot roster separately from pending
additions, so saving does not replace or respawn bots.

Changed menu copies are also included in a matching PK3 for pure-server access.
Pure hosting also requires the selected maps, characters and other required
content to be packaged in compatible PK3s; a loose-only asset is insufficient.
The existing VFS availability check does not certify a remote pure handshake.

The source overlay is in `development-source/match-rules/`.
