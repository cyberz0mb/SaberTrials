# Profile browser


## Build, verification and installation

- `tools/Build-Profile.py`: isolated UI-only build on the installed Controls/Setup
  frontend. Engine, cgame/game and renderer binaries retain their current APIs.
- `tools/Stage-Profile.py`: menu files and a UI-only PK3; creates no test launcher.
- `tools/Check-Profile.py`: private menu-only native regression checks/captures,
  including staged edits, metadata, custom skins, animation, and paint order.
- `tools/Install-Profile-Browser.py`: verifies source/build/check provenance,
  backs up replacements, and installs only the UI DLL and Profile menu artifacts.
- `dist/profile-browser-install.json`: exact targets, backups and preserved files.
- `dist/profile-candidate-01/`: source, build records and verification evidence.

Use the **Saber Trials** shortcut or [the current launcher](../tools/launchers/SaberTrials.cmd)
after installation. The verification records cover menu-only checks and track
connected gameplay and controller acceptance separately.
