# PUG and Ladder

Select **PUG** or **Ladder** in Host a Match or Solo. The in-game vote menu offers both under Game Type. An accepted vote queues the change for the next round. The Saber Trials server browser shows the format by name, and Quick Match can filter by either one. Tournament registration and bracket play have their own controls.

## PUG

Everyone who connects as a player starts as a spectator. Open **Pause → PUG Queue → Join Queue** to play. The same controls are available in the console with `pug join`, `pug leave` and `pug status`.

Open places go to the front of the queue, starting with the smallest team. Bots can fill places until a human needs one. At round end, a waiting player replaces the lowest scorer on a team. A tied score rotates the player who has held a place longer. When fewer people are waiting than there are teams, the first team considered changes each round. A benched human goes to the back of the queue. With an empty queue, the current teams stay in.

The active-player inactivity timer defaults to 90 seconds. Players get a warning with 15 seconds left. An idle player returns to spectating and can rejoin the queue. Watching or waiting preserves the player's place.

Hosts can choose the team count and size. With fixed teams, the host menu allows at least one waiting place per team where the 32-connection limit permits. For a dedicated 4v4 with four waiting places, set `sv_maxclients 12`, `g_tffaTeams 2` and `g_tffaTeamSize 4`. Spectators and active players share the server's connection limit. A full 8×4 lineup occupies all 32 places.

## Ladder

Each series is first to ten **duel-round wins**. The number next to a player's name is their position on that server. An asterisk on the scoreboard marks someone who has yet to finish a series. New arrivals join at the bottom.

One arena cycles through neighboring positions. For example, with six players the first pass is 1 vs 2, 3 vs 4, then 5 vs 6. The next pass is 2 vs 3, then 4 vs 5. The cycle repeats using the current standings. The lower-ranked challenger takes the higher position by winning the series. The outgoing pair gives way when another pairing is due.

When a player disconnects, everyone below that place moves up. A disconnect during a series cancels that unfinished result. Returning players enter at the bottom again.

## Official account points

On an enrolled server connected to the updated Saber Trials accounts service, a signed-in player earns one point for completing a PUG round or a full Ladder series. Winning adds one more point. A tied PUG awards one completion point. The server records who was signed in when play began and checks that the same player finished. Guests, bots, spectators and mid-round substitutes can play, with substitutes becoming eligible at the next start. Account status displays the saved balance after refresh. These points persist across servers and sessions. Ladder position belongs to the current server session.

For hosted rollout, update the accounts service and both the dedicated engine and game module. The server uses its existing enrollment credential. Results use unique identifiers so a retry cannot award the same points twice. If delivery fails, the server retries briefly and logs failures. A server shutdown or prolonged outage can lose an unsubmitted award.

## Dedicated setup

Set both values before loading a matching map.

| Format | `g_gametype` | `st_gameFormat` | Example map |
| --- | ---: | ---: | --- |
| PUG | 6 | 1 | `mp/ffa3` |
| Ladder | 3 | 2 | `mp/duel1` |

Use `st_gameFormat 0` for the standard modes. `st_pugAfkSeconds` controls the PUG inactivity interval. A player can request a mode vote with `callvote g_gametype pug` or `callvote g_gametype ladder`.
