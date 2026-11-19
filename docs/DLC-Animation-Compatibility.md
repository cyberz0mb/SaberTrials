# Custom-model animation compatibility

Compatible custom characters support handedness and ready stances. Unsupported
rigs use their stock ready pose. Hand and stance changes apply after respawning.

The animation loader preserves existing facial and accessory animations while
adding compatible stance frames in memory. Character packages are distributed
separately.

## Building

The source overlay is in `development-source/dlc-poses/`. Use
`tools/Build-DLC-Poses.py` to prepare and build matching engine, game, cgame,
UI and renderer modules. Native checks are in `tests/dlc-poses/`.
