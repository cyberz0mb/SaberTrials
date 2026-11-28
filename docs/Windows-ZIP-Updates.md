# Windows beta update

If your installed Windows beta is 1.11 or later and a newer beta is available,
download **SaberTrials-Windows-Fix.zip**. This one download brings both Full and
Lite up to date in a single step. If you're already on the current beta, you're
up to date. For a first install or a version before 1.11, use the latest Full or
Lite edition.

1. Close Saber Trials and any local Saber Trials dedicated server.
2. Open your Jedi Academy installation. In Steam, use **Manage → Browse local files**.
3. Extract the Fix directly into **GameData**, where the existing **SaberTrials**
   folder sits beside **base**. Allow Windows to replace the matching files.
4. Start **SaberTrials.x86_64.exe** in **GameData** and check the version shown on startup.

A Fix includes changed game files and any new bundled files. Your installed
translation languages carry over. The 1.14 Fix includes the two tournament test
presets introduced after 1.11. If you edited either preset, keep your copy when
Windows asks about those files. The update notes are in `SaberTrials/docs/ZIP-update.txt`.

## Building the update

`tools/Package-Client-Lite.py` records a compact file index for each edition in
`dist/beta-zip-history`. Keep that folder on the packaging machine. When the next
version is packaged, the script compares both editions with all recorded
revisions from 1.11 onward. It replaces `dist/private-beta/Fixes/SaberTrials-Windows-Fix.zip`
after verifying the patch against those file lists.

On a fresh packaging machine, import the Full and Lite archives for each
previously distributed Windows beta starting at 1.11. Pass their paths together
to `python tools/beta_fixes.py` after creating the target releases. With those
indexes available, rebuild the single download with:

```text
python tools/beta_fixes.py
```

Include all distributed revisions when a version number was reused. The builder
compares each edition's file sizes and ZIP checksums before and after applying
the update. It verifies the compressed payload before publishing it locally.
If a future update needs to remove an obsolete file, migrate an existing
configuration, or replace different content for each edition, the shared Fix
reports which file needs separate handling.
