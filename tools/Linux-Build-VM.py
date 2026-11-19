"""Disposable loopback-only Linux compiler VM; never starts a game server."""
from pathlib import Path
import argparse, concurrent.futures, hashlib, io, json, os, subprocess, sys, urllib.request
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'dist/linux-tooling'
sys.path.insert(0,str(WORK/'python'))

def download(base,name,sums):
    expected=next(line.split()[0] for line in sums.splitlines() if line.split()[-1].lstrip('*')==name)
    dest=WORK/name
    if not dest.exists():
        urllib.request.urlretrieve(base+name,dest)
    h=hashlib.file_digest(dest.open('rb'),'sha512').hexdigest()
    if h!=expected: raise RuntimeError('Download checksum mismatch: '+name)
    print('Verified '+name,flush=True)
    return h

def setup():
    import pycdlib,paramiko
    WORK.mkdir(parents=True,exist_ok=True)
    sources=[('https://qemu.weilnetz.de/w64/','qemu-w64-setup-20260811.exe','qemu-w64-setup-20260811.sha512'),
             ('https://cloud.debian.org/images/cloud/bullseye/latest/','debian-11-genericcloud-amd64.qcow2','SHA512SUMS')]
    def one(s):
        base,name,sumfile=s
        sums=urllib.request.urlopen(base+sumfile,timeout=60).read().decode()
        return name,download(base,name,sums)
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        hashes=dict(pool.map(one,sources))
    (WORK/'download-manifest.json').write_text(json.dumps(hashes,indent=2))
    qemu=WORK/'qemu'
    if not (qemu/'qemu-system-x86_64.exe').exists():
        subprocess.run(['C:/Program Files/7-Zip/7z.exe','x',str(WORK/sources[0][1]),'-o'+str(qemu),'-y'],check=True,stdout=subprocess.DEVNULL)
    for name in ('builder','host'):
        if not (WORK/(name+'.key')).exists():
            paramiko.RSAKey.generate(3072).write_private_key_file(str(WORK/(name+'.key')))
    key=paramiko.RSAKey.from_private_key_file(str(WORK/'builder.key'))
    host=paramiko.RSAKey.from_private_key_file(str(WORK/'host.key'))
    host_private=io.StringIO();host.write_private_key(host_private)
    user='#cloud-config\n'+json.dumps({
        'hostname':'sabertrials-builder', 'ssh_pwauth':False,'disable_root':True,
        'users':[{'name':'builder','shell':'/bin/bash','sudo':'ALL=(ALL) NOPASSWD:ALL',
                  'lock_passwd':True,'ssh_authorized_keys':[key.get_name()+' '+key.get_base64()]}],
        'ssh_keys':{'rsa_private':host_private.getvalue(),'rsa_public':host.get_name()+' '+host.get_base64()},
        'growpart':{'mode':'auto','devices':['/']},'resize_rootfs':True})
    iso=pycdlib.PyCdlib();iso.new(interchange_level=3,vol_ident='cidata',joliet=3,rock_ridge='1.09')
    for name,data in [('user-data',user),('meta-data','instance-id: sabertrials-linux-build-20261023\nlocal-hostname: sabertrials-builder\n')]:
        raw=data.encode();iso.add_fp(io.BytesIO(raw),len(raw),iso_path='/'+name.upper().replace('-','_')+';1',rr_name=name,joliet_path='/'+name)
    iso.write(str(WORK/'seed.iso'));iso.close()
    disk=WORK/'builder.qcow2'
    if not disk.exists():
        subprocess.run([str(qemu/'qemu-img.exe'),'create','-f','qcow2','-F','qcow2','-b',str(WORK/sources[1][1]),str(disk),'20G'],check=True)
    print('Compiler VM prepared. No game assets or account secrets included.')

def start():
    args=[str(WORK/'qemu/qemu-system-x86_64.exe'),'-machine','q35','-accel','whpx','-accel','tcg,thread=multi',
          '-m','4096','-smp','3','-drive','file='+str(WORK/'builder.qcow2')+',if=virtio',
          '-drive','file='+str(WORK/'seed.iso')+',if=virtio,format=raw,readonly=on',
          '-nic','user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:22222-:22',
          '-display','none','-serial','file:'+str(WORK/'serial.log'),'-monitor','none']
    with (WORK/'qemu.log').open('ab') as log:
        p=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    (WORK/'pid.txt').write_text(str(p.pid));print('Compiler VM process started:',p.pid)

def connect():
    import paramiko
    c=paramiko.SSHClient();host=paramiko.RSAKey.from_private_key_file(str(WORK/'host.key'))
    c.get_host_keys().add('[127.0.0.1]:22222',host.get_name(),host)
    c.connect('127.0.0.1',port=22222,username='builder',pkey=paramiko.RSAKey.from_private_key_file(str(WORK/'builder.key')),
              look_for_keys=False,allow_agent=False,timeout=15)
    return c

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['setup','start','exec','put','get']);p.add_argument('args',nargs='*');a=p.parse_args()
    if a.action=='setup': setup()
    elif a.action=='start': start()
    else:
        with connect() as c:
            if a.action=='exec':
                _,stdout,stderr=c.exec_command(a.args[0]);stdout.channel.set_combine_stderr(True)
                for line in stdout: print(line,end='',flush=True)
                sys.exit(stdout.channel.recv_exit_status())
            else:
                with c.open_sftp() as s:
                    getattr(s,a.action)(a.args[0],a.args[1])
