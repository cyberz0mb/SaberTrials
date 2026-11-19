# Making weapon DLC for Saber Trials

Weapon DLC adds guns to the weapon cycle alongside Jedi Academy's original guns.
It does not replace an existing gun slot. Use the normal next/previous weapon
controls (including mouse wheel or controller bindings) to select it. There are
no DLC weapon pickups or new map entities. This is multiplayer support only.

Every DLC gun declares its closest JKA gun in `baseWeapon`. That choice supplies
damage, firing rate, projectile physics, alternate fire, charging, animations,
ammo type and ammo cost. The author chooses this match; the game does not guess
from a model or filename. Custom effects change presentation, not damage or aim.

**Released DLC should provide its own muzzle, shot and impact effects, and firing
sounds, for both fire modes where applicable.** Keep them in your own namespace.
The runtime deliberately supports incomplete packs: each omitted or unloadable
effect falls back to the matching JKA gun's effect. A pack with no effects still
works. Do not overwrite stock effect files to customize one gun.

## What players and server hosts need

- Install the updated Saber Trials game and client modules. An old client cannot
  select these add-ons; an old server does not advertise them.
- Put the same weapon PK3 in each participant's `GameData/SaberTrials` folder and
  on the server. Restart the game/server or change map after changing packs.
- `g_weaponDLC 1` enables the catalogue (default); `0` disables it at the next
  map load. Up to **63 gun definitions** can be active together.
- The server's catalogue controls the cycle. Client-only packs are not offered.
  Catalogue order is deterministic, independent of file enumeration order.
- No gun pickup is required for an enabled DLC gun. Ammunition is still required
  when the chosen base consumes it. Existing ammo pickups refill the shared pool.
  Selecting a gun never grants ammo or grants ownership of the original gun.
- Empty DLC guns remain visible in the cycle; firing one uses the normal
  out-of-ammo handling. Original guns retain their usual pickup and selection rules.
- Saber-only matches, disabled gun families, private saber duels, Jedi-only
  restrictions, vehicles and spectator/dead states do not grant DLC gun access.
  Siege also requires the matching base gun in the player's class inventory.
- Missing/different definitions or missing models use the stock gun's appearance
  for other players, and that local add-on is not offered in the cycle. Pure-server
  package/download requirements still apply before joining.
- This format is for guns. Sabers use Saber Trials' saber definitions; grenades,
  mines, placed explosives, turrets and vehicle weapons are not DLC gun families.

## Choose a base gun

| `baseWeapon` | Closest JKA weapon | Shared ammo pool |
| --- | --- | --- |
| `bryar` | Modern blaster pistol | Blaster energy; stock pistol uses zero per shot |
| `bryar_old` | Legacy Bryar pistol | Blaster energy |
| `blaster` | E-11 blaster rifle | Blaster energy |
| `disruptor` | Tenloss disruptor rifle | Power cells |
| `bowcaster` | Wookiee bowcaster | Power cells |
| `repeater` | Imperial heavy repeater | Metallic bolts |
| `demp2` | DEMP2 | Power cells |
| `flechette` | Golan Arms flechette | Metallic bolts |
| `concussion` | Concussion rifle | Power cells |
| `rocket` | Merr-Sonn missile system | Rockets |

For example, a new blaster shares energy with the original E-11, a new repeating
gun shares metallic bolts with the heavy repeater, and a new missile launcher
shares rockets with the Merr-Sonn. Multiple add-ons in the same family consume
the same pool. Selecting or respawning with an add-on grants no extra ammo;
the base game still controls the normal respawn loadout.

For testing, use a cheat-enabled local map (`devmap mp/ffa3`), then
`g_infiniteAmmo 1`. This keeps gun ammo from being consumed, including charged
shots, and allows firing with an empty pool. It applies to the supported stock
guns and their DLC variants. `g_infiniteAmmo 0` restores normal consumption;
the option has no effect with `sv_cheats 0`. Merely enabling cheats does not
enable unlimited ammo. This does not refill stored ammo or affect explosives.

## PK3 layout

