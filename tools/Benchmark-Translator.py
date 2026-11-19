"""Measure the offline helper with synthetic chat; never reads player logs."""
import ctypes as c
from ctypes import wintypes as w
from importlib import import_module
import json
from pathlib import Path
import queue
import subprocess
import threading
import time

b=import_module('Build-Translator')

class Memory(c.Structure):
    _fields_=[('cb',w.DWORD),('PageFaultCount',w.DWORD)]+[(name,c.c_size_t) for name in
        ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage',
         'QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]


def run():
    runtime=b.OUT/'runtime'
    process=subprocess.Popen([str(runtime/'python.exe'),'-I','-B',str(runtime/'worker.py')],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    answers=queue.Queue()
    def read():
        for line in process.stdout:answers.put(line)
    threading.Thread(target=read,daemon=True).start()
    samples=[]
    corpus=[(0,1,'¿Dónde está mi equipo? Necesito ayuda.'),
        (2,1,'El equipo rojo esta cerca de nuestra base.'),(2,1,'Nos vemos mañana.'),
        (2,1,'Necesito municion para mi arma.'),(2,1,'Cuidado, hay dos enemigos detras de ti.'),
        (1,2,'Good game everyone, see you tomorrow.'),(1,2,'The blue team needs help at the bridge.'),
        (1,2,'I need ammunition for my weapon.'),(1,2,'Wait here while I check the other room.'),
        (1,2,'There are two enemies behind you.'),(1,2,'There are two enemies behind you.')]
    fixtures=b.read(b.ROOT/'tests/translator/language-fixtures.json')
    corpus += [(0,1,fixtures[code]) for code in ('ru','ja','zh','zt','ar','de','fr','it','pt','pb','ko','hi','pl','tr','uk')]
    corpus += [(7,14,fixtures['ar']),(13,17,fixtures['ko']),(12,8,fixtures['pb'])]
    memory=Memory();memory.cb=c.sizeof(memory)
    get_memory=c.WinDLL('psapi').GetProcessMemoryInfo
    get_memory.argtypes=[w.HANDLE,c.POINTER(Memory),w.DWORD]
    get_times=c.WinDLL('kernel32').GetProcessTimes
    get_times.argtypes=[w.HANDLE,*([c.POINTER(w.FILETIME)]*4)]
    try:
        for ticket,(source,target,text) in enumerate(corpus,1):
            started=time.perf_counter()
            process.stdin.write(f'STTR2 {ticket} {source} {target} {text.encode("utf8").hex()} -\n'.encode())
            process.stdin.flush()
            answer=answers.get(timeout=12).decode().split()
            elapsed=1000*(time.perf_counter()-started)
            assert answer[:3]==['STTR2',str(ticket),'ok'],answer
            assert get_memory(process._handle,c.byref(memory),c.sizeof(memory))
            samples.append(dict(source=source,target=target,ms=round(elapsed,2),
                commit_bytes=memory.PagefileUsage,working_set_bytes=memory.WorkingSetSize,input=text,output=bytes.fromhex(answer[3]).decode('utf8')))
        times=[w.FILETIME() for _ in range(4)]
        assert get_times(process._handle,*[c.byref(t) for t in times])
        cpu=sum((t.dwHighDateTime<<32)|t.dwLowDateTime for t in times[2:])/1e7
        cpu_name=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',
            'Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors | ConvertTo-Json'],text=True))
        result=dict(worker=b.sha(runtime/'worker.py'),dependencies=b.sha(b.SOURCE/'dependencies.json'),
            hardware=cpu_name,peak_working_set_bytes=memory.PeakWorkingSetSize,
            peak_commit_bytes=memory.PeakPagefileUsage,cpu_seconds=round(cpu,3),samples=samples,
            runtime_bytes=sum(p.stat().st_size for p in runtime.rglob('*') if p.is_file() and '__pycache__' not in p.parts),
            model_download_bytes=sum(e['bytes'] for e in b.read(b.SOURCE/'dependencies.json')['files'] if e['kind'] in ('model','marian')))
        b.write(b.OUT/'benchmark.json',result)
        print(json.dumps({k:v for k,v in result.items() if k!='samples'},indent=2))
        print('Latency ms:',[s['ms'] for s in samples])
    finally:
        process.stdin.close()
        try:process.wait(timeout=3)
        except subprocess.TimeoutExpired:process.kill();process.wait()


if __name__=='__main__':run()
