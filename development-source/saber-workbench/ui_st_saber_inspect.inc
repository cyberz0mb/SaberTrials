/* Hilt inspection for the front-end and pause-menu saber editors. */
extern qboolean Rect_ContainsPoint(rectDef_t *rect, float x, float y);
extern void UI_ScaleModelAxis(refEntity_t *ent);

static const rectDef_t swiViewport = {122, 112, 396, 244};
static const rectDef_t swiBack = {123, 378, 111, 24};
static const rectDef_t swiReset = {269, 378, 102, 24};
static const rectDef_t swiOther = {400, 378, 117, 24};

static struct {
	menuDef_t *menu;
	bool second, dragging;
	float yaw, pitch, distance;
} swi;

static bool SWI_Menu(const menuDef_t *menu)
{
	const char *name = menu ? menu->window.name : NULL;
	return LUI_Name(name, "saberMenu") || LUI_Name(name, "ingame_saber");
}

static bool SWI_Active(const menuDef_t *menu)
{
	if (swi.menu && (swi.menu != menu || !(trap->Key_GetCatcher() & KEYCATCH_UI)))
		swi = {};
	return swi.menu != NULL;
}

qboolean ST_SaberInspectHidesModel(const itemDef_t *item)
{
	return item->parent == swi.menu && SWI_Active(Menu_GetFocused()) &&
		(item->flags & ITF_ISANYSABER) && !(item->flags & ITF_ISCHARACTER) ? qtrue : qfalse;
}

static bool SWI_Dual()
{
	return !Q_stricmp(UI_Cvar_VariableString("ui_saber_type"), "dual");
}

static bool SWI_Hover(rectDef_t rect)
{
	return Rect_ContainsPoint(&rect, uiInfo.uiDC.cursorx, uiInfo.uiDC.cursory);
}

static rectDef_t SWI_Entry(const menuDef_t *menu)
{
	return LUI_Name(menu->window.name, "ingame_saber")
		? rectDef_t{442, 373, 76, 23}
		: rectDef_t{524, 391, 90, 23};
}

static void SWI_ResetView()
{
	swi.yaw = 0;
	swi.pitch = -12;
	swi.distance = 27;
}

static void SWI_Orbit(float x, float y)
{
	swi.yaw = fmodf(swi.yaw + x, 360.f);
	swi.pitch = fmodf(swi.pitch + y, 360.f);
}

static void SWI_Zoom(float amount)
{
	swi.distance = Com_Clamp(8.f, 100.f, swi.distance * expf(amount));
}

static void SWI_Action(const rectDef_t &rect, const char *label)
{
	const bool hover = SWI_Hover(rect);
	RUI_Control(rect.x, rect.y, rect.w, rect.h, "button", false, hover);
	const float scale = .65f;
	RUI_Text(rect.x + (rect.w - RUI_Width(label, scale)) / 2,
		rect.y + 6, scale, label, hover ? ruCyan : ruWhite);
}

static bool SWI_DrawHilt(const itemDef_t *item)
{
	if (!item || (!item->ghoul2 && !item->asset) || !item->typeData.model)
		return false;

	refdef_t view = {};
	view.rdflags = RDF_NOWORLDMODEL;
	view.time = uiInfo.uiDC.realTime;
	view.x = swiViewport.x * uiInfo.uiDC.xscale;
	view.y = swiViewport.y * uiInfo.uiDC.yscale;
	view.width = swiViewport.w * uiInfo.uiDC.xscale;
	view.height = swiViewport.h * uiInfo.uiDC.yscale;
	view.fov_y = 35;
	view.fov_x = atan2f(view.width, view.height / tanf(view.fov_y * M_PI / 360.f)) * (360.f / M_PI);
	AxisClear(view.viewaxis);

	refEntity_t hilt = {};
	hilt.ghoul2 = item->ghoul2;
	hilt.hModel = item->asset;
	hilt.customSkin = item->typeData.model->g2skin;
	hilt.radius = 1000;
	const vec3_t angles = {swi.pitch, swi.yaw, 90};
	AnglesToAxis(angles, hilt.axis);
	VectorCopy(item->typeData.model->g2scale, hilt.modelScale);
	if (hilt.ghoul2)
		UI_ScaleModelAxis(&hilt);
	VectorSet(hilt.origin, swi.distance, 0, 0);
	if (!hilt.ghoul2) {
		vec3_t mins, maxs;
		trap->R_ModelBounds(hilt.hModel, mins, maxs);
		for (int i = 0; i < 3; ++i)
			VectorMA(hilt.origin, -.5f * (mins[i] + maxs[i]), hilt.axis[i], hilt.origin);
	}
	VectorCopy(hilt.origin, hilt.oldorigin);
	VectorCopy(hilt.origin, hilt.lightingOrigin);
	hilt.renderfx = RF_LIGHTING_ORIGIN | RF_NOSHADOW;

	trap->R_ClearScene();
	vec3_t light = {swi.distance - 22, -35, 33};
	trap->R_AddLightToScene(light, 100, .92f, .98f, 1.f);
	VectorSet(light, swi.distance - 14, 34, -22);
	trap->R_AddLightToScene(light, 65, .65f, .82f, 1.f);
	trap->R_AddRefEntityToScene(&hilt);
	trap->R_RenderScene(&view);
	return true;
}

