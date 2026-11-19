"""Compile a QA-only UI and run isolated menu checks. No map/server is started."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,re,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):return {x.relative_to(p).as_posix():sha(x) for x in sorted(p.rglob('*')) if x.is_file() and '__pycache__' not in x.parts}
def prepare(out):
    candidate=json.loads((out/'sources.json').read_text());source=out/'qa/source'
    assert tree(out/'frontend')==candidate['sources']['frontend']
    if source.exists():
        current=tree(source)
        prior=out/'qa/manifest.json'
        if prior.exists():
            assert current==json.loads(prior.read_text())['source'], 'QA source changed unexpectedly'
            for n,h in candidate['sources']['frontend'].items():
                if current.get(n)!=h:shutil.copy2(out/'frontend'/n,source/n)
        else:
            for n,h in current.items():
                if n not in ('codemp/ui/ui_main.c','codemp/ui/ui_atoms.c'):assert h==candidate['sources']['frontend'][n],n
    else:shutil.copytree(out/'frontend',source)
    p=source/'codemp/ui/ui_main.c';main=(out/'frontend/codemp/ui/ui_main.c').read_text()
    anchor='\t\tST_UIRefreshShell();';assert main.count(anchor)==1
    main=main.replace(anchor,'''        { int before=st_stancePendingReturn;
          ST_UIRefreshShell();
          if(before) {menuDef_t* m=Menu_GetFocused();menuDef_t* p=Menus_FindByName(st_stanceReturn);
            trap->Print("STANCE_RETURN focused=%s parentFlags=%d\\n",m?m->window.name:"none",p?p->window.flags:-1);}
        }''')
    main=main.replace('void UI_KeyEvent( int key, qboolean down ) {','void UI_KeyEvent( int key, qboolean down ) {\n trap->Print("STANCE_KEY key=%d down=%d\\n",key,down);')
    main=main.replace('void UI_SetActiveMenu( uiMenuCommand_t menu ) {','void UI_SetActiveMenu( uiMenuCommand_t menu ) {\n trap->Print("STANCE_ACTIVE menu=%d\\n",menu);')
    p.write_text(main+'\n'+(ROOT/'tests/stances/ui_qa.inc').read_text(),newline='\n')
    p=source/'codemp/ui/ui_atoms.c';text=(out/'frontend/codemp/ui/ui_atoms.c').read_text()
    text=text.replace('typedef struct consoleCommand_s {','extern void ST_StanceQA_f(void);\ntypedef struct consoleCommand_s {')
    marker='static consoleCommand_t\tcommands[] = {';assert text.count(marker)==1
    text=text.replace(marker,marker+'\n {"st_stanceqa",ST_StanceQA_f},');p.write_text(text,newline='\n')
    expected=tree(source);changes=[n for n,h in expected.items() if candidate['sources']['frontend'].get(n)!=h]
    assert changes==['codemp/ui/ui_atoms.c','codemp/ui/ui_main.c']
    spec=importlib.util.spec_from_file_location('baseline',ROOT/'tools/Prepare-Handedness-Baseline.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    subprocess.run(['cmake','-S',str(source),'-B',str(out/'qa/build'),'-G','Visual Studio 18 2026','-A','x64',
        *[f'-D{flag}={"ON" if flag=="BuildMPUI" else "OFF"}' for flag in helper.FLAGS]],check=True)
    subprocess.run(['cmake','--build',str(out/'qa/build'),'--config','Release','--parallel','6'],check=True)
    assert tree(source)==expected
    (out/'qa/manifest.json').write_text(json.dumps({'source':expected,'qa_changes':changes,'production_frontend':candidate['sources']['frontend'],
        'qa_dll_sha256':sha(out/'qa/build/Release/uix86_64.dll')},indent=2)+'\n')
def run(out,tag,renderer,width,height,legacy_gla=False):
    record=json.loads((out/'qa/manifest.json').read_text())
    assert sha(out/'qa/build/Release/uix86_64.dll')==record['qa_dll_sha256']
    run=out/'qa/runs'/tag;assert not run.exists();mod=run/'home/SaberTrials';app=run/'bin';mod.mkdir(parents=True);app.mkdir()
    for name in ('SaberTrials.x86_64.exe','rd-vanilla_x86_64.dll','rd-rend2_x86_64.dll','SDL2.dll','OpenAL32.dll'):
        shutil.copy2(ROOT/'client'/name,app/name)
    shutil.copy2(out/'qa/build/Release/uix86_64.dll',mod/'uix86_64.dll')
    shutil.copy2(out/'assets/zz_sabertrials_stances_v1.pk3',mod/'zz_sabertrials_stances_v1.pk3')
    shutil.copytree(out/'menus/ui',mod/'ui')
    if legacy_gla:
        with zipfile.ZipFile(ROOT.parent/'base/japlus_gla_anims.pk3') as z:
            old=z.read('models/players/_humanoid/_humanoid.gla')
        # Replace only this disposable copy's GLA: do not depend on PK3 name sorting.
        with zipfile.ZipFile(mod/'zz_sabertrials_stances_v1.pk3') as z:
            members={name:z.read(name) for name in z.namelist()}
        members['models/players/_humanoid/_humanoid.gla']=old
        with zipfile.ZipFile(mod/'zz_sabertrials_stances_v1.pk3','w',zipfile.ZIP_DEFLATED) as z:
            for name,data in members.items():z.writestr(name,data)
    # No personal login/staff configuration is copied into this isolated home.
    lines=['wait 100','set model kyle/default','set saber1 single_1','set saber2 none','set saberHand 0',
           'set saberStances 000000000000',
           'st_stanceqa open','wait 25','st_stanceqa probe initial','st_stanceqa click next','wait 25',
           'st_stanceqa probe selected','screenshot_png stance-single-right','set ui_stanceHand 1','wait 20',
           'st_stanceqa probe left','screenshot_png stance-single-left','st_stanceqa click apply','wait 20','st_stanceqa probe applied',
           'st_stanceqa open','wait 10','st_stanceqa click next','wait 10','st_stanceqa click back','wait 10','st_stanceqa probe cancelled',
           'st_stanceqa game','wait 20','set ui_stanceFamily 1','wait 20','st_stanceqa click next','wait 20',
           'st_stanceqa probe dual','screenshot_png stance-dual','set ui_stanceFamily 2','wait 20','st_stanceqa click next','wait 20',
           'st_stanceqa probe staff','screenshot_png stance-staff','set ui_stanceFamily 0','set ui_stanceExperimental 1','wait 20',
           'st_stanceqa probe backhand','screenshot_png stance-backhand','wait 2','set ui_stanceExperimental 0','st_stanceqa swing',
           'st_stanceqa probe motion','screenshot_png stance-motion','wait 100','st_stanceqa rest','st_stanceqa probe returned',
           'st_stanceqa click reset','wait 10','st_stanceqa click apply','wait 15',
           'st_stanceqa probe reset','echo ST_STANCES_PREVIEW_COMPLETE','quit']
    if legacy_gla:
        lines=lines[:7]+['st_stanceqa open','wait 25','st_stanceqa probe initial',
           'st_stanceqa click next','wait 25','st_stanceqa probe selected','st_stanceqa click apply','wait 20',
           'st_stanceqa probe refused','screenshot_png stance-incompatible','wait 5','echo ST_STANCES_PREVIEW_COMPLETE','quit']
    (mod/'stance-preview.cfg').write_text('\n'.join(lines)+'\n')
    args=[str(app/'SaberTrials.x86_64.exe'),'+set','fs_basepath',str(ROOT.parent),'+set','fs_homepath',str(run/'home'),'+set','fs_game','SaberTrials',
          '+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth',str(width),'+set','r_customheight',str(height),
          '+set','cl_renderer',renderer,'+set','s_initsound','0','+set','com_maxfps','60','+set','logfile','2','+set','com_introplayed','1','+exec','stance-preview.cfg']
    si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    environment=os.environ.copy()
    # The account engine uses LOCALAPPDATA directly rather than fs_homepath.
    # Give this child an empty private directory so QA cannot restore a real session.
    (run/'local-app-data').mkdir();environment['LOCALAPPDATA']=str(run/'local-app-data')
    proc=subprocess.Popen(args,cwd=app,env=environment,startupinfo=si,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    print('Menu-only preview PID',proc.pid,flush=True)
    try:proc.wait(timeout=90)
    except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10);raise
    log=(mod/'qconsole.log').read_text(errors='replace')
    assert 'Server Initialization' not in log,'Unexpected server startup'
    samples=[line[line.index('STANCE_QA'):] for line in log.splitlines() if 'STANCE_QA' in line]
    (run/'samples.txt').write_text('\n'.join(samples)+'\n')
    assert proc.returncode==0 and 'ST_STANCES_PREVIEW_COMPLETE' in log
    assert 'STANCE_QA missing' not in log
    if legacy_gla:
        assert len(samples)==3 and all('protocol=0' in s and 'saved=000000000000' in s for s in samples),samples
        assert all(int(re.search(r' anim=(-?\d+)',s)[1])<1543 for s in samples),samples
        assert 'menu=st_stances_main' in samples[-1],samples
        (run/'evidence.json').write_text(json.dumps({'menu_only':True,'map_or_server_started':False,
            'legacy_gla_rejected':True,'samples':samples},indent=2)+'\n')
        print('PASS: real mounted legacy GLA override rejected; Stock shown, protocol disabled, Apply did not save.')
        return
    expected={'initial':'saved=000000000000','selected':'choice=1','applied':'saved=100000000000',
              'cancelled':'saved=100000000000','dual':'choice=11','staff':'choice=13','reset':'saved=000000000000'}
    for label,value in expected.items():assert any('label='+label+' ' in s and value in s for s in samples),(label,samples)
    # Disconnected clients force UIMENU_MAIN when only a nonfullscreen popup is
    # visible. Verify the real return before that engine behavior, without a server.
    assert 'STANCE_RETURN focused=ingame_saber parentFlags=131078' in log, 'In-server return did not focus its parent'
    for label in ('initial','selected','left','dual','staff','backhand'):
        assert any('label='+label+' ' in s and 'supported=1' in s and 'protocol=1' in s for s in samples),(label,samples)
    for s in samples:assert 'hand=0 hilt=single_1' in s,s
    motion=next(s for s in samples if 'label=motion ' in s)
    assert int(re.search(r' anim=(-?\d+)',motion)[1])<1543,motion
    assert any('label=returned ' in s and 'anim=1543 ' in s for s in samples),samples
    images=list((mod/'screenshots').glob('stance-*.png'));assert len(images)==6,len(images)
    (run/'evidence.json').write_text(json.dumps({'menu_only':True,'map_or_server_started':False,'ingame_return_checked_before_disconnected_client_main_menu':True,'renderer':renderer,'resolution':[width,height],
        'samples':samples,'images':{p.name:sha(p) for p in images}},indent=2)+'\n')
    print('PASS: native navigation, Apply/Cancel/Reset, compatible poses, unchanged hand/hilt, 6 screenshots.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--prepare',action='store_true');p.add_argument('--run');p.add_argument('--renderer',default='rd-vanilla');p.add_argument('--width',type=int,default=1280);p.add_argument('--height',type=int,default=800);p.add_argument('--legacy-gla',action='store_true');a=p.parse_args();out=a.candidate.resolve()
    if a.prepare:prepare(out)
    if a.run:run(out,a.run,a.renderer,a.width,a.height,a.legacy_gla)
