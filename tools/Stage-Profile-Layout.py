"""Align the Profile screen and add a soft, borderless name-field focus glow."""
from pathlib import Path
import hashlib,importlib.util,json,math,re
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'dist/profile-layout-staging'
SOURCE=ROOT/'development-source/menu/profile-layout-original/player.menu'
spec=importlib.util.spec_from_file_location('profile_theme',ROOT/'tools/Theme-Menu-Details.py')
theme=importlib.util.module_from_spec(spec);spec.loader.exec_module(theme)

def key(item):return re.search(r'\bname\s+"?([^\s"{}]+)',item)[1]

def main():
    SOURCE.parent.mkdir(parents=True,exist_ok=True)
    if not SOURCE.exists():SOURCE.write_bytes((ROOT/'ui/jamp/player.menu').read_bytes())
    s=SOURCE.read_text()
    for a,b in reversed(theme.blocks(s,'itemDef')):
        item=s[a:b];name=key(item);props={}
        if name=='customtitle':item=''
        elif name=='background' and theme.rect(item)[2]>0:item=''
        elif name=='nameglow':
            props={'rect':'30 116 404 36','background':'"ui/assets/sabertrials/profile_name_glow"'}
        elif name=='namefield':
            props={'rect':'30 121 404 28','textalignx':'8','textaligny':'0','textscale':'.9','maxPaintChars':'26'}
            item=re.sub(r'\bdescText\s+[^\n]+','',item)
            item=re.sub(r'\bmouse(?:enter|exit)\s*\{[^}]*\}','',item,flags=re.I)
            item=item[:-1]+'onFocus { show nameglow ; }\nleaveFocus { hide nameglow ; }\n}'
        elif name=='modeltitle':
            props={'rect':'30 176 180 24','textalign':'ITEM_ALIGN_LEFT','textalignx':'0','textaligny':'0','textscale':'.82'}
        elif name=='setcolor':
            props={'rect':'230 179 204 22','textaligny':'0','textscale':'.72'}
        elif name=='headlist':props={'rect':'30 206 404 198'}
        elif name in ('st_profile_preview','custom'):
            props={'rect':'448 195 164 220'}
            if name=='st_profile_preview':props.update(model_fovy='36')
        elif name=='st_profile_unavailable':props={'rect':'460 295 152 22'}
        elif name=='st_editor_footer':props={'rect':'30 438 580 .5'}
        elif name=='st_editor_brand':props={'rect':'30 18 450 22'}
        elif name=='st_editor_section':props={'rect':'30 50 520 22'}
        elif name=='st_editor_active':props={'rect':'190 104 110 1'}
        for index,button in enumerate(('newgamebutton','profilebutton','controlsbutton','setupbutton')):
            if name==button or name==button+'_glow':
                props['rect']=f'{20+index*150} 78 150 28'
                if name==button:props['textalignx']='75'
        if name in ('exitgamebutton','exitgamebutton_glow'):props['rect']='30 444 150 26'
        if name in ('next','next_glow'):props['rect']='460 444 150 26'
        if name in ('exitgamebutton','next'):props['textalignx']='75'
        for prop,value in props.items():item=theme.prop(item,prop,value)
        s=s[:a]+item+s[b:]
    s=re.sub(r'\bdescY\s+[\d.]+','descY 426',s,count=1)
    s=re.sub(r'\bdescScale\s+[\d.]+','descScale .55',s,count=1)
    _,end=theme.blocks(s,'menuDef')[0]
    hint='''itemDef {
 name st_profile_name_hint
 rect 38 151 380 16
 text "Click your name to edit"
 font 2 textscale .55 forecolor .55 .72 .83 1
 visible 1 decoration
}
'''
    s=s[:end-1]+hint+s[end-1:]
    # New procedural UI texture. Feather all four edges; no outline or sharp corners.
    glow=Image.new('RGBA',(512,64))
    def smooth(v):v=max(0,min(1,v));return v*v*(3-2*v)
    for y in range(64):
        for x in range(512):
            a=smooth(min(x,511-x)/65)*math.sin(math.pi*y/63)**1.5
            glow.putpixel((x,y),(20,125,184,round(96*a)))
    art=STAGE/'ui/assets/sabertrials/profile_name_glow.tga';art.parent.mkdir(parents=True,exist_ok=True);glow.save(art)
    menu=STAGE/'ui/jamp/player.menu';menu.parent.mkdir(parents=True,exist_ok=True)
    menu.write_text(re.sub(r'\n[ \t]*\n(?:[ \t]*\n)+','\n\n',s),newline='\n')
    manifest={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (menu,art)}
    (STAGE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Staged aligned Profile, centered viewport and soft name focus.')

if __name__=='__main__':main()
