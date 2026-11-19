"""Add head portrait settings to the accepted Game Options menus, reproducibly."""
from pathlib import Path
import hashlib, importlib.util, json, shutil
ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'development-source/menu/portrait-original'
OUT=ROOT/'dist/portrait-staging'

def generate():
    spec=importlib.util.spec_from_file_location('theme',ROOT/'tools/Theme-Menu-Details.py')
    theme=importlib.util.module_from_spec(spec);spec.loader.exec_module(theme)
    SOURCE.mkdir(parents=True,exist_ok=True)
    for name,menu,y,x in [('setup','st_portrait_main',376,270),('ingame_setup','st_portrait_ingame',297,222)]:
        p=SOURCE/(name+'.menu')
        if not p.exists():p.write_bytes((ROOT/'ui/jamp'/p.name).read_bytes())
        s=theme.read_source(p)
        a,b=theme.blocks(s,'menuDef')[0]
        button=f'''\nitemDef {{
 name st_portrait_settings
 group options
 rect {x} {y} 270 21
 type ITEM_TYPE_BUTTON
 text "Head portrait settings..."
 font 2
 textscale .8
 forecolor .30 .78 1 1
 visible 0
 action {{ open {menu} ; }}
 descText "Live head, portrait size, leader and opponent options."
}}
'''
        s=s[:b-1]+button+s[b-1:]
        def item(name,body):return 'itemDef {\n name '+name+'\n '+body+'\n}\n'
        shared='font 2\n textscale .85\n forecolor .76 .86 .93 1\n visible 1\n'
        popup=f'''menuDef {{
 name {menu}
 rect 170 90 440 330
 visible 0
 fullscreen 0
 style 1
 backcolor .008 .026 .044 .99
 border 1
 borderSize 1
 bordercolor .30 .78 1 .8
 focusColor 1 1 1 1
 onOpen {{ uiScript stPortraitInit ; setfocus mode ; }}
 onESC {{ close {menu} ; }}
'''
        popup+=item('title', 'rect 20 16 400 24\n text "HEAD PORTRAIT"\n font 4\n textscale 1\n forecolor .30 .78 1 1\n visible 1\n decoration')
        for id,label,cv,values,row in [('mode','Portrait:','st_portraitMode','Live 1 Static 2 Off 0',60),
                ('target','Show:','st_portraitTarget','Leader 0 "Your character" 1 Opponent 2',94),
                ('damage','Damage reactions:','st_portraitDamage','On 1 Off 0',128)]:
            popup+=item(id,f'rect 22 {row} 396 26\n type ITEM_TYPE_MULTI\n text "{label}"\n cvar "{cv}"\n cvarFloatList {{ {values} }}\n textalign ITEM_ALIGN_RIGHT\n textalignx 166\n '+shared+'action { setcvar cg_drawEnemyInfo 1 ; }')
        popup+=item('size', 'rect 22 171 275 24\n type ITEM_TYPE_SLIDER\n text "Size:"\n cvarFloat "st_uiPortraitSize" 80 48 144\n textalign ITEM_ALIGN_RIGHT\n textalignx 85\n '+shared)
        popup+=item('size_value','rect 300 171 110 24\n type ITEM_TYPE_EDITFIELD\n text ""\n textalignx 5\n textaligny 2\n style 1\n backcolor .02 .06 .09 1\n border 1\n bordercolor .22 .49 .64 .65\n cvar "st_uiPortraitSize"\n maxChars 12\n maxPaintChars 8\n '+shared)
        popup+=item('apply','rect 280 204 135 24\n type ITEM_TYPE_BUTTON\n text "Apply size"\n '+shared+'action { uiScript stPortraitSize ; }')
        popup+=item('hint','rect 22 238 400 16\n text "Leader switches to your opponent during duels."\n font 2\n textscale .65\n forecolor .55 .72 .83 1\n visible 1\n decoration')
        popup+=item('status','rect 22 260 400 16\n cvar "st_uiPortraitStatus"\n font 2\n textscale .65\n forecolor .55 .72 .83 1\n visible 1\n decoration')
        popup+=item('reset','rect 22 295 180 25\n type ITEM_TYPE_BUTTON\n text "Reset portrait defaults"\n '+shared+'action { uiScript stPortraitReset ; }')
        popup+=item('back',f'rect 330 295 90 25\n type ITEM_TYPE_BUTTON\n text "Back"\n '+shared+f'action {{ close {menu} ; }}')
        popup+='}\n'
        s=s[:s.rfind('}')]+popup+s[s.rfind('}'):]
        dest=OUT/'ui/jamp'/p.name;dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(s,encoding=theme.source_encoding(p),newline='\n')
    (SOURCE/'manifest.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.glob('*.menu')},indent=2)+'\n')
    shutil.copytree(ROOT/'development-source/menu/portrait-profiles',OUT,dirs_exist_ok=True)
    print('Generated',OUT)

if __name__=='__main__':generate()
