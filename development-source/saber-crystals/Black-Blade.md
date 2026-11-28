# Rounded black crystal blade

The original black path used an oversized `RT_LINE` camera-facing rectangle
and a texture with a permanently baked white border. It ignored White Core,
produced a broad flat center, and stretched the tip along the blade.

Black crystals now use an original closed MD3 mesh with a circular cross-section
and rounded tip. It is 114 vertices / 224 triangles, scaled from the existing
blade radius and exact animated blade length. One native model entity draws the
body, preserving scene depth/occlusion and camera render flags. The opaque body
does not use forced post-processing or cast an extra stencil shadow.

- **White Core off:** one opaque unlit RGB 0/0/0 body. No rim, glow shell or light
  is submitted for the black blade.
- **White Core on:** thin back-facing shells provide a narrow white energy edge
  with a faint outer halo. The opaque body's depth keeps that edge outside the
  black center instead of painting over it.

The same implementation is included by the Workbench and the match renderer,
including staff and dual-saber blades. Existing White Core draft/apply/cancel
behavior is retained. Other RGB colors retain their approved width, glow,
core shaders, masks and white-center behavior.

`black_blade.py` generates the model using the MD3 structures in OpenJK's
`codemp/qcommon/qfiles.h`. Clockwise triangle winding matches stock JKA MD3s;
generation checks offsets, index bounds and nondegenerate quantized faces.
It uses no stock model geometry or textures.

`tools/Build-Black-Sabers.py` stages on the installed Profile/uniform frontend,
compiles only UI/cgame, and updates the existing crystal PK3. All previous
texture entries are byte-preserved; only its shader gains the new materials,
plus the original mesh. The install is transactional and preserves the current
combat/team/game modules, client engine, other assets and saved cfgs. No game
is launched: gameplay and appearance acceptance are reserved for the user.

Build/check/install commands are `python tools/Build-Black-Sabers.py build`,
`check`, and `install` (after one initial `prepare`). The native scene-submission
contract reproduces the legacy border with White Core off, checks the new
toggle, camera/depth flags, blade size/tip and missing-model fallback, and
compares 42 colored-blade cases against the installed baseline. Those checks
and archive integrity passed; neither gameplay nor final pixels were tested.
The combined installed receipt is `dist/black-sabers-install.json`.
