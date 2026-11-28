// Add native items to selected retail pages without redistributing those pages.
extern bool ST_ClassicLayout();
static itemDef_t *ThemeItem(menuDef_t *menu, const char *name, const char *text,
                            rectDef_t rect, const char *action) {
    if (menu->itemCount >= MAX_MENUITEMS) return NULL;
    auto item = (itemDef_t*)UI_Alloc(sizeof(itemDef_t));
    if (!item) return NULL;
    Item_Init(item);
    item->parent = menu;
    item->window.name = name;
    item->window.rectClient = rect;
    item->window.flags = WINDOW_VISIBLE;
    const vec4_t color = {.88f,.85f,.64f,1};
    memcpy(item->window.foreColor,color,sizeof(color));
    item->type = ITEM_TYPE_BUTTON;
    item->iMenuFont = FONT_MEDIUM;
    item->text = text;
    item->textscale = .75f;
    item->textalignx = 4;
    item->textaligny = 2;
    item->action = action;
    menu->items[menu->itemCount++] = item;
    return item;
}

static void ThemeItems(menuDef_t *menu) {
    const char *name = menu->window.name;
    if (!name) return;
    if (!Q_stricmp(name,"createserver")) {
        // Retail closes the host page immediately. The shared match review
        // stays on that page until the player confirms or goes back.
        auto begin = Menu_FindItemByName(menu,"accept");
        if (begin && begin->action && strstr(begin->action,"StartServer") &&
            strstr(begin->action,"createserver"))
            begin->action = "uiScript StartServer ;";
        auto item = ThemeItem(menu,"stHostPreset","Gameplay",{215,414,270,22},"uiScript stHostPresetChanged ;");
        if (!item) return;
        item->type = ITEM_TYPE_MULTI;
        item->cvar = "ui_stHostPreset";
        Item_ValidateTypeData(item);
        auto choices = item->typeData.multi;
        choices->count = 2;
        choices->cvarList[0] = "Classic JKA";
        choices->cvarList[1] = "Saber Trials";
        choices->cvarValue[0] = 0;
        choices->cvarValue[1] = 1;
        return;
    }
    if (!ST_ClassicLayout()) return;
    itemDef_t *link = NULL;
    if (!Q_stricmp(name,"main"))
        link = ThemeItem(menu,"stExtensions","Saber Trials",{18,440,173,28},"uiScript stThemeExtensions ;");
    else if (!Q_stricmp(name,"ingame"))
        ThemeItem(menu,"stExtensions","Saber Trials",{8,40,146,25},"uiScript stThemeExtensions ;");
    else if (!Q_stricmp(name,"setup_menu"))
        link = ThemeItem(menu,"stInterface","Interface",{80,330,170,24},"open st_theme_interface ;");
    else if (!Q_stricmp(name,"ingame_setup"))
        ThemeItem(menu,"stInterface","Interface",{20,194,168,30},"open st_theme_interface ;");
    if (link) {
        const vec4_t gold = {1,.682f,0,1};
        memcpy(link->window.foreColor,gold,sizeof(gold));
        link->textscale = .9f;
        link->iMenuFont = 3;
        link->textalignment = ITEM_ALIGN_RIGHT;
        link->textalignx = link->window.rectClient.w-10;
    }
}

void ST_AddClassicInterface() {
    if (!ST_ClassicLayout() || Menus_FindByName("st_theme_interface") || menuCount >= MAX_MENUS) return;
    auto menu = &Menus[menuCount];
    Menu_Init(menu);
    menu->window.name = "st_theme_interface";
    menu->window.rect = {152,169,336,130};
    menu->window.flags = WINDOW_POPUP;
    menu->window.style = WINDOW_STYLE_FILLED;
    menu->window.border = WINDOW_BORDER_FULL;
    const vec4_t blue = {.015f,.025f,.16f,1}, edge = {.34f,.45f,.83f,1}, gold = {1,.682f,0,1};
    memcpy(menu->window.backColor,blue,sizeof(blue));
    memcpy(menu->window.borderColor,edge,sizeof(edge));
    memcpy(menu->focusColor,gold,sizeof(gold));
    menu->onESC = "close st_theme_interface ;";
    ThemeItem(menu,"menuTheme","Menu Theme: Classic JKA",{18,12,300,27},"uiScript stThemeModern ;");
    ThemeItem(menu,"allSettings","All interface settings",{18,49,300,27},"uiScript stThemeInterface ;");
    ThemeItem(menu,"back","Back",{18,87,300,27},"close st_theme_interface ;");
    Menu_PostParse(menu);
    ++menuCount;
}
