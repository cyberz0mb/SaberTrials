"""Loopback-only native transport fault fixture. Never writes packet contents."""
import socket
import threading

class Proxy:
    def __init__(self,server):
        self.server=server;self.client=None;self.running=True
        self.socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.socket.bind(('127.0.0.1',0));self.socket.settimeout(.1)
        self.port=self.socket.getsockname()[1]
        self.drops={};self.duplicate_actions=False;self.hold_results=False
        self.held=[];self.last_action=None;self.counts={}
        self.lock=threading.Lock();self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
    def run(self):
        while self.running:
            try:data,source=self.socket.recvfrom(65535)
            except socket.timeout:continue
            except OSError:break
            kind=data[4:].split(b' ',1)[0] if data.startswith(b'\xff'*4) else b'game'
            with self.lock:
                if source==self.server:
                    self.counts[kind]=self.counts.get(kind,0)+1
                    if self.drops.get(kind,0):self.drops[kind]-=1;continue
                    if kind==b'stresult' and self.hold_results:self.held.append(data);continue
                    if self.client:self.socket.sendto(data,self.client)
                elif kind==b'stqacmd':
                    if self.client:self.socket.sendto(data,self.client)
                else:
                    self.client=source
                    if kind==b'staction':self.last_action=data
                    self.socket.sendto(data,self.server)
                    if kind==b'staction' and self.duplicate_actions:self.socket.sendto(data,self.server)
    def release(self):
        with self.lock:
            self.hold_results=False
            for packet in self.held:self.socket.sendto(packet,self.client)
            self.held.clear()
    def replay(self,packet):self.socket.sendto(packet,self.server)
    def close(self):
        self.running=False;self.thread.join(2);self.socket.close()
