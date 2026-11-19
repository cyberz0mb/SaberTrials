"""Reproducible presentation-only skin for the existing native menu editors.

The input snapshots retain the working actions, cvars, feeders and custom controls.
Never regenerate snapshots from already themed installed files.
"""
from pathlib import Path
import json
import re
import hashlib
import zipfile
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'development-source/menu/details-original'
OUT = ROOT / 'dist/menu-details-staging'
NAMES = '''player player2 saber controls setup demo joinserver createserver
quickgame quickgame2 quickbots advancedcreateserver ingame_controls ingame_setup
ingame_player ingame_player2 ingame_playerforce ingame_saber password password_request
createfavorite serverinfo findplayer videodriver vid_warning'''.split()
CYAN = '.30 .78 1 1'
PALE = '.76 .86 .93 1'
EDGE = '.22 .49 .64 .65'
PANEL = '.008 .026 .044 .91'
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/|[^\s{}]+|[{}]')
NUM = r'-?(?:\d*\.)?\d+'
VEC = rf'({NUM})\s+({NUM})\s+({NUM})\s+({NUM})'

def read_source(p):
    data=p.read_bytes()
    try:return data.decode('utf-8-sig')
    except UnicodeDecodeError:return data.decode('cp1252')

def source_encoding(p):
    try:p.read_bytes().decode('utf-8-sig');return 'utf-8'
    except UnicodeDecodeError:return 'cp1252'