Keep one definition per `.weapon` file. A PK3 is a ZIP with a `.pk3` extension.
Use lowercase paths, forward slashes and your own author/pack namespace.

```text
my_author_pulse_rifle_weapon.pk3
  ext_data/st_weapons/my_author_pulse_rifle.weapon
  models/st_dlc/my_author/pulse/view.md3
  models/st_dlc/my_author/pulse/world.glm
  models/st_dlc/my_author/pulse/...textures and supporting model files...
  gfx/st_dlc/my_author/pulse/icon.png
  effects/st_dlc/my_author/pulse/muzzle.efx
  effects/st_dlc/my_author/pulse/shot.efx
  effects/st_dlc/my_author/pulse/impact.efx
  sound/st_dlc/my_author/pulse/fire.wav
  shaders/my_author_pulse.shader
  README.txt
```

Never include stock `models/weapons2/...`, stock effect/sound replacements, game
libraries or configuration files in this PK3. Distinct asset paths are what let
the original gun and several add-ons coexist. Shaders must also have distinct
names; naming the shader file differently does not rename the shaders inside it.
Do not redistribute JKA assets. Test fixtures in this repository reference the
user's existing JKA assets without distributing them.

For character releases, keep weapons in their own Weapon PK3. The character's
standard PK3, optional Rend2 add-on, Weapon PK3 and README can share one release ZIP.

## Complete definition example

Save this as `ext_data/st_weapons/my_author_pulse_rifle.weapon`. Replace the
example asset names with your files. This is a template, not a bundled weapon.

```text
weapon {
    version 1
    id my_author_pulse_rifle
    name "Pulse Rifle"
    baseWeapon blaster

    viewModel models/st_dlc/my_author/pulse/view.md3
    worldModel models/st_dlc/my_author/pulse/world.glm
    icon gfx/st_dlc/my_author/pulse/icon

    muzzleEffect st_dlc/my_author/pulse/muzzle
    altMuzzleEffect st_dlc/my_author/pulse/alt_muzzle
    shotEffect st_dlc/my_author/pulse/shot
    altShotEffect st_dlc/my_author/pulse/alt_shot
    impactEffect st_dlc/my_author/pulse/impact
    altImpactEffect st_dlc/my_author/pulse/alt_impact
    fireSound sound/st_dlc/my_author/pulse/fire.wav
    altFireSound sound/st_dlc/my_author/pulse/alt_fire.wav
}
```

The minimum working definition contains `version`, `id`, `name`, `baseWeapon`,
`viewModel` and `worldModel`. Other fields are optional at runtime. Unknown keys,
duplicate keys, unsupported versions and invalid/traversing paths reject the
definition and log its filename. Duplicate weapon IDs reject all definitions
with that ID. A definition must fit within 8,191 bytes.

| Field | Meaning and fallback |
| --- | --- |
| `version` | Must be `1`. |
| `id` | Stable, unique, lowercase ID; 1–31 letters/digits/underscores/hyphens. Prefix with your author name. |
| `name` | Player-facing name, at most 63 bytes, quoted if it contains spaces. No color/control codes. |
| `baseWeapon` | Exactly one value from the table above. |
| `viewModel` | Required first-person MD3 model with `tag_flash`. |
| `worldModel` | Required Ghoul2 GLM gun, attached to the player's hand, with a `*flash` bolt. |
| `handsModel` | Optional first-person MD3 positioning/animation model; otherwise use the base gun's hands. Match its `tag_weapon`, frame layout and attachment offsets. |
| `icon` | Optional shader/image path without extension; otherwise use the base gun icon. |
| `muzzleEffect`, `altMuzzleEffect` | Muzzle `.efx` names relative to `effects/`, without `.efx`. Each independently falls back. |
| `shotEffect`, `altShotEffect` | Moving-projectile trail `.efx`, or beam-segment `.efx` for hitscan fire. Each independently falls back. |
| `impactEffect`, `altImpactEffect` | Impact `.efx` for both world and player impacts. Each independently falls back. |
| `fireSound`, `altFireSound` | Firing sound path; each independently falls back. |
| `projectileModel`, `altProjectileModel` | Optional MD3 projectile; otherwise inherit the base projectile model. A custom `shotEffect` replaces the stock trail/model unless you also supply this field. |

