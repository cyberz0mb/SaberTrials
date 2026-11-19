# Permanent staff accounts

**October 22, 2026 staff update:** permanent accounts and moderation commands
have passed isolated native dedicated/listen-server testing. Release checks and
the installation record are documented in `Staff-Verification.md` and
`dist/staff-install-manifest.json`. Start with `Launch-SaberTrials-Overhaul.cmd`
and use the matching updated server/game modules.

Appointments are local to each server: **Owner > Admin > Moderator**. Accounts
survive reconnects, map changes and restarts. This does not create a worldwide
ranked identity and does not require Discord or a website.

## First enrollment

For file-based setup, copy `templates/staff-setup.cfg` to the mod folder and
edit the public IDs in that copy. Its comments explain local hosting,
dedicated servers and later role changes. Run `exec staff-setup.cfg` manually
for the selected operation. Appointments persist separately; do not add staff
setup to automatic server startup. See [configuration templates](../templates/README.md).
The individual console commands below perform the same setup.

1. In the updated client, run `staff identity`. It prints your public account
   ID. Send that public ID to the trusted server operator.
2. The operator runs `staff serverkey` in the trusted server console and shares
   that public server key through a trusted channel.
3. The operator appoints the first Owner in the server console:
   `staff owner add <public-account-id> "Owner label"`.
4. Join that server and run `staff trust <verified-server-key>` once. This pins
   the server identity and starts login. On later connections authentication is
   automatic. `staff login` explicitly retries; `staff whoami` shows your role.

Only public IDs belong in these commands. A name, clan tag, IP or copied public
ID does not grant access. Owner grants/recovery require the trusted server
console. No Owner is created automatically during installation.

## Account commands

| Command | Purpose |
| --- | --- |
| `staff identity` | Create a private local identity on first use; display its public ID |
| `staff trust <server-key>` | Explicitly pin the verified current server identity |
| `staff login` | Authenticate on the current trusted server |
| `staff logout` | End staff access and suppress automatic login until explicitly re-enabled |
| `staff whoami` | Show only your authenticated role: Owner, Admin or Moderator |
| `staff list` | Show enrolled staff; use the server console for the complete roster |
| `staff add <public-id> <admin\|moderator> "label"` | Enroll a lower role |
| `staff role <account-id> <admin\|moderator>` | Change a lower role |
| `staff remove <account-id>` | Disable an appointment and revoke active access |
| `staff export "C:/path/backup.key"` | Create an encrypted portable identity backup |
| `staff import "C:/path/backup.key"` | Replace the local identity with a verified encrypted backup |

Owners can manage Admins and Moderators. Admins can manage Moderators. Moderators
cannot appoint anyone. In-game staff cannot modify themselves, peers or superiors.
The trusted console can add an additional Owner for recovery; the final Owner
cannot be removed or demoted until a replacement Owner has been appointed.

## Moderation commands

The ghost HUD label is `Ghost`. Routine staff-action console lines show the role,
client slot, action and outcome without account keys or numeric command codes.
Read-only role checks and target lookups do not print a duplicate audit line.
Authentication and the saved account records still use the same identities.

| Command | Purpose |
| --- | --- |
| `freeze "player name"` / `freeze #3` | Hold a lower-authority player in place, including in the air |
| `unfreeze "player name"` / `unfreeze #3` | Release the freeze |
| `freeze` / `unfreeze` | Use your current aim to select a visible player or bot |
| `ghost on` / `ghost off` | Enter/leave invisible, noncombat flight through geometry |
| `summon "player name"` / `summon #3` | Move a lower-authority player to a clear nearby location |
| `travel "player name"` / `travel #3` | Move yourself near that player |
| `travel coords 100 200 300` | Move to validated map coordinates |
| `travel server 127.0.0.1:29070` | Authorize the local client to connect to a numeric address |

Exact names take precedence; ambiguous partial names fail. Use `#client-ID` to
avoid numeric-name ambiguity. Ordinary `connect`, `record`, `stoprecord` and
other existing commands remain available. The developer-only engine freeze is
routed to moderation while connected, avoiding a local engine hang.

These moderation commands have **no `staff` prefix**. For example, use
`freeze #0`, not `staff freeze 0`. `status` shows the current client IDs.
Bots can also be targeted; they do not receive staff accounts or login access.

For convenient keys, enter `bind F6 "freeze"` and `bind F7 "unfreeze"` in your
game console. Pick different keys if F6/F7 already have bindings you want to keep.
Close the console, aim directly at the player, then press the key. Freeze and
unfreeze are separate actions, not a toggle. No target means no action; walls
block aiming. The server traces the character's aim from eye height, matching
the normal dynamic saber crosshair, up to 8192 map units. Custom static or offset
crosshairs may not line up; named/ID targeting remains available. Each request
locks the selected connection, so moving your aim or a recycled client slot cannot
redirect the follow-up action. Frozen players remain aim-selectable even though
their collision is disabled. The same staff and match protections apply.

Freeze and ghost suppress combat, pickups and objective interaction. Ghost off
returns to the saved safe entry position; if unsafe, the implementation tries a
safe spawn, then spectator mode. Logout/disconnect clear effects issued by that
connection. Account revocation clears all of its connections' effects; map change
clears all effects. These cleanup paths have passed native local tests.
Interventions involving active private duels/tournament competitors, objective
carriers, vehicles or active Duel/Power Duel players are rejected. Solid or
hazardous teleport destinations fail without telefragging anyone.

## Private storage and recovery

Windows native builds use `%LOCALAPPDATA%/SaberTrialsStaff/` outside downloadable
game paths. `client/identity.key` contains a Windows DPAPI-protected key;
`client/pins/` holds public server pins. A server stores `server.key` and
`accounts.db` in `servers/<net_port>/`. Run separate server instances under
distinct ports or Windows accounts so their private stores are independent.

The OS-bound key file is not a portable backup. Use `staff export`; the local
masked dialog requests a passphrase of at least 12 characters and confirmation.
The passphrase is never a console argument or cvar. Export refuses to overwrite
an existing file. Import requires the passphrase and only replaces the identity
after successful verification and a durable protected write. Importing another
identity means servers must recognize that identity's public ID.

Back up the server's private directory while the server is stopped. Preserve the
server key alongside the account database. Never put this directory in a PK3,
download folder, release ZIP or public repository. Corrupt/unreadable storage
denies staff access; it is not reset automatically. If a client key is lost,
appoint a new identity and disable the old account using trusted console access.

## Implementation and verification

Ed25519 signatures bind login to the pinned server, account, random nonces and
connection generation. Each privileged action is signed and sequence checked.
Targets also carry a connection generation to reject stale/recycled client IDs.
Private keys stay local. Signed command payloads are authenticated, not encrypted.
Staff protocol packets are handled outside demo recording and normal chat.

Build/test entry points: `tools/Build-Staff.py --tests-only`, `--qa`, and
`tools/Test-Staff.py`. Dependency versions/checksums and licenses live under
`development-source/staff/dependencies/`. Runtime tests use isolated fixtures;
their identities must never ship. Do not install a QA build: it contains
test-only local input hooks which production builds exclude.
