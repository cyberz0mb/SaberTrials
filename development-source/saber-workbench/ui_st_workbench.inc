/* Saber workbench. Native saber definitions, models and saved equipment. */
extern void UI_SaberDrawBlades(itemDef_t *item, vec3_t origin, vec3_t angles);

enum SWB_Action {
	SWB_Back, SWB_Apply, SWB_Cancel, SWB_Family, SWB_Editor, SWB_Slot, SWB_Search,
	SWB_Hilt, SWB_Color, SWB_Ignite, SWB_Inspect, SWB_Angle, SWB_Hand, SWB_Stances, SWB_Combat
};

static const rectDef_t swbStage = {23, 113, 401, 267};
static const rectDef_t swbScene = {23, 149, 401, 192};
static const rectDef_t swbList = {437, 165, 177, 209};
static const rectDef_t swbAngle = {321, 350, 92, 22};
static const char *const swbTypes[] = {"single", "dual", "staff"};
static const char *const swbCvars[] = {
	"ui_saber", "ui_saber2", "ui_saber_color", "ui_saber2_color", "ui_saberHand", "ui_saber_type"
};
static constexpr int swbRows = 9;

struct SWB_Control {
	rectDef_t rect;
	SWB_Action action;
	int value;
};

static struct {
	menuDef_t *menu;
	bool crystal, second, dark, searching, angleDrag, scrollDrag, child;
	int scroll, focus;
	float angle, scrollGrab;
	char query[64], saved[6][MAX_QPATH], childDraft[6][MAX_QPATH];
} swb;

static std::vector<SWB_Control> swbControls;
static std::vector<int> swbResults;
static std::vector<std::string> swbHiltTitles[2];

static int SWB_FamilyIndex()
{
	const char *type = UI_Cvar_VariableString("ui_saber_type");
	return LUI_Name(type, "staff") ? 2 : LUI_Name(type, "dual") ? 1 : 0;
}

static void SWB_Read(char (&snapshot)[6][MAX_QPATH])
{
	for (int i = 0; i < 6; ++i)
		trap->Cvar_VariableStringBuffer(swbCvars[i], snapshot[i], sizeof(snapshot[i]));
}

static void SWB_Restore(const char (&snapshot)[6][MAX_QPATH])
{
	for (int i = 0; i < 6; ++i)
		trap->Cvar_Set(swbCvars[i], snapshot[i]);
	UI_UpdateSaberHilt(qfalse);
	if (SWI_Dual())
		UI_UpdateSaberHilt(qtrue);
}

static bool SWB_Dirty()
{
	char draft[6][MAX_QPATH];
	SWB_Read(draft);
	for (int i = 0; i < 5; ++i)
		if (Q_stricmp(draft[i], swb.saved[i]))
			return true;
	return false;
}

static void SWB_Title(const char *name, char (&title)[1024])
{
	if (!UI_SaberProperNameForSaber(name, title) || !title[0])
		Q_strncpyz(title, name, sizeof(title));
	Q_CleanStr(title);
}

static void SWB_Filter()
{
	swbResults.clear();
	const auto &titles = swbHiltTitles[SWB_FamilyIndex() == 2];
	for (int i = 0; i < (int)titles.size(); ++i)
		if (!swb.query[0] || Q_stristr(titles[i].c_str(), swb.query))
			swbResults.push_back(i);
	swb.scroll = 0;
}

static void SWB_Start(menuDef_t *menu)
{
	if (swb.menu == menu && !swb.child)
		return;
	if (swb.menu == menu && swb.child) {
		SWB_Restore(swb.childDraft);
		swb.child = false;
		return;
	}

	swb = {};
	swb.menu = menu;
	swb.focus = -1;
	SWB_Read(swb.saved);
	const char *primary = swb.saved[0];
	bool staff = false;
	for (int list = 0; list < 2; ++list) {
		auto &titles = swbHiltTitles[list];
		titles.clear();
		const char *const *hilts = list ? saberStaffHiltInfo : saberSingleHiltInfo;
		for (int i = 0; i < MAX_SABER_HILTS && hilts[i]; ++i) {
			char title[1024];
			SWB_Title(hilts[i], title);
			titles.emplace_back(title);
			if (list && !Q_stricmp(hilts[i], primary))
				staff = true;
		}
	}
	const char *secondary = swb.saved[1];
	const int family = staff ? 2 : (*secondary && Q_stricmp(secondary, "none")) ? 1 : 0;
	trap->Cvar_Set("ui_saber_type", swbTypes[family]);
	Q_strncpyz(swb.saved[5], swbTypes[family], sizeof(swb.saved[5]));
	SWB_Filter();
}

