"""Render a labelled layout preview from the actual staged native menu generator."""
from pathlib import Path
import importlib.util
import json
import re
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/tournament-ui-preview'
spec=importlib.util.spec_from_file_location('menus',ROOT/'tools/Stage-Tournament.py')
menus=importlib.util.module_from_spec(spec);spec.loader.exec_module(menus)


def blocks(text, kind):
    tokens=list(re.finditer(r'"(?:\\.|[^"\\])*"|[{}]|[^\s{}]+',text))
    for i,t in enumerate(tokens):
        if t.group()!=kind:continue
        depth=0
        for end in tokens[i+1:]:
            if end.group()=='{':depth+=1
            if end.group()=='}':
                depth-=1
                if not depth:
                    yield text[t.end():end.end()]
                    break


def data():
    result={}
    for block in blocks(menus.tournament(),'menuDef'):
        name=re.search(r'\bname\s+"([^"]+)"',block).group(1)
        rect=list(map(float,re.search(r'\brect\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',block).groups()))
        items=[]
        for item in blocks(block,'itemDef'):
            entry={'rect':list(map(float,re.search(r'\brect\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',item).groups()))}
            for key in ('text','cvar','cvarTest'):
                match=re.search(r'\b'+key+r'\s+"([^"]*)"',item)
                if match:entry[key]=match.group(1)
            entry['button']=bool(re.search(r'\btype\s+1\b',item))
            entry['scale']=float(re.search(r'textscale\s+([\d.]+)',item).group(1)) if 'textscale' in item else 1
            entry['action']=re.search(r'\baction\s*\{([^}]*)\}',item).group(1) if entry['button'] else ''
            if 'backcolor' in item:
                entry['fill']=list(map(float,re.search(r'backcolor\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',item).groups()))
            items.append(entry)
        result[name]={'rect':rect,'items':items}
    return result


def samples():
    state={f'ui_ste{i}':'' for i in range(61)}
    state.update(ui_stEventCanJoin='0',ui_stEventCanLeave='0',ui_stEventCanReady='1',ui_stEventHasBracket='1')
    values={0:'Ready check | 2v2 TFFA / 20 kills',11:'Ready',12:'0  -  0',44:'Both complete lineups must select Ready. Click again to unready.',
      45:'Your match: use Ready / Unready below.',46:'8 / 8 teams registered',47:'Blue Horizon',48:'Crimson Guard',
      49:'2/2 present | 0/2 ready',50:'2/2 present | 2/2 ready',51:'Time played 0:00 / 10:00',
      1:'Your player | Not ready',2:'Teammate | Not ready',6:'Opponent one | READY',7:'Opponent two | READY',
      54:'No replacement available. Only reserves can replace absent teammates.'}
    values.update({13:'1. Blue Horizon / Crimson Guard [Current]',14:'2. Night Watch / Dawn Patrol',15:'3. Echo / Nova',16:'4. Falcon / Atlas',17:'5. TBD / TBD',18:'6. TBD / TBD',19:'7. TBD / TBD'})
    state.update({f'ui_ste{k}':v for k,v in values.items()})
    for i in range(4):state[f'ui_stEventBracketPage{i+1}']='1' if i==0 else '0'
    for i in range(5):state[f'ui_stEventSubAvailable{i}']='0'
    return state


