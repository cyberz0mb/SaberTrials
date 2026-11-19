/* Shared artwork and aspect-correct logo sizing for UI and cgame. */
#pragma once

#define ST_BRAND_LOGO "gfx/st_workbench/brand"
#define ST_BRAND_FRAME "gfx/st_workbench/frame.png"
#define ST_BRAND_GLOW "ui/assets/sabertrials/main/glow"
#define ST_BRAND_RATIO (1672.f / 941.f)

static void ST_BrandSize(float aspect, float maxWidth, float maxHeight, float *width, float *height)
{
	*width = maxWidth;
	*height = maxWidth * aspect / ST_BRAND_RATIO;
	if (*height > maxHeight) {
		*height = maxHeight;
		*width = maxHeight * ST_BRAND_RATIO / aspect;
	}
}

// Fade the source image's outer matte in the additive pass, preserving the
// original logo and its highlights. Both clients use 640x480 UI coordinates.
static void ST_DrawBrandTexture(float x, float y, float width, float height, qhandle_t logo)
{
	if (!logo)
		return;
	const float u[] = {0, .012f, .026f, .042f, .958f, .974f, .988f, 1};
	const float v[] = {0, .025f, .054f, .085f, .915f, .946f, .975f, 1};
	const float fade[] = {.10f, .38f, .74f, 1, .74f, .38f, .10f};
	for (int row = 0; row < 7; ++row)
		for (int col = 0; col < 7; ++col) {
			const float f = fade[row] * fade[col];
			const vec4_t light = {f, f, f, 1};
			trap->R_SetColor(light);
			trap->R_DrawStretchPic(x + width * u[col], y + height * v[row],
				width * (u[col + 1] - u[col]), height * (v[row + 1] - v[row]),
				u[col], v[row], u[col + 1], v[row + 1], logo);
		}
	trap->R_SetColor(NULL);
}
