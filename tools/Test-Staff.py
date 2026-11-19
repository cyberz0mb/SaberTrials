"""Exercise staff accounts with an isolated native dedicated server and clients.

Uses test-only loopback input in QA builds. All identities, databases and logs
belong to this run under dist/verification; it never edits the user's profile.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, secrets, shutil, socket, subprocess, time, sys
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'dist/verification/staff-20261012'
PORT=27977
sys.path.insert(0,str(ROOT/'tests/staff'))
from native_proxy import Proxy
from native_gameplay import gameplay
from native_ui import backup_and_media

class Native:
    def __init__(self,qa=True,installed=False):
        # Keep the private atomic-write suffix below Windows MAX_PATH in this deep workspace.
        self.qa=qa;self.installed=installed;self.run=EVIDENCE/('runtime-'+time.strftime('%H%M%S')+'-'+secrets.token_hex(2))
        self.run.mkdir(parents=True);self.processes=[];self.clients=[];self.handles=[];self.endpoints={};self.proxies={}
        self.secret=secrets.token_hex(24);self.token=secrets.token_hex(24)
        self.build=ROOT/('dist/staff-build-qa/Release' if qa else 'dist/staff-build/Release')
        self.data=self.run/'data';self.data.mkdir();(self.data/'base').mkdir();self.mod=self.data/'SaberTrials';self.mod.mkdir()
        for a in (ROOT.parent/'base').glob('assets*.pk3'):os.link(a,self.data/'base'/a.name)
        for name in ['jampgamex86_64.dll','cgamex86_64.dll']:shutil.copy2((ROOT if installed else self.build)/name,self.mod/name)
        shutil.copy2(ROOT/'uix86_64.dll',self.mod/'uix86_64.dll')
        for folder in ('ui','menu','gfx','shaders'):shutil.copytree(ROOT/folder,self.mod/folder)
        for name in ('SDL2.dll','OpenAL32.dll','rd-vanilla_x86_64.dll'):shutil.copy2(ROOT.parent/name,self.data/name)
        self.private=self.run/'private';subprocess.run([str(ROOT/'dist/staff-build-tests/Release/staff_fixture.exe'),str(self.private)],check=True)
        self.ids=dict(line.split() for line in (self.private/'public.txt').read_text().splitlines())
        manifest=json.loads((self.build/'staff-build-manifest.json').read_text())
        self.report={'kind':'installed' if installed else 'qa' if qa else 'production','coverage':'partial-smoke','milestone_accepted':False,'checks':[],'files':manifest['files'],'inputs':manifest.get('inputs',{}),'run':str(self.run.relative_to(ROOT))}
        for name,sha in self.report['files'].items():assert hashlib.sha256((self.build/name).read_bytes()).hexdigest()==sha
        if installed:
            for name,target in {'openjk.x86_64.exe':'client/SaberTrials.x86_64.exe','jampgamex86_64.dll':'jampgamex86_64.dll','cgamex86_64.dll':'cgamex86_64.dll'}.items():
                assert hashlib.sha256((ROOT/target).read_bytes()).hexdigest()==manifest['files'][name]
    def launch(self,exe,label,extra):
        env=os.environ.copy();env['LOCALAPPDATA']=str(self.private/label);env['ST_STAFF_QA_TOKEN']=self.token
        home=self.run/(label+'-home');home.mkdir(exist_ok=True)
        executable=ROOT/'client/SaberTrials.x86_64.exe' if self.installed and exe=='openjk.x86_64.exe' else self.build/exe
        args=[str(executable),'+set','fs_basepath',str(self.data),'+set','fs_homepath',str(home),'+set','fs_game','SaberTrials','+set','net_ip','127.0.0.1','+set','logfile','2']+extra
        si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
        h=open(self.run/(label+'-stdout.log'),'ab');self.handles.append(h)
        p=subprocess.Popen(args,cwd=self.data,env=env,startupinfo=si,stdout=h,stderr=h,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        self.processes.append(p);return p
    def server(self):
        cfg=f'''set rconPassword {self.secret}
set sv_pure 0
set sv_maxclients 6
set sv_maxOOBRate 0
set sv_maxOOBRateIP 0
set g_gametype 0
set g_doWarmup 0
set g_inactivity 0
set fraglimit 0
set timelimit 0
set bot_minplayers 0
set sv_floodProtect 0
devmap mp/ffa3
'''
        (self.mod/'staff-server.cfg').write_text(cfg)
        extra=['+set','dedicated','2','+set','net_port',str(PORT)]
        for i in range(1,6):extra+=['+set',f'sv_master{i}','']
        self.server_process=self.launch('openjkded.x86_64.exe','server',extra+['+exec','staff-server.cfg'])
        self.until(lambda:'Staff server public key:' in self.command('staff serverkey'),30,'server startup')
    def command(self,text):
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
            s.settimeout(.35);s.sendto(b'\xff'*4+f'rcon {self.secret} {text}'.encode(),('127.0.0.1',PORT));out=b''
            try:
                while True:
                    out+=s.recv(65535)
                    s.settimeout(.02)
            # Windows reports ICMP port-unreachable while the server is starting.
            # Let the bounded startup wait retry instead of aborting the harness.
            except (socket.timeout, ConnectionResetError):pass
        return out.decode('utf8','replace')
    def log(self,i):
        path=self.run/f'client{i}-home/SaberTrials/qconsole.log'
        return path.read_text(errors='replace') if path.exists() else ''
    def client(self,i,script=None):
        label=f'client{i}';name=['StaffOwner','StaffAdmin','StaffModerator'][i]
        log_start=len(self.log(i))
        cfg=f'connect 127.0.0.1:{self.proxies[i].port if i in self.proxies else PORT}\n'
        if script:cfg+='wait 180\nstaff trust '+self.ids['server']+'\nwait 180\n'+script+'\n'
        (self.mod/(label+'.cfg')).write_text(cfg)
        extra=['+set','net_port',str(27981+i),'+set','name',name,'+set','model','kyle/default','+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','640','+set','r_customheight','480','+set','cl_renderer','rd-vanilla','+set','s_initsound','0','+set','com_maxfps','30','+set','cl_allowDownload','0','+exec',label+'.cfg']
        p=self.launch('openjk.x86_64.exe',label,extra)
        if i<len(self.clients):self.clients[i]=p
        else:self.clients.append(p)
        self.until(lambda:name in self.command('status'),40,'client join '+label)
        if not script:
            self.until(lambda:'CL_InitCGame' in self.log(i)[log_start:],40,'client load '+label)
            self.input(i,'team free');self.input(i,'staff trust '+self.ids['server'])
            self.until(lambda:'Staff: authenticated.' in self.log(i)[log_start:],15,'client authentication '+label)
            self.close_menus(i)
            self.check('native authentication '+label)
        return p
    def endpoint(self,i):
        name=['StaffOwner','StaffAdmin','StaffModerator'][i]
        status=self.command('status')
        for line in status.splitlines():
            if name in line:
                m=re.search(r'127\.0\.0\.1:(\d+)',line)
                if m:
                    self.endpoints[i]=('127.0.0.1',int(m.group(1)))
                    return self.endpoints[i]
        if i in self.proxies:return ('127.0.0.1',self.proxies[i].port)
        if i in self.endpoints and self.clients[i].poll() is None:return self.endpoints[i]
        raise AssertionError('Client endpoint not present: '+name+'\n'+status)
    def input(self,i,text):
        endpoint=self.endpoint(i)
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:s.sendto(b'\xff'*4+f'stqacmd {self.token} {text.encode().hex()}'.encode(),endpoint)
        time.sleep(.15)
    def action(self,i,text,expected,timeout=12):
        before=len(self.log(i));self.input(i,text)
        try:self.until(lambda:expected in self.log(i)[before:],timeout,text)
        except AssertionError as error:
            raise AssertionError(str(error)+'\nClient reply: '+self.log(i)[before:]) from error
        return self.log(i)[before:]
    def client_state(self,i):
        reply=self.action(i,'qa_client_state','STAFF_CLIENT_QA')
        line=next(line for line in reply.splitlines() if 'STAFF_CLIENT_QA' in line)
        return {k:float(v) for k,v in re.findall(r'(\w+)=(-?[\d.]+)',line)}
    def close_menus(self,i):
        for attempt in range(3):
            state=self.client_state(i)
            if state['catcher']==0:return
            self.input(i,'toggleconsole' if int(state['catcher'])&1 else 'togglemenu')
        assert self.client_state(i)['catcher']==0,'Test movement requires closed menus'
    def view(self,i):
        reply=self.action(i,'set st_staffQAProbe '+str(int(time.monotonic()*1000)%2000000000),'STAFF_VIEW')
        rows=[line for line in reply.splitlines() if 'STAFF_VIEW' in line or 'STAFF_VISIBLE' in line]
        parsed=[{k:float(v) for k,v in re.findall(r'(\w+)=(-?[\d.]+)',line)} for line in rows]
        return parsed[0],{int(row['slot']):row for row in parsed[1:]}
    def states(self):
        s=self.command('st_staffqa state 0');out={}
        for line in s.splitlines():
            if 'STAFF_QA ' in line:
                fields=dict(re.findall(r'(\w+)=(-?[\d.]+)',line));out[int(fields['slot'])]={k:float(v) for k,v in fields.items()}
        assert out,s
        with (self.run/'states.jsonl').open('a') as history:history.write(json.dumps(out)+'\n')
        return out
    def until(self,condition,timeout,description):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            if condition():return
            if any(p.poll() not in (None,0) for p in self.processes):raise AssertionError('Native process crashed: '+description)
            time.sleep(.2)
        raise AssertionError('Timed out: '+description)
    def check(self,name):self.report['checks'].append(name);print('PASS '+name,flush=True)
    def startup(self):
        for attempt in range(8):
            self.server()
            assert self.ids['server'] in self.command('staff serverkey')
            assert 'Fixture Owner' in self.command('staff list')
            self.stop(self.server_process)
        self.check('eight redirected-output dedicated startups and persistent server identity/roster')
    def accounts(self):
        for i in range(3):self.client(i)
        self.action(1,'staff role '+self.ids['client2']+' admin','denied')
        self.action(2,'staff remove '+self.ids['client0'],'denied')
        self.action(0,'staff remove '+self.ids['client0'],'denied')
        self.check('admin/moderator/self hierarchy denials')
        self.action(0,'staff list','Fixture Owner')
        self.action(0,'staff remove '+self.ids['client2'],'updated')
        self.action(2,'ghost on','timed out',15)
        self.action(0,'staff add '+self.ids['client2']+' moderator "Fixture Moderator"','updated')
        self.action(2,'staff login','authenticated')
        self.check('immediate removal and explicit re-enrollment')
        self.action(0,'freeze Staff','No unique')
        self.check('ambiguous target rejected')
        self.command('map_restart 0');time.sleep(2)
        self.action(0,'staff whoami','\nOwner\n')
        self.check('map restart reauthentication and permanent role')
    def movement(self):
        for i in range(3):self.close_menus(i)
        # An observed clear spawn column in mp/ffa3, rather than a random ceiling.
        self.command('st_staffqa place 2 2432 -744 -39.88')
        original=self.states();target=original[2]
        self.command(f"st_staffqa place 2 {target['x']} {target['y']} {target['z']+160}")
        self.states()
        self.action(0,'freeze #2','completed')
        a=self.states()[2];time.sleep(.5);b=self.states()[2]
        assert a['z']>target['z']+40,('freeze must be midair',target,a)
        assert a['mode']==b['mode']==1 and abs(a['z']-b['z'])<.01,(a,b)
        self.input(2,'+forward');self.input(2,'+attack');time.sleep(.4);self.input(2,'-forward');self.input(2,'-attack')
        after=self.states()[2]
        assert all(abs(after[axis]-b[axis])<.01 for axis in ('x','y','z')),(after,b)
        assert all(abs(after[axis])<.01 for axis in ('vx','vy','vz')),after
        health=self.states()[2]['health'];self.command('st_staffqa hit 2 0 50');assert self.states()[2]['health']==health
        team=self.states()[2]['team'];self.input(2,'kill');self.input(2,'team spectator');after=self.states()[2]
        assert after['mode']==1 and after['health']==health and after['team']==team,after
        self.check('midair freeze, all-axis movement lock, incoming damage and kill/team denial')
        self.action(0,'unfreeze #2','completed');time.sleep(.3);assert self.states()[2]['mode']==0
        self.action(0,'ghost on','completed');assert self.states()[0]['mode']==2
        before=self.states()[0];self.input(0,'+moveup');time.sleep(.6);moving=self.client_state(0);self.input(0,'-moveup');after=self.states()[0]
        assert after['z']>before['z'],(before,after,moving)
        health=self.states()[1]['health'];self.command('st_staffqa hit 1 0 50');assert self.states()[1]['health']==health
        self.action(0,'ghost off','Ghost off');assert self.states()[0]['mode']==0
        self.check('ghost flight, scripted outgoing damage denial and exit')
        self.action(1,'ghost on','completed')
        self.action(0,'staff role '+self.ids['client1']+' moderator','updated');assert self.states()[1]['mode']==0
        self.check('demotion clears active ghost')
        self.action(0,'travel coords nan 0 0','denied')
        self.action(0,'travel coords 999999 0 0','denied')
        self.action(0,'summon #2','completed');self.action(0,'travel #2','completed')
        self.check('safe summon/travel; nonfinite and excessive coordinates rejected')
    def lifecycle(self):
        self.action(0,'staff role '+self.ids['client1']+' admin','updated')
        self.action(1,'staff login','authenticated')
        # A spectator/normal player's visible name cannot grant the Owner's authority.
        self.action(2,'staff logout','Logged out')
        self.input(2,'name StaffOwner')
        self.action(2,'staff whoami','login required')
        self.input(2,'cmd freeze #0')
        assert self.states()[0]['mode']==0
        self.input(2,'name StaffModerator')
        self.action(2,'staff login','authenticated')
        self.check('copied display name and unsigned moderation command do not elevate')
        # Wrong server pins must fail authentication; restoring the verified pin recovers.
        self.action(2,'staff trust '+self.ids['client0'],'timed out',15)
        self.action(2,'staff trust '+self.ids['server'],'authenticated')
        self.check('wrong server identity rejected; verified pin recovers')
        self.action(1,'freeze #2','completed')
        self.action(1,'staff logout','Logged out')
        assert self.states()[2]['mode']==0
        self.action(1,'staff whoami','login required')
        self.action(1,'staff login','authenticated')
        self.check('logout releases effects and disables staff actions until login')
        for i in (1,2):
            self.endpoint(i)
            self.input(i,'disconnect')
            self.until(lambda:i not in self.states(),5,'client disconnect')
            start=len(self.log(i));self.input(i,'reconnect')
            self.until(lambda:'Staff: authenticated.' in self.log(i)[start:],25,'reconnect authentication')
            self.action(i,'staff whoami','\nAdmin\n' if i==1 else '\nModerator\n')
            self.input(i,'team free')
        self.check('appointed roles survive disconnect/reconnect')
        starts=[len(self.log(i)) for i in range(3)]
        self.command('map mp/ffa1')
        for i in range(3):
            self.until(lambda i=i:'Staff: authenticated.' in self.log(i)[starts[i]:],35,'map-change authentication')
        self.check('appointments and pinned login survive a different map')
        for i in range(3):
            self.endpoint(i);self.input(i,'disconnect')
        self.stop(self.server_process)
        self.server()
        for i in range(3):
            start=len(self.log(i));self.input(i,'reconnect')
            self.until(lambda i=i:'Staff: authenticated.' in self.log(i)[start:],30,'server-restart authentication')
            self.action(i,'staff whoami',['\nOwner\n','\nAdmin\n','\nModerator\n'][i])
            self.input(i,'team free')
        self.check('all three appointments survive a full dedicated-process restart')
        self.input(2,'disconnect')
        self.until(lambda:2 not in self.states(),5,'offline removal setup')
        self.action(0,'staff remove '+self.ids['client2'],'updated')
        start=len(self.log(2));self.input(2,'reconnect')
        self.until(lambda:'timed out' in self.log(2)[start:],30,'offline removed account rejected')
        self.action(2,'ghost on','login required')
        assert self.states()[2]['role']==0
        self.check('offline removal prevents login after reconnect')
        self.action(0,'staff add '+self.ids['client2']+' moderator "Fixture Moderator"','updated')
        self.action(2,'staff login','authenticated');self.input(2,'team free')
    def stop(self,p):
        if p.poll() is None:
            p.terminate()
            try:p.wait(8)
            except subprocess.TimeoutExpired:p.kill();p.wait(8)
        if p in self.processes:self.processes.remove(p)
    def listen(self):
        destination=self.private/'client0/SaberTrialsStaff/servers/27981'
        destination.parent.mkdir(exist_ok=True)
        shutil.copytree(self.private/'server/SaberTrialsStaff/servers/27977',destination)
        cfg='''set sv_pure 0
set sv_maxclients 1
set bot_minplayers 0
set g_gametype 0
set g_doWarmup 0
devmap mp/ffa3
wait 120
team free
wait 30
staff serverkey
staff trust SERVERKEY
wait 120
staff whoami
wait 30
ghost on
wait 45
ghost off
wait 30
map_restart 0
wait 120
staff whoami
st_photo
wait 30
set st_photoFreeze 1
wait 30
echo STAFF_FROZEN_START
st_staffqa time 0
wait 60
st_staffqa time 0
echo STAFF_FROZEN_END
set st_photoFreeze 0
wait 30
st_staffqa time 0
st_photo
wait 30
staff whoami
echo STAFF_LISTEN_DONE
'''.replace('SERVERKEY',self.ids['server'])
        (self.mod/'listen.cfg').write_text(cfg)
        extra=['+set','net_port','27981','+set','name','StaffOwner','+set','model','kyle/default','+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','640','+set','r_customheight','480','+set','s_initsound','0','+set','com_maxfps','30','+exec','listen.cfg']
        self.clients.append(self.launch('openjk.x86_64.exe','client0',extra))
        self.until(lambda:'STAFF_LISTEN_DONE' in self.log(0),60,'listen-server staff/photo sequence')
        log=self.log(0)
        assert log.count('Staff: authenticated.')>=2 and log.count('\nOwner\n')>=3 and 'Ghost off' in log,log[-2200:]
        times=[int(t) for t in re.findall(r'STAFF_CLOCK level=(\d+)',log)]
        assert len(times)==3 and times[0]==times[1] and times[2]>times[1],times
        self.check('native listen-server pinned login, ghost, map-restart login and persistent Owner')
        self.check('solo Photo Mode freeze holds server time; Live resumes it')
    def visuals(self):
        self.client(0);self.input(0,'set con_notifytime 0')
        for height in (720,1024):
            before=len(self.log(0))
            self.input(0,f'set r_customwidth 1280; set r_customheight {height}; vid_restart')
            self.until(lambda:'CL_InitCGame' in self.log(0)[before:],30,'renderer resize')
            self.close_menus(0);self.action(0,'ghost on','completed')
            # Let the weapon-selection overlay and renderer restart settle.
            time.sleep(3)
            for surface in ('hud','pause'):
                if surface=='pause':
                    self.input(0,'ui_openmenu ingame')
                    time.sleep(1)
                    assert int(self.client_state(0)['catcher'])&2
                name=f'staff-{height}-{surface}';self.input(0,'screenshot_png '+name)
                path=self.run/'client0-home/SaberTrials/screenshots'/(name+'.png')
                self.until(path.exists,5,'native '+surface+' screenshot')
                self.report.setdefault('screenshots',[]).append(str(path.relative_to(ROOT)))
            self.close_menus(0);self.action(0,'ghost off','Ghost off')
        self.check('native HUD/pause captures at 1280x720 and 1280x1024 for visual inspection')
    def same_identity(self):
        self.client(0)
        shutil.copy2(self.private/'client0/SaberTrialsStaff/client/identity.key',self.private/'client1/SaberTrialsStaff/client/identity.key')
        self.client(1);self.client(2)
        self.action(1,'staff whoami','\nOwner\n')
        self.action(1,'staff identity',self.ids['client0'])
        self.action(0,'freeze #2','completed');self.action(1,'ghost on','completed')
        self.action(0,'staff logout','Logged out')
        s=self.states();assert s[2]['mode']==0 and s[1]['mode']==2,s
        self.action(0,'staff login','authenticated');self.action(1,'ghost off','Ghost off')
        self.action(1,'freeze #2','completed');self.action(0,'ghost on','completed')
        self.input(1,'disconnect');time.sleep(.5)
        s=self.states();assert s[2]['mode']==0 and s[0]['mode']==2,s
        self.check('same-identity logout/disconnect releases only the issuing connection effects')
        start=len(self.log(1));self.input(1,'reconnect')
        self.until(lambda:'Staff: authenticated.' in self.log(1)[start:],30,'shared identity reconnect')
        self.input(1,'team free');self.close_menus(1);self.action(1,'ghost on','completed')
        assert 'saved' in self.command('staff owner add '+self.ids['client2']+' "Recovery Owner"')
        assert 'saved' in self.command('staff owner remove '+self.ids['client0'])
        s=self.states();assert s[0]['mode']==s[1]['mode']==0 and s[0]['role']==s[1]['role']==0,s
        self.check('account revocation clears both same-identity connections immediately')
    def network(self):
        proxy=Proxy(('127.0.0.1',PORT));self.proxies[0]=proxy
        proxy.drops[b'stsession']=1
        self.client(0);self.client(1);self.client(2)
        assert proxy.counts.get(b'stsession',0)>=2
        self.check('native login recovers a dropped successful session reply')
        proxy.duplicate_actions=True;proxy.drops[b'stresult']=1
        self.action(0,'ghost on','completed');captured=proxy.last_action
        assert self.states()[0]['mode']==2
        server_log=(self.run/'server-home/SaberTrials/qconsole.log').read_text(errors='replace')
        # Each action reaches the native server multiple times; the game runs once.
        assert len(re.findall(r'Staff action: Owner #0 \| ghost on \| allowed',server_log))==1
        self.check('lost action reply and duplicate signed requests execute ghost once')
        self.action(0,'ghost off','Ghost off');self.action(0,'staff logout','Logged out')
        proxy.replay(captured);time.sleep(.3);assert self.states()[0]['mode']==0
        self.action(0,'staff login','authenticated');proxy.replay(captured);time.sleep(.3);assert self.states()[0]['mode']==0
        self.check('captured native action rejected after logout and in a new session')
        proxy.duplicate_actions=False;proxy.hold_results=True
        self.input(0,'freeze #2');self.until(lambda:bool(proxy.held),5,'held target resolution')
        self.input(2,'disconnect');self.until(lambda:2 not in self.states(),5,'target slot disconnect')
        start=len(self.log(2));self.input(2,'reconnect')
        self.until(lambda:'Staff: authenticated.' in self.log(2)[start:],25,'replacement connection')
        self.input(2,'team free');self.close_menus(2)
        start=len(self.log(0));proxy.release()
        self.until(lambda:'Action denied' in self.log(0)[start:],8,'stale target rejected')
        assert self.states()[2]['mode']==0
        self.check('reused player slot cannot inherit a delayed freeze target')
        proxy.hold_results=True;self.input(0,'travel server 127.0.0.1:27998')
        self.until(lambda:bool(proxy.held),5,'held server travel authorization')
        self.action(0,'travel server 127.0.0.1:27999','wait for the current request')
        start=len(self.log(0));proxy.release();time.sleep(.4)
        self.input(0,'cl_reconnectArgs')
        tail=self.log(0)[start:]
        assert '127.0.0.1:27998' in tail and '27999' not in tail,tail
        self.check('delayed server travel keeps the originally authorized destination')
    def close(self):
        for p in list(reversed(self.processes)):self.stop(p)
        for proxy in self.proxies.values():proxy.close()
        for h in self.handles:h.close()
    def save(self):
        self.report['passed']=True;(self.run/'report.json').write_text(json.dumps(self.report,indent=2)+'\n')
        (EVIDENCE/(self.report['kind']+'-smoke-pass.json')).write_text(json.dumps(self.report,indent=2)+'\n')
        (EVIDENCE/(self.report['kind']+'-'+self.report['suite']+'-pass.json')).write_text(json.dumps(self.report,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('suite',choices=['startup','accounts','movement','lifecycle','same-identity','network','gameplay','backup-media','listen','visuals','all','production']);p.add_argument('--qa',action='store_true');p.add_argument('--installed',action='store_true');args=p.parse_args()
    if args.installed and args.suite!='production':p.error('--installed requires the production suite')
    # Never attach to an existing server on the test port.
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:s.bind(('127.0.0.1',PORT))
    n=Native(args.suite!='production',args.installed)
    n.report['suite']=args.suite
    try:
        if args.suite=='startup':n.startup()
        elif args.suite!='listen':n.server()
        if args.suite=='production':
            script='team free\nwait 30\nstaff whoami\nwait 30\nghost on\nwait 30\nghost off\nwait 30\ntravel coords nan 0 0\nwait 30\nstaff remove '+n.ids['client1']+'\nwait 30\nstaff logout\nwait 30\necho STAFF_PRODUCTION_DONE\n'
            n.client(0,script);n.until(lambda:'STAFF_PRODUCTION_DONE' in n.log(0),45,'production commands')
            log=n.log(0);assert 'Staff: authenticated.' in log and '\nOwner\n' in log and 'Ghost off' in log and 'Logged out' in log,log[-2500:]
            assert 'Account updated' in log and 'Action denied' in log
            n.stop(n.clients[0]);n.stop(n.server_process);n.server()
            roster=n.command('staff list')
            assert any(n.ids['client1'] in line and 'disabled' in line for line in roster.splitlines()),roster
            assert n.ids['server'] in n.command('staff serverkey')
            n.check('production native login, ghost/exit, unsafe travel denial and logout')
            n.check('production account removal and server identity persist across a full process restart')
        elif args.suite=='network':n.network()
        elif args.suite=='same-identity':n.same_identity()
        elif args.suite=='gameplay':gameplay(n)
        elif args.suite=='backup-media':backup_and_media(n)
        elif args.suite=='listen':n.listen()
        elif args.suite=='visuals':n.visuals()
        elif args.suite!='startup':
            n.accounts()
            if args.suite in ('movement','all'):n.movement()
            if args.suite in ('lifecycle','all'):n.lifecycle()
        n.save()
    except Exception as error:
        n.report.update(passed=False,error=str(error))
        (n.run/'report.json').write_text(json.dumps(n.report,indent=2)+'\n')
        raise
    finally:n.close()
if __name__=='__main__':main()
