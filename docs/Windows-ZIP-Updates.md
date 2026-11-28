# Windows beta update

**Already have Windows beta 1.11?** Download **SaberTrials-Windows-Fix.zip** to
update directly to **1.15**. The same ZIP works for Full and Lite.

**First install?** Download the complete **1.15 Full** or **1.15 Lite** ZIP.

1. Close Saber Trials and any local Saber Trials dedicated server.
2. Open your Jedi Academy installation. In Steam, use **Manage → Browse local files**.
3. Extract the Fix directly into **GameData**, where the existing **SaberTrials**
   folder sits beside **base**. Allow Windows to replace the matching files.
4. Start **SaberTrials.x86_64.exe** in **GameData** and check the version shown on startup.

A Fix includes changed game files and any new bundled files. Your installed
translation languages carry over. The 25.47 MB Fix includes the new menus and keyboards. For Dutch, Swedish or Finnish offline chat, extract the desired language packs into the same GameData folder. The complete Full edition includes them. The Fix also includes the two tournament test
presets introduced after 1.11. If you edited either preset, keep your copy when
Windows asks about those files. The update notes are in `SaberTrials/docs/ZIP-update.txt`.

## Building the update

`tools/Package-Client-Lite.py` records a compact file index for each edition in
`dist/beta-zip-history`. Keep that folder on the packaging machine. When the next
version is packaged, the script compares both editions against the versions in
`RELEASED_BASELINES` in `tools/beta_fixes.py`. Add a version there once it has
actually gone out to testers. Internal builds can have local indexes without
becoming update baselines. The script replaces `dist/private-beta/Fixes/SaberTrials-Windows-Fix.zip`
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