static bool SWB_Track(const rectDef_t &rect, SWB_Action action, int value = 0)
{
	const bool focus = (int)swbControls.size() == swb.focus;
	swbControls.push_back({rect, action, value});
	return focus || SWI_Hover(rect);
}

static void SWB_Text(const rectDef_t &r, const char *label, float scale, const float *color, bool center = false)
{
	float width = RUI_Width(label, scale);
	if (width > r.w - 10) {
		scale *= (r.w - 10) / width;
		width = r.w - 10;
	}
	RUI_Text(center ? r.x + (r.w - width) / 2 : r.x + 5, r.y + 5, scale, label, color);
}

static void SWB_Button(const rectDef_t &r, const char *label, SWB_Action action, int value = 0, bool selected = false)
{
	const bool focus = SWB_Track(r, action, value);
	RUI_Control(r.x, r.y, r.w, r.h, "button", selected, focus);
	SWB_Text(r, label, .66f, focus || selected ? ruCyan : ruWhite, true);
}

static void SWB_DrawSaber(menuDef_t *menu, int slot, int family, float distance)
{
	itemDef_t *item = Menu_FindItemByName(menu, slot ? "saber2" : "saber");
	if (!item || (!item->ghoul2 && !item->asset) || !item->typeData.model)
		return;
	refEntity_t model = {};
	model.ghoul2 = item->ghoul2;
	model.hModel = item->asset;
	model.customSkin = item->typeData.model->g2skin;
	model.radius = 1000;
	vec3_t angles = {-7, swb.angle, 90};
	AnglesToAxis(angles, model.axis);
	VectorCopy(item->typeData.model->g2scale, model.modelScale);
	if (model.ghoul2)
		UI_ScaleModelAxis(&model);
	VectorSet(model.origin, distance, swb.dark || family == 2 ? 0 : 17,
		family == 1 ? (slot ? -7.5f : 6.5f) : -1.f);
	VectorCopy(model.origin, model.oldorigin);
	VectorCopy(model.origin, model.lightingOrigin);
	model.renderfx = RF_LIGHTING_ORIGIN | RF_NOSHADOW;
	trap->R_AddRefEntityToScene(&model);
	if (!swb.dark && model.ghoul2)
		UI_SaberDrawBlades(item, model.origin, angles);
}

static void SWB_DrawScene(menuDef_t *menu)
{
	refdef_t view = {};
	view.rdflags = RDF_NOWORLDMODEL;
	view.time = uiInfo.uiDC.realTime;
	view.x = swbScene.x * uiInfo.uiDC.xscale;
	view.y = swbScene.y * uiInfo.uiDC.yscale;
	view.width = swbScene.w * uiInfo.uiDC.xscale;
	view.height = swbScene.h * uiInfo.uiDC.yscale;
	view.fov_y = 32;
	const float tangent = tanf(view.fov_y * M_PI / 360.f) * view.width / view.height;
	view.fov_x = atan2f(tangent, 1) * (360.f / M_PI);
	AxisClear(view.viewaxis);
	const int family = SWB_FamilyIndex();
	const float distance = (swb.dark ? 28 : family == 2 ? 62 : 39) / tangent;
	trap->R_ClearScene();
	vec3_t light = {distance - 48, -18, 38};
	trap->R_AddLightToScene(light, 140, .68f, .88f, 1.f);
	VectorSet(light, distance - 25, 27, -19);
	trap->R_AddLightToScene(light, 95, 1.f, .79f, .5f);
	SWB_DrawSaber(menu, 0, family, distance);
	if (family == 1)
		SWB_DrawSaber(menu, 1, family, distance);
	trap->R_RenderScene(&view);
}

static float SWB_ThumbHeight()
{
	return Com_Clamp(18, swbList.h, swbList.h * swbRows / std::max(1, (int)swbResults.size()));
}

static int SWB_MaxScroll()
{
	return std::max(0, (int)swbResults.size() - swbRows);
}

static rectDef_t SWB_Thumb()
{
	const float h = SWB_ThumbHeight();
	const float progress = (float)swb.scroll / std::max(1, SWB_MaxScroll());
	return {611, swbList.y + (swbList.h - h) * progress, 4, h};
}