def stripped(s):
    return ''.join(' ' * len(m[0]) if m[0].startswith(('//','/*')) else m[0]
                   for m in re.finditer(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/|[\s\S]',s))

def blocks(s, key):
    tokens=list(TOKEN.finditer(s)); result=[]
    for i,t in enumerate(tokens):
        if t[0].lower()!=key.lower(): continue
        assert tokens[i+1][0]=='{'
        depth=0
        for end in tokens[i+1:]:
            if end[0]=='{': depth+=1
            elif end[0]=='}':
                depth-=1
                if not depth:
                    result.append((t.start(),end.end()));break
        else: raise ValueError('Unclosed '+key)
    return result

def get(s,key):
    # Properties precede event scripts in these editor files.
    m=re.search(r'(?im)^\s*'+key+r'\s+("[^"]*"|[^\s{}]+)',s)
    return m[1].strip('"') if m else ''

def prop(s,key,value):
    p=r'(?im)^(\s*)'+key+r'\s+[^\r\n]*'
    if re.search(p,s): return re.sub(p,lambda m:m[1]+key+' '+value,s,count=1)
    return s[:s.rfind('}')]+f'\n {key} {value}\n'+s[s.rfind('}'):]

def rect(s):
    m=re.search(r'(?im)^\s*rect\s+'+VEC,s)
    return list(map(float,m.groups())) if m else None

def fmt(v): return f'{v:g}'

def colors(s):
    def replace(m):
        key=m[1];r,g,b,a=map(float,m.groups()[1:])
        if a==0: return m[0]
        if key.lower()=='bordercolor':v=EDGE
        elif key.lower()=='outlinecolor':v='.06 .32 .48 .28'
        elif key.lower()=='descColor'.lower():v='.55 .72 .83 1'
        elif key.lower()=='backcolor':
            v=('.06 .25 .37 .82' if max(r,g,b)>=.4 and abs(r-g)<.02 and abs(g-b)<.02
               else PANEL)
        elif (abs(r-.615)<.015 and abs(g-.615)<.015) or (r>.7 and .5<g<.75 and b<.3): v=PALE
        elif (r>.9 and .5<g<.75 and b<.05) or (b>.95 and .5<r<.56 and g>.8): v=CYAN
        else:return m[0] # Preserve team colours, player colours and neutral image tints.
        return key+' '+v
    return re.sub(r'\b(forecolor|backcolor|bordercolor|outlinecolor|descColor)\s+'+VEC,replace,s,flags=re.I)

def art(name,x,y,w,h,texture):
    return f'itemDef {{\n name "{name}"\n rect {x} {y} {w} {h}\n style 3\n background "{texture}"\n forecolor 1 1 1 1\n visible 1\n decoration\n}}\n'
def box(name,x,y,w,h,color):
    return f'itemDef {{\n name "{name}"\n rect {x} {y} {w} {h}\n style 1\n backcolor {color}\n visible 1\n decoration\n}}\n'
def text(name,label,x,y,w,scale,color=PALE,font=2):
    return f'itemDef {{\n name "{name}"\n rect {x} {y} {w} 22\n text "{label}"\n font {font}\n textscale {scale}\n forecolor {color}\n visible 1\n decoration\n}}\n'

LABELS={
 '@MENUS_PLAY':'Play','@MENUS_PROFILE':'Profile','@MENUS_CONTROLS2':'Controls','@MENUS_SETUP':'Setup',
 '@MENUS_CONTROLS':'Controls',
 '@MENUS_MOVEMENT':'Movement','@MENUS_INTERACTION':'Interaction','@MENUS_WEAPONS':'Weapons',
 '@MENUS_FORCE_POWERS_1':'Force powers I','@MENUS_FORCE_POWERS_2':'Force powers II',
 '@MENUS_MOUSE_JOYSTICK':'Mouse / joystick','@MENUS_OTHER':'Other',
 '@MENUS_VIDEO':'Video','@MENUS_MORE_VIDEO':'More video','@MENUS_SOUND':'Sound',
 '@MENUS_OPTIONS':'Game options','@MENUS_MODS':'Mods','@MENUS_DEFAULTS':'Defaults',
 '@MENUS_BACK':'Back','@MENUS_EXIT':'Main menu','@MENUS_NEXT':'Next','@MENUS_BEGIN':'Begin match',
 '@MENUS_ADVANCED':'Advanced','@MENUS_APPLY_CAPS':'Apply','@MENUS_PLAY_DEMO':'Play recording',
 '@MENUS_DEMOS':'RECORDINGS','@MENUS_CONFIGURE_CONTROLS':'CONTROLS',
 '@MENUS_SETUP_OPTIONS':'SETUP','@MENUS_CHARACTER_MODEL':'CHARACTER',
 '@MENUS_JOIN_A_GAME_IN_PROGRESS':'SABER TRIALS  /  FIND A SERVER',
 '@MENUS_CREATE_A_NEW_MULTIPLAYER':'SABER TRIALS  /  HOST A MATCH',
 '@MENUS_SOLO_GAME':'SABER TRIALS  /  SOLO MATCH',
}

def theme_item(s,tabbed):
    name=get(s,'name');bg=get(s,'background');r=rect(s)
    # Keep named decorative targets available to old show/hide scripts.
    obsolete=['gfx/menus/main_centerblue','gfx/menus/menu_side_text','gfx/menus/menu_side_text_right',
              'gfx/menus/main_background','gfx/menus/jediacademy','gfx/menus/menu_boxes_left','gfx/menus/menu_boxes_right',
              'gfx/menus/charmenu','gfx/menus/charmenu_bottom','gfx/menus/sabermenu_back']
    if bg in obsolete:
        s=prop(s,'background','"ui/assets/sabertrials/blank"');s=prop(s,'rect','0 0 0 0');return s
    if bg.startswith(('gfx/menus/menu_blendbox','gfx/menus/menu_buttonback')):
        if get(s,'text'):
            s=prop(s,'style','0');s=re.sub(r'(?im)^\s*background\s+[^\r\n]*','',s)
        else:s=prop(s,'background','"ui/assets/sabertrials/focus"')
    if bg in ('gfx/menus/menu_box_ingame','gfx/menus/menu_boxred') or bg.startswith('gfx/menus/sabermenu_box'):
        s=prop(s,'style','1');s=re.sub(r'(?im)^\s*background\s+[^\r\n]*','',s)
        s=prop(s,'backcolor',PANEL);s=prop(s,'border','1');s=prop(s,'bordersize','.5');s=prop(s,'bordercolor',EDGE)
        if bg=='gfx/menus/menu_box_ingame':s=prop(s,'backcolor','.008 .026 .044 .84')
        if bg.startswith('gfx/menus/sabermenu_box_'):s=prop(s,'border','0')
    if bg=='gfx/mp/custom_mp_default':
        s=prop(s,'background','"ui/assets/sabertrials/player"')
    if name=='customtitle':s=prop(s,'text','"Customize"')
    if get(s,'border')=='1':s=prop(s,'bordersize','.5')
    if name not in ('humanbotfield','humanbotnonfield'):
        s=re.sub(r'\bforecolor\s+0?\.65\s+0?\.65\s+1\s+1', 'forecolor '+PALE,s)
    if get(s,'font')=='3':
        s=prop(s,'font','2');scale=float(get(s,'textscale') or 1)
        s=prop(s,'textscale',fmt(min(scale,.92)))
    if get(s,'text') in LABELS:s=prop(s,'text','"'+LABELS[get(s,'text')]+'"')
    if get(s,'textstyle')=='3':s=prop(s,'textstyle','0')
    if name in ('movementcontrolbutton','attackcontrolbutton','weaponscontrolbutton','forcecontrolbutton',
                'forcecontrolbutton2','mousejoystickcontrolbutton','othercontrolbutton') or get(s,'group')=='setup_submenu':
        s=prop(s,'textalign','ITEM_ALIGN_LEFT');s=prop(s,'textalignx','12');s=prop(s,'textscale','.82')
    if r and tabbed and r[1]>=126 and r[1]<422:
        # Compact masthead and increase editor spacing; native hitboxes follow.
        r[1]=78+(r[1]-126)*344/296
        r[3]*=344/296
        s=prop(s,'rect',' '.join(fmt(n) for n in r))
    return s

def theme_menu(s,stem):
    s=colors(s)
    if stem in ('saber','ingame_saber'):
        s=re.sub(r'\bforecolor\s+0?\.65\s+0?\.65\s+1\s+1','forecolor '+PALE,s)
    parts=blocks(s,'itemDef'); header=s[:parts[0][0]]
    tabbed=any(get(s[a:b],'name')=='starwars' for a,b in parts)
    full=get(header,'fullScreen').lower() in ('1','menu_true')
    new=''
    if full:
        new+=art('st_editor_arena',0,0,640,480,'ui/assets/sabertrials/arena.tga')
        new+=box('st_editor_shade',0,0,640,480,'.004 .014 .025 .83')
        new+=box('st_editor_edge',12,12,1,454,'.30 .78 1 .6')
        new+=box('st_editor_footer',24,438,592,.5,EDGE)
    if tabbed:
        new+=text('st_editor_brand','S A B E R   T R I A L S',26,18,450,1,CYAN,3)
        sub={'player':'PLAYER PROFILE','player2':'CUSTOMIZE CHARACTER','saber':'SABER LOADOUT',
             'controls':'CONTROLS','setup':'SETUP','demo':'MATCH RECORDINGS'}.get(stem,'MULTIPLAYER')
        new+=text('st_editor_section',sub,28,50,520,.68)
        new+=box('st_editor_nav',20,77,600,29,'.02 .075 .115 .8')
        new+=box('st_editor_navline',20,106,600,.5,EDGE)
        active={'player':1,'player2':1,'saber':1,'controls':2,'setup':3,'demo':0}.get(stem,0)
        new+=box('st_editor_active',[7,170,340,502][active]+14,104,102,1,CYAN)
        if stem in ('controls','setup'):
            new+=box('st_editor_categories',80,146,170,272,'.008 .026 .044 .82')
            new+=box('st_editor_categoryedge',80,146,.5,272,EDGE)
            for i in range(7 if stem=='controls' else 6):
                new+=box(f'st_editor_categoryline{i}',88,174+i*27.89,154,.4,'.22 .49 .64 .35')
    if stem=='player2':
        new+=box('st_editor_species',24,80,315,45,PANEL)
        new+=box('st_editor_colors',24,138,315,94,PANEL)
        new+=box('st_editor_appearance',24,244,315,178,PANEL)
        new+=box('st_editor_preview',354,80,268,342,PANEL)
    if stem=='saber':new+=box('st_editor_saberpreview',18,236,604,187,PANEL)
    # Dark card behind popup content, including otherwise empty dialog windows.
    if not full:
        r=rect(header)
        covered=r and any(rect(s[a:b])==[0,0,r[2],r[3]] and (get(s[a:b],'background') or get(s[a:b],'backcolor')) for a,b in parts)
        if r and not covered:new+=box('st_editor_popup',0,0,fmt(r[2]),fmt(r[3]),'.004 .014 .025 .45')
    cursor=parts[0][0]; result=s[:cursor]+new
    for a,b in parts:
        themed=theme_item(s[a:b],tabbed)
        if stem=='player2' and get(themed,'name')=='character':
            themed=prop(themed,'rect','354 84 268 330')
            themed=prop(themed,'model_g2mins','-30 -15 -14')
        result+=s[cursor:a]+themed;cursor=b
    result+=s[cursor:]
    if tabbed:
        # Hover rectangle commands share the transformed item coordinates.
        def move(m):
            x,y,w,h=map(float,m.groups()[1:])
            if 126<=y<422:y=78+(y-126)*344/296;h*=344/296
            return m[1]+' '+' '.join(fmt(v) for v in (x,y,w,h))
        result=re.sub(r'(setitemrect\s+\S+)\s+'+VEC,move,result,flags=re.I)
    result=re.sub(r'(?im)^(\s*descScale)\s+\S+',r'\1 .8',result)
    return result

def capture():
    SOURCE.mkdir(parents=True,exist_ok=True)
    for name in NAMES:
        dest=SOURCE/(name+'.menu')
        if dest.exists():continue
        rel='ui/jamp/'+dest.name;data=None
        for folder in (ROOT.parent/'base',ROOT):
            for pk3 in sorted(folder.glob('*.pk3'),key=lambda p:p.name.lower()):
                with zipfile.ZipFile(pk3) as z:
                    if rel in z.namelist():data=z.read(rel)
        if (ROOT/rel).exists():data=(ROOT/rel).read_bytes()
        if data is None:raise FileNotFoundError(rel)
        dest.write_bytes(data)

def make_art():
    dest=OUT/'ui/assets/sabertrials';dest.mkdir(parents=True,exist_ok=True)
    Image.new('RGBA',(2,2)).save(dest/'blank.tga')
    dest=OUT/'gfx/menus';dest.mkdir(parents=True,exist_ok=True)
    c=(109,204,249,255);edge=(51,101,130,255)
    for name in ['scrollbar','scrollbar_thumb','scrollbar_arrow_up_a','scrollbar_arrow_dwn_a','scrollbar_arrow_left','scrollbar_arrow_right']:
        im=Image.new('RGBA',(64,64));d=ImageDraw.Draw(im)
        d.rectangle((20,0,43,63),fill=(5,22,33,230))
        if name=='scrollbar_thumb':d.rounded_rectangle((23,5,40,58),radius=7,fill=c)
        elif 'arrow' in name:
            pts=[(19,36),(32,23),(45,36)]
            if 'dwn' in name:pts=[(x,64-y) for x,y in pts]
            if 'left' in name:pts=[(y,x) for x,y in pts]
            if 'right' in name:pts=[(64-y,x) for x,y in pts]
            d.line(pts,fill=c,width=4)
        else:d.line((31,0,31,64),fill=edge,width=2)
        im.save(dest/(name+'.tga'))
        if name in ('scrollbar','scrollbar_thumb'):
            # The stock shader may resolve the original JPEG name explicitly.
            im.convert('RGB').save(dest/(name+'.jpg'),quality=95)
    dest=OUT/'menu/new';dest.mkdir(parents=True,exist_ok=True)
    im=Image.new('RGB',(256,32));d=ImageDraw.Draw(im)
    d.rounded_rectangle((2,13,253,18),radius=2,fill=(52,106,137));im.save(dest/'slider.tga')
    im=Image.new('RGB',(32,64));d=ImageDraw.Draw(im)
    d.rounded_rectangle((7,9,24,54),radius=7,fill=(89,194,250));im.save(dest/'sliderthumb.tga')

def generate():
    capture();target=OUT/'ui/jamp';target.mkdir(parents=True,exist_ok=True)
    manifest={}
    for name in NAMES:
        p=SOURCE/(name+'.menu');s=stripped(read_source(p))
        for a,b in reversed(blocks(s,'menuDef')):s=s[:a]+theme_menu(s[a:b],name)+s[b:]
        s=re.sub(r'\n[ \t]*\n(?:[ \t]*\n)+','\n\n',s)
        (target/p.name).write_text('// Saber Trials presentation skin; generated by Theme-Menu-Details.py\n'+s,encoding=source_encoding(p))
        manifest[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    make_art()
    (SOURCE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Generated {len(NAMES)} native editor menus and matching controls in {OUT}')

if __name__=='__main__':generate()
