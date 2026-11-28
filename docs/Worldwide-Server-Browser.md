# Worldwide server browser and Quick Match

Open **Find a server** from Play to browse the Worldwide list. The source selector also offers LAN and Favorites. **Refresh** queries the masters and measures server response times. The search field matches server names, maps, and addresses as you type. **Direct Connect** accepts a hostname or IPv4 address with an optional port. Favorites, password entry, Server Info, Find Player, and manual joins use the existing OpenJK flows.

Click **Region** to sort by region and click again to reverse the order. Unknown locations stay at the bottom. The map preview panel shows the mod advertised by the selected server.

**Players** shows humans against the advertised public slot capacity. A row such as `?/32` means the server has 32 public slots and its human count is unknown. Quick Match checks actual occupancy, including bots, before recommending a server.

## Quick Match

Quick Match recommends a server before joining. Game mode, ping ceiling, minimum human population, password requirement, and combat preset each have an unrestricted setting. The same preferences can optionally filter the browser. The search field narrows the visible browser list independently.

The recommendation uses the lowest measured ping, then free public slots, then known human population. A preferred region breaks a tie after those criteria. Use **Selected region only** to make region a hard filter. **Clear filters and search** explicitly resets the match preferences and reruns the search if it finds no eligible server. A password-protected recommendation opens the existing password prompt.

Quick Match checks the server's advertised limits and current browser data. The actual connect handshake can still reject a connection after a slot fills, for an invalid password or a ban, or when the server requires a different client or game files. This feature uses public server discovery and ordinary connections.

## Network compatibility

- Worldwide queries `sv_master1` through `sv_master5`, plus the configurable `cl_browserBackupMaster`. The defaults already include Raven and JKHub. JK2MV is the new client-side backup. It is the same endpoint as `master.ouned.de` at the time of the probe. Servers retain their existing heartbeat settings. [JKHub master-server guide](https://jkhub.org/wiki/index.php?title=Master_server)
- The client merges overlapping IPv4 master replies up to the existing 2,048-row browser capacity. It retains cached addresses if no source supplies a usable list and rechecks them before recommending a server. Discovery is bounded to a 2.5-second master window. Per-server browser pings use the existing 32-request queue and a 2-second timeout. The separate manual `ping` command retains `cl_maxPing`. The inherited master-list and connection code uses IPv4.
- The browser uses a valid `g_humanplayers` count first, then subtracts a valid advertised `bots` count from total occupancy. An empty server has zero humans. For populated legacy servers that supply neither count, it sends a `getstatus` request when a probe slot is available and retries once after one second if the roster is still unresolved. It accepts extended mod status headers below 8 KiB. The fallback uses TaystJK's zero-ping bot heuristic. When a roster includes extra occupants within the reserved-slot capacity, an all-bot or all-human roster still yields an exact public count. A mixed roster with an unknown split between public and reserved slots, an unanswered query, or malformed data leaves the count at `?`. Zero-ping humans can be misclassified on servers without explicit counts. Probes use a separate 32-request pool and can extend the ping refresh by at most two seconds. [TaystJK client source](https://github.com/taysta/TaystJK/blob/master/codemp/client/cl_main.cpp)
- Combat matching requires `st_combatMode` in the short `getinfo` reply. Updated Saber Trials servers advertise it as Classic (`0`) or Manual (`1`).
- Region is an approximate lookup of the server's advertised IPv4 address against the bundled, offline server geolocation dataset. Unknown ranges show `?`. VPNs, proxies, and stale geolocation can affect the estimate. [ip-location-db server-country data and license](https://github.com/sapics/ip-location-db/tree/main/server-country)

## Build and verify

Restore or prepare the `dist/emotes-01` engine and frontend trees and their source receipt using `tools/Build-Emotes.py`. The browser overlay uses that checkpoint's engine and UI alongside the matching game, cgame, and renderer binaries. The prepare step downloads a pinned regional dataset, checks its SHA-256, and packages it with the menu. Use `--country-csv PATH` to build with a local ip-location-db CSV.

```powershell
python tools/Build-Server-Browser.py prepare
python tools/Build-Server-Browser.py engine
python tools/Build-Server-Browser.py ui
python tools/Build-Server-Browser.py dedicated
cmake -S tests/server-browser -B dist/quick-match-tests
cmake --build dist/quick-match-tests --config Release
ctest --test-dir dist/quick-match-tests -C Release --output-on-failure
python tests/server-browser/check_runtime.py rd-vanilla
python tests/server-browser/check_runtime.py rd-vanilla --population
python tests/server-browser/check_runtime.py rd-rend2 --protected
```

For the current Windows client, run `python tools/Build-Mod-Compatibility.py build` and add `--compat` to the runtime test commands. The portable tests exercise the production roster parser and status probe scheduler without UDP sockets.

The staged Windows executables, UI module, region/menu PK3, Linux binaries, and isolated playtest evidence are in `dist/server-browser-01`. The Linux dedicated source staging flow applies the same getinfo change and runs the portable browser tests alongside the other server checks.