static void SWB_DrawHilts()
{
	const rectDef_t search = {438, 132, 176, 24};
	const bool focus = SWB_Track(search, SWB_Search);
	RUI_Control(search.x, search.y, search.w, search.h, "field", swb.searching, focus);
	const char *text = swb.query[0] ? swb.query : swb.searching ? "|" : "Search hilts";
	SWB_Text(search, text, .67f, swb.query[0] || swb.searching ? ruWhite : ruCyan);

	const bool staff = SWB_FamilyIndex() == 2;
	const auto &titles = swbHiltTitles[staff];
	const char *const *hilts = staff ? saberStaffHiltInfo : saberSingleHiltInfo;
	char selected[MAX_QPATH];
	trap->Cvar_VariableStringBuffer(swb.second ? "ui_saber2" : "ui_saber", selected, sizeof(selected));
	const vec4_t current = {.04f, .24f, .31f, .8f};
	const vec4_t row = {.021f, .061f, .085f, .57f};
	if (swbResults.empty())
		SWB_Text({437, 170, 170, 23}, "No matching hilts", .65f, ruWhite);
	for (int i = 0; i < swbRows && i + swb.scroll < (int)swbResults.size(); ++i) {
		const int index = swbResults[i + swb.scroll];
		const rectDef_t r = {437, swbList.y + i * 23, 167, 21};
		const bool hot = SWB_Track(r, SWB_Hilt, index);
		const bool active = !Q_stricmp(selected, hilts[index]);
		if (active || (i % 2))
			UI_FillRect(r.x, r.y, r.w, r.h, active ? current : row);
		SWB_Text(r, titles[index].c_str(), .64f, hot || active ? ruCyan : ruWhite);
	}
	if (SWB_MaxScroll()) {
		const rectDef_t thumb = SWB_Thumb();
		UI_FillRect(612, swbList.y, 2, swbList.h, current);
		UI_FillRect(thumb.x, thumb.y, thumb.w, thumb.h, ruCyan);
	}
}

static const struct {
	const char *name;
	vec4_t rgb;
} swbColors[] = {
	{"blue", {.14f, .45f, 1.f, 1.f}}, {"green", {.15f, .95f, .33f, 1.f}},
	{"orange", {1.f, .48f, .09f, 1.f}}, {"purple", {.71f, .24f, 1.f, 1.f}},
	{"yellow", {1.f, .83f, .14f, 1.f}}, {"red", {1.f, .14f, .19f, 1.f}}
};

static void SWB_DrawCrystals()
{
	const char *color = UI_Cvar_VariableString(swb.second ? "ui_saber2_color" : "ui_saber_color");
	for (int i = 0; i < 6; ++i) {
		const rectDef_t r = {440.f + (i % 3) * 56, 149.f + (i / 3) * 54, 48, 44};
		const bool focus = SWB_Track(r, SWB_Color, i);
		const bool active = LUI_Name(color, swbColors[i].name);
		RUI_Control(r.x, r.y, r.w, r.h, "field", active, focus);
		const vec4_t &rgb = swbColors[i].rgb;
		UI_FillRect(r.x + 11, r.y + 10, 26, 8, rgb);
		char name[8];
		Q_strncpyz(name, swbColors[i].name, sizeof(name));
		name[0] = toupper((unsigned char)name[0]);
		SWB_Text({r.x, r.y + 20, r.w, 20}, name, .57f, active || focus ? ruCyan : ruWhite, true);
	}
}

