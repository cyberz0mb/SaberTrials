# Editable Saber Trials configuration

These are clean distribution templates. Copy the file you need into
`GameData/SaberTrials`, then edit that copy with a text editor such as Notepad.
Preserve any existing personal configuration instead of overwriting it.

| File | What you edit | When to run it |
| --- | --- | --- |
| `server.cfg` | Server name, slots, join password, game type, map, combat options, limits, bots and votes | Server startup |
| `staff-setup.cfg` | Public account IDs, public server key, role labels and appointment/removal commands | Manually, for setup or a deliberate staff change |

Text after `//` is an explanation. It is ignored by the game. Change values
inside quotes. The staff template's commands are disabled by default: replace
its placeholders, then remove `//` only from the section you intend to run.
Keep the other sections disabled. There is no preassigned Owner, shared password
or personal account ID in these templates.

Run a prepared copy from the appropriate console:

```text
exec server.cfg
```

This loads the selected map and replaces the match currently running. Dedicated
server startup can use `+set fs_game SaberTrials +exec server.cfg`; choose its
network port at process startup with `+set net_port 29070` if needed. The port
identifies this installation's private server-account store, so keep it stable.
For a game hosted inside the client, use the updated Overhaul launcher.

For staff enrollment, use:

```text
exec staff-setup.cfg
```

The local host can enroll their own Owner and trust their hosted server using
section A. On a dedicated server, the operator runs the owner-add command in the
server console; the player runs the trust command in their own game. Subsequent
appointments/removals can use the relevant section of the file. These commands
need trusted console access or the appropriate authenticated staff role.

The game saves appointments permanently; a CFG is an instruction file, not the
account database. Comment out completed grant lines. Do not run staff setup on
every startup: an old grant would otherwise restore someone you removed. Staff
private sign-in keys and account storage stay outside these files. See
`docs/STAFF_ACCOUNTS.md` for recovery and encrypted backups.

The `server.cfg` example is self-contained. Its values override previous settings
each time you run it, including changes made during a prior match. Update your
edited copy when you want a choice to remain your startup default. Many combat
settings need a map restart; the final `map` command applies them at startup.

Distribute only these clean templates. Keep edited passwords, personal staff
setup files and private account storage out of release packages. Build output
ships the templates as loose, editable files alongside the asset PK3; staff
update ZIPs include them under `SaberTrials/templates/`.
