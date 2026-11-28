"""Polish shared Saber Trials menu layout and retire Tournament player votes."""
import re

from screenshot_layout import edit_items, field, replace

MENUS = tuple(f"ui/jamp/{name}.menu" for name in ("createserver", "joinserver", "ingame_callvote", "demo", "quit"))


def menus(root, output):
    for relative in MENUS:
        path = root / relative
        content = path.read_text(encoding="utf-8")

        def edit(name, item):
            if path.stem == "createserver":
                if name == "settingsbutton3b" or '"duel_fraglimit"' in item:
                    item = field(item, "rect", "10 195 180 20")
            elif path.stem == "joinserver":
                if name == "secondary_background":
                    return ""
                filters = ("netsource", "netfilter", "gametypefilter", "viewempty", "viewfull", "datarate")
                if name in filters:
                    column, row = divmod(filters.index(name), 3)
                    item = field(item, "rect", f"{250 + column * 180} {29 + row * 17} 180 17")
                    item = field(item, "textscale", ".79")
                actions = {"passwordtext": 14, "createfavoritetext": 137, "addfavorite": 260,
                           "delfavorite": 260, "serverinfotext": 383, "findplayertext": 506}
                if name in actions:
                    item = field(item, "rect", f"{actions[name]} 399 120 24")
            elif path.stem in {"demo", "quit"}:
                if name in {"st_editor_nav", "st_editor_navline", "st_editor_active"}:
                    return ""
                nav = {"newgamebutton": 28, "profilebutton": 176, "controlsbutton": 324, "setupbutton": 472}
                if name in nav:
                    item = field(item, "rect", f"{nav[name]} 77 140 27")
            else:
                if "callvote tournament" in item:
                    return ""
                if name == "miscbutton":
                    item = item.replace("map rotation, Tournament, and team entry", "map rotation and team entry")
                if 'text "Lock Teams"' in item or 'text "Unlock Teams"' in item:
                    item = re.sub(r"(rect\s+\d+\s+)235(\s+165\s+)28", r"\g<1>211\g<2>27", item, count=1)
            return item

        content = edit_items(content, edit)
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def patch_ui(frontend):
    root = frontend / "codemp/ui"

    def edit(filename, *edits):
        path = root / filename
        content = path.read_text(encoding="utf-8")
        for old, new in edits:
            content = replace(content, old, new)
        path.write_text(content, encoding="utf-8")

    edit("menu_items.inc",
         ('    if (!Q_stricmp(name,"createserver")) {', '''    if (!ST_ClassicLayout() && !Q_stricmp(name,"ingame_siegeclass")) {
        // Keep the mission description in the column beside its image.
        if (auto* description = Menu_FindItemByName(menu,"obj_longdesc")) {
            description->window.rectClient = {13,399,189,70};
            description->textalignx = 5;
            description->textaligny = 4;
            description->textscale = .60f;
        }
        for (const char* panel : {"description", "itemdescription"}) {
            if (auto* item = Menu_FindItemByName(menu,panel))
                item->window.rectClient.h = 74;
        }
        for (const char* control : {"cancel", "okay"}) {
            if (auto* item = Menu_FindItemByName(menu,control)) {
                item->window.rectClient.y = 435;
                item->window.rectClient.h = 24;
            }
        }
    }
    if (!Q_stricmp(name,"createserver")) {'''),
         ("rectDef_t{215,414,270,22} : rectDef_t{217,399,206,23}",
          "rectDef_t{13,132,181,22} : rectDef_t{10,215,180,22}"),
         ('item->cvar = "ui_stHostPreset";', '''item->cvar = "ui_stHostPreset";
        item->textscale = ST_ClassicLayout() ? .64f : .72f;
        if (!ST_ClassicLayout()) {
            item->textalignment = ITEM_ALIGN_RIGHT;
            item->textalignx = 80;
        }'''))

    edit("ui_st_rich.inc",
         ("// The atlas ink spans about 4 to 47 pixels from the draw origin, at .43 units per pixel.\nstatic void RUI_ButtonLabel",
          '''static float RUI_CaptionY(float y, float h, const char* text, float scale) {
 // Ink bounds from the 64 x 80 cells in the shipped type atlas.
 static const unsigned char top[] = {
  80,9,9,9,7,9,9,9,9,9,9,13,36,27,36,9,9,9,9,9,9,9,9,9,9,9,18,18,13,18,13,9,
  9,9,9,8,9,9,9,8,9,9,9,9,9,9,9,8,9,8,9,8,9,9,9,9,9,9,9,9,9,9,8,47,
  8,17,9,17,9,17,9,17,9,9,9,9,9,17,17,17,17,17,17,17,10,18,18,18,18,18,18,9,9,9,21
 };
 static const unsigned char bottom[] = {
  0,41,20,41,45,41,41,20,50,50,24,36,48,32,41,41,41,41,41,41,41,41,41,41,41,41,41,48,37,33,37,41,
  51,41,41,42,41,41,41,42,41,41,42,41,41,41,41,42,41,46,41,42,41,42,41,41,41,41,41,50,41,50,25,50,
  13,41,41,41,41,41,41,50,41,41,50,41,41,41,41,41,50,50,41,41,41,41,41,41,41,50,41,50,51,50,29
 };
 static_assert(ARRAY_LEN(top) == 95 && ARRAY_LEN(bottom) == 95, "Saber Trials glyph count");
 text = STML_Translate(text);
 float center = 10.8f;
 if (RUI_Ascii(text)) {
  int first = 80, last = 0;
  for (; *text; ++text) {
   if (Q_IsColorString(text)) { ++text; continue; }
   const unsigned char glyph = *text - ' ';
   first = std::min(first, int(top[glyph]));
   last = std::max(last, int(bottom[glyph]));
  }
  if (last > first) center = (.5f * (first + last) - 3.f) * .43f;
 }
 return y + h * .5f - center * scale;
}

static void RUI_ButtonLabel'''),
         ("RUI_Text(left, y + h * .5f - 10.8f * scale, scale, text, color);",
          "RUI_Text(left, RUI_CaptionY(y, h, text, scale), scale, text, color);"),
         ("const char* text, const float* color, int align = ITEM_ALIGN_CENTER) {\n const float inset = std::min(12.f, w * .12f);",
          """const char* text, const float* color, int align = ITEM_ALIGN_CENTER,
                            float padding = 0.f) {
 if (w <= 2.f || h <= 5.f || !text || !*text) return;
 const float inset = std::min(w * .24f, padding > 0.f ? padding : std::min(12.f, w * .12f));"""))

    controls = (root / "ui_st_controls.inc").read_text(encoding="utf-8")
    start = controls.index(" const bool binding=id>=500&&id<570;")
    end = controls.index(" SCUI_Hit(x,y,w,h,id,a,b);", start)
    edit("ui_st_controls.inc",
         (controls[start:end], ''' const bool binding = id >= 500 && id < 570;
 const bool tab = (id >= 100 && id < 107) || (id >= 2000 && id < 2007);
 const bool value = (id >= 600 && id < 625) || (id >= 2200 && id < 2400);
 const bool centered = binding || tab || (id >= 1200 && id <= 1302) ||
   (id >= 2900 && id <= 2906) || (id >= 3200 && id <= 3202) || id == 3500;
 const bool action = (w >= 48 && h >= 20 && !(id >= 300 && id < 320) &&
   !(id >= 700 && id < 725)) || selected;
 const char* kind = tab ? "tab" : binding || value ? "field" : "action";
 rectDef_t art = {x, y, w, h};
 const float labelWidth = RUI_Width(text, .57f);
 if (binding) {
  art.w = std::min(w - 4.f, std::max(30.f, labelWidth + 16.f));
  art.x += (w - art.w) * .5f;
  art.y += 2.f;
  art.h -= 4.f;
  RUI_FieldArt(focus ? "field_focus" : "field_idle", art.x, art.y, art.w, art.h);
 } else if (tab || value || action) {
  if (value || (!tab && w >= 140.f)) {
   art.w = std::min(w, std::max(44.f, labelWidth + 22.f));
   if (centered) art.x += (w - art.w) * .5f;
  }
  RUI_Control(art.x, art.y, art.w, art.h, kind, selected, focus);
 }
 const float gutter = tab ? std::min(11.f, art.w * .115f) : binding || value || !action ? 6.f : 0.f;
 RUI_ButtonLabel(art.x, art.y, art.w, art.h, .57f, text, color,
                 centered ? ITEM_ALIGN_CENTER : ITEM_ALIGN_LEFT, gutter);
'''))

    edit("ui_st_controls_draw.inc",
         ("widths[]={85,61,111,47,73,90,85}", "widths[]={87,58,122,48,75,97,89}"),
         ("r=SCUI_Row(scope,-1,group);count=r.count;\n  if(scui.modal!=3",
          "r=SCUI_Row(scope,-1,group);count=r.count;\n  if(scope==STC_SERVER && count<=rows){columns=1;rows=per;}\n  if(scui.modal!=3"),
         ("SCUI_Button(20,443,56,22", "SCUI_Button(24,442,56,21"),
         ("SCUI_Button(390,443,110,22", "SCUI_Button(383,442,113,21"),
         ("SCUI_Button(506,443,114,22", "SCUI_Button(502,442,112,21"))

    profile = (root / "ui_st_profile.inc").read_text(encoding="utf-8")
    start = profile.index("static void SPUI_Button(")
    end = profile.index("static void SPUI_Mouse()", start)
    edit("ui_st_profile.inc", (profile[start:end], '''static void SPUI_Button(float x,float y,float w,float h,const char* text,int id,int arg=0,bool selected=false,bool enabled=true){
 const bool focus=SPUI_Over(x,y,w,h)||(!spui.mouse&&spui.focus==id);
 const bool collection=id>=110&&id<=112;
 const bool centered=collection||(id>=500&&id<=502)||id>=1000;
 const bool modalAction=spui.modal&&id>=1000&&id<1020+ST_TFFA_MAX_TEAMS;
 vec4_t color;MSUI_Color(color,selected,focus,enabled||selected);
 rectDef_t art={x,y,w,h};
 if(modalAction||(id<520&&w>=32&&(id<130||id==137||id>=410))){
  const bool compact=id==121||id==137||id==412;
  if(compact)art.w=std::min(w,std::max(34.f,20.f+RUI_Width(text,.53f)));
  if(centered)art.x+=(w-art.w)*.5f;
  RUI_Control(art.x,art.y,art.w,art.h,collection?"tab":"action",selected,focus&&enabled);
 }
 RUI_ButtonLabel(art.x,art.y,art.w,art.h,w<22.f?.43f:.53f,text,color,
                centered||w<22.f?ITEM_ALIGN_CENTER:ITEM_ALIGN_LEFT,collection?3.f:6.f);
 if(enabled)SPUI_Hit(x,y,w,h,id,arg);
}
'''))
    edit("ui_st_emotes.inc",
         ("SCUI_Centered(x+2,y,w-4,h,.53f,label,selected||hover?scuCyan:scuText);",
          "RUI_ButtonLabel(x,y,w,h,.53f,label,selected||hover?scuCyan:scuText);"),
         ('EM_Button(294,48,152,25', 'EM_Button(294,57,152,25'),
         ('EM_Button(455,48,161,25', 'EM_Button(455,57,161,25'),
         ('SCUI_Text(23,132,.62f,"Emote library"', 'SCUI_Text(23,123,.62f,"Emote library"'),
         ('SCUI_Text(206,132,.62f,"Wheel slots"', 'SCUI_Text(206,123,.62f,"Wheel slots"'))

    legacy = (root / "ui_st_legacy.inc").read_text(encoding="utf-8")
    start = legacy.index("void ST_LegacyEditField(")
    end = legacy.index("static void LUI_Fit(", start)
    menu_button = legacy[legacy.index("  const bool rules ="):legacy.index(" if(limit>0", legacy.index("  const bool rules ="))]
    multi = legacy[legacy.index(" if((i->type==ITEM_TYPE_MULTI"):legacy.index(" if(ST_SelectionSlotText(")]
    edit("ui_st_legacy.inc",
         ('if(LUI_Name(m->window.name,"rulesMenu_games")&&(LUI_Name(n,"st_editor_ruledetails")||LUI_Name(n,"setup_background")))return true;',
          '''const bool rules = !Q_stricmpn(m->window.name, "rulesMenu", 9);
 if (rules && LUI_Name(n, "st_editor_ruledetails")) return true;
 if (LUI_Name(m->window.name, "rulesMenu_games") && LUI_Name(n, "setup_background")) return true;'''),
         (legacy[start:end], '''static void LUI_Caption(float x, float y, float w, float h, float scale, const char* label,
 const float* color, int align = ITEM_ALIGN_CENTER, float padding = 0.f) {
 const bool bypass = lui.bypass;
 lui.bypass = true;
 RUI_ButtonLabel(x, y, w, h, scale, label, color, align, padding);
 lui.bypass = bypass;
}

// Use the same bounds for a field's plate, glyphs and caret.
static float LUI_FieldRight(const itemDef_t* item) {
 const auto& r = item->window.rect;
 return std::min(632.f, r.x + r.w - 2.f);
}

static float LUI_FieldSplit(const itemDef_t* item) {
 const auto* menu = static_cast<const menuDef_t*>(item->parent);
 const auto& r = item->window.rect;
 if (!item->text || !*item->text) return r.x + 3.f;
 if (LUI_Name(menu->window.name, "joinserver") &&
     (LUI_Name(item->window.name, "viewEmpty") || LUI_Name(item->window.name, "viewFull") ||
      LUI_Name(item->window.name, "datarate"))) return r.x + 91.f;
 return std::min(item->textRect.x + item->textRect.w + 5.f, LUI_FieldRight(item) - 25.f);
}

static void LUI_FieldLabel(itemDef_t* item, const char* label, float scale, const float* color) {
 const auto& r = item->window.rect;
 const float width = LUI_FieldSplit(item) - r.x - 3.f;
 LUI_Caption(r.x, r.y, width, r.h, scale, label, color, item->textalignment, 3.f);
}

static rectDef_t LUI_FieldRect(itemDef_t* item, const char* value, float scale, bool editing) {
 const auto& r = item->window.rect;
 const float left = LUI_FieldSplit(item);
 const float space = LUI_FieldRight(item) - left;
 const bool unlabelledEdit = item->type == ITEM_TYPE_EDITFIELD && (!item->text || !*item->text);
 const bool fill = editing || unlabelledEdit || LUI_Name(item->window.name, "server_search") ||
                   LUI_Name(item->cvar, "ui_stDirectAddress");
 const float minimum = item->type == ITEM_TYPE_EDITFIELD ? 49.f : 27.f;
 const float width = fill ? space : std::min(space, std::max(minimum, RUI_Width(value, scale) + 12.f));
 return {left, r.y + 1.f, width, r.h - 2.f};
}

qboolean ST_LegacyEditField(itemDef_t* item, const char* value, vec4_t color, bool editing, int cursor) {
 if (!LUI_UseItem() || item->window.background || item->window.rect.h < 12.f) return qfalse;
 const float scale = std::min(item->textscale, (item->window.rect.h - 7.f) / 22.f);
 STML_Raw raw;
 const auto box = LUI_FieldRect(item, value, scale, editing);
 if (box.w < 12.f) return qfalse;
 RUI_FieldArt(LUI_Focus(item) ? "field_focus" : "field_idle", box.x, box.y, box.w, box.h);
 if (!editing) {
  LUI_Caption(box.x, box.y, box.w, box.h, scale, value, color, ITEM_ALIGN_LEFT, 5.f);
  return qtrue;
 }
 const float textWidth = RUI_Width(value, scale);
 const float paintScale = textWidth > box.w - 12.f ? scale * (box.w - 12.f) / textWidth : scale;
 const bool bypass = lui.bypass;
 lui.bypass = true;
 RUI_Text(box.x + 5.f, RUI_CaptionY(box.y, box.h, value, paintScale), paintScale, value, color);
 lui.bypass = bypass;
 if ((uiInfo.uiDC.realTime / 400) & 1) {
  char prefix[1024];
  Q_strncpyz(prefix, value, sizeof(prefix));
  prefix[std::min(std::max(0, cursor), (int)strlen(prefix))] = 0;
  const float caretX = box.x + 5.f + RUI_Width(prefix, paintScale);
  if (trap->Key_GetOverstrikeMode())
   UI_FillRect(caretX, box.y + box.h - 4.f, 3.f, 1.f, color);
  else
   UI_FillRect(caretX, box.y + 3.f, 1.f, box.h - 6.f, color);
 }
 return qtrue;
}
'''),
         (menu_button, '''  const bool rules = !Q_stricmpn(m->window.name, "rulesMenu", 9);
  const bool host = LUI_Name(m->window.name, "createserver");
  const bool votes = LUI_Name(m->window.name, "ingame_callvote");
  const bool browserActions = LUI_Name(m->window.name, "joinserver") && r.y >= 398.f && r.y < 423.f;
  const bool rail = LUI_Rail(m);
  const bool railIcon = rail && LUI_RailIcon(i->window.name);
  const bool fixed = rules || host || votes || browserActions || LUI_Name(i->window.group, "toprow");
  const bool selected = LUI_Selected(i);
  const bool focus = LUI_Focus(i);
  vec4_t ink;
  MSUI_Color(ink, selected, focus, color[0] > .4f || color[1] > .4f);
  ink[3] = color[3];
  if (ST_IsPersonalFrontend() && (LUI_Name(i->window.name, "photo") ||
      LUI_Name(i->window.name, "account_link") || LUI_Name(i->window.name, "match_rules")))
   memcpy(ink, scuMuted, sizeof(ink));

  int align = i->textalignment;
  if (LUI_CenterAction(i->window.name) || LUI_Name(text, "Cancel") || browserActions) align = ITEM_ALIGN_CENTER;
  if ((host || votes || rules) && !LUI_Name(i->window.group, "game_submenu"))
   align = LUI_Name(i->window.group, "grpbutton") ? ITEM_ALIGN_RIGHT : ITEM_ALIGN_CENTER;
  const float paintScale = std::min(.83f, r.h / 33.f);
  rectDef_t box = {r.x + 1.f, r.y + 1.f, r.w - 2.f, r.h - 2.f};
  if (!fixed && !rail) {
   box.w = std::min(box.w, std::max(29.f, RUI_Width(text, paintScale) + 23.f));
   if (align == ITEM_ALIGN_CENTER) box.x = r.x + (r.w - box.w) * .5f;
   if (align == ITEM_ALIGN_RIGHT) box.x = r.x + r.w - box.w - 1.f;
  }
  if (!rail) RUI_Control(box.x, box.y, box.w, box.h, "action", LUI_Primary(i->window.name) || selected, focus);
  if (railIcon) { box.x += 33.f; box.w -= 33.f; }
  LUI_Caption(box.x, box.y, box.w, box.h, paintScale, text, ink, align);
  return qtrue;
 }
'''),
         (multi, ""),
         (""" if(i->type==ITEM_TYPE_EDITFIELD||i->type==ITEM_TYPE_NUMERICFIELD||i->type==ITEM_TYPE_LISTBOX||i->type==ITEM_TYPE_TEXTSCROLL)return qfalse;""",
          ''' if (i->type == ITEM_TYPE_LISTBOX || i->type == ITEM_TYPE_TEXTSCROLL) return qfalse;
 const bool edit = i->type == ITEM_TYPE_EDITFIELD || i->type == ITEM_TYPE_NUMERICFIELD;
 const bool choice = i->type == ITEM_TYPE_MULTI || i->type == ITEM_TYPE_YESNO;
 if ((edit || choice) && !i->window.background && r.h >= 12.f) {
  const bool hasLabel = i->text && *i->text;
  if (hasLabel && std::abs(x - i->textRect.x) < 1.f) {
   LUI_FieldLabel(i, text, std::min(scale, .86f), color);
   return qtrue;
  }
  if (edit) return qtrue;
  const float paintScale = std::min(scale, (r.h - 7.f) / 22.f);
  const auto box = LUI_FieldRect(i, text, paintScale, false);
  RUI_FieldArt(LUI_Focus(i) ? "field_focus" : "field_idle", box.x, box.y, box.w, box.h);
  LUI_Caption(box.x, box.y, box.w, box.h, paintScale, text, color, ITEM_ALIGN_LEFT, 5.f);
  return qtrue;
 }
 if (edit) return qfalse;
 if (LUI_Name(m->window.name, "joinserver") && i->type == ITEM_TYPE_OWNERDRAW &&
     (LUI_Name(i->window.name, "netsource") || LUI_Name(i->window.name, "netfilter") ||
      LUI_Name(i->window.name, "gametypefilter"))) {
  LUI_Caption(x, r.y, r.x + r.w - x, r.h, .72f, text, color, ITEM_ALIGN_LEFT, 0.1f);
  return qtrue;
 }'''))

    edit("ui_shared.c",
         ("extern void ST_LegacyEditField(itemDef_t*,float,float,const char*);",
          "extern qboolean ST_LegacyEditField(itemDef_t*,const char*,vec4_t,bool,int);"),
         ("\tST_LegacyEditField(item,item->textRect.x+item->textRect.w+offset,item->textRect.y,buff+editPtr->paintOffset);",
          """\tif (ST_LegacyEditField(item, buff + editPtr->paintOffset, newColor,
\t\t(item->window.flags & WINDOW_HASFOCUS) && g_editingField,
\t\titem->cursorPos - editPtr->paintOffset)) return;"""))

    edit("ui_main.c",
         ('handle = trap->PC_LoadSource(ThemeAsset(menuFile));', '''// Namespaced assets keep the same layout in either package search order.
	handle = 0;
	if (!ST_ClassicLayout() && !ST_IsPersonalFrontend()) {
		static const char* const menus[] = {
			"ui/jamp/createserver.menu", "ui/jamp/joinserver.menu",
			"ui/jamp/ingame_callvote.menu", "ui/jamp/demo.menu", "ui/jamp/quit.menu"
		};
		for (const char* menu : menus) {
			if (!Q_stricmp(menu, menuFile)) {
				handle = trap->PC_LoadSource(va("st_interface_audit/%s", menu));
				break;
			}
		}
	}
	if (!handle) handle = trap->PC_LoadSource(ThemeAsset(menuFile));'''),
         ('trap->Cvar_Create("ui_stHostPresetSet","0",CVAR_TEMP);',
          'trap->Cvar_Create("ui_stHostPresetSet","0",CVAR_TEMP);\n    trap->Cvar_Create("st_uiHideGameHud","0",CVAR_TEMP);\n    trap->Cvar_Set("st_uiHideGameHud","0");'),
         ('ThemeFrame();\n\tif(EM_WheelOpen())', '''ThemeFrame();
 const auto* focused = Menu_GetFocused();
 const bool hideGameHud = !ST_ClassicLayout() && (SSUI_CameraView() ||
  (focused && focused->window.name && !Q_stricmp(focused->window.name, "ingame_siegeclass")));
 trap->Cvar_Set("st_uiHideGameHud", hideGameHud ? "1" : "0");
	if(EM_WheelOpen())'''),
         ("int y, i=0;\n\n\tText_Paint(rect->x + 2", """int y, i=0;
	const bool modern = !ST_ClassicLayout();
	if (modern) scale = std::min(scale, .72f);
	const int rowHeight = modern ? 13 : 11;
	const int end = rect->y + rect->h - (modern ? 28 : 0);
	auto paint = [&](float x, float y, const char* text, float width) {
		const float measured = Text_Width(text, scale, iMenuFont);
		const float fit = modern && measured > width ? scale * width / measured : scale;
		Text_Paint(x, y, fit, color, text, 0, width, textStyle, iMenuFont);
	};

	paint(rect->x + 2"""),
         ('scale, color, va("GL_VENDOR: %s", uiInfo.uiDC.glconfig.vendor_string), 0, rect->w, textStyle,iMenuFont);',
          'va("GL_VENDOR: %s", uiInfo.uiDC.glconfig.vendor_string), rect->w - 12.f);'),
         ('Text_Paint(rect->x + 2, rect->y + 15, scale, color, va("GL_VERSION: %s: %s", uiInfo.uiDC.glconfig.version_string,uiInfo.uiDC.glconfig.renderer_string), 0, rect->w, textStyle,iMenuFont);',
          'paint(rect->x + 2, rect->y + 15, va("GL_VERSION: %s: %s", uiInfo.uiDC.glconfig.version_string, uiInfo.uiDC.glconfig.renderer_string), rect->w - 12.f);'),
         ('Text_Paint(rect->x + 2, rect->y + 30, scale, color, va ("GL_PIXELFORMAT: color(%d-bits) Z(%d-bits) stencil(%d-bits)", uiInfo.uiDC.glconfig.colorBits, uiInfo.uiDC.glconfig.depthBits, uiInfo.uiDC.glconfig.stencilBits), 0, rect->w, textStyle,iMenuFont);',
          'paint(rect->x + 2, rect->y + 30, va("GL_PIXELFORMAT: color(%d-bits) Z(%d-bits) stencil(%d-bits)", uiInfo.uiDC.glconfig.colorBits, uiInfo.uiDC.glconfig.depthBits, uiInfo.uiDC.glconfig.stencilBits), rect->w - 12.f);'),
         ("while ( y < rect->y + rect->h && extensionName != NULL )", "while ( y < end && extensionName != NULL )"),
         ("Text_Paint (rect->x + 2, y, scale, color, extensionName, 0, (rect->w / 2), textStyle, iMenuFont);",
          "paint(rect->x + 2, y, extensionName, rect->w * .5f - 12.f);"),
         ("Text_Paint (rect->x + rect->w / 2, y, scale, color, extensionName, 0, (rect->w / 2), textStyle, iMenuFont);\n\t\t\ty += 11;",
          "paint(rect->x + rect->w / 2, y, extensionName, rect->w * .5f - 12.f);\n\t\t\ty += rowHeight;"))

    edit("ui_st_match_rules.inc",
         ('"Force rules","Tournament","Add bot"', '"Force rules",nullptr,"Add bot"'),
         ('for(int i=0;i<14;++i)add(MR_VOTE', 'for(int i=0;i<14;++i)if(mrVotes[i])add(MR_VOTE'),
         ('for(int i=0;i<14;++i)mrui.review.push_back', 'for(int i=0;i<14;++i)if(mrVotes[i])mrui.review.push_back'))

    fix_feeder_selection(root)
    add_feeder_fixture(root)


