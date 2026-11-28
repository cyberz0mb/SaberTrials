"""Replay the November 23 layout corrections on the matching client UI."""
import re
from pathlib import Path

RULES = ("rules", "rules_games", "rules_force", "rules_items", "rules_weapons")
MENUS = tuple(f"ui/jamp/{name}.menu" for name in (*RULES, "createserver", "ingame_callvote"))

PUG = (
    "PICKUP GAMES\nPlayers start as spectators. Open Pause > PUG Queue > Join Queue "
    "to play. The server fills the smallest teams first. Bots can hold places until a human is waiting.\n\n"
    "ROUND ROTATION\nAt round end, a waiting player replaces a team's lowest scorer. Ties rotate "
    "the player who has held a spot longer. Benched players move to the back of the queue. "
    "With an empty queue, the teams stay in.\n\n"
    "INACTIVITY\nIdle players return to spectator after a warning. Waiting and watching preserve your queue position.\n\n"
    "ACCOUNT POINTS\nOn an enrolled server with account scoring, signed-in players earn one point for "
    "finishing a round they started, plus one for winning."
)
LADDER = (
    "FIRST TO TEN\nTwo players fight for ten duel-round wins. Everyone else waits. "
    "New arrivals enter at the bottom. An asterisk means a player has yet to finish a series.\n\n"
    "MOVING UP\nThe arena rotates through neighboring ranks. The first pass pairs 1 vs 2, 3 vs 4, "
    "and so on. The next pass starts at 2 vs 3. The lower-ranked player takes the higher spot by winning.\n\n"
    "LEAVING AND RETURNING\nA disconnect cancels an unfinished series. Players below the vacated spot "
    "move up. A returning player enters at the bottom.\n\n"
    "ACCOUNT POINTS\nOn an enrolled server with account scoring, signed-in players earn one point for "
    "finishing a series they started, plus one for winning. Ladder position belongs to this server session."
)
TOKEN = re.compile(r'//[^\r\n]*|"(?:\\.|[^"\\])*"|[{}]|[^\s{}"]+')


def blocks(text):
    """Yield complete item definitions, including nested action blocks."""
    tokens = [m for m in TOKEN.finditer(text) if not m.group().startswith("//")]
    for index, token in enumerate(tokens[:-1]):
        if token.group().lower() != "itemdef" or tokens[index + 1].group() != "{":
            continue
        depth = 1
        for match in tokens[index + 2:]:
            depth += (match.group() == "{") - (match.group() == "}")
            if depth == 0:
                yield token.start(), match.end(), text[token.start():match.end()]
                break
        else:
            raise ValueError("Unclosed itemDef")


def field(item, key, value):
    edited, count = re.subn(rf"(?im)^(\s*{key}\s+)[^\n]+", lambda m: m[1] + value,
                            item, count=1)
    return edited if count else item[:-1] + f"\n {key} {value}\n" + item[-1:]


def item_name(item):
    match = re.search(r'(?im)^\s*name\s+"?([\w]+)', item)
    return match[1].lower() if match else ""


def edit_items(text, update):
    for start, end, item in reversed(list(blocks(text))):
        text = text[:start] + update(item_name(item), item) + text[end:]
    return text


MODES = ("ffa", "duel", "pduel", "teamffa", "ctf", "siege", "tournament", "pug", "ladder")


def new_mode(mode, title, description):
    return f'''
        itemDef {{
            name {mode}menubutton
            group game_submenu
            type ITEM_TYPE_BUTTON
            text "{title}"
            font 2
            forecolor .76 .86 .93 1
            visible 1
            action {{
                play "sound/interface/button1.wav" ;
                setitemcolor game_submenu forecolor .76 .86 .93 1 ;
                setitemcolor {mode}menubutton forecolor 1 1 1 1 ;
                hide gamedesc ;
                show {mode}_desc ;
            }}
        }}
        itemDef {{
            name {mode}_desc
            group gamedesc
            type ITEM_TYPE_TEXTSCROLL
            text "{description.replace(chr(10), r'\n')}"
            font 4
            visible 0
        }}
'''


