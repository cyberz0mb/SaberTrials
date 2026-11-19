"""Stage only the Photo Mode page; preserve all other accepted menu panels."""
from pathlib import Path
import hashlib, json, re, shutil

ROOT=Path(__file__).resolve().parent.parent
STAGE=ROOT/'dist/photo-staging'
ORIGINAL=ROOT/'development-source/menu/photo-original'

def stage():
    ORIGINAL.mkdir(parents=True,exist_ok=True)
    source=ORIGINAL/'ingame.menu'
    if not source.exists():shutil.copy2(ROOT/'ui/jamp/ingame.menu',source)
    text=source.read_text()
    start=text.index('menuDef { name "st_pause_photo"')
    end=text.index('menuDef { name "st_pause_respawn"',start)
    page=['''menuDef { name "st_photo" rect 0 0 640 480 visible 0 fullscreen 0 popup
 focusColor 1 1 1 1 disableColor .35 .42 .47 1
 onOpen { uiScript stPhotoInit ; setfocus start ; }
 onESC { close st_photo ; }
 itemDef { name panel rect 88 28 464 424 style 1 backcolor .008 .026 .044 .96
  border 1 borderSize 1 bordercolor .30 .78 1 .65 visible 1 decoration }
 itemDef { name heading rect 110 45 420 24 type 0 text "PHOTO MODE" font 4 textscale 1
  forecolor .30 .78 1 1 visible 1 decoration }
 itemDef { name note rect 110 73 420 18 type 0 text "Solo, spectator and replay camera. Online matches stay live."
  font 2 textscale .66 forecolor .76 .86 .93 1 visible 1 decoration }
''']
    def label(name,text,x,y,w=420,scale='.76'):
        return f'itemDef {{ name {name} rect {x} {y} {w} 20 type 0 text "{text}" font 2 textscale {scale} forecolor .76 .86 .93 1 visible 1 decoration }}\n'
    for i,(title,field,default,low,high) in enumerate([
        ('Field of view','Fov',90,20,120),('Camera tilt','Roll',0,-45,45),('Solo / replay speed','Speed',200,20,800)]):
        y=100+i*38
        page += [label('label'+str(i),title,110,y),f'''itemDef {{ name slider{i} rect 280 {y} 150 22 type 10
 cvarFloat "st_uiPhoto{field}" {default} {low} {high} font 2 textscale .75
 forecolor .76 .86 .93 1 visible 1 }}
itemDef {{ name value{i} rect 442 {y} 80 22 type 4 text ""
 cvar "st_uiPhoto{field}" maxChars 8 maxPaintChars 8 font 2 textscale .8
 textalignx 5 textaligny 2 forecolor .76 .86 .93 1 style 1 backcolor .02 .07 .10 1
 border 1 bordercolor .30 .78 1 .6 visible 1 }}
''']
    page += ['''itemDef { name scene rect 110 242 420 23 type 12 text "Scene: " cvar "st_photoFreeze"
 cvarFloatList { "Live" 0 "Freeze" 1 } font 2 textscale .82 forecolor .76 .86 .93 1 visible 1
 cvarTest "st_photoSolo" enableCvar { "1" } }
itemDef { name guides rect 110 271 205 22 type 11 text "Composition grid: " cvar "st_photoGuides"
 font 2 textscale .76 forecolor .76 .86 .93 1 visible 1 }
itemDef { name help rect 330 271 195 22 type 11 text "Show controls: " cvar "st_photoHelp"
 font 2 textscale .76 forecolor .76 .86 .93 1 visible 1 }
''',label('freeze_note','Freeze is available in local solo games, including bots.',110,300,scale='.67'),
        label('speed_note','Online free camera uses your normal spectator movement.',110,317,scale='.67'),
        '''itemDef { name status rect 110 335 420 20 type 0 cvar "st_uiPhotoStatus"
 font 2 textscale .67 forecolor .30 .78 1 1 visible 1 decoration }
''']
    for name,title,x,y,w,action in [
        ('apply','Apply camera',110,205,200,'uiScript stPhotoApply'),
        ('reset','Reset camera',330,205,200,'uiScript stPhotoReset'),
        ('start','Start / Resume',110,361,200,'uiScript stPhotoStart'),
        ('capture','Take photo',330,361,200,'uiScript stPhotoCapture'),
        ('exit','Exit Photo Mode',110,405,200,'uiScript stPhotoExit'),
        ('back','Back',330,405,200,'close st_photo')]:
        page+=[f'''itemDef {{ name {name} rect {x} {y} {w} 30 type 1 text "{title}"
 font 2 textscale .85 textalignx 10 textaligny 5 forecolor .76 .86 .93 1 visible 1
 style 1 backcolor .02 .07 .11 .9 border 1 bordercolor .30 .78 1 .45
 action {{ play "sound/interface/button1.wav" ; {action} ; }} }}
''']
    page += ['}\n']
    staged=text[:start]+''.join(page)+text[end:]
    staged=staged.replace('open st_pause_photo ;','open st_photo ;')
    target=STAGE/'ui/jamp/ingame.menu';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(staged,newline='\n')
    baseline=STAGE/'baseline.json'
    if not baseline.exists():
        paths=[*ROOT.glob('*.cfg'),ROOT/'cgamex86_64.dll',ROOT/'uix86_64.dll',ROOT/'jampgamex86_64.dll',ROOT/'client/SaberTrials.x86_64.exe']
        paths += [p for p in (ROOT/'ui').rglob('*') if p.is_file()]
        paths += [p for p in (ROOT/'gfx').rglob('*') if p.is_file()]
        baseline.write_text(json.dumps({p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2)+'\n')
    print('Staged Photo Mode page; other menus preserved.')

if __name__=='__main__':stage()
