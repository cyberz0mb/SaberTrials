# Windows beta Fix ZIPs

If you already have Saber Trials, choose the Fix ZIP whose first version matches
the beta shown when your game starts. Full and Lite can use the same Fix when
their updated files are identical. A new installation needs a complete edition.

1. Close Saber Trials and any local Saber Trials dedicated server.
2. Open your Jedi Academy installation. In Steam, use **Manage → Browse local files**.
3. Extract the Fix directly into **GameData**, where the existing **SaberTrials**
   folder sits beside **base**. Allow Windows to replace the matching files.
4. Start **SaberTrials.x86_64.exe** in **GameData** and check the version shown on startup.

A Fix includes changed game files and any new bundled files. Your installed
translation languages carry over. If you previously created a custom server
preset with the same name as a newly added preset, keep your own copy when
Windows asks. The update notes are in `SaberTrials/docs/ZIP-update.txt`.

## Building the update

`tools/Package-Client-Lite.py` records a compact file index for each edition in
`dist/beta-zip-history`. Keep that folder on the packaging machine. When the next
version is packaged, the script compares both editions with the latest recorded
older beta and places the verified update in `dist/private-beta/Fixes`.

To build a Fix from older distribution ZIPs, supply their Full and Lite files
to `tools/beta_fixes.py` after creating the target releases. For example:

```text
python tools/beta_fixes.py "archive/SaberTrials-Full-beta-1.13.zip" "archive/SaberTrials-Lite-beta-1.13.zip"
```

Include all distributed revisions when a version number was reused. The builder
compares each edition's file sizes and ZIP checksums before and after applying
the update. It verifies the compressed payload before publishing it locally.
If a future update needs to remove an obsolete file, migrate an existing
configuration, or replace different content for each edition, the shared Fix
reports which file needs separate handling.
