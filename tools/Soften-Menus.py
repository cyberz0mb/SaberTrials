"""Apply the accepted soft-edge style across the native menu collection.

Only presentation properties change; controls, geometry, actions and data
bindings are retained. Run this last after the earlier menu generators.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import shutil
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'development-source/menu/soft-original'
OUT=ROOT/'dist/menu-soft-staging'
ART=OUT/'ui/assets/sabertrials'

def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

theme=module('theme','Theme-Menu-Details.py')
MASKS={name:'ui/assets/sabertrials/soft_'+name for name in ['panel','line','edge']}
ARITY={key:1 for key in '''name group text desctext background font textscale textalign
    textalignx textaligny textstyle style border bordersize visible fullscreen
    cvar cvartest ownerdraw feeder type maxchars maxpaintchars descx descy descscale
    descalignment appearanceincrement appearanceslot elementwidth elementheight
    elementtype special align widescreen horizontalscroll'''.split()}
ARITY.update({key:4 for key in ['rect','forecolor','backcolor','bordercolor',
    'outlinecolor','focuscolor','disablecolor','desccolor','cvarfloat']})

def property_span(s,key,count=1):
    tokens=[t for t in theme.TOKEN.finditer(s) if not t[0].startswith(('//','/*'))]
    depth=0;i=0
    while i<len(tokens):
        t=tokens[i]
        if t[0]=='{':depth+=1
        elif t[0]=='}':depth-=1
        elif depth==1 and t[0].lower()==key.lower():
            return tokens[i+1].start(),tokens[i+count].end()
        elif depth==1 and t[0].lower() in ARITY:
            # A property value can itself be a keyword (e.g. name background).
            i+=ARITY[t[0].lower()]
        i+=1
    return None

def get(s,key,count=1):
    span=property_span(s,key,count)
    return s[span[0]:span[1]].strip('"') if span else ''

def put(s,key,value,count=1):
    span=property_span(s,key,count)
    if span:return s[:span[0]]+value+s[span[1]:]
    pos=s.index('{')+1
    return s[:pos]+f'\n {key} {value}\n'+s[pos:]

def rect(s):
    value=get(s,'rect',4)
    return list(map(float,value.split())) if value else [0,0,0,0]

def soften(s,header=False):
    name=get(s,'name');style=get(s,'style');bg=get(s,'background')
    x,y,w,h=rect(s)
    if get(s,'type') in ['ITEM_TYPE_EDITFIELD','ITEM_TYPE_NUMERICFIELD','4','9']:return s
    # Already accepted pause-rail artwork remains untouched.
    if bg.startswith('ui/assets/sabertrials/pause_'):return s
    if name=='rail_edge':
        s=put(s,'background','"'+MASKS['edge']+'"')
    # Keep full-screen dimming, pictures, movies, model previews and small
    # editable fields intact. A field's border communicates its click target.
    elif name in ['shade','movie_shade','st_editor_shade'] or (w>=640 and h>=480 and not header):
        return s
    elif style in ['1','WINDOW_STYLE_FILLED'] and not bg:
        if w>=30 and 0<h<=2:
            s=put(s,'background','"'+MASKS['line']+'"')
        elif h>=30 and 0<w<=2:
            s=put(s,'background','"'+MASKS['edge']+'"')
        elif (w>=80 and h>2) or (w>=24 and h>=35):
            s=put(s,'background','"'+MASKS['panel']+'"')
        else:return s
    elif w>=24 and h>=35 and not bg and get(s,'border') not in ['', '0','WINDOW_BORDER_NONE']:
        # Empty decorative frames also need their hard outline removed.
        pass
    elif bg=='ui/assets/sabertrials/focus':
        # The shared focus texture is replaced by the accepted fading one.
        pass
    else:
        return s
    if get(s,'border') not in ['','0','WINDOW_BORDER_NONE']:
        # Preserve border width and client-coordinate offsets, removing only
        # the hard outline. This keeps mouse hitboxes and text positions exact.
        s=put(s,'bordercolor','0 0 0 0',4)
        # Legacy focus scripts can restore a list's old rectangular frame.
        s=re.sub(r'(\bsetitemcolor\s+\S+\s+bordercolor\s+)(?:[-.\d]+\s+){3}[-.\d]+',
                 r'\g<1>0 0 0 0',s,flags=re.I)
    return s

def transform(s):
    for a,b in reversed(theme.blocks(s,'menuDef')):
        menu=s[a:b]
        for c,d in reversed(theme.blocks(menu,'itemDef')):
            menu=menu[:c]+soften(menu[c:d])+menu[d:]
        menu=soften(menu,header=True)
        s=s[:a]+menu+s[b:]
    return s

def smooth(v):
    v=max(0,min(1,v));return v*v*(3-2*v)

def artwork():
    ART.mkdir(parents=True,exist_ok=True)
    # Reuse the user's accepted rail and hover treatment consistently.
    for src,dest in [('pause_rail','rail'),('pause_focus','focus')]:
        shutil.copy2(SOURCE/(src+'.tga'),ART/(dest+'.tga'))
    image=Image.new('RGBA',(512,512));pixels=image.load()
    for y in range(512):
        vertical=smooth(y/20)*smooth((511-y)/28)
        for x in range(512):
            alpha=smooth(x/14)*smooth((511-x)/40)*vertical
            pixels[x,y]=(255,255,255,round(255*alpha))
    image.save(ART/'soft_panel.tga')
    image=Image.new('RGBA',(512,8));draw=ImageDraw.Draw(image)
    for x in range(512):
        draw.line((x,0,x,7),fill=(255,255,255,round(255*(1-smooth((x-170)/341)))))
    image.save(ART/'soft_line.tga')
    image=Image.new('RGBA',(8,256));draw=ImageDraw.Draw(image)
    for y in range(256):
        draw.line((0,y,7,y),fill=(255,255,255,round(255*smooth(y/22)*smooth((255-y)/28))))
    image.save(ART/'soft_edge.tga')

def main():
    SOURCE.mkdir(parents=True,exist_ok=True)
    target=OUT/'ui/jamp';target.mkdir(parents=True,exist_ok=True)
    changes={}
    for live in sorted((ROOT/'ui/jamp').glob('*.menu')):
        original=SOURCE/live.name
        if not original.exists():shutil.copy2(live,original)
        before=theme.read_source(original)
        after=transform(before)
        (target/live.name).write_text(after,encoding=theme.source_encoding(original),newline='\n')
        changes[live.name]=before!=after
    # Preserve the texture inputs too, allowing exact reconstruction of this pass.
    for name in ['pause_rail','pause_focus']:
        path=SOURCE/(name+'.tga')
        if not path.exists():shutil.copy2(ROOT/f'ui/assets/sabertrials/{name}.tga',path)
    artwork()
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.iterdir() if p.name!='manifest.json'}
    (SOURCE/'manifest.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print('Staged soft styling for',sum(changes.values()),'of',len(changes),'menu files')

if __name__=='__main__':main()
