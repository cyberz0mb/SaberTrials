# Block, Parry and Feint

Open **Controls → Key Bindings → Combat** to assign Block and Feint.
Hold Block to guard while moving and aiming. With Trials active defense enabled,
tap Attack near incoming melee contact to parry. Tap Feint during an eligible
single-saber wind-up. A successful feint has a 200 ms recovery.

| Server setting | Default | Behavior |
| --- | --- | --- |
| `g_manualBlocking` | `1` | `0` automatic and Walk guard, `1` combined, `2` manual only |
| `st_attackParry` | `1` | Attack-timed parry at melee contact |
| `st_attackParryWindow` | `150` | Parry window in milliseconds |
| `g_directionalFeints` | `1` | Enable directional feints |

Blocking mode and the parry and feint switches apply on map restart.
Use matching client and server gameplay modules. The source overlay is in
`development-source/combat-controls/`.
