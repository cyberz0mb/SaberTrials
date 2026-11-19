# Saber Trials voting system

Status: v1 policy approved

## Eligible voters

- Connected human players
- Connected human spectators
- Bots are excluded
- Each eligible client gets one vote

## Allowed vote categories

### Match limits and maps

- Time Limit, Frag Limit (Duel/FFA/TFFA), and Capture Limit (CTF).
- Map selection, Restart Map, Next Map, and Warmup On/Off.
- TFFA Lock Teams / Unlock Teams.

These are available through Call Vote. Limit changes use the normal vote
execution delay and can end a round if its current time or score already
exceeds the new limit. Tournament retains its fixed one-kill rounds.
See `MENU_CONTROLS.md` for menu locations, ranges, and configuration.

### Force Mode

- `Restricted Force`
- `Full Force`

A passed Force Mode vote is queued. It is announced immediately and applied at the next round boundary. The selected mode persists until another Force Mode vote passes or an administrator overrides it.

### Game Type

- `Duel`
- `FFA`
- `TFFA`
- `CTF`

A passed Game Type vote is queued and applied at the next safe round boundary.

Announcements use the readable proposal (for example, `Game Type: TFFA`).
Ordinary gametype changes do not announce or perform a tournament reset.
If a legacy tournament is present when the accepted change executes, its
registration/match state is cleared and saved before queuing the new mode.

### Kick

- The target must be a currently connected human player or bot.
- Human targets retain staff protection; bot targets use the bot-only removal path.
- A passed Kick vote executes immediately.
- The vote UI must identify the target unambiguously.

### Bots

- FFA may add Duelist, Sentinel, Berserker, or Trickster.
- TFFA may add Duelist, Sentinel, or Berserker.
- CTF may add Defender or Flag Catcher.
- Duel may add only Saber Master.
- Tournament keeps classic bot behavior and cannot select Saber Master.
- A passed Add Bot vote executes immediately and chooses a random installed bot character.

## Safety requirements

- Vote choices map to internal allowlisted actions; user-supplied console commands are never executed.
- A client cannot vote more than once on the same proposal.
- Disconnected clients and bots do not count toward the result.
- Administrators can cancel or override queued rule changes.
- The server announces the proposal, running tally/status, result, and when a queued change becomes active.

## Approved vote policy

- A proposal requires more than 50 percent of eligible connected human voters to vote yes.
- Each vote remains open for 30 seconds unless it passes or becomes impossible to pass sooner.
- A 60-second cooldown applies between vote calls.
- Each person may initiate at most three votes per map.
- Administrators and moderators are protected from kick votes.
