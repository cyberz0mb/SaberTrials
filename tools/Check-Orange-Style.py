"""Check normal Orange availability, every single-saber ready pose and both hands."""
from pathlib import Path
import argparse,importlib.util,json,os,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('stage',ROOT/'tools/Stage-MVP-Cinematic.py')
stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)

def main(a):
    folder=stage.OUT/'qa'/a.run
    assert not folder.exists(),'Choose a new evidence folder'
    mod=stage.installed_home(folder) if a.installed else stage.stage(folder)
    lines=stage.match_settings()+['set fraglimit 0','set sv_floodProtect 0',
        'set saberStyleLoadout "6 1 2"','set forcepowers "7-1-033000000000000330"',
        'set saberHand '+str(a.hand),'set cg_thirdPerson 1','set cg_thirdPersonRange 110',
        'set cg_thirdPersonAngle 150','devmap mp/duel1','wait 180','team free','wait 120',
        'st_mvptestready','set st_mvpPrototype 0','setviewpos 480 640 200 90','wait 120',
        'g_hybridStyles','st_mvpproof style']
    for pose in range(11):
        packed='00000'+format(pose,'x')+'000000'
        # Ready-pose and hand choices intentionally latch on spawn.
        lines+=['set saberStances '+packed,'wait 30','map_restart 0','wait 120',
            'setviewpos 480 640 200 90','wait 90','echo STYLE_CASE_'+str(pose),
            'st_mvpproof style','screenshot_png orange-%02d'%pose,'+attack']
        for i in range(16):lines+=['wait 8','st_mvpproof style']
        lines+=['-attack','wait 180']
    # Also verify the visible labels of all three stock styles in the normal HUD.
    lines+=['set saberStyleLoadout "1 2 3"','wait 120']
    for i in range(3):lines+=['saberAttackCycle','wait 90','screenshot_png base-style-'+str(i)]
    lines+=['echo STYLE_CHECK_COMPLETE','disconnect','wait 30','quit']
    assert not any(x.startswith('set g_hybridStyles') for x in lines)
    (mod/'orange-qa.cfg').write_text('\n'.join(lines)+'\n')
    cmd=[str(stage.executable(folder,a.installed))]+stage.arguments(folder,a.renderer,a.installed)
    cmd[cmd.index('net_port')+1]=str(29100+a.hand)
    cmd+=['+exec','orange-qa.cfg']
    env=os.environ.copy();env['LOCALAPPDATA']=str(folder/'local-app-data')
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    proc=subprocess.Popen(cmd,cwd=ROOT.parent if a.installed else folder/'bin',env=env,startupinfo=startup,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    print('Orange stance/hand check started: hand='+str(a.hand),flush=True)
    try:proc.wait(timeout=240)
    except subprocess.TimeoutExpired:proc.kill();proc.wait();raise
    log=(mod/'qconsole.log').read_text(errors='replace')
    cases=[]
    for pose in range(11):
        part=log.split('STYLE_CASE_'+str(pose)+'\n',1)[-1]
        part=part.split('STYLE_CASE_',1)[0]
        rows=[tuple(map(int,row)) for row in re.findall(r'STYLE_STATUS actor=(\d+) enabled=(\d+) selected=(\d+) active=(\d+) family=(\d+) hand=(\d+) stance=(\d+) torso=(\d+) animStyle=(\d+) attackStyle=(\d+)',part)]
        assert rows and all(r[1:7]==(1,6,6,3,a.hand,pose) for r in rows), (pose,rows[:2])
        assert any(r[8:]==(6,6) for r in rows),'No actual Orange strike for stance '+str(pose)
        cases.append(dict(stance=pose,hand=a.hand,readyTorso=rows[0][7],attacks=sum(r[8:]==(6,6) for r in rows)))
    assert proc.returncode==0 and 'STYLE_CHECK_COMPLETE' in log
    assert len({c['readyTorso'] for c in cases})==11,'Ready stance did not change'
    result=dict(passed=True,returncode=proc.returncode,installed=a.installed,renderer=a.renderer,
        defaultEnabled=True,cases=cases,log_sha256=stage.helper().sha(mod/'qconsole.log'))
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--hand',type=int,choices=(0,1),required=True)
    p.add_argument('--installed',action='store_true');p.add_argument('--renderer',choices=('vanilla','rend2'),default='vanilla')
    main(p.parse_args())
