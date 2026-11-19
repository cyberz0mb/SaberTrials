"""Generate original HUD line art, lettering, and matching native Setup pages."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import hashlib, importlib.util, json
import hud_theme_art

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT/'dist/hud-staging'
ART = OUT/'gfx/sabertrials/hud'
SOURCE = ROOT/'development-source/menu/hud-original'

# Original single-stroke glyphs on a 10x14 grid. No external font dependency.
GLYPHS = {
'0':'2,0 8,0 10,2 10,12 8,14 2,14 0,12 0,2 2,0',
'1':'2,2 5,0 5,14|1,14 9,14', '2':'0,2 2,0 8,0 10,2 10,5 0,12 0,14 10,14',
'3':'0,0 8,0 10,2 10,5 8,7 3,7|8,7 10,9 10,12 8,14 0,14',
'4':'0,0 0,8 10,8|8,0 8,14', '5':'10,0 0,0 0,7 8,7 10,9 10,12 8,14 0,14',
'6':'10,0 2,0 0,2 0,12 2,14 8,14 10,12 10,9 8,7 0,7',
'7':'0,0 10,0 3,14', '8':'2,0 8,0 10,2 10,5 8,7 2,7 0,5 0,2 2,0|2,7 0,9 0,12 2,14 8,14 10,12 10,9 8,7',
'9':'10,7 2,7 0,5 0,2 2,0 8,0 10,2 10,12 8,14 0,14',
'A':'0,14 0,4 4,0 6,0 10,4 10,14|0,8 10,8',
'B':'0,14 0,0 7,0 10,3 10,5 7,7 0,7|7,7 10,10 10,12 8,14 0,14',
'C':'10,0 2,0 0,2 0,12 2,14 10,14', 'D':'0,0 7,0 10,3 10,11 7,14 0,14 0,0',
'E':'10,0 0,0 0,14 10,14|0,7 8,7', 'F':'10,0 0,0 0,14|0,7 8,7',
'G':'10,0 2,0 0,2 0,12 2,14 10,14 10,7 6,7', 'H':'0,0 0,14|10,0 10,14|0,7 10,7',
'I':'1,0 9,0|5,0 5,14|1,14 9,14', 'J':'2,0 10,0 10,12 8,14 2,14 0,12',
'K':'0,0 0,14|10,0 0,7 10,14', 'L':'0,0 0,14 10,14',
'M':'0,14 0,0 5,6 10,0 10,14', 'N':'0,14 0,0 10,14 10,0',
'O':'2,0 8,0 10,2 10,12 8,14 2,14 0,12 0,2 2,0',
'P':'0,14 0,0 8,0 10,2 10,5 8,7 0,7',
'Q':'2,0 8,0 10,2 10,12 8,14 2,14 0,12 0,2 2,0|6,10 10,14',
'R':'0,14 0,0 8,0 10,2 10,5 8,7 0,7|5,7 10,14',
'S':'10,0 2,0 0,2 0,5 2,7 8,7 10,9 10,12 8,14 0,14',
'T':'0,0 10,0|5,0 5,14', 'U':'0,0 0,12 2,14 8,14 10,12 10,0',
'V':'0,0 0,7 5,14 10,7 10,0', 'W':'0,0 0,14 5,8 10,14 10,0',
'X':'0,0 10,14|10,0 0,14', 'Y':'0,0 5,7 10,0|5,7 5,14',
'Z':'0,0 10,0 0,14 10,14', '-':'1,7 9,7', '/':'0,14 10,0',
':':'5,4 5,5|5,10 5,11', '+':'0,7 10,7|5,2 5,12',
'?':'0,2 2,0 8,0 10,2 10,5 5,8 5,10|5,13 5,14', '.':'5,13 5,14',
}

def save_mask(name, mask):
    image = Image.new('RGBA', mask.size, 'white'); image.putalpha(mask)
    image.save(ART/(name+'.tga'))

def panel(name, w, h, output):
    factor=4
    pts=[(9,1),(w-10,1),(w-1,10),(w-1,h-9),(w-10,h-1),(9,h-1),(1,h-9),(1,10),(9,1)]
    points=[(int(x*factor),int(y*factor)) for x,y in pts]
    mask=Image.new('L',(w*factor,h*factor)); d=ImageDraw.Draw(mask)
    d.polygon(points,fill=255)
    save_mask(name+'_fill',mask.resize(output,Image.Resampling.LANCZOS))
    line=Image.new('L',mask.size); d=ImageDraw.Draw(line)
    d.line(points,fill=160,width=2,joint='curve')
    d.line([(16*factor,1*factor),(int(w*.53)*factor,1*factor)],fill=235,width=3)
    d.line([(int(w*.68)*factor,(h-1)*factor),((w-13)*factor,(h-1)*factor)],fill=215,width=3)
    glow=line.filter(ImageFilter.GaussianBlur(3))
    from PIL import ImageChops
    line=ImageChops.add(line,glow.point(lambda a:int(a*.7)))
    save_mask(name,line.resize(output,Image.Resampling.LANCZOS))

def art():
    hud_theme_art.generate(ART.with_name('hud_theme'))
    ART.mkdir(parents=True,exist_ok=True)
    panel('row',160,24,(1024,128));panel('weapon',118,51,(512,256))
    glyphs=Image.new('L',(2048,1024));d=ImageDraw.Draw(glyphs)
    for i,paths in enumerate(GLYPHS.values()):
        ox=(i%16)*32+5.5;oy=(i//16)*64+12
        for path in paths.split('|'):
            pts=[tuple(map(float,p.split(','))) for p in path.split()]
            pts=[(int((ox+x*2.1)*4),int((oy+y*2.85)*4)) for x,y in pts]
            d.line(pts,fill=255,width=12,joint='curve')
    save_mask('type',glyphs.resize((512,256),Image.Resampling.LANCZOS))
    paths={
    'health':['11,2 19,2 19,11 28,11 28,19 19,19 19,28 11,28 11,19 2,19 2,11 11,11 11,2'],
    'armor':['15,2 27,7 26,19 22,25 15,29 8,25 4,19 3,7 15,2', '15,6 23,10 22,18 19,22 15,25 11,22 8,18 7,10 15,6'],
    'saber':['13,2 17,2 17,21 13,21 13,2','12,22 18,22 18,28 12,28 12,22','12,25 18,25'],
    'staff':['13,1 17,1 17,12 13,12 13,1','12,13 18,13 18,18 12,18 12,13','13,19 17,19 17,30 13,30 13,19'],
    'dual':['7,2 10,2 10,21 7,21 7,2','6,22 11,22 11,28 6,28 6,22','20,2 23,2 23,21 20,21 20,2','19,22 24,22 24,28 19,28 19,22'],
    'ammo':['6,28 6,10 10,3 14,10 14,28 6,28','18,28 18,10 22,3 26,10 26,28 18,28','6,22 14,22','18,22 26,22'],
    }
    for name,lines in paths.items():
        im=Image.new('L',(256,256)); d=ImageDraw.Draw(im)
        for path in lines:
            pts=[tuple(int(float(n)*8) for n in p.split(',')) for p in path.split()]
            d.line(pts,fill=255,width=10,joint='curve')
        save_mask(name,im.resize((128,128),Image.Resampling.LANCZOS))

def menus():
    spec=importlib.util.spec_from_file_location('theme',ROOT/'tools/Theme-Menu-Details.py')
    theme=importlib.util.module_from_spec(spec);spec.loader.exec_module(theme)
    SOURCE.mkdir(parents=True,exist_ok=True)
    for name,popup,x,y in [('setup','st_hud_main',270,399),('ingame_setup','st_hud_ingame',222,322)]:
        original=SOURCE/(name+'.menu')
        if not original.exists(): original.write_bytes((ROOT/'ui/jamp'/original.name).read_bytes())
        s=theme.read_source(original)
        _,end=theme.blocks(s,'menuDef')[0]
        def item(name,body):return 'itemDef {\nname '+name+'\n'+body+'\n}\n'
        standard='font 2 textscale .85 forecolor .76 .86 .93 1 visible 1\n'
        button=item('st_hud_settings',f'group options rect {x} {y} 270 21 type ITEM_TYPE_BUTTON\ntext "HUD appearance..."\nfont 2 textscale .8 forecolor .30 .78 1 1 visible 0\naction {{ open {popup} ; }}\ndescText "Saber Trials HUD, size and panel transparency."')
        s=s[:end-1]+button+s[end-1:]
        menu=f'''menuDef {{
name {popup}
rect 170 75 440 355
visible 0 fullscreen 0 style 1
backcolor .008 .026 .044 .99 border 1 borderSize 1 bordercolor .30 .78 1 .8
focusColor 1 1 1 1
onOpen {{ uiScript stHudInit ; setfocus style ; }}
onESC {{ close {popup} ; }}
'''
        menu+=item('title','rect 22 17 400 24 text "HUD APPEARANCE" font 4 textscale 1 forecolor .30 .78 1 1 visible 1 decoration')
        for id,label,cv,options,row in [('style','Style:','st_hudStyle','"Saber Trials" 1 "Original JKA" 0',58),
              ('score','Show score:','cg_drawScores','On 1 Off 0',94),('pulse','Low health pulse:','st_hudPulse','On 1 Off 0',130)]:
            menu+=item(id,f'rect 22 {row} 396 26 type ITEM_TYPE_MULTI text "{label}" cvar "{cv}" cvarFloatList {{ {options} }} textalign ITEM_ALIGN_RIGHT textalignx 166\n'+standard+('action { setcvar cg_drawStatus 1 ; }' if id=='style' else ''))
        for id,label,cv,default,lo,hi,row in [('size','Size %:','st_uiHudScale',100,75,125,173),('opacity','Panel opacity %:','st_uiHudOpacity',55,0,100,210)]:
            menu+=item(id,f'rect 22 {row} 275 24 type ITEM_TYPE_SLIDER text "{label}" cvarFloat "{cv}" {default} {lo} {hi} textalign ITEM_ALIGN_RIGHT textalignx 138\n'+standard)
            menu+=item(id+'_value',f'rect 320 {row} 90 24 type ITEM_TYPE_EDITFIELD text "" textalignx 5 textaligny 2 style 1 backcolor .02 .06 .09 1 border 1 bordercolor .22 .49 .64 .65 cvar "{cv}" maxChars 12 maxPaintChars 8\n'+standard)
        menu+=item('apply','rect 290 246 120 24 type ITEM_TYPE_BUTTON text "Apply"\n'+standard+'action { uiScript stHudApply ; }')
        menu+=item('status','rect 22 280 396 16 cvar "st_uiHudStatus" font 2 textscale .65 forecolor .55 .72 .83 1 visible 1 decoration')
        menu+=item('reset','rect 22 320 220 25 type ITEM_TYPE_BUTTON text "Reset HUD defaults"\n'+standard+'action { uiScript stHudReset ; }')
        menu+=item('back',f'rect 330 320 90 25 type ITEM_TYPE_BUTTON text "Back"\n'+standard+f'action {{ close {popup} ; }}')
        menu+='}\n'
        s=s[:s.rfind('}')]+menu+s[s.rfind('}'):]
        dest=OUT/'ui/jamp'/original.name;dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(s,encoding=theme.source_encoding(original),newline='\n')
    (SOURCE/'manifest.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.glob('*.menu')},indent=2)+'\n')

if __name__=='__main__':
    art();menus();print('Generated HUD assets and menus:',OUT)