static bool SWB_Paint()
{
	menuDef_t *menu = Menu_GetFocused();
	if (!SWI_Menu(menu)) {
		if (!swb.child)
			swb.menu = NULL;
		return false;
	}
	SWB_Start(menu);
	swbControls.clear();
	const vec4_t solid = {.009f, .024f, .039f, 1.f};
	const vec4_t shade = {.003f, .013f, .021f, .80f};
	UI_FillRect(0, 0, 640, 480, RUI_Connected() ? shade : solid);
	LUI_Frame();

	SWB_Text({150, 29, 340, 31}, "Saber workbench", 1.25f, ruCyan, true);
	SWB_Button({24, 34, 83, 23}, "< Profile", SWB_Back);
	RUI_Divider(23, 72, 594);
	const int family = SWB_FamilyIndex();
	SWB_Button({23, 81, 71, 24}, "Single", SWB_Family, 0, family == 0);
	SWB_Button({100, 81, 94, 24}, "Dual sabers", SWB_Family, 1, family == 1);
	SWB_Button({200, 81, 66, 24}, "Staff", SWB_Family, 2, family == 2);

	SMUI_Image("gfx/st_workbench/bench.png", swbStage.x, swbStage.y, swbStage.w, swbStage.h);
	_UI_DrawRect(swbStage.x, swbStage.y, swbStage.w, swbStage.h, .65f, ruCyan);
	if (!SWI_Active(menu))
		SWB_DrawScene(menu);
	SWB_Button({33, 348, 81, 23}, swb.dark ? "Blade off" : "Blade on", SWB_Ignite);
	SWB_Button({119, 348, 88, 23}, "Inspect hilt", SWB_Inspect);
	SWB_Text({267, 348, 51, 23}, "Angle", .65f, ruWhite);
	const bool angleFocus = SWB_Track(swbAngle, SWB_Angle);
	UI_FillRect(323, 359, 86, 2, ruWhite);
	UI_FillRect(322 + 86 * (swb.angle + 25) / 50.f, 354, 6, 12, angleFocus ? ruCyan : ruGold);

	SWB_Button({437, 81, 82, 24}, "Hilt", SWB_Editor, 0, !swb.crystal);
	SWB_Button({525, 81, 89, 24}, "Crystal", SWB_Editor, 1, swb.crystal);
	if (family == 1) {
		SWB_Button({437, 107, 82, 21}, "Saber 1", SWB_Slot, 0, !swb.second);
		SWB_Button({525, 107, 89, 21}, "Saber 2", SWB_Slot, 1, swb.second);
	}
	if (swb.crystal)
		SWB_DrawCrystals();
	else
		SWB_DrawHilts();

	const bool left = trap->Cvar_VariableValue("ui_saberHand") == 1;
	SWB_Button({23, 391, 133, 23}, left ? "Left hand" : "Right hand", SWB_Hand);
	SWB_Button({163, 391, 78, 23}, "Stances", SWB_Stances);
	SWB_Button({248, 391, 129, 23}, "Combat styles", SWB_Combat);
	RUI_Divider(23, 426, 594);
	if (SWB_Dirty()) {
		SWB_Text({23, 437, 149, 24}, "Pending changes", .67f, ruGold);
		SWB_Button({388, 435, 126, 26}, "Cancel changes", SWB_Cancel);
	}
	SWB_Button({527, 435, 87, 26}, "Apply", SWB_Apply, 0, true);
	return true;
}

static void SWB_Return(menuDef_t *menu, bool apply)
{
	if (apply)
		UI_UpdateSaberCvars();
	else
		SWB_Restore(swb.saved);
	const bool game = LUI_Name(menu->window.name, "ingame_saber");
	Menus_CloseByName(menu->window.name);
	Menus_ActivateByName(game ? "ingame_player" : "playerMenu");
	swb = {};
}

static void SWB_ChangeFamily(int family)
{
	const int previous = SWB_FamilyIndex();
	if (previous == family)
		return;
	trap->Cvar_Set("ui_saber_type", swbTypes[family]);
	if (previous == 2 || family == 2) {
		trap->Cvar_Set("ui_saber", family == 2 ? DEFAULT_SABER_STAFF : DEFAULT_SABER);
		UI_UpdateSaberHilt(qfalse);
	}
	trap->Cvar_Set("ui_saber2", family == 1 ? DEFAULT_SABER : "");
	if (family == 1)
		UI_UpdateSaberHilt(qtrue);
	swb.second = false;
	SWB_Filter();
}

static void SWB_SetAngle()
{
	swb.angle = -25 + 50 * Com_Clamp(0, 1, (uiInfo.uiDC.cursorx - 323) / 86.f);
}

static void SWB_Activate(menuDef_t *menu, const SWB_Control &control)
{
	swb.searching = false;
	switch (control.action) {
	case SWB_Back: SWB_Return(menu, false); break;
	case SWB_Apply: SWB_Return(menu, true); break;
	case SWB_Cancel: SWB_Restore(swb.saved); swb.second = false; SWB_Filter(); break;
	case SWB_Family: SWB_ChangeFamily(control.value); break;
	case SWB_Editor: swb.crystal = control.value != 0; break;
	case SWB_Slot: swb.second = control.value != 0; break;
	case SWB_Search: swb.searching = true; break;
	case SWB_Hilt: {
		const bool staff = SWB_FamilyIndex() == 2;
		const char *name = staff ? saberStaffHiltInfo[control.value] : saberSingleHiltInfo[control.value];
		trap->Cvar_Set(swb.second ? "ui_saber2" : "ui_saber", name);
		UI_UpdateSaberHilt(swb.second ? qtrue : qfalse);
		break;
	}
	case SWB_Color:
		trap->Cvar_Set(swb.second ? "ui_saber2_color" : "ui_saber_color", swbColors[control.value].name);
		break;
	case SWB_Ignite: swb.dark = !swb.dark; break;
	case SWB_Inspect: swb.dark = false; swi.menu = menu; swi.second = swb.second; SWI_ResetView(); break;
	case SWB_Angle: swb.angle = swb.angle >= 25 ? -25 : std::min(25.f, swb.angle + 5.f); break;
	case SWB_Hand:
		trap->Cvar_Set("ui_saberHand", trap->Cvar_VariableValue("ui_saberHand") == 1 ? "0" : "1");
		break;
	case SWB_Stances:
	case SWB_Combat: {
		const bool game = LUI_Name(menu->window.name, "ingame_saber");
		SWB_Read(swb.childDraft);
		swb.child = true;
		Menus_CloseByName(menu->window.name);
		if (control.action == SWB_Stances)
			ST_UIStanceScript(game ? "stStanceOpenGame" : "stStanceOpenMain");
		else
			ST_UIHybridScript(game ? "stHybridOpenGame" : "stHybridOpenMain");
		break;
	}
	}
}

