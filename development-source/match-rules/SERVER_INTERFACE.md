# Match Rules game adapter

`server.apply(root)` overlays a disposable game source clone. The baseline is
`dist/profile-uniform-fix/game`. `server.apply_frontend(root)` adds the prediction
cap hook to a disposable frontend clone based on `dist/black-sabers-01/frontend`.
Only the new `g_st_match_rules.cpp` uses C++; the existing game units remain C.

All commands below are server-console commands. They have no ClientCommand
dispatch or client privilege path.

- `st_match_set <catalog-cvar> <integer>` stages a validated numeric field.
  `ui_dedicated` is start-only and is rejected by the game adapter.
- `st_match_force <0..17> <0..3>` stages a Force cap.
- `st_match_weapons <disable-mask>` stages the 19-bit custom mask; melee and
  lightsaber bits cannot be disabled.
- `st_match_text <rotation|map|hostname|password> "value"` stages validated text.
  Rotations use ordered space-separated map slugs, at most 32 maps and
  `stmatch::RotationLimit` characters. Apply checks installed BSPs.
- `st_match_addbot "bot-definition-name" <skill 1..5> <team> <role 0..7> [slot]`
  stages a real loaded bot definition. Team 0 is automatic/free; team games use
  1/2 and active TFFA teams 4..9. Role IDs use the shared header's roleTokens.
- `st_match_clearbots` stages an explicit rebuild that removes bots only.
- `st_match_rosterreset` discards only staged roster edits and the rebuild flag.
- `st_match_apply now` commits and restarts only if a field requires it.
  Existing independent rule/combat queues retain their normal authority.
- `st_match_apply later` arms the complete draft for the existing normal rule,
  round or map boundary. Further edits disarm it until applied again.
- `st_match_apply roster` commits only roster actions without a restart.
- `st_match_cancel` discards only this adapter's unapplied edits.
- `st_match_nextmap` selects the next validated installed BSP from the rotation.

Pre-host setup sets validated catalog cvars directly, sets `st_matchManaged=1`,
and uses `st_matchForceCap0..17`, `st_matchWeaponDisable`, and `st_matchRotation`.
The global managed flag belongs only to that complete pre-host configuration.
Live commits adopt independent domains: `st_matchWeaponsManaged` for an explicit
weapon mode/mask, `st_matchTeamsManaged` for an explicit team cap,
`st_matchPopulationManaged` for automatic population, and `st_matchVotesManaged`
for the allowed-vote mask. Vote, password and roster changes preserve unrelated
legacy weapon and team-cap behavior. A field whose raw value matches an old cvar
can still represent a new explicit adoption, such as Saber-only 0 in legacy FFA
or unlimited team cap 0 when legacy TFFA size was 2.

Unowned weapons use the live `g_weaponDisable`/`g_duelWeaponDisable` masks.
Unowned TFFA caps use `g_tffaTeamSize`; unowned CTF caps remain unlimited. The
exported C helpers `ST_MatchEffectiveWeaponMask` and `ST_MatchEffectiveTeamCap`
provide those effective values to all server admission/inventory paths.
For an initial roster, set `st_matchInitialRosterPending=1` before the map
command; after the map loads, stage the roster and run `st_match_apply roster`.
This defers team locking until the initial roster has been populated. With no
roster transaction the initial-pending flag must be 0. An already locked running
TFFA match rejects new roster additions until explicitly unlocked.

Pending state is exposed in local ROM cvars (never serverinfo):

- `st_matchPending_<catalog-cvar>`, `st_matchPending_force0..17`,
  `st_matchPending_weapons`, `st_matchPending_rotation`,
  `st_matchPending_hostname`, and `st_matchPending_map` contain pending values.
- `st_matchPending_hasrotation`, `st_matchPending_hashostname`, and
  `st_matchPending_hasmap` are 1 when the corresponding text edit exists, including
  a queued empty string. `st_matchPending_password` is presence only, never secret
  text.
- `st_matchPending_bots` is the pending roster count;
  `st_matchPending_clearbots` marks the explicit rebuild.
- `st_matchPending_bot<slot>_model/skill/team/role` expose each pending roster slot.
  An empty model indicates an absent slot.
- `st_matchPendingCount` counts edits; `st_matchPendingApply` is 1 when armed.

Default spawn health 0 and shield -1 preserve stock mode/combat behavior. The
minimum respawn delay excludes Duel, Power Duel and Siege. Team capacity is
independent of connection capacity. Bots must leave one connection for the host
or another human; that human may consume the reserved connection. Roster
transactions preflight surviving humans/bots and team capacity before changing
any current bots. Power Duel requires at least three connection slots.
Complete pre-host configurations and explicit runtime changes into Duel or
Power Duel normalize each round to one kill while retaining the Duel series.

Force cap prediction appends optional fields to the existing
`CS_ST_COMBAT_CONTROLS` payload, preserving its initial protocol fields and
configstring allocation. No engine binary changes are needed.
