"""Exercise candidate dedicated Ghoul2 with a real independently loaded client."""
from datetime import datetime
from importlib import import_module
import os,re,secrets,shutil,socket,subprocess,time
b=import_module('Build-DLC-Poses')

def run():
    folder=b.OUT/f'network-{datetime.now():%Y%m%d-%H%M%S}'
    server=folder/'server';client=folder/'client';port=29596
    mods={r:p/'home/SaberTrials' for r,p in [('server',server),('client',client)]}
    stage={}
    for role,root in [('server',server),('client',client)]:
        mods[role].mkdir(parents=True);(root/'bin').mkdir()
        inputs={'jampgamex86_64.dll':b.binary('game')} if role=='server' else {
            'cgamex86_64.dll':b.binary('cgame'),'uix86_64.dll':b.binary('ui')}
        for name,path in inputs.items():
            dst=mods[role]/name;shutil.copyfile(path,dst);stage[role+'/'+name]=dst
        inputs={'openjkded.x86_64.exe':b.binary('dedicated')} if role=='server' else {
            'SaberTrials.x86_64.exe':b.ROOT/'client/SaberTrials.x86_64.exe',
            'rd-vanilla_x86_64.dll':b.binary('vanilla')}
        for name,path in inputs.items():
            dst=root/'bin'/name;shutil.copyfile(path,dst);stage[role+'/'+name]=dst
        if role=='client':
            for name in ('SDL2.dll','OpenAL32.dll'):shutil.copyfile(b.ROOT/'client'/name,root/'bin'/name)
    hashes={n:b.sha(p) for n,p in stage.items()};source=b.sha(b.RECEIPT)
    secret=secrets.token_hex(16)
    (mods['server']/'test.cfg').write_text('\n'.join(['set developer 1','set sv_pure 0','set g_gametype 0',
        'set sv_maxclients 8','set g_warmup 0','set fraglimit 0','set st_mvpPrototype 0',
        'set g_spawnInvulnerability 0','set rconPassword '+secret,'devmap mp/duel1'])+'\n')
    cases=[('marsattacks',0,1,0),('marsattacks',1,1,0),('jedi_alien',0,1,0),('jedi_alien',1,1,0),
           ('hk47',1,1,0),('spacewolves',1,1,0),('jedi_alien',1,11,1),('jedi_alien',1,13,2)]
    lines=['wait 60','set developer 1','set con_notifytime 0','set st_translate 0',
        'set rconPassword '+secret,'set cl_allowDownload 0','set rate 100000',
        'set saberStyleLoadout "6 1 2"','set forcepowers "7-1-033000000000000330"',
        'set cg_forceModel 0','set cg_deferPlayers 0',
        'set cg_thirdPerson 1','set cg_thirdPersonRange 145','set cg_thirdPersonVertOffset -25',
        'set cg_thirdPersonAngle 150',f'connect 127.0.0.1:{port}','wait 450','team free','wait 100',
        'ui_openmenu ingame_setup','wait 10','togglemenu','wait 30']
    for i,(model,hand,pose,family) in enumerate(cases):
        stances=['0']*12;stances[(5,6,9)[family]]=format(pose,'x')
        sabers=[('single_1','none'),('single_1','single_2'),('dual_1','none')][family]
        lines += [f'set model {model}/default',f'set saberHand {hand}','set saberStances '+''.join(stances),
            'set saber1 '+sabers[0],'set saber2 '+sabers[1],'wait 60','rcon map_restart 0','wait 150',
            'setviewpos 480 640 200 90','wait 75',f'rcon echo DLC_NETWORK_CASE_{i}_{model}',
            'wait 45','rcon st_mvpproof style','wait 45',f'screenshot_png network-{i}-{model}',
            '+attack','wait 30','-attack','wait 120']
    lines+=['echo DLC_NETWORK_DONE','wait 30','disconnect','wait 30','quit']
    (mods['client']/'test.cfg').write_text('\n'.join(lines)+'\n')
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    def launch(role):
        root=server if role=='server' else client
        opts=dict(fs_basepath=b.ROOT.parent,fs_homepath=root/'home',fs_game='SaberTrials',com_unpackLibraries=0,
                  logfile=2,net_ip='127.0.0.1',net_port=port+(role=='client'))
        if role=='server':opts['dedicated']=1
        else:opts.update(r_fullscreen=0,r_mode=-1,r_customwidth=1280,r_customheight=720,cl_renderer='rd-vanilla',
                         com_maxfps=60,s_initsound=0,com_introplayed=1)
        exe='openjkded.x86_64.exe' if role=='server' else 'SaberTrials.x86_64.exe'
        cmd=[str(root/'bin'/exe),'+safe']
        for n,v in opts.items():cmd+=['+set',n,str(v)]
        return subprocess.Popen(cmd+['+exec','test.cfg'],cwd=b.ROOT.parent,startupinfo=si,
            env={**os.environ,'LOCALAPPDATA':str(root/'local-app-data')},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    def log(role):
        path=mods[role]/'qconsole.log'
        return path.read_text(errors='replace') if path.exists() else ''
    def command(value):
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.sendto(b'\xff'*4+('rcon '+secret+' '+value+'\n').encode(),('127.0.0.1',port))
    processes={};print(folder,flush=True)
    try:
        processes['server']=launch('server');start=time.monotonic()
        while '------- Game Initialization -------' not in log('server'):
            assert time.monotonic()-start<45 and processes['server'].poll() is None,'Server did not start'
            time.sleep(.2)
        processes['client']=launch('client')
        assert processes['client'].wait(timeout=200)==0,'Client failed'
        assert 'DLC_NETWORK_DONE' in log('client'),'Client did not complete'
        command('quit');assert processes['server'].wait(timeout=10)==0,'Server failed'
        # Rcon redirects the dedicated server's diagnostic reply to its caller.
        clean=re.sub(r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d ','',log('client'),flags=re.M)
        observed=[]
        for i,(model,hand,pose,family) in enumerate(cases):
            # Server diagnostics prove its own dedicated renderer accepted the model.
            parts=clean.split(f'DLC_NETWORK_CASE_{i}_{model}\n');assert len(parts)>1,(i,'marker missing')
            part=parts[-1].split('DLC_NETWORK_CASE_',1)[0]
            match=re.search(r'STYLE_STATUS ([^\n]+)',part);assert match,(i,'state missing')
            state=dict((k,int(v)) for k,v in re.findall(r'(\w+)=(\d+)',match[1]))
            assert state['hand']==hand,(i,state)
            if model=='hk47':assert state['stance']==0,(i,state)
            else:assert state['torso']==1542+pose,(i,state)
            assert (mods['client']/f'screenshots/network-{i}-{model}.png').exists()
            observed.append(dict(model=model,hand=hand,pose=pose,family=family,state=state))
        assert 'ERROR:' not in log('client'),'Client reported an error'
        for role in mods:
            assert 'added compatible stance frames to models/players/_humanoid/alien_mkx.gla in memory.' in log(role)
            for model in {c[0] for c in cases}:
                assert 'Saber Trials rejected models/players/'+model+'/' not in log(role),model+' rejected by '+role
        assert source==b.sha(b.RECEIPT) and hashes=={n:b.sha(p) for n,p in stage.items()}
        b.write(folder/'result.json',dict(source=source,files=hashes,cases=observed,
            logs={r:b.sha(m/'qconsole.log') for r,m in mods.items()}))
        print(f'Passed {len(cases)} dedicated server/client DLC pose cases.',flush=True)
    finally:
        for p in processes.values():
            if p.poll() is None:p.kill();p.wait()

if __name__=='__main__':run()
