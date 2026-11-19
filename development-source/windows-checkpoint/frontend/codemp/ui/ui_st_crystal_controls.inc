/* Crystal tab for the saber workbench. */
extern int UI_SaberNumBladesForSaber(const char *saberName);
static const rectDef_t swbRgbTracks[] = {
	{441, 193, 168, 12}, {441, 233, 168, 12}, {441, 273, 168, 12}
};
static const char *const swbChannels[] = {"Red", "Green", "Blue"};
static const vec4_t swbChannelTint[] = {{1,.22f,.28f,1}, {.27f,1,.49f,1}, {.28f,.61f,1,1}};

static const struct {
	const char *name;
	int rgb;
} swbColors[] = {
	{"Blue", 0x2473FF}, {"Green", 0x26F254}, {"Orange", 0xFF7A17}, {"Purple", 0xB53DFF},
	{"Yellow", 0xFFD424}, {"Red", 0xFF2430}, {"White", 0xFFFFFF}, {"Black", 0x000000}
};

static int SWB_BladeCount()
{
	char name[MAX_QPATH];
	trap->Cvar_VariableStringBuffer(swb.second ? "ui_saber2" : "ui_saber", name, sizeof(name));
	return std::max(1, std::min(MAX_BLADES, UI_SaberNumBladesForSaber(name)));
}

static const char *SWB_PresetCvar()
{
	return swb.second ? "ui_saber2_color" : "ui_saber_color";
}

static int SWB_PresetIndex()
{
	const char *preset = UI_Cvar_VariableString(SWB_PresetCvar());
	for (int i = 0; i < 6; ++i)
		if (!Q_stricmp(preset, swbColors[i].name))
			return i;
	return 0;
}

static void SWB_CrystalDraft(int (&colors)[MAX_BLADES])
{
	char value[ST_CRYSTAL_TEXT_SIZE + 1];
	trap->Cvar_VariableStringBuffer(stCrystalDrafts[swb.second], value, sizeof(value));
	ST_CrystalParse(value, colors);
}

static int SWB_CurrentRgb()
{
	int colors[MAX_BLADES];
	SWB_CrystalDraft(colors);
	return colors[swb.blade] < 0 ? swbColors[SWB_PresetIndex()].rgb : colors[swb.blade];
}

static void SWB_StoreRgb(int rgb, bool updateFallback)
{
	int colors[MAX_BLADES];
	SWB_CrystalDraft(colors);
	colors[swb.blade] = rgb;
	char value[ST_CRYSTAL_TEXT_SIZE];
	ST_CrystalFormat(colors, value);
	trap->Cvar_Set(stCrystalDrafts[swb.second], value);

	if (updateFallback && swb.blade == 0 && rgb > 0) {
		int best = 0, distance = 3 * 255 * 255 + 1;
		for (int i = 0; i < 6; ++i) {
			int error = 0;
			for (int channel = 0; channel < 3; ++channel) {
				const int diff = ST_CrystalChannel(rgb, channel) - ST_CrystalChannel(swbColors[i].rgb, channel);
				error += diff * diff;
			}
			if (error < distance) {
				best = i;
				distance = error;
			}
		}
		char preset[8];
		Q_strncpyz(preset, swbColors[best].name, sizeof(preset));
		Q_strlwr(preset);
		trap->Cvar_Set(SWB_PresetCvar(), preset);
	}
}

static void SWB_SetPreset(int index)
{
	if (index < 6 && swb.blade == 0) {
		char preset[8];
		Q_strncpyz(preset, swbColors[index].name, sizeof(preset));
		Q_strlwr(preset);
		trap->Cvar_Set(SWB_PresetCvar(), preset);
		SWB_StoreRgb(ST_CRYSTAL_DEFAULT, false);
	} else {
		SWB_StoreRgb(swbColors[index].rgb, true);
	}
}

static void SWB_SetChannel(int channel, int value)
{
	const int shift = (2 - channel) * 8;
	const int rgb = (SWB_CurrentRgb() & ~(255 << shift)) | ((int)Com_Clamp(0, 255, value) << shift);
	SWB_StoreRgb(rgb, true);
}

static void SWB_DragChannel(int channel)
{
	const rectDef_t &track = swbRgbTracks[channel];
	const float fraction = Com_Clamp(0, 1, (uiInfo.uiDC.cursorx - track.x) / track.w);
	SWB_SetChannel(channel, (int)(255 * fraction + .5f));
}

static void SWB_TintedArt(const char *path, float x, float y, float w, float h, const vec4_t tint)
{
	const qhandle_t shader = trap->R_RegisterShaderNoMip(path);
	trap->R_SetColor(tint);
	UI_DrawHandlePic(x, y, w, h, shader);
	trap->R_SetColor(NULL);
}

