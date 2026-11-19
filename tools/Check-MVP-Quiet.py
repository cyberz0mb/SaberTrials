"""Verify a real replay with normal console settings and its visible final hold."""
from pathlib import Path
import argparse,importlib.util,json,os,re,secrets,socket,subprocess,time
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('stage',ROOT/'tools/Stage-MVP-Cinematic.py')
stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)

def main(a):
    folder=stage.OUT/'qa'/a.run;assert not folder.exists()
    mod=stage.installed_home(folder) if a.installed else stage.stage(folder)
    password=secrets.token_hex(16);port=29104
    lines=stage.match_settings()+['set developer 0','set g_logSync 1','set rconPassword '+password,
        'set cg_saberTrail 1','set cg_dismember 2','devmap mp/duel1','wait 180','team free','wait 90',
        'addbot "Kyle Katarn" 1 free 0 "Quiet Bot" duelist','wait 240','st_mvptestready',
        'setviewpos 480 640 200 90','wait 120','st_mvpproof','wait 350',
        '+attack','wait 180','-attack','wait 2400','quit']
    (mod/'quiet.cfg').write_text('\n'.join(lines)+'\n')
    cmd=[str(stage.executable(folder,a.installed))]+stage.arguments(folder,a.renderer,a.installed)
    cmd[cmd.index('net_port')+1]=str(port);cmd+=['+exec','quiet.cfg']
    env=os.environ.copy();env['LOCALAPPDATA']=str(folder/'local-app-data')
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    proc=subprocess.Popen(cmd,cwd=ROOT.parent if a.installed else folder/'bin',env=env,startupinfo=startup,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    def command(value):
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.sendto(b'\xff'*4+('rcon '+password+' '+value+'\n').encode(),('127.0.0.1',port))
    started=time.monotonic();kill=None;sent=set()
    try:
        while proc.poll() is None:
            now=time.monotonic();game=mod/'games.log'
            if kill is None and game.exists() and 'by MOD_SABER' in game.read_text(errors='replace'):kill=now
            if kill is not None:
                for delay,name in ((6,'quiet-linger-a'),(7,'quiet-linger-b'),(9.5,'quiet-scoreboard')):
                    if now-kill>=delay and name not in sent:
                        command('screenshot_png '+name);sent.add(name)
                if now-kill>11:command('quit')
            if now-started>90:raise RuntimeError('Quiet replay timed out')
            time.sleep(.1)
        assert proc.returncode==0 and kill is not None and len(sent)==3
        log=(mod/'qconsole.log').read_text(errors='replace')
        assert not re.search(r'MVP_(?:CAPTURE|FINAL|LIMBS|PLAYBACK|SHOT|EFFECTS|LINGER|TRANSFER)|WINNER_(?:FINAL|ROUND)',log),'Normal console exposed diagnostics'
        shots=mod/'screenshots'
        images=[str(shots/(name+'.png')) for name in ('quiet-linger-a','quiet-linger-b','quiet-scoreboard')]
        comparison=json.loads(subprocess.check_output(['powershell','-NoProfile','-ExecutionPolicy','Bypass',
            '-File',str(ROOT/'tools/Compare-MVP-Frames.ps1'),*images],text=True))
        stable=comparison['stable'];results_changed=comparison['scoreboard']
        assert stable>.97 and results_changed<.9,(stable,results_changed)
        result=dict(passed=True,returncode=proc.returncode,installed=a.installed,developer=0,
            realSaberKill=True,automaticDiagnostics=0,finalSceneSimilarity=stable,scoreboardSimilarity=results_changed,
            screenshots={p.name:stage.helper().sha(p) for p in shots.glob('quiet-*.png')})
        (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--installed',action='store_true')
    p.add_argument('--renderer',choices=('vanilla','rend2'),default='vanilla');main(p.parse_args())
