"""Capture Profile layout and exercise its fields in an isolated menu-only client."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,math,os,re,shutil,subprocess,tempfile

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'dist/verification/profile-layout-20261023'
STAGE=ROOT/'dist/profile-layout-staging'
spec=importlib.util.spec_from_file_location('profile_preview_check',ROOT/'tools/Check-Profile-Preview.py')
preview=importlib.util.module_from_spec(spec);spec.loader.exec_module(preview)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def sources():return {**preview.source_hashes(),'tools/Stage-Profile-Layout.py':digest(ROOT/'tools/Stage-Profile-Layout.py')}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--production',action='store_true');p.add_argument('--installed',action='store_true')
    p.add_argument('--height',type=int,default=1024);p.add_argument('--tag',default='');a=p.parse_args()
    qa=not a.production and not a.installed
    kind='installed' if a.installed else 'production' if a.production else 'qa'
    run=EVIDENCE/(kind+'-'+str(a.height)+a.tag);assert not run.exists()
    mod=run/'home/SaberTrials';mod.mkdir(parents=True)
    targets=json.loads((STAGE/'manifest.json').read_text())
    if not a.installed:
        folder=Path(tempfile.gettempdir())/'SaberTrials-interface-20261011'/('build-qa' if qa else 'build')/'Release'
        shutil.copy2(folder/'uix86_64.dll',mod/'uix86_64.dll')
        for name in targets:
            target=mod/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(STAGE/name,target)
    lines=['wait 100','set name "Profile Test"','ui_openmenu playerMenu','wait 10','set model kyle/default','wait 35']
    def capture(name):return ['screenshot_png ST-'+name,'wait 20']
    if qa:lines+=['st_clientqa profile']
    lines+=capture('profile')
    if qa:
        lines+=['st_clientqa move playerMenu namefield','wait 15','st_clientqa state']+capture('name-focus')
        lines+=['st_clientqa click','st_clientqa type Q','st_clientqa enter','ui_Name','wait 20','st_clientqa profile']
        lines+=['set ui_Name "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW"','wait 10']+capture('long-name')
        lines+=['set ui_Name "Profile Test"','st_clientqa move playerMenu headlist','st_clientqa click','wait 20','st_clientqa profile']+capture('selection')
        lines+=['st_clientqa move playerMenu custom','st_clientqa click','wait 15','st_clientqa state','st_clientqa escape','wait 10']
        lines+=['st_clientqa move playerMenu next','st_clientqa click','wait 15','st_clientqa state','ui_openmenu playerMenu','wait 10']
    lines+=['set model boba_fett/default','wait 30']+capture('boba')
    lines+=['set model luffy/default','wait 30']+capture('luffy')
    lines+=['echo ST_PROFILE_LAYOUT_COMPLETE','quit']
    (mod/'st-profile-layout.cfg').write_text('\n'.join(lines)+'\n')
    args=[str(ROOT/'client/SaberTrials.x86_64.exe'),'+set','fs_basepath',str(ROOT.parent),'+set','fs_homepath',str(run/'home'),'+set','fs_game','SaberTrials',
        '+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','1280','+set','r_customheight',str(a.height),
        '+set','cl_renderer','rd-vanilla','+set','s_initsound','0','+set','com_maxfps','60','+set','logfile','2','+set','com_introplayed','1','+exec','st-profile-layout.cfg']
    si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    env=os.environ.copy();env['PATH']=str(ROOT.parent)+';'+env.get('PATH','')
    proc=subprocess.Popen(args,cwd=ROOT.parent,env=env,startupinfo=si,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    print('Checking native Profile layout, no map/server. PID',proc.pid,flush=True)
    try:proc.wait(timeout=120)
    except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10);raise
    log=(mod/'qconsole.log').read_text(errors='replace')
    assert proc.returncode==0 and 'ST_PROFILE_LAYOUT_COMPLETE' in log and 'Server Initialization' not in log
    if qa:
        assert 'MENU_QA item=namefield' in log and 'MENU_QA focused=playerMenu2' in log and 'MENU_QA focused=saberMenu' in log
        plain=re.sub(r'\^[0-9]','',log)
        assert re.search(r'Cvar ui_Name = "[^"]*Q',plain), 'Typing did not reach the name field'
        states=re.findall(r'PROFILE_QA valid=1 selected=(\S+) anim=(\d+) frame=([\d.]+).*loop=(\d+)',log)
        assert len(states)==3 and all(s[1]=='1' and s[3]=='1' for s in states)
        assert states[0][2]!=states[1][2] and states[0][0]!=states[2][0]
        geometry=re.findall(r'PROFILE_LAYOUT width=([\d.]+) height=([\d.]+) fovx=([\d.]+) fovy=([\d.]+) xscale=([\d.]+) yscale=([\d.]+)',log)
        for dims in geometry:
            w,h,fx,fy,xs,ys=map(float,dims)
            assert abs(math.tan(math.radians(fx/2))/math.tan(math.radians(fy/2))-w*xs/(h*ys))<.002
        assert len(geometry)==3
    captures=list((mod/'screenshots').glob('ST-*.png'))
    assert len(captures)==(6 if qa else 3)
    files={name:digest((ROOT if a.installed else mod)/name) for name in [*targets,'uix86_64.dll']}
    (run/'capture.json').write_text(json.dumps({'files':files,'sources':sources(),'screenshots':{str(f.relative_to(ROOT)):digest(f) for f in captures},'native_controls_checked':qa,'exit_code':proc.returncode,'map_or_server_started':False},indent=2)+'\n')
    print('Verified native layout captures:',len(captures),flush=True)

if __name__=='__main__':main()
