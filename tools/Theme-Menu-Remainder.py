"""Finish the Rules and pause auxiliary menus using the accepted native theme."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('details_theme', ROOT/'tools/Theme-Menu-Details.py')
theme = importlib.util.module_from_spec(spec); spec.loader.exec_module(theme)
SOURCE = ROOT/'development-source/menu/remainder-original'
OUT = ROOT/'dist/menu-remainder-staging'
NAMES = '''rules rules_games rules_force rules_weapons rules_items rules_moves
ingame_join ingame_about ingame_addbot ingame_vote ingame_callvote
ingame_voicechat ingame_objectives quit'''.split()


def multiline(item):
    # Earlier custom vote menus mix compact and multiline definitions. Normalize
    # only property boundaries, never quoted values or nested action scripts.
    keys = set('''name group rect type style background forecolor backcolor
        border bordercolor bordersize outlinecolor visible decoration text font
        textscale textstyle textalign textalignx textaligny cvar cvarTest
        maxChars maxPaintChars cvarFloat cvarFloatList cvarStrList showCvar
        hideCvar enableCvar disableCvar action onFocus leaveFocus mouseEnter
        mouseExit ownerdraw feeder columns elementwidth elementheight'''.lower().split())
    if '\n' in item: return item
    arity = {k:1 for k in keys}
    arity.update(dict.fromkeys('rect forecolor backcolor bordercolor outlinecolor'.split(),4))
    arity.update(dict.fromkeys('decoration'.split(),0))
    arity.update(dict.fromkeys('showcvar hidecvar enablecvar disablecvar action onfocus leavefocus mouseenter mouseexit cvarfloatlist cvarstrlist'.split(),0))
    depth = 0; starts = []; skip = 0
    for m in theme.TOKEN.finditer(item):
        if skip: skip -= 1; continue
        if m[0] == '{': depth += 1
        elif m[0] == '}': depth -= 1
        elif depth == 1 and m[0].lower() in keys:
            starts.append(m.start())
            skip = arity[m[0].lower()]
    for pos in reversed(starts): item = item[:pos]+'\n '+item[pos:]
    return item


def insert_items(s, new):
    pos = theme.blocks(s, 'itemDef')[0][0]
    return s[:pos]+new+s[pos:]


def apply(s, stem):
    for a,b in reversed(theme.blocks(s,'itemDef')):
        s = s[:a]+multiline(s[a:b])+s[b:]
    s = theme.theme_menu(s, stem)
    parts = theme.blocks(s, 'itemDef')
    header = s[:parts[0][0]]
    header = re.sub(r'(?im)^(\s*focusColor)\s+[^\n]*', r'\1 1 1 1 1', header)
    if theme.get(header, 'border') == '1':
        # Header is an open brace, so update inline rather than using prop().
        header += '\n borderSize .5\n bordercolor '+theme.EDGE+'\n'
    cards = {
        'ingame_join': (300,240,'JOIN THE MATCH'),
        'ingame_about': (568,306,'SERVER INFORMATION'),
        'ingame_addbot': (350,240,'ADD A BOT'),
        'ingame_vote': (300,180,'CAST YOUR VOTE'),
    }
    if stem in cards:
        w,h,title = cards[stem]
        header = re.sub(r'(?im)^(\s*rect)\s+[^\n]*',r'\g<1> 28 62 '+f'{w} {h}',header,count=1)
    result = header; cursor = parts[0][0]
    for a,b in parts:
        item = s[a:b]; name = theme.get(item,'name'); r = theme.rect(item)
        if stem in cards and name in ('background_pic','st_editor_popup'):
            item = theme.prop(item,'rect',f'0 0 {w} {h}')
            item = theme.prop(item,'backcolor','0 0 0 0' if name == 'st_editor_popup' else '.008 .026 .044 .90')
        elif stem in cards and r:
            if stem == 'ingame_about' and name == 'about':
                if theme.get(item,'cvar') == 'version':
                    item = theme.prop(item,'rect','18 262 532 18')
                    item = theme.prop(item,'textalign','ITEM_ALIGN_LEFT')
                    item = theme.prop(item,'textalignx','0')
                    item = theme.prop(item,'textaligny','0')
                    item = theme.prop(item,'font','2')
                    item = theme.prop(item,'textscale','.60')
                else:
                    item = theme.prop(item,'rect',f'18 {r[1]+44:g} 532 22')
                    item = theme.prop(item,'textalignx','174')
                    item = theme.prop(item,'textaligny','1')
                    item = theme.prop(item,'textscale','.85')
            else:
                item = theme.prop(item,'rect',f'14 {r[1]+48:g} {w-28} {r[3]:g}')
                if theme.get(item,'text'):
                    item = theme.prop(item,'textscale','.9')
                    item = theme.prop(item,'textaligny','4')
                    if stem == 'ingame_addbot' and theme.get(item,'ownerdraw'):
                        item = theme.prop(item,'textalignx','100')
                    else:
                        item = theme.prop(item,'textalign','ITEM_ALIGN_LEFT')
                        item = theme.prop(item,'textalignx','14')
        if stem.startswith('rules'):
            if name == 'st_editor_section': item = theme.prop(item,'text','"GAME RULES"')
            if name == 'title_glow': item = theme.prop(item,'rect','0 0 0 0')
            if name == 'exitgamebutton':item = theme.prop(item,'text','"Quit game"')
            if stem == 'rules_moves' and name == 'game_rulesheader':
                item = theme.prop(item,'text','"SABER TRIALS  /  MOVES"')
                item = theme.prop(item,'textscale','.80')
            if r and r[0] == 40 and theme.get(item,'text') and theme.get(item,'type') in ('1','ITEM_TYPE_BUTTON'):
                item = theme.prop(item,'textalign','ITEM_ALIGN_LEFT')
                item = theme.prop(item,'textalignx','10')
        if stem == 'quit':
            if name == 'st_editor_section':item = theme.prop(item,'text','"EXIT"')
            if name == 'quit_title':item = theme.prop(item,'text','"LEAVE SABER TRIALS"')
            if name == 'confirm':item = theme.prop(item,'text','"Quit the game and return to your desktop?"')
        result += s[cursor:a]+item; cursor = b
    result += s[cursor:]
    new = ''
    if stem in cards:
        # Draw these after the existing backdrop, so the original named panel
        # cannot cover the title/dividers. Added art never captures input.
        new += theme.box('st_editor_cardedge',0,0,1,h,theme.CYAN)
        new += theme.text('st_editor_cardtitle',title,20,15,w-40,.86,theme.CYAN,4)
        new += theme.box('st_editor_cardline',14,43,w-28,.5,theme.EDGE)
        new += theme.box('st_editor_cardfooter',14,h-30,w-28,.5,theme.EDGE)
        new += theme.text('st_editor_hint','Esc  /  Back',20,h-24,w-40,.64)
        at = result.rfind('}')
        result = result[:at]+new+result[at:]
    elif stem == 'rules':
        new += theme.box('st_editor_rulescard',218,150,204,267,'.008 .026 .044 .78')
        for i in range(5):
            new += theme.box(f'st_editor_rulesline{i}',232,195+i*46.49,176,.5,theme.EDGE)
        # Put cards between the common full-screen backdrop and native content.
        at = next(a for a,b in theme.blocks(result,'itemDef') if theme.get(result[a:b],'name') == 'really_background')
        result = result[:at]+new+result[at:]
    elif stem in ('rules_games','rules_force','rules_weapons','rules_items'):
        new += theme.box('st_editor_rulecategories',32,146,186,267,'.008 .026 .044 .85')
        new += theme.box('st_editor_ruledetails',228,146,380,267,'.008 .026 .044 .85')
        new += theme.box('st_editor_ruleedge',218,146,.5,267,theme.EDGE)
        at = next(a for a,b in theme.blocks(result,'itemDef') if theme.get(result[a:b],'name') == 'really_background')
        result = result[:at]+new+result[at:]
    return result


def generate():
    theme.SOURCE=SOURCE; theme.OUT=OUT; theme.NAMES=NAMES
    theme.capture()
    theme.LABELS.update({'@MENUS_RULES':'GAME RULES','@MENUS_GAMES':'Game types',
        '@MENUS_FORCE_POWERS':'Force powers','@MENUS_ITEMS':'Items','@MENUS_MOVES':'Moves',
        '@MENUS_GAME_RULES_TITLE':'GAME TYPES','@MENUS_FORCE_RULES_TITLE':'FORCE POWERS',
        '@MENUS_WEAPON_RULES_TITLE':'WEAPONS','@MENUS_ITEM_RULES_TITLE':'ITEMS'})
    dest=OUT/'ui/jamp'; dest.mkdir(parents=True,exist_ok=True)
    hashes={}
    for stem in NAMES:
        p=SOURCE/(stem+'.menu'); s=theme.stripped(theme.read_source(p))
        for a,b in reversed(theme.blocks(s,'menuDef')): s=s[:a]+apply(s[a:b],stem)+s[b:]
        s=re.sub(r'\n[ \t]*\n(?:[ \t]*\n)+','\n\n',s)
        (dest/p.name).write_text('// Saber Trials; generated by Theme-Menu-Remainder.py\n'+s,encoding=theme.source_encoding(p))
        hashes[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    (SOURCE/'manifest.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print(f'Generated {len(NAMES)} matching Rules/pause menus in {OUT}')


if __name__=='__main__': generate()