Asset values must fit within 63 bytes and contain only lowercase letters,
digits, `_`, `-`, `/` and `.`. Do not use absolute paths or `..`.

## Authoring effects and models

- Author JKA-compatible `.efx` files and include all textures, shaders and sounds
  they reference. Definition paths omit `effects/` and `.efx`; actual files include both.
- Design primary and alternate muzzle/shot/impact effects intentionally. To use
  the same effect for both, set both keys to the same path. An omitted alternate
  key inherits JKA's alternate effect, not your primary effect.
- Projectile trails are evaluated at the moving projectile position. Disruptor
  beams and concussion alternate shots use short repeated effect segments along
  their ray, approximately every 64 units, capped at 128 segments. Author short,
  inexpensive segments rather than a whole beam in each effect.
- DEMP2 alternate impact replaces the stock detonation presentation when supplied;
  its damage radius/timing remains the base gun's behavior. Charge/zoom/deflection
  presentation and incidental marks continue to use the base weapon behavior.
- A custom projectile trail suppresses the original projectile visual. Supply a
  `projectileModel` too when the projectile needs both geometry and a trail.
- Gun models must fit the base gun's existing animations. Check first person,
  third person, left-handed settings, spectators and remote players. Model
  geometry does not change hit detection or projectile launch position.
- Include the complete visible gun in `viewModel`, including its barrel. Custom
  view models do not automatically attach the stock gun's separate barrel model.
- Avoid long-lived or extremely dense effects. Test several players firing both
  modes simultaneously. Include appropriate credit and permission for every asset.

## Converting an old replacement pack

Old replacement PK3s still replace files because JKA loads by asset path. They
cannot become independent guns just by renaming the PK3.

1. Move models, textures, shader names, effects and sounds into unique paths.
2. Update every embedded model, skin, shader and effect reference to those paths.
3. Add a `.weapon` definition with a unique ID and the closest `baseWeapon`.
4. Remove every stock-path override from the new PK3.
5. Remove the old replacement PK3 from your test installation. Verify the
   original JKA gun is restored and both guns are independently selectable.

Existing third-party packs are not rewritten automatically. Two PK3s providing
the same definition filename still follow normal JKA filesystem override rules;
give definition filenames unique names as well as unique IDs.

## Release checks

Run `python tools/Check-Weapon-Pack.py path/to/your_weapon.pk3` from the repository.
The checker verifies the definition, declared files, unique namespaces and
custom-effect coverage. It does not validate embedded GLM/MD3 references, shader
contents or the appearance of effects; perform the following game checks too.
For a development pack that intentionally uses fallbacks, add `--allow-fallbacks`.

1. Install only this pack and its stated dependencies. Verify the original gun
   still looks and sounds original; cycle forward and backward through both.
2. Spawn without picking up the base gun. Confirm the add-on appears in a
   gun-enabled match, uses the existing ammo pool, and grants no free ammo.
3. Fire both modes, switch between stock and add-on, and verify ammo is shared.
   Test empty ammo, charging, death/respawn and map restart.
4. Test first/third person and a second connected client. Fire, then switch guns
   while a projectile is in flight: the projectile must keep its own effects.
5. Test omitted/missing effects: only those effects should fall back. Test a
   missing pack on a non-pure test server: other players use stock visuals.
6. Test saber-only rules, a disabled base family, private duels, spectators and
   `g_infiniteAmmo` with cheats on/off. No add-on may bypass server restrictions.
7. Run `st_weaponinfo` in the console to list the server catalogue and inspect
   the current gun's authoritative selection, ammo, models and custom effects.

Include the weapon name/version, base family, ammo behavior, installation,
controls, dependencies, credits/license and known limitations in your release
README. Tell players that both the server and clients need matching Saber Trials
weapon-DLC support and the same pack to select and see your gun.
