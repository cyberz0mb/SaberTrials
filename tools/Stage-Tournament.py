"""Legacy server-bound menu prototype and shared Account helpers.

The pause-menu tournament topology is retired. Current presentation staging
is Stage-Tournament-Frontend.py; preserve this prototype for its data adapter.
"""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'dist/tournament-staging'

def span(text,name):
    tokens=list(re.finditer(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/|[{}]|[^\s{}]+',text,re.S))
    for i,t in enumerate(tokens):
        if t.group()!='menuDef':continue
        if [x.group().strip('"') for x in tokens[i+1:i+4]]!=['{','name',name]:continue
        depth=0
        for end in tokens[i+1:]:
            if end.group()=='{':depth+=1
            if end.group()=='}':
                depth-=1
                if depth==0:return t.start(),end.end()
    raise ValueError('Missing menu '+name)

def label(name,text,x,y,w=550,scale='.72',cvar=False):
    return f'itemDef {{ name {name} rect {x} {y} {w} 20 type 0 {"cvar" if cvar else "text"} "{text}" font 2 textscale {scale} forecolor .76 .86 .93 1 visible 1 decoration }}\n'

def button(name,text,x,y,w,action,extra=''):
    return f'''itemDef {{ name {name} rect {x} {y} {w} 26 type 1 text "{text}" font 2 textscale .72
 forecolor .76 .86 .93 1 visible 1 {extra}
 action {{ play "sound/interface/button1.wav" ; {action} ; }} }}
'''

def panel(name,title,x=20,y=45,w=600,h=390,onopen=''):
    return f'''menuDef {{ name "{name}" rect {x} {y} {w} {h} visible 0 fullscreen 0 popup
 focusColor 1 1 1 1 onESC {{ close {name} ; }} onOpen {{ {onopen} }}
 itemDef {{ name panel rect 0 0 {w} {h} style 1 backcolor .008 .026 .044 .97 border 1 bordercolor .22 .49 .64 .8 visible 1 decoration }}
'''+label('title',title,18,12,w-36,scale='.95')

def account(name):
    s=panel(name,'SABER TRIALS / ACCOUNT',80,115,480,230,'setfocus back ;')
    s+=label('name','ui_stAccountName',20,48,440,'.92',True)
    s+=label('team','ui_stAccountTeam',20,77,440,'.68',True)
    s+=label('status','ui_stAccountStatus',20,106,440,'.68',True)
    s+=label('notice','Tournaments also require verification on the game server.',20,136,440,'.61')
    s+=button('login','Log in with Discord',20,181,205,'exec "login"','cvarTest "ui_stAccountCanLogin" showCvar { "1" }')
    s+=button('logout','Log out / Cancel',235,181,145,'exec "logout"','cvarTest "ui_stAccountCanLogout" showCvar { "1" }')
    s+=button('back','Back',390,181,70,f'close {name}')
    return s+'}\n'

def rule(name, x, y, w):
    return f'itemDef {{ name {name} rect {x} {y} {w} .5 style 1 backcolor .22 .49 .64 .6 visible 1 decoration }}\n'


def event_panel(name, title, opening=''):
    return panel(name, title, 20, 20, 600, 440, opening).replace(
        'focusColor 1 1 1 1', 'focusColor 1 1 1 1 disableColor .35 .43 .48 1', 1) + rule('title_rule', 18, 37, 564)


def event_button(name, text, x, y, w, action, enabled=None, dynamic=False):
    extra = f'cvarTest "{enabled}" enableCvar {{ "1" }}' if enabled else ''
    result = button(name, text, x, y, w, action, extra)
    if dynamic:
        result = result.replace('text "'+text+'"', 'cvar "'+text+'"')
    return result.replace('forecolor .76 .86 .93 1 visible 1',
        f'''style 1 backcolor .015 .055 .08 .9 border 1 bordersize .5 bordercolor .22 .49 .64 .65
 textalignx 8 textaligny 3 forecolor .76 .86 .93 1 visible 1
 onFocus {{ setitemcolor {name} backcolor .035 .19 .28 .95 ; }}
 leaveFocus {{ setitemcolor {name} backcolor .015 .055 .08 .9 ; }}''')


def tournament():
    s=event_panel('ingame_tournament','SABER TRIALS / TOURNAMENT','exec "tournament status" ; setfocus back ;')
    for name, field, y, scale in [('phase',0,43,'.72'),('entries',46,64,'.62'),('identity',45,85,'.60'),('score',12,106,'.77')]:
        s+=label(name,'ui_ste'+str(field),18,y,564,scale,True)
    for side in range(2):
        x=18+side*292
        s+=rule('side_rule'+str(side),x,128,272)
        s+=label('side'+str(side),'ui_ste'+str(47+side),x,132,272,'.74',True)
        s+=label('attendance'+str(side),'ui_ste'+str(49+side),x,154,272,'.61',True)
        for row in range(5):
            s+=label('player'+str(side*5+row),'ui_ste'+str(1+side*5+row),x,178+row*20,272,'.60',True)
        s+=label('reconnect'+str(side),'ui_ste'+str(52+side),x,283,272,'.63',True)
    s+=label('clock','ui_ste51',18,305,564,'.63',True)
    s+=label('instruction','ui_ste44',18,326,564,'.59',True)
    s+=label('feedback','ui_ste55',18,346,564,'.59',True)
    s+=event_button('ready','ui_ste11',18,371,120,'exec "tournament ready"','ui_stEventCanReady',True)
    s+=event_button('join','Join tournament',150,371,158,'exec "tournament join"','ui_stEventCanJoin')
    s+=event_button('leave','Leave',320,371,100,'open st_event_leave','ui_stEventCanLeave')
    s+=event_button('substitutes','Substitutes',432,371,150,'open st_event_substitutes')
    s+=event_button('account','Account',18,407,110,'open st_pause_account')
    s+=event_button('bracket','View bracket',140,407,155,'open st_event_bracket','ui_stEventHasBracket')
    s+=event_button('refresh','Refresh',307,407,110,'exec "tournament status"')
    s+=event_button('back','Back',472,407,110,'close ingame_tournament')
    s+='}\n'
    for page in range(4):
        name='st_event_bracket'+(f'_{page+1}' if page else '')
        s+=event_panel(name,'TOURNAMENT / BRACKET','exec "tournament bracket" ; setfocus back ;')
        s+=label('range',f'Matches {1+page*8}-{min(8+page*8,31)}',18,48,564,'.76')
        s+=label('legend','Current matchup, upcoming opponents and completed results',18,71,564,'.61')
        for row, line in enumerate(range(13+page*8,min(13+(page+1)*8,44))):
            s+=label('match'+str(line),'ui_ste'+str(line),18,104+row*34,564,'.70',True)
            s+=rule('match_rule'+str(line),18,132+row*34,564)
        for target in range(4):
            destination='st_event_bracket'+(f'_{target+1}' if target else '')
            action='exec "tournament bracket"' if destination==name else f'close {name} ; open {destination}'
            s+=event_button('page'+str(target+1),str(target+1),18+target*52,407,42,action,'ui_stEventBracketPage'+str(target+1))
        s+=event_button('refresh','Refresh',307,407,110,'exec "tournament bracket"')
        s+=event_button('back','Back',472,407,110,'close '+name)
        s+='}\n'
    s+=event_panel('st_event_substitutes','TOURNAMENT / SUBSTITUTES','exec "tournament status" ; setfocus back ;')
    s+=label('instruction','ui_ste54',18,52,564,'.61',True)
    s+=label('rules','Your registered team and the reconnect timer still apply.',18,80,564,'.63')
    for i in range(5):
        s+=event_button('replace'+str(i),'ui_ste'+str(56+i),18,130+i*44,564,
            f'exec "st_event_substitute {i}"','ui_stEventSubAvailable'+str(i),True)
    s+=label('feedback','ui_ste55',18,365,564,'.61',True)
    s+=event_button('refresh','Refresh',307,407,110,'exec "tournament status"')
    s+=event_button('back','Back',472,407,110,'close st_event_substitutes')
    s+='}\n'
    s+=panel('st_event_leave','LEAVE TOURNAMENT?',100,150,440,180,'setfocus cancel ;')
    s+=label('notice','Remove your registration from this event?',18,58,404,'.70')
    s+=button('leave','Leave tournament',18,122,210,'exec "tournament leave" ; close st_event_leave')
    s+=button('cancel','Stay registered',240,122,180,'close st_event_leave')
    return s+'}\n'

def stage():
    outputs={}
    for filename,menu,accountname,x,y in [('main.menu','main','st_main_account',485,2),('ingame.menu','ingame','st_pause_account',34,402)]:
        p=ROOT/'ui/jamp'/filename;s=p.read_text()
        try:
            a,b=span(s,accountname)
            s=s[:a]+account(accountname).rstrip()+s[b:]
        except ValueError:
            a,b=span(s,menu)
            s=s[:b-1]+button('account_link','Account / Log in',x,y,150,'open '+accountname)+s[b-1:]
            end=s.rfind('}');s=s[:end]+account(accountname)+s[end:]
        outputs['ui/jamp/'+filename]=s
    p=ROOT/'ui/jamp/ingame_player.menu';s=p.read_text().replace(
        'Join, leave, view, or vote to start the Saber Trials Tournament.',
        'Register, ready up, view brackets, or choose a substitute.')
    for name in ('st_event_bracket','st_event_bracket_2','st_event_bracket_3','st_event_bracket_4','st_event_substitutes','st_event_leave'):
        try:
            a,b=span(s,name)
            s=s[:a]+s[b:].lstrip('\n')
        except ValueError:
            pass
    a,b=span(s,'ingame_tournament')
    outputs['ui/jamp/ingame_player.menu']=s[:a]+tournament().rstrip()+s[b:]
    manifest={'installed':False,'account_service':'native bridge staged; hosted verification pending','files':{},'originals':{}}
    for name,s in outputs.items():
        target=STAGE/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(s)
        manifest['files'][name]=hashlib.sha256(target.read_bytes()).hexdigest()
        manifest['originals'][name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    (STAGE/'menu-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Staged three menus; installed files unchanged.')

if __name__=='__main__':
    raise SystemExit('Legacy pause-menu staging retired. Use tools/Stage-Tournament-Frontend.py stage for the current Play -> Tournament visual preview. Live front-end integration is pending.')
