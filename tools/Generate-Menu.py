"""Generate the native Saber Trials menu shell and original vector-style UI art."""
from pathlib import Path
import math
import shutil
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT/'dist/menu-staging'
ART = OUT/'ui/assets/sabertrials'
CYAN = '.30 .78 1 1'
PALE = '.76 .86 .93 1'
ASSETS = '''assetGlobalDef {
 font "ergoec" 18 smallFont "ocr_a" 18 bigFont "anewhope" 20 small2Font "arialnb" 14
 cursor "ui/assets/sabertrials/cursor" gradientBar "ui/assets/gradientbar2.tga"
 itemFocusSound "sound/interface/menuroam.wav"
 fadeClamp 1 fadeCycle 1 fadeAmount 0.1 shadowColor 0 0 0 .6
}'''

def item(name, body): return f'itemDef {{ name "{name}" {body} }}\n'
def box(name,x,y,w,h,color,border=False,extra=''):
    return item(name,f'rect {x} {y} {w} {h} style 1 backcolor {color} visible 1 decoration '+
                (f'border 1 borderSize 1 bordercolor {CYAN} ' if border else '')+extra)
def art(name,x,y,w,h,texture,extra=''):
    return item(name,f'rect {x} {y} {w} {h} style 3 background "{texture}" forecolor 1 1 1 1 visible 1 decoration {extra}')
def text(name,label,x,y,w=380,scale=.8,color=PALE,font=2,center=False,extra=''):
    return item(name,f'type 0 rect {x} {y} {w} 22 text "{label}" font {font} textscale {scale} '+
                f'textalign {1 if center else 0} textalignx {w/2 if center else 0} textaligny 0 forecolor {color} visible 1 decoration {extra}')
def button(name,label,x,y,w,h,action,icon=None,extra=''):
    result=box(name+'_line',x,y+h-1,w,0.5,'.38 .64 .78 .28')
    if icon: result+=art(name+'_icon',x+12,y+(h-20)/2,20,20,'ui/assets/sabertrials/'+icon)
    result+=item(name,f'''rect {x} {y} {w} {h} type 1 style 0 text "{label}"
 font 2 textscale .85 textalignx {48 if icon else 14} textaligny {(h-20)/2}
 forecolor {PALE} visible 1
 onFocus {{ show focus_glow ; setitemrect focus_glow {x} {y} {w} {h} ; }}
 leaveFocus {{ hide focus_glow ; }}
 action {{ play "sound/interface/button1.wav" ; {action} }} {extra}''')
    return result
def glow():
    return art('focus_glow',0,0,1,1,'ui/assets/sabertrials/focus','group focus').replace('visible 1','visible 0')
def menu(name,body,opening='',escape='',fullscreen=False):
    return f'''menuDef {{ name "{name}" rect 0 0 640 480 visible 0 fullscreen {int(fullscreen)}
 focusColor 1 1 1 1 disableColor .35 .42 .47 1
 onOpen {{ {opening} }} onESC {{ {escape} }}
{body}
}}\n'''
def backdrop():
    return art('arena',0,0,640,480,'ui/assets/sabertrials/arena.tga')+box('shade',0,0,640,480,'.005 .018 .032 .27')
def title():
    return box('brand_line',155,24,425,1,'.22 .64 .93 .8')+text('starwars','STAR WARS',135,34,460,2.3,'.85 .93 1 1',3,True)+text('brand','S A B E R   T R I A L S',135,98,460,.97,CYAN,3,True)+text('multiplayer','M U L T I P L A Y E R',135,135,460,.66,PALE,4,True)
def main_root(name):
    body=backdrop()
    body+=item('movie','rect 0 0 640 480 style 5 cinematic "video/sabertrials_menu.roq" visible 1 decoration cvarTest "st_uiMenuMovie" showCvar { "1" }')
    body+=box('movie_shade',0,0,640,480,'.005 .018 .032 .18')
    body+=art('hologram',290,178,272,272,'ui/assets/sabertrials/hologram')
    body+=art('rail',18,165,195,272,'ui/assets/sabertrials/rail')+box('rail_edge',18,165,1,272,CYAN)+title()+glow()
    for i,(key,label,icon,target) in enumerate([
        ('play','Play','play','multiplayermenu'),('profile','Profile','player','playerMenu'),
        ('controls','Controls','controls','controlsMenu'),('setup','Setup','settings','setup_menu'),
        ('exit','Exit','exit','st_main_exit')]):
        action=f'open {target} ;' if key=='exit' else f'close {name} ; open {target} ;'
        body+=button(key,label,20,178+i*50,192,46,action,icon)
    body+=button('motion','Menu animation',458,452,160,22,'uiScript stMenuMotion ;',extra='textscale .65').replace('text "Menu animation"','cvar "st_uiMenuMotionLabel"')
    body+=text('edition','SABER TRIALS  /  MULTIPLAYER',22,457,330,.58,'.54 .69 .79 1')
    return menu(name,body,'uiScript stMenuInit ; setfocus play ;','open st_main_exit ;',True)

