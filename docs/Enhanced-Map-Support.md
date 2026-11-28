# Enhanced Map Support

Saber Trials multiplayer supports the opt-in enhanced map format in the Windows x64 Vanilla, Rend2 and Vulkan renderers. They use the same compiled BSP, collision data and native game interfaces.

| Map type | Format | Client requirement |
| --- | --- | --- |
| Classic | Jedi Academy RBSP 1 | Existing protocol 26 compatibility and the server's usual Saber Trials requirements |
| Enhanced | Saber Trials RBSP 2 | Enhanced Map Support in both the client and server, plus the server's usual requirements |

RBSP 2 uses the same little-endian records and 18 lumps as RBSP 1. The header version identifies the expanded profile. Q3Map2 finishes BSP, visibility, and lighting as ordinary RBSP, then the Saber Trials wrapper marks and validates the final output. Compile tools and third-party viewers that only recognize version 1 can continue to work on the pre-marking build. The Enhanced Map Support connection field is independent of the snapshot protocol. The server checks it at connection and again when connected players rotate to an enhanced map.

## Limits

| Capacity | Jedi Academy source reference | Candidate guardrail |
| --- | ---: | ---: |
| Absolute authored coordinate per axis | 65,536 | 131,072 for RBSP 2 |
| BSP brushes | 32,768 | 131,072 |
| Brush sides | 131,072 | 1,048,576 |
| Planes | 131,072 | 524,288 |
| Draw surfaces | 131,072 | 262,144 |
| Draw vertices | 524,288 | 2,097,152 |
| Draw indices | 524,288 | 6,291,456 |
| Nodes and leaves | 131,072 each | 262,144 each |
| Leaf brush and surface references | 262,144 and 131,072 | 1,048,576 each |
| BSP file | Signed 32-bit file offsets | 256 MiB |

The original totals in the table are the reference constants in OpenJK's `qfiles.h`. Collision and renderer loaders already allocate many arrays from the actual lump sizes. The candidate checks lump lengths, alignment, overlap, references, tree depth, patch dimensions, light grid and visibility data before following disk offsets. The vertex and index budgets also cover the summed references across surfaces, including shared spans. Classic RBSP 1 can still use the count headroom that the runtime already had. The dedicated server preflights operator `map` and `devmap` commands before it shuts down the current match.

The coordinate bound doubles the span on each axis. IEEE-754 single-precision spacing at the bound is 1/64 unit. This is below the engine's 1/8-unit collision clip epsilon. The player and entity snapshot encoders already fall back from a 13-bit compact integer to a 32-bit float. Protocol 26 and the existing player state, entity state, user commands, and area mask layouts are retained. Enhanced patch collision builds bevels and facets relative to the patch, then moves the result into world coordinates. World bounds and NPC floor traces use the expanded range.

Leave margin between the playable envelope and the coordinate cap for outer walls, player hulls, and compiler padding. Split enhanced patches whose control points are more than 16,384 units from the first point along any axis. Keep the existing 31-by-31 control-grid limit, the per-surface batch limits of fewer than 1,000 vertices and 6,000 indices, and the 256-area wire limit. The candidate also caps BSP patches at 8,192, internal lightmaps at 256 128-by-128 tiles, visibility at 16,384 clusters, light-grid array entries at 1,048,576, and inline models at 510. The total BSP byte budget applies across all lumps.

Use structural walls and portals to break up visible space, detail brushes for decoration, and an appropriately coarse `gridsize` for maps with widely separated rooms. PVS row size grows with the number of clusters. A world that puts all geometry in one visible area can still be expensive.

Vanilla tests the frustum against enhanced planar face bounds before submitting faces. Both renderers reserve up to 524,288 draw-queue entries for large enhanced worlds and report queue exhaustion without wrapping into other views' work. Rend2 uses its shader-sorted VBOs and multidraw for enhanced maps. Its render pass stores actual submissions in reusable arrays, so a pessimistic stage estimate no longer consumes the render scratch arena. The older leaf merge still applies to Classic maps.