def fix_feeder_selection(root):
    shared = root / "ui_shared.c"
    text = shared.read_text(encoding="utf-8")
    start = text.index("void Menu_ScrollFeeder(")
    end = text.index("qboolean Menus_AnyFullScreenVisible", start)
    text = text[:start] + """// Ownerdraws use special for their own data, which can match a feeder ID.
static itemDef_t *Menu_FindFeederList(menuDef_t *menu, int feeder) {
	if (!menu) return NULL;
	for (int i = 0; i < menu->itemCount; ++i) {
		itemDef_t *item = menu->items[i];
		if (item->type == ITEM_TYPE_LISTBOX && item->typeData.listbox && item->special == feeder)
			return item;
	}
	return NULL;
}

void Menu_ScrollFeeder(menuDef_t *menu, int feeder, qboolean down) {
	if (itemDef_t *item = Menu_FindFeederList(menu, feeder))
		Item_ListBox_HandleKey(item, down ? A_CURSOR_DOWN : A_CURSOR_UP, qtrue, qtrue);
}

void Menu_SetFeederSelection(menuDef_t *menu, int feeder, int index, const char *name) {
	if (!menu)
		menu = name ? Menus_FindByName(name) : Menu_GetFocused();

	itemDef_t *item = Menu_FindFeederList(menu, feeder);
	if (!item) return;
	if (index == 0) {
		listBoxDef_t *list = item->typeData.listbox;
		list->cursorPos = 0;
		list->startPos = 0;
	}
	item->cursorPos = index;
	DC->feederSelection(item->special, item->cursorPos, NULL);
}

""" + text[end:]
    shared.write_text(text, encoding="utf-8")

    main = root / "ui_main.c"
    text = main.read_text(encoding="utf-8")
    text = replace(text, "Menu_SetFeederSelection(NULL, FEEDER_SERVERS, 0, NULL);",
                   'Menu_SetFeederSelection(NULL, FEEDER_SERVERS, 0, "joinserver");')
    main.write_text(text, encoding="utf-8")


