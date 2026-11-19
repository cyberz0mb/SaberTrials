"""Isolated live DLC character/stance regression using the actual game client."""
from datetime import datetime
from importlib import import_module
from pathlib import Path
import os,re,shutil,subprocess,sys
b=import_module('Build-DLC-Poses')

def run(renderer='vanilla',full=False,installed=False):
    folder=b.OUT/f'{"installed" if installed else "runtime"}-{renderer}-{datetime.now():%Y%m%d-%H%M%S}'
    mod=folder/'home/SaberTrials';mod.mkdir(parents=True)
    stage={}
    inputs={'client/SaberTrials.x86_64.exe':b.ROOT/'client/SaberTrials.x86_64.exe',
            'cgamex86_64.dll':b.binary('cgame'),
            'jampgamex86_64.dll':b.binary('game'),'uix86_64.dll':b.binary('ui'),
            'client/rd-'+renderer+'_x86_64.dll':b.binary(renderer)}
    for name,path in inputs.items():
        if installed:stage[name]=b.ROOT/name
        else:
            dst=folder/name if name.startswith('client/') else mod/name
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dst);stage[name]=dst
    if not installed:
        for name in ('SDL2.dll','OpenAL32.dll'):shutil.copyfile(b.ROOT/'client'/name,folder/'client'/name)
    hashes={n:b.sha(p) for n,p in stage.items()};source=b.sha(b.RECEIPT)
    cases=[('kyle',0,1,0),('marsattacks',0,0,0),('marsattacks',1,0,0),('marsattacks',1,1,0),
           ('jedi_alien',0,0,0),('jedi_alien',1,1,0),('spacewolves',1,1,0),('hk47',1,1,0),('akaza',1,1,0)]
    if full:
        cases += [(model,1,pose,0) for model in ('marsattacks','jedi_alien') for pose in range(2,11)]
        cases += [(model,hand,pose,1 if pose<13 else 2) for model in ('marsattacks','jedi_alien')
                  for hand in (0,1) for pose in (11,12,13,14)]
    lines=['wait 60','set developer 1','set con_notifytime 0','set sv_pure 0','set g_gametype 0',
        'set g_warmup 0','set fraglimit 0','set st_mvpPrototype 0','set st_translate 0',
        'set g_spawnInvulnerability 0','set saberStyleLoadout "6 1 2"','set forcepowers "7-1-033000000000000330"',
        'set cg_forceModel 0','set cg_deferPlayers 0',
        'set cg_thirdPerson 1','set cg_thirdPersonRange 145','set cg_thirdPersonVertOffset -25',
        'set cg_thirdPersonAngle 150','devmap mp/duel1','wait 450','team free','wait 100',
        'ui_openmenu ingame_setup','wait 10','togglemenu','wait 30']
    for i,(model,hand,pose,family) in enumerate(cases):
        stances=['0']*12;stances[(5,6,9)[family]]=format(pose,'x')
        sabers=[('single_1','none'),('single_1','single_2'),('dual_1','none')][family]
        lines += [f'set model {model}/default',f'set saberHand {hand}','set saberStances '+''.join(stances),
            'set saber1 '+sabers[0],'set saber2 '+sabers[1],'wait 40','map_restart 0','wait 150',
            'setviewpos 480 640 200 90','wait 75',f'echo DLC_POSE_CASE_{i}_{model}_{hand}_{pose}_{family}',
            'st_mvpproof style',f'screenshot_png pose-{i}-{model}','+attack','wait 30','-attack','wait 120']
    lines+=['echo DLC_POSE_DONE','wait 15','quit'];(mod/'test.cfg').write_text('\n'.join(lines)+'\n')
    options=dict(fs_basepath=b.ROOT.parent,fs_homepath=folder/'home',fs_game='SaberTrials',com_unpackLibraries=0,
        logfile=2,net_ip='127.0.0.1',net_port=29590+(renderer=='rend2'),r_fullscreen=0,r_mode=-1,
        r_customwidth=1280,r_customheight=720,cl_renderer='rd-'+renderer,com_maxfps=60,
        s_initsound=0,com_introplayed=1)
    cmd=[str(stage['client/SaberTrials.x86_64.exe']),'+safe']
    for n,v in options.items():cmd+=['+set',n,str(v)]
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    print(folder,flush=True)
    p=subprocess.Popen(cmd+['+exec','test.cfg'],cwd=b.ROOT.parent,startupinfo=si,
        env={**os.environ,'LOCALAPPDATA':str(folder/'local-app-data')},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:assert p.wait(timeout=480 if full else 180)==0
    finally:
        if p.poll() is None:p.kill();p.wait()
    log=(mod/'qconsole.log').read_text(errors='replace')
    assert 'DLC_POSE_DONE' in log,log[-2000:]
    assert 'ERROR:' not in log,'Client reported an error'
    for model in {c[0] for c in cases}:
        assert 'Saber Trials rejected models/players/'+model+'/' not in log,model+' rejected by renderer'
    assert 'added compatible stance frames to models/players/_humanoid/alien_mkx.gla in memory.' in log
    clean=re.sub(r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d ','',log,flags=re.M)
    observed=[]
    for i,(model,hand,pose,family) in enumerate(cases):
        part=clean.split(f'DLC_POSE_CASE_{i}_{model}_{hand}_{pose}_{family}\n')[1].split('DLC_POSE_CASE_',1)[0]
        match=re.search(r'STYLE_STATUS ([^\n]+)',part);assert match,(i,model)
        state=dict((k,int(v)) for k,v in re.findall(r'(\w+)=(\d+)',match[1]))
        assert state['hand']==hand,(i,model,state)
        if not family:
            expected=0 if model=='hk47' else pose
            assert state['stance']==expected,(i,model,state)
            if expected:assert state['torso']==1542+pose,(i,model,state)
        else:assert state['torso']==1542+pose,(i,model,state)
        observed.append(dict(model=model,hand=hand,pose=pose,family=family,state=state))
    assert source==b.sha(b.RECEIPT) and hashes=={n:b.sha(p) for n,p in stage.items()}
    b.write(folder/'result.json',dict(source=source,files=hashes,renderer=renderer,full=full,installed=installed,
        cases=observed,log=b.sha(mod/'qconsole.log')))
    print(f'Passed {len(cases)} live DLC pose/hand cases with {renderer}.',flush=True)

if __name__=='__main__':run('rend2' if '--rend2' in sys.argv else 'vanilla','--full' in sys.argv,'--installed' in sys.argv)
