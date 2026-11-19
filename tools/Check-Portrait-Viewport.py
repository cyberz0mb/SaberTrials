"""Native portrait fixture, no maps/server. QA world-presence simulation is viewport-only."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,re,shutil,subprocess,sys
from PIL import Image,ImageChops
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'dist/handedness-baseline-06';FIX=ROOT/'dist/portrait-vote-fix'
QA=ROOT/'dist/portrait-vote-qa'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def write(p,data):p.write_text(json.dumps(data,indent=2)+'\n')
def build():
    assert not QA.exists();QA.mkdir()
    helper=load('baseline',ROOT/'tools/Prepare-Handedness-Baseline.py')
    provenance=json.loads((BASE/'provenance.json').read_text());manifest=json.loads((FIX/'manifest.json').read_text())
    for name,original in [('ui',BASE/'frontend'),('engine',FIX/'engine')]:
        expected=provenance['components']['frontend'] if name=='ui' else manifest['sources']['engine']
        assert helper.tree(original)==expected
        source=QA/name;shutil.copytree(original,source);assert helper.tree(source)==expected
        if name=='ui':
            f=source/'codemp/ui/ui_atoms.c';f.write_text(f.read_text()+'\n'+(ROOT/'tests/portrait-vote/portrait_qa.inc').read_text(),newline='\n')
            f=source/'codemp/ui/ui_main.c';text=f.read_text();anchor='\t\tST_UIPresentation();';assert text.count(anchor)==1
            f.write_text(text.replace(anchor,anchor+'\n\t\t{ extern void ST_PortraitViewportQAPaint(void); ST_PortraitViewportQAPaint(); }'),newline='\n')
            flag='BuildMPUI';target='uix86_64'
        else:
            f=source/'codemp/rd-rend2/tr_main.cpp';text=f.read_text()
            anchor='if (!tr.world || (refdef->rdflags & RDF_NOWORLDMODEL))';assert text.count(anchor)==1
            # Only this branch sees simulated map presence. No world is loaded,
            # no world traversal is changed and the QA renderer is never installed.
            replacement='if ((!tr.world && !ri.Cvar_VariableIntegerValue("st_viewportqa_world")) || ((refdef->rdflags & RDF_NOWORLDMODEL) && !ri.Cvar_VariableIntegerValue("st_viewportqa_legacy")))'
            f.write_text(text.replace(anchor,replacement),newline='\n')
            flag='BuildMPRend2';target='rd-rend2_x86_64'
        before=helper.tree(source);builddir=QA/('build-'+name)
        subprocess.run(['cmake','-S',str(source),'-B',str(builddir),'-G','Visual Studio 18 2026','-A','x64',
            '-DST_DEPS='+str(BASE/'deps'),*[f'-D{k}={"ON" if k==flag else "OFF"}' for k in helper.FLAGS]],check=True)
        subprocess.run(['cmake','--build',str(builddir),'--config','Release','--target',target,'--parallel','6'],check=True)
        assert helper.tree(source)==before
        write(QA/(name+'-source.json'),{'original':str(original),'changed':[n for n,h in before.items() if expected.get(n)!=h],
            'source':before,'outputs':{p.name:sha(p) for p in (builddir/'Release').glob('*.dll')}})
    print('Built isolated native portrait fixture and viewport-only simulation.')
def run(tag,renderer,width,height):
    folder=ROOT/'dist/verification/portrait-vote-20261024'/tag
    assert not folder.exists();app=folder/'bin';mod=folder/'home/SaberTrials';app.mkdir(parents=True);mod.mkdir(parents=True)
    for name in ('SDL2.dll','OpenAL32.dll','SaberTrials.x86_64.exe'):shutil.copy2(ROOT/'client'/name,app/name)
    dll='rd-vanilla_x86_64.dll' if renderer=='vanilla' else 'rd-rend2_x86_64.dll'
    source=ROOT/'client'/dll if renderer=='vanilla' else (QA/'build-engine/Release'/dll if renderer=='simulation' else FIX/'build-engine/Release'/dll)
    shutil.copy2(source,app/dll);shutil.copy2(QA/'build-ui/Release/uix86_64.dll',mod/'uix86_64.dll')
    lines=['wait 100','set st_portraitviewportqa 1','set st_portraitviewportqa_hidden 1','wait 90','screenshot_png empty','wait 120']
    cases=['fixed'] if renderer!='simulation' else ['no-map','legacy-loaded','fixed-loaded']
    for case in cases:
        lines += ['set st_portraitviewportqa_hidden 0',f'set st_viewportqa_world {int(case!="no-map")}',
            f'set st_viewportqa_legacy {int(case=="legacy-loaded")}', 'wait 120',f'screenshot_png {case}','wait 120']
    lines+=['echo PORTRAIT_VIEW_QA_COMPLETE','quit'];(mod/'viewport.cfg').write_text('\n'.join(lines)+'\n')
    args=[str(app/'SaberTrials.x86_64.exe'),'+set','fs_basepath',str(ROOT.parent),'+set','fs_homepath',str(folder/'home'),
        '+set','fs_game','SaberTrials','+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth',str(width),
        '+set','r_customheight',str(height),'+set','cl_renderer','rd-vanilla' if renderer=='vanilla' else 'rd-rend2',
        '+set','s_initsound','0','+set','com_maxfps','60','+set','logfile','2','+set','com_introplayed','1','+exec','viewport.cfg']
    si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    env={k.upper():v for k,v in os.environ.items()}
    account_home=folder/'private-appdata';account_home.mkdir();env['LOCALAPPDATA']=str(account_home)
    proc=subprocess.Popen(args,cwd=app,env=env,startupinfo=si,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:proc.wait(timeout=100)
    except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10);raise
    log=(mod/'qconsole.log').read_text(errors='replace')
    assert proc.returncode==0 and 'PORTRAIT_VIEW_QA_COMPLETE' in log and 'PORTRAIT_VIEW_QA ready bolt=' in log
    assert 'Server Initialization' not in log and 'PORTRAIT_VIEW_QA failed' not in log
    loads=re.findall(r'Trying to load "(rd-[^"]+)" from "([^"]+)"',log)
    assert loads and all(name==dll and Path(path).resolve()==app.resolve() for name,path in loads),loads
    assert 'Account: Logged in' not in log,'Account storage was not isolated'
    empty=Image.open(mod/'screenshots/empty.png').convert('RGB');assert empty.size==(width,height)
    boxes={};head=int(80*height/480);top=int(5*height/480)
    for case in cases:
        shot=mod/'screenshots'/(case+'.png');diff=ImageChops.difference(empty,Image.open(shot).convert('RGB'))
        mask=diff.convert('L').point(lambda v:255 if v>12 else 0);box=mask.getbbox();assert box,case
        pixels=sum(v>0 for v in mask.getdata());assert pixels>100,(case,pixels)
        expected_y=height-top-head if case=='legacy-loaded' else top
        assert box[1]>=expected_y-2 and box[3]<=expected_y+head+2,(case,box,expected_y)
        assert box[0]>=int(width*630/640)-head-2 and box[2]<=int(width*630/640)+2,(case,box)
        boxes[case]={'changed_pixel_bounds':box,'head_pixels':pixels}
    files=[*app.glob('*'),mod/'uix86_64.dll',mod/'viewport.cfg',mod/'qconsole.log',*(mod/'screenshots').glob('*.png')]
    write(folder/'evidence.json',{'passed':True,'renderer':renderer,'dimensions':[width,height],
        'simulated_loaded_world':renderer=='simulation','map_or_server_started':False,'returncode':proc.returncode,
        'checker':sha(Path(__file__)),'probe':sha(ROOT/'tests/portrait-vote/portrait_qa.inc'),
        'cases':boxes,'files':{p.relative_to(folder).as_posix():sha(p) for p in files}})
    print('PASS native portrait pixels:',boxes)
def main():
    p=argparse.ArgumentParser();p.add_argument('--build',action='store_true');p.add_argument('--tag');p.add_argument('--renderer',choices=['vanilla','production','simulation'],default='production');p.add_argument('--width',type=int,default=1280);p.add_argument('--height',type=int,default=720);a=p.parse_args()
    if a.build:build()
    else:assert a.tag;run(a.tag,a.renderer,a.width,a.height)
if __name__=='__main__':main()
