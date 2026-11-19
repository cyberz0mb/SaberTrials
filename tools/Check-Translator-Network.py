"""Three production clients on loopback: channel audiences and UTF-8 transport."""
from datetime import datetime
from importlib import import_module
import os
import re
import subprocess
import sys
import struct
import time
from zipfile import ZipFile

b=import_module('Build-Translator');checks=import_module('Check-Translator')

def log(folder):
    path=folder/'home/SaberTrials/qconsole.log'
    return path.read_text(encoding='utf8',errors='replace') if path.exists() else ''

def wait_for(folder,marker,timeout=70):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if marker in log(folder):return
        time.sleep(.25)
    raise AssertionError((marker,log(folder)[-2200:]))

def start(folder,lines,port,server=False,locations=False):
    if server:
        mod=folder/'home/SaberTrials';mod.mkdir(parents=True)
        exe=b.ROOT/'client/openjkded.x86_64.exe'
    else:
        mod,_=checks.stage(folder,'chat');exe=folder/'client/SaberTrials.x86_64.exe'
    if locations:
        # Stock CTF maps have no target_location entities. Add named markers to
        # an isolated map copy so real lchat/ltchat routing can be exercised.
        with ZipFile(b.ROOT.parent/'base/assets3.pk3') as archive:data=bytearray(archive.read('maps/mp/ctf1.bsp'))
        offset,size=struct.unpack_from('<ii',data,8);entities=data[offset:offset+size].rstrip(b'\0')
        blocks=re.findall(rb'\{[^}]*\}',entities)
        for block in blocks:
            if re.search(rb'"classname"\s+"(?:info_player|team_CTF)[^"]*"',block):
                origin=re.search(rb'"origin"\s+"([^"]+)"',block)
                if origin:entities+=b'\n{\n"classname" "target_location"\n"message" "Translator Test Room"\n"origin" "'+origin[1]+b'"\n}\n'
        entities+=b'\0';struct.pack_into('<ii',data,8,len(data),len(entities));data+=entities
        path=mod/'maps/mp/st_translate_ctf.bsp';path.parent.mkdir(parents=True);path.write_bytes(data)
    (mod/'test.cfg').write_text('\n'.join(lines)+'\n',encoding='utf8')
    (mod/'watch.cfg').write_text('st_translatorinfo\nwait 120\nexec watch.cfg\n')
    options=dict(fs_basepath=b.ROOT.parent,fs_homepath=folder/'home',fs_game='SaberTrials',com_unpackLibraries=0,
        logfile=2,net_ip='127.0.0.1',net_port=port,sv_pure=0,sv_allowDownload=0)
    if not server:options.update(r_fullscreen=0,r_mode=-1,r_customwidth=960,r_customheight=540,
        cl_renderer='rd-vanilla',com_maxfps=60,s_initsound=0,com_introplayed=1,cl_allowDownload=0)
    command=[str(exe),'+safe']
    for name,value in options.items():command+=['+set',name,str(value)]
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    return subprocess.Popen(command+['+exec','test.cfg'],cwd=b.ROOT.parent,startupinfo=si,
        env={**os.environ,'LOCALAPPDATA':str(folder/'local-app-data')},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def run(locations=False):
    folder=b.OUT/f'network-{"locations-" if locations else ""}{datetime.now():%H%M%S}';processes=[];results={}
    source_hash=b.sha(b.RECEIPT);files={name:b.sha(path) for name,path in b.files().items()}
    print(folder,flush=True)
    try:
        server=folder/'server'
        processes.append(start(server,['set sv_hostname "Translator local test"','set sv_maxclients 4',
            'set g_gametype '+('8' if locations else '6'),'set g_warmup 0','set st_mvpPrototype 0','set sv_floodProtect 0',
            *['set sv_master'+str(i)+' ""' for i in range(1,6)],'devmap mp/'+('st_translate_ctf' if locations else 'ctf1')],29344,True,locations))
        wait_for(server,'InitGame:')
        common=['wait 60','set st_translate 1','set st_translateSource 0','set st_translateTarget 1',
            'set st_translateOriginal 1','set cg_chatBox 60000','set st_chatHeight 45','set st_chatWidth 90',
            'connect 127.0.0.1:29344','wait 700']
        for i,(name,team) in enumerate([('RedReader','red'),('BlueReader','blue'),('Sender','red')]):
            player=folder/name
            lines=['set name '+name]+common+['team '+team,'wait 120','ui_openmenu ingame_setup','wait 10',
                'togglemenu','wait 50','echo ST_CHAT_READY']
            if name=='Sender':
                lines+=['wait 120','say "¿Dónde está mi equipo? Necesito ayuda."','wait 900',
                    'say_team "El equipo rojo esta cerca de nuestra base."','wait 300',
                    'tell 0 "Esta es una conversación privada con nuestro compañero de equipo."','wait 300',
                    'tell 1 "Esta es una conversación privada con el otro jugador."','wait 300',
                    'say "私のチームはどこですか？助けが必要です。"','wait 600',
                    'st_translatorinfo','screenshot_png channels','echo ST_CHANNELS_DONE','exec watch.cfg']
            else:lines+=['exec watch.cfg']
            processes.append(start(player,lines,29345+i,locations=locations));wait_for(player,'ST_CHAT_READY')
        wait_for(folder/'Sender','ST_CHANNELS_DONE',100)
        time.sleep(2)
        expected={'Sender':(5,2,1,2),'RedReader':(4,2,1,1),'BlueReader':(3,2,0,1)}
        for name,counts in expected.items():
            record=log(folder/name)
            states=re.findall(r'ST_TRANSLATOR [^\n]+',record);assert states,name
            final=states[-1]
            actual=tuple(int(re.search(key+r'=(\d+)',final)[1]) for key in ('translated','public','team','private'))
            assert actual==counts,(name,actual,final)
            assert '私のチーム' in record,(name,'UTF-8 did not survive server transport')
            if name=='BlueReader':assert 'El equipo rojo' not in record and 'con nuestro compañero' not in record
            if name=='RedReader':assert 'con el otro jugador' not in record
            if locations and name=='Sender':assert re.search(r'\*\(Sender\^7\): .*<.+>',record),record[-2000:]
            results[name]=dict(state=final,log=b.sha(folder/name/'home/SaberTrials/qconsole.log'))
    finally:
        for p in reversed(processes):
            if p.poll() is None:p.terminate();p.wait(timeout=15)
    for name in results:results[name]['log']=b.sha(folder/name/'home/SaberTrials/qconsole.log')
    assert source_hash==b.sha(b.RECEIPT) and files=={name:b.sha(path) for name,path in b.files().items()},'Build changed during network check'
    b.write(folder/'result.json',dict(proof_version=2,source=source_hash,files=files,
        runtime=b.sha(b.OUT/'runtime/worker.py'),server=b.sha(b.ROOT/'jampgamex86_64.dll'),locations=locations,results=results))
    print('Passed public, team, private audiences and Unicode transport on three clients.',flush=True)

if __name__=='__main__':run('--locations' in sys.argv)
