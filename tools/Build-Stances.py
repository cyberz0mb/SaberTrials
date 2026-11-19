"""Prepare/build isolated ready-stance candidate; no installation or server launch."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, re, shutil, subprocess, sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/stance-candidate'
BASE=ROOT/'dist/handedness-baseline-06'

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def tree(p):return {f.relative_to(p).as_posix():sha(f) for f in sorted(p.rglob('*')) if f.is_file() and '__pycache__' not in f.parts}
def write(p,value):p.write_text(json.dumps(value,indent=2)+'\n')
def inputs():
    result=tree(ROOT/'development-source/stances')
    result.update({'tools/'+n:sha(ROOT/'tools'/n) for n in ['Build-Stances.py','stance_library.py']})
    return result
def menus():
    page=(ROOT/'development-source/stances/stances.menu').read_text()
    for path,parent,mode,rect in [('ui/jamp/saber.menu','saberMenu','Main','32 230 170 24'),
                                  ('ui/jamp/ingame_saber.menu','ingame_saber','Game','15 179 180 22')]:
        text=(ROOT/path).read_text()
        # A file can contain several pages (e.g. the appended handedness page).
        # Locate the named Saber menu, never the last menu in the file.
        match=re.search(r'\bmenuDef\s*\{\s*name\s+(?:"'+re.escape(parent)+r'"|'+re.escape(parent)+r')\s',text,re.I)
        assert match, 'Missing Saber parent: '+parent
        brace=text.index('{',match.start());depth=0;parent_end=None
        for token in re.finditer(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/|[{}]',text[brace:]):
            if token[0]=='{':depth+=1
            elif token[0]=='}':
                depth-=1
                if not depth:parent_end=brace+token.start();break
        assert parent_end is not None, 'Unclosed Saber parent: '+parent
        button='''itemDef {
 name st_stances_options text "Stances..." rect '''+rect+'''
 type ITEM_TYPE_BUTTON font 4 textscale .75 forecolor .76 .86 .93 1 visible 1
 action { close '''+parent+'''; uiScript stStanceOpen'''+mode+'''; }
}
'''
        text=text[:parent_end]+button+text[parent_end:]
        last=text.rfind('}')
        text=text[:last]+page.replace('@PAGE@','st_stances_'+mode.lower())+text[last:]
        p=OUT/'menus'/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,newline='\n')
def prepare():
    assert not (OUT/'sources.json').exists(),'Candidate already prepared; do not overwrite frozen sources'
    accepted={}
    for filename in ('handedness-install.json','handedness-ingame-install.json','portrait-vote-install.json'):
        m=read(ROOT/'dist'/filename);accepted.update(m.get('protected',{}));accepted.update(m['after'])
    for name,h in accepted.items():
        if sha(ROOT/name)!=h:raise ValueError('Installed baseline changed: '+name)
    baseline=read(BASE/'provenance.json');fix=read(ROOT/'dist/portrait-vote-fix/manifest.json')
    origins={'game':ROOT/'dist/portrait-vote-fix/game','frontend':BASE/'frontend'}
    expected={'game':fix['sources']['game'],'frontend':baseline['components']['frontend']}
    library=read(OUT/'assets/library.json');overlay=module('stance_overlay',ROOT/'development-source/stances/prepare.py')
    before=inputs();changes={};sources={}
    for kind,original in origins.items():
        assert tree(original)==expected[kind], 'Accepted source drift: '+kind
        target=OUT/kind
        if target.exists():raise ValueError('Partial candidate exists; use a new candidate directory')
        shutil.copytree(original,target)
        if kind=='frontend':
            # Catalog strings are generated from the same reviewed asset manifest.
            names=['Stock']+[p['label'] for p in library['stances']]
            authors=['Raven Software']+[p['author'] for p in library['stances']]
            authors[15]='Backhand HQ / attribution under review'
            code='static const char* st_stanceNames[16]={'+','.join(json.dumps(s) for s in names)+'};\n'
            code+='static const char* st_stanceAuthors[16]={'+','.join(json.dumps(s) for s in authors)+'};\n'
            (target/'codemp/ui/ui_st_stance_catalog.h').write_text(code,newline='\n')
        overlay.apply(target,kind,library)
        sources[kind]=tree(target)
        changes[kind]=[n for n,h in sources[kind].items() if expected[kind].get(n)!=h]
    menus()
    assert before==inputs()
    write(OUT/'sources.json',{'installed':False,'inputs':before,'protected':accepted,
         'origins':{k:str(v) for k,v in origins.items()},'baseline_sources':expected,
         'sources':sources,'changes':changes,'library_sha256':sha(OUT/'assets/zz_sabertrials_stances_v1.pk3'),
         'menus':tree(OUT/'menus'),'builds':{}})
    print('Prepared isolated game/frontend candidate; installed files unchanged.')
def build(kind):
    m=read(OUT/'sources.json');assert inputs()==m['inputs']
    assert tree(OUT/kind)==m['sources'][kind]
    helper=module('baseline',ROOT/'tools/Prepare-Handedness-Baseline.py')
    builddir=OUT/('build-'+kind)
    subprocess.run(['cmake','-S',str(OUT/kind),'-B',str(builddir),'-G','Visual Studio 18 2026','-A','x64',
        '-DST_DEPS='+str(BASE/'deps'),'-DST_STAFF_QA=OFF',
        *[f'-D{flag}={"ON" if flag in helper.TARGETS[kind] else "OFF"}' for flag in helper.FLAGS]],check=True)
    subprocess.run(['cmake','--build',str(builddir),'--config','Release','--parallel','6'],check=True)
    assert tree(OUT/kind)==m['sources'][kind] and inputs()==m['inputs']
    m=read(OUT/'sources.json');m['builds'][kind]={n:sha(builddir/'Release'/n) for n in helper.ARTIFACTS[kind]}
    write(OUT/'sources.json',m)
    print('Built',kind,'without installing.')
def sync():
    """Regenerate only this candidate's recorded overlay after an in-scope edit."""
    m=read(OUT/'sources.json')
    overlay=module('stance_overlay',ROOT/'development-source/stances/prepare.py')
    library=read(OUT/'assets/library.json')
    for kind,origin in m['origins'].items():
        source=OUT/kind;original=Path(origin)
        assert tree(source)==m['sources'][kind], 'Candidate changed outside the overlay: '+kind
        assert tree(original)==m['baseline_sources'][kind], 'Baseline drift: '+kind
        for name in m['changes'][kind]:
            if name in m['baseline_sources'][kind]:shutil.copy2(original/name,source/name)
        overlay.apply(source,kind,library)
        m['sources'][kind]=tree(source)
        m['changes'][kind]=[n for n,h in m['sources'][kind].items() if m['baseline_sources'][kind].get(n)!=h]
    menus();m['menus']=tree(OUT/'menus');m['inputs']=inputs();m['builds']={}
    m['library_sha256']=sha(OUT/'assets/zz_sabertrials_stances_v1.pk3')
    write(OUT/'sources.json',m);print('Regenerated recorded candidate overlays.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--sync',action='store_true');p.add_argument('--build',choices=['game','frontend']);p.add_argument('--output',type=Path,default=OUT);a=p.parse_args()
    OUT=a.output.resolve()
    if OUT.parent != (ROOT/'dist').resolve() or not OUT.name.startswith('stance-candidate'):
        p.error('Output must be a dedicated dist/stance-candidate directory')
    if a.prepare:prepare()
    elif a.sync:sync()
    elif a.build:build(a.build)
    else:p.error('Use --prepare or --build')
