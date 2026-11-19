"""Native menu-only render/animation checks in a disposable profile; no maps or servers."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess,tempfile

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'dist/verification/profile-preview-20261023'

def source_hashes():
    paths=set((ROOT/'development-source/bot-roles/codemp/ui').glob('*.inc'))
    paths.update((ROOT/'development-source/client-overhaul/patches').glob('*.patch'))
    paths.update((ROOT/'development-source/bot-roles/patches').glob('ui-*.patch'))
    paths.update(ROOT/name for name in ('tools/Build-Interface.py','tools/Build-Menu.py','tools/Build-Overhaul.py','tools/Stage-Profile-Preview.py'))
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',action='store_true');p.add_argument('--production',action='store_true')
    p.add_argument('--installed',action='store_true');p.add_argument('--height',type=int,default=1024)
    p.add_argument('--tag',default='');a=p.parse_args()
    kind='baseline' if a.baseline else 'installed' if a.installed else 'production' if a.production else 'qa'
    run=EVIDENCE/(kind+'-'+str(a.height)+a.tag);assert not run.exists()
    mod=run/'home/SaberTrials';mod.mkdir(parents=True)
    if not a.installed:
        folder=Path(tempfile.gettempdir())/'SaberTrials-interface-20261011'/('build' if a.production else 'build-qa')/'Release'
        shutil.copy2(folder/'uix86_64.dll',mod/'uix86_64.dll')
    if not a.baseline and not a.installed:
        dest=mod/'ui/jamp/player.menu';dest.parent.mkdir(parents=True)
        shutil.copy2(ROOT/'dist/profile-preview-staging/ui/jamp/player.menu',dest)
    qa=not a.production and not a.installed
    lines=['wait 180','ui_openmenu playerMenu','wait 10','set model kyle/default','wait 40']
    def capture(name):return (['st_clientqa profile'] if qa else [])+['screenshot_png ST-'+name,'wait 30']
    lines+=capture('kyle-a')
    if not a.baseline:
        lines+=['wait 190']+capture('kyle-b')
        lines+=['wait 440']+capture('kyle-c')
        for model,key in [('kyle/red','red'),('jawa/default','jawa'),('luffy/default','luffy'),('jedi_hm/head_a1|torso_a1|lower_a1','custom')]:
            lines+=['set model "'+model+'"','wait 45']+capture(key)
        if qa:
            # Real grid mouse selection and unchanged Customize destination.
            lines+=['st_clientqa move playerMenu headlist','st_clientqa click','wait 35','model']+capture('grid-selected')
            lines+=['st_clientqa move playerMenu custom','st_clientqa click','wait 30','st_clientqa state']
            lines+=['screenshot_png ST-customize','wait 20','st_clientqa escape','wait 15','st_clientqa state']
        lines+=['ui_openmenu st_main_tournament','wait 20','screenshot_png ST-tournament-preserved','wait 10']
    lines+=['echo ST_PROFILE_COMPLETE','quit']
    (mod/'st-profile-capture.cfg').write_text('\n'.join(lines)+'\n')
    args=[str(ROOT/'client/SaberTrials.x86_64.exe'),'+set','fs_basepath',str(ROOT.parent),'+set','fs_homepath',str(run/'home'),'+set','fs_game','SaberTrials',
        '+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','1280','+set','r_customheight',str(a.height),
        '+set','cl_renderer','rd-vanilla','+set','s_initsound','0','+set','com_maxfps','60','+set','logfile','2','+set','com_introplayed','1','+exec','st-profile-capture.cfg']
    si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    env=os.environ.copy();env['PATH']=str(ROOT.parent)+';'+env.get('PATH','')
    proc=subprocess.Popen(args,cwd=ROOT.parent,env=env,startupinfo=si,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    print('Checking native Profile preview, without a map or server. PID',proc.pid,flush=True)
    try:proc.wait(timeout=100)
    except subprocess.TimeoutExpired:
        proc.terminate();proc.wait(timeout=10);raise
    log=(mod/'qconsole.log').read_text(errors='replace')
    assert 'ST_PROFILE_COMPLETE' in log and 'Server Initialization' not in log
    if a.baseline:
        assert 'PROFILE_QA valid=0' in log
        print('Confirmed baseline: Profile has no live model preview.',flush=True);return
    if qa:
        assert 'PROFILE_QA valid=0' not in log and 'QA item missing' not in log
        samples=re.findall(r'PROFILE_QA valid=1 selected=(\S+) anim=(\d+) frame=([\d.]+) first=(\d+) last=(\d+) loop=(\d+) yaw=([\d.]+) skin=(\d+)',log)
        assert len(samples)==8,samples
        assert all(s[0]=='kyle/default' for s in samples[:3]),samples[:3]
        assert all(s[1]=='1' and s[5]=='1' and int(s[4])>int(s[3]) for s in samples),samples
        assert len({s[2] for s in samples[:3]})>=2 and float(samples[2][6])>float(samples[0][6])+5,samples[:3]
        assert samples[0][7]!=samples[3][7], 'Red skin did not change'
        assert samples[7][0]!=samples[6][0], 'Grid click did not select a different model'
        assert 'MENU_QA focused=playerMenu2' in log
    images=list((mod/'screenshots').glob('ST-*.png'))
    assert proc.returncode==0 and len(images)==(10 if qa else 8)
    dll=ROOT/'uix86_64.dll' if a.installed else mod/'uix86_64.dll'
    menu=ROOT/'ui/jamp/player.menu' if a.installed else mod/'ui/jamp/player.menu'
    result={'map_or_server_started':False,'exit_code':proc.returncode,'screenshots':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in images},'native_animation_checked':qa,
        'sources':source_hashes(),'files':{'uix86_64.dll':hashlib.sha256(dll.read_bytes()).hexdigest(),'ui/jamp/player.menu':hashlib.sha256(menu.read_bytes()).hexdigest()}}
    (run/'capture.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Verified Profile captures:',len(images),flush=True)


if __name__=='__main__':main()
