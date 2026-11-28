"""Fix native list selection drawing without replacing the approved menu shell."""
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Menu selection anchor changed: ' + old[:100])
    return text.replace(old, new)


def apply(root):
    ui = Path(root) / 'codemp/ui'
    path = ui / 'ui_shared.c'
    text = path.read_text()
    text = replace(text, 'extern qboolean ST_LegacyListText(itemDef_t*,float,float,float,const char*);',
        'extern qboolean ST_LegacyListText(itemDef_t*,float,float,float,const char*);\n'
        'extern qboolean ST_LegacyListRow(itemDef_t*,int,float,float,float,float);')
    text = replace(text, '''\t\t\t\tconst char *text;
\t\t\t\t// always draw at least one''', '''\t\t\t\tconst char *text;
#ifdef UI_BUILD
                const qboolean themedRow = ST_LegacyListRow(item, (int)i, x+2,
                    y+listPtr->elementHeight, item->window.rect.w-SCROLLBAR_SIZE-4,
                    listPtr->elementHeight);
#endif
\t\t\t\t// always draw at least one''')
    text = replace(text, '''\t\t\t\tif (i == item->cursorPos)
\t\t\t\t{
\t\t\t\t\tDC->fillRect(x + 2, y + listPtr->elementHeight + 2, item->window.rect.w - SCROLLBAR_SIZE - 4, listPtr->elementHeight, item->window.outlineColor);
\t\t\t\t}''', '''\t\t\t\t// The themed row was painted beneath its text, before the feeder cells.
\t\t\t\tif (i == item->cursorPos
#ifdef UI_BUILD
                    && !themedRow
#endif
                )
\t\t\t\t{
\t\t\t\t\tDC->fillRect(x + 2, y + listPtr->elementHeight + 2, item->window.rect.w - SCROLLBAR_SIZE - 4, listPtr->elementHeight, item->window.outlineColor);
\t\t\t\t}''')
    path.write_text(text)
    path = ui / 'ui_st_legacy.inc'
    text = path.read_text()
    text = replace(text, 'int ST_LegacyItemWindow(itemDef_t* i){',
                   '#include "ui_st_selection.inc"\n\nint ST_LegacyItemWindow(itemDef_t* i){')
    text = replace(text, ' if(r.w<4||r.h<4)return 0;',
                   ' if(r.w<4||r.h<4)return 0;\n if(ST_SelectionSlotWindow(i))return 1;')
    text = replace(text, ' if(!(i->window.flags&WINDOW_DECORATION)&&LUI_Focus(i)&&(LUI_Value(i)||i->type==ITEM_TYPE_OWNERDRAW)){',
        ' if(ST_SelectionSlotText(i,x,y,w,scale,text,color))return qtrue;\n'
        ' if(!(i->window.flags&WINDOW_DECORATION)&&LUI_Focus(i)&&(LUI_Value(i)||i->type==ITEM_TYPE_OWNERDRAW)){')
    start = text.index('qboolean ST_LegacyListText(')
    end = text.index('qboolean ST_LegacyForceRanks(', start)
    text = text[:start] + '''qboolean ST_LegacyListText(itemDef_t* i,float x,float y,float width,const char* s){
 return ST_SelectionListText(i,x,y,width,s);
}
''' + text[end:]
    path.write_text(text)
    shutil.copyfile(HERE / 'ui_st_selection.inc', ui / 'ui_st_selection.inc')


def menu(name, data):
    """Preserve the installed menu's bytes/line endings around targeted colors."""
    if name == 'ui/jamp/createserver.menu':
        data, blue = re.subn(rb'(\bforecolor[ \t]+)0\.65[ \t]+0\.65[ \t]+1[ \t]+1\b',
                             rb'\g<1>.14 .70 1 1', data)
        data, red = re.subn(rb'(\bforecolor[ \t]+)1[ \t]+0\.2[ \t]+0\.2[ \t]+1\b',
                            rb'\g<1>1 .24 .34 1', data)
        # Eight interactive and eight human-only labels per team.
        assert blue == red == 16, (blue, red)
        old = b'outlinecolor .06 .32 .48 .28'
        assert data.count(old) == 1
        return data.replace(old, b'outlinecolor .025 .22 .32 .98')
    if name == 'ui/jamp/ingame_callvote.menu':
        old = b'elementheight 18 elementtype LISTBOX_TEXT'
        assert data.count(old) == 2
        return data.replace(old, b'elementheight 18 outlinecolor .025 .22 .32 .98 elementtype LISTBOX_TEXT')
    raise ValueError('Unexpected menu: ' + name)