static void SWI_UpdateView()
{
	if (trap->Key_GetCatcher() & KEYCATCH_CONSOLE) {
		swi.dragging = false;
		return;
	}
	const float dt = Com_Clamp(0, 50, uiInfo.uiDC.frameTime) * .001f;
	const float stickX = trap->Cvar_VariableValue("st_uiRightStickX") / 32767.f;
	const float stickY = trap->Cvar_VariableValue("st_uiRightStickY") / 32767.f;
	const int horizontal = trap->Key_IsDown(A_CURSOR_RIGHT) - trap->Key_IsDown(A_CURSOR_LEFT);
	const int vertical = trap->Key_IsDown(A_CURSOR_DOWN) - trap->Key_IsDown(A_CURSOR_UP);
	SWI_Orbit(155 * dt * Com_Clamp(-1, 1, stickX + horizontal),
		155 * dt * Com_Clamp(-1, 1, stickY + vertical));
	SWI_Zoom(1.35f * dt * (trap->Key_IsDown(A_JOY9) - trap->Key_IsDown(A_JOY10)));
}

static void SWI_Draw()
{
	menuDef_t *menu = Menu_GetFocused();
	if (!SWI_Active(menu)) {
		if (SWI_Menu(menu))
			SWI_Action(SWI_Entry(menu), "Inspect hilt");
		return;
	}

	SWI_UpdateView();
	const vec4_t shade = {.004f, .012f, .019f, .68f};
	const vec4_t stage = {.009f, .029f, .043f, 1.f};
	UI_FillRect(0, 0, 640, 480, shade);
	LUI_Panel(107, 62, 426, 352, true);
	UI_FillRect(swiViewport.x, swiViewport.y, swiViewport.w, swiViewport.h, stage);
	RUI_Text(124, 76, .82f, "Inspect hilt", ruCyan);
	const bool dual = SWI_Dual();
	const bool second = dual && swi.second;
	char name[MAX_QPATH];
	trap->Cvar_VariableStringBuffer(second ? "ui_saber2" : "ui_saber", name, sizeof(name));
	char title[1024];
	if (!UI_SaberProperNameForSaber(name, title))
		Q_strncpyz(title, name, sizeof(title));
	SCUI_Label(124, 94, 386, .62f, title, ruWhite);

	if (!SWI_DrawHilt(Menu_FindItemByName(menu, second ? "saber2" : "saber")))
		SMUI_Text(132, 221, 376, .72f, "Hilt preview unavailable", ruWhite, FONT_SMALL2, true);
	RUI_Divider(123, 356, 394);
	const bool pad = trap->Cvar_VariableValue("st_controllerEnabled") != 0;
	SMUI_Text(124, 363, 391, .57f,
		pad ? "Drag or right stick to orbit  /  Scroll or bumpers to zoom" : "Drag to orbit  /  Scroll to zoom",
		ruWhite, FONT_SMALL2, true);
	SWI_Action(swiBack, "Lit preview");
	SWI_Action(swiReset, "Reset view");
	if (dual)
		SWI_Action(swiOther, second ? "Inspect primary" : "Inspect off-hand");
}

static bool SWI_Key(int key, qboolean down)
{
	menuDef_t *menu = Menu_GetFocused();
	if (!SWI_Active(menu)) {
		if (down && SWI_Menu(menu) && (key == A_JOY3 ||
			(key == A_MOUSE1 && SWI_Hover(SWI_Entry(menu))))) {
			swi.menu = menu;
			SWI_ResetView();
			return true;
		}
		return false;
	}

	if (!down) {
		if (key == A_MOUSE1)
			swi.dragging = false;
		return true;
	}
	if (key == A_ESCAPE || key == A_JOY1 ||
		(key == A_MOUSE1 && SWI_Hover(swiBack))) {
		swi = {};
	} else if (key == A_JOY2 || (key == A_MOUSE1 && SWI_Hover(swiReset))) {
		SWI_ResetView();
	} else if (SWI_Dual() && (key == A_JOY3 || (key == A_MOUSE1 && SWI_Hover(swiOther)))) {
		swi.second = !swi.second;
		SWI_ResetView();
	} else if (key == A_MOUSE1) {
		swi.dragging = SWI_Hover(swiViewport);
	} else if (key == A_MWHEELUP || key == '+' || key == A_KP_PLUS) {
		SWI_Zoom(-.16f);
	} else if (key == A_MWHEELDOWN || key == '-' || key == A_KP_MINUS) {
		SWI_Zoom(.16f);
	}
	return true;
}

static bool SWI_Mouse(int dx, int dy)
{
	if (!SWI_Active(Menu_GetFocused()))
		return false;
	if (swi.dragging)
		SWI_Orbit(-dx * .65f, dy * .65f);
	return true;
}
#ifdef ST_CONTROLS_QA
extern void UI_MouseEvent(int dx, int dy);
extern void UI_KeyEvent(int key, qboolean down);

qboolean ST_InspectQA()
{
	if (Q_stricmp(SMUI_Arg(0), "st_inspectqa"))
		return qfalse;
	const char *action = SMUI_Arg(1);
	if (!Q_stricmp(action, "move")) {
		UI_MouseEvent(atoi(SMUI_Arg(2)) - uiInfo.uiDC.cursorx,
			atoi(SMUI_Arg(3)) - uiInfo.uiDC.cursory);
	} else if (!Q_stricmp(action, "key")) {
		UI_KeyEvent(atoi(SMUI_Arg(2)), atoi(SMUI_Arg(3)) ? qtrue : qfalse);
	} else {
		menuDef_t *menu = Menu_GetFocused();
		const bool active = SWI_Active(menu);
		const itemDef_t *model = active ? Menu_FindItemByName(menu, swi.second ? "saber2" : "saber") : NULL;
		Com_Printf("ST_INSPECT %s %d %d %.2f %.2f %.2f %d\n", menu ? menu->window.name : "-",
			active, swi.second, swi.yaw, swi.pitch, swi.distance, model && (model->ghoul2 || model->asset));
	}
	return qtrue;
}
#endif