Additional engine constraints include the four-level server entity broad phase, the fixed entity and configstring namespaces, and the patch facet budget. They affect levels with dense interactive objects or many patches independently of the static geometry limits. The 16-bit light-grid array references a compressed sample table. A larger map can require a coarser grid even when the BSP geometry fits.

## Build and compile

Run these commands from the Saber Trials checkout. The engine build uses the existing local MVP candidate-03 checkpoint and its verified dependency extraction. It stages the client, dedicated executable, two renderers, and gameplay DLL under `dist/enhanced-maps`. Reuse the matching cgame, UI, and animation assets from that checkpoint when staging a client. The build files stay separate from the installed game.

```powershell
python tools/Build-Enhanced-Maps.py
cmake -S tests/enhanced-maps -B dist/enhanced-maps/build-check -G "Visual Studio 18 2026" -A x64 "-DST_ENGINE_SOURCE=$((Resolve-Path dist/enhanced-maps/engine).Path)"
cmake --build dist/enhanced-maps/build-check --config Release
python tools/Build-Enhanced-Q3Map2.py
```

The Q3Map2 builder accepts `--msys PATH` and defaults to the portable MSYS2 tree staged under `dist/enhanced-maps/msys64`. It needs `make` and the MINGW64 GCC, pkgconf, Assimp, GLib, libxml2, libjpeg-turbo, and libpng packages. The source is NetRadiant Custom 20260114, pinned to `68ecbed64b7be78741878c730279b5471d978c7c`. The patch doubles the tool's winding bounds and rejects an authored brush outside that envelope. The wrapper passes the increased draw-surface budget through Q3Map2's `-maxmapdrawsurfs` flag. The existing NetRadiant editor build has its own ±65,536-unit editing bounds. The expanded pipeline is a command-line compiler for authored `.map` files. [NetRadiant Custom source](https://github.com/Garux/netradiant-custom/tree/68ecbed64b7be78741878c730279b5471d978c7c)

WzMap has larger compiler constants and Warzone-specific options. The Windows candidate was built and tested with patched NetRadiant Q3Map2. WzMap outputs have not been qualified with either renderer. [WzMap source](https://github.com/OpenWarzone/WzMap)

```powershell
$p = "dist/enhanced-maps"
python tests/enhanced-maps/fixtures.py "$p/fixtures"
python tools/Compile-Enhanced-Map.py "$p/fixtures/st_far.map" --profile enhanced --compiler "$p/netradiant/install/q3map2.exe" --compiler-dlls "$p/msys64/mingw64/bin" --pakpath "$p/fixtures" --output "$p/compiled" --raw-faces
python tools/Compile-Enhanced-Map.py "$p/fixtures/st_dense.map" --profile enhanced --compiler "$p/netradiant/install/q3map2.exe" --compiler-dlls "$p/msys64/mingw64/bin" --pakpath "$p/fixtures" --output "$p/raw" --raw-faces --geometry-only
python tests/enhanced-maps/fixtures.py "$p/compiled" --expand-indices "$p/raw/st_dense.bsp"
& "$p/build-check/Release/st-bsp-check.exe" "$p/compiled/st_dense.bsp"
python tools/Compile-Enhanced-Map.py "$p/fixtures/st_classic.map" --profile classic --compiler "PATH_TO_STOCK_Q3MAP2" --pakpath "$p/fixtures" --output "$p/compiled" --raw-faces
```

Use the default compiler stages for normal maps. The dense fixture deliberately retains unmerged faces and omits baked lighting so the test measures geometry and visibility. The fixture helper expands Q3Map2's shared index spans into separate spans with identical triangles, exercising the larger on-disk index budget. The boundary fixture includes baked lighting. Package the final BSP as `maps/<mapname>.bsp` inside the PK3 alongside the map's shaders and textures. Both multiplayer sides need the same package. Keep the original `.map` and assets for future rebuilds.

## Verification

```powershell
$p = "dist/enhanced-maps"
$archives = @((Get-ChildItem ../base/assets*.pk3).FullName)
$las = "PATH_TO_CLASSIC_MAP_PK3"
python tests/enhanced-maps/check_bsp.py "$p/build-check/Release/st-bsp-check.exe" @archives $las
python tests/enhanced-maps/runtime.py --renderer rd-vanilla --dense --las-noches $las
python tests/enhanced-maps/runtime.py --renderer rd-rend2 --dense --las-noches $las
python -B tests/enhanced-maps/saber_probe.py
ctest --test-dir dist/combat-foundation-tests -C Release --output-on-failure
ctest --test-dir dist/hybrid-native-tests -C Release --output-on-failure
```

The runtime runner stages stock assets and copies the installed Saber Trials PK3s into isolated profiles. It uses an IPv4 loopback-only dedicated server and two separate client processes. Reports, sample counters, and raw logs are written under `dist/enhanced-maps/runtime`. The test checks the previous client's classic connection, its rejection on enhanced map rotation and fresh connect, both updated clients on the far map, curved-patch and wall collision, travel to the negative sector, map reloads, and malformed BSP recovery.

Both renderers passed the Windows multiplayer suite. The dense fixture contained 33,862 brushes, 203,137 surfaces, 812,548 vertices, and 1,218,822 stored indices. a separately supplied classic map loaded as Classic RBSP with 3,649 surfaces and 100,590 vertices. The boundary map reached both X extents at ±131,072. The server stopped the player against the far wall near X 131,040 and both clients continued through map rotation. A separate Vanilla probe recorded a server-confirmed saber kill at approximately X 130,760 and Z 130,844.

| Renderer | Stock `mp/duel1` p95, before → after | Dense median / p95 | Dense client peak working set | Dense reload with two clients |
| --- | ---: | ---: | ---: | ---: |
| Vanilla | 2 → 2 ms | 8 / 10 ms | 346 MiB | 2.16 s |
| Rend2 | 1 → 1 ms | 13 / 14 ms | 1,166 MiB | 4.01 s |

The client timings are short, single-client `com_speeds` samples at 960 × 540 on an RTX 4070 Laptop GPU. They measure engine frame work at the sampled viewpoints. The dedicated server peaked near 175 MiB across the two-client rotation. The raw reports record individual samples, baseline timings, and process memory.

The stock archive and a separately supplied classic map validation covered 62 BSP files. Eighteen malformed or oversized fixtures were rejected. The patched compiler also rejected an out-of-bounds brush in an otherwise valid room fixture. The combat and hybrid suites passed nine checks, including the accepted damage ramp and snapshot parity. The gameplay damage source is identical to the pinned baseline. The Windows x64 candidate is staged for review. Linux packaging, WAN play, populated-server measurements, and full far-coordinate combat coverage remain open.

## Windows installation

The local Saber Trials launcher uses the installed Windows x64 build. The five installed binaries and their previous versions are recorded in `dist/enhanced-maps-install.json`. The test maps are available separately under `dist/enhanced-maps/maps`.

## Source changes

- `development-source/enhanced-maps/overlay.py` applies the feature to the pinned OpenJK-based source checkpoint. `st_bsp_validate.h` and `st_bsp_read.h` hold the shared loader checks. `q3map2.patch` records the compiler changes.
- Generated engine changes touch `qcommon/{cm_load.cpp,cm_local.h,cm_public.h,q_shared.h}`, `shared/qcommon/q_math.c`, `client/cl_main.cpp`, and `server/{server.h,sv_ccmds.cpp,sv_client.cpp,sv_init.cpp}`. The native gameplay DLL uses the new world bounds from the two shared files.
- Renderer changes touch both `tr_bsp.cpp`, `tr_local.h`, `tr_main.cpp`, and `tr_scene.cpp` implementations. Vanilla also updates `tr_world.cpp`. Rend2 also updates `tr_allocator.cpp`, `tr_backend.cpp`, `tr_init.cpp`, and `tr_weather.cpp`.
- `tools/Build-Enhanced-Maps.py`, `tools/Build-Enhanced-Q3Map2.py`, and `tools/Compile-Enhanced-Map.py` reproduce the candidate. `tests/enhanced-maps` contains the shared BSP checker, fixture generator, malformed-input cases, and multiplayer runner.
