"""Exercise the real pause-menu controls in an isolated UI; never starts a map."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tag',required=True);a=parser.parse_args()
    assert re.fullmatch(r'[a-zA-Z0-9_-]+',a.tag)
    run=ROOT/'dist/verification/handedness-20261024'/a.tag
    assert not run.exists()
    mod=run/'home/SaberTrials';app=run/'bin';mod.mkdir(parents=True);app.mkdir()
    baseline=ROOT/'dist/handedness-baseline-06'
    qa=json.loads((baseline/'qa/qa-manifest.json').read_text())
    assert sha(ROOT/'client/SaberTrials.x86_64.exe')==qa['files']['openjk.x86_64.exe']
    assert sha(ROOT/'client/rd-vanilla_x86_64.dll')==qa['files']['rd-vanilla_x86_64.dll']
    assert sha(baseline/'qa/Release/uix86_64.dll')==qa['files']['uix86_64.dll']
    for name in ('SaberTrials.x86_64.exe','rd-vanilla_x86_64.dll','SDL2.dll','OpenAL32.dll'):
        shutil.copy2(ROOT/'client'/name,app/name)
    shutil.copy2(baseline/'qa/Release/uix86_64.dll',mod/'uix86_64.dll')
    menu=mod/'ui/jamp/ingame_saber.menu';menu.parent.mkdir(parents=True)
    staged=ROOT/'dist/handedness-ingame-staging/ui/jamp/ingame_saber.menu'
    # A disconnected client replaces non-fullscreen menus with the main menu.
    # Override only this presentation flag in the isolated copies; the installed
    # popup remains non-fullscreen, with exactly the same controls and scripts.
    for source,target in ((staged,menu),(ROOT/'ui/jamp/ingame_player.menu',menu.with_name('ingame_player.menu'))):
        text=source.read_text()
        text,count=re.subn(r'(?im)^(\s*fullscreen\s+)0\b',r'\g<1>1',text,count=1)
        assert count==1
        target.write_text(text)
    lines=['wait 100','set saberHand 0','set model kyle/default',
        'set saber1 single_1','set saber2 single_2','ui_openmenu ingame_player','wait 20',
        'st_handqa click saber','wait 20','st_handqa state opened',
        'screenshot_png ingame-hand-right','st_handqa click st_ingame_hand','wait 10',
        'st_handqa state edited','screenshot_png ingame-hand-left',
        'st_handqa escape','wait 10','ui_openmenu ingame_saber','wait 10',
        'st_handqa state cancelled','st_handqa click st_ingame_hand','wait 10',
        'st_handqa click applycurrent','wait 10','ui_openmenu ingame_saber','wait 10',
        'st_handqa state applied','st_handqa click typebut_dual','wait 10',
        'st_handqa state dual','screenshot_png ingame-hand-dual',
        'st_handqa click typebut_staff','wait 10','st_handqa state staff',
        'screenshot_png ingame-hand-staff','st_handqa escape','wait 10',
        'writeconfig hand-ingame-persist.cfg','echo ST_INGAME_HAND_COMPLETE','quit']
    (mod/'hand-ingame.cfg').write_text('\n'.join(lines)+'\n')
    (mod/'hand-ingame-reopen.cfg').write_text('wait 100\nexec hand-ingame-persist.cfg\nwait 10\nui_openmenu ingame_saber\nwait 10\nst_handqa state persisted\necho ST_INGAME_HAND_COMPLETE\nquit\n')
    launch=[str(app/'SaberTrials.x86_64.exe'),'+set','fs_basepath',str(ROOT.parent),
        '+set','fs_homepath',str(run/'home'),'+set','fs_game','SaberTrials',
        '+set','ui_menuFilesMP','ui/jampingame.txt',
        '+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','1280',
        '+set','r_customheight','800','+set','cl_renderer','rd-vanilla',
        '+set','s_initsound','0','+set','com_maxfps','60','+set','logfile','2','+set','com_introplayed','1']
    si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    logs={};codes=[]
    for cfg in ('hand-ingame','hand-ingame-reopen'):
        proc=subprocess.Popen([*launch,'+exec',cfg+'.cfg'],cwd=app,env=os.environ.copy(),startupinfo=si,
                              stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:proc.wait(timeout=70)
        except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10);raise
        codes.append(proc.returncode);assert proc.returncode==0
        log=(mod/'qconsole.log').read_text(errors='replace')
        assert 'ST_INGAME_HAND_COMPLETE' in log and 'HAND_NAV missing' not in log
        assert not re.search(r'Server Initialization|SpawnServer|Loading map',log,re.I)
        loads=re.findall(r'Trying to load "(rd-[^"]+)" from "([^"]+)"',log)
        assert loads and all(n=='rd-vanilla_x86_64.dll' and Path(p).resolve()==app.resolve() for n,p in loads)
        (run/(cfg+'.log')).write_text(log);logs[cfg+'.log']=log
    expected={'opened':(0,0),'edited':(0,1),'cancelled':(0,0),'applied':(1,1),
              'dual':(1,1),'staff':(1,1),'persisted':(1,1)}
    found={}
    for line in '\n'.join(logs.values()).splitlines():
        m=re.search(r'HAND_NAV label=(\S+) menu=(\S+) saved=(\d+) edit=(\d+) hilt=(\S+) second=(\S+)',line)
        if m:
            label,menu_name,saved,edit,hilt,second=m.groups()
            assert menu_name=='ingame_saber' and (int(saved),int(edit))==expected[label],line
            found[label]=line
    assert set(found)==set(expected)
    shots=list((mod/'screenshots').glob('ingame-hand-*.png'));assert len(shots)==4
    artifacts=[*shots,menu,app/'SaberTrials.x86_64.exe',app/'rd-vanilla_x86_64.dll',mod/'uix86_64.dll']
    (run/'evidence.json').write_text(json.dumps({'passed':True,'checks':found,'returncodes':codes,
        'map_or_server_started':False,'checker_sha256':sha(Path(__file__)),
        'staged_menu_sha256':sha(staged),
        'qa_only_overrides':{'ingame_player.menu':'fullscreen 1','ingame_saber.menu':'fullscreen 1'},
        'logs':{name:sha(run/name) for name in logs},
        'files':{str(p.relative_to(run)):sha(p) for p in artifacts}},indent=2)+'\n')
    print('PASS: real pause Player > Saber entry, Right/Left, Escape, Apply, dual/staff and restart persistence.')

if __name__=='__main__':main()