def main():
    OUT.mkdir(parents=True,exist_ok=True);views=data();sample=samples()
    template='''<!doctype html><meta charset="utf-8"><title>Saber Trials tournament layout preview</title>
<style>body{margin:0;background:#080f16;color:#c2dbea;font:16px Arial,sans-serif}header{max-width:1000px;margin:18px auto;padding:0 16px}h1{font-size:24px;color:#4bc8ff;margin:0 0 8px}p{margin:8px 0;color:#9bb4c3}select{background:#122738;color:#d3e6f2;border:1px solid #477890;padding:8px;margin-right:12px}#wrap{width:min(96vw,1100px);aspect-ratio:4/3;position:relative;margin:20px auto}#canvas{position:absolute;width:640px;height:480px;transform-origin:0 0;background:radial-gradient(ellipse at 55% 40%,#152a38,#071019 70%)}.item{position:absolute;box-sizing:border-box;color:#c2dbea;white-space:nowrap;overflow:hidden}.control{font-family:Arial,sans-serif;text-align:left;cursor:pointer;border:1px solid #3a718b;padding:3px 8px}.control:hover:not(:disabled){background:#103d53!important;color:white}.control:disabled{color:#586e7c;cursor:default}.label{padding-top:2px}</style>
<header><h1>Saber Trials / Tournament</h1><p>Layout preview with sample data. These are the native menu positions and actions; fonts are approximate. This does not connect to the game or verify multiplayer behavior.</p>
<select id="scenario"><option value="ready">2v2 ready check</option><option value="registration">Individual registration</option><option value="missing">Disconnected teammate / reserve</option><option value="bracket">32-player bracket</option></select><span id="hint">Try Ready, View bracket, Substitutes and Back.</span></header>
<div id="wrap"><div id="canvas"></div></div>
<script>const views=VIEWS,initial=STATE;let state={},stack=[];
function reset(){state={...initial};stack=['ingame_tournament'];const mode=document.querySelector('#scenario').value;
if(mode==='registration'){Object.assign(state,{ui_ste0:'Registration | Individual / 10 rounds',ui_ste46:'8 / 32 players registered',ui_ste45:'Verified account: select Join tournament.',ui_ste44:'An even 8-32 players required. The operator locks the bracket.',ui_ste12:'All 10 rounds; deciding round at 5-5',ui_stEventCanJoin:'1',ui_stEventCanReady:'0',ui_stEventHasBracket:'0'});for(const n of [1,2,6,7,49,50,51])state['ui_ste'+n]='';state.ui_ste47='Current match';state.ui_ste48='Opponent';}
if(mode==='missing'){Object.assign(state,{ui_ste0:'Paused | 2v2 TFFA / 20 kills',ui_ste45:'Registered reserve. Open Substitutes to replace an absent teammate.',ui_ste44:'Match paused: waiting for reconnect or a registered substitute.',ui_ste1:'Absent teammate | Disconnected',ui_ste49:'1/2 present | 0/2 ready',ui_ste52:'Reconnect: 7:42',ui_ste54:'Choose an absent teammate. The full lineup must ready again.',ui_ste56:'Replace absent teammate',ui_stEventSubAvailable0:'1',ui_stEventCanReady:'0'});}
if(mode==='bracket'){for(let i=0;i<31;i++)state['ui_ste'+(i+13)]=`${i+1}. ${i<16?'Duelist '+(2*i+1)+' / Duelist '+(2*i+2):'TBD / TBD'}${i===0?' [Current]':''}`;for(let i=1;i<=4;i++)state['ui_stEventBracketPage'+i]='1';Object.assign(state,{ui_ste0:'Ready check | Individual / 10 rounds',ui_ste46:'32 / 32 players registered',ui_ste47:'Duelist 1',ui_ste48:'Duelist 2',ui_ste1:'Duelist 1 | Not ready',ui_ste2:'',ui_ste6:'Duelist 2 | Not ready',ui_ste7:'',ui_ste49:'1/1 present | 0/1 ready',ui_ste50:'1/1 present | 0/1 ready',ui_ste51:'Rounds played 0 / 10'});}
render();}
function click(action){if(action.includes('tournament ready')){state.ui_ste11=state.ui_ste11==='Ready'?'Unready':'Ready';state.ui_ste1='Your player | '+(state.ui_ste11==='Unready'?'READY':'Not ready');state.ui_ste55=state.ui_ste11==='Unready'?'You are ready.':'You are not ready.';}
if(action.includes('tournament ready'))state.ui_ste49=state.ui_ste49.replace(/\\d+\\/([12]) ready/,(all,size)=>(state.ui_ste11==='Unready'?'1':'0')+'/'+size+' ready');
if(action.includes('tournament join'))Object.assign(state,{ui_stEventCanJoin:'0',ui_stEventCanLeave:'1',ui_ste46:'9 / 32 players registered',ui_ste45:'Registered as a starter. Waiting for the bracket.',ui_ste55:'Registered for this tournament.'});
if(action.includes('tournament leave'))Object.assign(state,{ui_stEventCanJoin:'1',ui_stEventCanLeave:'0',ui_ste46:'8 / 32 players registered',ui_ste45:'Verified account: select Join tournament.',ui_ste55:'Registration removed.'});
if(action.includes('st_event_substitute '))Object.assign(state,{ui_stEventSubAvailable0:'0',ui_stEventCanReady:'1',ui_ste0:'Ready check | 2v2 TFFA / 20 kills',ui_ste1:'Your player | Not ready',ui_ste49:'2/2 present | 0/2 ready',ui_ste52:'',ui_ste56:'',ui_ste55:'Replacement accepted. Everyone must ready again.',ui_ste54:'No replacement available. Only reserves can replace absent teammates.'});
if(action.includes('st_event_substitute '))Object.assign(state,{ui_ste45:'Your match: use Ready / Unready below.',ui_ste44:'Both complete lineups must select Ready. Click again to unready.',ui_ste50:'2/2 present | 0/2 ready',ui_ste6:'Opponent one | Not ready',ui_ste7:'Opponent two | Not ready'});
if(/close st_event_/.test(action)&&stack.length>1)stack.pop();
const open=action.match(/open (\\w+)/);if(open&&views[open[1]])stack.push(open[1]);
if(open&&!views[open[1]])document.querySelector('#hint').textContent='The Account page uses the existing Discord login flow. This preview does not sign in.';
render();}
function render(){const root=document.querySelector('#canvas');root.replaceChildren();const view=views[stack.at(-1)];for(const item of view.items){const node=document.createElement(item.button?'button':'div');node.className='item '+(item.button?'control':'label');const [x,y,w,h]=item.rect;Object.assign(node.style,{left:(x+view.rect[0])+'px',top:(y+view.rect[1])+'px',width:w+'px',height:h+'px',fontSize:(22*item.scale)+'px'});if(item.fill){const c=item.fill;node.style.background=`rgba(${c[0]*255},${c[1]*255},${c[2]*255},${c[3]})`;}node.textContent=item.cvar?(state[item.cvar]||''):(item.text||'');if(item.button){node.disabled=!!item.cvarTest&&state[item.cvarTest]!=='1';node.onclick=()=>click(item.action);}root.append(node);}resize();}
function resize(){document.querySelector('#canvas').style.transform='scale('+document.querySelector('#wrap').clientWidth/640+')';}document.querySelector('#scenario').onchange=reset;addEventListener('resize',resize);reset();</script>'''
    html=template.replace('VIEWS',json.dumps(views).replace('</','<\\/')).replace('STATE',json.dumps(sample))
    (OUT/'index.html').write_text(html,encoding='utf-8')
    image=Image.new('RGB',(1280,1020),(7,16,25));draw=ImageDraw.Draw(image)
    draw.text((40,10),'LAYOUT PREVIEW - SAMPLE DATA - NOT AN IN-GAME CAPTURE',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20),fill='#6db5cf')
    view=views['ingame_tournament'];overflow=[]
    for item in view['items']:
        x,y,w,h=item['rect'];x=(x+view['rect'][0])*2;y=(y+view['rect'][1])*2+60
        if 'fill' in item:draw.rectangle((x,y,x+w*2,y+h*2),fill=tuple(int(c*255) for c in item['fill'][:3]))
        text=sample.get(item.get('cvar'),item.get('text',''))
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',max(10,round(44*item['scale'])))
        if text and draw.textlength(text,font=font)>w*2-8:overflow.append(text)
        if item['button']:draw.rectangle((x,y,x+w*2,y+h*2),outline='#3a718b',width=1)
        disabled=item.get('cvarTest') and sample.get(item['cvarTest'])!='1'
        draw.text((x+(16 if item['button'] else 0),y+4),text,font=font,fill='#586e7c' if disabled else '#c2dbea')
    image.save(OUT/'lobby-layout.png')
    print('Preview:',OUT/'index.html');print('Approximate-font overflow:',overflow)


if __name__=='__main__':main()
