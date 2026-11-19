# Model metadata for Profile

This is the local documentation for the new Saber Trials browser. Publishing it
to GitHub is deferred until requested.

Add an optional `st_profile.ini` beside a model's `model.glm` and skin files:

```text
models/players/my_character/model.glm
models/players/my_character/model_default.skin
models/players/my_character/icon_default.jpg
models/players/my_character/st_profile.ini
```

Package it inside the model's existing PK3 at that virtual path. Install the PK3
normally in `GameData/base`, then restart the client to mount/index new packages.
No browser source changes are needed. Models without metadata still appear.

```ini
displayName=My Character
universe=My Franchise
themes=Sci-Fi,Fantasy
```

- **displayName:** human-readable character name, up to 96 UTF-8 bytes.
- **universe:** actual franchise, such as One Piece or Star Wars. Optional; absent
  information stays hidden in the portrait tooltip.
- **themes:** comma-separated Anime, Sci-Fi, Horror, Fantasy and/or Comics.
  Names are case-insensitive. Unknown themes are ignored; a character without
  recognized themes appears under Uncategorized.
- **group:** optional shared identifier for known alternate model directories,
  up to 48 ASCII letters/digits/spaces/underscores/hyphens. Use the same group,
  displayName, universe and themes across those directories. Outfits within a
  directory group automatically. Grouping never combines Base and DLC entries.

Files are data only and limited to 4 KiB. UTF-8 BOM, CRLF, optional surrounding
double quotes, and full-line `#`/`;` comments are supported. Malformed files are
ignored atomically, retaining bundled fallback metadata. An installed valid
sidecar replaces its model's bundled fallback; omitted fields are left unknown.
No commands are executed, and metadata cannot supply asset paths or scripts.

The bundled catalog labels familiar models, with original JKA characters assigned
to Star Wars/Sci-Fi. Base means original character directories, even when their
textures are replaced; DLC means installed custom character directories.

Team support is detected from actual red/blue skin files. Custom sound detection
checks `sounds.cfg` for an installed voice folder containing audio files, excluding
the original game's stock voice folders. This is file detection, not a guarantee
of complete team/voice compatibility. Replacing audio inside an original stock
voice folder is not classified as a separate custom voice set.

Use [the template](../templates/model-profile.ini) as a starting point. Authors
remain responsible for correct franchise tags and compatible JKA animations.
