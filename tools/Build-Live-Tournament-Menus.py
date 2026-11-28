"""Build the live Tournament menu assets from the current Play and pause menus."""
from pathlib import Path
import argparse, zipfile
ROOT=Path(__file__).resolve().parents[1]
PK3="zzzzzzzzzzzzzzzz_sabertrials_tournament_lobby.pk3"
PAUSE="ui/jamp/ingame.menu"
PLAY="ui/jamp/multiplayer.menu"
def field(name,value,x,y,w,scale=".68",literal=False):
    attr="text" if literal else "cvar"
    return f'itemDef {{ name {name} rect {x} {y} {w} 22 type 0 {attr} "{value}" font 2 textscale {scale} forecolor .81 .91 .96 1 visible 1 decoration }}\n'
def button(name,label,x,y,w,action,gate=None,dynamic=False):
    gate=f'cvarTest "{gate}" showCvar {{ "1" }}' if gate else ''
    attr='cvar' if dynamic else 'text'
    return f'itemDef {{ name {name} rect {x} {y} {w} 28 type 1 {attr} "{label}" font 2 textscale .73 textalignx 7 textaligny 4 forecolor .8 .92 1 1 style 1 backcolor .015 .055 .08 .96 border 1 bordersize .5 bordercolor .20 .65 .84 .9 visible 1 {gate} action {{ play "sound/interface/button1.wav" ; {action} ; }} }}\n'
def go(current,destination):
    return f'close {current} ; open {destination}'
def page(name,title,escape,opening='setfocus back ;'):
    return f'menuDef {{ name "{name}" rect 0 0 640 480 visible 0 fullscreen 1 focusColor .25 .85 1 1 onOpen {{ {opening} }} onESC {{ {escape} ; }}\n'+'itemDef { name panel rect 10 10 620 460 style 1 backcolor .012 .029 .040 .96 visible 1 decoration }\n'+field('brand','SABER TRIALS',27,22,420,'.96',True)+field('heading',title,27,57,584,'.87',True)
