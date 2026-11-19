/* Native level loading presentation, using the actual map and load stages. */
#include "st_brand.h"
#include "ui/menudef.h"

static void ST_LoadText(float x, float y, float scale, float maxWidth, vec4_t color,
	const char *text, int font)
{
	float width = CG_Text_Width(text, scale, font);
	if (width > maxWidth)
		scale *= maxWidth / width;
	CG_Text_Paint(x, y, scale, color, text, 0, 0, ITEM_TEXTSTYLE_OUTLINED, font);
}

static int ST_LoadCvarInt(const char *name)
{
	char value[16];
	trap->Cvar_VariableStringBuffer(name, value, sizeof(value));
	return atoi(value);
}

static void ST_LoadFrame()
{
	CG_DrawPic(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, trap->R_RegisterShaderNoMip("ui/assets/sabertrials/rollout/frame"));
	if (!ST_LoadCvarInt("st_menuMotion"))
		return;

	const qhandle_t glow = trap->R_RegisterShaderNoMip(ST_BRAND_GLOW);
	const float ratio = cgs.screenYScale / cgs.screenXScale;
	const float perimeter = 2 * (620 / ratio + 460);
	for (int head = 0; head < 3; ++head) {
		for (int tail = 12; tail >= 0; --tail) {
			float phase = (trap->Milliseconds() % 11000) / 11000.f + head / 3.f - tail * .0016f;
			float distance = (phase - floorf(phase)) * perimeter;
			const float horizontal = 620 / ratio;
			float x, y;
			if (distance < horizontal) {
				x = 10 + distance * ratio;
				y = 10;
			} else if ((distance -= horizontal) < 460) {
				x = 630;
				y = 10 + distance;
			} else if ((distance -= 460) < horizontal) {
				x = 630 - distance * ratio;
				y = 470;
			} else {
				x = 10;
				y = 470 - (distance - horizontal);
			}
			const float opacity = 1.f - tail / 13.f;
			vec4_t cyan = {.16f, .83f, 1.f, opacity * .72f};
			trap->R_SetColor(cyan);
			CG_DrawPic(x - 6 * ratio, y - 6, 12 * ratio, 12, glow);
		}
	}
	trap->R_SetColor(NULL);
}

void CG_DrawInformation(void)
{
	const char *info = CG_ConfigString(CS_SERVERINFO);
	const char *system = CG_ConfigString(CS_SYSTEMINFO);
	const char *map = Info_ValueForKey(info, "mapname");
	char mapTitle[256];
	Q_strncpyz(mapTitle, CG_ConfigString(CS_MESSAGE), sizeof(mapTitle));
	Q_CleanStr(mapTitle);
	if (!mapTitle[0])
		Q_strncpyz(mapTitle, map, sizeof(mapTitle));

	qhandle_t levelshot = trap->R_RegisterShaderNoMip(va("levelshots/%s", map));
	if (!levelshot)
		levelshot = trap->R_RegisterShaderNoMip("menu/art/unknownmap_mp");
	CG_DrawPic(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, levelshot);
	const vec4_t baseShade = {.004f, .016f, .03f, .27f};
	CG_FillRect(0, 0, 640, 480, baseShade);
	for (int i = 0; i < 40; ++i) {
		const float t = i / 39.f;
		const vec4_t shade = {.003f, .012f, .023f, .76f * t * t};
		CG_FillRect(0, 240 + i * 6, 640, 6, shade);
	}
	ST_LoadFrame();

	vec4_t silver = {.82f, .94f, 1.f, 1.f};
	vec4_t cyan = {.19f, .84f, 1.f, 1.f};
	vec4_t muted = {.67f, .8f, .88f, 1.f};
	const float aspect = cgs.screenXScale / cgs.screenYScale;
	float logoW, logoH;
	ST_BrandSize(aspect, 157, 112, &logoW, &logoH);
	const char *wordmark = "S T A R   W A R S";
	ST_LoadText(26 + (logoW - CG_Text_Width(wordmark, .68f, FONT_SMALL2)) / 2,
		25, .68f, logoW, silver, wordmark, FONT_SMALL2);
	const qhandle_t logo = trap->R_RegisterShaderNoMip(ST_BRAND_LOGO);
	ST_DrawBrandTexture(26, 37, logoW, logoH, logo);

	ST_LoadText(32, 331, .82f, 410, cyan, BG_GetGametypeString(cgs.gametype), FONT_SMALL2);
	ST_LoadText(30, 359, 1.72f, 566, silver, mapTitle, FONT_LARGE);
	const vec4_t rail = {.17f, .40f, .48f, .72f};
	CG_FillRect(32, 408, 576, .85f, rail);
	if (cg.loadLCARSStage > 0)
		CG_FillRect(32, 408, 576 * Com_Clamp(0, 1, cg.loadLCARSStage / 9.f), 1.2f, cyan);

	const char *status = cg.infoScreenText[0] ?
		va(CG_GetStringEdString("MENUS", "LOADING_MAPNAME"), cg.infoScreenText) :
		CG_GetStringEdString("MENUS", "AWAITING_SNAPSHOT");
	ST_LoadText(32, 415, .75f, 555, silver, status, FONT_SMALL2);

	if (atoi(Info_ValueForKey(system, "sv_cheats"))) {
		ST_LoadText(32, 436, .65f, 560, muted,
			CG_GetStringEdString("MP_INGAME", "CHEATSAREENABLED"), FONT_SMALL2);
	} else if (!ST_LoadCvarInt("sv_running")) {
		char message[1024];
		const char *motd = CG_ConfigString(CS_MOTD);
		Q_strncpyz(message, motd[0] ? motd : Info_ValueForKey(info, "sv_hostname"), sizeof(message));
		Q_CleanStr(message);
		ST_LoadText(32, 436, .65f, 560, muted, message, FONT_SMALL2);
	}
}



