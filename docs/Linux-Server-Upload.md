# Saber Trials Linux server upload

Use a compatible x86_64 Linux host with the matching Saber Trials dedicated
engine and game module. Beta 1.15 preserves accented Latin letters in player names. Obtain Jedi Academy game data separately.

## Before uploading

Your host must allow a **custom x86_64 Linux executable** and the matching game
module. Uploading only a PK3 or replacing the gameplay module under the old
engine cannot provide the new native staff/account systems.

Locate the server's existing `base` folder. The `upload` folder in this ZIP
contains the files to place **beside that base folder**. Do not put them in
`base`, `.ssh`, or the home folder unless `base` is actually there.

Stop the chosen server in its panel and take a backup before replacing anything.
Use one server for the first trial. Keep the original startup setting and engine
available so you can switch back. Never merge this gameplay module into JA+,
Lugormod, or another mod's directory.

## Upload and start

1. Extract this ZIP on your computer. Upload the **contents of `upload`** to the
   directory containing `base`. You should then have:

   ```text
   base/                         your existing licensed game files
   openjkded.x86_64              new Saber Trials server engine
   start-sabertrials.sh
   SaberTrials/
     jampgamex86_64.so
     server.cfg.example
     staff-setup.cfg.example
   ```

2. Set `openjkded.x86_64` and `start-sabertrials.sh` to permission **755** in the
   panel's file manager. ZIP uploads do not always preserve executable flags.
3. Copy `SaberTrials/server.cfg.example` to `SaberTrials/server.cfg`. Edit your
   server name, player count and gameplay choices there. Existing `server.cfg`
   is never included or overwritten by this package. Keep edited passwords private.
4. Set the panel startup command to `./start-sabertrials.sh YOUR_ALLOCATED_PORT`.
   Replace the final part with the port your host assigned; do not invent a new one.
5. If you have a terminal, first run `./start-sabertrials.sh --check YOUR_ALLOCATED_PORT`.
   This checks required files and libraries without starting the game.
6. Start through your panel and read the console for missing files/libraries.
   Join using the matching Saber Trials client before testing staff or tournaments.

If the panel accepts a binary and arguments instead of a script, use
`openjkded.x86_64` with arguments:

```text
+set dedicated 2 +set net_port YOUR_ALLOCATED_PORT +set fs_game SaberTrials +exec server.cfg
```

The working directory and `fs_basepath` must point to the directory containing
`base` and `SaberTrials`. Prefer the supplied script because it sets these paths
explicitly. Use the exact folder case: Linux is case sensitive.

## Staff setup

Copy `staff-setup.cfg.example` to `staff-setup.cfg`, then follow its dedicated-server
section. Existing staff files are not overwritten. Assignments are saved under
the Linux server account, not in the public PK3 or the player's display name.
Never automatically execute staff grants from the startup configuration.

Default private state is in `$HOME/.sabertrials`, with separate server folders
for each port. A host can set `SABERTRIALS_STATE_DIR` to an absolute, writable,
private directory outside `base` and `SaberTrials`. Its parent must exist.
The server creates private directories with mode 700 and files with mode 600.
Symlinked credential/state paths are rejected. Keep the service's user and HOME
consistent across restarts.

Back up the **entire** private state directory while the server is stopped.
Encrypted files and their adjacent `.protect` keys must stay together. These
keys are protected by Linux ownership/permissions; someone controlling that OS
account can access them. Windows DPAPI files cannot simply be copied to Linux.
This Linux server starts with its own server identity; players trust that server
and the operator enrolls Owners/Admins/Moderators as described in the template.

## Discord accounts and tournaments

Normal Saber Trials hosting does not require a central service credential.
Verified account registration for tournaments does. After you select the first
server, provide its public join IP and port so it can be enrolled separately.
Do not share a credential between independently operated servers.

Once a credential is privately delivered, give its file mode 600 and import it
from the trusted **server console**, using an absolute Linux path:

```text
accountserver import "/private/path/server-credential.json"
accountserver status
```

Do not put the credential, Discord client secret, or a player token into a CFG,
PK3, server name, chat, or public download. The ordinary server package has none.

Players need the matching client with the server-account bridge. The earlier
browser-login-only client can sign in to Discord but cannot complete this new
server verification. The Windows bridge development package is separate; update
the client before testing the end-to-end connection.

Once approved and configured, a signed-in player should see
`Account: Verified on this server.` Tournament registration then uses the verified
ranked name and registered team. Bots cannot register as ranked accounts.

The new tournament controller supports the agreed individual and team formats,
ready checks, disconnect windows, substitutes, and staff intervention. It uses
Duel/TFFA simulation for now. It does not yet replace the Siege protocol game type,
survive map/server restarts, publish results to Discord, or award global rank points.
Team accounts must exist centrally before team registration can work.

## Restore the previous server

Stop the server, restore its previous startup executable/arguments and game
module from your backup, then start it again. Keep the new private state backup
if you want to resume Saber Trials later. Do not erase your licensed base assets,
other mods, maps, or player configuration during rollback.
