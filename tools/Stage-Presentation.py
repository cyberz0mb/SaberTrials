"""Stage the visual pass from immutable accepted menus. Never changes installed files."""
from pathlib import Path
import hashlib,importlib.util,json,re
ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'dist/presentation-input';OUT=ROOT/'dist/presentation-staging'
spec=importlib.util.spec_from_file_location('front',ROOT/'tools/Stage-Tournament-Frontend.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
span=f.block_span

def edit(text,name,fn):
    a,b=span(text,'itemDef',name);return text[:a]+fn(text[a:b])+text[b:]
def prop(block,key,value):
    pattern=r'\b'+key+r'\s+[^\r\n}]+'
    # Use this only for the old multiline menu syntax.
    return re.sub(pattern,key+' '+value,block,count=1,flags=re.I)
def rect(block,x,y,w,h):return re.sub(r'\brect\s+[-\d.]+\s+[-\d.]+\s+[-\d.]+\s+[-\d.]+',f'rect {x} {y} {w} {h}',block,count=1)
def browser(s):
    for name in ['horizontalseparators','serverColumn','mapColumn','playerColumn','typeColumn','pingColumn']:
        while True:
            try:a,b=span(s,'itemDef',name);s=s[:a]+s[b:]
            except ValueError:break
    for name,x,w,label in [('server',16,148,'Server'),('map',170,80,'Map'),('Players',252,44,'Players'),('Type',298,68,'Mode'),('Ping',374,48,'Ping')]:
        def change(b,x=x,w=w,label=label):
            b=rect(b,x,92,w,20);b=prop(b,'textscale','.72')
            b=re.sub(r'\btext\s+(?:"[^"]*"|@\w+)',f'text "{label}"',b,count=1)
            return b
        s=edit(s,name,change)
    def listing(b):
        b=rect(b,12,112,422,264);b=prop(b,'elementheight','18');b=prop(b,'textscale','.66')
        return prop(b,'columns','5 4 24 148 158 12 80 240 7 44 286 12 68 362 5 36')
    s=edit(s,'serverlist',listing)
    s=edit(s,'refreshdate',lambda b:prop(rect(b,16,380,592,16),'textscale','.65'))
    for name in ['passwordText','createFavoriteText','addFavorite','delfavorite','serverinfoText','findplayerText']:
        s=edit(s,name,lambda b:prop(b,'textscale','.78'))
    s=edit(s,'join_button',lambda b:rect(b,470,444,140,26))
    for name in ['source','netfilter','gametypefilter','viewEmpty','viewFull','datarate']:
        try:s=edit(s,name,lambda b:prop(b,'textscale','.84'))
        except ValueError:pass
    return re.sub(r'\n[ \t]*\n', '\n',s)

def label(name,text,x,y,w=550,scale='.70',color='.76 .86 .93 1',cvar=False,extra=''):
    # Same family as Profile, with content text lighter than primary actions.
    return f.label(name,text,x,y,w,scale,color,cvar,extra).replace('font 2','font 4')
def line(name,x,y,w):return f'itemDef {{ name {name} rect {x} {y} {w} .5 style 1 backcolor .30 .55 .65 .35 visible 1 decoration }}\n'
def icon(name,path,x,y):return f'itemDef {{ name {name} rect {x} {y} 22 22 style 3 background "ui/assets/sabertrials/{path}" forecolor .40 .80 1 1 visible 1 decoration }}\n'
def button(name,text,x,y,w,action,extra=''):
    return f.button(name,text,x,y,w,action,extra).replace('textscale .78','textscale .71').replace('border 1 bordersize .5 bordercolor .30 .78 1 .5','border 0')
def page(name,title,back,focus='back'):
    return f.page(name,title,back,focus)
def bracket_card(idx,x,y,w=272):
    return f.box('card'+str(idx),x,y,w,46)+label('matchlabel'+str(idx),'ui_stCardTitle'+str(idx),x+10,y+4,w-20,'.53','.30 .78 1 1',True)+label('pairA'+str(idx),'ui_stCardA'+str(idx),x+10,y+17,w-20,'.68',cvar=True)+label('pairB'+str(idx),'ui_stCardB'+str(idx),x+10,y+30,w-20,'.68',cvar=True)

def tournaments(original):
    # Preserve accepted Play menu, Ranked pages and all account actions.
    a,b=span(original,'menuDef','st_main_tournament')
    header=original[:a]
    s=page('st_main_tournament','SELECT A FORMAT','multiplayermenu','individual')
    s+=label('intro','Choose a format to preview its tournament lobby.',28,98,584,'.79')
    for x,title,glyph in [(28,'INDIVIDUAL','player'),(326,'TEAMS','join')]:
        s+=f.box('format'+str(x),x,140,286,271)+icon('emblem'+str(x),glyph,x+18,159)
        s+=label('name'+str(x),title,x+52,158,210,'.95','.30 .78 1 1')+line('formatline'+str(x),x+18,191,250)
    for i,t in enumerate(['8-32 players / even entries','10 rounds per match','5-5 tie: one deciding round','5 minutes to reconnect']):s+=label('ruleA'+str(i),t,46,207+i*29,250,'.75')
    s+=button('individual','Enter individual lobby',46,359,250,'exec "exec st-tournament-preview-individual.cfg" ; '+f.route('st_main_tournament','st_tournament_ready'))
    for i,t in enumerate(['Up to 8 registered teams','One TFFA match / respawns','Equal, complete lineups required']):s+=label('ruleB'+str(i),t,344,207+i*24,250,'.71')
    for n in range(2,6):s+=button('team'+str(n),f'{n}v{n} / {n*10} kills',344+((n-2)%2)*128,288+((n-2)//2)*36,122,f'exec "exec st-tournament-preview-{n}v{n}.cfg" ; '+f.route('st_main_tournament','st_tournament_ready'))
    s+=label('reconnect','10 minutes: reconnect or substitute',344,367,250,'.64')+label('readyhint','Every active player selects Ready.',344,388,250,'.64')+'}\n'
    name='st_tournament_ready';s+=page(name,'READY ROOM','st_main_tournament','ready').replace('Back to ready room','Select tournament')
    s+=label('event','ui_stFrontEvent',28,96,584,'.91','.30 .78 1 1',True)+label('entries','ui_stFrontEntries',28,122,584,'.66',cvar=True)
    s+=label('versus','VS',310,228,26,'.95','.30 .78 1 1')
    for side,x in enumerate([28,340]):
        s+=f.box('roster'+str(side),x,153,272,199)+icon('emblem'+str(side),'join',x+14,167)
        s+=label('team'+str(side),'ui_stFrontSide'+str(side),x+45,165,213,'.80','.9 .96 1 1',True)+line('rosterline'+str(side),x+14,214,244)
        if side==0:
            for r in (0,1,2):s+=label('count'+str(r),'ui_stFrontCount'+str(r),x+14,193,244,'.63',cvar=True,extra=f.shown('Ready',r))
        else:s+=label('opponentcount','ui_stFrontOpponentCount',x+14,193,244,'.63',cvar=True)
        for row in range(5):
            y=223+row*24
            if side==row==0:
                for r in (0,1,2):s+=label('you'+str(r),'[+] You / READY' if r==1 else '[ ] You / Waiting',x+14,y,244,'.71','.42 .87 .77 1' if r==1 else '.96 .8 .47 1',extra=f.shown('Ready',r))
            elif side==0 and row==1:
                s+=label('row01','ui_stFrontRow1',x+14,y,244,'.71',cvar=True,extra='cvarTest "ui_stFrontReady" showCvar { 0 ; 1 }')
                s+=label('row01offline','[!] Mira / Disconnected',x+14,y,244,'.71','1 .55 .44 1',extra=f.shown('Ready',2))
            else:s+=label('row'+str(side)+str(row),'ui_stFrontRow'+str(side*5+row),x+14,y,244,'.71',cvar=True)
    s+=label('waiting','[ ] Waiting for you. Click Ready when prepared.',28,361,584,'.72',extra=f.shown('Ready',0))
    s+=label('allready','[+] Everyone is ready. Sample lobby: no match will start.',28,361,584,'.72','.42 .87 .77 1',extra=f.shown('Ready',1))
    s+=label('disconnected','[!] Match paused / missing teammate. Reconnect window: 10:00 (sample).',28,361,584,'.68','1 .55 .44 1',extra=f.shown('Ready',2))
    s+=button('ready','Ready',28,391,108,'setcvar ui_stFrontReady "1" ; setcvar st_uiPresentationNotice "Preview: ready selected." ; setfocus unready',f.shown('Ready',0))
    s+=button('unready','Unready',28,391,108,'setcvar ui_stFrontReady "0" ; setcvar st_uiPresentationNotice "Preview: ready cleared." ; setfocus ready',f.shown('Ready',1))
    s+=button('reconnect','Reset preview',28,391,108,'setcvar ui_stFrontReady "0" ; setfocus ready',f.shown('Ready',2))
    for key,title,x,dest,extra in [('bracket','Bracket',146,'st_tournament_bracket1',''),('result','Result preview',264,'st_tournament_result',''),('reserves','Reserves',382,'st_tournament_reserves',f.shown('Team',1)),('leave','Leave lobby',500,'st_tournament_leave','')]:s+=button(key,title,x,391,112,f.route(name,dest),extra)
    s+='}\n'
    for p in range(1,5):
        name='st_tournament_bracket'+str(p);s+=page(name,'BRACKET','st_tournament_ready')
        s+=label('stage','ui_stFrontBracketHeading'+str(p),28,98,584,'.82','.30 .78 1 1',True)
        # Teams and the final individual page use an actual connected elimination tree.
        tree=p==4
        if p==1:
            for r in range(8):s+=bracket_card(r,28+(r%2)*312,139+(r//2)*57).replace('visible 1 decoration','visible 1 decoration '+f.shown('Team',0))
        elif not tree:
            for r in range(8):s+=bracket_card((p-1)*8+r,28+(r%2)*312,139+(r//2)*57)
        if tree or p==1:
            extra='' if tree else f.shown('Team',1)
            for i,(x,y,w) in enumerate([(28,139,170),(28,196,170),(28,253,170),(28,310,170),(242,167,170),(242,281,170),(456,224,156)]):
                s+=bracket_card((24 if tree else 0)+i,x,y,w).replace('visible 1 decoration','visible 1 decoration '+extra)
            for j,(x,y,w,h) in enumerate([(198,162,22,.5),(198,219,22,.5),(220,162,.5,57),(220,190,22,.5),(198,276,22,.5),(198,333,22,.5),(220,276,.5,57),(220,304,22,.5),(412,190,22,.5),(412,304,22,.5),(434,190,.5,114),(434,247,22,.5)]):
                s+=f'itemDef {{ name connector{j} rect {x} {y} {w} {h} style 1 backcolor .30 .65 .8 .6 visible 1 decoration {extra} }}\n'
        for n in range(1,5):s+=button('page'+str(n),str(n),28+(n-1)*52,391,44,f.route(name,'st_tournament_bracket'+str(n)),f.shown('BracketPage'+str(n),1))
        s+=label('legend','NOW = current match   /   WAIT = upcoming',260,398,352,'.62')+'}\n'
    # Existing reserve and leave flows remain intact, with matching readable text.
    for name in ['st_tournament_reserves','st_tournament_leave']:
        a,b=span(original,'menuDef',name);block=original[a:b]
        if name=='st_tournament_reserves':
            block=edit(block,'available',lambda b:b.replace('Both lineups are complete. No replacement is needed.','Preview how a missing teammate appears in the ready room.').replace('46 354','46 344'))
            block=block[:-1]+button('disconnectpreview','Preview disconnect',46,376,244,'setcvar ui_stFrontReady "2" ; '+f.route(name,'st_tournament_ready'))+'}\n'
        s+=block+'\n'
    name='st_tournament_result';s+=page(name,'MATCH RESULT','st_tournament_ready')
    s+=f.box('result',28,134,584,276)+icon('winnericon','player',52,159)
    s+=label('winner','SAMPLE WINNER',88,157,490,'.70','.30 .78 1 1')+label('champion','You / Blue Horizon',52,190,520,1.15,'.90 .96 1 1')
    s+=line('resultline',52,226,536)+label('score','ui_stFrontResultScore',52,243,536,'.92',cvar=True)
    s+=label('advance','Advances to the next round',52,279,536,'.80','.42 .87 .77 1')+label('next','Next opponent: awaiting the other match winner',52,309,536,'.72')
    s+=label('rating','Rating: unavailable / no verified ranked result',52,350,536,'.69')+label('previewresult','Illustration only. This result does not update your account.',52,378,536,'.62')+'}\n'
    return header+s+'}\n'

def configs(size):
    s=f.config(size)
    s+=f'set ui_stFrontCount2 "{max(0,size-1)}/{size} present / waiting for full lineup"\n'
    team=size>1
    pairs=[('You (preview)','Mira')]+[(f'Duelist {i*2+1}',f'Duelist {i*2+2}') for i in range(1,16)]
    if team:pairs=[('Blue Horizon','Crimson Guard'),('Silver Dawn','Nightwatch'),('Saber Guild','Eclipse'),('Vanguard','Nova Squad')]
    first=len(pairs);total=first*2-1
    for i in range(total):
        if i<first:a,b=pairs[i]
        else:a,b=f'Winner of match {(i-first)*2+1}',f'Winner of match {(i-first)*2+2}'
        for key,value in [('Title',f'MATCH {i+1} / '+('NOW' if i==0 else 'WAIT')),('A',a),('B','vs  '+b)]:s+=f'set ui_stCard{key}{i} "{value}"\n'
    s+=f'set ui_stFrontResultScore "Final score: {size*10} - {size*6}"\n' if team else 'set ui_stFrontResultScore "Final score: 6 - 4 / 10 rounds"\n'
    for i in range(1,10):s=re.sub(r'(set ui_stFrontRow'+str(i)+r' ")([^"]+)',r'\1[+] \2',s)
    return s

def settings(s,suffix):
    a,b=span(s,'menuDef','st_interface_'+suffix);block=s[a:b]
    block=block[:-1]+'''itemDef { name notifications rect 22 258 396 26 type ITEM_TYPE_YESNO text "Status notifications:" cvar "st_notifications" font 4 textscale .80 textalignx 12 textaligny 3 forecolor .76 .86 .93 1 visible 1 }
'''+block[-1:]
    return s[:a]+block+s[b:]

def main():
    files={}
    for p in (INPUT/'ui/jamp').glob('*.menu'):
        key=p.relative_to(INPUT).as_posix();s=p.read_text()
        if p.name=='joinserver.menu':s=browser(s)
        elif p.name=='multiplayer.menu':s=tournaments(s)
        elif p.name in ['setup.menu','ingame_setup.menu']:s=settings(s,'main' if p.name=='setup.menu' else 'ingame')
        # Focus glow only: do not fade or recolor content panels or the accepted Profile.
        if p.name not in ['player.menu','main.menu','ingame.menu','multiplayer.menu']:
            matches=list(re.finditer(r'\bitemDef\s*\{\s*name\s+"?(button_glow\w*)"?',s))
            for m in reversed(matches):
                name=m.group(1)
                try:
                    a,b=span(s,'itemDef',name);block=s[a:b]
                    block=re.sub(r'background\s+"?ui/assets/sabertrials/focus(?:\.tga)?"?', 'background "ui/assets/sabertrials/profile_name_glow"',block)
                    block=re.sub(r'\bborder\s+1\b','border 0',block)
                    s=s[:a]+block+s[b:]
                except ValueError:pass
        if s!=p.read_text():files[key]=s
    for n in range(1,6):files['st-tournament-preview-'+('individual' if n==1 else f'{n}v{n}')+'.cfg']=configs(n)
    for name,text in files.items():
        target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text,newline='\n')
    (OUT/'manifest.json').write_text(json.dumps({n:hashlib.sha256((OUT/n).read_bytes()).hexdigest() for n in files},indent=2)+'\n')
    print('Staged',len(files),'menu/config files; Profile and side rails preserved')
if __name__=='__main__':main()
