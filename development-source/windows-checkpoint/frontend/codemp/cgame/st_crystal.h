/* Optional crystal colors in userinfo and player configstrings.
 * Each blade is six hex digits or a dash to inherit the saber's preset.
 */
#pragma once

#define ST_CRYSTAL_DEFAULT (-1)
#define ST_CRYSTAL_TEXT_SIZE (MAX_BLADES * 7)
static const char *const stCrystalCvars[] = {"st_crystal1", "st_crystal2"};
static const char *const stCrystalDrafts[] = {"ui_st_crystal1", "ui_st_crystal2"};
static const char *const stCrystalKeys[] = {"cr1", "cr2"};

#define ST_WHITE_CORE_CVAR "cg_crystalWhiteCore"
#define ST_WHITE_CORE_DRAFT "ui_st_crystalWhiteCore"

static int ST_CrystalHexDigit(char c)
{
	if (c >= '0' && c <= '9') return c - '0';
	if (c >= 'a' && c <= 'f') return c - 'a' + 10;
	if (c >= 'A' && c <= 'F') return c - 'A' + 10;
	return -1;
}

static int ST_CrystalParseHex(const char *text)
{
	int rgb = 0;
	for (int i = 0; i < 6; ++i) {
		const int digit = ST_CrystalHexDigit(text[i]);
		if (digit < 0) return ST_CRYSTAL_DEFAULT;
		rgb = (rgb << 4) | digit;
	}
	return rgb;
}

static qboolean ST_CrystalParse(const char *text, int colors[MAX_BLADES])
{
	int parsed[MAX_BLADES];
	for (int i = 0; i < MAX_BLADES; ++i)
		colors[i] = parsed[i] = ST_CRYSTAL_DEFAULT;

	for (int blade = 0; *text; ++blade) {
		if (blade == MAX_BLADES) return qfalse;
		if (*text == '-') {
			++text;
		} else {
			const int rgb = ST_CrystalParseHex(text);
			if (rgb < 0) return qfalse;
			parsed[blade] = rgb;
			text += 6;
		}
		if (!*text) break;
		if (*text++ != ',' || !*text) return qfalse;
	}

	for (int i = 0; i < MAX_BLADES; ++i)
		colors[i] = parsed[i];
	return qtrue;
}

static void ST_CrystalFormat(const int colors[MAX_BLADES], char text[ST_CRYSTAL_TEXT_SIZE])
{
	int count = MAX_BLADES;
	while (count > 0 && colors[count - 1] == ST_CRYSTAL_DEFAULT)
		--count;
	text[0] = '\0';
	for (int i = 0; i < count; ++i) {
		const int used = strlen(text);
		if (colors[i] == ST_CRYSTAL_DEFAULT)
			Com_sprintf(text + used, ST_CRYSTAL_TEXT_SIZE - used, "%s-", i ? "," : "");
		else
			Com_sprintf(text + used, ST_CRYSTAL_TEXT_SIZE - used, "%s%06X", i ? "," : "", (unsigned)colors[i]);
	}
}

static int ST_CrystalChannel(int rgb, int channel)
{
	return (rgb >> ((2 - channel) * 8)) & 255;
}
