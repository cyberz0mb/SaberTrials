"""Stage only the account controls, preserving the accepted main/pause design."""
from pathlib import Path
import hashlib, importlib.util, json, re

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'dist/account-client-staging'
spec=importlib.util.spec_from_file_location('menus',ROOT/'tools/Stage-Tournament.py')
menus=importlib.util.module_from_spec(spec);spec.loader.exec_module(menus)

def page(name):
    return menus.account(name).replace('onOpen {  }','onOpen { setfocus back ; }',1)

def stage():
    manifest={'installed':False,'account_service':'https://accounts-production-b56d.up.railway.app','files':{},'originals':{}}
    for filename,root,page_name,x,y in [('main.menu','main','st_main_account',482,0),('ingame.menu','ingame','st_pause_account',34,400)]:
        name='ui/jamp/'+filename;original=(ROOT/name).read_text();text=original
        # Idempotent restaging, including the previous tournament placeholder.
        if re.search(r'name\s+"?'+page_name+r'"?\s',text):
            a,b=menus.span(text,page_name);text=text[:a]+text[b:]
        a,b=menus.span(text,root)
        if not re.search(r'itemDef\s*\{\s*name\s+"?account_link"?\s',text[a:b]):
            guard='cvarTest "st_uiPauseShell" showCvar { "1" }' if root=='ingame' else ''
            link=menus.button('account_link','Account / Log in',x,y,148,'open '+page_name,guard)
            text=text[:b-1]+link+text[b-1:]
        end=text.rfind('}');text=text[:end]+page(page_name)+text[end:]
        target=STAGE/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
        manifest['files'][name]=hashlib.sha256(target.read_bytes()).hexdigest()
        manifest['originals'][name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    (STAGE/'menu-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Staged main/pause account pages. Installed menus unchanged.')

if __name__=='__main__':stage()
