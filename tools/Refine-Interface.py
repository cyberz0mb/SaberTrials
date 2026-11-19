"""Refine the accepted HUD-era menus without regenerating unrelated screens.

Run after older menu generators when rebuilding the full presentation stack.
The snapshots are immutable inputs; output is staged for isolated verification.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT/'development-source/menu/interface-original'
OUT = ROOT/'dist/interface-staging'
ART = OUT/'ui/assets/sabertrials'

def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/'tools'/file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

theme = load('theme', 'Theme-Menu-Details.py')
shell = load('shell', 'Generate-Menu.py')

def value(s, key):
    match = re.search(r'\b'+key+r'\s+("[^"]*"|[^\s{}]+)', s, re.I)
    return match[1].strip('"') if match else ''

def replace_item(s, name, replacement):
    matches = [(a,b) for a,b in theme.blocks(s,'itemDef') if value(s[a:b],'name')==name]
    assert len(matches)==1, (name,len(matches))
    a,b=matches[0]
    return s[:a]+replacement+s[b:]

def insert_item(s, item):
    _,end=theme.blocks(s,'menuDef')[0]
    return s[:end-1]+item+s[end-1:]

def snapshot(name):
    path=SOURCE/(name+'.menu')
    if not path.exists(): path.write_bytes((ROOT/'ui/jamp'/path.name).read_bytes())
    return theme.read_source(path).replace('\r\n','\n').replace('\r','\n')

def hub(suffix):
    name='st_interface_'+suffix
    s=f'''menuDef {{
name {name}
rect 170 75 440 355
visible 0 fullscreen 0 style 1
backcolor .008 .026 .044 1 border 1 borderSize .5 bordercolor .22 .49 .64 .8
focusColor 1 1 1 1
onOpen {{ setfocus hud ; }}
onESC {{ close {name} ; }}
'''
    s+=shell.text('title','UI SETTINGS',22,17,396,1,shell.CYAN,4)
    s+=shell.text('intro','Choose what you want to customize.',22,47,396,.74)
    s+=shell.glow()
    for key,label,icon,y,description in [
        ('hud','HUD appearance','controls',87,'Style, size, transparency and score display.'),
        ('portrait','Head portraits','player',173,'Live or static heads, subject, size and reactions.')]:
        s+=shell.box(key+'_panel',22,y,396,67,'.02 .07 .105 .8')
        s+=shell.button(key,label,22,y,396,36,f'open st_{key}_{suffix} ;',icon)
        s+=shell.text(key+'_description',description,37,y+40,370,.70,'.55 .72 .83 1')
    s+=shell.box('footer',22,302,396,.5,'.22 .49 .64 .5')
    s+=shell.button('back','Back',318,318,100,25,f'close {name} ;',extra='textscale .78')
    return s+'}\n'

def settings(name):
    s=snapshot(name)
    for obsolete in ['st_portrait_settings','st_hud_settings']:
        s=replace_item(s,obsolete,'')
    main=name=='setup'
    suffix='main' if main else 'ingame'
    # Add a category after Game options and move later categories down one row.
    move=['modsmenubutton','gamedefaultsmenubutton'] if main else [
        'networkmenubutton','inputmenubutton','streamermenubutton','gamedefaultsmenubutton']
    move += ['modsbutton_glow','gamedefaultsbutton_glow'] if main else [
        'networkbutton_glow','inputbutton_glow','streamerbutton_glow','gamedefaultsbutton_glow']
    for a,b in reversed(theme.blocks(s,'itemDef')):
        item=s[a:b]
        if value(item,'name') in move:
            rect=theme.rect(item)
            if rect:
                rect[1]+=27.8919 if main else 30
                item=theme.prop(item,'rect',' '.join(theme.fmt(n) for n in rect))
                s=s[:a]+item+s[b:]
    x,y,h=(80,258.135,27.8919) if main else (20,163,30)
    s=insert_item(s, f'''itemDef {{
name st_interface_settings
group setup_submenu
rect {x} {y} 170 {h}
type ITEM_TYPE_BUTTON
text "UI Settings"
font 2 textscale .82 textalign ITEM_ALIGN_LEFT textalignx 12 textaligny {2 if main else 5}
forecolor .76 .86 .93 1 visible 1
descText "Customize the HUD and character portraits."
action {{ play "sound/interface/button1.wav" ; open st_interface_{suffix} ; }}
}}
''')
    if main:
        s=insert_item(s,theme.box('st_editor_categoryline6',88,174+6*27.89,154,.4,'.22 .49 .64 .35'))
    # Both child pages cover the hub completely; their native Back stack returns here.
    s=s.replace('rect 170 90 440 330','rect 170 75 440 355')
    # Parent labels must not ghost through the settings pages.
    s=s.replace('backcolor .008 .026 .044 .99','backcolor .008 .026 .044 1')
    # The engine paints visible menus in definition order, not focus order.
    # Place the hub before its child pages so an open child covers it.
    _,end=theme.blocks(s,'menuDef')[0]
    return s[:end]+hub(suffix)+s[end:]

def pause():
    s=snapshot('ingame')
    a,b=theme.blocks(s,'menuDef')[0]
    body=shell.art('rail',18,54,230,340,'ui/assets/sabertrials/pause_rail')
    body+=shell.art('rail_edge',18,54,1,340,'ui/assets/sabertrials/pause_edge')
    body+=shell.text('brand','SABER TRIALS',33,64,168,.59,shell.CYAN,3)
    body+=shell.glow().replace('sabertrials/focus','sabertrials/pause_focus')
    entries=[('about','About','info','open st_pause_about ;'),
        ('join','Join','join','open ingame_join ;'),('player','Player','player','open ingame_player ;'),
        ('vote','Vote / Call Vote','vote','open st_pause_vote ;'),('setup','Setup','settings','open st_pause_setup ;'),
        ('streamer','Streamer Mode','stream','uiScript stStreamerSettings ;'),
        ('photo','Photo Mode','camera','open st_pause_photo ;'),
        ('respawn','Respawn','refresh','open st_pause_respawn ;'),('exit','Exit','exit','open st_pause_exit ;')]
    for i,(key,label,icon,action) in enumerate(entries):
        y=91+i*28
        row=shell.button(key,label,20,y,210,27,action,icon)
        row=replace_item(row,key+'_line',shell.art(key+'_line',20,y+26,210,.5,'ui/assets/sabertrials/pause_line'))
        row=row.replace('textscale .85','textscale .78').replace('textalignx 48','textalignx 42')
        row=replace_item(row,key+'_icon',shell.art(key+'_icon',32,y+4.5,18,18,'ui/assets/sabertrials/'+icon))
        body+=row
    row=shell.button('resume','Resume  /  Esc',20,354,210,24,'uiScript closeingame ;',extra='textscale .70')
    body+=replace_item(row,'resume_line','')
    root=shell.menu('ingame',body,'uiScript stPauseInit ; setfocus resume ;','uiScript closeingame ;')
    root=root.replace('visible 1 decoration','visible 1 decoration cvarTest "st_uiPauseShell" showCvar { "1" }')
    root=root.replace(f'forecolor {shell.PALE} visible 1\n',f'forecolor {shell.PALE} visible 1 cvarTest "st_uiPauseShell" showCvar {{ "1" }}\n')
    root=root.replace('visible 0 decoration group focus','visible 0 decoration group focus cvarTest "st_uiPauseShell" showCvar { "1" }')
    s=s[:a]+root+s[b:]
    # Keep every existing Setup action, adding the direct UI shortcut.
    for a,b in theme.blocks(s,'menuDef'):
        if value(s[a:b],'name')=='st_pause_setup':
            card=shell.card('st_pause_setup','SETUP',[],[
                ('controls','Controls and recording key','open ingame_controls ;'),
                ('settings','Video, audio and game settings','open ingame_setup ;'),
                ('interface','UI Settings','open st_interface_ingame ;'),
                ('input','Turn speed and mouse acceleration','uiScript stInputSettings ;')],
                'close st_pause_setup ;')
            # Four rows with room for the Back button.
            for index,key in enumerate(['controls','settings','interface','input']):
                old_y=178+index*34; new_y=126+index*38
                card=card.replace(f' {old_y} ',f' {new_y} ').replace(f' {old_y+31} ',f' {new_y+31} ')
            # card shares the pause shell visibility rules with the existing cards.
            card=card.replace('visible 1 decoration','visible 1 decoration cvarTest "st_uiPauseShell" showCvar { "1" }')
            card=card.replace(f'forecolor {shell.PALE} visible 1\n',f'forecolor {shell.PALE} visible 1 cvarTest "st_uiPauseShell" showCvar {{ "1" }}\n')
            card=card.replace('visible 0 decoration group focus','visible 0 decoration group focus cvarTest "st_uiPauseShell" showCvar { "1" }')
            return s[:a]+card+s[b:]
    raise AssertionError('Missing pause Setup card')

def smooth(t):
    t=max(0,min(1,t)); return t*t*(3-2*t)

def artwork():
    ART.mkdir(parents=True,exist_ok=True)
    # New procedural textures, independent of the main-menu art.
    im=Image.new('RGBA',(512,512))
    pixels=im.load()
    for y in range(512):
        vertical=smooth(y/24)*smooth((511-y)/40)
        for x in range(512):
            pixels[x,y]=(2,12,22,round(219*vertical*(1-smooth((x-290)/221))))
    im.save(ART/'pause_rail.tga')
    im=Image.new('RGBA',(8,256)); d=ImageDraw.Draw(im)
    for y in range(256):
        d.line((0,y,7,y),fill=(77,199,255,round(200*smooth(y/22)*smooth((255-y)/28))))
    im.save(ART/'pause_edge.tga')
    im=Image.new('RGBA',(512,8)); d=ImageDraw.Draw(im)
    for x in range(512):
        d.line((x,0,x,7),fill=(97,163,199,round(70*(1-smooth((x-170)/341)))))
    im.save(ART/'pause_line.tga')
    im=Image.new('RGBA',(512,64)); pixels=im.load()
    for y in range(64):
        for x in range(512):
            fade=1-smooth((x-280)/231)
            edge=y<2 or y>61 or x<2
            pixels[x,y]=((119,214,255,round(215*fade)) if edge else (12,87,145,round(155*fade)))
    im.save(ART/'pause_focus.tga')

def main():
    SOURCE.mkdir(parents=True,exist_ok=True)
    dest=OUT/'ui/jamp'; dest.mkdir(parents=True,exist_ok=True)
    for name in ['setup','ingame_setup','ingame']:
        result=pause() if name=='ingame' else settings(name)
        (dest/(name+'.menu')).write_text(result,encoding=theme.source_encoding(SOURCE/(name+'.menu')),newline='\n')
    (SOURCE/'manifest.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.glob('*.menu')},indent=2)+'\n')
    artwork()
    print('Staged compact pause menu and UI Settings:',OUT)

if __name__=='__main__': main()