def rules_page(text, page):
    if page == "rules_games":
        anchor = next(s for s, _, b in blocks(text) if item_name(b) == "tournament_desc")
        text = text[:anchor] + new_mode("pug", "PUG", PUG) + new_mode("ladder", "LADDER", LADDER) + text[anchor:]
    nav = dict(playbutton=28, newgamebutton=28, profilebutton=176, controlsbutton=324, setupbutton=472)

    def update(name, item):
        if name in {"st_editor_nav", "st_editor_navline", "st_editor_active", "default_rulesheader"}:
            return ""
        if name in nav:
            return field(item, "rect", f"{nav[name]} 77 140 27")
        if page != "rules_games":
            return item
        if name in {"st_editor_ruledetails", "st_editor_ruleedge", "setup_background"} or name.startswith("mainhighlight"):
            return ""
        if name == "st_editor_rulecategories":
            return field(item, "rect", "28 141 184 274")
        if name.endswith("menubutton") and name[:-10] in MODES:
            index = MODES.index(name[:-10])
            item = re.sub(r"(?im)^\s*descText\s+[^\n]+", "", item, count=1)
            item = field(item, "rect", f"38 {149+29*index} 164 25")
            item = field(item, "textscale", ".72")
            item = field(item, "textalign", "ITEM_ALIGN_LEFT")
            item = field(item, "textalignx", "10")
            return field(item, "textaligny", "3")
        if name.endswith("_desc") and name[:-5] in MODES:
            for key, value in (("rect", "224 141 388 274"), ("font", "4"),
                               ("textscale", ".88"), ("textalignx", "7"),
                               ("textaligny", "9"), ("lineHeight", "15"),
                               ("forecolor", ".85 .92 .96 1")):
                item = field(item, key, value)
            return item
        return item
    text = edit_items(text, update)
    if page == "rules_games":
        # Old decorative hover glows are superseded by the native focus art.
        text = re.sub(r"(?im)^\s*(?:show|hide)\s+mainhighlight\d+\s*;?", "", text)
    return text


def menus(root, output):
    for relative in MENUS:
        path = root / relative
        text = path.read_text(encoding="utf-8")
        if path.stem in RULES:
            text = rules_page(text, path.stem)
        elif path.stem == "createserver":
            # Map cards finish above the Gameplay select. Hover help has its own row.
            for old, new in (("204 244 429 178", "209 244 419 151"),
                             ("2 244 200 178", "12 244 188 151"),
                             ("314 254 210 158", "325 248 188 141"),
                             ("313 253 212 160", "324 247 190 143"),
                             ("@MENUS_UPDATE_ADVANCED_SERVER", '"Combat, Force, bots and server settings."')):
                text = replace(text, old, new)
            text = re.sub(r"(?im)^(\s*descY\s+)424\b", r"\g<1>426", text, count=1)
            text = re.sub(r"(?im)^(\s*descScale\s+)\.8\b", r"\g<1>.65", text, count=1)
        elif path.stem == "ingame_callvote":
            text = replace(text, '"Open Tournament registration."', '"Vote to open registration for this server\'s bracket."')
            text = replace(text, '"Close registration and start the Tournament."', '"Vote to close registration and build the bracket."')
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Expected one menu layout anchor: {old[:110]}")
    return text.replace(old, new, 1)