def add_feeder_fixture(root):
    legacy = root / "ui_st_legacy.inc"
    text = legacy.read_text(encoding="utf-8")
    at = ' if(LUI_Name(op,"layout")){'
    fixture = r""" if (LUI_Name(op, "refilter-host")) {
  auto* browser = Menus_FindByName("joinserver");
  auto* list = browser ? Menu_FindItemByName(browser, "serverlist") : nullptr;
  auto* slot = m ? Menu_FindItemByName(m, "tffaSlot3") : nullptr;
  if (!m || !LUI_Name(m->window.name, "createserver") || !slot ||
      slot->type != ITEM_TYPE_OWNERDRAW || slot->special != FEEDER_SERVERS ||
      !list || list->type != ITEM_TYPE_LISTBOX || list->special != FEEDER_SERVERS ||
      !list->typeData.listbox) {
   fail("browser refresh collision fixture missing");
   return qtrue;
  }
  const int slotCursor = slot->cursorPos;
  list->cursorPos = list->typeData.listbox->cursorPos = list->typeData.listbox->startPos = 1;
  Com_Printf("ST_FEEDER_REFRESH_HOST\n");
  UI_BuildServerDisplayList(qtrue);
  if (list->cursorPos || list->typeData.listbox->cursorPos || list->typeData.listbox->startPos)
   fail("browser refresh did not reset its list");
  Menu_SetFeederSelection(m, FEEDER_SERVERS, 0, nullptr);
  Menu_ScrollFeeder(m, FEEDER_SERVERS, qtrue);
  if (slot->cursorPos != slotCursor || Menu_GetFocused() != m)
   fail("browser refresh changed the host menu");
  Com_Printf("ST_FEEDER_REFRESH_DONE\n");
 } else"""
    legacy.write_text(replace(text, at, fixture + at), encoding="utf-8")