def card(name,heading,lines,buttons,back,main=False):
    body=backdrop()+title() if main else ''
    x,y,w=(225,184,390) if main else (236,62,380)
    body+=box('panel',x,y,w,275,'.008 .026 .044 .94',True)
    body+=text('heading',heading,x+20,y+18,w-40,1.02,CYAN,4)
    for i,line in enumerate(lines): body+=text(f'copy{i}',line,x+20,y+51+i*20,w-40,.77)
    body+=glow()
    first_y=y+max(116,63+len(lines)*20)
    for i,(key,label,action) in enumerate(buttons): body+=button(key,label,x+14,first_y+i*34,w-28,32,action)
    body+=button('back','Back',x+14,y+237,w-28,28,back,extra='textscale .8')
    return menu(name,body,'setfocus back ;',back,main).replace('focusColor 1 1 1 1','popup\n focusColor 1 1 1 1')

def generate():
    ART.mkdir(parents=True,exist_ok=True)
    arena=ROOT/'development-source/menu/assets/arena.tga'
    with Image.open(arena) as im:
        if any(n<=0 or n & (n-1) for n in im.size):
            raise RuntimeError('The native UI requires power-of-two texture dimensions')
    shutil.copy2(arena,ART/'arena.tga')
    target=OUT/'ui/jamp';target.mkdir(parents=True,exist_ok=True)
    main=ASSETS+main_root('main')+main_root('mainMenu')
    main+=card('st_main_exit','EXIT SABER TRIALS',['Quit the game and return to your desktop?'],
               [('confirm','Quit game','uiScript quit ;')],'close st_main_exit ;')
    ranked=['Online ranked play is not available yet.','Your account, team and world rank will live','on the Saber Trials website when it launches.',
            'Ranked Duel + Challenge Duel share a ladder.','Ranked TFFA uses registered teams.']
    main+=card('st_main_ranked','RANKED PLAY',ranked,[],
               'close st_main_ranked ; open multiplayermenu ;',True)
    (target/'main.menu').write_text('{\n'+main+'}\n')
    play=backdrop()+title()+art('rail',18,172,195,269,'ui/assets/sabertrials/rail')+box('rail_edge',18,172,1,269,CYAN)
    play+=text('section','PLAY',242,190,350,1.3,CYAN,3)+text('subtitle','Choose your arena.',242,225,350,.95)
    play+=text('rank_note','Ranked services are coming soon.',242,401,350,.76)
    play+=glow()
    entries=[('joinserver_button','Find a server','joinserver','join'),('startserver_button','Host a match','createserver','settings'),
             ('quickserver_button','Solo match','quickgame','play'),('playdemo_button','Recordings','demo','camera'),
             ('ranked','Ranked Play','st_main_ranked','rank'),('rules_button','Game rules','rulesMenu','info')]
    for i,(key,label,dest,icon) in enumerate(entries):
        play+=button(key,label,20,180+i*38,192,36,f'close multiplayermenu ; open {dest} ;',icon)
    play+=button('back','Back',20,420,192,28,'close multiplayermenu ; open mainMenu ;',extra='textscale .8')
    (target/'multiplayer.menu').write_text('{\n'+menu('multiplayermenu',play,'setfocus joinserver_button ;','close multiplayermenu ; open mainMenu ;',True)+'}\n')
    body=art('rail',18,20,192,435,'ui/assets/sabertrials/rail')+box('rail_edge',18,20,1,435,CYAN)
    body+=text('brand','SABER TRIALS',33,29,168,.62,CYAN,3)+glow()
    entries=[('about','About','info','open st_pause_about ;'),('join','Join','join','open ingame_join ;'),
             ('player','Player','player','open ingame_player ;'),('vote','Vote / Call Vote','vote','open st_pause_vote ;'),
             ('setup','Setup','settings','open st_pause_setup ;'),('streamer','Streamer Mode','stream','uiScript stStreamerSettings ;'),
             ('photo','Photo Mode','camera','open st_pause_photo ;'),('respawn','Respawn','refresh','open st_pause_respawn ;'),
             ('exit','Exit','exit','open st_pause_exit ;')]
    for i,(key,label,icon,action) in enumerate(entries): body+=button(key,label,20,59+i*41,190,39,action,icon)
    body+=button('resume','Resume  /  Esc',20,432,190,22,'uiScript closeingame ;',extra='textscale .7')
    pause=ASSETS+menu('ingame',body,'uiScript stPauseInit ; setfocus resume ;','uiScript closeingame ;')
    pause+=card('st_pause_about','SABER TRIALS',['Multiplayer built around pro saber dueling.',
        'Your server chooses the combat rules.','Original JKA and Saber Trials Combat are supported.'],
        [('details','Server information','open ingame_about ;'),('match','Match tools','open st_pause_tools ;')],
        'close st_pause_about ;')
    pause+=card('st_pause_tools','MATCH TOOLS',[],[
        ('bots','Add bots','open ingame_addbot ;'),('objectives','Siege objectives','open ingame_objectives ;'),
        ('voice','Siege voice commands','open ingame_voicechat ;')],'close st_pause_tools ;')
    pause+=card('st_pause_vote','VOTING',['Have your say on the current vote,','or propose a change to this server.'],[
        ('cast','Cast your vote','open ingame_vote ;'),('call','Call a vote','open ingame_callvote ;')],'close st_pause_vote ;')
    pause+=card('st_pause_setup','SETUP',[],[
        ('controls','Controls and recording key','open ingame_controls ;'),
        ('settings','Video, audio and game settings','open ingame_setup ;'),
        ('input','Turn speed and mouse acceleration','uiScript stInputSettings ;')],'close st_pause_setup ;')
    pause+=card('st_pause_photo','PHOTO MODE',['Photo Mode is planned and is not available yet.',
        'You can still capture screenshots using the', 'screenshot key in Controls > Other.'],
        [('controls','Open Controls','open ingame_controls ;')],'close st_pause_photo ;')
    pause+=card('st_pause_respawn','RESPAWN?',['This ends your current life.','Your server may deduct a point.'],[
        ('confirm','Respawn now','exec "kill" ; uiScript closeingame ;')],'close st_pause_respawn ;')
    pause+=card('st_pause_exit','LEAVE THE MATCH?',[],[
        ('disconnect','Disconnect','open st_pause_disconnect ;'),('quit','Quit game','open st_pause_quit ;')],'close st_pause_exit ;')
    pause+=card('st_pause_disconnect','DISCONNECT?',['Leave this server and return to the main menu?'],[
        ('confirm','Disconnect','uiScript leave ;')],'close st_pause_disconnect ;')
    pause+=card('st_pause_quit','QUIT GAME?',['Leave this server and return to your desktop?'],[
        ('confirm','Quit game','uiScript quit ;')],'close st_pause_quit ;')
    # Keep the root in the native back stack, but hide its art under legacy editors.
    pause=pause.replace('visible 1 decoration','visible 1 decoration cvarTest "st_uiPauseShell" showCvar { "1" }')
    pause=pause.replace(f'forecolor {PALE} visible 1\n',f'forecolor {PALE} visible 1 cvarTest "st_uiPauseShell" showCvar {{ "1" }}\n')
    pause=pause.replace('visible 0 decoration group focus','visible 0 decoration group focus cvarTest "st_uiPauseShell" showCvar { "1" }')
    (target/'ingame.menu').write_text('{\n'+pause+'}\n')
    votes=(ROOT/'ui/jamp/ingame_callvote.menu').read_text()
    votes=votes.replace('onESC { uiScript closeingame ; }','onESC { close ingame_callvote ; }')
    (target/'ingame_callvote.menu').write_text(votes)
    make_art()
    print('Generated native menus and original UI art:',OUT)