def patch_ui(frontend):
    root = frontend / "codemp/ui"

    def edit(filename, *edits):
        path = root / filename
        text = path.read_text(encoding="utf-8")
        for old, new in edits:
            text = replace(text, old, new)
        path.write_text(text, encoding="utf-8")

    edit("menu_items.inc",
         ('"Gameplay",{215,414,270,22},',
          '"Gameplay",ST_ClassicLayout() ? rectDef_t{215,414,270,22} : rectDef_t{217,399,206,23},'))
    edit("ui_st_workbench.inc", ('"Inspect hilt", SWB_Inspect', '"Inspect", SWB_Inspect'),
         ('SWB_Text(r, label, .66f, SWB_Locked(action,value) ? scuMuted : focus || selected ? ruCyan : ruWhite, true);',
          'RUI_ButtonLabel(r.x, r.y, r.w, r.h, .66f, label,\n\t\tSWB_Locked(action,value) ? scuMuted : focus || selected ? ruCyan : ruWhite);'))
    edit("ui_st_saber_inspect.inc", ('"Inspect hilt", ruCyan', '"Inspect", ruCyan'),
         ('''const float scale = .65f;
	RUI_Text(rect.x + (rect.w - RUI_Width(label, scale)) / 2,
		rect.y + 6, scale, label, hover ? ruCyan : ruWhite);''',
          'RUI_ButtonLabel(rect.x, rect.y, rect.w, rect.h, .65f, label, hover ? ruCyan : ruWhite);'))
    edit("ui_st_rich.inc", ('static bool RUI_Motion()', '''// The atlas ink spans about 4 to 47 pixels from the draw origin, at .43 units per pixel.
static void RUI_ButtonLabel(float x, float y, float w, float h, float scale,
                            const char* text, const float* color, int align = ITEM_ALIGN_CENTER) {
 const float inset = std::min(12.f, w * .12f);
 const float available = w - 2 * inset;
 scale = std::min(scale, (h - 5.f) / 22.f);
 float width = RUI_Width(text, scale);
 if (width > available) {
  scale *= available / width;
  width = RUI_Width(text, scale);
 }
 const float left = align == ITEM_ALIGN_LEFT ? x + inset :
                    align == ITEM_ALIGN_RIGHT ? x + w - inset - width : x + (w - width) * .5f;
 RUI_Text(left, y + h * .5f - 10.8f * scale, scale, text, color);
}
static bool RUI_Motion()'''))
    edit("ui_st_legacy.inc", ('if(LUI_Button(i)&&i->text2==NULL){', '''if(LUI_Button(i)&&i->text2==NULL){
  const bool rules = !Q_stricmpn(m->window.name, "rulesMenu", 9);
  const bool host = LUI_Name(m->window.name, "createserver");
  const bool votes = LUI_Name(m->window.name, "ingame_callvote");
  if (rules || host || votes) {
   const bool alignedLeft = LUI_Name(i->window.group, "game_submenu");
   const bool alignedRight = LUI_Name(i->window.group, "grpbutton");
   const bool selected = LUI_Selected(i);
   const bool focus = LUI_Focus(i);
   vec4_t ink;
   MSUI_Color(ink, selected, focus, color[0] > .4f || color[1] > .4f);
   ink[3] = color[3];
   RUI_Control(r.x+1, r.y+1, r.w-2, r.h-2, "action", LUI_Primary(i->window.name) || selected, focus);
   const float labelScale = std::min(.83f, r.h / 34.f);
   RUI_ButtonLabel(r.x, r.y, r.w, r.h, labelScale, text, ink,
                   alignedLeft ? ITEM_ALIGN_LEFT : alignedRight ? ITEM_ALIGN_RIGHT : ITEM_ALIGN_CENTER);
   return qtrue;
  }'''))
    edit("ui_st_match_rules.inc", ('SCUI_Centered(x,y,w,h,.57f,text.c_str(),ink);MRUI_Hit(x,y,w,h,action,a,b);',
                                  '''if ((action == MR_PREV || action == MR_NEXT) && (text == "^" || text == "v")) {
  const float aspect = uiInfo.uiDC.yscale / uiInfo.uiDC.xscale;
  const float midX = x + w * .5f, midY = y + h * .5f;
  const float direction = action == MR_PREV ? 1.f : -1.f;
  for (int col = -4; col <= 4; ++col) {
   const float offset = direction * (std::abs(col) - 2) * .85f;
   UI_FillRect(midX + (col - .5f) * aspect, midY + offset - .7f, aspect, 1.4f, ink);
  }
 } else {
  RUI_ButtonLabel(x, y, w, h, .57f, text.c_str(), ink);
 }
 MRUI_Hit(x,y,w,h,action,a,b);'''))
    edit("ui_shared.c",
         ('int Item_TextScroll_MaxScroll ( itemDef_t *item )', '''static bool Item_GameRulesText(const itemDef_t *item) {
 const auto* menu = static_cast<const menuDef_t*>(item->parent);
 return menu && menu->window.name && !Q_stricmp(menu->window.name, "rulesMenu_games");
}

int Item_TextScroll_MaxScroll ( itemDef_t *item )'''),
         ('int count = scrollPtr->iLineCount;\n\tint max', '''int count = scrollPtr->iLineCount;
 if (Item_GameRulesText(item) && scrollPtr->lineHeight > 0) {
  const int available = static_cast<int>(item->window.rect.h - item->textaligny - 8);
  const int lastPage = count - available / scrollPtr->lineHeight;
  return lastPage > 0 ? lastPage : 0;
 }
 int max'''),
         ('count = scrollPtr->iLineCount;\n\n\t// draw scrollbar to right side of the window',
          '''count = scrollPtr->iLineCount;
 const bool gameRules = Item_GameRulesText(item);
 const int lastPage = Item_TextScroll_MaxScroll(item);
 if (gameRules && scrollPtr->startPos > lastPage) scrollPtr->startPos = lastPage;
 scrollPtr->endPos = scrollPtr->startPos;

 if (!gameRules || lastPage > 0) {
	// draw scrollbar to right side of the window'''),
         ('DC->drawHandlePic(x, thumb, SCROLLBAR_SIZE, SCROLLBAR_SIZE, DC->Assets.scrollBarThumb);\n\n\tif (item->cvar)',
          'DC->drawHandlePic(x, thumb, SCROLLBAR_SIZE, SCROLLBAR_SIZE, DC->Assets.scrollBarThumb);\n }\n\n\tif (item->cvar)'),
         ('size = item->window.rect.h - 2;\n\tx\t = item->window.rect.x + item->textalignx + 1;',
          'size = item->window.rect.h - (gameRules ? item->textaligny + 8 : 2);\n\tx\t = item->window.rect.x + item->textalignx + 1;'),
         ('int iBoxWidth = item->window.rect.w - SCROLLBAR_SIZE - 10;',
          'int iBoxWidth = item->window.rect.w - SCROLLBAR_SIZE - 10;\n\tif (Item_GameRulesText(item)) iBoxWidth -= item->textalignx;'))
