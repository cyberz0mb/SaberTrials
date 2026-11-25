# Enhanced cosmetic mesh format (STCOS1)

This is an opt-in renderer association for an existing multiplayer character,
implemented by the independent Enhanced Models overlay. It is not a new GLM
version. Keep the working classic character installed. Never replace its
`models/players/.../model.glm` with the high-detail mesh.

## Association

Place a text sidecar next to the **classic skin**, adding `.cosmetic` to its name.
For example, `models/players/t800_endo/model_default.skin.cosmetic` contains:

```text
STCOS1 models/players/t800_endo/model.glm models/cosmetics/t800_endo/model.glm models/cosmetics/t800_endo/model_default.skin
```

These are four whitespace-separated tokens: version, canonical GLM, visual GLM,
visual skin. No comments, additional tokens, NUL bytes or quoted paths. The file
is at most 256 bytes. Paths are at most 63 bytes, lowercase ASCII letters, digits,
underscore, hyphen, slash and period. Traversal and repeated slashes are rejected.
The canonical path must start `models/players/`; both visual paths must start
`models/cosmetics/`. Required extensions are `.glm`, `.glm`, `.skin` respectively.

The selected classic skin registers the optional dependencies. Unknown versions,
malformed sidecars and failed dependencies leave the classic skin usable. There
is no recursive association loading. The dedicated renderer does not read these
sidecars. A listen server also skips visual dependency loading while its client
renderer is inactive; client skin registration rebuilds the association after
graphics initialization. This prevents access to cleared shader memory during
map changes. The additional package contains visual geometry, visual skins and the
sidecars, not replacements for gameplay models, animations or game modules.

## Geometry and skeleton

Visual geometry uses validated GLM v6, the same exact registered GLA asset and
declared bone count as the canonical GLM. Vertex coordinates must already be in
that skeleton's bind space. Equality of animation references cannot prove correct
rigging; the exporter and animation review must establish it. Root surface 0 must
be the root of the visual hierarchy. Authors must use one connected hierarchy.

Current limits remain below 1000 vertices and 2000 triangles per surface, at most
1024 surfaces and skin assignments, 32 bone references per surface and four
influences per vertex. Rend2 permits 72 declared bones. GLM validation permits
128 MiB per file, eight LODs and hierarchy depth 128. This does not increase the
safe collision budget or justify using a dense GLM as a player model.

Visual GLMs may contain one to eight authored LODs. The November 9 T800 candidate
contains three. Every level uses the same surface hierarchy and assignments;
unused chunks can be empty at reduced levels. Reduce connected meshes before
partitioning into draw surfaces to avoid independently collapsing chunk seams.
This remains a four-influence, 32-reference-per-surface export pipeline.

Its default surface flags must express its intended
visibility; skin `*off` overrides are not applied to visual surface state in this
increment. Do not put optional visible components into an enabled default surface.
The pilot uses material assignments on its already-enabled body surfaces.

## Runtime behavior

`r_enhancedModels 1` enables substitution in **Rend2 and Windows Vulkan**.
The renderer default is `0`. A saved profile can enable the feature.
Vanilla automatically keeps canonical geometry, even when this preference is on,
and prints an explicit compatibility message. The tested twelve-character CPU
path managed only 14.4 FPS with automatic LOD, and a coarsest-LOD diagnostic
reached only 44.9 FPS; it is not a supported enhanced rendering configuration.
This is a client renderer preference. Classic clients ignore the sidecar and display the canonical
model. No protocol, userinfo model name, capability advertisement, game DLL or
server collision rule changes. Servers still need the ordinary classic package.
Pure-server package policies can prohibit a client-only add-on. Local testing
includes `sv_pure 0` and a controlled `sv_pure 1` fixture with identical model
packages on the server and both peers. The pure fixture deduplicates two existing
identical style archives; it does not qualify arbitrary public-server policies
or change the installed package collection.

The renderer submits the visual mesh with the canonical character's bone cache,
animation state and entity transforms. The character's Ghoul2 model, surface/bolt
lists, collision cache and saber attachments stay canonical. Culling/lighting
bounds also remain canonical: large silhouettes outside those bounds need further
work. More source bones, morph targets and source animations are not supported by
this association.

Substitution falls back to classic geometry for:

| Developer-log reason | Condition |
| ---: | --- |
| 1 | Preference disabled |
| 2 | Actual canonical model differs from sidecar declaration |
| 4 | Surface root is not zero, including detached components |
| 8 | Character has a gore set |
| 16 | `cg_shadows 2` requests stencil shadows |
| 32 | Canonical model chooses a nonzero LOD and the visual mesh has fewer than two LODs, or canonical LOD is invalid |
| 64 | Caller requests a custom shader override |
| 128 | Canonical surface overrides differ from the selected classic skin |
| 256 | Skeleton/animation or visual root compatibility check fails |
| 131072 | Vanilla renderer: enhanced geometry requires Rend2 GPU skinning |

Only the first reason applies, with a diagnostic once per reason per skin.
Non-default skins without a sidecar render classically. The November 9 source
team conversion supplies red and blue sidecars for both T800 character names,
sharing `models/cosmetics/t800_teams/model.glm` with separate color skins. Its
66,224 source triangles are retained in LOD0 (66,270 including attachment tags);
LOD1 and LOD2 contain 33,156 and 13,287 triangles. Damage effects and
dismemberment can still visibly change detail: those paths use classic geometry.

For a visual mesh with two or more levels, Rend2 selects its LOD with
its ordinary projected-radius calculation, `r_lodscale`, `r_lodbias` and the
canonical model's LOD bias. Selection uses the visual model's level count, not
the canonical level number. A one-level mesh retains the original distance
fallback. No LOD choice changes collision or bolt geometry. The diagnostic
reports `lod=0`, `lod=1`, etc. once per selected level per skin. These messages
establish that a level was submitted, not how many characters used it per frame.

Dependencies are loaded at skin registration even while the preference is off,
allowing live toggling. Switching off does not release their memory immediately.
A classic package without cosmetic sidecars, followed by a restart, avoids this
additional load/memory cost; removing only T800's optional HD textures does not
remove its cosmetic geometry. The installation ledger records a local modern-GPU
twelve-character benchmark. Total resident model/texture budgets, larger crowds,
many distinct assets and older hardware remain unqualified. Rend2's 2048-entry
wrapping surface pool is replaced with reusable,
address-stable pages (256 entries each), capped at 65536 pending Ghoul2 surfaces.
Exhaustion drops the render session with a diagnostic instead of overwriting
pending entries. Pages remain allocated until the renderer unloads. This is a
storage safety fix, not a production performance guarantee.

## Build and validation

See [the implementation ledger](Enhanced-Character-Model-Support.md) for build
commands, source audit, exact tests and remaining limitations. The builder stages
four binaries and never installs them. The existing classic package is always the
fallback; an enhanced-only character package is not supported.