def patch_game(game):
    path = game / "codemp/game/g_cmds.c"
    content = path.read_text(encoding="utf-8")
    start = content.index("qboolean G_VoteTournament(")
    end = content.index("qboolean G_VoteAddBot(", start)
    content = content[:start] + content[end:]
    content, count = re.subn(r'\{\s*"tournament",\s*"tourney",\s*G_VoteTournament[^\n]+',
        "{ NULL, NULL, NULL, 0, 0, qfalse, NULL }, // Reserved vote bit 11.", content)
    assert count == 1
    content = replace(content, "for ( i = 0; i<validVoteStringsSize; i++ ) {\n\t\t\tif",
                      "for ( i = 0; i<validVoteStringsSize; i++ ) {\n\t\t\tif ( !validVoteStrings[i].string ) continue;\n\t\t\tif")
    content = replace(content, "index >= validVoteStringsSize )", "index >= validVoteStringsSize || !validVoteStrings[index].string )")
    content = content.replace("if ( !(g_allowVote.integer & (1<<i)) )",
                      "if ( !validVoteStrings[i].string || !(g_allowVote.integer & (1<<i)) )")
    path.write_text(content, encoding="utf-8")


def patch_cgame(cgame):
    root = cgame / "codemp/cgame"
    view = root / "cg_view.c"
    draw = root / "cg_draw.c"
    header = root / "cg_local.h"
    for path in (view, draw, header):
        content = path.read_text(encoding="utf-8")
        if path == view:
            content = replace(content, "CG_DrawActive( stereoView );",
                              '''char hideHudSetting[2] = {0};
	trap->Cvar_VariableStringBuffer("st_uiHideGameHud", hideHudSetting, sizeof(hideHudSetting));
	const qboolean hideGameHud = (trap->Key_GetCatcher() & KEYCATCH_UI) && hideHudSetting[0] == '1' ? qtrue : qfalse;
	CG_DrawActive( stereoView, hideGameHud );''')
            content = replace(content, "if (!ST_PhotoActive()) CG_DrawAutoMap();",
                              "if (!hideGameHud && !ST_PhotoActive()) CG_DrawAutoMap();")
        else:
            content, count = re.subn(r"(CG_DrawActive\s*\(\s*stereoFrame_t\s+stereoView)\s*\)",
                                     r"\1, qboolean hideGameHud )", content)
            assert count == 1, path
        if path == draw:
            content = replace(content, "CG_Draw2D();",
                              "if (!hideGameHud) CG_Draw2D();")
        path.write_text(content,encoding="utf-8")
