"""Capture main-menu pages in the native client. Never loads a map or starts a server."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'dist/tournament-frontend-staging'
EVIDENCE=ROOT/'dist/verification/tournament-frontend-20261023'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--height',type=int,default=720)
    parser.add_argument('--installed',action='store_true')
    parser.add_argument('--qa-ui',type=Path)
    parser.add_argument('--tag',default='')
    args=parser.parse_args()
    mode='qa' if args.qa_ui else 'installed' if args.installed else 'production'
    run=EVIDENCE/(mode+'-'+str(args.height)+args.tag)
    home=run/'home';mod=home/'SaberTrials'
    assert not run.exists(), 'Keep earlier captures; use a fresh run folder.'
    mod.mkdir(parents=True)
    if not args.installed:
        files=json.loads((STAGE/'manifest.json').read_text())
        for name in files:
            dst=mod/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(STAGE/name,dst)
    if args.qa_ui:
        shutil.copy2(args.qa_ui,mod/'uix86_64.dll')
    lines=['wait 240','ui_openmenu multiplayermenu','wait 30']
    def shot(key):return ['screenshot_png ST-'+key,'wait 20']
    def click(menu,item):
        if menu=='multiplayermenu':expected='st_main_tournament'
        elif menu=='st_main_tournament':expected='st_tournament_ready'
        elif menu=='st_tournament_ready':expected={'ready':menu,'unready':menu,'bracket':'st_tournament_bracket1','reserves':'st_tournament_reserves','leave':'st_tournament_leave','back':'st_main_tournament'}[item]
        elif menu.startswith('st_tournament_bracket'):expected='st_tournament_ready' if item=='back' else 'st_tournament_bracket'+item[-1]
        elif menu=='st_tournament_reserves':expected='st_tournament_ready'
        else:expected='st_tournament_ready' if item=='stay' else 'st_main_tournament'
        return [f'st_clientqa move {menu} {item}','st_clientqa click','wait 12','echo ST_EXPECT_FOCUS '+expected,'st_clientqa state']
    lines+=shot('play')
    if args.qa_ui:
        lines+=click('multiplayermenu','tournament')
    else:lines+=['ui_openmenu st_main_tournament','wait 25']
    lines+=shot('select')
    if args.qa_ui:
        lines+=click('st_main_tournament','team5')
        lines+=shot('team5')
        lines+=click('st_tournament_ready','ready')+['ui_stFrontReady']+shot('ready')
        lines+=click('st_tournament_ready','unready')+['ui_stFrontReady']
        lines+=click('st_tournament_ready','bracket')
        lines+=click('st_tournament_bracket1','back')
        lines+=click('st_tournament_ready','reserves')
        lines+=click('st_tournament_reserves','back')
        lines+=click('st_tournament_ready','leave')
        lines+=click('st_tournament_leave','stay')
        lines+=click('st_tournament_ready','leave')+click('st_tournament_leave','confirm')
        for size in range(2,5):
            lines+=click('st_main_tournament','team'+str(size))+shot('team'+str(size))
            lines+=click('st_tournament_ready','back')
        lines+=click('st_main_tournament','individual')
        lines+=click('st_tournament_ready','bracket')
        for page in range(2,5):lines+=click('st_tournament_bracket'+str(page-1),'page'+str(page))
        lines+=shot('bracket4')
        lines+=['st_clientqa escape','wait 12','st_clientqa state','st_clientqa escape','wait 12','st_clientqa state','st_clientqa escape','wait 12','st_clientqa state']
    else:
        for size in (5,1):
            cfg='individual' if size==1 else '5v5'
            lines+=['exec st-tournament-preview-'+cfg+'.cfg','wait 5','ui_openmenu st_tournament_ready','wait 25']+shot('individual' if size==1 else 'team5')
            if size==5:
                lines+=['set ui_stFrontReady 1','wait 10']+shot('ready')
                lines+=['ui_openmenu st_tournament_reserves','wait 10']+shot('reserves')
            lines+=['ui_openmenu st_tournament_bracket1','wait 15']+shot('bracket-'+cfg)
        lines+=['ui_openmenu st_tournament_leave','wait 15']+shot('leave')
    lines+=['ui_report','echo ST_FRONTEND_COMPLETE','quit']
    assert not any(line.split()[0] in ('map','devmap','connect','login','logout','rcon') for line in lines)
    # UI Script_Exec queues EXEC_APPEND. A monolithic console script would
    # finish/quit before queued sample CFGs. Chain isolated QA steps behind
    # those queued commands, just as they run during ordinary user clicks.
    chunks=[[]]
    for line in lines:
        chunks[-1].append(line)
        if args.qa_ui and line=='st_clientqa click':chunks.append([])
    for i,chunk in enumerate(chunks):
        name='st-front-capture.cfg' if i==0 else f'st-front-step{i}.cfg'
        if i+1<len(chunks):chunk.append(f'st_clientqa continue st-front-step{i+1}.cfg')
        (mod/name).write_text('\n'.join(chunk)+'\n')
    command=[str(ROOT/'client/SaberTrials.x86_64.exe'),'+set','fs_basepath',str(ROOT.parent),'+set','fs_homepath',str(home),'+set','fs_game','SaberTrials',
             '+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','1280','+set','r_customheight',str(args.height),
             '+set','cl_renderer','rd-vanilla','+set','s_initsound','0','+set','com_maxfps','60','+set','logfile','2',
             '+set','com_introplayed','1','+set','ui_stMenuMotion','0','+exec','st-front-capture.cfg']
    startup=subprocess.STARTUPINFO();startup.dwFlags=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    env=os.environ.copy();env['PATH']=str(ROOT.parent)+';'+env.get('PATH','')
    proc=subprocess.Popen(command,cwd=ROOT.parent,env=env,startupinfo=startup,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    (run/'process.json').write_text(json.dumps({'pid':proc.pid,'map_loaded':False,'local_server_started':False,'personal_profile_used':False},indent=2))
    print('Capturing native main-menu pages; no map or server. PID',proc.pid,flush=True)
    try:
        proc.wait(timeout=100)
    except subprocess.TimeoutExpired:
        proc.terminate();proc.wait(timeout=10)
        raise RuntimeError('Capture timeout; isolated client stopped.')
    log=(mod/'qconsole.log').read_text(errors='replace')
    assert 'ST_FRONTEND_COMPLETE' in log,log[-1500:]
    assert 'Server Initialization' not in log and 'SpawnServer' not in log
    assert 'QA item missing' not in log
    assert 'unknown menu keyword' not in log.lower() and 'couldn\'t load menu' not in log.lower()
    images=list((mod/'screenshots').glob('ST-*.png'))
    assert len(images)>=5,len(images)
    if args.qa_ui:
        checks=re.findall(r'ST_EXPECT_FOCUS (\w+).*?MENU_QA focused=(\w+)',log,re.S)
        assert len(checks)==sum(line.startswith('echo ST_EXPECT_FOCUS') for line in lines)
        assert all(want==got for want,got in checks),checks
        clean=re.sub(r'\^[0-9]','',log)
        assert 'ui_stFrontReady = "1"' in clean and 'ui_stFrontReady = "0"' in clean
        for cfg in ('5v5','2v2','3v3','4v4','individual'):
            assert 'execing st-tournament-preview-'+cfg+'.cfg' in log
    report={'map_loaded':False,'local_server_started':False,'client_exit_code':proc.returncode,
            'menu_source':{name:hashlib.sha256((ROOT/name if args.installed else STAGE/name).read_bytes()).hexdigest() for name in json.loads((STAGE/'manifest.json').read_text())},
            'screenshots':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in images}}
    (run/'capture.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Captured',len(images),'screenshots in',run,flush=True)


if __name__=='__main__':main()
