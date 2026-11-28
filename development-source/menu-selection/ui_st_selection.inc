/* Saber Trials native menu selection presentation. GPL-2.0. */
static bool LUI_UseItem();
static void LUI_Fit(float, float, float, float, const char*, const float*);

static struct {
    const itemDef_t* item;
    bool selected, hover;
} stListRow;

static std::string ST_SelectionPlain(const char* text) {
    std::string result;
    for (const char* p = text; p && *p; ++p) {
        if (Q_IsColorString(p)) ++p;
        else result += *p;
    }
    return result;
}

/* Called before row text, using the list's actual selection index. The
 * selection stays visible after focus moves to the map/vote action button.
 */
qboolean ST_LegacyListRow(itemDef_t* item, int row, float x, float y, float w, float h) {
    stListRow.item = NULL;
    if (!LUI_UseItem() || item->type != ITEM_TYPE_LISTBOX ||
        (item->window.flags & WINDOW_HORIZONTAL)) return qfalse;
    stListRow.item = item;
    const auto* list = item->typeData.listbox;
    stListRow.selected = !list->notselectable && row == item->cursorPos;
    stListRow.hover = !list->notselectable && item->parent == lui.top &&
        LUI_Focus(item) && uiInfo.uiDC.cursorx >= x && uiInfo.uiDC.cursorx < x+w &&
        uiInfo.uiDC.cursory >= y && uiInfo.uiDC.cursory < y+h;
    if (!stListRow.selected && !stListRow.hover) return qtrue;
    /* Keep the inset, stripe and rules inside the list's frame. */
    const float left = std::max(x, item->window.rect.x+3);
    const float right = std::min(x+w, item->window.rect.x+item->window.rect.w-3);
    const float top = std::max(y+.5f, item->window.rect.y+2);
    const float bottom = std::min(y+h-.5f, item->window.rect.y+item->window.rect.h-2);
    if (right <= left || bottom <= top) return qtrue;
    const vec4_t selected = {.025f,.22f,.32f,.98f};
    const vec4_t selectedHover = {.035f,.28f,.39f,.98f};
    const vec4_t hover = {.018f,.11f,.17f,.94f};
    const vec4_t cyan = {.06f,.78f,1,.85f};
    UI_FillRect(left, top, right-left, bottom-top,
        stListRow.selected ? (stListRow.hover ? selectedHover : selected) : hover);
    UI_FillRect(left, top, 2, bottom-top, stListRow.selected ? ruGold : cyan);
    if (stListRow.selected) {
        UI_FillRect(left+2, top, right-left-2, .55f, cyan);
        UI_FillRect(left+2, bottom-.55f, right-left-2, .55f, cyan);
    }
    return qtrue;
}

static qboolean ST_SelectionListText(itemDef_t* item, float x, float y,
    float width, const char* text) {
    if (!LUI_UseItem() || !text || (!RUI_Ascii(text) && !STML_UTF8(text))) return qfalse;
    const float height = item->typeData.listbox->elementHeight;
    const float scale = std::min(item->textscale, height*.045f);
    const bool selected = stListRow.item == item && stListRow.selected;
    const bool hover = stListRow.item == item && stListRow.hover;
    const float* color = selected ? ruWhite : hover ? ruCyan : item->window.foreColor;
    /* A player's ^0 name must not hide the selected target. Only remove color
     * escapes for the selected display; preserve names and UTF-8 bytes. */
    const std::string plain = selected ? ST_SelectionPlain(text) : std::string();
    SCUI_Fit(x+4, y+(height-17.f*scale)*.5f, std::max(8.f,width-4),
        scale, selected ? plain.c_str() : text, color);
    return qtrue;
}

static bool ST_SelectionSlot(const itemDef_t* item) {
    return item->type == ITEM_TYPE_OWNERDRAW &&
        (LUI_Name(item->window.name,"humanbotfield") || LUI_Name(item->window.name,"humanbotnonfield"));
}

static bool ST_SelectionSlotWindow(itemDef_t* item) {
    if (!ST_SelectionSlot(item)) return false;
    if (LUI_Focus(item)) {
        const auto& r = item->window.rect;
        vec4_t tint = {item->window.foreColor[0]*.10f, item->window.foreColor[1]*.10f,
            item->window.foreColor[2]*.10f, .95f};
        RUI_FieldArt("field_focus", r.x+1, r.y, r.w-2, r.h);
        UI_FillRect(r.x+5, r.y+3, r.w-10, r.h-6, tint);
        UI_FillRect(r.x+3, r.y+3, 1.5f, r.h-6, item->window.foreColor);
    }
    return true;
}

static bool ST_SelectionSlotText(itemDef_t* item, float x, float y, float w,
    float scale, const char* text, const float* nativeColor) {
    if (!ST_SelectionSlot(item)) return false;
    const auto& r = item->window.rect;
    if (r.h >= 12) {
        scale = std::min(scale, (r.h-3.f)/17.f);
        y = r.y+(r.h-17.f*scale)*.5f;
    }
    /* Native owner draws dim closed slots to half brightness. Preserve that
     * distinction, and keep the team's hue when focus would otherwise turn
     * both teams into the same generic cyan color. */
    const float brightness = std::max(nativeColor[0], std::max(nativeColor[1],nativeColor[2]));
    vec4_t color = {item->window.foreColor[0]*brightness, item->window.foreColor[1]*brightness,
        item->window.foreColor[2]*brightness, nativeColor[3]};
    const std::string plain = ST_SelectionPlain(text);
    LUI_Fit(x, y, w, scale, plain.c_str(), color);
    return true;
}
