/* Draw the same custom blade in the Workbench and in a match. */
static qboolean ST_DrawCrystalBlade(const vec3_t origin, const vec3_t direction, float length,
	float maxLength, float radius, int rgb, int renderFlags, qboolean addLight, qboolean whiteCore)
{
	if (length < .5f || radius <= 0)
		return qtrue;

	const qboolean black = rgb == 0 ? qtrue : qfalse;
	const char *coreShader = whiteCore ? "gfx/st_crystals/rgbWhiteCore" : "gfx/st_crystals/rgbCore";
	const qhandle_t core = trap->R_RegisterShaderNoMip(black ? "gfx/st_crystals/blackCore" : coreShader);
	const qhandle_t glow = black ? 0 : trap->R_RegisterShaderNoMip("gfx/st_crystals/rgbGlow");
	if (!core || (!black && !glow))
		return qfalse;

	const float extensionScale = length < maxLength ? 1.f + 2.f / length : 1.f;
	const float radiusJitter = radius * .075f;
	refEntity_t beam = {0};
	beam.renderfx = renderFlags;
	beam.shaderRGBA[3] = 255;
	if (!black) {
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
	beam.radius = (black ? radius * .58f :
		radius * .245f + Q_flrand(-1.f, 1.f) * radiusJitter * .48f) * extensionScale;
	beam.shaderTexCoord[0] = beam.shaderTexCoord[1] = 1;
	VectorMA(origin, length, direction, beam.origin);
	VectorMA(origin, -.65f, direction, beam.oldorigin);
	trap->R_AddRefEntityToScene(&beam);
	return qtrue;
}
