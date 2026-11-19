"""Replace only the Profile customization icon with a selected-model viewport."""
from pathlib import Path
import hashlib,importlib.util,json,re

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'dist/profile-preview-staging'
SOURCE=ROOT/'development-source/menu/profile-preview-original/player.menu'
spec=importlib.util.spec_from_file_location('front',ROOT/'tools/Stage-Tournament-Frontend.py')
front=importlib.util.module_from_spec(spec);spec.loader.exec_module(front)


def main():
    SOURCE.parent.mkdir(parents=True,exist_ok=True)
    if not SOURCE.exists():SOURCE.write_bytes((ROOT/'ui/jamp/player.menu').read_bytes())
    original=SOURCE.read_text()
    a,b=front.block_span(original,'itemDef','custom')
    old=original[a:b]
    action=re.search(r'\baction\s*\{([^}]+)\}',old,re.S)[1]
    replacement='''itemDef {
 name st_profile_preview
 type ITEM_TYPE_MODEL
 rect 448 250 174 174
 model_g2anim "BOTH_WALK1"
 model_angle 180
 model_rotation 100
 model_g2mins -32 -32 -26
 model_g2maxs 32 32 42
 model_fovx 28
 model_fovy 32
 isCharacter 1
 visible 1
 decoration
 cvarTest "ui_stProfilePreviewAvailable" showCvar { "1" }
}
itemDef {
 name st_profile_unavailable
 type 0
 rect 451 319 170 22
 text "Preview unavailable"
 font 2
 textscale .65
 forecolor .76 .86 .93 1
 visible 1
 decoration
 cvarTest "ui_stProfilePreviewAvailable" showCvar { "0" }
}
itemDef {
 name custom
 type ITEM_TYPE_BUTTON
 style WINDOW_STYLE_EMPTY
 rect 448 250 174 174
 descText @MENUS_CUSTOMPLAYER_DESC
 visible 1
 action {'''+action+'}\n}\n'
    target=STAGE/'ui/jamp/player.menu';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(original[:a]+replacement+original[b:],newline='\n')
    (STAGE/'manifest.json').write_text(json.dumps({'ui/jamp/player.menu':hashlib.sha256(target.read_bytes()).hexdigest()},indent=2)+'\n')
    print('Staged selected-character viewport; existing customization action retained.')


if __name__=='__main__':main()
