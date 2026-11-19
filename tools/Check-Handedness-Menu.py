"""Exercise the staged menu through real UI mouse/key actions, without a map."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, re, shutil, subprocess

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tag',required=True)
    parser.add_argument('--build-dir',type=Path,default=ROOT/'dist/handedness-preview-build/Release')
    a=parser.parse_args()
    run=ROOT/'dist/verification/handedness-20261024'/a.tag
    if run.exists():raise RuntimeError('Evidence directory already exists')
    mod=run/'home/SaberTrials';app=run/'bin';mod.mkdir(parents=True);app.mkdir()
    build=a.build_dir.resolve()
    for name in ('SDL2.dll','OpenAL32.dll'):shutil.copy2(ROOT/'client'/name,app/name)
    shutil.copy2(build/'openjk.x86_64.exe',app/'SaberTrials.x86_64.exe')
    shutil.copy2(build/'rd-vanilla_x86_64.dll',app/'rd-vanilla_x86_64.dll')
    shutil.copy2(build/'uix86_64.dll',mod/'uix86_64.dll')
    spec=importlib.util.spec_from_file_location('stage_hand',ROOT/'tools/Stage-Handedness.py')
    stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)
    menu=mod/'ui/jamp/saber.menu';menu.parent.mkdir(parents=True);menu.write_text(stage.saber_menu())
    lines=['wait 100','set model kyle/default','set saberHand 0','set saber1 single_1',
           'set saber2 single_2','set ui_saber_type dual','st_handqa navigation','wait 20',
           'st_handqa state initial','screenshot_png hand-nav-entry',
           'st_handqa click st_hand_options','wait 20','st_handqa state opened',
           'st_handqa click hand','wait 10','st_handqa state edited',
           'screenshot_png hand-nav-left','st_handqa click back','wait 10','st_handqa state cancelled',
           'st_handqa click st_hand_options','wait 10','st_handqa click hand','wait 10',
           'st_handqa click apply','wait 20','st_handqa state applied',
           'st_handqa click st_hand_options','wait 10','st_handqa click hand','wait 10',
           'st_handqa escape','wait 20','st_handqa state escaped',
           'screenshot_png hand-nav-return',
           'st_handqa click typebut_dual','wait 20','st_handqa click st_hand_options','wait 20',
           'st_handqa probe','screenshot_png hand-nav-dual','st_handqa click back','wait 20',
           'st_handqa click typebut_staff','wait 20','st_handqa click st_hand_options','wait 20',
           'st_handqa probe','screenshot_png hand-nav-staff','st_handqa click back','wait 20',
           'set saber1 single_1','set saber2 single_2','st_handqa navigation','wait 10','writeconfig hand-persist.cfg',
           'echo ST_HAND_MENU_COMPLETE','quit']
    (mod/'hand-menu.cfg').write_text('\n'.join(lines)+'\n')
    (mod/'hand-reopen.cfg').write_text('wait 100\nexec hand-persist.cfg\nwait 10\nst_handqa navigation\nwait 20\nst_handqa state persisted\necho ST_HAND_MENU_COMPLETE\nquit\n')
    base=[str(app/'SaberTrials.x86_64.exe'),'+set','fs_basepath',str(ROOT.parent),'+set','fs_homepath',str(run/'home'),
          '+set','fs_game','SaberTrials','+set','r_fullscreen','0','+set','r_mode','-1',
          '+set','r_customwidth','1280','+set','r_customheight','800','+set','cl_renderer','rd-vanilla',
          '+set','s_initsound','0','+set','com_maxfps','60','+set','logfile','2','+set','com_introplayed','1']
    si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    logs=[];returncodes=[]
    for cfg in ('hand-menu','hand-reopen'):
        proc=subprocess.Popen([*base,'+exec',cfg+'.cfg'],cwd=app,env=os.environ.copy(),startupinfo=si,
                              stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:proc.wait(timeout=70)
        except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10);raise
        log=(mod/'qconsole.log').read_text(errors='replace');(run/(cfg+'.log')).write_text(log);logs.append(log)
        returncodes.append(proc.returncode)
        assert proc.returncode==0 and 'ST_HAND_MENU_COMPLETE' in log
        assert 'Server Initialization' not in log and 'HAND_NAV missing' not in log
        loads=re.findall(r'Trying to load "(rd-[^"]+)" from "([^"]+)"',log)
        assert loads and all(name=='rd-vanilla_x86_64.dll' and Path(folder).resolve()==app.resolve()
                             for name,folder in loads),loads
    expected={'initial':('saberMenu',0,0),'opened':('st_handedness',0,0),
              'edited':('st_handedness',0,1),'cancelled':('saberMenu',0,0),
              'applied':('saberMenu',1,1),'escaped':('saberMenu',1,1),'persisted':('saberMenu',1,1)}
    found={}
    for line in '\n'.join(logs).splitlines():
        match=re.search(r'HAND_NAV label=(\S+) menu=(\S+) saved=(\d+) edit=(\d+) hilt=(\S+) second=(\S+)',line)
        if match:
            label,menu_name,saved,edit,hilt,second=match.groups()
            assert (menu_name,int(saved),int(edit))==expected[label],line
            assert (hilt,second)==('single_1','single_2'),line
            found[label]=line
    assert set(found)==set(expected),found
    probes=[s for s in logs[0].splitlines() if 'HAND_QA ready' in s]
    assert len(probes)==2 and 'style=dual hand=1 mirror=1' in probes[0] and 'style=staff hand=1 mirror=1' in probes[1],probes
    shots=list((mod/'screenshots').glob('hand-nav-*.png'));assert len(shots)==5
    artifacts=[*shots,menu,app/'SaberTrials.x86_64.exe',app/'rd-vanilla_x86_64.dll',mod/'uix86_64.dll']
    (run/'evidence.json').write_text(json.dumps({'map_or_server_started':False,'checks':found,
        'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'logs':{cfg+'.log':hashlib.sha256((run/(cfg+'.log')).read_bytes()).hexdigest()
                for cfg in ('hand-menu','hand-reopen')},'returncodes':returncodes,
        'files':{str(p.relative_to(run)):hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts}},indent=2)+'\n')
    print('Native menu entry, mouse toggle, Back, Apply, Escape and fresh-process persistence passed:',run)


if __name__=='__main__':main()
