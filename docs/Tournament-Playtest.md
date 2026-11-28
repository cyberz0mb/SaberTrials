# Tournament playtest

The beta 1.12 tournament host supports Saber Trials Windows clients 1.12 through 1.14. Anyone with the mod can enter the public tournament, including players without a Discord account. Each host runs an independent lobby and bracket.

## Host a lobby

1. Install the Linux server ZIP into the host's Jedi Academy server directory using its included installation guide. Keep your server name, port and private configuration.
2. Start the server and run `exec tournament-test.cfg` in its server console. This opens registration on a duel map with 32 connection slots. For a dedicated event night, put that command at the end of the server's startup configuration in place of its usual map command.
3. For teams, use `exec tournament-teams-test.cfg`. It starts on Tatooine with two starters per squad. To use three, four or five starters, edit the size in a separate copy of that configuration before loading it.
4. Run `st_event status` to check registrations. Run `st_event start` when the roster is complete. Individual entry requires an even number from 2 to 32. Team entry requires 2 to 8 squads with a full starting lineup. All connected players and reserves share the host's connection slots.
5. The server places the current opponents in the arena. Their ready confirmations start play. Individual matches run ten rounds plus a deciding round at 5–5. Teams play to ten kills per starter or ten minutes, with sudden death on a tie. Winners advance through the bracket.
6. Use `st_event pause <reason>` and `st_event resume <reason>` to pause and resume a matchup. Use `st_event close` when the event ends. Re-executing an event configuration or restarting the map starts a fresh event. Restore the normal host configuration to return to ordinary play.

## Play

Choose **Play → Tournament → Find a server**, then join your host. The ready room opens on connection. Use **Esc → Tournament lobby** to return to it. Select **Join** for individual play or **Join squad** and the same squad number as your teammates for team play. You can leave while registration is open. Open **Roster** to check entries or **Bracket** to see current opponents and results. Spectators can watch without registering.

When your match is called, select **Ready**. You can select **Unready** until the final competitor confirms. Select **Resume** to return to the arena. An open tournament keeps a reconnect ticket in the running client for its most recent event server. Reconnect to the same address and port in the same client to reclaim your place. Individuals have five minutes and teams have ten. In team play a registered reserve can replace an absent starter.

These public playtests do not award global ranked points. Discord recruitment and optional account services are separate from entering the playtest.
