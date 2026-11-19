#include "st_brand.h"

static void ST_DrawBrand(float center, float y, float maxWidth, float maxHeight, float scale)
{
	const char *wordmark = "S T A R   W A R S";
	RUI_Text(center - RUI_Width(wordmark, scale) / 2, y, scale, wordmark, ruWhite);
	float width, height;
	ST_BrandSize(uiInfo.uiDC.xscale / uiInfo.uiDC.yscale, maxWidth, maxHeight, &width, &height);
	const qhandle_t logo = trap->R_RegisterShaderNoMip(ST_BRAND_LOGO);
	ST_DrawBrandTexture(center - width / 2, y + 18, width, height, logo);
}
