# Menu themes

Choose **Setup → Interface → Menu Theme**. Saber Trials is the default. Choose Classic JKA and select **Apply changes** to switch immediately. In Classic, open **Setup → Interface** and activate the **Menu Theme** row to return to Saber Trials. **All interface settings** opens the existing settings editor.

Classic uses the installed Jedi Academy multiplayer menus, fonts and artwork. Its main menu and pause menu each have a **Saber Trials** button for the expanded menus, including the advanced browser, controller settings and profile tools. **Back to Classic JKA**, Escape or controller Back on the expanded root returns to Classic. The shared match review uses the Saber Trials layout in both themes.

**Host a Match → Gameplay** chooses the existing Classic JKA or Saber Trials combat preset. Review the match and select **Start this match** to apply it. The menu theme and HUD each have their own preference. Both Windows editions include the listen-server game module and use the existing launcher.

## Implementation

| Source | Responsibility |
| --- | --- |
| `development-source/menu-theme/menu_theme.inc` | Defers menu replacement until input processing finishes, restores the destination, and handles access to the extended menus. |
| `development-source/menu-theme/menu_items.inc` | Adds native controls to the stock menus and a gameplay selector to both host layouts. |
| `development-source/menu-theme/preference.inc` | Loads and saves a single client-owned choice across mod directories. Uses an atomic replacement for `SaberTrials/menu-theme.txt` under the active client home. |
| `tools/menu_theme.py` | Integrates the shared settings catalog, native UI input and rendering, match review, client cvar guards and filesystem lookup into the generated OpenJK sources. |
| `tools/Build-Mod-Compatibility.py` | Applies the integration to the Windows engine and UI before compilation. |
| `tools/Package-Private-Beta.py` | Packages the local game module and the existing client binaries. Lite inherits the same binaries from Full. |
| `tests/compatibility/menu_theme.py` | Exercises both selectors, menu navigation, persisted settings, host combinations and the personal pause UI. |

The client registers `st_menuTheme` as an archived, protected client variable. Valid values are `0` for Classic and `1` for Saber Trials. Local console changes and the settings service can update it. Server and VM setter paths ignore writes to this variable, as do per-mod startup configuration files. The shared preference takes effect before those configurations load.

The frontend loads one menu layout at a time. Its Classic lookup accepts only the two retail menu indexes, menu definitions and the menu header from the installed base asset packs. The usual pure-pack check still applies. Both layouts share the same menu parser, game actions, browser data and match-rule service.

## Windows validation

- Captured main, play, browser, host, solo, profile, setup and controls screens in both themes at 640 × 480. Rechecked main, host, setup and browser with the installed Release client at 1280 × 720. Checked the host selector against the map list, preview and footer.
- Tested both directions through the menu controls, including mouse activation and simulated controller navigation, Accept and Back. Checked the expanded menus and the Classic Interface dialog.
- Restarted with a conflicting theme entry in the per-mod configuration. The selected theme, player name, HUD setting and test key binding persisted.
- Started all four theme and gameplay combinations through the host screen and match review. Each client entered active play, opened its pause menu and disconnected with its theme selection intact.
- Connected to a local pure server using the stock client modules and a compatible local server fixture. Opened the personal pause menu, switched themes in both directions while connected and verified the saved preference after disconnecting.
- Verified the release engine, both UI DLLs, local game DLL and launcher in the Full and Lite archives against their installed or source files. Both archives passed complete CRC checks.

The automated navigation tests use the same UI source built with `ST_CONTROLS_QA`. The Windows packages use the Release UI. To run the regression on Windows, pass the QA UI DLL to `tests/compatibility/menu_theme.py` after building and installing the Release engine.

Physical controller testing and a live dedicated-server join remain unverified. The separate dedicated-server process started, but UDP packets sent to localhost timed out in this environment, including an independent socket check. The optional `--udp` regression covers that path on a host with working loopback UDP.
