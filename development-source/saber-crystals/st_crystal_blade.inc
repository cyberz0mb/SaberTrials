/* Draw the same custom blade in the Workbench and in a match. */
static qboolean ST_DrawBlackCrystalBlade(const vec3_t origin, const vec3_t direction,
	float length, float radius, int renderFlags, qboolean whiteCore)
{
	const qhandle_t model = trap->R_RegisterModel("models/st_crystals/black_blade.md3");
	const qhandle_t material = trap->R_RegisterShaderNoMip("gfx/st_crystals/blackVolume");
	if (!model || !material)
		return qfalse;
	vec3_t forward, right, up;
	VectorCopy(direction, forward);
	if (VectorNormalize(forward) < .001f)
		return qtrue;
	PerpendicularVector(right, forward);
	CrossProduct(forward, right, up);

	// A real round cross-section replaces the oversized camera-facing strip.
	// The mesh is one unit in radius and 40 units long, with a rounded tip.
	const float width = radius * .32f;
	const float bladeLength = length + .3f;
	refEntity_t body = {0};
	body.reType = RT_MODEL;
	body.hModel = model;
	body.customShader = material;
	// Opaque depth must exist before the optional rim's transparent pass.
	body.renderfx = (renderFlags & ~RF_FORCEPOST) | RF_NOSHADOW;
	body.nonNormalizedAxes = qtrue;
	body.shaderRGBA[3] = 255;
	VectorMA(origin, -.3f, forward, body.origin);
	VectorCopy(body.origin, body.oldorigin);
	VectorScale(right, width, body.axis[0]);
	VectorScale(up, width, body.axis[1]);
	VectorScale(forward, bladeLength / 40.f, body.axis[2]);
	trap->R_AddRefEntityToScene(&body);

	// Off means only the opaque RGB 0/0/0 volume: no white geometry or glow.
	if (!whiteCore)
		return qtrue;
	const qhandle_t edge = trap->R_RegisterShaderNoMip("gfx/st_crystals/blackEdge");
	if (!edge)
		return qtrue;
	// Back-facing shells sit behind the depth-writing body. Only a narrow
	// silhouette remains visible; the white cannot wash over the black center.
	const float scales[] = {1.36f, 1.10f};
	const byte opacity[] = {36, 230};
	for (int layer = 0; layer < 2; ++layer) {
		refEntity_t halo = body;
		const float extension = width * (scales[layer] - 1.f);
		halo.customShader = edge;
		halo.shaderRGBA[0] = halo.shaderRGBA[1] = halo.shaderRGBA[2] = 255;
		halo.shaderRGBA[3] = opacity[layer];
		VectorMA(body.origin, -extension, forward, halo.origin);
		VectorCopy(halo.origin, halo.oldorigin);
		VectorScale(right, width * scales[layer], halo.axis[0]);
		VectorScale(up, width * scales[layer], halo.axis[1]);
		VectorScale(forward, (bladeLength + 2.f * extension) / 40.f, halo.axis[2]);
		trap->R_AddRefEntityToScene(&halo);
	}
	return qtrue;
}

static qboolean ST_DrawCrystalBlade(const vec3_t origin, const vec3_t direction, float length,
	float maxLength, float radius, int rgb, int renderFlags, qboolean addLight, qboolean whiteCore)
{
	if (length < .5f || radius <= 0)
		return qtrue;

	if (rgb == 0)
		return ST_DrawBlackCrystalBlade(origin, direction, length, radius, renderFlags, whiteCore);
	const char *coreShader = whiteCore ? "gfx/st_crystals/rgbWhiteCore" : "gfx/st_crystals/rgbCore";
	const qhandle_t core = trap->R_RegisterShaderNoMip(coreShader);
	const qhandle_t glow = trap->R_RegisterShaderNoMip("gfx/st_crystals/rgbGlow");
	if (!core || !glow)
		return qfalse;

	const float extensionScale = length < maxLength ? 1.f + 2.f / length : 1.f;
	const float radiusJitter = radius * .075f;
	refEntity_t beam = {0};
	beam.renderfx = renderFlags;
	beam.shaderRGBA[3] = 255;
	{
		beam.reType = RT_SABER_GLOW;
		beam.customShader = glow;
		beam.saberLength = length;
		beam.radius = (radius - radiusJitter + Q_flrand(-1.f, 1.f) * radiusJitter) * extensionScale;
		VectorCopy(origin, beam.origin);
		VectorCopy(direction, beam.axis[0]);
		for (int i = 0; i < 3; ++i)
			beam.shaderRGBA[i] = ST_CrystalChannel(rgb, i);
		trap->R_AddRefEntityToScene(&beam);

		if (addLight) {
			vec3_t midpoint;
			VectorMA(origin, length * .5f, direction, midpoint);
			trap->R_AddLightToScene(midpoint, length * 1.4f,
				beam.shaderRGBA[0] / 255.f, beam.shaderRGBA[1] / 255.f, beam.shaderRGBA[2] / 255.f);
		}

		// Lift the core toward the brightest selected channel. An absolute white
		// floor would wash out saturated colors and make dark crystals look pale.
		int peak = 0;
		for (int i = 0; i < 3; ++i)
			if (beam.shaderRGBA[i] > peak)
				peak = beam.shaderRGBA[i];
		for (int i = 0; i < 3; ++i)
			beam.shaderRGBA[i] += (peak - beam.shaderRGBA[i]) * 18 / 100;
	}
	beam.reType = RT_LINE;
	beam.customShader = core;
	beam.radius = (radius * .245f + Q_flrand(-1.f, 1.f) * radiusJitter * .48f) * extensionScale;
	beam.shaderTexCoord[0] = beam.shaderTexCoord[1] = 1;
	VectorMA(origin, length, direction, beam.origin);
	VectorMA(origin, -.65f, direction, beam.oldorigin);
	trap->R_AddRefEntityToScene(&beam);
	return qtrue;
}