static void SWB_DrawSlider(float x, float y, float w, float fraction, const vec4_t tint, bool focus)
{
	const float fill = w * fraction;
	const float aspect = uiInfo.uiDC.yscale / uiInfo.uiDC.xscale;
	const float thumb = 9.f * aspect;
	const vec4_t rim = {.26f,.42f,.49f,1}, slot = {.016f,.043f,.065f,1};
	const vec4_t shaded = {tint[0]*.36f,tint[1]*.36f,tint[2]*.36f,1};
	const vec4_t highlight = {.34f + tint[0]*.66f,.34f + tint[1]*.66f,.34f + tint[2]*.66f,1};
	vec4_t halo = {tint[0],tint[1],tint[2],focus ? .72f : .44f};

	UI_FillRect(x - 1, y - 2, w + 2, 5, rim);
	UI_FillRect(x, y - 1, w, 3, slot);
	if (fill > 0) {
		RUI_Image("glow", x, y - 5, fill, 10, halo);
		UI_FillRect(x, y - 1, fill, 3, shaded);
		UI_FillRect(x, y - 1, fill, 1, tint);
	}
	RUI_Image("glow", x + fill - 13*aspect, y - 14, 26*aspect, 28, halo);
	SWB_TintedArt("gfx/st_crystals/thumb.tga", x + fill - thumb/2, y - 8, thumb, 17, highlight);
}

static void SWB_DrawCrystalSample(float x, float y, float w, float h, int rgb, bool active)
{
	vec4_t tint;
	for (int i = 0; i < 3; ++i)
		tint[i] = ST_CrystalChannel(rgb, i) / 255.f;
	tint[3] = 1;
	const vec4_t frame = {.52f,.69f,.78f,1};
	const vec4_t halo = {tint[0],tint[1],tint[2],active ? .70f : .38f};
	RUI_Image("glow", x - 3, y - 3, w + 6, h + 6, halo);
	SWB_TintedArt("gfx/st_crystals/facet.tga", x, y, w, h, frame);
	SWB_TintedArt("gfx/st_crystals/facet.tga", x + 1, y + 1, w - 2, h - 2, tint);
}

static void SWB_DrawCrystals()
{
	const int count = SWB_BladeCount();
	if (swb.blade >= count)
		swb.blade = 0;
	const int rgb = SWB_CurrentRgb();
	if (count > 1) {
		SWB_Button({438, 134, 28, 21}, "<", SWB_Blade, -1);
		SWB_Text({470, 134, 112, 21}, va("Blade %d / %d", swb.blade + 1, count), .64f, ruWhite, true);
		SWB_Button({586, 134, 28, 21}, ">", SWB_Blade, 1);
	}
	for (int i = 0; i < 3; ++i) {
		const rectDef_t &track = swbRgbTracks[i];
		const int value = ST_CrystalChannel(rgb, i);
		const bool focus = SWB_Track({track.x - 3, track.y - 4, track.w + 6, track.h + 8}, SWB_Channel, i);
		SWB_Text({436, track.y - 24, 124, 21}, swbChannels[i], .67f, ruWhite);
		SWB_Text({574, track.y - 24, 39, 21}, va("%d", value), .65f, ruWhite, true);
		SWB_DrawSlider(track.x, track.y + 6, track.w, value / 255.f, swbChannelTint[i], focus);
	}
	const rectDef_t hex = {464, 296, 88, 25};
	SWB_DrawCrystalSample(439, 300, 18, 18, rgb, true);
	const bool hot = SWB_Track(hex, SWB_Hex);
	RUI_Control(hex.x, hex.y, hex.w, hex.h, "field", swb.hexEditing, hot);
	const char *hexLabel = swb.hexEditing ? va("#%s|", swb.hex) : va("#%06X", (unsigned)rgb);
	SWB_Text(hex, hexLabel, .65f, ruWhite, true);
	SWB_Button({556, 296, 58, 25}, "Reset", SWB_ResetRgb);
	for (int i = 0; i < 8; ++i) {
		const rectDef_t r = {437.f + (i % 4) * 45, 332.f + (i / 4) * 29, 41, 25};
		const bool focus = SWB_Track(r, SWB_Color, i);
		const bool active = rgb == swbColors[i].rgb;
		RUI_Control(r.x, r.y, r.w, r.h, "field", active, focus);
		SWB_DrawCrystalSample(r.x + 7, r.y + 3, r.w - 14, 8, swbColors[i].rgb, active || focus);
		SWB_Text({r.x, r.y + 8, r.w, 17}, swbColors[i].name, .54f, active || focus ? ruCyan : ruWhite, true);
	}
	const bool whiteCore = trap->Cvar_VariableValue(ST_WHITE_CORE_DRAFT) != 0;
	SWB_Button({437, 391, 104, 23}, whiteCore ? "White core: On" : "White core: Off", SWB_WhiteCore, 0, whiteCore);
}

static bool SWB_HexKey(int key)
{
	if (!swb.hexEditing)
		return false;
	if (key == A_ENTER || key == A_ESCAPE || key == A_JOY1) {
		swb.hexEditing = false;
		return true;
	}
	if (!(key & K_CHAR_FLAG) && key != A_BACKSPACE)
		return false;
	const int c = key & ~K_CHAR_FLAG;
	const size_t length = strlen(swb.hex);
	if (key == A_BACKSPACE || c == 8) {
		if (length)
			swb.hex[length - 1] = '\0';
	} else if (ST_CrystalHexDigit((char)c) >= 0 && length < 6) {
		swb.hex[length] = toupper((unsigned char)c);
		swb.hex[length + 1] = '\0';
		if (length == 5)
			SWB_StoreRgb(ST_CrystalParseHex(swb.hex), true);
	}
	return true;
}
