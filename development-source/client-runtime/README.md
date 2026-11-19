# Controller configuration lifecycle fix

This overlay is independent of Enhanced Maps and Enhanced Models. It corrects
the controller input paths in the installed-client source checkpoint used by
`tools/Build-Enhanced-Models-Install.py`.

Both SDL polling and client movement repeatedly registered archived controller
cvars. OpenJK's `Cvar_Get` marks the archive dirty even when a variable is already
registered, so ordinary input frames caused `openjk.cfg` to be rewritten. The
model benchmark exposed this as substantial file I/O outside renderer timings.

The replacement files cache the returned engine-owned cvar pointers, following
the engine's existing cvar lifetime convention. Their values remain live:
enabling/disabling, horizontal/vertical sensitivity, inversion and deadzone still
take effect without restarting. Legacy joystick fallback, release events,
controller discovery, button mappings and look calculations are unchanged.
No game modules, map code, renderer code or network structures are changed.

The overlay checks the exact checkpoint source hashes before replacement and is
idempotent for its own output. The full combined builder applies it after the
independent model and map overlays. `--client-runtime-only` verifies the previous
binary hashes and unchanged model/map source inputs, then rebuilds only the
client executable; the renderer and dedicated-server binaries remain intact.

Reproduce the regression test:

```powershell
cmake -S tests/client-runtime -B dist/client-runtime-tests -G "Visual Studio 18 2026" -A x64
cmake --build dist/client-runtime-tests --config Release
ctest --test-dir dist/client-runtime-tests -C Release --output-on-failure
```

The test compiles the actual production include files with mock input/cvar APIs.
It checks repeated disabled/active polling without archive dirtying, live
sensitivity/inversion/deadzone changes, menu input blocking and release on
disable. It does not claim physical-controller hardware acceptance.
