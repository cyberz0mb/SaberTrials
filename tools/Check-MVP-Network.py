"""Run a private dedicated match with two independent native clients."""
from pathlib import Path
import argparse, importlib.util, json, os, re, secrets, shutil, socket, subprocess, time
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('stage',ROOT/'tools/Stage-MVP-Cinematic.py')
stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)

def main(args):
    root=stage.OUT/'qa'/args.run
    assert not root.exists(),'Choose a new evidence folder'
    build=stage.helper();state=build.verify()
    server=root/'server';a=root/'viewer-a';b=root/'viewer-b'
    mods={name:stage.stage(folder) for name,folder in [('server',server),('a',a),('b',b)]}
    dedicated=stage.OUT/'build-server/Release/openjkded.x86_64.exe'
    assert build.sha(dedicated)==build.read(stage.OUT/'server-build.json')['binary_sha256']
    shutil.copy2(dedicated,server/'bin/openjkded.x86_64.exe')
    password=secrets.token_hex(16);port=29087
    def command(value):
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.sendto(b'\xff'*4+('rcon '+password+' '+value+'\n').encode(),('127.0.0.1',port))
    server_lines=stage.match_settings()+['set sv_maxclients 8','set sv_floodProtect 1',
        'set st_mvpTestSingleSaber 0','set rconPassword "'+password+'"','set g_saberDmgDelay_Idle 100000',
        'devmap mp/duel1']
    # Do not explicitly enable replay: a normal dedicated server enables it by default.
    server_lines=[line for line in server_lines if not line.startswith('set st_mvpPrototype ')]
    (mods['server']/'server.cfg').write_text('\n'.join(server_lines)+'\n')
    common=['set st_mvpPrototype 1','set cl_allowDownload 0','set rate 100000','set snaps 40','set cl_maxpackets 60',
            'set cg_saberTrail 1','set cg_dismember 2','connect 127.0.0.1:'+str(port),'wait 350']
    a_lines=['set name Network_A','set model joker/nohat',
        'set saber1 single_1','set saber2 single_1']+common+['team free','wait 180',
        'setviewpos 480 640 200 90','wait 120','st_mvptestready','echo NETWORK_A_READY',
        'wait 1500']
    for i in range(40):a_lines+=['wait 90','screenshot_png network-a-%02d'%i]
    a_lines+=['wait 2000','disconnect','wait 30','quit']
    (mods['a']/'viewer.cfg').write_text('\n'.join(a_lines)+'\n')
    b_lines=['set name Network_B','set model kyle/default']+common+['team spectator','wait 180','st_mvptestready','echo NETWORK_B_READY']
    for i in range(120):b_lines+=['wait 60','st_mvpskip']
    b_lines+=['screenshot_png network-b-after','disconnect','wait 30','quit']
    (mods['b']/'viewer.cfg').write_text('\n'.join(b_lines)+'\n')
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    def launch(folder,server_mode=False):
        env=os.environ.copy();env['LOCALAPPDATA']=str(folder/'local-app-data')
        if server_mode:
            commandline=[str(folder/'bin/openjkded.x86_64.exe'),'+set','dedicated','1',
                '+set','fs_basepath',str(ROOT.parent),'+set','fs_homepath',str(folder/'home'),
                '+set','fs_game','SaberTrials','+set','com_unpackLibraries','0',
                '+set','net_ip','127.0.0.1','+set','net_port',str(port),'+set','logfile','2',
                '+set','developer','1','+exec','server.cfg']
        else:
            options=stage.arguments(folder)
            options[options.index('net_port')+1]='29088' if folder==a else '29089'
            commandline=[str(stage.executable(folder))]+options+['+exec','viewer.cfg']
        return subprocess.Popen(commandline,cwd=folder/'bin',env=env,startupinfo=startup,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    def log(which):
        path=mods[which]/'qconsole.log'
        return path.read_text(errors='replace') if path.exists() else ''
    processes={};started=time.monotonic();bot=False;fixture=0;ready=None;finished=False
    try:
        processes['server']=launch(server,True)
        while time.monotonic()-started<180:
            sl=log('server');al=log('a');bl=log('b')
            if '------- Game Initialization -------' in sl and 'a' not in processes:
                processes['a']=launch(a);print('Dedicated client A launched',flush=True)
            if 'NETWORK_A_READY' in al and not bot:
                command('addbot "Kyle Katarn" 1 free 0 "Network Bot" duelist');bot=True
                processes['b']=launch(b);print('Dedicated client B launched',flush=True)
            if 'NETWORK_B_READY' in bl and 'MVP_CAPTURE' not in sl and time.monotonic()-fixture>1:
                ready=ready or time.monotonic()
                command('st_mvpproof finish' if time.monotonic()-ready>6 else 'st_mvpproof');fixture=time.monotonic()
            if 'MVP_PLAYBACK stopped' in al and 'MVP_PLAYBACK stopped' in bl:
                finished=True
            if finished and all(processes.get(k) and processes[k].poll() is not None for k in ('a','b')):break
            if processes['server'].poll() is not None:raise RuntimeError('Dedicated server exited unexpectedly')
            time.sleep(.2)
        command('quit')
        for process in processes.values():
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        logs={key:log(key) for key in mods}
        events={key:re.findall(r'(?:MVP_(?:CAPTURE|FINAL|TRANSFER|PLAYBACK|EFFECTS|SHOT)[^\r\n]*)',value) for key,value in logs.items()}
        elapsed={key:[int(v) for v in re.findall(r'MVP_PLAYBACK stopped elapsed=(\d+)',logs[key])] for key in ('a','b')}
        result=dict(returncodes={k:p.returncode for k,p in processes.items()},finished=finished,elapsed=elapsed,events=events,
            server_sha256=build.sha(dedicated),floodProtection=True,viewerASkips=False,viewerBSkips=True)
        (root/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
        assert finished and all(v==0 for v in result['returncodes'].values()),'Network replay failed'
        assert len(elapsed['a'])==len(elapsed['b'])==1
        assert 7000<=elapsed['a'][0]<8000 and 0<elapsed['b'][0]<2500,'Skip affected the other viewer'
        assert 'MVP_TRANSFER received' in logs['a'] and 'MVP_TRANSFER received' in logs['b']
        assert 'MVP_TRANSFER rejected' not in logs['a']+logs['b']
        build.verify()
    finally:
        for process in processes.values():
            if process.poll() is None:process.kill();process.wait()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);main(parser.parse_args())