static bool SWB_Mouse()
{
	if (!SWI_Menu(Menu_GetFocused()))
		return false;
	if (swb.angleDrag)
		SWB_SetAngle();
	if (swb.scrollDrag) {
		const float travel = swbList.h - SWB_ThumbHeight();
		const float p = Com_Clamp(0, 1, (uiInfo.uiDC.cursory - swbList.y - swb.scrollGrab) / std::max(1.f, travel));
		swb.scroll = (int)(p * SWB_MaxScroll() + .5f);
	}
	return true;
}

static bool SWB_Key(int key, qboolean down)
{
	menuDef_t *menu = Menu_GetFocused();
	if (!SWI_Menu(menu))
		return false;
	if (!down) {
		if (key == A_MOUSE1)
			swb.angleDrag = swb.scrollDrag = false;
		return true;
	}
	SWB_Start(menu);
	if (key == A_ESCAPE || key == A_JOY1) {
		if (swb.searching)
			swb.searching = false;
		else
			SWB_Return(menu, false);
	} else if (key == A_JOY3) {
		SWB_Activate(menu, {{}, SWB_Inspect, 0});
	} else if (swb.searching && ((key & K_CHAR_FLAG) || key == A_BACKSPACE)) {
		const int c = key & ~K_CHAR_FLAG;
		const size_t length = strlen(swb.query);
		if (key == A_BACKSPACE || c == 8) {
			if (length)
				swb.query[length - 1] = '\0';
		} else if (c >= 32 && c < 127 && length + 1 < sizeof(swb.query)) {
			swb.query[length] = (char)c;
			swb.query[length + 1] = '\0';
		}
		SWB_Filter();
	} else if (key == A_MOUSE1) {
		swb.searching = false;
		if (!swb.crystal && SWB_MaxScroll() && SWI_Hover({607, swbList.y, 11, swbList.h})) {
			const rectDef_t thumb = SWB_Thumb();
			swb.scrollGrab = SWI_Hover(thumb) ? uiInfo.uiDC.cursory - thumb.y : thumb.h / 2;
			swb.scrollDrag = true;
			SWB_Mouse();
		} else {
			for (const auto &control : swbControls)
				if (SWI_Hover(control.rect)) {
					swb.focus = -1;
					if (control.action == SWB_Angle) {
						swb.angleDrag = true;
						SWB_SetAngle();
					} else
						SWB_Activate(menu, control);
					break;
				}
		}
	} else if (!swb.crystal && (key == A_MWHEELUP || key == A_MWHEELDOWN ||
		key == A_PAGE_UP || key == A_PAGE_DOWN)) {
		const int step = key == A_MWHEELUP ? -2 : key == A_MWHEELDOWN ? 2 : key == A_PAGE_UP ? -swbRows : swbRows;
		swb.scroll = std::max(0, std::min(swb.scroll + step, SWB_MaxScroll()));
	} else if ((key == A_ENTER || key == A_JOY0) && swb.searching) {
		swb.searching = false;
	} else if ((key == A_ENTER || key == A_JOY0) && swb.focus >= 0 && swb.focus < (int)swbControls.size()) {
		SWB_Activate(menu, swbControls[swb.focus]);
	} else if (key == A_TAB || key == A_CURSOR_UP || key == A_CURSOR_DOWN || key == A_JOY11 || key == A_JOY12) {
		const int count = (int)swbControls.size();
		const bool back = key == A_CURSOR_UP || key == A_JOY11 || (key == A_TAB && trap->Key_IsDown(A_SHIFT));
		if (count)
			swb.focus = (swb.focus < 0 && back) ? count - 1 : (swb.focus + count + (back ? -1 : 1)) % count;
		swb.searching = false;
	}
	return true;
}

