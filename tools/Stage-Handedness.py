"""Stage saber hand menus from current accepted files. Does not install anything."""
from pathlib import Path
import hashlib, json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/handedness-staging'

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def saber_menu():
    source=ROOT/'ui/jamp/saber.menu'
    text=source.read_text()
    if text.count('name st_hand_options'):
        raise RuntimeError('Hand menu already present; inspect before restaging')
    button='''itemDef {
 name st_hand_options
 text "Dominant hand..."
 rect 32 202 170 24
 type ITEM_TYPE_BUTTON
 font 4 textscale .80 forecolor .76 .86 .93 1
 visible 1
 action { uiScript updatesabercvars; close saberMenu; open st_handedness; }
}
'''
    end=text.rfind('}')
    menu_end=text.rfind('}',0,end)
    assert text[menu_end+1:end].strip()==''
    # Draw after the accepted backdrop and controls; inserting first would
    # leave a clickable but invisible button behind the full-screen shader.
    text=text[:menu_end]+button+'\n'+text[menu_end:]
    end=text.rfind('}')
    hand=(ROOT/'development-source/handedness/ui/handedness.menu').read_text()
    return text[:end]+'\n'+hand+'\n'+text[end:]

def main():
    menu=OUT/'ui/jamp/saber.menu'
    menu.parent.mkdir(parents=True,exist_ok=True)
    menu.write_text(saber_menu())
    inputs=['ui/jamp/saber.menu','development-source/handedness/ui/handedness.menu']
    (OUT/'menus.json').write_text(json.dumps({'installed':False,
        'inputs':{n:digest(ROOT/n) for n in inputs},
        'files':{'ui/jamp/saber.menu':digest(menu)}},indent=2)+'\n')
    print(menu)

if __name__=='__main__': main()
