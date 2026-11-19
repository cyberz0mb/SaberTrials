"""Apply the accepted pause fade only to the main and Play navigation rails."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import shutil
import sys
import zipfile

ROOT=Path(__file__).resolve().parent.parent
STAGE=ROOT/'dist/side-menu-staging'
SOURCE=ROOT/'development-source/menu/side-original'
BACKUP=ROOT/'dist/backups/side-menu-20261012'
MANIFEST=ROOT/'dist/side-menu-install-manifest.json'
FILES=['ui/jamp/main.menu','ui/jamp/multiplayer.menu']
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
theme=module('side_theme','Theme-Menu-Details.py')
shell=module('side_shell','Generate-Menu.py')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def name(s):return re.search(r'\bname\s+"?([^"\s{}]+)',s)[1]

def rail_menu(s,buttons,split_focus):
    for a,b in reversed(theme.blocks(s,'itemDef')):
        item=s[a:b];key=name(item)
        if key=='rail':item=item.replace('sabertrials/rail"','sabertrials/pause_rail"')
        elif key=='rail_edge' or key in [x+'_line' for x in buttons]:
            rect=re.search(r'\brect\s+([^{}]+?)\s+style',item)[1].split()
            item=shell.art(key,*map(float,rect),'ui/assets/sabertrials/pause_'+('edge' if key=='rail_edge' else 'line')).rstrip()
        elif key=='focus_glow':
            soft=item.replace('sabertrials/focus"','sabertrials/pause_focus"')
            # Menu motion is outside the sidebar and keeps the original glow.
            item=item+'\n'+soft.replace('name "focus_glow"','name "side_focus_glow"') if split_focus else soft
        elif split_focus and key in buttons:
            item=item.replace('focus_glow','side_focus_glow')
        s=s[:a]+item+s[b:]
    return s

def transform(s):
    for a,b in reversed(theme.blocks(s,'menuDef')):
        menu=s[a:b];key=name(menu)
        if key in ['main','mainMenu']:
            menu=rail_menu(menu,['play','profile','controls','setup','exit'],True)
        elif key=='multiplayermenu':
            menu=rail_menu(menu,['joinserver_button','startserver_button','quickserver_button',
                'playdemo_button','ranked','rules_button','back'],False)
        s=s[:a]+menu+s[b:]
    return s

def stage():
    checkpoint=json.loads((ROOT/'dist/interface-install-manifest.json').read_text())
    expected={**checkpoint['unchanged'],**checkpoint['files']}
    for rel in FILES:assert digest(ROOT/rel)==expected[rel],'Target changed: '+rel
    protected={}
    for folder in ['ui','gfx']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and p.relative_to(ROOT).as_posix() not in FILES:
                protected[p.relative_to(ROOT).as_posix()]=digest(p)
    for p in list(ROOT.glob('*.cfg'))+list(ROOT.glob('*.dll'))+[ROOT/'client/SaberTrials.x86_64.exe']:
        protected[p.relative_to(ROOT).as_posix()]=digest(p)
    SOURCE.mkdir(parents=True,exist_ok=True)
    for rel in FILES:
        source=SOURCE/Path(rel).name
        if not source.exists():shutil.copy2(ROOT/rel,source)
        assert digest(source)==digest(ROOT/rel)
        s=source.read_bytes().decode('utf-8')
        dest=STAGE/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(transform(s).encode('utf-8'))
    (STAGE/'baseline.json').write_text(json.dumps({'targets':{r:digest(ROOT/r) for r in FILES},'unchanged':protected},indent=2)+'\n')
    print('Staged only main.menu and multiplayer.menu; protected',len(protected),'other files.')

def install():
    baseline=json.loads((STAGE/'baseline.json').read_text())
    evidence=json.loads((ROOT/'dist/verification/side-menu-20261012/result.json').read_text())
    assert evidence['passed'] and evidence['files']=={r:digest(STAGE/r) for r in FILES}
    for rel,sha in {**baseline['targets'],**baseline['unchanged']}.items():
        assert digest(ROOT/rel)==sha,'Changed during review: '+rel
    assert not BACKUP.exists(),'Backup already exists; inspect before reinstalling.'
    BACKUP.mkdir(parents=True)
    for rel in FILES:
        p=BACKUP/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
    (BACKUP/'manifest.json').write_text(json.dumps(baseline['targets'],indent=2)+'\n')
    try:
        for rel in FILES:
            target=ROOT/rel
            pending=target.with_name(target.name+'.side-tmp');shutil.copy2(STAGE/rel,pending);pending.replace(target)
            assert digest(target)==digest(STAGE/rel)
        for rel,sha in baseline['unchanged'].items():assert digest(ROOT/rel)==sha,rel
    except Exception:
        for rel in FILES:shutil.copy2(BACKUP/rel,ROOT/rel)
        raise
    MANIFEST.write_text(json.dumps({'files':{r:digest(ROOT/r) for r in FILES},'unchanged':baseline['unchanged'],
        'backup':str(BACKUP),'scope':'main and Play side navigation only'},indent=2)+'\n')
    archive=ROOT/'dist/SaberTrials-side-menu-20261012.zip'
    paths=FILES+['tools/Fade-Side-Menus.py','tools/Generate-Menu.py','tools/Theme-Menu-Details.py',
        'docs/Side-Menu-Fade.md','dist/side-menu-install-manifest.json','LICENSE.txt','CREDITS.txt']
    paths += [p.relative_to(ROOT).as_posix() for p in SOURCE.glob('*.menu')]
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for rel in paths:z.write(ROOT/rel,'SaberTrials/'+rel)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    archive.with_suffix('.zip.sha256').write_text(digest(archive)+'  '+archive.name+'\n')
    print('Installed two menus. All',len(baseline['unchanged']),'protected files unchanged. Backup:',BACKUP)

if __name__=='__main__':
    if sys.argv[1:]==['install']:install()
    else:stage()
