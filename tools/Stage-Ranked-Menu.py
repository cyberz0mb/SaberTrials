"""Replace only the Ranked placeholder with navigable, honest offline screens."""
from pathlib import Path
import hashlib, json, shutil
ROOT=Path(__file__).resolve().parent.parent
STAGE=ROOT/'dist/ranked-menu-staging'
ORIGINAL=ROOT/'development-source/menu/ranked-original'

def label(name,text,x,y,width=548,scale='.8',color='.76 .86 .93 1'):
    return f'itemDef {{ name {name} rect {x} {y} {width} 22 type 0 text "{text}" font 2 textscale {scale} forecolor {color} visible 1 decoration }}\n'
def box(name,x,y,w,h,color='.008 .026 .044 .96'):
    return f'itemDef {{ name {name} rect {x} {y} {w} {h} style 1 backcolor {color} border 1 bordercolor .30 .78 1 .38 visible 1 decoration }}\n'
def button(name,text,x,y,w,action,selected=False):
    return f'''itemDef {{ name {name} rect {x} {y} {w} 30 type 1 text "{text}" font 2 textscale .82
 textalignx 10 textaligny 6 forecolor .76 .86 .93 1 visible 1
 style 1 backcolor {'.035 .16 .24 1' if selected else '.015 .05 .08 .94'} border 1 bordercolor .30 .78 1 .5
 action {{ play "sound/interface/button1.wav" ; {action} ; }} }}
'''

def page(name,subtitle,selected):
    text=f'''menuDef {{ name "{name}" rect 0 0 640 480 visible 0 fullscreen 1 popup
 focusColor 1 1 1 1 disableColor .35 .42 .47 1
 onOpen {{ setfocus {selected} ; }} onESC {{ close {name} ; open multiplayermenu ; }}
 itemDef {{ name arena rect 0 0 640 480 style 3 background "ui/assets/sabertrials/arena.tga" forecolor 1 1 1 1 visible 1 decoration }}
 itemDef {{ name shade rect 0 0 640 480 style 1 backcolor .004 .015 .028 .55 visible 1 decoration }}
'''
    text+=label('brand','S A B E R   T R I A L S',28,20,scale='1.3',color='.30 .78 1 1')
    text+=label('heading','RANKED PLAY  /  '+subtitle,28,53,scale='.9')
    for index,(key,title,dest) in enumerate([
        ('overview','Overview','st_main_ranked'),('duel','Duel ladder','st_ranked_duel'),
        ('teams','Team ladder','st_ranked_teams'),('servers','Ranked servers','st_ranked_servers')]):
        action=f'close {name} ; open {dest}' if dest!=name else 'setfocus '+key
        text+=button(key,title,28+index*146,88,142,action,selected==key)
    text+=box('content',28,130,584,285)
    text+=button('back','Back to Play',28,431,180,f'close {name} ; open multiplayermenu')
    text+=label('offline','Ranked connection: not configured',255,437,350,'.73','.46 .66 .77 1')
    return text

def stage():
    ORIGINAL.mkdir(parents=True,exist_ok=True)
    source=ORIGINAL/'main.menu'
    if not source.exists():shutil.copy2(ROOT/'ui/jamp/main.menu',source)
    original=source.read_text()
    start=original.index('menuDef { name "st_main_ranked"')
    # The placeholder is the final menu inside the file's outer wrapper.
    assert original[start:].count('menuDef')==1
    pages=[]
    s=page('st_main_ranked','OVERVIEW','overview')
    for n,t,y,scale,color in [
        ('title','Three ways to compete',150,'1.05','.30 .78 1 1'),
        ('duelTitle','Ranked Duel',189,'.9','.90 .96 1 1'),
        ('duelCopy','Official 1v1 matches on a Ranked Duel server.',213,'.77','.76 .86 .93 1'),
        ('challengeTitle','Ranked Challenge Duel',245,'.9','.90 .96 1 1'),
        ('challengeCopy','Accepted 1v1 challenges inside FFA. Shares the Duel ladder.',269,'.77','.76 .86 .93 1'),
        ('teamTitle','Ranked TFFA',301,'.9','.90 .96 1 1'),
        ('teamCopy','Registered teams compete on their own team ladder.',325,'.77','.76 .86 .93 1'),
        ('account','Accounts and match reporting are not connected yet.',369,'.76','.46 .76 .88 1'),
        ('unranked','Ordinary matches remain unranked.',389,'.73','.76 .86 .93 1')]:
        s+=label(n,t,46,y,548,scale,color)
    pages.append(s+'}\n')
    for team in [False,True]:
        name='st_ranked_teams' if team else 'st_ranked_duel'
        s=page(name,'TEAM LADDER' if team else 'DUEL LADDER','teams' if team else 'duel')
        s+=label('title','TEAM STANDINGS' if team else 'DUEL STANDINGS',46,147,scale='1',color='.30 .78 1 1')
        for i,(title,x,w) in enumerate([('Rank',46,50),('Team / tag' if team else 'Player',106,235),('Rating',355,70),('W / L',448,60),('Matches',521,72)]):
            s+=label('column'+str(i),title,x,186,w,'.72')
        s+=box('rule',46,214,548,1,'.30 .78 1 .45')
        s+=label('empty','No standings available',46,249,scale='1.05',color='.90 .96 1 1')
        s+=label('reason','The ranking service is not connected.',46,281,scale='.83')
        s+=label('scope','Only official registered teams enter this ladder.' if team else 'Ranked Duel and Ranked Challenge Duel share this ladder.',46,339,scale='.73')
        s+=label('points','Starting rating: 1000   |   Results and opponent strength decide changes.',46,366,scale='.71')
        s+=label('note','Rankings appear after verified official results are connected.',46,389,scale='.71')
        pages.append(s+'}\n')
    s=page('st_ranked_servers','SERVER DIRECTORY','servers')
    s+=label('title','OFFICIAL RANKED SERVERS',46,147,scale='1',color='.30 .78 1 1')
    for i,(title,x,w) in enumerate([('Server',46,220),('Ranked mode',287,140),('Map',439,100),('Players',533,65)]):
        s+=label('column'+str(i),title,x,186,w,'.72')
    s+=box('rule',46,214,548,1,'.30 .78 1 .45')
    s+=label('empty','No official servers listed',46,244,scale='1.05',color='.90 .96 1 1')
    s+=label('reason','The ranked server directory is not connected yet.',46,276,scale='.8')
    s+=label('modes','Supports Ranked Duel, Ranked TFFA and FFA challenge servers.',46,315,scale='.71')
    s+=label('note','Installing the mod alone does not make a server official.',46,337,scale='.73')
    s+=button('browse','Browse unranked servers',46,369,300,'close st_ranked_servers ; open joinserver')
    pages.append(s+'}\n')
    target=STAGE/'ui/jamp/main.menu';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(original[:start]+''.join(pages)+'}\n',newline='\n')
    baseline=STAGE/'baseline.json'
    if not baseline.exists():
        paths=[*ROOT.glob('*.cfg'),*ROOT.glob('*.dll'),ROOT/'client/SaberTrials.x86_64.exe']
        paths += [p for folder in ['ui','gfx'] for p in (ROOT/folder).rglob('*') if p.is_file()]
        baseline.write_text(json.dumps({p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2)+'\n')
    print('Staged four Ranked screens; existing menus and side fades preserved.')

if __name__=='__main__':stage()
