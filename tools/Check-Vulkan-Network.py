"""Check the candidate client against the installed, unchanged dedicated server on loopback."""
from importlib import import_module
import argparse
from datetime import datetime
import os
import secrets
import shutil
import socket
import subprocess
import time

c=import_module('Check-Vulkan')
b=c.b

def run(enhanced=False):
    level = 'st_far' if enhanced else 'mp/ffa3'
    client = None
    if enhanced:
        folder = b.ROOT/'dist/vulkan-content'/('network-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        mod = folder/'home/SaberTrials'
        mod.mkdir(parents=True)
        client = b.ROOT/'client/SaberTrials.x86_64.exe'
        b.write(folder/'inputs.json', {name: b.sha(b.ROOT/name) for name in
                ('client/SaberTrials.x86_64.exe', 'client/rd-vulkan_x86_64.dll', 'cgamex86_64.dll')})
    else:
        folder,mod=c.stage('dedicated-loopback')
    serverhome=folder/'server-home/SaberTrials';serverhome.mkdir(parents=True)
    shutil.copyfile(b.ROOT/'jampgamex86_64.dll',serverhome/'jampgamex86_64.dll')
    if enhanced:
        for target in (mod, serverhome):
            shutil.copyfile(b.ROOT/'dist/enhanced-maps/maps/st_far.pk3', target/'st_far.pk3')
    password=secrets.token_hex(16)
    settings=dict(fs_basepath=b.ROOT.parent,fs_homepath=folder/'server-home',fs_game='SaberTrials',
        com_unpackLibraries=0,logfile=2,dedicated=1,net_ip='127.0.0.1',net_port=29740,
        sv_pure=0,g_gametype=0,g_warmup=0,fraglimit=0,rconPassword=password)
    command=[str(b.ROOT/'client/openjkded.x86_64.exe')]
    for key,value in settings.items():command+=['+set',key,str(value)]
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    server=subprocess.Popen(command+['+map',level],cwd=b.ROOT.parent,startupinfo=startup,
        env={**os.environ,'LOCALAPPDATA':str(folder/'server-local-app-data')},
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    process=None
    try:
        logfile=serverhome/'qconsole.log'
        for _ in range(100):
            if server.poll() is not None:raise RuntimeError('Dedicated server exited')
            if logfile.exists() and '------- Game Initialization -------' in logfile.read_text(errors='replace'):
                time.sleep(1);break
            time.sleep(.1)
        lines=['wait 80','connect 127.0.0.1:29740','wait 500','team free','wait 120',
            'st_emoteuiqa resume','set cg_thirdPerson 1','wait 60','st_activeRenderer',
            '+attack','+forward','wait 100','-attack','-forward','say "Vulkan loopback client check"',
            'wait 80','screenshot_png dedicated-client','wait 20','echo ST_VULKAN_NETWORK_DONE','disconnect','quit']
        if enhanced:
            lines[0:0] = ['set r_enhancedModels 1', 'set r_lodscale 20', 'set cg_deferPlayers 0',
                          'set cg_forceModel 0', 'set model t800_human/default']
            lines.insert(lines.index('st_activeRenderer'), 'viewpos')
        process=c.launch(folder,mod,'rd-vulkan',lines,{'r_vbo_models': 1} if enhanced else None,
                         executable=client)
        assert process.wait(timeout=90)==0
        output=(mod/'qconsole.log').read_text(errors='replace')
        serverlog=logfile.read_text(errors='replace')
        assert 'ST_VULKAN_NETWORK_DONE' in output and 'ERROR:' not in output
        assert 'Saved graphics settings retained.' not in output,'Unexpected OpenGL fallback'
        assert 'rd-vulkan' in c.re.sub(r'\^[0-9]','',output).split('Cvar st_activeRenderer = ')[-1]
        assert 'Vulkan loopback client check' in serverlog and 'ClientBegin:' in serverlog
        assert (mod/'screenshots/dedicated-client.png').exists()
        if enhanced:
            positions = c.re.findall(r'maps/st_far\.bsp \((-?\d+) -?\d+ (-?\d+)\)', output)
            assert any(abs(int(x)) > 130500 and abs(int(z)) > 130500 for x,z in positions)
            assert c.re.search(r'ST_COSMETIC draw .*visual=models/cosmetics/t800_human/model.glm .*lod=0', output)
            assert str(b.ROOT/'client') in next(row for row in output.splitlines() if 'Trying to load "rd-vulkan' in row)
    finally:
        if process and process.poll() is None:process.kill();process.wait()
        if server.poll() is None:
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as connection:
                connection.sendto(b'\xff\xff\xff\xffrcon '+password.encode()+b' quit\n',('127.0.0.1',29740))
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.terminate();server.wait()
    source = b.ROOT/'development-source/vulkan/enhanced-content.patch' if enhanced else b.OUT/'source-receipt.json'
    b.write(folder/'result.json',dict(passed=True,source=b.sha(source),map=level,installed=enhanced,
        scenario='dedicated-loopback',inputs=b.read(folder/'inputs.json'),
        server=b.sha(b.ROOT/'client/openjkded.x86_64.exe'),game=b.sha(b.ROOT/'jampgamex86_64.dll'),
        client_log=b.sha(mod/'qconsole.log'),server_log=b.sha(logfile),
        screenshot=b.sha(mod/'screenshots/dedicated-client.png')))
    print('Passed dedicated loopback: '+str(folder),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-enhanced', action='store_true', help='Test the installed client, far map and T800 on loopback')
    run(parser.parse_args().installed_enhanced)