def make_art():
    # All images below are new procedural UI assets, not edits of the user's concepts.
    for name in ['play','player','controls','settings','exit','join','camera','info','vote','stream','refresh','rank','cursor']:
        im=Image.new('RGBA',(128,128));d=ImageDraw.Draw(im);c=(169,212,235,255);w=6
        def line(points): d.line(points,fill=c,width=w,joint='curve')
        def circle(box): d.ellipse(box,outline=c,width=w)
        if name in ('player','join'):
            circle((43,13,85,55));d.arc((24,59,104,128),180,360,fill=c,width=w);line([(26,96),(26,110),(102,110),(102,96)])
            if name=='join': d.arc((3,20,47,64),100,290,fill=c,width=w);d.arc((80,20,124,64),250,80,fill=c,width=w)
        elif name=='play': line([(34,17),(104,64),(34,111),(34,17)])
        elif name=='settings':
            pts=[]
            for i in range(48):
                a=i*math.tau/48;r=51 if i%6 in (1,2,3) else 40
                pts.append((64+r*math.cos(a),64+r*math.sin(a)))
            line(pts+[pts[0]]);circle((45,45,83,83))
        elif name=='exit': line([(58,17),(108,17),(108,111),(58,111)]);line([(12,64),(80,64),(59,44)]);line([(80,64),(59,84)])
        elif name=='camera': d.rounded_rectangle((10,34,118,107),radius=9,outline=c,width=w);circle((42,46,88,92));line([(34,32),(43,19),(79,19),(90,32)])
        elif name=='info': circle((14,14,114,114));circle((61,34,67,40));line([(64,55),(64,92)])
        elif name=='vote':
            line([(29,12),(101,12),(101,116),(29,116),(29,12)])
            for y in (38,60,82):line([(44,y),(85,y)])
        elif name=='stream':
            circle((57,55,71,69));line([(64,70),(64,110)])
            for r in (30,49):
                d.arc((64-r,62-r,64+r,62+r),130,230,fill=c,width=w);d.arc((64-r,62-r,64+r,62+r),-50,50,fill=c,width=w)
        elif name=='refresh': d.arc((15,15,113,113),20,300,fill=c,width=w);line([(103,17),(103,42),(78,42)])
        elif name=='rank':line([(64,12),(109,35),(99,87),(64,117),(29,87),(19,35),(64,12)]);line([(43,67),(64,44),(85,67)])
        elif name=='controls':
            d.rounded_rectangle((11,30,117,101),radius=23,outline=c,width=w);line([(27,60),(53,60)]);line([(40,47),(40,73)]);circle((79,48,87,56));circle((93,66,101,74))
        elif name=='cursor': line([(24,12),(104,71),(66,78),(51,114),(24,12)])
        im.resize((64,64),Image.Resampling.LANCZOS).save(ART/(name+'.tga'))
    im=Image.new('RGBA',(512,128));d=ImageDraw.Draw(im)
    for x in range(512):d.line((x,0,x,127),fill=(2,12,22,int(228*(1-x/650))))
    im.save(ART/'rail.tga')
    im=Image.new('RGBA',(512,128));d=ImageDraw.Draw(im)
    for y in range(128):
        edge=min(y,127-y);a=int(130+90*math.exp(-edge/9))
        d.line((0,y,511,y),fill=(12,87,145,a))
    d.rectangle((1,1,510,126),outline=(119,214,255,230),width=2);d.line((2,2,2,126),fill=(205,244,255,255),width=3)
    im.save(ART/'focus.tga')
    im=Image.new('RGBA',(1024,1024));d=ImageDraw.Draw(im)
    for r in range(447,0,-2):
        d.ellipse((512-r,512-r,512+r,512+r),fill=(0,14,32,int(100+65*(1-r/447))))
    for r in (100,180,258,332,398,447):
        d.ellipse((512-r,512-r,512+r,512+r),outline=(90,192,255,190),width=2)
    for i in range(24):
        a=i*math.tau/24
        d.line((512+120*math.cos(a),512+120*math.sin(a),512+395*math.cos(a),512+395*math.sin(a)),fill=(60,153,219,110),width=2)
    for a,b,c in [(0,35,(125,222,255,240)),(62,92,(255,219,143,220)),(116,163,(86,196,255,240)),(210,245,(86,196,255,240)),(270,295,(255,219,143,220)),(310,330,(86,196,255,240))]:
        d.arc((95,95,929,929),a,b,fill=c,width=10)
    for i in range(96):
        a=i*math.tau/96
        d.line((512+421*math.cos(a),512+421*math.sin(a),512+428*math.cos(a),512+428*math.sin(a)),fill=(110,205,255,210),width=2)
    d.line((25,512,999,512),fill=(120,211,255,135),width=2);d.line((512,25,512,999),fill=(120,211,255,135),width=2)
    d.polygon([(512,484),(526,512),(512,540),(498,512)],fill=(255,222,146,255))
    im.save(ART/'hologram.tga')

if __name__=='__main__': generate()