def live():
    room='st_tournament_ready'
    resume='uiScript closeingame'
    s=page(room,'TOURNAMENT  /  READY ROOM',resume,'exec "cmd st_lobby status" ; setfocus back ;')
    for row,y,scale in [(0,99,'.87'),(46,126,'.70'),(45,150,'.66'),(44,348,'.65'),(55,372,'.62')]:
        s+=field('state'+str(row),'ui_ste'+str(row),28,y,584,scale)
    for side,x in enumerate((28,330)):
        for j,y in [(47,186),(49,211),(52,326)]:
            s+=field('side'+str(side)+'s'+str(j),'ui_ste'+str(j+side),x,y,278,'.70')
        for i in range(5):
            s+=field('line'+str(side*5+i),'ui_ste'+str(1+side*5+i),x,235+i*18,275,'.68')
    s+=field('score','ui_ste12',30,397,280,'.69')+field('clock','ui_ste51',330,397,278,'.65')
    for name,label,action,gate,dynamic in [('register','Join','exec "cmd st_lobby join"','ui_stLobbySoloJoin',False),('team','Join squad',go(room,'st_lobby_squads'),'ui_stLobbySquadJoin',False),('leave','Leave',go(room,'st_lobby_leave'),'ui_stEventCanLeave',False),('ready','ui_ste11','exec "cmd st_lobby ready"','ui_stEventCanReady',True)]:
        s+=button(name,label,28,432,100,action,gate,dynamic)
    s+=button('entries','Roster',140,432,96,go(room,'st_lobby_roster0'))+button('bracket','Bracket',248,432,96,go(room,'st_lobby_bracket0'),'ui_stEventHasBracket')
    s+=button('subs','Substitute',356,432,118,go(room,'st_lobby_subs'),'ui_stEventCanSubstitute')+button('back','Resume',494,432,118,resume)+'}\n'
    for kind in ('roster','bracket'):
        for page_no in range(4):
            name=f'st_lobby_{kind}{page_no}'
            s+=page(name,f'TOURNAMENT  /  {kind.upper()}     {page_no+1} / 4',go(name,room),('exec "cmd st_lobby bracket" ; ' if kind=='bracket' else '')+'setfocus back ;')
            for i in range(8):
                index=8*page_no+i
                if kind=='bracket' and index==31:break
                s+=field('row'+str(index),('ui_stLobbyEntry'+str(index) if kind=='roster' else 'ui_ste'+str(13+index)),34,123+i*31,572,'.77')
            if page_no:s+=button('prev','Previous',28,424,130,go(name,f'st_lobby_{kind}{page_no-1}'))
            if page_no<3:s+=button('next','Next',169,424,110,go(name,f'st_lobby_{kind}{page_no+1}'),f'ui_stEventBracketPage{page_no+2}' if kind=='bracket' else None)
            s+=button('back','Ready room',458,424,154,go(name,room))+'}\n'
    name='st_lobby_squads'
    s+=page(name,'TOURNAMENT  /  CHOOSE YOUR SQUAD',go(name,room))+field('tip','Choose the same squad number as your teammates.',30,112,580,'.74',True)
    for i in range(8):s+=button('squad'+str(i+1),f'Squad {i+1}',35+(i%2)*292,163+(i//2)*53,256,f'exec "cmd st_lobby join {i+1}" ; '+go(name,room))
    s+=button('back','Ready room',458,424,154,go(name,room))+'}\n'
    name='st_lobby_subs'
    s+=page(name,'TOURNAMENT  /  SUBSTITUTES',go(name,room))+field('hint','ui_ste54',32,116,576)
    for i in range(5):s+=button('sub'+str(i),'ui_ste'+str(56+i),35,162+i*42,570,f'exec "st_event_substitute {i}" ; '+go(name,room),f'ui_stEventSubAvailable{i}',True)
    s+=button('back','Ready room',458,424,154,go(name,room))+'}\n'
    name='st_lobby_leave'
    s+=page(name,'LEAVE TOURNAMENT?',go(name,room))+field('confirm','Remove your entry from this tournament?',32,163,570,'.80',True)
    return s+button('leave','Leave event',32,276,190,'exec "cmd st_lobby leave" ; '+go(name,room))+button('back','Stay registered',260,276,204,go(name,room))+'}\n'
def build(out):
    with zipfile.ZipFile(ROOT/'z_st_match_formats.pk3') as z:
        pause=z.read(PAUSE).decode().replace("\r\n","\n")
    # The event gate is set only by a connected game. Keep ordinary pause navigation intact.
    marker='itemDef { name "resume"'
    assert pause.count(marker)==1
    pause=pause.replace(marker,button('tournament','Tournament lobby',254,354,166,'open st_tournament_ready','ui_stLobbyActive')+marker)
    room_file="ui/jamp/st_lobby.menu"
    with zipfile.ZipFile(ROOT.parent/'base/assets1.pk3') as base:
        menu_list=base.read('ui/jampingame.txt').decode().replace('loadMenu {', 'loadMenu { "ui/jamp/st_lobby.menu" }\n\tloadMenu {',1)
    play=(ROOT/PLAY).read_text().split('menuDef { name "st_main_tournament"')[0]
    select='st_main_tournament'
    play+=page(select,'TOURNAMENT',go(select,'multiplayermenu'),'setfocus servers ;')
    for name,copy,y,scale in [('heading2','Join a tournament server',140,'.98'),('step1','Choose your host in the server browser or enter its address.',196,'.76'),('step2','The ready room opens when you connect to a tournament.',232,'.76'),('step3','You can return to it from the pause menu during the event.',268,'.76')]:
        play+=field(name,copy,36,y,560,scale,True)
    play+=button('servers','Find a server',36,349,205,go(select,'joinserver'))+button('back','Back to Play',36,423,180,go(select,'multiplayermenu'))+'}\n}\n'
    pause_file="ui/jamp/st_lobby_pause.menu"
    assert PAUSE in menu_list
    menu_list=menu_list.replace(PAUSE,pause_file)
    files=[(pause_file,pause),(PLAY,play),(room_file,"{\n"+live()+"}\n"),("ui/jampingame.txt",menu_list)]
    for n,s in files:
        path=out/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(s,encoding='utf8',newline='\n')
    with zipfile.ZipFile(out/PK3,'w',zipfile.ZIP_DEFLATED) as z:
        for name,_ in files:z.write(out/name,name)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);build(parser.parse_args().output)
